"""Experiment arms: the final arm must equal production, and each other arm must change only what it should."""
import unittest
from pathlib import Path

from dataclasses import replace
from types import SimpleNamespace
from unittest import mock

from coach import CoachAgent
from coach.arms import ARMS, ArmConfig
from coach.prompts import ABSTAIN_INSTRUCTION, BASE_PROMPT, GROUNDING_CLAUSES, NO_CONTENT_NOTE, build_coach_prompt
from rag.config import RagConfig
from rag.retriever import RagRetriever, RetrievalResult, RetrievedChunk, _apply_arm_to_config, _strip_slide_labels
from rag.router import RouteDecision

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




STRICT_LITERAL = (
    "Only state specific details, mechanisms, or examples that are explicitly present in the retrieved "
    "content below; if a detail isn't there, keep your explanation at the level of generality the content "
    "supports rather than filling the gap from general knowledge. When the retrieved content only "
    "partially covers the question, prefer omitting the missing part over inferring or generalizing "
    "past what's written."
)


class StubCompletions:
    def __init__(self, text="Stub reply"):
        self.calls, self.text = [], text

    def create(self, **kwargs):
        self.calls.append(kwargs)
        msg = SimpleNamespace(content=self.text)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def stub_client(text="Stub reply"):
    return SimpleNamespace(chat=SimpleNamespace(completions=StubCompletions(text)))


def agent(arm_name, client=None, retriever=None):
    return CoachAgent(client=client or stub_client(), model="fake", retriever=retriever, lesson_overviews={}, arm=ARMS[arm_name])


def chunk(text="Lesson 7 Slide 17 Habits", score=0.9, **meta):
    return RetrievedChunk(doc_type="master", text=text, metadata={"lesson_number": 7, "slide_number": 17, "slide_title": "Habits", **meta}, score=score)


class SwitchPromptTests(unittest.TestCase):
    def test_a1_drops_only_the_safety_section(self):
        p = build_coach_prompt({}, ARMS["a1_nosafety"])
        self.assertNotIn("HARD SAFETY & SCOPE BOUNDARIES", p)
        for kept in ("COACH PERSONALITY", "BEHAVIOUR CHANGE FRAMEWORK (M-PAC)", "DEFAULT RESPONSE STRUCTURE", "COACHING PRINCIPLES", "LESSON REFERENCE GUIDE", "OUTPUT RULES"):
            self.assertIn(kept, p)
        self.assertLess(len(p), len(GOLDEN))

    def test_a2_drops_only_the_coaching_sections(self):
        p = build_coach_prompt({}, ARMS["a2_nocoaching"])
        self.assertNotIn("DEFAULT RESPONSE STRUCTURE", p)
        self.assertNotIn("COACHING PRINCIPLES", p)
        for kept in ("HARD SAFETY & SCOPE BOUNDARIES", "BEHAVIOUR CHANGE FRAMEWORK (M-PAC)", "LESSON REFERENCE GUIDE", "OUTPUT RULES"):
            self.assertIn(kept, p)

    def test_other_new_arms_leave_the_prompt_unchanged(self):
        for name in ("a4b_nopost", "r1_floor", "r3_k1", "r3_k3", "r3_k12", "r4_nostitch", "r4_long", "r2_rewrite", "f1_permissive", "f2_gap"):
            self.assertEqual(build_coach_prompt({}, ARMS[name]), GOLDEN, name)

    def test_each_new_arm_differs_from_final_in_one_switch(self):
        base = ARMS["final"].__dict__
        for name in ("a1_nosafety", "a2_nocoaching", "a4b_nopost", "r1_floor", "r3_k1", "r3_k3", "r3_k12", "r4_nostitch", "r4_long", "r2_rewrite", "f1_permissive", "f2_gap"):
            diff = [k for k, v in ARMS[name].__dict__.items() if k != "name" and v != base[k]]
            self.assertEqual(len(diff), 1, (name, diff))


