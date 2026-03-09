# Evaluation Framework: Reframing Retirement RAG Chatbot

## Context

The project has a functioning RAG coaching agent (`coach/agent.py`) with three Qdrant collections, keyword-based routing, and 7 response modes. Feasibility testing with real participants starts March 11 2026. This framework supports the primary thesis contribution: a systematic, multi-condition comparison of domain-specialised RAG coaching against GPT-4o baselines on an offline benchmark.

The harness functions as a multi-model experiment runner so the thesis can answer: "which OpenAI model performs best in this system, and how does the full RAG agent compare to a normal baseline?"

---

## Scope Decisions

These are deliberate, justified exclusions, not deferrals. This evaluation is designed to support a single thesis submission alongside qualitative feasibility data. The goal is a defensible, rigorous analysis, not a production monitoring system.

- **Recall@K**: requires exhaustive relevance labelling across every chunk in the collection per query. This is only tractable for the activity and home collections (~30-40 entries each). For the master collection it is not feasible within the scope of this study. Precision@3 and MRR give sufficient retrieval signal for a thesis contribution.
- **nDCG**: requires graded relevance scores (0/1/2) across all relevant chunks per query. Excluded for the same reason as Recall@K. The gold chunk `relevance` field exists in the schema for future use but is not used in this evaluation.
- **Inferential statistics**: 35 cases is insufficient for significance testing. Bootstrap confidence intervals and paired case-level comparisons provide appropriate uncertainty estimation without overstating statistical claims.
- **Online production monitoring**: participant data privacy concern. All evaluation is offline against pre-curated cases.
- **Dashboard/web UI**: out of scope. Results are reported as CSV, JSONL, and a generated markdown comparison report.
- **CI regression gates**: no CI pipeline in this project. Sentinel cases serve the regression function manually.

---

## Tooling Decision: Custom, No Third-Party Eval Framework

- RAGAS requires LangChain/LlamaIndex pipeline objects, not raw strings.
- DeepEval and TruLens require instrumenting CoachAgent directly or adding heavy dependencies.
- LangSmith routes prompts through a third-party server -- unsuitable for a study with participant data.
- **Decision**: custom LLM-as-judge using the OpenAI client already in the project for generation, and Claude Sonnet (Anthropic) as the independent judge model.

---

## Directory Structure

```
eval/
  __init__.py
  test-data/
    eval_cases.jsonl          # 35 hand-curated eval cases (see schema below)
  results/
    .gitkeep                  # rest of results/ is gitignored
  eval_types.py               # EvalCase, GoldChunk, EvalResult dataclasses
  dataset.py                  # load_eval_cases(), save_eval_cases()
  retrieval_eval.py           # precision_at_k(), mrr(), response_mode_accuracy(), run_retrieval_eval()
  generation_eval.py          # domain_factual_support_score(), relevance_score(), run_generation_eval()
  system_eval.py              # latency, token count, cost capture
  harness.py                  # EvalHarness, BaselineHarness, _InstrumentedClient
  judge_prompts.py            # FACTUAL_SUPPORT_JUDGE_V1, RELEVANCE_JUDGE_V1, COACHING_QUALITY_JUDGE_V1
  run_eval.py                 # CLI with --suite, --model, --condition, --prompt-variant, --dry-run
  logger.py                   # append_jsonl(), load_jsonl(), print_summary_table()
  report.py                   # generate comparison_report.md from two result files
  EVALUATION_PLAN.md          # this document
```

---

## Critical Files to Read / Reference

- `rag/retriever.py` - RetrievedChunk.score (cosine 0-1), RetrievalResult with three chunk lists, do_not_reference filter
- `coach/agent.py` - generate_response() entry point to wrap; agent.latest_retrieval public attribute; snapshot() for state
- `coach/state.py` - ConversationState dataclass to reset between eval cases; _PreparedPrompt.response_mode to capture
- `rag/config.py` - load_rag_config() to initialise RagRetriever in CLI (same as backend/app.py)
- `tests/test_rag_routing.py` - StubClient / StubRetriever pattern to follow for _InstrumentedClient

---

## A. Dataset

### File Location

`eval/test-data/eval_cases.jsonl`

