"""LLM-as-judge generation scoring using Claude Sonnet as the independent judge."""

from __future__ import annotations

import json
import logging

from anthropic import Anthropic

from eval.eval_types import EvalCase, GenerationMetrics, JudgeScore
from eval.judge_prompts import (
    COACHING_QUALITY_JUDGE_V1,
    FACTUAL_SUPPORT_JUDGE_V1,
    RELEVANCE_JUDGE_V1,
)

logger = logging.getLogger(__name__)

JUDGE_MODEL = "claude-sonnet-4-20250514"


def _call_judge(client: Anthropic, prompt: str) -> JudgeScore:
    """Call Claude Sonnet with a judge prompt. Retries once on JSON parse failure."""
    for attempt in range(2):
        try:
            response = client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            parsed = json.loads(text)
            return JudgeScore(
                score=float(parsed["score"]),
                reasoning=parsed.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            if attempt == 0:
                logger.warning("Judge parse failure (attempt 1): %s. Retrying.", exc)
            else:
                logger.error("Judge parse failure (attempt 2): %s. Recording None.", exc)
    return JudgeScore(score=None, reasoning="parse_failure")


def format_reference_material(chunks: list[dict]) -> str:
    """Format a list of {chunk_id, text} dicts into the reference block for judge prompts."""
    if not chunks:
        return "(no reference material provided)"
    lines = [f"[{c['chunk_id']}]: {c['text']}" for c in chunks]
    return "\n".join(lines)


def run_generation_eval(
    case: EvalCase,
    response_text: str,
    reference_chunks: list[dict],
    judge_client: Anthropic,
) -> GenerationMetrics:
    """
    Score a single response on all three generation metrics.

    reference_chunks: list of {chunk_id, text} dicts.
        - Condition A: the chunks the agent actually retrieved (from Qdrant).
        - Conditions B/C: the gold chunks for this case, fetched from Qdrant by chunk_id.
    """
    ref_material = format_reference_material(reference_chunks)
    themes_str = "\n".join(f"- {t}" for t in case.ideal_answer_themes)

    factual_prompt = FACTUAL_SUPPORT_JUDGE_V1.format(
        query=case.query,
        reference_material=ref_material,
        response=response_text,
    )
    relevance_prompt = RELEVANCE_JUDGE_V1.format(
        query=case.query,
        ideal_answer_themes=themes_str,
        response=response_text,
    )
    coaching_prompt = COACHING_QUALITY_JUDGE_V1.format(
        query=case.query,
        response=response_text,
    )

    return GenerationMetrics(
        domain_factual_support=_call_judge(judge_client, factual_prompt),
        answer_relevance=_call_judge(judge_client, relevance_prompt),
        coaching_quality=_call_judge(judge_client, coaching_prompt),
    )
