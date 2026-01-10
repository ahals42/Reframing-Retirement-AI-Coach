"""Core conversational agent logic"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, Generator, List, Optional

from openai import OpenAI

from prompts.prompt import build_coach_prompt
from rag.retriever import RagRetriever, RetrievalResult, RetrievedChunk
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

LOWEST_MPAC_STRONG_PATTERNS = [
    r"\bwhy bother\b",
    r"\bwhat'?s the point\b",
    r"\bwhat'?s the use\b",
    r"\bno point\b",
    r"\bpointless\b",
    r"\bnot worth (?:it|the effort)\b",
    r"\btoo late for me\b",
]

LOWEST_MPAC_ACTIVITY_PATTERNS = [
    r"\b(can't|cannot) be bothered\b.*\b(exercise|physical activity|being active|move|movement)\b",
    r"\bno intention\b.*\b(exercise|physical activity|being active|move|movement)\b",
    r"\bnot interested\b.*\b(exercise|physical activity|being active|move|movement)\b",
    r"\b(don'?t|do not)\s+want\s+to\s+be\s+active\b",
    r"\b(don'?t|do not)\s+want\s+to\s+exercise\b",
    r"\b(don'?t|do not)\s+want\s+to\s+move\b",
    r"\bnever going to\b.*\b(exercise|physical activity|being active|move|movement|start)\b",
    r"\bwon't ever\b.*\b(exercise|physical activity|being active|move|movement|start)\b",
    r"\bnot going to\b.*\b(exercise|physical activity|being active|move|movement|start)\b",
]

GENERAL_DISINTEREST_PATTERNS = [
    r"\bi\s+don'?t\s+want\s+to\s+be\s+active\b",
    r"\bi\s+don'?t\s+want\s+to\s+exercise\b",
    r"\bi\s+don'?t\s+want\s+to\s+move\b",
    r"\bnot\s+interested\s+in\s+being\s+active\b",
    r"\bnot\s+interested\s+in\s+physical\s+activity\b",
    r"\bnot\s+interested\s+in\s+exercise\b",
    r"\bnever(?:ing)?\s+going\s+to\s+be\s+active\b",
    r"\bwon'?t\s+ever\s+be\s+active\b",
    r"\bwon'?t\s+ever\s+exercise\b",
    r"\bwon'?t\s+ever\s+be\s+active\b",
    r"\b(no\s+point|pointless|waste\s+of\s+time|not\s+worth\s+it|won'?t\s+help|nothing\s+will\s+change)\b",
    r"\b(physical\s+active|physical\s+activity|being\s+active|exercise)\s+is\s+pointles\b",
    r"\b(physical\s+activity|being\s+active|exercise)\s+seems\s+worthless\b",
    r"\bpointles\s+to\s+(exercise|be\s+active|try)\b",
    r"\bi\s+just\s+don'?t\s+have\s+it\s+in\s+me\b",
    r"\bi'?m\s+done\s+trying\b",
    r"\bi\s+can'?t\s+be\s+bothered\b",
    r"\bi'?m\s+checked\s+out\b",
    r"\btoo\s+old\s+to\s+(exercise|start)\b",
    r"\bmy\s+body\s+can'?t\s+do\s+that\s+anymore\b",
    r"\bthat\s+ship\s+has\s+sailed\b",
    r"\bit'?s\s+too\s+late\s+for\s+me\b",
    r"\bnothing\s+will\s+change\b",
    r"\bit\s+won'?t\s+help\s+anyway\b",
    r"\bi'?ll\s+never\s+stick\s+with\s+it\b",
    r"\bi\s+always\s+quit\b",
    r"\bi\s+can'?t\s+keep\s+it\s+up\b",
    r"\b(worthless|useless)\s+(to|trying\s+to)?\s*(exercise|be\s+active)\b",
    r"\bexercise\s+is\s+(useless|worthless)\b",
    r"\b(waste|wasting)\s+of\s+time\b",
    r"\bnot\s+worth\s+the\s+effort\b",
    r"\bno\s+point\s+(in|to)\s+(exercise|being\s+active|trying)\b",
    r"\bwhat'?s\s+the\s+point\s+of\s+(exercise|being\s+active)\b",
    r"\bpointless\s+to\s+(exercise|try|be\s+active)\b",
    r"\bit\s+won'?t\s+make\s+a\s+difference\b",
    r"\bdoesn'?t\s+matter\s+if\s+i\s+exercise\b",
]

ACTIVITY_CONTEXT_KEYWORDS = [
    "exercise",
    "physical activity",
    "activity",
    "move",
    "movement",
    "be active",
    "being active",
    "walk",
    "walking",
    "workout",
    "working out",
    "fitness",
]

EDUCATIONAL_REQUEST_PATTERNS = [
    r"\bwhy (?:is|does)\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\bwhat is\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\bbenefits?\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\bhealth benefits?\b",
    r"\bhow does\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\bexplain\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\bhelp me understand\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\bwhat happens if\b.*\b(not active|inactive|sedentary)\b",
    r"\bevidence\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\bresearch\b.*\b(physical activity|exercise|movement|being active)\b",
    r"\btell me about\b.*\b(physical activity|exercise|movement|being active)\b",
]

MODULE_REQUEST_PATTERNS = [
    r"\bmodule\b",
    r"\blesson\s+\d+\b",
    r"\bslide\s+\d+\b",
    r"\bwhat does (?:the )?module say\b",
    r"\bwhat does (?:the )?lesson say\b",
    r"\bwhat does (?:the )?slide say\b",
]

LESSON_LOOKUP_PATTERNS = [
    r"\bwhich lesson\b",
    r"\bwhat lesson\b",
    r"\bwhere in (?:the )?module\b",
    r"\bwhere in (?:the )?lesson\b",
]


EMOTION_STRONG_PATTERNS = [
    r"\b(stress|stressed|stressful)\s+(about|around)\s+(exercise|activity|moving|movement|being active)\b",
    r"\b(anxious|anxiety)\s+(about|around)\s+(exercise|activity|moving|movement|being active)\b",
    r"\bdread(?:ing)?\s+(exercise|activity|moving|movement|being active)\b",
    r"\bfeel\s+(guilty|ashamed|embarrassed)\s+about\s+(exercise|activity|being active)\b",
    r"\bexercise\s+makes\s+me\s+(anxious|stressed|guilty|ashamed|embarrassed)\b",
]

EMOTION_WEAK_PATTERNS = [
    r"\b(stress|stressed|stressful)\b",
    r"\banxious\b",
    r"\banxiety\b",
    r"\bdread\b",
    r"\bguilty\b",
    r"\bshame\b",
    r"\bashamed\b",
    r"\bfrustrated\b",
    r"\bfrustration\b",
    r"\boverwhelmed\b",
    r"\bembarrassed\b",
    r"\bself-conscious\b",
]

ACTION_SUGGESTION_PATTERNS = [
    r"\btry\b",
    r"\bstart (?:with|by)\b",
    r"\bconsider\b",
    r"\bexplore\b",
    r"\bhow about\b",
    r"\byou could\b",
    r"\byou might\b",
    r"\bwould you\b",
    r"\bif you(?:'re| are)?\s+open\b",
    r"\bif you want to\b",
    r"\bfind movement\b",
    r"\bif you ever\b",
    r"\bif you decide to\b",
]

REFERENCE_MIN_SCORE = 0.68
REFERENCE_SCORE_MARGIN = 0.08
REFERENCE_POOL_SIZE = 5
EARLY_LESSON_MAX = 2
EARLY_LESSON_MARGIN = 0.08

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


def detect_lowest_mpac(text: str) -> bool:
    lowered = text.lower()
    if _contains_patterns(lowered, LOWEST_MPAC_STRONG_PATTERNS):
        return True
    if _contains_patterns(lowered, LOWEST_MPAC_ACTIVITY_PATTERNS):
        return True
    return False


def detect_general_disinterest(text: str) -> bool:
    lowered = text.lower()
    if "?" in lowered:
        return False
    return _contains_patterns(lowered, GENERAL_DISINTEREST_PATTERNS)


def detect_emotion_regulation(text: str) -> bool:
    lowered = text.lower()
    if _contains_patterns(lowered, EMOTION_STRONG_PATTERNS):
        return True
    if _contains_patterns(lowered, EMOTION_WEAK_PATTERNS) and _contains_keywords(lowered, ACTIVITY_CONTEXT_KEYWORDS):
        return True
    return False


def detect_module_request(text: str) -> bool:
    lowered = text.lower()
    return _contains_patterns(lowered, MODULE_REQUEST_PATTERNS)


def detect_lesson_lookup(text: str) -> bool:
    lowered = text.lower()
    return _contains_patterns(lowered, LESSON_LOOKUP_PATTERNS)


def detect_educational_use_case(text: str, *, explicit_module_request: bool, decision: Optional[RouteDecision]) -> bool:
    if explicit_module_request:
        return True
    if decision and decision.use_activities:
        return False
    lowered = text.lower()
    return _contains_patterns(lowered, EDUCATIONAL_REQUEST_PATTERNS)


def detect_sources_only(text: str) -> bool:
    lowered = text.lower()
    if not any(pattern.search(lowered) for pattern in SOURCE_REQUEST_PATTERNS):
        return False
    cleaned = lowered
    for pattern in SOURCE_REQUEST_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned).strip()
    return len(cleaned.split()) <= 2


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
    reference_block_references: List[str]
    response_mode: str
    module_reference_sentence: str


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
            needs_citations=source_request and response_mode in {"default", "source_request"},
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
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": assistant_reply})

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
