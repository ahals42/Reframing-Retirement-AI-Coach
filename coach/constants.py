"""Constants, thresholds, keyword lists, and questions for the coach module."""

import os

# Security and performance thresholds
LAYER_CONFIDENCE_THRESHOLD = 0.7
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "100"))
MAX_INPUT_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "10000"))
STREAMING_TIMEOUT_SECONDS = int(os.getenv("STREAMING_TIMEOUT_SECONDS", "300"))  # 5 minutes

# Keyword lists for layer detection
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

# Clarifying questions for layer inference
FREQUENCY_QUESTION = "In the last 7 days, about how many days did you do any purposeful movement, even a short walk counts?"
ROUTINE_QUESTION = "Do you already have something you do most weeks, or are you still figuring out what could work?"
TIMEFRAME_QUESTION = "Has this been going on for a while (weeks/months), or is it something you're just starting to experiment with?"

# Reference selection constants
REFERENCE_MIN_SCORE = 0.68
REFERENCE_SCORE_MARGIN = 0.08
REFERENCE_POOL_SIZE = 5
EARLY_LESSON_MAX = 2
EARLY_LESSON_MARGIN = 0.08

# Known activity hub locations
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
