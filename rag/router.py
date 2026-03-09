"""Keyword-based routing logic for deciding which indexes to query."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

DAY_PATTERN = re.compile(
    r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Weekend|Weekends?)\b",
    flags=re.IGNORECASE,
)

ACTIVITY_KEYWORDS = [
    "class",
    "classes",
    "activity",
    "activities",
    "things to do",
    "something to do",
    "local",
    "near me",
    "community",
    "program",
    "resource",
    "resources",
    "activity list",
    "group",
    "club",
    "schedule",
    "where can i go",
    "something nearby",
    "in my area",
    "pickleball",
    "yoga",
    "pilates",
    "walk with others",
    "walking group",
    "kayak",
    "swim",
    "pool",
]

LOCATION_HINTS = {
    "crystal": "fernwood",
    "crystal pool": "fernwood",
    "fairfield": "fairfield",
    "fernwood": "fernwood",
    "downtown": "downtown",
    "victoria": "victoria",
    "oaklands": "oaklands",
    "oak bay": "oak bay",
    "uplands": "oak bay",
    "james bay": "james bay",
    "victoria west": "victoria west",
    "ocean river": "downtown",
    "saanich": "saanich",
    "cedar hill": "cedar hill",
    "online": "online",
}

HOME_KEYWORDS = [
    "at home",
    "at-home",
    "home workout",
    "home exercise",
    "home activity",
    "workout video",
    "exercise video",
    "fitness video",
    "youtube",
    "online workout video",
    "video workout",
    "from home",
    "in my house",
    "blog",
    "blogs",
    "playlist",
    "playlists",
    "video playlist",
    "video series",
    "individual video",
    "watch a workout",
    "watch a video",
    "home video",
    "home videos",
]

HOME_RESOURCE_TYPE_KEYWORDS: Dict[str, List[str]] = {
    "video": ["video", "watch", "youtube"],
    "playlist": ["playlist", "series", "collection"],
    "blog": ["blog", "article", "read", "reading"],
}

TYPE_KEYWORDS = {
    "yoga": ["yoga"],
    "walking": ["walk", "walking", "hike"],
    "pickleball": ["pickleball"],
    "dance": ["dance", "zumba"],
    "strength": ["strength", "weights", "resistance", "band", "pilates"],
    "aquatic": ["aqua", "pool", "swim"],
    "kayaking": ["kayak"],
}

SCIENCE_KEYWORDS = [
    "science",
    "evidence",
    "research",
    "studies",
    "mechanism",
    "data",
    "proof",
]

# Compiled once at import time — used in QueryRouter.route() on every message
_SCIENCE_RE = re.compile("|".join(re.escape(k) for k in SCIENCE_KEYWORDS), re.IGNORECASE)
_ACTIVITY_RE = re.compile("|".join(re.escape(k) for k in ACTIVITY_KEYWORDS), re.IGNORECASE)
_HOME_RE = re.compile("|".join(re.escape(k) for k in HOME_KEYWORDS), re.IGNORECASE)
_TYPE_RE: Dict[str, re.Pattern] = {
    act_type: re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    for act_type, keywords in TYPE_KEYWORDS.items()
}
_HOME_RESOURCE_RE: Dict[str, re.Pattern] = {
    res_type: re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    for res_type, keywords in HOME_RESOURCE_TYPE_KEYWORDS.items()
}


@dataclass
class ActivityFilters:
    cost_label: Optional[str] = None
    days: Optional[List[str]] = None
    location: Optional[str] = None
    activity_type: Optional[str] = None

    def has_filters(self) -> bool:
        return any([self.cost_label, self.days, self.location, self.activity_type])


@dataclass
class RouteDecision:
    use_master: bool = True
    use_activities: bool = False
    activity_filters: Optional[ActivityFilters] = None
    needs_location_clarification: bool = False
    prefer_science: bool = False
    use_home: bool = False
    home_resource_type: Optional[str] = None


class QueryRouter:
    """Simple heuristic router for selecting between master vs. activity indexes."""

    def route(self, user_input: str) -> RouteDecision:
        lowered = user_input.lower()
        prefer_science = bool(_SCIENCE_RE.search(lowered))

        # At-home detection takes priority over local activity routing
        if _HOME_RE.search(lowered):
            activity_filters = ActivityFilters()
            for act_type, pattern in _TYPE_RE.items():
                if pattern.search(lowered):
                    activity_filters.activity_type = act_type
                    break
            if not activity_filters.has_filters():
                activity_filters = None

            home_resource_type = None
            for res_type, pattern in _HOME_RESOURCE_RE.items():
                if pattern.search(lowered):
                    home_resource_type = res_type
                    break

            return RouteDecision(
                use_master=False,
                use_home=True,
                activity_filters=activity_filters,
                prefer_science=prefer_science,
                home_resource_type=home_resource_type,
            )

        use_activities = bool(_ACTIVITY_RE.search(lowered))
        activity_filters = ActivityFilters()

        recognized_location = False
        if "free" in lowered:
            activity_filters.cost_label = "free"

        day_matches = [match.group(1).capitalize() for match in DAY_PATTERN.finditer(user_input)]
        if day_matches:
            activity_filters.days = list(dict.fromkeys(day_matches))

        for hint, normalized in LOCATION_HINTS.items():
            if hint in lowered:
                activity_filters.location = normalized
                use_activities = True
                recognized_location = True
                break

        for act_type, pattern in _TYPE_RE.items():
            if pattern.search(lowered):
                activity_filters.activity_type = act_type
                use_activities = True
                break

        if not activity_filters.has_filters():
            activity_filters = None

        return RouteDecision(
            use_master=True,
            use_activities=use_activities,
            activity_filters=activity_filters,
            needs_location_clarification=use_activities and not recognized_location,
            prefer_science=prefer_science,
        )
