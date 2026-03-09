"""
Generate comparison_report.md from results JSONL files.

Usage:
    python -m eval.report                          # reads all JSONL files in eval/results/
    python -m eval.report --run-ids run1 run2      # specific runs only
    python -m eval.report --out eval/results/comparison_report.md
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path

from eval.logger import load_jsonl

RESULTS_DIR = Path(__file__).parent / "results"
DEFAULT_OUT = RESULTS_DIR / "comparison_report.md"

# Structural P@3 ceiling by query family.
# = mean(min(gold_count, 3) / 3) across cases in each family.
# This is the theoretical maximum P@3 achievable with perfect retrieval,
# accounting for cases that have fewer than 3 gold chunks.
P3_CEILINGS = {
    "knowledge":             0.933,  # (1+1+0.667+1+1)/5
    "behaviour_change":      1.000,  # all 5 cases have 3+ gold chunks
    "retirement_transition": 1.000,  # all 5 cases have 3+ gold chunks
    "activity_home":         0.933,  # activity_home_004 has only 2 gold chunks
    "activity_community":    0.667,  # two single-gold cases (kayaking, pickleball)
    "reflective_coaching":   1.000,  # all 5 cases have 3+ gold chunks
    "edge_case":             0.600,  # two out-of-scope cases with 0 gold chunks
}


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------

def bootstrap_ci(
    values: list[float | None],
    n_resamples: int = 1000,
    ci: float = 0.95,
) -> tuple[float | None, float | None, float | None]:
    """Returns (mean, ci_low, ci_high) or (None, None, None) if no valid values."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None, None, None
    means = []
    for _ in range(n_resamples):
        sample = [random.choice(vals) for _ in range(len(vals))]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo_idx = int((1 - ci) / 2 * n_resamples)
    hi_idx = int((1 + ci) / 2 * n_resamples)
    return sum(vals) / len(vals), means[lo_idx], means[hi_idx]


def fmt_ci(mean: float | None, lo: float | None, hi: float | None) -> str:
    if mean is None:
        return "n/a"
    return f"{mean:.3f} [{lo:.3f}-{hi:.3f}]"


