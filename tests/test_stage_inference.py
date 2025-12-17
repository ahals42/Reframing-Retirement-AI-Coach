"""Tests for the process-layer inference helpers and follow-up questions."""

import unittest

from main import (
    FREQUENCY_QUESTION,
    LAYER_CONFIDENCE_THRESHOLD,
    ROUTINE_QUESTION,
    TIMEFRAME_QUESTION,
    LayerSignals,
    infer_process_layer,
    pick_layer_question,
)


class ProcessLayerInferenceTests(unittest.TestCase):
    def test_reflective_layer_detected_for_not_started_language(self) -> None:
        result = infer_process_layer("I keep meaning to walk but honestly haven't started yet.")
        self.assertEqual(result.layer, "initiating_reflective")
        self.assertGreaterEqual(result.confidence, LAYER_CONFIDENCE_THRESHOLD)

    def test_reflective_layer_detected_for_intent_without_behavior(self) -> None:
        text = "I'm going to start walking after dinner this week and need a plan to stick to it."
        result = infer_process_layer(text)
        self.assertEqual(result.layer, "initiating_reflective")
        self.assertGreaterEqual(result.confidence, LAYER_CONFIDENCE_THRESHOLD)

    def test_regulatory_layer_detected_with_recent_frequency(self) -> None:
        text = "I walked 3 times this week for about 20 minutes each."
        result = infer_process_layer(text)
        self.assertEqual(result.layer, "regulatory")
        self.assertGreaterEqual(result.confidence, LAYER_CONFIDENCE_THRESHOLD)

    def test_regulatory_layer_detected_with_spelled_frequency(self) -> None:
        text = "I walked twice this week."
        result = infer_process_layer(text)
        self.assertEqual(result.layer, "regulatory")
        self.assertGreaterEqual(result.confidence, LAYER_CONFIDENCE_THRESHOLD)

    def test_reflexive_layer_detected_with_routine_and_timeframe(self) -> None:
        text = "I've been walking 4 times a week for months and it's part of my morning routine now."
        result = infer_process_layer(text)
        self.assertEqual(result.layer, "reflexive")
        self.assertGreaterEqual(result.confidence, LAYER_CONFIDENCE_THRESHOLD)

    def test_reflexive_layer_detected_with_progressive_statement(self) -> None:
        text = "I've been running for years but recently tweaked my knee."
        result = infer_process_layer(text)
        self.assertEqual(result.layer, "reflexive")
        self.assertGreaterEqual(result.confidence, LAYER_CONFIDENCE_THRESHOLD)

    def test_ongoing_reflective_detected_with_affective_language(self) -> None:
        text = "I love how calm I feel after short walks and take them whenever I get the chance."
        result = infer_process_layer(text)
        self.assertEqual(result.layer, "ongoing_reflective")
        self.assertGreaterEqual(result.confidence, LAYER_CONFIDENCE_THRESHOLD)

    def test_vague_statement_requests_clarifying_question(self) -> None:
        text = "I've just been super busy lately."
        result = infer_process_layer(text)
        self.assertIsNone(result.layer)
        self.assertLess(result.confidence, LAYER_CONFIDENCE_THRESHOLD)
        self.assertEqual(pick_layer_question(result.signals), FREQUENCY_QUESTION)

    def test_frequency_question_when_no_behavior_signals(self) -> None:
        signals = LayerSignals()
        self.assertEqual(pick_layer_question(signals), FREQUENCY_QUESTION)

    def test_routine_question_when_frequency_without_habit(self) -> None:
        signals = LayerSignals(has_frequency=True)
        self.assertEqual(pick_layer_question(signals), ROUTINE_QUESTION)

    def test_timeframe_question_when_frequency_without_duration(self) -> None:
        signals = LayerSignals(has_frequency=True, has_routine_language=True)
        self.assertEqual(pick_layer_question(signals), TIMEFRAME_QUESTION)

    def test_frequency_question_when_timeframe_without_frequency(self) -> None:
        signals = LayerSignals(has_timeframe=True)
        self.assertEqual(pick_layer_question(signals), FREQUENCY_QUESTION)


if __name__ == "__main__":
    unittest.main()
