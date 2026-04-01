"""Optional reranking for merged retrieval candidates."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings


@dataclass(slots=True)
class RerankCandidate:
    candidate_id: str
    base_score: float
    confidence: float
    authority_weight: float
    review_status: str | None
    last_verified_at: datetime | None
    source_count: int
    is_current: bool
    is_stale: bool


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self, question: str, candidates: list[RerankCandidate]
    ) -> list[RerankCandidate]:
        """Return candidates in final ranking order."""


class HeuristicReranker(BaseReranker):
    async def rerank(
        self, question: str, candidates: list[RerankCandidate]
    ) -> list[RerankCandidate]:
        now = datetime.now(timezone.utc)
        current_truth_focus = bool(
            {
                "active",
                "current",
                "latest",
                "now",
                "today",
            }
            & set(re.findall(r"[a-z0-9_]+", question.lower()))
        )

        def _score(candidate: RerankCandidate) -> tuple[float, float, float]:
            score = candidate.base_score
            score += 0.35 * candidate.confidence
            score += 0.4 * candidate.authority_weight
            score += 0.1 * min(candidate.source_count, 3)

            if candidate.is_current:
                score += 0.2
            if candidate.is_stale:
                score -= 0.2

            if candidate.review_status == "needs_review":
                score -= 0.55 if current_truth_focus else 0.35
            elif candidate.review_status == "approved":
                score += 0.15

            age_penalty = 0.0
            if candidate.last_verified_at is not None:
                age_penalty = min(
                    (now - candidate.last_verified_at).days / 365.0,
                    0.5,
                )
                score -= age_penalty
                if current_truth_focus and (now - candidate.last_verified_at).days > 30:
                    score -= 0.15

            return (score, candidate.authority_weight, candidate.confidence)

        return sorted(candidates, key=_score, reverse=True)


class DisabledReranker(BaseReranker):
    async def rerank(
        self, question: str, candidates: list[RerankCandidate]
    ) -> list[RerankCandidate]:
        return sorted(
            candidates,
            key=lambda candidate: candidate.base_score,
            reverse=True,
        )


def build_default_reranker() -> BaseReranker:
    if settings.enable_reranking:
        return HeuristicReranker()
    return DisabledReranker()
