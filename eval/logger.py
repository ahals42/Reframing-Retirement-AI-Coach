"""JSONL logging and summary table printing."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def append_jsonl(path: str | Path, record: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")


def load_jsonl(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _avg(vals: list) -> str:
    vals = [v for v in vals if v is not None]
    if not vals:
        return "n/a"
    return f"{sum(vals) / len(vals):.3f}"


def print_summary_table(results: list[dict]) -> None:
    if not results:
        print("No results.")
        return

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        key = f"{r.get('model', '?')} / {r.get('condition', '?')}"
        groups[key].append(r)

    headers = ["Model / Condition", "N", "P@3", "MRR", "Mode", "Factual", "Relev", "Coach", "Issues"]
    widths = [32, 4, 6, 6, 6, 7, 7, 7, 6]

    def fmt(row: list) -> str:
        return " | ".join(str(v).ljust(w) for v, w in zip(row, widths))

    print(fmt(headers))
    print("-" * (sum(widths) + 3 * len(widths)))

    for key in sorted(groups):
        rows = groups[key]
        issues = sum(1 for r in rows if r.get("critical_issue"))
        print(
            fmt([
                key,
                len(rows),
                _avg([r.get("precision_at_3") for r in rows]),
                _avg([r.get("mrr") for r in rows]),
                _avg([r.get("response_mode_accuracy") for r in rows]),
                _avg([r.get("domain_factual_support") for r in rows]),
                _avg([r.get("answer_relevance") for r in rows]),
                _avg([r.get("coaching_quality") for r in rows]),
                issues if issues else "-",
            ])
        )
