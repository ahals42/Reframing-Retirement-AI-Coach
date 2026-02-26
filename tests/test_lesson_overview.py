"""Tests for the lesson overview feature.

Covers:
- extract_lesson_number / detect_lesson_overview_request pattern matching
- parse_lesson_overviews reads the real data file
- CoachAgent returns the correct override text without hitting OpenAI
"""

import unittest
from pathlib import Path

from coach import CoachAgent
from coach.detection.detectors import detect_lesson_overview_request
from coach.inference import extract_lesson_number
from rag.parsing_master import parse_lesson_overviews

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "reframing_retirement_master_data_set.txt"


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

class ExtractLessonNumberTests(unittest.TestCase):

    def test_tell_me_about(self):
        self.assertEqual(extract_lesson_number("tell me about lesson 3"), 3)

    def test_what_is(self):
        self.assertEqual(extract_lesson_number("what is lesson 1"), 1)

    def test_whats(self):
        self.assertEqual(extract_lesson_number("what's lesson 7?"), 7)

    def test_explain(self):
        self.assertEqual(extract_lesson_number("can you explain lesson 5"), 5)

    def test_describe(self):
        self.assertEqual(extract_lesson_number("describe lesson 10"), 10)

    def test_about(self):
        self.assertEqual(extract_lesson_number("about lesson 2"), 2)

    def test_overview_suffix(self):
        self.assertEqual(extract_lesson_number("lesson 4 overview"), 4)

    def test_overview_prefix(self):
        self.assertEqual(extract_lesson_number("overview of lesson 6"), 6)

    def test_summary(self):
        self.assertEqual(extract_lesson_number("summary of lesson 8"), 8)

    def test_what_is_in(self):
        self.assertEqual(extract_lesson_number("what's in lesson 9"), 9)

    def test_what_does_cover(self):
        self.assertEqual(extract_lesson_number("what does lesson 3 cover"), 3)

    def test_no_match_returns_none(self):
        self.assertIsNone(extract_lesson_number("tell me about physical activity"))

    def test_which_lesson_is_not_overview(self):
        # "which lesson" should NOT be treated as an overview request
        self.assertIsNone(extract_lesson_number("which lesson covers goal setting"))

    def test_detect_lesson_overview_request_matches(self):
        self.assertEqual(detect_lesson_overview_request("tell me about lesson 3"), 3)

    def test_detect_lesson_overview_request_no_match(self):
        self.assertIsNone(detect_lesson_overview_request("how do I stay active"))


# ---------------------------------------------------------------------------
# Data parsing
# ---------------------------------------------------------------------------

@unittest.skipUnless(DATA_PATH.exists(), "Master data file not found")
class ParseLessonOverviewsTests(unittest.TestCase):

    def setUp(self):
        self.overviews = parse_lesson_overviews(DATA_PATH)

    def test_all_ten_lessons_parsed(self):
        self.assertEqual(set(self.overviews.keys()), set(range(1, 11)))

    def test_lesson_3_title(self):
        title = self.overviews[3]["title"]
        self.assertIn("Social", title)

    def test_lesson_3_description_non_empty(self):
        desc = self.overviews[3]["description"]
        self.assertTrue(len(desc) > 20)

    def test_no_slide_count_in_title(self):
        # Slide counts like "(27 slides)" should be stripped
        for num, info in self.overviews.items():
            self.assertNotIn("slides", info["title"].lower(), msg=f"Lesson {num} title has slide count")


# ---------------------------------------------------------------------------
# CoachAgent override (no OpenAI call needed)
# ---------------------------------------------------------------------------

class StubCompletion:
    def __init__(self, text: str) -> None:
        message = type("Msg", (), {"content": text})
        choice = type("Choice", (), {"message": message()})
        self.choices = [choice()]


class StubChatCompletions:
    def __init__(self, client):
        self._client = client

    def create(self, **kwargs):
        self._client.calls.append(kwargs)
        return StubCompletion("Should not be called")


class StubChat:
    def __init__(self, client):
        self.completions = StubChatCompletions(client)


class StubClient:
    def __init__(self):
        self.calls = []
        self.chat = StubChat(self)


class LessonOverviewAgentTests(unittest.TestCase):

    def _make_agent_with_overviews(self, overviews):
        stub = StubClient()
        agent = CoachAgent(client=stub, model="fake-model")
        agent.lesson_overviews = overviews
        return agent, stub

    def test_lesson_overview_is_returned_directly(self):
        overviews = {
            3: {"title": "Social Connections Test", "description": "A test description."},
        }
        agent, stub = self._make_agent_with_overviews(overviews)

        reply = agent.generate_response("tell me about lesson 3")

        # Should NOT call OpenAI
        self.assertEqual(len(stub.calls), 0, "OpenAI should not be called for lesson overview")
        self.assertIn("Lesson 3", reply)
        self.assertIn("Social Connections Test", reply)
        self.assertIn("A test description.", reply)

    def test_lesson_not_in_map_falls_through_to_normal_flow(self):
        agent, stub = self._make_agent_with_overviews({})
        # lesson_overviews is empty so no override — should hit OpenAI stub
        agent.generate_response("tell me about lesson 3")
        # The stub was called because no override matched
        self.assertGreater(len(stub.calls), 0)

    def test_normal_question_is_unaffected(self):
        agent, stub = self._make_agent_with_overviews({3: {"title": "T", "description": "D"}})
        reply = agent.generate_response("How do I stay motivated?")
        # Normal question → OpenAI stub called, reply is stub text
        self.assertGreater(len(stub.calls), 0)
        self.assertEqual(reply, "Should not be called")


if __name__ == "__main__":
    unittest.main()