def fmt_val(v: float | None) -> str:
    return f"{v:.3f}" if v is not None else "n/a"


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def _group_by(records: list[dict], key: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        groups[r.get(key, "unknown")].append(r)
    return dict(groups)


def _metric_row(label: str, rows: list[dict], metric: str, with_ci: bool = True) -> str:
    vals = [r.get(metric) for r in rows]
    mean, lo, hi = bootstrap_ci(vals)
    n = len([v for v in vals if v is not None])
    if with_ci:
        return f"| {label} | {n} | {fmt_ci(mean, lo, hi)} |"
    return f"| {label} | {n} | {fmt_val(mean)} |"


def build_overview_table(records: list[dict]) -> str:
    """Main model × condition matrix across all primary metrics."""
    by_model_condition: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        key = f"{r.get('model', '?')} | {r.get('condition', '?')}"
        by_model_condition[key].append(r)

    lines = [
        "| Model | Condition | N | P@3 [95% CI] | MRR [95% CI] | Mode Acc | Factual [95% CI] | Relevance [95% CI] | Coaching [95% CI] | Cost/q | Lat P50 (ms) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for key in sorted(by_model_condition):
        rows = by_model_condition[key]
        model, condition = key.split(" | ", 1)
        n = len(rows)
        p3 = bootstrap_ci([r.get("precision_at_3") for r in rows])
        mrr = bootstrap_ci([r.get("mrr") for r in rows])
        mode = bootstrap_ci([r.get("response_mode_accuracy") for r in rows])
        factual = bootstrap_ci([r.get("domain_factual_support") for r in rows])
        relev = bootstrap_ci([r.get("answer_relevance") for r in rows])
        coach = bootstrap_ci([r.get("coaching_quality") for r in rows])
        costs = [r.get("cost_usd") for r in rows if r.get("cost_usd") is not None]
        avg_cost = f"${sum(costs)/len(costs):.4f}" if costs else "n/a"
        latencies = sorted(r.get("latency_ms") for r in rows if r.get("latency_ms") is not None)
        lat_p50 = f"{latencies[len(latencies) // 2]:.0f}" if latencies else "n/a"
        lines.append(
            f"| {model} | {condition} | {n} "
            f"| {fmt_ci(*p3)} | {fmt_ci(*mrr)} | {fmt_ci(*mode)} "
            f"| {fmt_ci(*factual)} | {fmt_ci(*relev)} | {fmt_ci(*coach)} | {avg_cost} | {lat_p50} |"
        )
    return "\n".join(lines)


def build_family_breakdown(records: list[dict], condition: str = "rag") -> str:
    """Per-query-family P@3 and factual support for a single condition."""
    subset = [r for r in records if r.get("condition") == condition]
    # Deduplicate by case_id: retrieval metrics are model-independent (same Qdrant query),
    # so averaging across models would inflate N and double-count the same P@3 values.
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in subset:
        cid = r.get("case_id", "")
        if cid not in seen:
            seen.add(cid)
            deduped.append(r)
    by_family = _group_by(deduped, "query_family")

    lines = [
        f"*Condition: {condition}*\n",
        "| Query Family | N | P@3 | Structural Ceiling | vs Ceiling | Factual Support |",
        "|---|---|---|---|---|---|",
    ]
    for family in sorted(by_family):
        rows = by_family[family]
        p3_vals = [r.get("precision_at_3") for r in rows]
        factual_vals = [r.get("domain_factual_support") for r in rows]
        p3_mean = sum(v for v in p3_vals if v is not None) / max(len([v for v in p3_vals if v is not None]), 1)
        factual_mean, _, _ = bootstrap_ci(factual_vals)
        ceiling = P3_CEILINGS.get(family)
        vs_ceiling = f"{min(p3_mean / ceiling, 1.0):.0%}" if ceiling and p3_mean is not None else "n/a"
        ceiling_str = fmt_val(ceiling)
        lines.append(
            f"| {family} | {len(rows)} | {fmt_val(p3_mean)} | {ceiling_str} | {vs_ceiling} | {fmt_val(factual_mean)} |"
        )
    return "\n".join(lines)


def build_paired_comparisons(records: list[dict]) -> str:
    """Delta tables for A vs B, B vs C, A vs C per model."""
    models = sorted({r.get("model", "?") for r in records})
    metrics = [
        ("precision_at_3", "P@3"),
        ("domain_factual_support", "Factual Support"),
        ("answer_relevance", "Answer Relevance"),
        ("coaching_quality", "Coaching Quality"),
    ]

    lines = [
        "Positive delta = first condition better. Bootstrap 95% CI on the difference.\n",
        "| Model | Comparison | Metric | Delta [95% CI] |",
        "|---|---|---|---|",
    ]

    comparisons = [
        ("rag", "no_rag_prompted", "A vs B (retrieval contribution)"),
        ("no_rag_prompted", "plain_baseline", "B vs C (prompt contribution)"),
        ("rag", "plain_baseline", "A vs C (full system benefit)"),
    ]

    for model in models:
        for cond_a, cond_b, label in comparisons:
            rows_a = {r["case_id"]: r for r in records if r.get("model") == model and r.get("condition") == cond_a}
            rows_b = {r["case_id"]: r for r in records if r.get("model") == model and r.get("condition") == cond_b}
            shared = set(rows_a) & set(rows_b)
            if not shared:
                continue
            for metric_key, metric_label in metrics:
                deltas = []
                for cid in shared:
                    va = rows_a[cid].get(metric_key)
                    vb = rows_b[cid].get(metric_key)
                    if va is not None and vb is not None:
                        deltas.append(va - vb)
                mean, lo, hi = bootstrap_ci(deltas)
                lines.append(f"| {model} | {label} | {metric_label} | {fmt_ci(mean, lo, hi)} |")

    return "\n".join(lines)


def build_critical_issue_log(records: list[dict]) -> str:
    flagged = [r for r in records if r.get("critical_issue")]
    if not flagged:
        return "*No critical issues flagged.*"
    lines = [
        "| Model | Condition | Case ID | Category | Note |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(flagged, key=lambda x: (x.get("model", ""), x.get("condition", ""))):
        lines.append(
            f"| {r.get('model')} | {r.get('condition')} | {r.get('case_id')} "
            f"| {r.get('critical_issue')} | {r.get('critical_issue_note', '')} |"
        )
    return "\n".join(lines)


def build_retrieval_error_analysis(records: list[dict]) -> str:
    """Cases where P@3 = 0 or MRR < 0.5 in the best-performing condition."""
    rag_records = [r for r in records if r.get("condition") == "rag"]
    failures = [r for r in rag_records if
                (r.get("precision_at_3") is not None and r["precision_at_3"] == 0.0)
                or (r.get("mrr") is not None and r["mrr"] < 0.5)]
    if not failures:
        return "*No retrieval failures (P@3=0 or MRR<0.5) detected in RAG condition.*"
    lines = [
        "Cases where P@3 = 0.0 or MRR < 0.5 in Condition A (RAG).\n",
        "| Model | Case ID | Family | P@3 | MRR | Retrieved Chunks |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(failures, key=lambda x: x.get("case_id", "")):
        retrieved = ", ".join(r.get("retrieved_chunk_ids", [])[:3])
        lines.append(
            f"| {r.get('model')} | {r.get('case_id')} | {r.get('query_family')} "
            f"| {fmt_val(r.get('precision_at_3'))} | {fmt_val(r.get('mrr'))} | {retrieved} |"
        )
    return "\n".join(lines)


def generate_report(records: list[dict], out_path: Path) -> None:
    models = sorted({r.get("model", "?") for r in records})
    conditions = sorted({r.get("condition", "?") for r in records})
    n_cases = len({r.get("case_id") for r in records})

    report = f"""# Evaluation Results: Reframing Retirement Coach

Generated from {len(records)} result rows across {n_cases} cases.
Models: {', '.join(models)}
Conditions: {', '.join(conditions)}

---

## 1. Overview: Model × Condition Matrix

All primary metrics with bootstrap 95% confidence intervals (1000 resamples).

{build_overview_table(records)}

---

## 2. Per-Query-Family Breakdown (Condition A: Full RAG)

{build_family_breakdown(records, condition='rag')}

---

## 3. Paired Case-Level Comparisons

{build_paired_comparisons(records)}

---

## 4. Critical Issue Log

{build_critical_issue_log(records)}

---

## 5. Retrieval Error Analysis

{build_retrieval_error_analysis(records)}

---

## 6. Cost Summary

| Model | Condition | Avg Cost/Query | Total Cost (35 cases) |
|---|---|---|---|
"""
    # Cost summary
    by_mc: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_mc[f"{r.get('model')} | {r.get('condition')}"].append(r)
    for key in sorted(by_mc):
        rows = by_mc[key]
        model, condition = key.split(" | ", 1)
        costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
        avg = sum(costs) / len(costs) if costs else 0
        total = sum(costs)
        report += f"| {model} | {condition} | ${avg:.4f} | ${total:.4f} |\n"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"Report written to: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate comparison report from eval results")
    parser.add_argument("--run-ids", nargs="*", help="Specific run ID prefixes to include")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    jsonl_files = sorted(RESULTS_DIR.glob("*.jsonl"))
    if args.run_ids:
        jsonl_files = [f for f in jsonl_files if any(rid in f.name for rid in args.run_ids)]

    if not jsonl_files:
        print(f"No result files found in {RESULTS_DIR}")
        return

    records: list[dict] = []
    for f in jsonl_files:
        records.extend(load_jsonl(f))

    print(f"Loaded {len(records)} records from {len(jsonl_files)} file(s).")
    generate_report(records, args.out)


if __name__ == "__main__":
    main()