One JSON object per line. The dataset contains **35 manually curated benchmark cases spanning the primary query types expected from end users, stratified across 7 query families at 5 cases each.**

### Dataset Schema

Each case must include the following fields:

```json
{
  "case_id": "knowledge_001",
  "query": "Why does exercise matter so much in retirement specifically?",
  "query_family": "knowledge",
  "difficulty": "easy",
  "expected_response_mode": "default",

  "gold_chunks": [
    {
      "collection": "master",
      "chunk_id": "master-L01-S03-G003",
      "relevance": 2
    }
  ],

  "ideal_answer_themes": [
    "loss of structured routine",
    "health trajectory in retirement",
    "evidence base"
  ],

  "sentinel_case": false,

  "retrieval_eval": "master",

  "banned_chunks": []
}
```

Required fields: `case_id`, `query`, `query_family`, `difficulty`, `expected_response_mode`, `gold_chunks`, `ideal_answer_themes`, `sentinel_case`, `retrieval_eval`, `banned_chunks`.

`retrieval_eval` values: `"master"` | `"activity"` | `"home"` | `"none"` (used when no retrieval is expected, e.g. scope boundary cases).

Key rules:
- Use `ideal_answer_themes`, NOT verbatim gold answers. Generative outputs never reproduce exact text.
- Gold chunk IDs must come from chunks where `do_not_reference=False` only.
- Use `chunk_id` from metadata, not text content (stable across re-ingestion).
- `difficulty` values: `easy` | `medium` | `hard`
- `sentinel_case: true` flags cases used for debugging and regression checks

### Dataset Composition (35 cases, stratified by query_family)

| Query Family | Count | Purpose |
|---|---|---|
| `knowledge` | 5 | Core educational explanations grounded in the master collection |
| `behaviour_change` | 5 | M-PAC framework and behaviour change conversations |
| `retirement_transition` | 5 | Identity, motivation, and life-stage transition queries |
| `activity_home` | 5 | At-home activity resources and program materials |
| `activity_community` | 5 | Community and in-person activity recommendations with filters |
| `reflective_coaching` | 5 | Open-ended coaching, autonomy support, goal exploration |
| `edge_case` | 5 | Scope limits, safety boundaries, clinical question handling |

All metrics are reported **both overall and stratified by `query_family`**. A single aggregate hides that precision varies across collections and that boundary cases behave differently.

### Difficulty Distribution

Include a mix to prevent inflated retrieval results from trivially easy cases:

- **Easy**: obvious KB match, single collection, clean routing
- **Medium**: multiple plausible chunks, requires correct routing
- **Hard**: requires correct routing + precise retrieval, or ambiguous intent

At minimum: 40% easy, 40% medium, 20% hard.

### Sentinel Case Subset

3 sentinel cases are flagged with `sentinel_case: true` (edge_case_002, edge_case_003, edge_case_004). These represent critical failure modes:

- **edge_case_002**: skeptical stance with statistics prompt (hallucination/fabrication risk)
- **edge_case_003**: medical advice boundary (clinical scope refusal)
- **edge_case_004**: complete out-of-scope query (scope boundary handling)

Sentinel cases are used for debugging, regression testing, and optional stability reruns between model runs. A system that passes all other cases but fails any sentinel is not deployment-ready.

---

## B. Experimental Conditions

Running multiple conditions on the same 35 cases isolates what each system component contributes.

| Condition | Model | RAG | Coaching Prompt | What it tests |
|---|---|---|---|---|
| A: Full RAG Agent | model | Yes | Full coaching system prompt | Full system |
| B: Prompted No-RAG | model | No | Same coaching system prompt | Value of retrieval alone |
| C: Plain Baseline | model | No | Minimal: "You are a helpful assistant." | Real-world naive use |

- **A vs B**: isolates the contribution of retrieval
- **B vs C**: isolates the contribution of the coaching system prompt
- **A vs C**: measures the combined benefit of the full system

Condition C uses a minimal system prompt rather than no system message at all. A completely promptless call produces model-specific defaults that vary by model version and are not representative of any realistic baseline. "You are a helpful assistant." is the closest equivalent to how a user would access the model directly. This makes the B vs C comparison cleaner: B uses the full coaching prompt, C uses a neutral one-line prompt.

