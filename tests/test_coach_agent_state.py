"""Tests for CoachAgent state updates:makes sure the agent's state flips to the right layer when someone gives clear info, and falls back to a clarifying question when they're vague."""

import unittest

from coach import CoachAgent, LAYER_CONFIDENCE_THRESHOLD
from coach.constants import FREQUENCY_QUESTION, TIMEFRAME_QUESTION


class DummyClient:
    """Minimal stub for OpenAI client used in tests."""

    pass


class CoachAgentStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = CoachAgent(client=DummyClient(), model="test-model")

    def test_update_state_sets_layer_when_confident(self) -> None:
        self.agent._update_state("I walked 3 times this week for about 20 minutes.")
        self.assertEqual(self.agent.state.process_layer, "regulatory")
        self.assertGreaterEqual(self.agent.state.layer_confidence, LAYER_CONFIDENCE_THRESHOLD)
        self.assertEqual(self.agent.state.pending_layer_question, TIMEFRAME_QUESTION)

    def test_update_state_sets_pending_question_when_uncertain(self) -> None:
        self.agent._update_state("I've just been super busy lately.")
        self.assertEqual(self.agent.state.process_layer, "unclassified")
        self.assertLess(self.agent.state.layer_confidence, LAYER_CONFIDENCE_THRESHOLD)
        self.assertEqual(self.agent.state.pending_layer_question, FREQUENCY_QUESTION)

    def test_pending_question_clears_after_confident_input(self) -> None:
        self.agent._update_state("I've just been super busy lately.")
        self.assertIsNotNone(self.agent.state.pending_layer_question)
        self.agent._update_state("I've been running for years, part of my morning routine.")
        self.assertEqual(self.agent.state.process_layer, "reflexive")
        self.assertIsNone(self.agent.state.pending_layer_question)

    def test_timeframe_question_triggers_even_when_layer_set(self) -> None:
        self.agent._update_state("I walk 3 times a week.")
        self.assertEqual(self.agent.state.process_layer, "regulatory")
        self.assertEqual(self.agent.state.pending_layer_question, TIMEFRAME_QUESTION)

    def test_timeframe_question_clears_after_duration_shared(self) -> None:
        self.agent._update_state("I walk 3 times a week.")
        self.agent._update_state("I've kept those walks going for months now.")
        self.assertIsNone(self.agent.state.pending_layer_question)


if __name__ == "__main__":
    unittest.main()
