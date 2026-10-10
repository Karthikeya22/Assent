"""Benchmark metrics (PRODUCT §6, BUILD_PLAN §3). Pure functions over (gold, predicted) pairs."""

from collections import Counter
from collections.abc import Sequence
from typing import Any

LABELS = ("met", "not_met", "insufficient")


def criterion_scores(pairs: Sequence[tuple[str, str]]) -> dict[str, Any]:
    """Macro-F1 over the three verdict labels, plus per-class P/R/F1 and a confusion matrix."""
    conf = Counter(pairs)
    per: dict[str, dict[str, float]] = {}
    for lab in LABELS:
        tp = conf[(lab, lab)]
        pred = sum(v for (g, p), v in conf.items() if p == lab)
        gold = sum(v for (g, p), v in conf.items() if g == lab)
        prec = tp / pred if pred else 0.0
        rec = tp / gold if gold else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per[lab] = {"precision": prec, "recall": rec, "f1": f1, "support": gold}
    present = [lab for lab in LABELS if per[lab]["support"]]  # macro over labels that occur
    macro = sum(per[lab]["f1"] for lab in present) / len(present) if present else 0.0
    return {
        "macro_f1": macro,
        "accuracy": sum(conf[(lab, lab)] for lab in LABELS) / len(pairs) if pairs else 0.0,
        "per_class": per,
        "confusion": {g: {p: conf[(g, p)] for p in LABELS} for g in LABELS},
        "n": len(pairs),
    }


def case_accuracy(pairs: Sequence[tuple[str, str]]) -> float:
    return sum(g == p for g, p in pairs) / len(pairs) if pairs else 0.0


def percentile(xs: Sequence[float], q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    i = min(len(s) - 1, max(0, round(q / 100 * (len(s) - 1))))
    return s[i]
