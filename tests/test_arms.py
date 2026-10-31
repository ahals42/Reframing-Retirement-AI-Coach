"""Experiment arms: the final arm must equal production, and each other arm must change only what it should."""
import unittest
from pathlib import Path

from coach.arms import ARMS, ArmConfig
from coach.prompts import BASE_PROMPT, build_coach_prompt
from rag.retriever import RetrievalResult, RetrievedChunk, _strip_slide_labels

GOLDEN = (Path(__file__).parent / "golden_final_prompt.txt").read_text()


class ArmPromptTests(unittest.TestCase):
    def test_final_arm_prompt_equals_production(self):
        self.assertEqual(build_coach_prompt({}, ARMS["final"]), GOLDEN)
        self.assertEqual(build_coach_prompt({}), GOLDEN)
        self.assertEqual(ArmConfig(), ARMS["final"])

    def test_comp1_swaps_the_citation_paragraph_only(self):
        p = build_coach_prompt({}, ARMS["comp1_nocite"])
        self.assertIn("Do not name lesson numbers, slides, pages or activities as sources.", p)
        self.assertIn("BEHAVIOUR CHANGE FRAMEWORK (M-PAC)", p)
        self.assertIn("Topic-to-lesson mapping:", p)
        self.assertNotIn("add a brief one-sentence reference", p)

    def test_comp2_drops_mpac_and_lesson_guide(self):
        p = build_coach_prompt({}, ARMS["comp2_noprompt"])
        self.assertNotIn("BEHAVIOUR CHANGE FRAMEWORK (M-PAC)", p)
        self.assertNotIn("LESSON REFERENCE GUIDE", p)
        self.assertIn("Use a motivational interviewing style.", p)
        self.assertIn("HARD SAFETY & SCOPE BOUNDARIES", p)
        self.assertIn("OUTPUT RULES", p)

    def test_comp3_prompt_equals_comp1_prompt(self):
        self.assertEqual(build_coach_prompt({}, ARMS["comp3_generic"]), build_coach_prompt({}, ARMS["comp1_nocite"]))


class SlideLabelTests(unittest.TestCase):
    def test_labels_stripped_only_when_asked(self):
        chunk = RetrievedChunk(doc_type="master", text="Lesson 7 Slide 17 Is it true it takes 66 days?\nThere is no magic number.",
                               metadata={"lesson_number": 7, "slide_number": 17, "slide_title": "Is it true"})
        result = RetrievalResult(master_chunks=[chunk], activity_chunks=[])
        self.assertIn("Lesson 7, Page 17", result.build_prompt_context())
        stripped = result.build_prompt_context(show_labels=False)
        self.assertNotIn("Slide 17", stripped)
        self.assertNotIn("Page 17", stripped)
        self.assertIn("There is no magic number.", stripped)
        self.assertEqual(_strip_slide_labels("Science Module 3 Slide 6 Habits"), "Habits")


if __name__ == "__main__":
    unittest.main()