class PostprocessTests(unittest.TestCase):
    TEXT = "Walking helps. Would you like to try it? Do this walk daily. It builds habits. A fourth sentence."

    def test_final_filters_and_caps_and_appends(self):
        a = agent("final")
        out = a._postprocess_response(self.TEXT, response_mode="educational", module_reference_sentence="See Lesson 7.")
        self.assertNotIn("?", out)
        self.assertTrue(out.endswith("See Lesson 7."))
        self.assertNotEqual(a._maybe_append_mh_disclaimer("x", "I feel anxious"), "x")

    def test_a4b_returns_text_unchanged_and_no_disclaimer(self):
        a = agent("a4b_nopost")
        out = a._postprocess_response(self.TEXT, response_mode="educational", module_reference_sentence="See Lesson 7.")
        self.assertEqual(out, self.TEXT)
        self.assertEqual(a._maybe_append_mh_disclaimer("x", "I feel anxious"), "x")


class RetrievalSwitchTests(unittest.TestCase):
    def config(self):
        return RagConfig(openai_api_key="k", chat_model="m", embedding_model="e", embedding_dimensions=3, master_collection="rr_master",
                         activities_collection="rr_activities", home_collection="rr_home", qdrant_url="u", qdrant_api_key=None,
                         master_data_path=None, activity_data_path=None, home_data_path=None)

    def test_top_k_override_only_for_k_arms(self):
        cfg = self.config()
        self.assertEqual(_apply_arm_to_config(cfg, ARMS["final"]).master_top_k, 7)
        self.assertEqual(_apply_arm_to_config(cfg, None).master_top_k, 7)
        for name, k in (("r3_k1", 1), ("r3_k3", 3), ("r3_k12", 12)):
            self.assertEqual(_apply_arm_to_config(cfg, ARMS[name]).master_top_k, k)
        self.assertEqual(_apply_arm_to_config(cfg, ARMS["r3_k12"]).master_collection, "rr_master")

    def retriever(self, arm_name):
        r = object.__new__(RagRetriever)
        r.arm, r.generic, r._cache = ARMS[arm_name], False, {}
        r.config = _apply_arm_to_config(self.config(), ARMS[arm_name])
        r.master_index, r._master_by_global_slide = None, {}
        return r

    def test_stitching_switch(self):
        for name, expect in (("final", 1), ("r4_nostitch", 0)):
            r = self.retriever(name)
            r._retrieve_chunks = lambda *a, **k: [chunk()]
            with mock.patch.object(RagRetriever, "_attach_neighbor_slides") as attach:
                r.retrieve_master("habits")
            self.assertEqual(attach.call_count, expect, name)

    def test_requested_passages_follow_top_k(self):
        r = self.retriever("r3_k3")
        asked = []
        r._retrieve_chunks = lambda index, query, top_k, doc_type: asked.append(top_k) or [chunk(score=0.9 - i / 100) for i in range(top_k)]
        out = r.retrieve_master("habits")
        self.assertEqual(len(out), 3)

    def test_truncation_limit(self):
        res = RetrievalResult(master_chunks=[chunk(text="x" * 3000)], activity_chunks=[])
        short = res.build_prompt_context(show_labels=False)
        long = res.build_prompt_context(show_labels=False, char_limit=2400)
        self.assertEqual(short, res.build_prompt_context(show_labels=False, char_limit=1200))
        self.assertGreater(len(long), len(short))
        self.assertLessEqual(len(long), 2400 + 100)

    def test_similarity_floor_drops_and_abstains(self):
        r = self.retriever("r1_floor")
        r.arm = replace(ARMS["r1_floor"], similarity_floor=0.5)
        r.retrieve_master = lambda *a, **k: [chunk(score=0.9), chunk(score=0.3)]
        r.retrieve_activities = lambda *a, **k: [RetrievedChunk(doc_type="activity", text="Yoga", metadata={}, score=0.2)]
        res = r.gather_context("q", RouteDecision(use_master=True, use_activities=True))
        self.assertEqual([c.score for c in res.master_chunks], [0.9])
        self.assertEqual(list(res.activity_chunks), [])
        self.assertFalse(res.no_relevant_master)
        r._cache = {}
        r.retrieve_master = lambda *a, **k: [chunk(score=0.1)]
        res = r.gather_context("q2", RouteDecision(use_master=True))
        self.assertEqual(list(res.master_chunks), [])
        self.assertTrue(res.no_relevant_master)

    def test_final_arm_applies_no_floor(self):
        r = self.retriever("final")
        r.retrieve_master = lambda *a, **k: [chunk(score=0.01)]
        res = r.gather_context("q", RouteDecision(use_master=True))
        self.assertEqual(len(res.master_chunks), 1)
        self.assertFalse(res.no_relevant_master)


