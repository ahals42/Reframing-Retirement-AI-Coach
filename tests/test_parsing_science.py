"""Tests for Science Behind (SB##) parsing in the master dataset."""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from rag.parsing_master import parse_master_file


SAMPLE_DATA = textwrap.dedent("""\
    *********************************************************************
    =====================================================================
    LESSON 1: Why Physical Activity Matters During Retirement (2 slides)
    =====================================================================
    L01-S01-G001 | Lesson 1 Slide 1/2 | Global 1/10

    Lesson Description: This lesson covers why activity matters.

    *********************************************************************
    L01-S02-G002 | Lesson 1 Slide 2/2 | Global 2/10

    Title: What is physical activity?
    +++

    Content:
    Physical activity means any movement of your body.

    *********************************************************************
    ==========================================================
    SCIENCE 1: The Science Behind WHY to be Active (2 slides)
    ==========================================================
    SB01-S01-G003 | Part 1 Slide 1/2 | Global 3/10

    Lesson Description: This module covers the science behind activity.

    *********************************************************************
    SB01-S02-G004 | Part 1 Slide 2/2 | Global 4/10

    Title: Did you know?
    +++

    Content:
    Exercise reduces the risk of over 25 chronic diseases.

    *********************************************************************
    ==========================================================
    SCIENCE 2: The Science Behind HOW to Stay Active (1 slide)
    ==========================================================
    SB02-S01-G005 | Part 2 Slide 1/1 | Global 5/10

    Title: Habit formation
    +++

    Content:
    Habits form through repeated cues and rewards.

    *********************************************************************
    <<<<<<<<<<<<<<<<<<<<<<<<<<<DATASET_END>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
""")


class ParseScienceChunksTests(unittest.TestCase):
    """Parser correctly handles SB## slides and assigns science metadata."""

    def _parse(self) -> list:
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_text", return_value=SAMPLE_DATA):
            return parse_master_file(Path("fake.txt"))

    def test_lesson_chunks_have_lesson_content_type(self):
        chunks = self._parse()
        lesson_chunks = [c for c in chunks if c.metadata.get("content_type") == "lesson"]
        self.assertEqual(len(lesson_chunks), 2)

    def test_science_chunks_have_science_content_type(self):
        chunks = self._parse()
        science_chunks = [c for c in chunks if c.metadata.get("content_type") == "science"]
        self.assertEqual(len(science_chunks), 3)

    def test_science_module_number_populated(self):
        chunks = self._parse()
        science_chunks = [c for c in chunks if c.metadata.get("content_type") == "science"]
        module_numbers = {c.metadata["science_module_number"] for c in science_chunks}
        self.assertIn(1, module_numbers)
        self.assertIn(2, module_numbers)

    def test_science_slide_number_populated(self):
        chunks = self._parse()
        sb1_chunks = [c for c in chunks if c.metadata.get("science_module_number") == 1]
        slide_numbers = {c.metadata["science_slide_number"] for c in sb1_chunks}
        self.assertEqual(slide_numbers, {1, 2})

    def test_science_module_title_populated(self):
        chunks = self._parse()
        sb1_chunks = [c for c in chunks if c.metadata.get("science_module_number") == 1]
        for chunk in sb1_chunks:
            self.assertIn("WHY to be Active", chunk.metadata["science_module_title"])

    def test_science_chunk_ids_use_sb_prefix(self):
        chunks = self._parse()
        science_chunks = [c for c in chunks if c.metadata.get("content_type") == "science"]
        for chunk in science_chunks:
            self.assertTrue(chunk.chunk_id.startswith("master-SB"), chunk.chunk_id)

    def test_science_global_slide_number_populated(self):
        chunks = self._parse()
        sb1_s2 = next(
            c for c in chunks
            if c.metadata.get("science_module_number") == 1 and c.metadata.get("science_slide_number") == 2
        )
        self.assertEqual(sb1_s2.metadata["global_slide_number"], 4)

    def test_science_lesson_number_is_none(self):
        chunks = self._parse()
        science_chunks = [c for c in chunks if c.metadata.get("content_type") == "science"]
        for chunk in science_chunks:
            self.assertIsNone(chunk.metadata.get("lesson_number"))

    def test_lesson_chunks_unaffected(self):
        """Existing lesson metadata is unchanged by the science additions."""
        chunks = self._parse()
        lesson_chunks = [c for c in chunks if c.metadata.get("content_type") == "lesson"]
        for chunk in lesson_chunks:
            self.assertIsNotNone(chunk.metadata.get("lesson_number"))
            self.assertIsNotNone(chunk.metadata.get("slide_number"))
            self.assertEqual(chunk.metadata.get("lesson_title"), "Why Physical Activity Matters During Retirement")

    def test_do_not_reference_still_works_for_science(self):
        data_with_dnr = SAMPLE_DATA.replace("Title: Did you know?", "***DO NOT REFERENCE***\n\nTitle: Did you know?")
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "read_text", return_value=data_with_dnr):
            chunks = parse_master_file(Path("fake.txt"))
        dnr_chunk = next(
            (c for c in chunks if c.metadata.get("science_slide_number") == 2 and c.metadata.get("science_module_number") == 1),
            None,
        )
        self.assertIsNotNone(dnr_chunk)
        self.assertTrue(dnr_chunk.metadata["do_not_reference"])


if __name__ == "__main__":
    unittest.main()
