"""Collect bench, robustness and risk results into one eval table (JSON for /evals, markdown).

Run: `uv run python -m assent_evals.report [--split dev|test]`
Rows are recomputed from the per-case logs, so a subset comparison (ablations, baselines) is
scored against the full pipeline on exactly the same cases.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from assent_agents.gaps import FITTED
from assent_evals.bench import RESULTS, load_done, summarize
from assent_evals.synth.build import FAMILIES

# The full-pipeline log per (split, family): the latest code's run of each.
FULL = {
    "dev": {
        "esi": "openai-dev-judge-met",
        "hgns": "hgns-openai-dev-v2",
        "pva": "pva-openai-dev-v2",
    },
    "test": {"esi": "openai-test", "hgns": "hgns-openai-test", "pva": "pva-openai-test"},
}
VARIANTS = ["no-verify", "no-rerank", "dense-only", "naive-rag", "long-context"]
KEYS = [
    "n_cases",
    "criterion_macro_f1",
    "case_accuracy",
    "citation_precision",
    "unsupported_claim_rate",
    "latency_p50_s",
    "cost_per_case_usd",
]


def _log(name: str) -> dict[str, dict[str, Any]]:
    return load_done(RESULTS / f"{name}.jsonl")


def _row(recs: list[dict[str, Any]], split: str, label: str) -> dict[str, Any]:
    s = summarize(recs, split, label)
    row = {k: s[k] for k in KEYS}
    row["false_ready"] = sum(r["decision"] == "ready" != r["gold_decision"] for r in recs)
    row["false_not_ready"] = sum(r["decision"] != "ready" == r["gold_decision"] for r in recs)
    return {"system": label, **row}


def variant_name(family: str, split: str, variant: str) -> str:
    base = f"openai-{split}" if family == "esi" else f"{family}-openai-{split}"
    return f"{base}-{variant}"


def build(split: str) -> dict[str, Any]:
    full = {f: _log(FULL[split][f]) for f in FAMILIES}
    table: dict[str, Any] = {"split": split, "per_family": [], "comparison": []}
    every = []
    for f, recs in full.items():
        if recs:
            table["per_family"].append({"family": f, **_row(list(recs.values()), split, f)})
            every += list(recs.values())
    if every:
        table["per_family"].append({"family": "all", **_row(every, split, "all")})

    # Ablations and baselines run on a subset; compare against full on the same case ids.
    subset_full: list[dict[str, Any]] = []
    rows = []
    for v in VARIANTS:
        vrecs = [r for f in FAMILIES for r in _log(variant_name(f, split, v)).values()]
        if not vrecs:
            continue
        rows.append(_row(vrecs, split, v))
        ids = {r["case_id"] for r in vrecs}
        subset_full += [r for f in FAMILIES for cid, r in full[f].items() if cid in ids]
    if rows:
        dedup = list({r["case_id"]: r for r in subset_full}.values())
        table["comparison"] = [_row(dedup, split, "assent (full)"), *rows]

    adv = RESULTS / "adversary-seeded.json"
    if adv.exists():
        a = json.loads(adv.read_text("utf-8"))
        table["adversary"] = {k: v for k, v in a.items() if k != "rows"}
    inj = RESULTS / "injection.json"
    if inj.exists():
        i = json.loads(inj.read_text("utf-8"))
        table["injection"] = {k: v for k, v in i.items() if k != "rows"}
    if FITTED.exists():
        r = json.loads(FITTED.read_text("utf-8"))
        table["risk_model"] = {k: r[k] for k in ("n", "positives", "cv", "prior_same_cases")}
    return table


def markdown(t: dict[str, Any]) -> str:
    def tbl(rows: list[dict[str, Any]], first: str) -> list[str]:
        cols = [first, *KEYS, "false_ready", "false_not_ready"]
        out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        out += ["| " + " | ".join(str(r.get(c, "")) for c in cols) + " |" for r in rows]
        return out

    lines = [f"### Per family ({t['split']})", "", *tbl(t["per_family"], "family"), ""]
    if t["comparison"]:
        lines += ["### Baselines and ablations (same cases)", "", *tbl(t["comparison"], "system")]
    for k in ("adversary", "injection", "risk_model"):
        if k in t:
            lines += ["", f"**{k}**: `{json.dumps(t[k])}`"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    a = ap.parse_args()
    t = build(a.split)
    out: Path = RESULTS / f"eval-table-{a.split}.json"
    out.write_text(json.dumps(t, indent=1) + "\n", "utf-8")
    print(markdown(t))
