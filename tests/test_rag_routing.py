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
            "lesson_number": 1,
            "lesson_title": "Why Physical Activity Matters",
            "slide_number": 3,
            "slide_title": "What is physical activity?",
        }
        return RetrievedChunk(doc_type="master", text="Physical activity definition", metadata=metadata)

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


if __name__ == "__main__":
    unittest.main()
