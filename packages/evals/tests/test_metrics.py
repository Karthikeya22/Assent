import pytest

from assent_evals.metrics import case_accuracy, criterion_scores, percentile


def test_perfect_predictions() -> None:
    pairs = [("met", "met"), ("not_met", "not_met"), ("insufficient", "insufficient")]
    s = criterion_scores(pairs)
    assert s["macro_f1"] == 1.0 and s["accuracy"] == 1.0


def test_hand_computed_macro_f1() -> None:
    # gold: met x3, not_met x1; pred: met, met, insufficient, met
    pairs = [("met", "met"), ("met", "met"), ("met", "insufficient"), ("not_met", "met")]
    s = criterion_scores(pairs)
    # met: P=2/3, R=2/3, F1=2/3. not_met: P=0, R=0, F1=0. insufficient: no gold support, excluded.
    assert s["per_class"]["met"]["f1"] == pytest.approx(2 / 3)
    assert s["macro_f1"] == pytest.approx((2 / 3 + 0) / 2)
    assert s["confusion"]["not_met"]["met"] == 1


def test_case_accuracy_and_percentile() -> None:
    assert case_accuracy([("ready", "ready"), ("ready", "not_ready")]) == 0.5
    assert percentile([5, 1, 3, 2, 4], 50) == 3
    assert percentile([], 95) == 0.0