This three-condition design is the **core methodological strength of the study** and directly answers: "does RAG actually help, and does prompt scaffolding help independently?"

### Reporting Language for the Thesis

Do NOT say: "specialised RAG agent vs raw GPT-4o"

DO say: "full domain-specialised RAG coaching agent vs prompted no-RAG baseline vs minimal-query baseline across 4 models"

---

## C. Metrics

### C1. Retrieval Metrics (Condition A only)

Retrieval metrics apply only when retrieval is active. They are not computed for Conditions B or C.

**All collections:**
- Precision@3: `|retrieved[:3] ∩ gold| / 3`
- MRR: `1 / rank_of_first_relevant_chunk`, or 0.0 if no gold chunk appears in top 5

P@5 is excluded. Most cases have 1-3 gold chunks, which structurally caps P@5 at 0.20-0.60 regardless of retrieval quality. MRR handles single-gold-chunk cases more cleanly. Recall@K and nDCG require exhaustive relevance labelling across all chunks in the collection; this is feasible for the smaller activity and home collections but not for master. These are deferred to Phase 2.

Both metrics are reported overall and stratified by query family so structural differences (specific vs broad activity cases, single- vs multi-gold cases) are visible rather than hidden in an aggregate.

**Response Mode Accuracy** (all cases):
- Proportion of cases where `observed_response_mode == expected_response_mode`
- Core system-specific metric unique to this agent's routing/mode logic. Captured by subclassing CoachAgent in EvalHarness rather than modifying agent.py.

### C2. Generation Metrics (LLM-as-judge, all conditions)

**Judge model**: Claude Sonnet (Anthropic). Using an independent model from a different company eliminates same-model self-preference bias. Published research shows LLMs favour outputs from their own model family. Using Claude to judge OpenAI outputs is directly defensible to a thesis committee.

Thesis limitation note: "Evaluation uses an LLM-as-judge; scores are structured approximations. A subset of outputs was manually reviewed to validate judge consistency (see Judge Validation section)."

**Metric naming across conditions**: do NOT use "faithfulness" for cross-condition comparisons. Use unified terms:

- **Domain Factual Support (0-1)**: does the response make claims supported by the relevant curated knowledge base materials for this case?
  - Condition A (RAG): assessed against retrieved chunks
  - Conditions B/C (no RAG): assessed against gold reference materials for that case
- **Answer Relevance (0-1)**: does the response address the query and cover expected themes?
- **Coaching Quality (0-1)**: is the response autonomy-supportive, non-prescriptive, appropriate in scope and length?

Retry once on JSON parse failure. Record score=None if retry also fails.

### C3. System Metrics (all conditions)

- `latency_ms`: wall-clock time for full generate_response() call
- `total_tokens`, `prompt_tokens`, `completion_tokens`: from completion.usage
- `cost_usd`: computed per-model using pricing lookup in system_eval.py
- `model_name`: stored explicitly in every result row

### C4. Critical Issue Annotation (Screening Field)

`critical_issue` is a per-case binary flag logged with every result row. It is not an aggregate threshold metric. With fewer than 10 boundary cases in the eval set, a single flagged case produces a rate of 0.10-0.25, which cannot be interpreted as a population estimate. Manual review after each full condition run is the right mechanism here, not an automated threshold.

The annotation still matters and should be surfaced prominently in reporting. A system with excellent average scores but any critical issues flagged may be unsuitable for deployment regardless of aggregate score.

**Categories**:

| Category | Description |
|---|---|
| `unsupported_claim` | factual claim with no basis in program content |
| `unsafe_health_advice` | clinical or medical guidance the system should not provide |
| `overly_prescriptive` | structured exercise prescription beyond coaching scope |
| `off_topic` | response does not address the query |
| `citation_problem` | invented or incorrect source, URL, or lesson number |
| `boundary_failure` | fails to redirect when a safety or scope boundary applies |

Report count and case IDs, not rate:

| Model | Condition | Critical Issue Count | Case IDs |
|---|---|---|---|

---

## D. Metric Reporting Standards

All summary tables must report:

- mean
- median
- standard deviation
- minimum
- maximum
- N (number of cases)
- critical issue count

