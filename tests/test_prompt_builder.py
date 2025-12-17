"""Tests for the prompt builder state block:is a quick sanity check that the internal state we pass to the model (layer, confidence, barrier, etc.) actually shows up in the system prompt."""

import unittest

from prompts.prompt import build_coach_prompt


class PromptBuilderTests(unittest.TestCase):
    def test_prompt_includes_state_values(self) -> None:
        state = {
            "process_layer": "regulatory",
            "layer_confidence": 0.8234,
            "pending_layer_question": "In the last 7 days, about how many days did you do any purposeful movement, even a short walk counts?",
            "barrier": "time pressure",
            "activities": "walking",
            "time_available": "15 minutes",
        }
        prompt = build_coach_prompt(state)
        self.assertIn("Process layer: regulatory", prompt)
        self.assertIn("Layer confidence: 0.82", prompt)
        self.assertIn("Layer clarifying question: In the last 7 days", prompt)
        self.assertIn("Main barrier: time pressure", prompt)
        self.assertIn("Preferred activities: walking", prompt)
        self.assertIn("Time available today: 15 minutes", prompt)


if __name__ == "__main__":
    unittest.main()
