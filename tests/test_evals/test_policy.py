from __future__ import annotations

from app.evals.harness import DomainSummary, EvalSummary
from app.evals.policy import evaluate_exit_criteria


def _summary() -> EvalSummary:
    return EvalSummary(
        pass_threshold=0.5,
        average_retrieval_hit_quality=0.84,
        average_extracted_fact_correctness=0.83,
        average_final_answer_correctness=0.79,
        confidence_calibration_error=0.18,
        domain_summaries=[
            DomainSummary("pricing", 5, 0.9, 0.9, 0.85, 1.0),
            DomainSummary("blocker", 5, 0.8, 0.8, 0.78, 0.8),
            DomainSummary("roadmap", 5, 0.81, 0.82, 0.76, 0.8),
            DomainSummary("decision", 5, 0.83, 0.82, 0.79, 0.8),
            DomainSummary("meeting", 5, 0.84, 0.81, 0.77, 0.8),
        ],
        pass_rate=0.84,
        total=25,
        passed_count=21,
        failed_count=4,
    )


class TestPhase3BPolicy:
    def test_exit_criteria_passes_for_policy_conforming_summary(self):
        assert evaluate_exit_criteria(_summary()) == []

    def test_exit_criteria_flags_metric_and_domain_failures(self):
        summary = _summary()
        summary.average_retrieval_hit_quality = 0.72
        summary.confidence_calibration_error = 0.41
        summary.domain_summaries = summary.domain_summaries[:-1]

        failures = evaluate_exit_criteria(summary)

        assert "missing_domain meeting" in failures
        assert "retrieval 0.72 < 0.80" in failures
        assert "confidence_calibration_error 0.41 > 0.25" in failures
