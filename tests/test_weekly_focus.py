"""Tests for the hardcoded weekly focus / lesson goal feature.

Covers:
- extract_lesson_goal_number / extract_week_focus_number / is_generic_weekly_query pattern matching
- No overlap with the existing lesson-overview detector
- CoachAgent returns the correct override text without hitting OpenAI
- Remembered current_lesson/current_week state resolves generic "this week" questions
"""

import unittest

from coach import CoachAgent
from coach.detection.detectors import (
    detect_lesson_goal_request,
    detect_week_focus_request,
    detect_generic_weekly_query,
    detect_lesson_overview_request,
)
from coach.inference import (
    extract_lesson_goal_number,
    extract_week_focus_number,
    is_generic_weekly_query,
)
from coach.weekly_focus import LESSON_GOALS, WEEK_FOCUS, OUT_OF_RANGE_MESSAGE, CLARIFYING_QUESTION


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

class ExtractLessonGoalNumberTests(unittest.TestCase):

    def test_goal_for_lesson(self):
        self.assertEqual(extract_lesson_goal_number("what's the goal for lesson 5"), 5)

    def test_what_do_i_need_to_do(self):
        self.assertEqual(extract_lesson_goal_number("what do I need to do for lesson 3"), 3)

    def test_task_for_lesson(self):
        self.assertEqual(extract_lesson_goal_number("task for lesson 7"), 7)

    def test_lessons_goal_possessive(self):
        self.assertEqual(extract_lesson_goal_number("lesson 2's goal"), 2)

    def test_no_match_on_plain_lesson_overview_phrasing(self):
        self.assertIsNone(extract_lesson_goal_number("what's lesson 5"))
        self.assertIsNone(extract_lesson_goal_number("tell me about lesson 3"))

    def test_no_match_returns_none(self):
        self.assertIsNone(extract_lesson_goal_number("how do I stay motivated"))


class ExtractWeekFocusNumberTests(unittest.TestCase):

    def test_focus_for_week(self):
        self.assertEqual(extract_week_focus_number("what's the focus for week 2"), 2)

    def test_focus_of_week(self):
        self.assertEqual(extract_week_focus_number("what is the focus of week 4"), 4)

    def test_weeks_focus_possessive(self):
        self.assertEqual(extract_week_focus_number("week 3's focus"), 3)

    def test_no_match_returns_none(self):
        self.assertIsNone(extract_week_focus_number("how do I stay motivated"))


class IsGenericWeeklyQueryTests(unittest.TestCase):

    def test_focus_this_week(self):
        self.assertTrue(is_generic_weekly_query("what is my focus this week?"))

    def test_goals_this_week(self):
        self.assertTrue(is_generic_weekly_query("what are my goals for this week?"))

    def test_whats_my_focus(self):
        self.assertTrue(is_generic_weekly_query("what's my focus?"))

    def test_number_present_is_not_generic(self):
        self.assertFalse(is_generic_weekly_query("what's the focus for week 2"))
        self.assertFalse(is_generic_weekly_query("what's the goal for lesson 5"))

    def test_unrelated_question_is_not_generic(self):
        self.assertFalse(is_generic_weekly_query("how do I stay motivated"))


class NoOverlapWithLessonOverviewTests(unittest.TestCase):

    def test_lesson_overview_phrasing_untouched(self):
        self.assertEqual(detect_lesson_overview_request("what is lesson 1 about"), 1)
        self.assertEqual(detect_lesson_overview_request("tell me about lesson 4"), 4)
        # These should not be picked up as goal requests
        self.assertIsNone(detect_lesson_goal_request("tell me about lesson 4"))

    def test_goal_phrasing_not_picked_up_as_overview(self):
        self.assertIsNone(detect_lesson_overview_request("what's the goal for lesson 5"))
        self.assertEqual(detect_lesson_goal_request("what's the goal for lesson 5"), 5)


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


class WeeklyFocusAgentTests(unittest.TestCase):

    def _make_agent(self):
        stub = StubClient()
        agent = CoachAgent(client=stub, model="fake-model")
        return agent, stub

    def test_lesson_goal_request_returns_exact_text(self):
        agent, stub = self._make_agent()
        reply = agent.generate_response("what's the goal for lesson 5")
        self.assertEqual(len(stub.calls), 0)
        self.assertEqual(reply.strip(), LESSON_GOALS[5])

    def test_week_focus_request_returns_exact_text(self):
        agent, stub = self._make_agent()
        reply = agent.generate_response("what's the focus for week 2")
        self.assertEqual(len(stub.calls), 0)
        self.assertEqual(reply.strip(), WEEK_FOCUS[2])

    def test_lesson_out_of_range(self):
        agent, stub = self._make_agent()
        reply = agent.generate_response("what's the goal for lesson 14")
        self.assertEqual(len(stub.calls), 0)
        self.assertEqual(reply.strip(), OUT_OF_RANGE_MESSAGE)

    def test_week_out_of_range(self):
        agent, stub = self._make_agent()
        reply = agent.generate_response("what's the focus for week 9")
        self.assertEqual(len(stub.calls), 0)
        self.assertEqual(reply.strip(), OUT_OF_RANGE_MESSAGE)

    def test_generic_query_with_no_prior_state_asks_clarifying_question(self):
        agent, stub = self._make_agent()
        reply = agent.generate_response("what is my focus this week?")
        self.assertEqual(len(stub.calls), 0)
        self.assertEqual(reply.strip(), CLARIFYING_QUESTION)

    def test_generic_query_resolves_from_remembered_lesson(self):
        agent, stub = self._make_agent()
        agent.generate_response("I'm on lesson 6 right now, what's my week look like?")
        reply = agent.generate_response("what's my focus this week?")
        self.assertEqual(reply.strip(), WEEK_FOCUS[3])

    def test_lesson_overview_question_unaffected(self):
        agent, stub = self._make_agent()
        agent.lesson_overviews = {1: {"title": "T", "description": "D"}}
        reply = agent.generate_response("what is lesson 1 about")
        self.assertEqual(len(stub.calls), 0)
        self.assertIn("Lesson 1", reply)


if __name__ == "__main__":
    unittest.main()
