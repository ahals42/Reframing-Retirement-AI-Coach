"""Tests for the stage inference helpers."""

import unittest

from main import (
    FREQUENCY_QUESTION,
    STAGE_CONFIDENCE_THRESHOLD,
    infer_stage,
    pick_clarifying_question,
)


class StageInferenceTests(unittest.TestCase):
    def test_early_stage_inferred_for_explicit_not_started(self) -> None:
        result = infer_stage("I keep meaning to walk but honestly haven't started yet.")
        self.assertEqual(result.stage, "early")
        self.assertGreaterEqual(result.confidence, STAGE_CONFIDENCE_THRESHOLD)

    def test_planning_stage_detected_for_specific_intent_without_action(self) -> None:
        text = "I'm going to start walking after dinner this week and need a plan to stick to it."
        result = infer_stage(text)
        self.assertEqual(result.stage, "planning")
        self.assertGreaterEqual(result.confidence, STAGE_CONFIDENCE_THRESHOLD)

    def test_action_stage_detected_with_recent_frequency(self) -> None:
        text = "I walked 3 times this week for about 20 minutes each."
        result = infer_stage(text)
        self.assertEqual(result.stage, "action")
        self.assertGreaterEqual(result.confidence, STAGE_CONFIDENCE_THRESHOLD)

    def test_maintenance_stage_detected_with_routine_and_timeframe(self) -> None:
        text = "I've been walking 4 times a week for months and it's part of my morning routine now."
        result = infer_stage(text)
        self.assertEqual(result.stage, "maintenance")
        self.assertGreaterEqual(result.confidence, STAGE_CONFIDENCE_THRESHOLD)

    def test_vague_statement_requests_clarifying_question(self) -> None:
        text = "I've just been super busy lately."
        result = infer_stage(text)
        self.assertIsNone(result.stage)
        self.assertLess(result.confidence, STAGE_CONFIDENCE_THRESHOLD)
        self.assertEqual(pick_clarifying_question(result.cues), FREQUENCY_QUESTION)


if __name__ == "__main__":
    unittest.main()
