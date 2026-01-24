"""Pattern definitions and layer inference functions."""

import re
from typing import List, Pattern

from .detection.text_match import _contains_patterns, _contains_keywords
from .state import LayerSignals, LayerInference
from .constants import (
    ROUTINE_KEYWORDS,
    PLANNING_KEYWORDS,
    NOT_STARTED_KEYWORDS,
    AFFECTIVE_KEYWORDS,
    OPPORTUNITY_KEYWORDS,
    FREQUENCY_QUESTION,
    ROUTINE_QUESTION,
    TIMEFRAME_QUESTION,
)

# Compiled regex patterns for better performance
# These patterns detect behavioral signals and user intent

FREQUENCY_PATTERNS: List[Pattern] = [
    re.compile(r"\b\d+\s*(?:x|times?)\s*(?:each|per|a|this)?\s*(?:day|week|month)\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:days?)\s*(?:each|per|a)\s+week\b", re.IGNORECASE),
    re.compile(r"\b(?:daily|every day|each day|every morning|every evening)\b", re.IGNORECASE),
    re.compile(r"\b(?:once|twice|thrice)\s*(?:each|per|a|this|these|last)?\s*(?:week|day)\b", re.IGNORECASE),
    re.compile(r"\b(?:one|two|three|four|five|six|seven)\s+times?\s*(?:each|per|a|this|these|last)?\s*(?:week|day|month)\b", re.IGNORECASE),
]

TIMEFRAME_PATTERNS: List[Pattern] = [
    re.compile(r"\bfor\s+\d+\s+(?:weeks?|months?|years?)\b", re.IGNORECASE),
    re.compile(r"\bfor\s+(?:weeks|months|years)\b", re.IGNORECASE),
    re.compile(r"\bsince\s+\w+\b", re.IGNORECASE),
    re.compile(r"\bover\s+the\s+last\s+\d+\s+(?:weeks?|months?|years?)\b", re.IGNORECASE),
]

