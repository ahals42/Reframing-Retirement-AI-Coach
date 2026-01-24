"""Core conversational agent logic with security controls"""

from __future__ import annotations

import re
import logging
from typing import Dict, Generator, List, Optional, Pattern

from openai import OpenAI

from coach.prompts import build_coach_prompt
from rag.retriever import RagRetriever, RetrievalResult, RetrievedChunk
from rag.router import QueryRouter, RouteDecision

# Import from new modules
from .constants import (
    LAYER_CONFIDENCE_THRESHOLD,
    MAX_HISTORY_MESSAGES,
    MAX_INPUT_LENGTH,
    REFERENCE_POOL_SIZE,
    EARLY_LESSON_MAX,
    EARLY_LESSON_MARGIN,
    TIMEFRAME_QUESTION,
)
from .state import ConversationState, _PreparedPrompt
from .inference import (
    infer_process_layer,
    pick_layer_question,
    infer_barrier,
    infer_activities,
    infer_time_available,
    SOURCE_REQUEST_PATTERNS,
    ACTION_SUGGESTION_PATTERNS,
)
from .detection.detectors import (
    detect_lowest_mpac,
    detect_general_disinterest,
    detect_emotion_regulation,
    detect_module_request,
    detect_lesson_lookup,
    detect_educational_use_case,
    detect_sources_only,
)

logger = logging.getLogger(__name__)


