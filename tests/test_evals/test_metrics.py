"""Unit tests for app.evals.metrics — pure scoring functions."""

from __future__ import annotations

import pytest

from app.evals.metrics import (
    answer_substring_coverage,
    confidence_calibration_error,
    extraction_source_coverage,
    retrieval_precision,
    retrieval_precision_recall,
    retrieval_recall,
)


class TestRetrievalRecall:
    def test_perfect_recall(self):
        assert retrieval_recall(["A", "B"], ["A", "B", "C"]) == 1.0

    def test_partial_recall(self):
        assert retrieval_recall(["A", "B"], ["A"]) == 0.5

    def test_no_recall(self):
        assert retrieval_recall(["A"], ["B"]) == 0.0

    def test_empty_expected_with_results(self):
        assert retrieval_recall([], ["A"]) == 1.0

    def test_empty_expected_no_results(self):
        assert retrieval_recall([], []) == 0.0

    def test_empty_retrieved(self):
        assert retrieval_recall(["A"], []) == 0.0


class TestRetrievalPrecision:
    def test_perfect_precision(self):
        assert retrieval_precision(["A", "B"], ["A", "B"]) == 1.0

    def test_partial_precision(self):
        assert retrieval_precision(["A"], ["A", "B"]) == 0.5

    def test_no_precision(self):
        assert retrieval_precision(["A"], ["B"]) == 0.0

    def test_empty_retrieved_empty_expected(self):
        assert retrieval_precision([], []) == 1.0

    def test_empty_retrieved_nonempty_expected(self):
        assert retrieval_precision(["A"], []) == 0.0


class TestPrecisionRecall:
    def test_f1_perfect(self):
        pr = retrieval_precision_recall(["A"], ["A"])
        assert pr.precision == 1.0
        assert pr.recall == 1.0
        assert pr.f1 == 1.0

    def test_f1_balanced(self):
        pr = retrieval_precision_recall(["A", "B"], ["A", "C"])
        assert pr.precision == 0.5
        assert pr.recall == 0.5
        assert pr.f1 == 0.5

    def test_f1_zero(self):
        pr = retrieval_precision_recall(["A"], ["B"])
        assert pr.f1 == 0.0


class TestExtractionSourceCoverage:
    def test_full_coverage(self):
        assert extraction_source_coverage(["slack", "notion"], ["slack", "notion", "zoom"]) == 1.0

    def test_partial_coverage(self):
        assert extraction_source_coverage(["slack", "notion"], ["slack"]) == 0.5

    def test_no_coverage(self):
        assert extraction_source_coverage(["gong"], ["slack"]) == 0.0

    def test_empty_expected(self):
        assert extraction_source_coverage([], ["slack"]) == 1.0


class TestAnswerSubstringCoverage:
    def test_all_present(self):
        assert answer_substring_coverage(["$600", "enterprise"], "Enterprise plan is $600/seat") == 1.0

    def test_partial(self):
        assert answer_substring_coverage(["$600", "missing"], "Price is $600") == 0.5

    def test_case_insensitive(self):
        assert answer_substring_coverage(["ENTERPRISE"], "enterprise plan") == 1.0

    def test_empty_substrings_nonempty_answer(self):
        assert answer_substring_coverage([], "some answer") == 1.0

    def test_empty_substrings_empty_answer(self):
        assert answer_substring_coverage([], "  ") == 0.0


class TestConfidenceCalibrationError:
    def test_perfectly_calibrated(self):
        # All predictions at 1.0 confidence and all correct → ECE = 0
        confidences = [1.0, 1.0, 1.0]
        correct = [True, True, True]
        assert confidence_calibration_error(confidences, correct) == 0.0

    def test_completely_miscalibrated(self):
        # All predictions at 1.0 confidence but all wrong
        confidences = [1.0, 1.0, 1.0]
        correct = [False, False, False]
        ece = confidence_calibration_error(confidences, correct)
        assert ece == 1.0

    def test_empty_input(self):
        assert confidence_calibration_error([], []) == 0.0

    def test_mixed_calibration(self):
        confidences = [0.9, 0.9, 0.1, 0.1]
        correct = [True, True, False, False]
        ece = confidence_calibration_error(confidences, correct)
        assert 0.0 <= ece <= 0.2  # well-calibrated
