from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.processing.reranker import HeuristicReranker, RerankCandidate


class TestHeuristicReranker:
    async def test_prefers_higher_authority_and_approved_candidates(self):
        reranker = HeuristicReranker()
        ordered = await reranker.rerank(
            "What is our enterprise price?",
            [
                RerankCandidate(
                    candidate_id="low-authority",
                    base_score=2.0,
                    confidence=0.95,
                    authority_weight=0.4,
                    review_status="needs_review",
                    last_verified_at=datetime.now(UTC),
                    source_count=1,
                    is_current=True,
                    is_stale=False,
                ),
                RerankCandidate(
                    candidate_id="high-authority",
                    base_score=1.85,
                    confidence=0.9,
                    authority_weight=0.95,
                    review_status="approved",
                    last_verified_at=datetime.now(UTC),
                    source_count=2,
                    is_current=True,
                    is_stale=False,
                ),
            ],
        )

        assert [candidate.candidate_id for candidate in ordered] == [
            "high-authority",
            "low-authority",
        ]

    async def test_penalizes_stale_candidates(self):
        reranker = HeuristicReranker()
        ordered = await reranker.rerank(
            "What blockers are active?",
            [
                RerankCandidate(
                    candidate_id="fresh",
                    base_score=1.5,
                    confidence=0.7,
                    authority_weight=0.7,
                    review_status=None,
                    last_verified_at=datetime.now(UTC),
                    source_count=1,
                    is_current=True,
                    is_stale=False,
                ),
                RerankCandidate(
                    candidate_id="stale",
                    base_score=1.5,
                    confidence=0.7,
                    authority_weight=0.7,
                    review_status=None,
                    last_verified_at=datetime.now(UTC) - timedelta(days=180),
                    source_count=1,
                    is_current=True,
                    is_stale=True,
                ),
            ],
        )

        assert ordered[0].candidate_id == "fresh"

    async def test_current_truth_question_penalizes_needs_review_more_strongly(self):
        reranker = HeuristicReranker()
        ordered = await reranker.rerank(
            "What is the current enterprise price?",
            [
                RerankCandidate(
                    candidate_id="needs-review",
                    base_score=2.0,
                    confidence=0.95,
                    authority_weight=0.9,
                    review_status="needs_review",
                    last_verified_at=datetime.now(UTC),
                    source_count=2,
                    is_current=True,
                    is_stale=False,
                ),
                RerankCandidate(
                    candidate_id="approved",
                    base_score=1.9,
                    confidence=0.9,
                    authority_weight=0.85,
                    review_status="approved",
                    last_verified_at=datetime.now(UTC),
                    source_count=1,
                    is_current=True,
                    is_stale=False,
                ),
            ],
        )

        assert ordered[0].candidate_id == "approved"
