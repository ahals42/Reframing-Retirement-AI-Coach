"""
CLI entry point for running eval experiments.

Usage:
    python -m eval.run_eval --suite=all --model=gpt-4o --condition=rag
    python -m eval.run_eval --suite=retrieval --sentinel-only --model=gpt-4o --condition=rag --dry-run
    python -m eval.run_eval --suite=generation --model=gpt-4o-mini --condition=no_rag_prompted
    python -m eval.run_eval --case-ids master_001 boundary_003 --model=gpt-4o --condition=rag
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic
from openai import OpenAI

from eval.dataset import filter_cases, load_eval_cases
from eval.eval_types import EvalResult, SystemMetrics
from eval.generation_eval import run_generation_eval
from eval.harness import EvalHarness, PlainBaselineHarness
from eval.logger import append_jsonl, print_summary_table
from eval.retrieval_eval import check_hallucination_sentinel, run_retrieval_eval
from eval.system_eval import compute_cost

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"
CONDITIONS = {"rag", "no_rag_prompted", "plain_baseline"}
SUITES = {"retrieval", "generation", "all"}


def _build_run_id(model: str, condition: str, temperature: float, top_k: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{model}_{condition}_t{temperature}_k{top_k}_{ts}"


def _fetch_gold_chunks_from_qdrant(retriever: object, case) -> list[dict]:
    """
    Fetch gold chunk texts from Qdrant by chunk_id for Conditions B/C.
    Returns list of {chunk_id, text} dicts for the judge reference material.
    Falls back gracefully if a chunk is not found.
    """
    results = []
    if not hasattr(retriever, "_master_index") or retriever is None:
        return results
    for gold in case.gold_chunks:
        # Retrieve by chunk_id stored in metadata — search top-1 by exact metadata match
        # LlamaIndex does not support exact metadata filter retrieval natively, so we use
        # a keyword search on the chunk_id string as a close approximation.
        try:
            from llama_index.core.retrievers import VectorIndexRetriever
            index = getattr(retriever, f"_{gold.collection}_index", None)
            if index is None:
                continue
            r = VectorIndexRetriever(index=index, similarity_top_k=5)
            nodes = r.retrieve(gold.chunk_id)
            for node in nodes:
                meta = node.node.metadata if hasattr(node, "node") else {}
                if meta.get("chunk_id") == gold.chunk_id:
                    results.append({"chunk_id": gold.chunk_id, "text": node.get_content()})
                    break
        except Exception as exc:
            logger.warning("Could not fetch gold chunk %s: %s", gold.chunk_id, exc)
    return results


def _detect_critical_issue(case, response_text: str, retrieved_chunk_ids: list[str]) -> tuple[str | None, str | None]:
    """Heuristic critical issue detection. Manual review is still required after each run."""
    # Hallucination sentinel: fabricated percentage (edge_case_002 tests skeptical stance with statistics)
    if case.case_id == "edge_case_002" and check_hallucination_sentinel(response_text):
        return "unsupported_claim", "Response contains a percentage figure not present in any program chunk"

    # Banned chunk retrieved and likely used
    banned_ids = {c.chunk_id for c in case.banned_chunks}
    if any(cid in banned_ids for cid in retrieved_chunk_ids):
        return "unsupported_claim", f"Banned chunk retrieved: {[c for c in retrieved_chunk_ids if c in banned_ids]}"

    # Edge cases: check for unsafe health advice patterns (medical advice boundary)
    if case.query_family == "edge_case":
        unsafe_patterns = [
            r"\b(you should|you must|i recommend|i suggest)\s+(take|stop|reduce|increase)\s+\w+\s+(medication|drug|pill|dose)",
            r"\bexercise\s+(can|will|may)\s+replace\s+(your\s+)?(medication|drug)",
        ]
        for pattern in unsafe_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                return "unsafe_health_advice", "Response appears to endorse medication guidance"

    return None, None


def run_eval(
    model: str,
    condition: str,
    suite: str,
    temperature: float,
    top_k: int,
    sentinel_only: bool,
    case_ids: list[str] | None,
    dry_run: bool,
) -> None:
    cases = load_eval_cases()
    cases = filter_cases(cases, sentinel_only=sentinel_only, case_ids=case_ids)

    if not cases:
        logger.error("No cases matched filters.")
        sys.exit(1)

    run_id = _build_run_id(model, condition, temperature, top_k)
    output_path = RESULTS_DIR / f"{run_id}.jsonl"

    print(f"\n{'DRY RUN — ' if dry_run else ''}Eval run: {run_id}")
    print(f"Cases: {len(cases)} | Suite: {suite} | Model: {model} | Condition: {condition}")
    print(f"Temperature: {temperature} | top_k: {top_k}")
    if not dry_run:
        print(f"Output: {output_path}\n")

    if dry_run:
        print("\nCase plan:")
        for c in cases:
            print(f"  [{c.difficulty:6}] {c.case_id:35} family={c.query_family:20} retrieval={c.retrieval_eval}")
        print(f"\nTotal API calls (generation): {len(cases)} agent + {len(cases) * 3} judge")
        print("Dry run complete. No API calls made.")
        return

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Build harness
    if condition in {"rag", "no_rag_prompted"}:
        retriever = None
        if condition == "rag":
            from rag.retriever import RagRetriever
            from rag.config import load_rag_config
            retriever = RagRetriever(load_rag_config())
            # Apply top_k override
            if hasattr(retriever, "config"):
                retriever.config.master_top_k = top_k
                retriever.config.activity_top_k = top_k
                retriever.config.home_top_k = top_k
        harness = EvalHarness(
            openai_client,
            model,
            retriever=retriever,
            temperature=temperature,
        )
    else:
        harness = PlainBaselineHarness(openai_client, model, temperature=temperature)

    results_log: list[dict] = []

    for i, case in enumerate(cases, 1):
        print(f"[{i:02}/{len(cases):02}] {case.case_id} ...", end=" ", flush=True)

        try:
            response_text, chunk_ids, observed_mode = harness.eval_generate(case)
            usage = harness.last_usage

            # Filter retrieved chunks to the collection under evaluation.
            # master chunks always come first in the flat list, so without this
            # filtering, activity/home cases always score against the wrong chunks.
            eval_chunk_ids = chunk_ids
            if condition == "rag" and hasattr(harness, "latest_retrieval") and harness.latest_retrieval:
                r = harness.latest_retrieval
                if case.retrieval_eval == "activity":
                    eval_chunk_ids = [c.metadata.get("chunk_id") for c in r.activity_chunks if c.metadata.get("chunk_id")]
                elif case.retrieval_eval == "home":
                    eval_chunk_ids = [c.metadata.get("chunk_id") for c in r.home_chunks if c.metadata.get("chunk_id")]
                elif case.retrieval_eval == "master":
                    eval_chunk_ids = [c.metadata.get("chunk_id") for c in r.master_chunks if c.metadata.get("chunk_id")]

            retrieval_metrics = run_retrieval_eval(case, eval_chunk_ids, observed_mode)

            # Reference chunks for judge: retrieved (Condition A) or gold (Conditions B/C)
            if condition == "rag" and hasattr(harness, "latest_retrieval") and harness.latest_retrieval:
                ref_chunks = [
                    {"chunk_id": c.metadata.get("chunk_id", ""), "text": c.text}
                    for bucket in (
                        harness.latest_retrieval.master_chunks,
                        harness.latest_retrieval.activity_chunks,
                        harness.latest_retrieval.home_chunks,
                    )
                    for c in bucket
                ]
            else:
                retriever_for_gold = getattr(harness, "retriever", None)
                ref_chunks = _fetch_gold_chunks_from_qdrant(retriever_for_gold, case)

            generation_metrics = None
            if suite in {"generation", "all"}:
                generation_metrics = run_generation_eval(case, response_text, ref_chunks, anthropic_client)

            from eval.eval_types import GenerationMetrics, JudgeScore
            if generation_metrics is None:
                generation_metrics = GenerationMetrics(
                    domain_factual_support=JudgeScore(score=None, reasoning="skipped"),
                    answer_relevance=JudgeScore(score=None, reasoning="skipped"),
                    coaching_quality=JudgeScore(score=None, reasoning="skipped"),
                )

            latency_ms = usage.get("latency_ms", 0.0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            cost = compute_cost(model, prompt_tokens, completion_tokens)

            critical_issue, critical_note = _detect_critical_issue(case, response_text, chunk_ids)

            result = EvalResult(
                case_id=case.case_id,
                query_family=case.query_family,
                difficulty=case.difficulty,
                model=model,
                condition=condition,
                temperature=temperature,
                top_k=top_k,
                response_text=response_text,
                retrieval=retrieval_metrics,
                generation=generation_metrics,
                system=SystemMetrics(
                    latency_ms=latency_ms,
                    total_tokens=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                ),
                critical_issue=critical_issue,
                critical_issue_note=critical_note,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            record = result.to_log_dict()
            append_jsonl(output_path, record)
            results_log.append(record)

            status = "OK"
            if critical_issue:
                status = f"CRITICAL: {critical_issue}"
            elif retrieval_metrics.precision_at_3 is not None:
                status = f"P@3={retrieval_metrics.precision_at_3:.2f}"
            print(status)

        except Exception as exc:
            logger.error("Case %s failed: %s", case.case_id, exc, exc_info=True)
            print("ERROR")

    print(f"\n--- Summary: {run_id} ---")
    print_summary_table(results_log)
    print(f"\nResults saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluation experiments")
    parser.add_argument("--model", required=True, choices=["gpt-4o-mini", "gpt-4o", "gpt-5-mini", "gpt-5"])
    parser.add_argument("--condition", required=True, choices=sorted(CONDITIONS))
    parser.add_argument("--suite", default="all", choices=sorted(SUITES))
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=5, dest="top_k")
    parser.add_argument("--sentinel-only", action="store_true")
    parser.add_argument("--case-ids", nargs="*")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_eval(
        model=args.model,
        condition=args.condition,
        suite=args.suite,
        temperature=args.temperature,
        top_k=args.top_k,
        sentinel_only=args.sentinel_only,
        case_ids=args.case_ids,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
