"""Core conversational agent logic shared by CLI and API layers."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, Generator, List, Optional

from openai import OpenAI

from prompts.prompt import build_coach_prompt
from rag.retriever import RagRetriever, RetrievalResult
from rag.router import QueryRouter, RouteDecision

LAYER_CONFIDENCE_THRESHOLD = 0.7


@dataclass
class LayerSignals:
    """Stores detected cues that hint at reflective/regulatory/reflexive focus."""

    has_frequency: bool = False
    has_timeframe: bool = False
    has_routine_language: bool = False
    has_planning_language: bool = False
    has_not_started_language: bool = False
    has_affective_language: bool = False
    has_opportunity_language: bool = False
    has_progressive_statement: bool = False

    @property
    def behavior_evidence(self) -> bool:
        return (
            self.has_frequency
            or self.has_timeframe
            or self.has_routine_language
            or self.has_progressive_statement
        )


@dataclass
class LayerInference:
    """Represents the inferred process layer and supporting metadata."""

    layer: str | None
    confidence: float
    signals: LayerSignals


@dataclass
class ConversationState:
    """Tracks inferred user context for prompt conditioning."""

    process_layer: str = "unclassified"
    layer_confidence: float = 0.0
    pending_layer_question: str | None = None
    barrier: str = "unknown"
    activities: str = "unknown"
    time_available: str = "unknown"

    def to_prompt_mapping(self) -> Dict[str, str]:
        return asdict(self)


FREQUENCY_PATTERNS = [
    r"\b\d+\s*(?:x|times?)\s*(?:each|per|a|this)?\s*(?:day|week|month)\b",
    r"\b\d+\s*(?:days?)\s*(?:each|per|a)\s+week\b",
    r"\b(?:daily|every day|each day|every morning|every evening)\b",
    r"\b(?:once|twice|thrice)\s*(?:each|per|a|this|these|last)?\s*(?:week|day)\b",
    r"\b(?:one|two|three|four|five|six|seven)\s+times?\s*(?:each|per|a|this|these|last)?\s*(?:week|day|month)\b",
]

TIMEFRAME_PATTERNS = [
    r"\bfor\s+\d+\s+(?:weeks?|months?|years?)\b",
    r"\bfor\s+(?:weeks|months|years)\b",
    r"\bsince\s+\w+\b",
    r"\bover\s+the\s+last\s+\d+\s+(?:weeks?|months?|years?)\b",
]

ROUTINE_KEYWORDS = [
    "part of my routine",
    "part of my day",
    "part of my morning",
    "part of my evening",
    "part of my life",
    "it's a habit",
    "its a habit",
    "habit now",
    "have a habit",
    "on autopilot",
    "automatic",
    "just what i do",
    "built into my day",
    "keep it going",
    "most days",
    "almost every day",
    "part of my week",
    "since i retired",
    "what i usually do",
    "second nature",
]

PLANNING_KEYWORDS = [
    "i'm going to",
    "i am going to",
    "going to start",
    "plan to",
    "planning to",
    "need a plan",
    "need to plan",
    "after dinner",
    "before breakfast",
    "schedule",
    "set a reminder",
    "reminder",
    "implementation",
    "i'm thinking about",
    "trying to get back into",
    "want to start again",
    "thinking of starting",
    "working up to",
    "ease into",
    "build up slowly",
    "after breakfast",
    "mid-morning",
]

NOT_STARTED_KEYWORDS = [
    "haven't started",
    "have not started",
    "haven't really",
    "not really",
    "keep meaning to",
    "haven't gotten around",
    "never start",
    "never really",
    "i should",
    "should probably",
    "maybe i will",
    "not sure i can",
    "fell out of the habit",
    "got out of the routine",
    "haven't been consistent",
    "on and off",
    "hard to get going",
    "not sure where to start",
]

AFFECTIVE_KEYWORDS = [
    "enjoy",
    "enjoyed",
    "like",
    "like it",
    "love",
    "love it",
    "fun",
    "feel good",
    "feel better",
    "feel calm",
    "calm",
    "energized",
    "energising",
    "energizing",
    "refreshing",
    "relaxing",
    "rewarding",
    "happy",
    "happiness",
    "stress relief",
    "stress reduction",
    "less stiff",
    "feel looser",
    "helps my joints",
    "helps my balance",
    "clears my head",
    "helps me sleep",
    "feel independent",
    "keeps me moving",
]

OPPORTUNITY_KEYWORDS = [
    "chance",
    "opportunity",
    "easy to get to",
    "access",
    "nearby",
    "close by",
    "paths",
    "trail",
    "safe place",
    "good weather",
    "daylight",
    "warm",
    "sunny",
    "not cold",
    "community centre",
    "rec centre",
    "indoor",
    "snow",
    "icy",
    "winter",
    "weather",
]

FREQUENCY_QUESTION = "In the last 7 days, about how many days did you do any purposeful movement, even a short walk counts?"
ROUTINE_QUESTION = "Do you already have something you do most weeks, or are you still figuring out what could work?"
TIMEFRAME_QUESTION = "Has this been going on for a while (weeks/months), or is it something you're just starting to experiment with?"

SOURCE_REQUEST_PATTERNS = [
    re.compile(r"\bsource(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\breference(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bcitation(s)?\b", flags=re.IGNORECASE),
    re.compile(r"where did that come from", flags=re.IGNORECASE),
    re.compile(r"show sources?", flags=re.IGNORECASE),
    re.compile(r"where can i read more", flags=re.IGNORECASE),
    re.compile(r"where can i find this", flags=re.IGNORECASE),
    re.compile(r"where in my app", flags=re.IGNORECASE),
    re.compile(r"show me where", flags=re.IGNORECASE),
]

KNOWN_ACTIVITY_HUBS = [
    "Fernwood / Crystal Pool",
    "Fairfield Gonzales",
    "James Bay",
    "Downtown Victoria",
    "Saanich (G.R. Pearkes or Commonwealth Place)",
    "Cedar Hill Recreation Centre",
    "Oaklands",
    "Oak Bay Recreation Centre / Uplands",
    "Victoria West",
    "Online / at home",
]


def _contains_patterns(text: str, patterns: List[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _contains_keywords(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def infer_process_layer(text: str) -> LayerInference:
    """Infer which M-PAC layer (reflective, regulatory, reflexive) is most active."""

    lowered = text.lower()
    signals = LayerSignals(
        has_frequency=_contains_patterns(lowered, FREQUENCY_PATTERNS),
        has_timeframe=_contains_patterns(lowered, TIMEFRAME_PATTERNS),
        has_routine_language=_contains_keywords(lowered, ROUTINE_KEYWORDS),
        has_planning_language=_contains_keywords(lowered, PLANNING_KEYWORDS),
        has_not_started_language=_contains_keywords(lowered, NOT_STARTED_KEYWORDS),
        has_affective_language=_contains_keywords(lowered, AFFECTIVE_KEYWORDS),
        has_opportunity_language=_contains_keywords(lowered, OPPORTUNITY_KEYWORDS),
        has_progressive_statement=bool(re.search(r"\bbeen\s+\w+ing\b", lowered)),
    )

    layer: str | None = None
    has_progressive_habit = signals.has_progressive_statement and signals.has_timeframe
    has_habit_pair = (signals.has_routine_language or has_progressive_habit) and (
        signals.has_frequency or signals.has_timeframe
    )
    has_regular_frequency_over_time = signals.has_frequency and signals.has_timeframe
    expresses_feelings_or_opportunity = signals.has_affective_language or signals.has_opportunity_language
    has_behavior_signals = signals.behavior_evidence

    if has_habit_pair or has_regular_frequency_over_time:
        layer = "reflexive"
    elif expresses_feelings_or_opportunity:
        layer = "ongoing_reflective"
    elif signals.has_frequency or signals.has_timeframe:
        layer = "regulatory"
    elif signals.has_planning_language or signals.has_not_started_language:
        layer = "initiating_reflective"
    elif not has_behavior_signals:
        layer = None

    confidence = 0.0
    if layer == "reflexive":
        confidence = 0.55
        if signals.has_frequency:
            confidence += 0.15
        if signals.has_timeframe:
            confidence += 0.15
        if signals.has_routine_language:
            confidence += 0.1
    elif layer == "regulatory":
        confidence = 0.5
        if signals.has_frequency:
            confidence += 0.25
        if signals.has_timeframe:
            confidence += 0.1
        if signals.has_routine_language:
            confidence += 0.05
    elif layer == "ongoing_reflective":
        confidence = 0.45
        if signals.has_affective_language:
            confidence += 0.25
        if signals.has_opportunity_language:
            confidence += 0.2
        if signals.behavior_evidence:
            confidence += 0.1
    elif layer == "initiating_reflective":
        confidence = 0.45
        if signals.has_planning_language:
            confidence += 0.25
        if signals.has_not_started_language:
            confidence += 0.25
        if not signals.behavior_evidence:
            confidence += 0.1

    confidence = min(confidence, 0.95)
    return LayerInference(layer=layer, confidence=confidence, signals=signals)


def pick_layer_question(signals: LayerSignals) -> str | None:
    """Return the best clarifying question based on missing supportive cues."""

    if not signals.behavior_evidence:
        return FREQUENCY_QUESTION
    if signals.has_frequency and not signals.has_routine_language:
        return ROUTINE_QUESTION
    if signals.has_frequency and not signals.has_timeframe:
        return TIMEFRAME_QUESTION
    if signals.has_timeframe and not signals.has_frequency:
        return FREQUENCY_QUESTION
    return None


def infer_barrier(text: str) -> str | None:
    lowered = text.lower()
    barrier_map = {
        "time pressure": [
            "busy",
            "no time",
            "schedule",
            "travel",
            "work",
            "appointments",
            "errands",
            "looking after",
            "caregiving",
            "day gets away",
        ],
        "motivation dip": [
            "motivation",
            "don't feel",
            "lazy",
            "energy",
            "tired",
            "drained",
            "low energy",
            "worn out",
            "hard to get going",
            "no drive",
            "can't get motivated",
        ],
        "weather": [
            "weather",
            "cold",
            "hot",
            "rain",
            "snow",
            "winter",
            "icy",
            "slippery",
            "too hot",
            "too cold",
        ],
        "pain or discomfort": [
            "pain",
            "ache",
            "sore",
            "injury",
            "hurt",
            "stiff",
            "stiffness",
            "joint pain",
            "back pain",
            "knee pain",
        ],
        "confidence": [
            "nervous",
            "intimidated",
            "embarrassed",
            "worried",
            "afraid",
            "fear of falling",
            "not confident",
        ],
    }
    for label, keywords in barrier_map.items():
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


def infer_activities(text: str) -> str | None:
    lowered = text.lower()
    activity_map = {
        "walking": [
            "walk",
            "walking",
            "hike",
            "go for a walk",
            "walking outside",
            "walking group",
            "group walk",
            "walking club",
        ],
        "light strength": [
            "strength",
            "weights",
            "dumbbell",
            "resistance",
            "band",
            "strength training",
            "bodyweight",
            "light weights",
        ],
        "mobility": [
            "stretch",
            "stretching",
            "mobility",
            "yoga",
            "range of motion",
            "flexibility",
            "tai chi",
            "taichi",
        ],
        "cycling": [
            "bike",
            "cycling",
            "spin",
            "stationary bike",
            "exercise bike",
        ],
        "swimming": [
            "swim",
            "swimming",
            "pool",
            "water",
            "aquafit",
            "water aerobics",
            "aqua fitness",
        ],
        "golf": [
            "golf",
            "golfing",
            "driving range",
        ],
        "pickleball": [
            "pickleball",
        ],
    }
    found: List[str] = []
    for label, keywords in activity_map.items():
        if any(keyword in lowered for keyword in keywords):
            found.append(label)
    if found:
        return ", ".join(dict.fromkeys(found))
    return None


def infer_time_available(text: str) -> str | None:
    match = re.search(r"(?:about|around)?\s*(\d{1,2})\s*(?:minutes?|mins?|min\.?|m)\b", text, flags=re.IGNORECASE)
    if match:
        minutes = match.group(1)
        return f"{minutes} minutes"
    if "half hour" in text.lower():
        return "30 minutes"
    return None


@dataclass
class _PreparedPrompt:
    messages: List[Dict[str, str]]
    needs_citations: bool
    override_citations: bool
    override_text: str
    references_source: Optional[RetrievalResult]


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

    def generate_response(self, user_input: str) -> str:
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
        assistant_reply = self._maybe_append_citations(assistant_reply, prepared)
        self._record_exchange(user_input, assistant_reply)
        return assistant_reply

    def stream_response(self, user_input: str) -> Generator[str, None, str]:
        prepared = self._prepare_prompt(user_input)
        if prepared.override_citations:
            reply = prepared.override_text
            self._record_exchange(user_input, reply)
            yield reply
            return reply

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
            if not text:
                continue
            response_chunks.append(text)
            yield text

        assistant_reply = "".join(response_chunks).strip()
        final_reply = self._maybe_append_citations(assistant_reply, prepared)
        trailing = final_reply[len(assistant_reply) :]
        if trailing:
            yield trailing
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
        if self.retriever:
            decision: RouteDecision = self.router.route(user_input)
            retrieval_result = self.retriever.gather_context(user_input, decision)
            context_block = retrieval_result.build_prompt_context() if retrieval_result else None
            self.latest_retrieval = retrieval_result
            if retrieval_result and (retrieval_result.master_chunks or retrieval_result.activity_chunks):
                self.last_retrieval_with_results = retrieval_result
            if decision.needs_location_clarification:
                routing_instruction = (
                    "The user mentioned a location that wasn't recognized. Ask a single friendly question like "
                    "\"Do you live near or feel comfortable traveling to downtown, James Bay, Oak Bay, Saanich, Fairfield, or somewhere else nearby?\""
                )

        needs_citations = self._needs_citations(user_input)
        override_citations = False
        override_text = ""
        if needs_citations and self.last_retrieval_with_results:
            references = self._filter_lesson_references(self.last_retrieval_with_results.references())
            if references:
                override_text = self._append_reference_block("", references)
                override_citations = True

        references_source: Optional[RetrievalResult] = None
        if needs_citations:
            if self.latest_retrieval and (
                self.latest_retrieval.master_chunks or self.latest_retrieval.activity_chunks
            ):
                references_source = self.latest_retrieval
            elif self.last_retrieval_with_results:
                references_source = self.last_retrieval_with_results

        messages = self._build_messages(
            user_input,
            context_block if not override_citations else None,
            routing_instruction if not override_citations else None,
        )
        return _PreparedPrompt(
            messages=messages,
            needs_citations=needs_citations,
            override_citations=override_citations,
            override_text=override_text,
            references_source=references_source,
        )

    def _maybe_append_citations(self, text: str, prepared: _PreparedPrompt) -> str:
        if not prepared.needs_citations:
            return text
        references = []
        if prepared.references_source:
            references = self._filter_lesson_references(prepared.references_source.references())
        return self._append_reference_block(text, references)

    def _record_exchange(self, user_input: str, assistant_reply: str) -> None:
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": assistant_reply})

    def _build_messages(
        self,
        user_input: str,
        context_block: Optional[str] = None,
        routing_instruction: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        system_prompt = build_coach_prompt(self.state.to_prompt_mapping())
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if context_block:
            retrieval_instruction = (
                "You have access to retrieved slides/activities below. When relevant, ground your answer in them. "
                "Respond in a conversational tone using a maximum of three sentences total—no bullet lists or numbered lists. "
                "If the retrieved context includes local activities, mention at least one concrete option by name (with location or schedule) before any reflective coaching. "
                "If the content is not helpful, briefly say so before proceeding without it."
            )
            messages.append({"role": "system", "content": f"{retrieval_instruction}\n\n{context_block}"})
        if routing_instruction:
            messages.append({"role": "system", "content": routing_instruction})
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        return messages

    def _needs_citations(self, user_input: str) -> bool:
        return any(pattern.search(user_input) for pattern in SOURCE_REQUEST_PATTERNS)

    def _append_reference_block(self, base_text: str, references: List[str]) -> str:
        if references:
            module_block = "\n".join(f"- {ref}" for ref in references)
            return f"{base_text}\n\nFrom your modules, you can find more detail at:\n{module_block}"
        fallback_msg = (
            "I couldn’t find a specific slide to cite. "
            "If you can share more detail about what you’d like to know, I can point to a specific lesson. "
            "In the meantime, feel free to elaborate and I’ll look for something relevant."
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


def run_rag_sanity_check(retriever: RagRetriever) -> None:
    """Query the master index once to confirm retrieval is working."""

    try:
        chunks = retriever.retrieve_master("What is physical activity?", top_k=1)
    except Exception as exc:
        print(f"[RAG check] Failed to query master index: {exc}")
        return

    if not chunks:
        print("[RAG check] No slides returned for sanity query.")
        return

    print(f"[RAG check] Top slide for 'What is physical activity?': {chunks[0].label()}")
