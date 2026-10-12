"""Fit the denial-risk model on dev-split bench runs (BUILD_PLAN §2 Phase 5).

Target: the case would be denied as submitted (gold decision != ready). Features: the ones
`gaps.risk_features` computes. Logistic regression, scored with 5-fold cross-validated
predictions (Brier, AUC, ECE) next to the hand-set prior on the same cases, then fit on all.

Run: `uv run python -m assent_evals.fit_risk data/bench/results/openai-dev-p5.jsonl ...`
Writes packages/agents/src/assent_agents/risk_v1.json, which `gaps.denial_risk` then loads.
"""

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from assent_agents.gaps import FITTED, PRIOR
from assent_evals.synth.build import REPO

FEATURES = list(PRIOR[1])


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error: |mean predicted - observed| weighted over equal-width bins."""
    idx = np.minimum((p * bins).astype(int), bins - 1)
    return float(
        sum(
            abs(p[idx == b].mean() - y[idx == b].mean()) * (idx == b).sum()
            for b in range(bins)
            if (idx == b).any()
        )
        / len(y)
    )


def scores(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    return {
        "brier": round(float(brier_score_loss(y, p)), 4),
        "auc": round(float(roc_auc_score(y, p)), 4),
        "ece": round(ece(y, p), 4),
    }


def main(paths: list[Path]) -> dict[str, Any]:
    recs = [
        json.loads(line)
        for p in paths
        for line in p.read_text("utf-8").splitlines()
        if line.strip()
    ]
    recs = [r for r in recs if "risk_features" in r]
    x = np.array([[r["risk_features"][f] for f in FEATURES] for r in recs])
    y = np.array([r["gold_decision"] != "ready" for r in recs], dtype=int)
    live = [i for i, f in enumerate(FEATURES) if x[:, i].std() > 0]

    model = LogisticRegression(C=1.0)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    p_cv = cross_val_predict(model, x[:, live], y, cv=cv, method="predict_proba")[:, 1]
    bias0, w0 = PRIOR
    p_prior = np.array(
        [
            1
            / (1 + math.exp(-(bias0 + sum(w0[f] * v for f, v in zip(FEATURES, row, strict=True)))))
            for row in x
        ]
    )

    model.fit(x[:, live], y)
    weights = dict(w0)  # features with no variance in the data keep their prior weight
    weights.update(
        {FEATURES[i]: round(float(c), 4) for i, c in zip(live, model.coef_[0], strict=True)}
    )
    out = {
        "bias": round(float(model.intercept_[0]), 4),
        "weights": weights,
        "fitted_on": [
            str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p) for p in paths
        ],
        "n": len(y),
        "positives": int(y.sum()),
        "prior_kept": [f for i, f in enumerate(FEATURES) if i not in live],
        "cv": scores(y, p_cv),
        "prior_same_cases": scores(y, p_prior),
    }
    FITTED.write_text(json.dumps(out, indent=1) + "\n", "utf-8")
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    main([Path(a) for a in sys.argv[1:]])