SOURCE_REQUEST_PATTERNS: List[Pattern] = [
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

# Patterns for detecting lowest M-PAC (unmotivated/disengaged language)
LOWEST_MPAC_STRONG_PATTERNS: List[Pattern] = [
    re.compile(r"\bwhy bother\b", re.IGNORECASE),
    re.compile(r"\bwhat'?s the point\b", re.IGNORECASE),
    re.compile(r"\bwhat'?s the use\b", re.IGNORECASE),
    re.compile(r"\bno point\b", re.IGNORECASE),
    re.compile(r"\bpointless\b", re.IGNORECASE),
    re.compile(r"\bnot worth (?:it|the effort)\b", re.IGNORECASE),
    re.compile(r"\btoo late for me\b", re.IGNORECASE),
]

LOWEST_MPAC_ACTIVITY_PATTERNS: List[Pattern] = [
    re.compile(r"\b(can't|cannot) be bothered\b.*\b(exercise|physical activity|being active|move|movement)\b", re.IGNORECASE),
    re.compile(r"\bno intention\b.*\b(exercise|physical activity|being active|move|movement)\b", re.IGNORECASE),
    re.compile(r"\bnot interested\b.*\b(exercise|physical activity|being active|move|movement)\b", re.IGNORECASE),
    re.compile(r"\b(don'?t|do not)\s+want\s+to\s+be\s+active\b", re.IGNORECASE),
    re.compile(r"\b(don'?t|do not)\s+want\s+to\s+exercise\b", re.IGNORECASE),
    re.compile(r"\b(don'?t|do not)\s+want\s+to\s+move\b", re.IGNORECASE),
    re.compile(r"\bnever going to\b.*\b(exercise|physical activity|being active|move|movement|start)\b", re.IGNORECASE),
    re.compile(r"\bwon't ever\b.*\b(exercise|physical activity|being active|move|movement|start)\b", re.IGNORECASE),
    re.compile(r"\bnot going to\b.*\b(exercise|physical activity|being active|move|movement|start)\b", re.IGNORECASE),
]

GENERAL_DISINTEREST_PATTERNS: List[Pattern] = [
    re.compile(r"\bi\s+don'?t\s+want\s+to\s+be\s+active\b", re.IGNORECASE),
    re.compile(r"\bi\s+don'?t\s+want\s+to\s+exercise\b", re.IGNORECASE),
    re.compile(r"\bi\s+don'?t\s+want\s+to\s+move\b", re.IGNORECASE),
    re.compile(r"\bnot\s+interested\s+in\s+being\s+active\b", re.IGNORECASE),
    re.compile(r"\bnot\s+interested\s+in\s+physical\s+activity\b", re.IGNORECASE),
    re.compile(r"\bnot\s+interested\s+in\s+exercise\b", re.IGNORECASE),
    re.compile(r"\bnever(?:ing)?\s+going\s+to\s+be\s+active\b", re.IGNORECASE),
    re.compile(r"\bwon'?t\s+ever\s+be\s+active\b", re.IGNORECASE),
    re.compile(r"\bwon'?t\s+ever\s+exercise\b", re.IGNORECASE),
    re.compile(r"\b(no\s+point|pointless|waste\s+of\s+time|not\s+worth\s+it|won'?t\s+help|nothing\s+will\s+change)\b", re.IGNORECASE),
    re.compile(r"\b(physical\s+active|physical\s+activity|being\s+active|exercise)\s+is\s+pointles\b", re.IGNORECASE),
    re.compile(r"\b(physical\s+activity|being\s+active|exercise)\s+seems\s+worthless\b", re.IGNORECASE),
    re.compile(r"\bpointles\s+to\s+(exercise|be\s+active|try)\b", re.IGNORECASE),
    re.compile(r"\bi\s+just\s+don'?t\s+have\s+it\s+in\s+me\b", re.IGNORECASE),
    re.compile(r"\bi'?m\s+done\s+trying\b", re.IGNORECASE),
    re.compile(r"\bi\s+can'?t\s+be\s+bothered\b", re.IGNORECASE),
    re.compile(r"\bi'?m\s+checked\s+out\b", re.IGNORECASE),
    re.compile(r"\btoo\s+old\s+to\s+(exercise|start)\b", re.IGNORECASE),
    re.compile(r"\bmy\s+body\s+can'?t\s+do\s+that\s+anymore\b", re.IGNORECASE),
    re.compile(r"\bthat\s+ship\s+has\s+sailed\b", re.IGNORECASE),
    re.compile(r"\bit'?s\s+too\s+late\s+for\s+me\b", re.IGNORECASE),
    re.compile(r"\bnothing\s+will\s+change\b", re.IGNORECASE),
    re.compile(r"\bit\s+won'?t\s+help\s+anyway\b", re.IGNORECASE),
    re.compile(r"\bi'?ll\s+never\s+stick\s+with\s+it\b", re.IGNORECASE),
    re.compile(r"\bi\s+always\s+quit\b", re.IGNORECASE),
    re.compile(r"\bi\s+can'?t\s+keep\s+it\s+up\b", re.IGNORECASE),
    re.compile(r"\b(worthless|useless)\s+(to|trying\s+to)?\s*(exercise|be\s+active)\b", re.IGNORECASE),
    re.compile(r"\bexercise\s+is\s+(useless|worthless)\b", re.IGNORECASE),
    re.compile(r"\b(waste|wasting)\s+of\s+time\b", re.IGNORECASE),
    re.compile(r"\bnot\s+worth\s+the\s+effort\b", re.IGNORECASE),
    re.compile(r"\bno\s+point\s+(in|to)\s+(exercise|being\s+active|trying)\b", re.IGNORECASE),
    re.compile(r"\bwhat'?s\s+the\s+point\s+of\s+(exercise|being\s+active)\b", re.IGNORECASE),
    re.compile(r"\bpointless\s+to\s+(exercise|try|be\s+active)\b", re.IGNORECASE),
    re.compile(r"\bit\s+won'?t\s+make\s+a\s+difference\b", re.IGNORECASE),
    re.compile(r"\bdoesn'?t\s+matter\s+if\s+i\s+exercise\b", re.IGNORECASE),
]

# Patterns for detecting educational queries and user intent
EDUCATIONAL_REQUEST_PATTERNS: List[Pattern] = [
    re.compile(r"\bwhy (?:is|does)\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bwhat is\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bbenefits?\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bhealth benefits?\b", re.IGNORECASE),
    re.compile(r"\bhow does\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bexplain\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bhelp me understand\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bwhat happens if\b.*\b(not active|inactive|sedentary)\b", re.IGNORECASE),
    re.compile(r"\bevidence\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bresearch\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\btell me about\b.*\b(physical activity|exercise|movement|being active)\b", re.IGNORECASE),
]

MODULE_REQUEST_PATTERNS: List[Pattern] = [
    re.compile(r"\bmodule\b", re.IGNORECASE),
    re.compile(r"\blesson\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bslide\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bwhat does (?:the )?module say\b", re.IGNORECASE),
    re.compile(r"\bwhat does (?:the )?lesson say\b", re.IGNORECASE),
    re.compile(r"\bwhat does (?:the )?slide say\b", re.IGNORECASE),
]

LESSON_LOOKUP_PATTERNS: List[Pattern] = [
    re.compile(r"\bwhich lesson\b", re.IGNORECASE),
    re.compile(r"\bwhat lesson\b", re.IGNORECASE),
    re.compile(r"\bwhere in (?:the )?module\b", re.IGNORECASE),
    re.compile(r"\bwhere in (?:the )?lesson\b", re.IGNORECASE),
]

# Patterns for detecting emotional regulation needs
EMOTION_STRONG_PATTERNS: List[Pattern] = [
    re.compile(r"\b(stress|stressed|stressful)\s+(about|around)\s+(exercise|activity|moving|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\b(anxious|anxiety)\s+(about|around)\s+(exercise|activity|moving|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bdread(?:ing)?\s+(exercise|activity|moving|movement|being active)\b", re.IGNORECASE),
    re.compile(r"\bfeel\s+(guilty|ashamed|embarrassed)\s+about\s+(exercise|activity|being active)\b", re.IGNORECASE),
    re.compile(r"\bexercise\s+makes\s+me\s+(anxious|stressed|guilty|ashamed|embarrassed)\b", re.IGNORECASE),
]

EMOTION_WEAK_PATTERNS: List[Pattern] = [
    re.compile(r"\b(stress|stressed|stressful)\b", re.IGNORECASE),
    re.compile(r"\banxious\b", re.IGNORECASE),
    re.compile(r"\banxiety\b", re.IGNORECASE),
    re.compile(r"\bdread\b", re.IGNORECASE),
    re.compile(r"\bguilty\b", re.IGNORECASE),
    re.compile(r"\bshame\b", re.IGNORECASE),
    re.compile(r"\bashamed\b", re.IGNORECASE),
    re.compile(r"\bfrustrated\b", re.IGNORECASE),
    re.compile(r"\bfrustration\b", re.IGNORECASE),
    re.compile(r"\boverwhelmed\b", re.IGNORECASE),
    re.compile(r"\bembarrassed\b", re.IGNORECASE),
    re.compile(r"\bself-conscious\b", re.IGNORECASE),
]

# Patterns for filtering action suggestions from educational responses
ACTION_SUGGESTION_PATTERNS: List[Pattern] = [
    re.compile(r"\btry\b", re.IGNORECASE),
    re.compile(r"\bstart (?:with|by)\b", re.IGNORECASE),
    re.compile(r"\bconsider\b", re.IGNORECASE),
    re.compile(r"\bexplore\b", re.IGNORECASE),
    re.compile(r"\bhow about\b", re.IGNORECASE),
    re.compile(r"\byou could\b", re.IGNORECASE),
    re.compile(r"\byou might\b", re.IGNORECASE),
    re.compile(r"\bwould you\b", re.IGNORECASE),
    re.compile(r"\bif you(?:'re| are)?\s+open\b", re.IGNORECASE),
    re.compile(r"\bif you want to\b", re.IGNORECASE),
    re.compile(r"\bfind movement\b", re.IGNORECASE),
    re.compile(r"\bif you ever\b", re.IGNORECASE),
    re.compile(r"\bif you decide to\b", re.IGNORECASE),
]


def infer_process_layer(text: str) -> LayerInference:
    """
    Infer which M-PAC layer (reflective, regulatory, reflexive) is most active.

    M-PAC is a motivational framework with three layers:
    - Reflexive: Automatic habits (frequency + routine language)
    - Regulatory: Planning/execution (frequency without routine)
    - Reflective: Thinking/considering (feelings, opportunities, planning)

    Returns inference with confidence score based on signal strength.
    """

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
    """Infer the user's primary barrier to physical activity."""
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
    """Infer which physical activities the user mentions."""
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
    """Infer how much time the user has available for activity."""
    match = re.search(r"(?:about|around)?\s*(\d{1,2})\s*(?:minutes?|mins?|min\.?|m)\b", text, flags=re.IGNORECASE)
    if match:
        minutes = match.group(1)
        return f"{minutes} minutes"
    if "half hour" in text.lower():
        return "30 minutes"
    return None
