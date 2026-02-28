"""Tests covering the RAG routing + context injection logic using stubs."""
# These tests stub the retriever/router/LLM so we can verify the RAG routing workflow without hitting Qdrant or OpenAI.

from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from coach import CoachAgent
    from rag.retriever import RetrievedChunk, RetrievalResult
    from rag.router import QueryRouter, RouteDecision

    RAG_AVAILABLE = True
except ModuleNotFoundError as exc:
    if "llama_index" in str(exc):
        RAG_AVAILABLE = False
    else:
        raise


if not RAG_AVAILABLE:

    class RagRoutingTests(unittest.TestCase):
        @unittest.skip("llama-index not installed; skip RAG routing tests")
        def test_placeholder(self) -> None:
            pass


else:

    class StubCompletion:
        def __init__(self, text: str) -> None:
            message = type("Msg", (), {"content": text})
            choice = type("Choice", (), {"message": message()})
            self.choices = [choice()]

    class StubChatCompletions:
        def __init__(self, client: "StubClient") -> None:
            self._client = client

        def create(self, **kwargs):
            self._client.calls.append(kwargs)
            return StubCompletion("Stub reply")

    class StubChat:
        def __init__(self, client: "StubClient") -> None:
            self.completions = StubChatCompletions(client)

    class StubClient:
        def __init__(self) -> None:
            self.calls = []
            self.chat = StubChat(self)

    class StubRetriever:
        def __init__(self, result: RetrievalResult) -> None:
            self.result = result
            self.received_queries = []
            self.received_decisions = []

        def gather_context(self, query: str, decision: RouteDecision) -> RetrievalResult:
            self.received_queries.append(query)
            self.received_decisions.append(decision)
            return self.result

    class StubRouter(QueryRouter):  # type: ignore[misc]
        def __init__(self, decision: RouteDecision) -> None:
            self.decision = decision
            self.inputs = []

        def route(self, user_input: str) -> RouteDecision:  # type: ignore[override]
            self.inputs.append(user_input)
            return self.decision

    def _activity_chunk() -> RetrievedChunk:
        metadata = {
            "doc_type": "activity",
            "activity_id": 1,
            "activity_name": "Walking Group",
            "location": "Waterfront",
            "schedule": "Wednesdays",
            "cost_raw": "Free",
        }
        return RetrievedChunk(doc_type="activity", text="Group walk details", metadata=metadata)

    def _master_chunk() -> RetrievedChunk:
        metadata = {
            "doc_type": "master",
            "content_type": "lesson",
            "lesson_number": 1,
            "lesson_title": "Why Physical Activity Matters",
            "slide_number": 3,
            "slide_title": "What is physical activity?",
        }
        return RetrievedChunk(doc_type="master", text="Physical activity definition", metadata=metadata)

    def _science_chunk() -> RetrievedChunk:
        metadata = {
            "doc_type": "master",
            "content_type": "science",
            "lesson_number": None,
            "science_module_number": 1,
            "science_module_title": "The Science Behind WHY to be Active",
            "science_slide_number": 2,
            "global_slide_number": 96,
            "slide_title": "Did you know?",
        }
        return RetrievedChunk(doc_type="master", text="Exercise reduces risk of 25+ chronic diseases", metadata=metadata)

    @unittest.skipUnless(RAG_AVAILABLE, "llama-index not installed; skip RAG routing tests")
    class RagRoutingTests(unittest.TestCase):
        def _build_agent(self, result: RetrievalResult, decision: RouteDecision) -> tuple[CoachAgent, StubClient]:
            stub_client = StubClient()
            retriever = StubRetriever(result)
            router = StubRouter(decision)
            agent = CoachAgent(client=stub_client, model="fake-model", retriever=retriever, router=router)
            return agent, stub_client

        def test_activity_context_injected_when_router_requests(self) -> None:
            # Test 1: when user asks for local resources, the activity index should be used
            result = RetrievalResult(master_chunks=[], activity_chunks=[_activity_chunk()])
            decision = RouteDecision(use_master=False, use_activities=True)
            agent, client = self._build_agent(result, decision)

            agent.generate_response("Any local walking groups?")

            self.assertTrue(client.calls, "Expected chat client to be invoked")
            context_block = client.calls[0]["messages"][1]["content"]
            self.assertIn("Local activities:", context_block)
            self.assertIn("Walking Group", context_block)

        def test_master_context_injected_for_general_query(self) -> None:
            # Test 2: general knowledge queries should pull in master slides for support
            result = RetrievalResult(master_chunks=[_master_chunk()], activity_chunks=[])
            decision = RouteDecision(use_master=True, use_activities=False)
            agent, client = self._build_agent(result, decision)

            agent.generate_response("Why does physical activity matter?")

            context_block = client.calls[0]["messages"][1]["content"]
            self.assertIn("Master slides:", context_block)
            self.assertIn("Lesson 1", context_block)

        def test_citations_added_when_user_requests_sources(self) -> None:
            # Test 3: explicit source requests should append formatted references
            result = RetrievalResult(master_chunks=[_master_chunk()], activity_chunks=[])
            decision = RouteDecision(use_master=True, use_activities=False)
            agent, _ = self._build_agent(result, decision)

            reply = agent.generate_response("Remind me what physical activity means (show sources).")

            self.assertIn("From your modules", reply)
            self.assertIn("Lesson 1:", reply)

        # ------------------------------------------------------------------
        # Science routing tests
        # ------------------------------------------------------------------

        def test_router_science_keywords_set_prefer_science(self) -> None:
            router = QueryRouter()
            for query in [
                "What does the science say?",
                "What evidence supports this?",
                "Show me the research on exercise",
                "What studies back this up?",
                "Explain the mechanism behind habit formation",
                "Is there data on this?",
                "Any proof that exercise helps?",
            ]:
                decision = router.route(query)
                self.assertTrue(decision.prefer_science, f"Expected prefer_science=True for: {query!r}")

        def test_router_why_alone_does_not_set_prefer_science(self) -> None:
            router = QueryRouter()
            decision = router.route("Why can't I stay motivated?")
            self.assertFalse(decision.prefer_science)

        def test_router_general_coaching_does_not_set_prefer_science(self) -> None:
            router = QueryRouter()
            for query in [
                "How do I stay active in retirement?",
                "I find it hard to get started",
                "What should I do this week?",
            ]:
                decision = router.route(query)
                self.assertFalse(decision.prefer_science, f"Expected prefer_science=False for: {query!r}")

        def test_science_chunk_label_format(self) -> None:
            chunk = _science_chunk()
            self.assertEqual(chunk.label(), "Science Module 1 Slide 2: Did you know?")

        def test_science_chunk_reference_format(self) -> None:
            chunk = _science_chunk()
            ref = chunk.reference()
            self.assertEqual(
                ref,
                "Science Module 1: The Science Behind WHY to be Active -> Slide 2 (Did you know?)",
            )

        def test_lesson_chunk_label_unchanged(self) -> None:
            chunk = _master_chunk()
            self.assertEqual(chunk.label(), "Lesson 1 Slide 3: What is physical activity?")

        def test_lesson_chunk_reference_unchanged(self) -> None:
            chunk = _master_chunk()
            ref = chunk.reference()
            self.assertEqual(
                ref,
                "Lesson 1: Why Physical Activity Matters -> Slide 3 (What is physical activity?)",
            )

        def test_science_chunks_excluded_from_regular_retrieval(self) -> None:
            # Science chunks should not appear in non-science (prefer_science=False) retrieve_master calls
            # StubRetriever captures decision; verify prefer_science=False is passed for a normal query
            result = RetrievalResult(master_chunks=[_master_chunk()], activity_chunks=[])
            decision = RouteDecision(use_master=True, use_activities=False, prefer_science=False)
            retriever = StubRetriever(result)
            router = StubRouter(decision)
            stub_client = StubClient()
            agent = CoachAgent(client=stub_client, model="fake-model", retriever=retriever, router=router)

            agent.generate_response("How do I stay motivated?")

            received_decision = retriever.received_decisions[0]
            self.assertFalse(received_decision.prefer_science)

        def test_prefer_science_passed_to_retriever_for_science_query(self) -> None:
            result = RetrievalResult(master_chunks=[_science_chunk()], activity_chunks=[])
            decision = RouteDecision(use_master=True, use_activities=False, prefer_science=True)
            retriever = StubRetriever(result)
            router = StubRouter(decision)
            stub_client = StubClient()
            agent = CoachAgent(client=stub_client, model="fake-model", retriever=retriever, router=router)

            agent.generate_response("What does the research show about exercise?")

            received_decision = retriever.received_decisions[0]
            self.assertTrue(received_decision.prefer_science)


if __name__ == "__main__":
    unittest.main()