class CoachAgent:
    """Handles conversation state, prompting, and OpenAI calls."""

    def __init__(
        self,
        client: OpenAI,
        model: str,
        *,
        temperature: float = 0.8,
        top_p: float = 0.9,
        max_tokens: int = 600,
        retriever: Optional[RagRetriever] = None,
        router: Optional[QueryRouter] = None,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.state = ConversationState()
        self.history: List[Dict[str, str]] = []
        self.retriever = retriever
        self.router = router or QueryRouter()
        self.latest_retrieval: Optional[RetrievalResult] = None
        self.last_retrieval_with_results: Optional[RetrievalResult] = None

    def _validate_input(self, user_input: str) -> None:
        """
        Validate user input for security concerns.

        This performs basic sanity checks on user input:
        - Ensures input is not empty
        - Enforces maximum length to prevent memory exhaustion
        - Detects obvious prompt injection attempts (logged but not blocked)

        Args:
            user_input: User message text

        Raises:
            ValueError: If input fails validation
        """
        if not user_input or not user_input.strip():
            raise ValueError("Input cannot be empty")

        if len(user_input) > MAX_INPUT_LENGTH:
            logger.warning(f"Input too long: {len(user_input)} chars (max: {MAX_INPUT_LENGTH})")
            raise ValueError(f"Input too long. Maximum {MAX_INPUT_LENGTH} characters allowed.")

        # Basic prompt injection detection - compiled at function level for thread safety
        # These patterns detect attempts to manipulate the system prompt
        dangerous_patterns: List[Pattern] = [
            re.compile(r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|prompts?|commands?)", re.IGNORECASE),
            re.compile(r"disregard\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|prompts?)", re.IGNORECASE),
            re.compile(r"new\s+instructions?:", re.IGNORECASE),
            re.compile(r"system\s+prompt:", re.IGNORECASE),
            re.compile(r"you\s+are\s+now\s+(?:a|an)", re.IGNORECASE),
            re.compile(r"\[SYSTEM\]", re.IGNORECASE),
            re.compile(r"\[ADMIN\]", re.IGNORECASE),
        ]

        for pattern in dangerous_patterns:
            if pattern.search(user_input):
                logger.warning(f"Potential prompt injection detected: {pattern.pattern}")
                # Don't reject - just log and continue
                # The system prompt includes instructions to resist manipulation
                break

    def _truncate_history(self) -> None:
        """
        Truncate conversation history to prevent memory exhaustion.

        Keeps the most recent MAX_HISTORY_MESSAGES messages.
        """
        if len(self.history) > MAX_HISTORY_MESSAGES:
            messages_to_remove = len(self.history) - MAX_HISTORY_MESSAGES
            logger.info(f"Truncating history: removing {messages_to_remove} oldest messages")
            self.history = self.history[-MAX_HISTORY_MESSAGES:]

    def generate_response(self, user_input: str) -> str:
        # Validate input first
        self._validate_input(user_input)

        prepared = self._prepare_prompt(user_input)
        if prepared.override_citations:
            assistant_reply = prepared.override_text
            self._record_exchange(user_input, assistant_reply)
            return assistant_reply

        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            messages=prepared.messages,
        )
        assistant_reply = completion.choices[0].message.content.strip()
        assistant_reply = self._postprocess_response(
            assistant_reply,
            response_mode=prepared.response_mode,
            module_reference_sentence=prepared.module_reference_sentence,
        )
        assistant_reply = self._maybe_append_citations(assistant_reply, prepared)
        assistant_reply = self._replace_em_dash(assistant_reply)
        self._record_exchange(user_input, assistant_reply)
        return assistant_reply

    def stream_response(self, user_input: str) -> Generator[str, None, str]:
        # Validate input first
        self._validate_input(user_input)

        prepared = self._prepare_prompt(user_input)
        if prepared.override_citations:
            reply = prepared.override_text
            self._record_exchange(user_input, reply)
            yield reply
            return reply
        if prepared.response_mode in {"lowest_mpac", "emotion_education", "educational", "source_request"}:
            completion = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
                messages=prepared.messages,
            )
            assistant_reply = completion.choices[0].message.content.strip()
            assistant_reply = self._postprocess_response(
                assistant_reply,
                response_mode=prepared.response_mode,
                module_reference_sentence=prepared.module_reference_sentence,
            )
            assistant_reply = self._maybe_append_citations(assistant_reply, prepared)
            assistant_reply = self._replace_em_dash(assistant_reply)
            self._record_exchange(user_input, assistant_reply)
            yield assistant_reply
            return assistant_reply

        response_chunks: List[str] = []
        stream = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            messages=prepared.messages,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            text = delta.content or ""
            text = self._replace_em_dash(text)
            if not text:
                continue
            response_chunks.append(text)
            yield text

        assistant_reply = "".join(response_chunks).strip()
        final_reply = self._maybe_append_citations(assistant_reply, prepared)
        final_reply = self._replace_em_dash(final_reply)
        trailing = final_reply[len(assistant_reply) :]
        if trailing:
            yield self._replace_em_dash(trailing)
        self._record_exchange(user_input, final_reply)
        return final_reply

    def snapshot(self) -> Dict[str, str]:
        """Return a shallow snapshot of the coach state for monitoring."""

        mapping = self.state.to_prompt_mapping()
        mapping["history_length"] = str(len(self.history))
        return mapping

    def _prepare_prompt(self, user_input: str) -> _PreparedPrompt:
        self._update_state(user_input)
        context_block = None
        self.latest_retrieval = None
        routing_instruction: Optional[str] = None
        decision: Optional[RouteDecision] = None
        if self.retriever:
            decision = self.router.route(user_input)
            retrieval_result = self.retriever.gather_context(user_input, decision)
            context_block = retrieval_result.build_prompt_context() if retrieval_result else None
            self.latest_retrieval = retrieval_result
            if retrieval_result and (retrieval_result.master_chunks or retrieval_result.activity_chunks):
                self.last_retrieval_with_results = retrieval_result

        source_request = self._needs_citations(user_input)
        sources_only = detect_sources_only(user_input)
        lesson_lookup = detect_lesson_lookup(user_input)
        explicit_module_request = source_request or detect_module_request(user_input) or lesson_lookup
        general_disinterest = detect_general_disinterest(user_input)
        lowest_mpac = detect_lowest_mpac(user_input) or general_disinterest
        emotion_regulation = detect_emotion_regulation(user_input)
        educational_use_case = detect_educational_use_case(
            user_input,
            explicit_module_request=explicit_module_request,
            decision=decision,
        )

        # Response mode routing determines coaching approach based on user state
        # - lowest_mpac: Educational only, no action suggestions (unmotivated users)
        # - emotion_education: Educational support for negative feelings
        # - educational: Info-focused responses for explicit knowledge requests
        # - source_request: Concise response with citations
        # - default: Standard conversational coaching
        response_mode = "default"
        response_instruction: Optional[str] = None
        if lowest_mpac:
            response_mode = "lowest_mpac"
            response_instruction = (
                "Lowest-intention routing: provide educational support only. "
                "Do NOT suggest activities, action steps, or behavior change. Do not ask questions. "
                "Never use question marks. Output format: 1-3 sentences total, conversational, no bullet lists, no numbering, no bold. "
                "Sentence 1 should neutrally acknowledge the feeling or hesitation. Sentence 2 should explain health relevance in plain language. "
                "If a relevant slide is available, add one final sentence that points to at most two slides as module support."
            )
        elif emotion_regulation:
            response_mode = "emotion_education"
            response_instruction = (
                "Emotion-regulation routing: the user expresses negative feelings about activity. "
                "Provide educational support only, without action suggestions or questions. "
                "Never use question marks. Output format: 1-3 sentences total, conversational, no bullet lists, no numbering, no bold. "
                "Sentence 1-2 should summarize the key educational points in plain language. "
                "If a relevant slide is available, add one final sentence that references one slide as optional module support."
            )
        elif educational_use_case:
            response_mode = "educational"
            response_instruction = (
                "Educational routing: respond primarily with informational support grounded in relevant slides. "
                "Never use question marks. Output format: 1-3 sentences total, conversational, no bullet lists, no numbering, no bold. "
                "Sentence 1-2 should give a concise, plain-language summary. "
                "If a relevant slide is available, add one final sentence that references one slide as optional module support."
            )

        if source_request and response_mode == "default":
            response_mode = "source_request"
            response_instruction = (
                "Source-request routing: keep the response concise (1-2 sentences), conversational, "
                "no bullet lists, no numbering, no bold. Do not add source citations in the body; they will be appended."
            )

        if decision and decision.needs_location_clarification and response_mode == "default":
            routing_instruction = (
                "The user mentioned a location that wasn't recognized. Ask a single friendly question like "
                "\"Do you live near or feel comfortable traveling to downtown, James Bay, Oak Bay, Saanich, Fairfield, or somewhere else nearby?\""
            )

        allow_module_references = False
        max_refs = 0
        prefer_early_lessons = False
        if lowest_mpac:
            allow_module_references = True
            max_refs = 2
            prefer_early_lessons = True
        elif emotion_regulation:
            allow_module_references = True
            max_refs = 1
        elif explicit_module_request:
            allow_module_references = True
            max_refs = 1
        elif educational_use_case:
            allow_module_references = True
            max_refs = 1

        reference_source = self._select_reference_source(self.latest_retrieval)
        selected_chunks: List[RetrievedChunk] = []
        if allow_module_references:
            selected_chunks = self._select_reference_chunks(
                reference_source,
                max_refs=max_refs,
                prefer_early_lessons=prefer_early_lessons,
            )
        selected_references = self._format_reference_list(selected_chunks)
        module_reference_sentence = ""
        module_reference_instruction: Optional[str] = None
        if response_mode in {"lowest_mpac", "emotion_education", "educational"}:
            if response_mode == "lowest_mpac" and general_disinterest:
                module_reference_sentence = (
                    "You should check out Lesson 1: Why Physical Activity Matters During Retirement and "
                    "Lesson 2: The Power of Physical Activity."
                )
            else:
                module_reference_sentence = self._build_module_reference_sentence(
                    selected_references,
                    max_refs=max_refs,
                    tone="direct" if response_mode == "lowest_mpac" else "optional",
                )
            if module_reference_sentence:
                module_reference_instruction = (
                    "Do not mention module, lesson, or slide names in your response. "
                    "A module reference sentence will be appended."
                )
        if module_reference_instruction is None:
            module_reference_instruction = self._build_module_reference_instruction(
                selected_references,
                max_refs=max_refs,
                allow=allow_module_references,
            )

        override_citations = False
        override_text = ""
        reference_block_references: List[str] = []
        if lesson_lookup:
            override_text = self._build_lesson_lookup_response(selected_references)
            override_citations = True
        if source_request:
            source_chunks = self._select_reference_chunks(
                reference_source,
                max_refs=self._reference_pool_limit(reference_source),
                prefer_early_lessons=False,
                pool_limit=self._reference_pool_limit(reference_source),
            )
            reference_block_references = self._format_reference_list(source_chunks)
            if reference_block_references and sources_only:
                override_text = self._append_reference_block(
                    "",
                    reference_block_references,
                    max_refs=len(reference_block_references),
                )
                override_citations = True

        messages = self._build_messages(
            user_input,
            context_block if not override_citations else None,
            routing_instruction if not override_citations else None,
            response_mode=response_mode,
            response_instruction=response_instruction,
            module_reference_instruction=module_reference_instruction,
        )
        return _PreparedPrompt(
            messages=messages,
            needs_citations=source_request and response_mode in {"default", "source_request", "educational"},
            override_citations=override_citations,
            override_text=override_text,
            reference_block_references=reference_block_references,
            response_mode=response_mode,
            module_reference_sentence=module_reference_sentence,
        )

    def _maybe_append_citations(self, text: str, prepared: _PreparedPrompt) -> str:
        if not prepared.needs_citations:
            return text
        max_refs = len(prepared.reference_block_references)
        return self._append_reference_block(text, prepared.reference_block_references, max_refs=max_refs)

    def _record_exchange(self, user_input: str, assistant_reply: str) -> None:
        """
        Record conversation exchange and truncate history if needed.

        Args:
            user_input: User's message
            assistant_reply: Assistant's response
        """
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": assistant_reply})

        # Truncate history to prevent unbounded growth
        self._truncate_history()

    def _build_messages(
        self,
        user_input: str,
        context_block: Optional[str] = None,
        routing_instruction: Optional[str] = None,
        response_mode: str = "default",
        response_instruction: Optional[str] = None,
        module_reference_instruction: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        system_prompt = build_coach_prompt(self.state.to_prompt_mapping())
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if context_block:
            retrieval_instruction = self._build_retrieval_instruction(response_mode)
            messages.append({"role": "system", "content": f"{retrieval_instruction}\n\n{context_block}"})
        if response_instruction:
            messages.append({"role": "system", "content": response_instruction})
        if module_reference_instruction:
            messages.append({"role": "system", "content": module_reference_instruction})
        if routing_instruction:
            messages.append({"role": "system", "content": routing_instruction})
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        return messages

    def _build_retrieval_instruction(self, response_mode: str) -> str:
        if response_mode == "lowest_mpac":
            return (
                "You have access to retrieved slides/activities below. Use only slide content that directly "
                "addresses the user's question. Ignore local activities unless the user explicitly asked for them. "
                "If the content is not helpful, briefly say so before proceeding."
            )
        if response_mode in {"emotion_education", "educational"}:
            return (
                "You have access to retrieved slides/activities below. Use slide content when directly relevant "
                "for educational support. Ignore local activities unless the user explicitly asked for them. "
                "If the content is not helpful, briefly say so before proceeding."
            )
        return (
            "You have access to retrieved slides/activities below. When relevant, ground your answer in them. "
            "Respond in a conversational tone using a maximum of three sentences total; no bullet lists or numbered lists. "
            "If the retrieved context includes local activities, mention at least one concrete option by name (with location or schedule) before any reflective coaching. "
            "If the content is not helpful, briefly say so before proceeding without it."
        )

    def _select_reference_source(self, current: Optional[RetrievalResult]) -> Optional[RetrievalResult]:
        if current and current.master_chunks:
            return current
        if self.last_retrieval_with_results and self.last_retrieval_with_results.master_chunks:
            return self.last_retrieval_with_results
        return None

    def _select_reference_chunks(
        self,
        retrieval: Optional[RetrievalResult],
        *,
        max_refs: int,
        prefer_early_lessons: bool,
        pool_limit: int = REFERENCE_POOL_SIZE,
    ) -> List[RetrievedChunk]:
        """
        Select most relevant lesson chunks for citation.

        When prefer_early_lessons is True (for lowest-MPAC users), prioritizes
        foundational content (Lessons 1-2) over higher-ranked later lessons,
        unless the later lesson significantly outscores early content.
        """
        if not retrieval or not retrieval.master_chunks or max_refs <= 0:
            return []
        chunks = list(retrieval.master_chunks)
        score_values = [chunk.score for chunk in chunks if chunk.score is not None]
        use_scores = bool(score_values) and all(0.0 <= score <= 1.0 for score in score_values)
        if use_scores:
            ranked = sorted(chunks, key=lambda chunk: (chunk.score is None, -(chunk.score or 0.0)))
        else:
            ranked = chunks
        ranked = ranked[:pool_limit]
        if not ranked:
            return []
        pool = ranked
        if prefer_early_lessons:
            early = [chunk for chunk in pool if (chunk.metadata.get("lesson_number") or 0) <= EARLY_LESSON_MAX]
            if early:
                top_is_early = pool[0] in early
                if top_is_early:
                    pool = early
                else:
                    top = pool[0]
                    top_score = top.score
                    early_score = early[0].score
                    if top_score is None or early_score is None:
                        pool = pool
                    elif early_score >= top_score - EARLY_LESSON_MARGIN:
                        pool = early
                    else:
                        pool = pool

        return pool[:max_refs]

    @staticmethod
    def _format_reference_list(chunks: List[RetrievedChunk]) -> List[str]:
        references: List[str] = []
        seen = set()
        for chunk in chunks:
            ref = chunk.reference()
            if ref and ref not in seen:
                seen.add(ref)
                references.append(ref)
        return references

    @staticmethod
    def _reference_pool_limit(retrieval: Optional[RetrievalResult]) -> int:
        if retrieval and retrieval.master_chunks:
            return max(len(retrieval.master_chunks), REFERENCE_POOL_SIZE)
        return REFERENCE_POOL_SIZE

    @staticmethod
    def _build_module_reference_instruction(
        references: List[str],
        *,
        max_refs: int,
        allow: bool,
    ) -> str:
        if not allow or not references or max_refs <= 0:
            return (
                "Do not mention module, lesson, or slide names. Do not cite or reference the modules. "
                "Use any retrieved slide content only as background."
            )
        limited = references[:max_refs]
        refs_line = "; ".join(limited)
        return (
            f"If you include module references, keep it to one sentence and use at most {max_refs} from this list: {refs_line}. "
            "Mention that it's in the module (Lesson/Slide), and do not invent or repeat references."
        )

    @staticmethod
    def _build_module_reference_sentence(
        references: List[str],
        *,
        max_refs: int,
        tone: str = "optional",
    ) -> str:
        if not references or max_refs <= 0:
            return ""
        limited = references[:max_refs]
        refs_line = "; ".join(limited)
        if tone == "direct":
            return f"You should check out these module sections for more detail: {refs_line}."
        return f"You can find more detail in the module here: {refs_line}."

    @staticmethod
    def _build_lesson_lookup_response(references: List[str]) -> str:
        if references:
            refs_line = "; ".join(references)
            return f"You can find that in the module here: {refs_line}."
        return "I couldn't find a specific lesson on that in the Reframing Retirement module."

    @staticmethod
    def _strip_markdown(text: str) -> str:
        cleaned = text.replace("**", "").replace("__", "")
        cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
        return cleaned

    @staticmethod
    def _replace_em_dash(text: str) -> str:
        return text.replace("—", "-")

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        return re.split(r"(?<=[.!?])\s+", text.strip())

    def _postprocess_response(
        self,
        text: str,
        *,
        response_mode: str,
        module_reference_sentence: str,
    ) -> str:
        if response_mode not in {"lowest_mpac", "emotion_education", "educational", "source_request"}:
            return self._replace_em_dash(text)
        cleaned = self._replace_em_dash(self._strip_markdown(text))
        sentences = [sentence.strip() for sentence in self._split_sentences(cleaned) if sentence.strip()]
        sentences = [sentence for sentence in sentences if "?" not in sentence]
        if response_mode in {"lowest_mpac", "emotion_education", "educational"}:
            filtered: List[str] = []
            for sentence in sentences:
                lowered = sentence.lower()
                if any(re.search(pattern, lowered) for pattern in ACTION_SUGGESTION_PATTERNS):
                    continue
                filtered.append(sentence)
            sentences = filtered
        if response_mode == "source_request":
            max_content = 2
        else:
            max_content = 2 if module_reference_sentence else 3
        content = " ".join(sentences[:max_content]).strip()
        if module_reference_sentence:
            if content:
                return f"{content} {module_reference_sentence}".strip()
            return module_reference_sentence.strip()
        return content

    def _needs_citations(self, user_input: str) -> bool:
        return any(pattern.search(user_input) for pattern in SOURCE_REQUEST_PATTERNS)

    def _append_reference_block(self, base_text: str, references: List[str], max_refs: int = 1) -> str:
        limited = references[:max_refs]
        if limited:
            module_block = "\n".join(f"- {ref}" for ref in limited)
            return f"{base_text}\n\nFrom your modules, you can find more detail at:\n{module_block}"
        fallback_msg = (
            "I couldn't find a specific slide to cite for that. "
            "If you can share more detail about what you'd like to know, I can point to a specific lesson."
        )
        return f"{base_text}\n\n{fallback_msg}"

    @staticmethod
    def _filter_lesson_references(references: List[str]) -> List[str]:
        """Keep only lesson references for citation blocks."""

        return [reference for reference in references if reference.startswith("Lesson ")]

    def _update_state(self, user_input: str) -> None:
        layer_inference = infer_process_layer(user_input)
        barrier = infer_barrier(user_input)
        activities = infer_activities(user_input)
        time_available = infer_time_available(user_input)

        if layer_inference.layer and layer_inference.confidence >= LAYER_CONFIDENCE_THRESHOLD:
            self.state.process_layer = layer_inference.layer
            self.state.layer_confidence = layer_inference.confidence
            self.state.pending_layer_question = None
        else:
            if self.state.process_layer == "unclassified":
                self.state.layer_confidence = layer_inference.confidence
                self.state.pending_layer_question = pick_layer_question(layer_inference.signals)

        if layer_inference.signals.has_frequency and not layer_inference.signals.has_timeframe:
            if self.state.pending_layer_question is None:
                self.state.pending_layer_question = TIMEFRAME_QUESTION
        elif layer_inference.signals.has_timeframe and self.state.pending_layer_question == TIMEFRAME_QUESTION:
            self.state.pending_layer_question = None

        if barrier:
            self.state.barrier = barrier
        if activities:
            self.state.activities = activities
        if time_available:
            self.state.time_available = time_available
