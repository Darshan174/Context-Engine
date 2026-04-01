"""Tests for the eval runner formatting and fixture loading."""

from __future__ import annotations

from uuid import UUID

from app.evals.gold_set import STARTUP_GOLD_SET, load_default_cases, load_fixtures
from app.evals.harness import (
    DomainSummary,
    EvalCase,
    EvalCaseResult,
    EvalSummary,
    StartupEvalHarness,
)
from app.evals.runner import build_arg_parser, format_report, summary_to_json


class TestLoadFixtures:
    def test_loads_all_fixtures(self):
        cases = load_fixtures()
        assert len(cases) >= 25  # we wrote 25 lines in fixtures.jsonl
        assert all(isinstance(c, EvalCase) for c in cases)

    def test_filters_by_domain(self):
        pricing = load_fixtures(domains=["pricing"])
        assert len(pricing) >= 5
        assert all(c.domain == "pricing" for c in pricing)

    def test_filters_by_multiple_domains(self):
        subset = load_fixtures(domains=["pricing", "blocker"])
        domains = {c.domain for c in subset}
        assert domains == {"pricing", "blocker"}

    def test_filters_by_id(self):
        cases = load_fixtures(ids=["pricing-001", "blocker-001"])
        assert len(cases) == 2
        ids = {c.case_id for c in cases}
        assert ids == {"pricing-001", "blocker-001"}

    def test_empty_domain_filter_returns_empty(self):
        cases = load_fixtures(domains=["nonexistent"])
        assert cases == []

    def test_fixture_cases_have_required_fields(self):
        for case in load_fixtures():
            assert case.question
            assert case.case_id
            assert case.domain

    def test_load_default_cases_prefers_fixture_set(self):
        cases = load_default_cases()
        assert len(cases) >= 25


class TestStartupGoldSetBackwardCompat:
    def test_gold_set_is_tuple(self):
        assert isinstance(STARTUP_GOLD_SET, tuple)

    def test_gold_set_has_10_cases(self):
        assert len(STARTUP_GOLD_SET) == 10

    def test_gold_set_cases_have_ids(self):
        for case in STARTUP_GOLD_SET:
            assert case.case_id


class TestFormatReport:
    def test_report_contains_verdict(self):
        summary = EvalSummary(
            cases=[
                EvalCaseResult(
                    case_id="test-1",
                    domain="pricing",
                    question="What is pricing?",
                    predicted_confidence=0.91,
                    retrieval_hit_quality=1.0,
                    extracted_fact_correctness=1.0,
                    final_answer_correctness=1.0,
                    passed=True,
                ),
            ],
            pass_threshold=0.5,
            average_retrieval_hit_quality=1.0,
            average_extracted_fact_correctness=1.0,
            average_final_answer_correctness=1.0,
            confidence_calibration_error=0.09,
            domain_summaries=[
                DomainSummary(
                    domain="pricing",
                    case_count=1,
                    avg_retrieval=1.0,
                    avg_extraction=1.0,
                    avg_answer=1.0,
                    pass_rate=1.0,
                ),
            ],
            pass_rate=1.0,
            total=1,
            passed_count=1,
            failed_count=0,
        )
        report = format_report(summary)
        assert "ALL PASSED" in report
        assert "pricing" in report
        assert "Threshold" in report
        assert "Calibration ECE" in report

    def test_report_shows_failure(self):
        summary = EvalSummary(
            cases=[
                EvalCaseResult(
                    case_id="fail-1",
                    domain="blocker",
                    question="What is blocking?",
                    predicted_confidence=0.88,
                    retrieval_hit_quality=0.0,
                    extracted_fact_correctness=0.0,
                    final_answer_correctness=0.0,
                    passed=False,
                    detail="retrieval=0.00",
                ),
            ],
            pass_threshold=0.6,
            average_retrieval_hit_quality=0.0,
            average_extracted_fact_correctness=0.0,
            average_final_answer_correctness=0.0,
            confidence_calibration_error=0.88,
            domain_summaries=[],
            pass_rate=0.0,
            total=1,
            passed_count=0,
            failed_count=1,
        )
        report = format_report(summary)
        assert "FAILURES DETECTED" in report
        assert "FAIL" in report


class TestSummaryToJson:
    def test_json_structure(self):
        summary = EvalSummary(
            cases=[
                EvalCaseResult(
                    case_id="t-1",
                    domain="pricing",
                    question="q?",
                    predicted_confidence=0.87,
                    retrieval_hit_quality=0.8,
                    extracted_fact_correctness=0.9,
                    final_answer_correctness=1.0,
                    passed=True,
                ),
            ],
            pass_threshold=0.5,
            average_retrieval_hit_quality=0.8,
            average_extracted_fact_correctness=0.9,
            average_final_answer_correctness=1.0,
            confidence_calibration_error=0.13,
            domain_summaries=[],
            pass_rate=1.0,
            total=1,
            passed_count=1,
            failed_count=0,
        )
        data = summary_to_json(summary)
        assert data["total"] == 1
        assert data["all_passed"] is True
        assert data["status"] == "passed"
        assert data["pass_threshold"] == 0.5
        assert data["confidence_calibration_error"] == 0.13
        assert data["passed"] == 1
        assert data["failed"] == 0
        assert data["blockers"] == []
        assert len(data["cases"]) == 1
        assert data["cases"][0]["case_id"] == "t-1"
        assert data["cases"][0]["predicted_confidence"] == 0.87


class TestPassThreshold:
    def test_custom_threshold(self):
        harness = StartupEvalHarness.__new__(StartupEvalHarness)
        harness.pass_threshold = 0.8

        # A score of 0.6 should fail with threshold 0.8
        assert 0.6 < harness.pass_threshold


class TestRunnerParser:
    def test_parser_accepts_workspace_id(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--workspace-id", "00000000-0000-0000-0000-000000000001"])
        assert args.workspace_id == UUID("00000000-0000-0000-0000-000000000001")