**Do not report only means.** Means over 35 cases are sensitive to outliers; reporting the full distribution is necessary.

All tables are stratified by `query_family` as well as reported overall.

---

## E. Model Selection Study

This is a core part of the thesis. The framework runs the full model x condition matrix, giving data to justify every architectural decision.

### Model Matrix

| Category | Model ID | Input $/1M | Output $/1M | What it tests |
|---|---|---|---|---|
| Legacy efficient | gpt-4o-mini | $0.15 | $0.60 | Old gen budget option |
| Balanced | gpt-4o | $2.50 | $10.00 | Current production model (baseline) |
| New gen efficient | gpt-5-mini | $0.25 | $2.00 | New gen value option |
| Maximum capability | gpt-5 | $1.25 | $10.00 | Best possible quality |

### Model Selection Criteria (Predefined)

Priority order used to select the best model from experiment 1:

1. Domain factual support (highest weight)
2. Critical issue rate (must be zero or near-zero)
3. Coaching quality
4. Answer relevance
5. Latency (P50)
6. Cost per query

Lower cost models are preferred only when quality differences are minimal and critical issue rate is equivalent.

### Three Experiments

| Experiment | Models | Conditions | Temperature | top_k | Cases | Purpose |
|---|---|---|---|---|---|---|
| 1. Main comparison | 4 models | A, B, C | Fixed 0.8 | Fixed 5/4/4 | 35 | Model selection + RAG vs baseline |
| 2. Temperature ablation | Best model from exp 1 | A only | 0.3, 0.5, 0.8 | Fixed 5/4/4 | 35 | Justify temperature setting |
| 3. top_k ablation | Best model from exp 1 | A only | Best from exp 2 | 3, 5, 7 | 35 | Justify retrieval depth |

Run experiment 1 first. Use its results to select the model for experiments 2 and 3 using the predefined criteria above.

---

## F. Single-Run Evaluation Policy

**Primary evaluation**: one generation per case per model-condition, fixed temperature, fixed retrieval parameters.

**Targeted reruns only when**:
- API error occurred
- JSON parse failure occurred after retry
- Judge returns null score
- Output is clearly unstable or malformed (e.g. truncated, wrong language)

> Due to cost constraints typical of applied thesis work involving commercial LLM APIs, the primary evaluation uses one controlled generation per case per condition. Variability is mitigated through fixed prompts, fixed retrieval parameters, deterministic evaluation conditions, and targeted reruns for error cases rather than full repeated sampling.

---

## G. Judge Validation / Reliability Check

Before treating judge scores as valid, perform a manual reliability check.

**Procedure**:
1. Randomly sample 8-10 evaluation cases across query families after the first full run
2. For each sampled case, manually score outputs on:
   - domain factual support (0-1)
   - answer relevance (0-1)
   - coaching quality (0-1)
3. Compare human ratings to LLM judge ratings

**Report**:
- agreement counts (within 0.2 threshold)
- mean absolute score difference per metric
- brief qualitative discussion of cases with notable disagreement

This is a **sanity check rather than full inter-rater validation**. Its purpose is to identify systematic judge bias (e.g. consistently lenient or strict) and to catch prompt wording that misleads the judge. If systematic bias is found, adjust judge prompts and rerun.

Document in thesis appendix as: "LLM judge calibration sample (n=8-10 cases, manual review)."

---

## H. Bootstrap Confidence Interval Analysis

Apply bootstrap uncertainty estimation to all primary metrics.

**Procedure**:
1. Collect per-case metric values (e.g. 35 domain factual support scores)
2. Resample cases with replacement (1000 iterations)
3. Compute mean for each resample
4. Report 2.5th and 97.5th percentiles as 95% CI

**Report format**:

Domain factual support = 0.89 [0.86-0.92]

Also bootstrap **paired differences** between conditions:

RAG vs prompted baseline: +0.12 [+0.08-+0.16]

This provides uncertainty estimation rather than formal hypothesis testing, which is appropriate for a 35-case benchmark.

> Note: with 35 cases, bootstrap CIs reflect sampling uncertainty but cannot support strong statistical claims. The comparative deltas between conditions matter more than whether absolute thresholds are met.

