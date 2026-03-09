"""Load and filter eval cases from JSONL."""

from __future__ import annotations

import json
from pathlib import Path

from eval.eval_types import BannedChunk, EvalCase, GoldChunk

DEFAULT_CASES_PATH = Path(__file__).parent / "test-data" / "eval_cases.jsonl"


def load_eval_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            gold_chunks = [GoldChunk(**c) for c in d.get("gold_chunks", [])]
            banned_chunks = [BannedChunk(**c) for c in d.get("banned_chunks", [])]
            cases.append(
                EvalCase(
                    case_id=d["case_id"],
                    query=d["query"],
                    query_family=d["query_family"],
                    difficulty=d["difficulty"],
                    expected_response_mode=d["expected_response_mode"],
                    gold_chunks=gold_chunks,
                    ideal_answer_themes=d["ideal_answer_themes"],
                    sentinel_case=d["sentinel_case"],
                    retrieval_eval=d["retrieval_eval"],
                    banned_chunks=banned_chunks,
                )
            )
    return cases


def filter_cases(
    cases: list[EvalCase],
    sentinel_only: bool = False,
    case_ids: list[str] | None = None,
    query_family: str | None = None,
) -> list[EvalCase]:
    if sentinel_only:
        cases = [c for c in cases if c.sentinel_case]
    if case_ids:
        id_set = set(case_ids)
        cases = [c for c in cases if c.case_id in id_set]
    if query_family:
        cases = [c for c in cases if c.query_family == query_family]
    return cases
