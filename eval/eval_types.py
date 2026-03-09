"""Typed dataclasses for all eval inputs and outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GoldChunk:
    collection: str
    chunk_id: str


@dataclass
class BannedChunk:
    collection: str
    chunk_id: str
    reason: str


@dataclass
class EvalCase:
    case_id: str
    query: str
    query_family: str
    difficulty: str                   # easy | medium | hard
    expected_response_mode: str
    gold_chunks: list[GoldChunk]
    ideal_answer_themes: list[str]
    sentinel_case: bool
    retrieval_eval: str               # master | activity | home | none
    banned_chunks: list[BannedChunk] = field(default_factory=list)


@dataclass
class RetrievalMetrics:
    precision_at_3: Optional[float]   # None when retrieval_eval = none
    mrr: Optional[float]              # None when retrieval_eval = none
    response_mode_accuracy: float     # 1.0 or 0.0
    retrieved_chunk_ids: list[str]
    false_positive_retrieval: bool = False  # True if a banned chunk was retrieved


@dataclass
class JudgeScore:
    score: Optional[float]            # None on double parse failure
    reasoning: str


@dataclass
class GenerationMetrics:
    domain_factual_support: JudgeScore
    answer_relevance: JudgeScore
    coaching_quality: JudgeScore


@dataclass
class SystemMetrics:
    latency_ms: float
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


@dataclass
class EvalResult:
    case_id: str
    query_family: str
    difficulty: str
    model: str
    condition: str                    # rag | no_rag_prompted | plain_baseline
    temperature: float
    top_k: int
    response_text: str
    retrieval: RetrievalMetrics
    generation: GenerationMetrics
    system: SystemMetrics
    critical_issue: Optional[str] = None       # category string if flagged
    critical_issue_note: Optional[str] = None
    timestamp: str = ""

    def to_log_dict(self) -> dict:
        """Flat dict for JSONL logging and CSV summary."""
        return {
            "case_id": self.case_id,
            "query_family": self.query_family,
            "difficulty": self.difficulty,
            "model": self.model,
            "condition": self.condition,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "response_mode_accuracy": self.retrieval.response_mode_accuracy,
            "precision_at_3": self.retrieval.precision_at_3,
            "mrr": self.retrieval.mrr,
            "retrieved_chunk_ids": self.retrieval.retrieved_chunk_ids,
            "false_positive_retrieval": self.retrieval.false_positive_retrieval,
            "domain_factual_support": self.generation.domain_factual_support.score,
            "domain_factual_support_reasoning": self.generation.domain_factual_support.reasoning,
            "answer_relevance": self.generation.answer_relevance.score,
            "answer_relevance_reasoning": self.generation.answer_relevance.reasoning,
            "coaching_quality": self.generation.coaching_quality.score,
            "coaching_quality_reasoning": self.generation.coaching_quality.reasoning,
            "latency_ms": self.system.latency_ms,
            "total_tokens": self.system.total_tokens,
            "prompt_tokens": self.system.prompt_tokens,
            "completion_tokens": self.system.completion_tokens,
            "cost_usd": self.system.cost_usd,
            "critical_issue": self.critical_issue,
            "critical_issue_note": self.critical_issue_note,
            "response_text": self.response_text,
            "timestamp": self.timestamp,
        }