class AgentSwitchTests(unittest.TestCase):
    def stub_retriever(self, result):
        seen = []
        return SimpleNamespace(gather_context=lambda q, d, science_module=None: seen.append(q) or result, config=None, seen=seen)

    def test_abstain_instruction_added_when_no_relevant_content(self):
        result = RetrievalResult(master_chunks=[], activity_chunks=[], no_relevant_master=True)
        client, ret = stub_client(), self.stub_retriever(result)
        a = agent("r1_floor", client=client, retriever=ret)
        a.generate_response("What does Lesson 11 cover about swimming?")
        contents = [m["content"] for m in client.chat.completions.calls[0]["messages"] if m["role"] == "system"]
        self.assertTrue(any(NO_CONTENT_NOTE in c for c in contents))
        self.assertTrue(any(ABSTAIN_INSTRUCTION in c for c in contents))
        self.assertTrue(any("HARD SAFETY & SCOPE BOUNDARIES" in c for c in contents))   # safety rules stay

    def test_final_arm_has_no_abstain_instruction(self):
        result = RetrievalResult(master_chunks=[chunk()], activity_chunks=[])
        client = stub_client()
        a = agent("final", client=client, retriever=self.stub_retriever(result))
        a.generate_response("Tell me about habits")
        contents = " ".join(m["content"] for m in client.chat.completions.calls[0]["messages"])
        self.assertNotIn(ABSTAIN_INSTRUCTION, contents)

    def test_query_rewrite_uses_rewritten_query_only_for_retrieval(self):
        result = RetrievalResult(master_chunks=[chunk()], activity_chunks=[])
        client = stub_client("habit cue routine consistency")
        ret = self.stub_retriever(result)
        a = agent("r2_rewrite", client=client, retriever=ret)
        a.generate_response("I keep forgetting my walk, any trick?")
        self.assertEqual(ret.seen, ["habit cue routine consistency"])
        first, second = client.chat.completions.calls[0], client.chat.completions.calls[1]
        self.assertEqual(first["max_completion_tokens"], 40)
        self.assertEqual(first["temperature"], 0)
        self.assertEqual(first["reasoning_effort"], "none")
        self.assertEqual(second["messages"][-1]["content"], "I keep forgetting my walk, any trick?")     # original wording stays in the prompt
        self.assertEqual(a.latest_retrieval.rewritten_query, "habit cue routine consistency")

    def test_no_rewrite_call_in_other_arms(self):
        result = RetrievalResult(master_chunks=[chunk()], activity_chunks=[])
        client, ret = stub_client(), self.stub_retriever(result)
        a = agent("final", client=client, retriever=ret)
        a.generate_response("I keep forgetting my walk, any trick?")
        self.assertEqual(len(client.chat.completions.calls), 1)
        self.assertEqual(ret.seen, ["I keep forgetting my walk, any trick?"])

    def test_grounding_clauses(self):
        self.assertEqual(GROUNDING_CLAUSES["strict"], STRICT_LITERAL)
        for mode in ("default", "educational", "lowest_mpac", "mpac_question", "home_resources"):
            self.assertIn(STRICT_LITERAL, agent("final")._build_retrieval_instruction(mode), mode)
        for name, key in (("f1_permissive", "permissive"), ("f2_gap", "gap")):
            text = agent(name)._build_retrieval_instruction("default")
            self.assertIn(GROUNDING_CLAUSES[key], text)
            self.assertNotIn(STRICT_LITERAL, text)
        self.assertIn("make clear that it is general", GROUNDING_CLAUSES["permissive"])
        self.assertIn("say so in one sentence", GROUNDING_CLAUSES["gap"])


if __name__ == "__main__":
    unittest.main()
