"""Token, latency, and cost capture."""

from __future__ import annotations

# Prices in USD per 1M tokens. Update if OpenAI changes pricing.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini":  {"input": 0.15,  "output": 0.60},
    "gpt-4o":       {"input": 2.50,  "output": 10.00},
    "gpt-5-mini":   {"input": 0.25,  "output": 2.00},
    "gpt-5":        {"input": 1.25,  "output": 10.00},
}


def compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return 0.0
    return (
        (prompt_tokens / 1_000_000) * pricing["input"]
        + (completion_tokens / 1_000_000) * pricing["output"]
    )