---

## I. Paired Case-Level Comparison Analysis

For each key comparison, analyse outputs at the individual case level.

**Comparisons**:
- A (RAG) vs B (prompted baseline) -- isolates retrieval contribution
- B (prompted baseline) vs C (plain baseline) -- isolates prompt contribution
- Best model vs second-best model in RAG condition

**Decision rule per case** (applied to domain factual support unless tied):
1. Higher domain factual support wins
2. If tied: lower critical issue rate wins
3. If tied: higher coaching quality wins
4. Otherwise: mark as tie

**Report**:

| Comparison | Wins | Ties | Losses |
|---|---|---|---|
| RAG vs prompted baseline | - | - | - |
| Prompted baseline vs plain baseline | - | - | - |
| Best model vs second-best (RAG) | - | - | - |

Frame as: **case-level evidence that improvements are consistent rather than driven by a few outliers**.

---

## J. JSONL Log Schema

Each result row must include:

```json
{
  "run_id": "2026-03-09T14:23:01",
  "suite": "all",
  "model_name": "gpt-4o",
  "condition": "rag",
  "prompt_variant": "coach_v1",
  "retrieval_enabled": true,
  "judge_model_name": "claude-sonnet-4-20250514",
  "judge_prompt_version": "v1",
  "temperature": 0.8,
  "top_k_master": 5,
  "top_k_activity": 4,
  "top_k_home": 4,
  "run_timestamp_utc": "2026-03-09T14:23:01Z",
  "case_version": "v3",

  "case_id": "knowledge_001",
  "query_family": "knowledge",
  "difficulty": "medium",
  "sentinel_case": false,
  "query": "...",
  "expected_response_mode": "educational",
  "observed_response_mode": "educational",
  "response_mode_correct": true,
  "response_text": "...",

  "retrieved_chunk_ids": {"master": ["master-L01-S03-G003"], "activity": [], "home": []},
  "retrieved_scores": {"master": [0.87], "activity": [], "home": []},
  "precision_at_3": 0.67,
  "mrr": 1.0,

  "domain_factual_support_score": 0.92,
  "domain_factual_support_reasoning": "...",
  "relevance_score": 0.88,
  "relevance_reasoning": "...",
  "coaching_quality_score": 0.85,
  "coaching_quality_reasoning": "...",

  "critical_issue": false,
  "critical_issue_type": null,

  "latency_ms": 2840,
  "prompt_tokens": 1240,
  "completion_tokens": 183,
  "total_tokens": 1423,
  "cost_usd": 0.0049,

  "coach_state": {"process_layer": "unclassified", "barrier": "unknown"},
  "error": null
}
```

Also append one summary row per run to `eval/results/summary.csv`.

---

## K. Quality Thresholds

These are internal engineering targets, not externally validated standards. Present them as such in the thesis. For reporting, the **comparative deltas between conditions matter more than whether absolute thresholds are passed**.

P@5 is excluded from reporting. Most cases have 1-3 gold chunks, which structurally caps P@5 at 0.20-0.60 regardless of retrieval quality. MRR handles the single-gold-chunk case more cleanly. P@3 and MRR together give a complete picture of retrieval performance. Stratified results by query family (master, activity_specific, activity_broad, home) are reported in the results section body.

Critical Issue Rate is logged per case as a binary screening field but is not a threshold metric. With fewer than 10 boundary cases in the eval set, a single flagged case produces a rate of 0.10-0.25, making aggregate thresholds statistically meaningless. Manual review after each condition run serves this function instead.

### Retrieval (Condition A only)

**P@3 structural ceiling:** P@3 is capped by gold chunk count, not retrieval quality. A perfect system cannot score above `min(gold_count, 3) / 3`. MRR has no structural ceiling — a perfect system always returns the gold chunk at rank 1, giving MRR = 1.00 regardless of how many gold chunks the case has.

**2 cases excluded from retrieval metrics** (`retrieval_eval = "none"`): edge_case_003 and edge_case_004 are scope and clinical boundary cases where no retrieval is expected. Both still receive full generation scoring.

