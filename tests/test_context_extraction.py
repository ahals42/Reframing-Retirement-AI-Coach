"""Tests for barrier/activity/time extraction helpers:just double-checks that our little helper functions actually recognize common barriers (“no time”), activities (“swimming + yoga”), and time estimates (“15 minutes”)."""

import unittest

from main import infer_activities, infer_barrier, infer_time_available


class ContextExtractionTests(unittest.TestCase):
    def test_infer_barrier_time_pressure(self) -> None:
        self.assertEqual(infer_barrier("Work has me so busy I have no time."), "time pressure")

    def test_infer_barrier_motivation(self) -> None:
        self.assertEqual(infer_barrier("I just don't feel motivated lately."), "motivation dip")

    def test_infer_activities_multiple(self) -> None:
        activities = infer_activities("I like swimming and a bit of yoga stretching.")
        self.assertEqual(activities, "mobility, swimming")

    def test_infer_activities_none(self) -> None:
        self.assertIsNone(infer_activities("Mostly just reading and relaxing."))

    def test_infer_time_available_minutes(self) -> None:
        self.assertEqual(infer_time_available("I can spare about 15 minutes."), "15 minutes")

    def test_infer_time_available_half_hour(self) -> None:
        self.assertEqual(infer_time_available("Maybe a half hour."), "30 minutes")


if __name__ == "__main__":
    unittest.main()
