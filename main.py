"""CLI entry point for the physical-activity conversational agent."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, asdict
from typing import Dict, List

from openai import OpenAI
from dotenv import load_dotenv

from prompts.prompt import build_coach_prompt


@dataclass
class ConversationState:
    """Tracks inferred user context for prompt conditioning."""