**How targets were set:** There is no established literature standard for ceiling-based thresholds in domain-specific RAG with incomplete labelling. Traditional IR benchmarks (TREC) use fully-labelled collections where ceiling = 1.00 and compare systems against each other, not against a ceiling percentage. RAG evaluation papers (RAGAS, ARES) also assume exhaustive labels. Targets here are therefore **utility-based**: what P@3 score means the system is reliably surfacing enough relevant content to support a grounded coaching response?

- **Target** = the system consistently returns most available gold chunks in the top 3. For 2-gold cases this means both chunks surfaced (P@3 = 0.67); for 3-gold cases it means at least 2 of 3 surfaced (P@3 = 0.67+). Targets are set at the mean P@3 achievable when the system gets most queries right.
- **Fail** = the system is missing relevant content in more than half of queries in that family, meaning responses are likely to be under-informed or ungrounded for that query type.
- Targets are stratified by family because ceilings differ structurally. Comparing a 0.67 score for activity_community (ceiling 0.67, all gold chunks surfaced) against knowledge (ceiling 0.93) without stratification would be misleading.

No literature-derived percentage was used. These are pre-registered internal engineering benchmarks. The comparative delta between conditions is the primary interpretive frame; threshold pass/fail is secondary.

#### P@3 by query family

| Query Family | N | Structural P@3 ceiling | Target | Fail below | Utility interpretation |
|---|---|---|---|---|---|
| `knowledge` | 5 | 0.93 | >= 0.80 | < 0.55 | Core science queries return relevant knowledge chunks in top 3 |
| `behaviour_change` | 5 | 1.00 | >= 0.78 | < 0.55 | M-PAC and behaviour change content surfaced for coaching queries |
| `retirement_transition` | 5 | 1.00 | >= 0.76 | < 0.55 | Identity and transition content reliably returned |
| `activity_home` | 5 | 0.80 | >= 0.72 | < 0.50 | Home activity entries returned in top 3 |
| `activity_community` | 5 | 0.67 | >= 0.58 | < 0.40 | Single correct community activity entry found in top 3 |
| `reflective_coaching` | 5 | 1.00 | >= 0.74 | < 0.50 | Reflective and autonomy-support chunks available in top 3 |
| `edge_case` | 3 | 0.53 | >= 0.40 | < 0.20 | Boundary queries return appropriate chunks where applicable |
| **Overall** | **33** | | **>= 0.72** | **< 0.48** | |

activity_community note: structural ceiling is 0.67 because most cases have 1 gold chunk (P@3 ceiling = 0.33) or 2 gold chunks (P@3 ceiling = 0.67). Report alongside Hit@3 rate (proportion of 5 cases where the single gold chunk appears in top 3).

edge_case note: 2 of 5 edge_case cases have `retrieval_eval = "none"` and are excluded from retrieval metrics. Only 3 cases contribute to the edge_case row above.

#### MRR (all retrieval families, uniform target)

| Metric | Target | Fail Below | Why | How |
|---|---|---|---|---|
| MRR | >= 0.75 | < 0.60 | Rank sensitivity: P@3 does not distinguish between a gold chunk at rank 1 vs rank 3. MRR captures whether the most relevant chunk is surfaced first, which is especially important for single-gold-chunk cases where P@3 is capped at 0.33. MRR ceiling is 1.00 for all families. | `1 / rank_of_first_gold_chunk` per case, 0.0 if no gold chunk appears in top 5. Averaged across all 33 retrieval cases and reported per family. |

#### Response Mode Accuracy

| Metric | Target | Fail Below | Why | How |
|---|---|---|---|---|
| Response Mode Accuracy | >= 0.80 | < 0.65 | Routing correctness: this agent uses keyword-based routing to select one of seven response modes. Wrong routing produces a structurally incorrect response regardless of retrieval or generation quality. Unique to this system. | `observed_response_mode == expected_response_mode` per case, proportion correct across all 35 cases. Captured by subclassing CoachAgent in EvalHarness. Note: the agent has no dedicated safety or refusal mode. All edge_case family queries route to `default`, so `expected_response_mode = "default"` for those cases. Response mode accuracy is not a meaningful signal for boundary cases; the critical issue flag carries the evaluation weight for those. |

### Generation (all conditions)

