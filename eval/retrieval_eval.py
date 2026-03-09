"""Retrieval metrics: Precision@3, MRR, response mode accuracy."""

from __future__ import annotations

import re

from eval.eval_types import EvalCase, RetrievalMetrics


def precision_at_k(retrieved: list[str], gold: list[str], k: int = 3) -> float:
    """Proportion of top-k retrieved chunks that are gold chunks."""
    if not gold:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for chunk_id in top_k if chunk_id in gold)
    return hits / k


def mrr(retrieved: list[str], gold: list[str]) -> float:
    """Reciprocal rank of the first gold chunk in the retrieved list."""
    if not gold:
        return 0.0
    gold_set = set(gold)
    for rank, chunk_id in enumerate(retrieved, start=1):
        if chunk_id in gold_set:
            return 1.0 / rank
    return 0.0


def check_hallucination_sentinel(response_text: str) -> bool:
    """Return True if the response contains a percentage figure (fabrication signal for master_009)."""
    return bool(re.search(r"\d+\s*%", response_text))


def run_retrieval_eval(
    case: EvalCase,
    retrieved_chunk_ids: list[str],
    observed_response_mode: str,
) -> RetrievalMetrics:
    gold_ids = [c.chunk_id for c in case.gold_chunks]
    banned_ids = {c.chunk_id for c in case.banned_chunks}

    if case.retrieval_eval == "none" or not gold_ids:
        p3 = None
        mrr_score = None
    else:
        p3 = precision_at_k(retrieved_chunk_ids, gold_ids, k=3)
        mrr_score = mrr(retrieved_chunk_ids, gold_ids)

    mode_correct = 1.0 if observed_response_mode == case.expected_response_mode else 0.0

    false_positive = any(chunk_id in banned_ids for chunk_id in retrieved_chunk_ids)

    return RetrievalMetrics(
        precision_at_3=p3,
        mrr=mrr_score,
        response_mode_accuracy=mode_correct,
        retrieved_chunk_ids=retrieved_chunk_ids,
        false_positive_retrieval=false_positive,
    )
