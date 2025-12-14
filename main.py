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

    mpac_stage: str = "unknown"
    barrier: str = "unknown"
    activities: str = "unknown"
    time_available: str = "unknown"

    def to_prompt_mapping(self) -> Dict[str, str]:
        return asdict(self)


def infer_stage(text: str) -> str | None:
    lowered = text.lower()
    if any(keyword in lowered for keyword in ("automatic", "habit", "keep it going", "consistent", "part of who i")):
        return "reflexive"
    if any(keyword in lowered for keyword in ("plan", "schedule", "follow through", "stick", "barrier", "forget", "routine")):
        return "regulatory"
    if any(keyword in lowered for keyword in ("should", "not sure", "maybe", "start", "starting", "thinking about", "unsure")):
        return "reflective"
    return None


def infer_barrier(text: str) -> str | None:
    lowered = text.lower()
    barrier_map = {
        "time pressure": ["busy", "no time", "schedule", "travel", "work"],
        "motivation dip": ["motivation", "don't feel", "lazy", "energy", "tired", "drained"],
        "weather": ["weather", "cold", "hot", "rain", "snow"],
        "pain or discomfort": ["pain", "ache", "sore", "injury", "hurt"],
        "confidence": ["nervous", "intimidated", "embarrassed"],
    }
    for label, keywords in barrier_map.items():
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


def infer_activities(text: str) -> str | None:
    lowered = text.lower()
    activity_map = {
        "walking": ["walk", "walking", "hike"],
        "light strength": ["strength", "weights", "dumbbell", "resistance", "band"],
        "mobility": ["stretch", "mobility", "yoga"],
        "cycling": ["bike", "cycling", "spin"],
        "swimming": ["swim", "pool"],
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
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.state = ConversationState()
        self.history: List[Dict[str, str]] = []

    def _update_state(self, user_input: str) -> None:
        stage = infer_stage(user_input)
        barrier = infer_barrier(user_input)
        activities = infer_activities(user_input)
        time_available = infer_time_available(user_input)

        if stage:
            self.state.mpac_stage = stage
        if barrier:
            self.state.barrier = barrier
        if activities:
            self.state.activities = activities
        if time_available:
            self.state.time_available = time_available

    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        system_prompt = build_coach_prompt(self.state.to_prompt_mapping())
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        return messages

    def generate_response(self, user_input: str) -> str:
        self._update_state(user_input)
        messages = self._build_messages(user_input)
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            messages=messages,
        )
        assistant_reply = completion.choices[0].message.content.strip()
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": assistant_reply})
        return assistant_reply


def main() -> None:
    load_dotenv()
    api_key = os.getenv("OPEN_API_KEY")
    if not api_key:
        raise ValueError("OPEN_API_KEY not found in environment variables")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    agent = CoachAgent(client=client, model=model)

    print("Physical-activity coach is ready. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            user_text = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_text:
            continue

        if user_text.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        try:
            response = agent.generate_response(user_text)
        except Exception as exc:  # Broad catch to keep CLI alive.
            print(f"[Error contacting coach model: {exc}]")
            continue

        print(f"Coach: {response}\n")


if __name__ == "__main__":
    main()
