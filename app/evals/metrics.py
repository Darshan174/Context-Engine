"""Accuracy metrics — explicit, reviewable scoring functions.

Each function takes ground-truth and predicted sets and returns a float in
[0, 1].  All metrics are deterministic and do not call external services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class PrecisionRecall:
    precision: float
    recall: float
    f1: float


def retrieval_recall(
    expected_names: Sequence[str],
    retrieved_names: Sequence[str],
) -> float:
    """Fraction of expected component names that were retrieved.

    Returns 1.0 when ``expected_names`` is empty and anything was retrieved
    (vacuous truth), 0.0 when nothing expected and nothing retrieved.
    """
    if not expected_names:
        return 1.0 if retrieved_names else 0.0
    expected_set = set(expected_names)
    retrieved_set = set(retrieved_names)
    hits = len(expected_set & retrieved_set)
    return round(hits / len(expected_set), 4)


def retrieval_precision(
    expected_names: Sequence[str],
    retrieved_names: Sequence[str],
) -> float:
    """Fraction of retrieved component names that were expected.

    Measures noise — a high precision means few irrelevant components.
    """
    if not retrieved_names:
        return 1.0 if not expected_names else 0.0
    expected_set = set(expected_names)
    retrieved_set = set(retrieved_names)
    hits = len(expected_set & retrieved_set)
    return round(hits / len(retrieved_set), 4)


def retrieval_precision_recall(
    expected_names: Sequence[str],
    retrieved_names: Sequence[str],
) -> PrecisionRecall:
    """Compute precision, recall, and F1 for retrieval."""
    p = retrieval_precision(expected_names, retrieved_names)
    r = retrieval_recall(expected_names, retrieved_names)
    f1 = 0.0
    if p + r > 0:
        f1 = round(2 * p * r / (p + r), 4)
    return PrecisionRecall(precision=p, recall=r, f1=f1)


def extraction_source_coverage(
    expected_source_types: Sequence[str],
    actual_source_types: Sequence[str],
) -> float:
    """Fraction of expected source types that contributed to the answer.

    Measures whether the extraction pipeline pulled from the right
    connectors (Slack, Notion, Zoom, etc.).
    """
    if not expected_source_types:
        return 1.0 if actual_source_types else 0.0
    expected_set = set(expected_source_types)
    actual_set = set(actual_source_types)
    hits = len(expected_set & actual_set)
    return round(hits / len(expected_set), 4)


def answer_substring_coverage(
    expected_substrings: Sequence[str],
    answer_text: str,
) -> float:
    """Fraction of expected substrings present in the answer (case-insensitive).

    The primary measure of final answer quality — did the answer contain the
    facts that a human reviewer would look for?
    """
    if not expected_substrings:
        return 1.0 if answer_text.strip() else 0.0
    lowered = answer_text.lower()
    hits = sum(1 for s in expected_substrings if s.lower() in lowered)
    return round(hits / len(expected_substrings), 4)


def confidence_calibration_error(
    predicted_confidences: Sequence[float],
    actual_correct: Sequence[bool],
    n_bins: int = 5,
) -> float:
    """Expected Calibration Error (ECE) over equal-width confidence bins.

    Returns a float in [0, 1].  Lower is better.  Measures how well the
    system's confidence scores predict actual correctness.

    For a perfectly calibrated system, facts predicted with 0.8 confidence
    should be correct 80% of the time.
    """
    if not predicted_confidences:
        return 0.0

    bin_sums: list[float] = [0.0] * n_bins
    bin_correct: list[float] = [0.0] * n_bins
    bin_counts: list[int] = [0] * n_bins

    for conf, correct in zip(predicted_confidences, actual_correct):
        idx = min(int(conf * n_bins), n_bins - 1)
        bin_sums[idx] += conf
        bin_correct[idx] += 1.0 if correct else 0.0
        bin_counts[idx] += 1

    total = len(predicted_confidences)
    ece = 0.0
    for i in range(n_bins):
        if bin_counts[i] == 0:
            continue
        avg_conf = bin_sums[i] / bin_counts[i]
        avg_acc = bin_correct[i] / bin_counts[i]
        ece += (bin_counts[i] / total) * abs(avg_acc - avg_conf)

    return round(ece, 4)
