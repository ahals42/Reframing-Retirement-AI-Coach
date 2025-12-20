"""Keyword-based routing logic for deciding which indexes to query."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

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
    "home": "online",
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


class QueryRouter:
    """Simple heuristic router for selecting between master vs. activity indexes."""

    def route(self, user_input: str) -> RouteDecision:
        lowered = user_input.lower()
        use_activities = any(keyword in lowered for keyword in ACTIVITY_KEYWORDS)

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

        for act_type, keywords in TYPE_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                activity_filters.activity_type = act_type
                use_activities = True
                break

        if not activity_filters.has_filters():
            activity_filters = None

        route = RouteDecision(
            use_master=True,
            use_activities=use_activities,
            activity_filters=activity_filters,
            needs_location_clarification=use_activities and not recognized_location,
        )

        return route
