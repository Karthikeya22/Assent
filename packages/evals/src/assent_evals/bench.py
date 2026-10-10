"""Run the benchmark (BUILD_PLAN §3) through the real case graph and score it against gold.

Run: `uv run python -m assent_evals.bench --split dev --llm oracle|openai [--limit N]`
`openai` goes through cassettes in data/fixtures/cassettes/<service>, so re-runs are free.
"""

import argparse
import asyncio
import json
import time
from collections import defaultdict
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select

from assent_agents import llm as llm_mod
from assent_agents.case_graph import CaseInput, CaseResult, run_case
from assent_agents.cassette import Cassette
from assent_agents.evidence.agent import CaseContext
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_api.models import Case, Organization, Patient
from assent_evals.metrics import case_accuracy, criterion_scores, percentile
from assent_evals.oracle import make_oracle
from assent_evals.synth.build import BENCH, BUNDLES, GOLD_TREE, REPO
from assent_fhir.source import FileFhirSource

RESULTS = REPO / "data" / "bench" / "results"
CASSETTES = REPO / "data" / "fixtures" / "cassettes" / "esi"


async def _case_row(case_id: str, facts: dict[str, Any]) -> Any:
    """One Patient + Case row per benchmark case, reused across runs (chunks hang off it)."""
    async with SessionLocal() as s:
        fhir_id = f"bench/{case_id}"
        p = await s.scalar(select(Patient).where(Patient.fhir_id == fhir_id))
        if p is None:
            org = await s.scalar(select(Organization).order_by(Organization.name).limit(1))
            if org is None:
                raise SystemExit("no organization; run `python -m assent_api.seed` first")
            p = Patient(
                fhir_id=fhir_id,
                display_name_synthetic=facts["patient"]["name"],
                birth_year=int(facts["patient"]["birth_date"][:4]),
                sex=facts["patient"]["sex"],
            )
            s.add(p)
            await s.flush()
            s.add(
                Case(
                    org_id=org.id,
                    patient_id=p.id,
                    service_family="esi",
                    cpt_codes=[facts["cpt"]],
                    icd10_codes=[facts["icd10"]],
                )
            )
        await s.commit()
        return await s.scalar(select(Case.id).where(Case.patient_id == p.id))


def _citation_stats(res: CaseResult) -> dict[str, int]:
    decided = [
        r.verdict
        for r in res.leaves.values()
        if (r.verdict.original or r.verdict.verdict) != "insufficient"
    ]
    cites = [c for v in decided for c in v.citations]
    return {
        "claims": len(decided),
        "downgraded": sum(v.downgraded is not None for v in decided),
        "citations": len(cites),
        "valid_citations": sum(c.verbatim_ok and (c.support or 0) >= 0.7 for c in cites),
        "verbatim_citations": sum(c.verbatim_ok for c in cites),
    }


async def main(split: str, which: str, limit: int | None) -> dict[str, Any]:
    tree = CriteriaTree.model_validate_json(GOLD_TREE.read_text("utf-8"))
    manifest = [
        m for m in json.loads((BENCH / "manifest.json").read_text("utf-8")) if m["split"] == split
    ][:limit]
    source = FileFhirSource(BUNDLES)
    real = Cassette(CASSETTES, llm_mod.structured, mode="auto") if which == "openai" else None
    leaf_pairs: list[tuple[str, str]] = []
    by_diff: dict[str, list[tuple[str, str]]] = defaultdict(list)
    dec_pairs, latencies, cases = [], [], []
    totals: dict[str, int] = defaultdict(int)
    for m in manifest:
        facts = json.loads((BENCH / f"{m['case_id']}.json").read_text("utf-8"))["facts"]
        case_uuid = await _case_row(m["case_id"], facts)
        inp = CaseInput(
            case_id=case_uuid,
            chart_ref=m["case_id"],
            tree=tree,
            patient_names=[facts["patient"]["name"]],
            ctx=CaseContext(
                order_date=date.fromisoformat(facts["order_date"]),
                service="Epidural steroid injection",
                cpt=facts["cpt"],
                icd10=facts["icd10"],
            ),
        )
        llm = real if real else make_oracle(facts, tree)
        t = time.perf_counter()
        res = await run_case(inp, SessionLocal, source, llm)
        latencies.append(time.perf_counter() - t)
        pred = {k: r.verdict.verdict for k, r in res.leaves.items()}
        pairs = [(facts["gold"][k], pred.get(k, "insufficient")) for k in facts["gold"]]
        leaf_pairs += pairs
        by_diff[m["difficulty"]] += pairs
        decision = "ready" if res.logic.state == "met" else "not_ready"
        dec_pairs.append((facts["decision"], decision))
        stats = _citation_stats(res)
        for k, v in stats.items():
            totals[k] += v
        misses = {
            k: f"{g}->{p}"
            for (k, g), (_, p) in zip(facts["gold"].items(), pairs, strict=True)
            if g != p
        }
        cases.append(
            {
                "case_id": m["case_id"],
                "difficulty": m["difficulty"],
                "gold_decision": facts["decision"],
                "decision": decision,
                "readiness": res.readiness,
                "chunks": res.n_chunks,
                "seconds": round(latencies[-1], 2),
                "misses": misses,
                "downgrades": {
                    k: r.verdict.downgraded for k, r in res.leaves.items() if r.verdict.downgraded
                },
                **stats,
            }
        )
        print(
            f"{m['case_id']} {m['difficulty']:13} gold={facts['decision']:9} "
            f"pred={decision:9} misses={len(misses)} {latencies[-1]:5.1f}s"
        )

    crit = criterion_scores(leaf_pairs)
    report = {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "split": split,
        "llm": which,
        "n_cases": len(cases),
        "criterion_macro_f1": round(crit["macro_f1"], 4),
        "criterion_accuracy": round(crit["accuracy"], 4),
        "case_accuracy": round(case_accuracy(dec_pairs), 4),
        "citation_precision": round(totals["valid_citations"] / totals["citations"], 4)
        if totals["citations"]
        else None,
        "downgrade_rate": round(totals["downgraded"] / totals["claims"], 4)
        if totals["claims"]
        else None,
        "latency_p50_s": round(percentile(latencies, 50), 2),
        "latency_p95_s": round(percentile(latencies, 95), 2),
        "per_difficulty_f1": {
            d: round(criterion_scores(p)["macro_f1"], 4) for d, p in sorted(by_diff.items())
        },
        "confusion": crit["confusion"],
        "cassette": {"hits": real.hits, "misses": real.misses} if real else None,
        "cases": cases,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{which}-{split}.json"
    out.write_text(json.dumps(report, indent=1) + "\n", "utf-8", newline="\n")
    print(
        json.dumps({k: v for k, v in report.items() if k not in ("cases", "confusion")}, indent=1)
    )
    print(f"wrote {out.relative_to(REPO)}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--llm", default="oracle", choices=["oracle", "openai"])
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    asyncio.run(main(a.split, a.llm, a.limit))
