from __future__ import annotations

from uuid import UUID

from app.evals.regression import build_arg_parser, format_report_payload


class TestRegressionCli:
    def test_parser_accepts_workspace_id(self):
        parser = build_arg_parser()
        args = parser.parse_args(["--workspace-id", "00000000-0000-0000-0000-000000000001"])
        assert args.workspace_id == UUID("00000000-0000-0000-0000-000000000001")

    def test_format_report_payload_handles_failures(self):
        report = format_report_payload(
            {
                "status": "failed",
                "pass_rate": 0.76,
                "passed": 19,
                "total": 25,
                "average_retrieval_hit_quality": 0.79,
                "average_extracted_fact_correctness": 0.81,
                "average_final_answer_correctness": 0.73,
                "confidence_calibration_error": 0.28,
                "failures": [
                    "retrieval 0.79 < 0.80",
                    "answer 0.73 < 0.75",
                ],
            }
        )
        assert "Phase 3B eval regression" in report
        assert "Status: failed" in report
        assert "retrieval 0.79 < 0.80" in report
        assert "answer 0.73 < 0.75" in report
