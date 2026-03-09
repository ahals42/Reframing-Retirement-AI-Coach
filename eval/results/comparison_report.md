# Evaluation Results: Reframing Retirement Coach

Generated from 350 result rows across 35 cases.
Models: gpt-4o, gpt-4o-mini, gpt-5, gpt-5-mini
Conditions: no_rag_prompted, plain_baseline, rag

---

## 1. Overview: Model × Condition Matrix

All primary metrics with bootstrap 95% confidence intervals (1000 resamples).

| Model | Condition | N | P@3 [95% CI] | MRR [95% CI] | Mode Acc | Factual [95% CI] | Relevance [95% CI] | Coaching [95% CI] | Cost/q | Lat P50 (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-4o | rag | 35 | 0.717 [0.626-0.798] | 0.914 [0.843-0.980] | 1.000 [1.000-1.000] | 0.807 [0.750-0.864] | 0.679 [0.614-0.743] | 0.809 [0.771-0.844] | $0.0077 | 1538 |
| gpt-4o-mini | no_rag_prompted | 35 | 0.000 [0.000-0.000] | 0.000 [0.000-0.000] | 0.857 [0.743-0.971] | 0.236 [0.114-0.364] | 0.471 [0.379-0.564] | 0.814 [0.736-0.886] | $0.0003 | 2123 |
| gpt-4o-mini | plain_baseline | 35 | 0.000 [0.000-0.000] | 0.000 [0.000-0.000] | 0.829 [0.686-0.943] | 0.043 [0.000-0.107] | 0.629 [0.536-0.714] | 0.550 [0.464-0.636] | $0.0003 | 8598 |
| gpt-4o-mini | rag | 175 | 0.715 [0.677-0.749] | 0.914 [0.882-0.943] | 1.000 [1.000-1.000] | 0.817 [0.786-0.845] | 0.700 [0.657-0.743] | 0.828 [0.801-0.854] | $0.0005 | 1736 |
| gpt-5 | rag | 35 | 0.717 [0.636-0.808] | 0.914 [0.838-0.970] | 1.000 [1.000-1.000] | 0.764 [0.721-0.807] | 0.793 [0.729-0.850] | 0.631 [0.564-0.696] | $0.0162 | 28340 |
| gpt-5-mini | rag | 35 | 0.717 [0.626-0.798] | 0.914 [0.833-0.980] | 1.000 [1.000-1.000] | 0.736 [0.679-0.779] | 0.764 [0.693-0.829] | 0.621 [0.543-0.693] | $0.0028 | 18845 |

---

## 2. Per-Query-Family Breakdown (Condition A: Full RAG)

*Condition: rag*

| Query Family | N | P@3 | Structural Ceiling | vs Ceiling | Factual Support |
|---|---|---|---|---|---|
| activity_community | 5 | 0.667 | 0.667 | 100% | 0.850 |
| activity_home | 5 | 0.867 | 0.933 | 93% | 0.750 |
| behaviour_change | 5 | 0.667 | 1.000 | 67% | 0.800 |
| edge_case | 5 | 0.556 | 0.600 | 93% | 0.650 |
| knowledge | 5 | 0.800 | 0.933 | 86% | 0.950 |
| reflective_coaching | 5 | 0.533 | 1.000 | 53% | 0.750 |
| retirement_transition | 5 | 0.867 | 1.000 | 87% | 0.900 |

---

## 3. Paired Case-Level Comparisons

Positive delta = first condition better. Bootstrap 95% CI on the difference.

| Model | Comparison | Metric | Delta [95% CI] |
|---|---|---|---|
| gpt-4o-mini | A vs B (retrieval contribution) | P@3 | 0.727 [0.646-0.808] |
| gpt-4o-mini | A vs B (retrieval contribution) | Factual Support | n/a |
| gpt-4o-mini | A vs B (retrieval contribution) | Answer Relevance | n/a |
| gpt-4o-mini | A vs B (retrieval contribution) | Coaching Quality | n/a |
| gpt-4o-mini | B vs C (prompt contribution) | P@3 | 0.000 [0.000-0.000] |
| gpt-4o-mini | B vs C (prompt contribution) | Factual Support | 0.193 [0.086-0.314] |
| gpt-4o-mini | B vs C (prompt contribution) | Answer Relevance | -0.157 [-0.257--0.064] |
| gpt-4o-mini | B vs C (prompt contribution) | Coaching Quality | 0.264 [0.150-0.371] |
| gpt-4o-mini | A vs C (full system benefit) | P@3 | 0.727 [0.646-0.818] |
| gpt-4o-mini | A vs C (full system benefit) | Factual Support | n/a |
| gpt-4o-mini | A vs C (full system benefit) | Answer Relevance | n/a |
| gpt-4o-mini | A vs C (full system benefit) | Coaching Quality | n/a |

---

## 4. Critical Issue Log

*No critical issues flagged.*

---

## 5. Retrieval Error Analysis

Cases where P@3 = 0.0 or MRR < 0.5 in Condition A (RAG).

| Model | Case ID | Family | P@3 | MRR | Retrieved Chunks |
|---|---|---|---|---|---|
| gpt-4o-mini | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-4o-mini | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-4o-mini | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-4o-mini | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-4o-mini | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-4o | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-5-mini | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-5 | behaviour_change_001 | behaviour_change | 0.333 | 0.333 | master-L07-S24-G249, master-L07-S23-G248, master-L06-S02-G184 |
| gpt-4o-mini | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |
| gpt-4o-mini | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |
| gpt-4o-mini | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |
| gpt-4o-mini | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |
| gpt-4o-mini | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |
| gpt-4o | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |
| gpt-5-mini | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |
| gpt-5 | behaviour_change_005 | behaviour_change | 0.333 | 0.333 | master-L04-S05-G128, master-L04-S14-G137, master-L04-S13-G136 |

---

## 6. Cost Summary

| Model | Condition | Avg Cost/Query | Total Cost (35 cases) |
|---|---|---|---|
| gpt-4o | rag | $0.0077 | $0.2684 |
| gpt-4o-mini | no_rag_prompted | $0.0003 | $0.0117 |
| gpt-4o-mini | plain_baseline | $0.0003 | $0.0088 |
| gpt-4o-mini | rag | $0.0005 | $0.0799 |
| gpt-5 | rag | $0.0162 | $0.5654 |
| gpt-5-mini | rag | $0.0028 | $0.0979 |
