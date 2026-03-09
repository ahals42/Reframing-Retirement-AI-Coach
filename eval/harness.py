"""
Eval harnesses for the three experimental conditions.

Condition A (full RAG):   EvalHarness         - wraps CoachAgent with real retriever
Condition B (no-RAG):     EvalHarness         - same, but retriever=None so no context injected
Condition C (plain):      PlainBaselineHarness - direct OpenAI call, minimal system prompt

Usage:
    harness = EvalHarness(client, model, retriever=retriever, temperature=0.8)
    response, chunk_ids, mode = harness.eval_generate(case)

    harness_b = EvalHarness(client, model, retriever=None, temperature=0.8)
    response, chunk_ids, mode = harness_b.eval_generate(case)

    harness_c = PlainBaselineHarness(client, model, temperature=0.8)
    response, chunk_ids, mode = harness_c.eval_generate(case)
"""

from __future__ import annotations

import time
import logging
from typing import Any, Optional

from openai import OpenAI

from coach.agent import CoachAgent
from coach.state import ConversationState, _PreparedPrompt
from eval.eval_types import EvalCase

logger = logging.getLogger(__name__)

PLAIN_BASELINE_SYSTEM = "You are a helpful assistant."


# ---------------------------------------------------------------------------
# Instrumented OpenAI client wrapper
# ---------------------------------------------------------------------------

class _CompletionsProxy:
    def __init__(self, completions: Any, capture: dict) -> None:
        self._completions = completions
        self._capture = capture

    def create(self, **kwargs: Any) -> Any:
        start = time.monotonic()
        result = self._completions.create(**kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000
        self._capture["latency_ms"] = elapsed_ms
        if hasattr(result, "usage") and result.usage:
            self._capture["total_tokens"] = result.usage.total_tokens
            self._capture["prompt_tokens"] = result.usage.prompt_tokens
            self._capture["completion_tokens"] = result.usage.completion_tokens
        return result


class _ChatProxy:
    def __init__(self, chat: Any, capture: dict) -> None:
        self._chat = chat
        self.completions = _CompletionsProxy(chat.completions, capture)


class _InstrumentedClient:
    """Wraps an OpenAI client to capture token usage and latency from completions calls."""

    def __init__(self, client: OpenAI) -> None:
        self._client = client
        self._capture: dict = {}
        self.chat = _ChatProxy(client.chat, self._capture)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    def reset(self) -> None:
        self._capture.clear()

    @property
    def last_usage(self) -> dict:
        return dict(self._capture)


# ---------------------------------------------------------------------------
# Condition A / B: CoachAgent-based harness
# ---------------------------------------------------------------------------

class EvalHarness(CoachAgent):
    """
    Thin CoachAgent subclass that:
    - Captures response_mode from _prepare_prompt before the API call.
    - Extracts retrieved chunk IDs from latest_retrieval after generation.
    - Resets per-case state and history between calls.
    - Records token usage and latency via _InstrumentedClient.

    Pass retriever=None for Condition B (no RAG, coaching prompt still applied).
    Pass a real RagRetriever for Condition A (full RAG).
    """

    def __init__(self, client: OpenAI, model: str, **kwargs: Any) -> None:
        self._instrumented = _InstrumentedClient(client)
        super().__init__(self._instrumented, model, **kwargs)
        self._last_response_mode: str = "default"

    def _prepare_prompt(self, user_input: str) -> _PreparedPrompt:
        result = super()._prepare_prompt(user_input)
        self._last_response_mode = result.response_mode
        return result

    def eval_generate(self, case: EvalCase) -> tuple[str, list[str], str]:
        """
        Run a single eval case. Returns (response_text, retrieved_chunk_ids, observed_response_mode).
        Resets conversation state and history before each call.
        """
        # Fresh state per case — no cross-contamination between cases
        self.state = ConversationState()
        self.history = []
        self.latest_retrieval = None
        self._instrumented.reset()

        response = self.generate_response(case.query)

        # Extract chunk IDs from all three retrieval buckets
        chunk_ids: list[str] = []
        if self.latest_retrieval:
            for chunk in (
                list(self.latest_retrieval.master_chunks)
                + list(self.latest_retrieval.activity_chunks)
                + list(self.latest_retrieval.home_chunks)
            ):
                cid = chunk.metadata.get("chunk_id")
                if cid:
                    chunk_ids.append(cid)

        return response, chunk_ids, self._last_response_mode

    @property
    def last_usage(self) -> dict:
        return self._instrumented.last_usage


# ---------------------------------------------------------------------------
# Condition C: plain baseline (direct OpenAI, minimal system prompt)
# ---------------------------------------------------------------------------

class PlainBaselineHarness:
    """
    Direct OpenAI call with a minimal system prompt.
    No RAG, no coaching prompt. Represents real-world naive GPT use.
    """

    def __init__(self, client: OpenAI, model: str, temperature: float = 0.8, max_tokens: int = 600) -> None:
        self._instrumented = _InstrumentedClient(client)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def eval_generate(self, case: EvalCase) -> tuple[str, list[str], str]:
        """
        Returns (response_text, retrieved_chunk_ids=[], observed_response_mode="default").
        """
        self._instrumented.reset()
        completion = self._instrumented.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": PLAIN_BASELINE_SYSTEM},
                {"role": "user", "content": case.query},
            ],
        )
        response_text = completion.choices[0].message.content or ""
        return response_text, [], "default"

    @property
    def last_usage(self) -> dict:
        return self._instrumented.last_usage
