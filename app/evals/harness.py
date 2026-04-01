"""Evaluation harness for source-backed startup questions.

Runs gold-set questions against ``QueryService`` and scores three dimensions:
  1. **Retrieval hit quality** — did we find the right components?
  2. **Extracted fact correctness** — did the right source types contribute?
  3. **Final answer correctness** — does the answer contain expected substrings?

``EvalSummary`` exposes per-case results plus per-domain and overall averages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence
from uuid import UUID

from app.evals.metrics import confidence_calibration_error
from app.schemas.query import QueryFilters
from app.services.query_service import QueryService


@dataclass(frozen=True, slots=True)
class EvalCase:
    question: str
    expected_answer_substrings: tuple[str, ...] = ()
    expected_component_names: tuple[str, ...] = ()
    expected_source_types: tuple[str, ...] = ()
    case_id: str = ""
    domain: str = ""


@dataclass(frozen=True, slots=True)
class EvalCaseResult:
    case_id: str
    domain: str
    question: str
    predicted_confidence: float
    retrieval_hit_quality: float
    extracted_fact_correctness: float
    final_answer_correctness: float
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class DomainSummary:
    domain: str
    case_count: int
    avg_retrieval: float
    avg_extraction: float
    avg_answer: float
    pass_rate: float


@dataclass(slots=True)
class EvalSummary:
    cases: list[EvalCaseResult] = field(default_factory=list)
    pass_threshold: float = 0.5
    average_retrieval_hit_quality: float = 0.0
    average_extracted_fact_correctness: float = 0.0
    average_final_answer_correctness: float = 0.0
    confidence_calibration_error: float = 0.0
    domain_summaries: list[DomainSummary] = field(default_factory=list)
    pass_rate: float = 0.0
    total: int = 0
    passed_count: int = 0
    failed_count: int = 0

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0


# Minimum per-metric score for a case to be considered passing.
PASS_THRESHOLD = 0.5


class StartupEvalHarness:
    def __init__(
        self,
        query_service: QueryService,
        *,
        pass_threshold: float = PASS_THRESHOLD,
    ) -> None:
        self.query_service = query_service
        self.pass_threshold = pass_threshold

    async def run(
        self,
        *,
        workspace_id: UUID,
        cases: Sequence[EvalCase],
        filters: QueryFilters | None = None,
    ) -> EvalSummary:
        results: list[EvalCaseResult] = []
        for case in cases:
            response = await self.query_service.query(
                case.question,
                workspace_id,
                filters=filters,
            )
            component_names = {component.name for component in response.components}
            source_types = {source.type for source in response.sources}
            answer_text = response.answer.lower()

            retrieval_score = self._coverage_score(
                component_names,
                case.expected_component_names,
            )
            source_score = self._coverage_score(source_types, case.expected_source_types)
            fact_score = retrieval_score
            if case.expected_source_types:
                fact_score = round((retrieval_score + source_score) / 2.0, 2)

            answer_score = self._answer_score(
                answer_text,
                case.expected_answer_substrings,
            )

            case_passed = (
                retrieval_score >= self.pass_threshold
                and fact_score >= self.pass_threshold
                and answer_score >= self.pass_threshold
            )

            detail_parts: list[str] = []
            if retrieval_score < self.pass_threshold:
                detail_parts.append(
                    f"retrieval={retrieval_score:.2f} (expected {case.expected_component_names}, "
                    f"got {sorted(component_names)})"
                )
            if case.expected_source_types and fact_score < self.pass_threshold:
                detail_parts.append(
                    f"extraction={fact_score:.2f} (expected {case.expected_source_types}, "
                    f"got {sorted(source_types)})"
                )
            if answer_score < self.pass_threshold:
                missing = [
                    s for s in case.expected_answer_substrings
                    if s.lower() not in answer_text
                ]
                detail_parts.append(f"answer missing {missing}")

            results.append(
                EvalCaseResult(
                    case_id=case.case_id,
                    domain=case.domain,
                    question=case.question,
                    predicted_confidence=response.confidence,
                    retrieval_hit_quality=retrieval_score,
                    extracted_fact_correctness=fact_score,
                    final_answer_correctness=answer_score,
                    passed=case_passed,
                    detail="; ".join(detail_parts),
                )
            )

        domain_summaries = self._build_domain_summaries(results)
        passed_count = sum(1 for r in results if r.passed)

        return EvalSummary(
            cases=results,
            pass_threshold=self.pass_threshold,
            average_retrieval_hit_quality=self._average(
                item.retrieval_hit_quality for item in results
            ),
            average_extracted_fact_correctness=self._average(
                item.extracted_fact_correctness for item in results
            ),
            average_final_answer_correctness=self._average(
                item.final_answer_correctness for item in results
            ),
            confidence_calibration_error=confidence_calibration_error(
                [item.predicted_confidence for item in results],
                [item.passed for item in results],
            ),
            domain_summaries=domain_summaries,
            pass_rate=round(passed_count / len(results), 2) if results else 0.0,
            total=len(results),
            passed_count=passed_count,
            failed_count=len(results) - passed_count,
        )

    def _build_domain_summaries(
        self, results: list[EvalCaseResult]
    ) -> list[DomainSummary]:
        by_domain: dict[str, list[EvalCaseResult]] = {}
        for r in results:
            by_domain.setdefault(r.domain or "unknown", []).append(r)

        summaries: list[DomainSummary] = []
        for domain, items in sorted(by_domain.items()):
            passed = sum(1 for i in items if i.passed)
            summaries.append(
                DomainSummary(
                    domain=domain,
                    case_count=len(items),
                    avg_retrieval=self._average(i.retrieval_hit_quality for i in items),
                    avg_extraction=self._average(i.extracted_fact_correctness for i in items),
                    avg_answer=self._average(i.final_answer_correctness for i in items),
                    pass_rate=round(passed / len(items), 2),
                )
            )
        return summaries

    @staticmethod
    def _coverage_score(found: set[str], expected: Sequence[str]) -> float:
        if not expected:
            return 1.0 if found else 0.0
        hits = sum(1 for item in expected if item in found)
        return round(hits / len(expected), 2)

    @staticmethod
    def _answer_score(answer_text: str, expected_substrings: Sequence[str]) -> float:
        if not expected_substrings:
            return 1.0 if answer_text else 0.0
        hits = sum(1 for item in expected_substrings if item.lower() in answer_text)
        return round(hits / len(expected_substrings), 2)

    @staticmethod
    def _average(values) -> float:
        values = list(values)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)