| Metric | Target | Fail Below | Why | How |
|---|---|---|---|---|
| Domain Factual Support | >= 0.80 | < 0.65 | The cross-condition comparison metric. Measures whether the response makes claims that are grounded in the program knowledge base. In Condition A this is assessed against retrieved chunks; in Conditions B and C it is assessed against the gold reference materials for that case. The metric that answers whether RAG reduces unsupported claims vs baseline. | LLM-as-judge (Claude Sonnet) scoring 0-1 from FACTUAL_SUPPORT_JUDGE_V1 prompt with JSON output. One retry on parse failure; score recorded as None if retry fails. |
| Answer Relevance | >= 0.75 | < 0.60 | Baseline quality bar. A response can be factually grounded but still fail to address the query or cover the themes the participant actually needed. Ensures the system is not just faithful but on-topic. | LLM-as-judge (Claude Sonnet) scoring 0-1 from RELEVANCE_JUDGE_V1 prompt against ideal_answer_themes from the eval case. |
| Coaching Quality | >= 0.75 | < 0.60 | The strongest thesis contribution metric. Standard benchmarks do not measure whether a response is autonomy-supportive, non-prescriptive, and appropriately scoped for a coaching context. This metric is unique to this system and directly tied to the intervention design. | LLM-as-judge (Claude Sonnet) scoring 0-1 from COACHING_QUALITY_JUDGE_V1 prompt. Assesses tone, boundary respect, and length appropriateness independent of factual content. |

### System (all conditions)

| Metric | Target | Fail Below | Why | How |
|---|---|---|---|---|
| Latency P50 | < 4000ms | > 8000ms | Feasibility study viability. Participants in the March 2026 study will use the chatbot in real time. A median response time above 4 seconds degrades the coaching interaction. | Wall-clock time for the full `generate_response()` call, measured in `EvalHarness`. Median across all cases per model and condition. |
| Cost per query | < $0.05 | > $0.15 | Deployment viability. The selected model must be sustainable for a full feasibility study cohort without prohibitive API spend. | Computed from `completion.usage` token counts and MODEL_PRICING lookup in `system_eval.py`. Stored per case and averaged per model and condition. |

---

## L. Planned Thesis Output

### Tables

| Table | Content |
|---|---|
| Dataset distribution | Case counts by query_family and difficulty |
| Metrics by model and condition | Mean, median, SD, min, max, N, critical issues |
| Query-family breakdown | All generation metrics stratified by family |
| Critical issue counts | By model, condition, and issue category |
| Paired case comparison | Win/tie/loss counts per comparison |

### Figures

- Cost per query vs domain factual support (scatter, all model-condition combinations)
- Latency P50 vs coaching quality (tradeoff chart)
- Rank position of first gold chunk (bar chart, x = rank 1-5+none, y = case count) — shows at a glance whether the system consistently surfaces the right chunk first or buries it at position 3

### Appendix

- Example judged cases: 2 successes and 2 failures, one failure must be a boundary case. Include full query, response, judge reasoning, and score.
- Human vs judge calibration results (n=8-10 cases, manual scoring on all three generation metrics with agreement table)
- Retrieval error analysis: after experiment 1, scan all cases where P@3 = 0.0 or MRR < 0.5. Categorise each by error type and include a short table. This shows system insight and critical analysis.

---

## M. CLI

**Available flags:**
- `--suite`: `retrieval` | `generation` | `all`
- `--model`: `gpt-4o-mini` | `gpt-4o` | `gpt-5-mini` | `gpt-5`
- `--condition`: `rag` | `no_rag_prompted` | `plain_baseline`
- `--temperature`: float, default 0.8
- `--top-k`: int (applies to all collections), default uses per-collection values
- `--dry-run`: validate dataset and config, print plan, no API calls
- `--case-ids`: comma-separated list for targeted reruns
- `--sentinel-only`: run sentinel cases only (3 flagged cases, fast smoke test)

**Experiment 1: minimum viable model comparison (6 runs)**

Run all 4 models in Condition A (RAG) first to identify the best model. Then run that model in conditions B and C to isolate the contribution of retrieval and prompting. This gives the core thesis findings with half the API cost of the full 12-run matrix.

Step 1: Run all 4 models in the full RAG condition to select the best model.
```bash
python -m eval.run_eval --suite=all --model=gpt-4o-mini --condition=rag
python -m eval.run_eval --suite=all --model=gpt-4o --condition=rag
python -m eval.run_eval --suite=all --model=gpt-5-mini --condition=rag
python -m eval.run_eval --suite=all --model=gpt-5 --condition=rag
```

Step 2: Run the best model from step 1 in conditions B and C.
```bash
python -m eval.run_eval --suite=all --model=<best> --condition=no_rag_prompted
python -m eval.run_eval --suite=all --model=<best> --condition=plain_baseline
```

If budget allows, extend step 2 to all 4 models for a complete 12-run matrix. The 6-run plan is the minimum needed for thesis findings.

Generate report after completing all runs:
```bash
python -m eval.report
```

**Experiment 2: temperature ablation (best model from exp 1, condition A only)**
```bash
python -m eval.run_eval --suite=all --model=<best> --condition=rag --temperature=0.3
python -m eval.run_eval --suite=all --model=<best> --condition=rag --temperature=0.5
python -m eval.run_eval --suite=all --model=<best> --condition=rag --temperature=0.8
```

**Experiment 3: top_k ablation (best model, best temperature from exp 2, condition A only)**
```bash
python -m eval.run_eval --suite=retrieval --model=<best> --condition=rag --top-k=3
python -m eval.run_eval --suite=retrieval --model=<best> --condition=rag --top-k=5
python -m eval.run_eval --suite=retrieval --model=<best> --condition=rag --top-k=7
```

**Other common commands:**
```bash
# Validate dataset without running
python -m eval.run_eval --suite=all --dry-run

# Targeted rerun for error cases
python -m eval.run_eval --suite=all --model=gpt-5 --condition=rag --case-ids knowledge_001,knowledge_002

# Fast smoke test (sentinel cases only)
python -m eval.run_eval --suite=all --sentinel-only --model=gpt-5 --condition=rag  # runs edge_case_002, 003, 004

# Compare two result files
python -m eval.report results/run_A.jsonl results/run_B.jsonl
```

---

## N. Limitations

Acknowledged in the thesis methods section:

1. **Offline benchmark**: cases are hand-curated and may not fully represent the distribution of real user queries from feasibility participants
2. **LLM-as-judge**: scores are structured approximations of quality; judge calibration sample provides partial validation but cannot substitute for human annotation at scale
3. **Single-run evaluation**: one generation per case per condition means stochastic variation is not quantified; mitigated by fixed prompts and targeted reruns for error cases
4. **Incomplete retrieval labels**: exhaustive relevance labelling is only feasible for smaller collections; master collection uses precision-only metrics
5. **Feasibility sample**: actual participant behaviour may differ from benchmark query patterns; offline results are indicative rather than predictive of deployment quality

---

## O. Implementation Order

**Day 1:** `eval_types.py`, `dataset.py`, first 20 eval cases in `eval/test-data/eval_cases.jsonl` (mpac + science families)
**Day 2:** `retrieval_eval.py` (including `response_mode_accuracy`), `logger.py`, run retrieval eval, complete remaining 30 cases
**Day 3:** `judge_prompts.py` (all 3 judges), `generation_eval.py` with retry, `harness.py` with `_InstrumentedClient` and `BaselineHarness`, run generation eval, tune judges, run manual calibration check (8-10 cases)
**Day 4:** `run_eval.py` CLI, `report.py` with bootstrap CIs and paired comparisons, full end-to-end run on all 3 conditions, save baseline

---

## P. Interview and Thesis Narrative

The story has four parts:

1. **Problem**: standard benchmarks don't apply to domain-specific coaching agents. We needed our own eval.
2. **Design**: 35 eval cases across 7 query families, 3 experimental conditions to isolate what each component adds, LLM-as-judge with manual calibration.
3. **Finding**: retrieval improved domain factual support by [X] points vs the prompted no-RAG baseline. Coaching prompt scaffolding added [Y] points vs the plain baseline. Model [Z] hit the best quality-cost tradeoff with zero critical issues.
4. **Decision**: selected [model] for production because [evidence].

That is a complete engineering decision story backed by data.
