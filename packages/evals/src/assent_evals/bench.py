"""Run the benchmark (BUILD_PLAN §3) through the real case graph and score it against gold.

Run: `uv run python -m assent_evals.bench --family esi|hgns|pva --split dev --llm oracle|openai`
`openai` goes through cassettes in data/fixtures/cassettes/<family>, so re-runs are free.
"""

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from assent_agents import llm as llm_mod
from assent_agents.case_graph import CaseInput, CaseResult, Variant, run_case
from assent_agents.cassette import Cassette
from assent_agents.evidence.agent import CaseContext
from assent_api.db import SessionLocal
from assent_api.models import Case, Organization, Patient
from assent_evals.baselines import BASELINES
from assent_evals.metrics import case_accuracy, criterion_scores, percentile
from assent_evals.oracle import make_oracle
from assent_evals.synth.build import FAMILIES, REPO, family_of
from assent_fhir.source import FileFhirSource

RESULTS = REPO / "data" / "bench" / "results"
CASSETTES = REPO / "data" / "fixtures" / "cassettes" / "esi"


def cassettes_for(family: str) -> Path:
    return REPO / "data" / "fixtures" / "cassettes" / family


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
                    service_family=family_of(case_id).name,
                    cpt_codes=[facts["cpt"]],
                    icd10_codes=[facts["icd10"]],
                )
            )
        await s.commit()
        return await s.scalar(select(Case.id).where(Case.patient_id == p.id))


VARIANTS = {
    "full": Variant(),
    "no-rerank": Variant(rerank=False),
    "dense-only": Variant(hybrid=False),
    "no-verify": Variant(verify=False),
}


def _valid(c: Any) -> bool:
    return bool(c.verbatim_ok and (c.support or 0) >= 0.7)


def _citation_stats(res: CaseResult) -> dict[str, int]:
    decided = [
        r.verdict
        for r in res.leaves.values()
        if (r.verdict.original or r.verdict.verdict) != "insufficient"
    ]
    cites = [c for v in decided for c in v.citations]
    final = [r.verdict for r in res.leaves.values() if r.verdict.verdict != "insufficient"]
    return {
        # a met/not_met that survives with no valid citation: what the verifier exists to stop
        "final_claims": len(final),
        "unsupported": sum(not any(_valid(c) for c in v.citations) for v in final),
        "claims": len(decided),
        "downgraded": sum(v.downgraded is not None for v in decided),
        "citations": len(cites),
        "valid_citations": sum(_valid(c) for c in cites),
        "verbatim_citations": sum(c.verbatim_ok for c in cites),
    }


MIN_FREE_GB = 1.5  # the first case loads embeddings + reranker + NLI (~2 GB) on a 7 GB laptop
MIN_FREE_GB_LOADED = 0.5  # later cases reuse the loaded models


def free_ram_gb() -> float | None:
    """Available physical memory, or None if this platform can't tell us."""
    if sys.platform == "win32":
        import ctypes

        class _Mem(ctypes.Structure):
            _fields_ = [
                ("len", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                *(
                    (n, ctypes.c_ulonglong)
                    for n in ("total", "avail", "pt", "pa", "vt", "va", "ext")
                ),
            ]

        m = _Mem()
        m.len = ctypes.sizeof(_Mem)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return float(m.avail) / 2**30
    try:
        line = next(x for x in open("/proc/meminfo") if x.startswith("MemAvailable"))
        return int(line.split()[1]) / 2**20
    except (OSError, StopIteration):
        return None


def load_done(path: Path) -> dict[str, dict[str, Any]]:
    """Cases already finished in this run's log (one JSON object per line)."""
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text("utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["case_id"]] = rec
    return out


def summarize(records: list[dict[str, Any]], split: str, which: str) -> dict[str, Any]:
    leaf_pairs = [tuple(p) for r in records for p in r["leaf_pairs"]]
    by_diff: dict[str, list[Any]] = defaultdict(list)
    for r in records:
        by_diff[r["difficulty"]] += [tuple(p) for p in r["leaf_pairs"]]
    tot = {
        k: sum(r.get(k, 0) for r in records)  # older logs lack the newer stats
        for k in (
            "claims",
            "downgraded",
            "citations",
            "valid_citations",
            "final_claims",
            "unsupported",
        )
    }
    secs = [r["seconds"] for r in records]
    cost = [r.get("cost_usd", 0.0) for r in records]
    crit = criterion_scores(leaf_pairs)
    return {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "split": split,
        "llm": which,
        "n_cases": len(records),
        "criterion_macro_f1": round(crit["macro_f1"], 4),
        "criterion_accuracy": round(crit["accuracy"], 4),
        "case_accuracy": round(
            case_accuracy([(r["gold_decision"], r["decision"]) for r in records]), 4
        ),
        "citation_precision": round(tot["valid_citations"] / tot["citations"], 4)
        if tot["citations"]
        else None,
        "downgrade_rate": round(tot["downgraded"] / tot["claims"], 4) if tot["claims"] else None,
        "unsupported_claim_rate": round(tot["unsupported"] / tot["final_claims"], 4)
        if tot["final_claims"]
        else None,
        "latency_p50_s": round(percentile(secs, 50), 2),
        "latency_p95_s": round(percentile(secs, 95), 2),
        "cost_per_case_usd": round(sum(cost) / len(cost), 4) if cost else None,
        "per_difficulty_f1": {
            d: round(criterion_scores(p)["macro_f1"], 4) for d, p in sorted(by_diff.items())
        },
        "confusion": crit["confusion"],
        "cases": [{k: v for k, v in r.items() if k != "leaf_pairs"} for r in records],
    }


async def main(
    split: str,
    which: str,
    limit: int | None,
    name: str | None = None,
    family: str = "esi",
    variant: str = "full",
    max_usd: float = 8.0,
) -> dict[str, Any]:
    if variant in BASELINES and which != "openai":
        raise SystemExit(
            "baselines need a real LLM (--llm openai); the oracle only answers the agent"
        )
    fam = FAMILIES[family]
    tree = fam.tree
    manifest = [
        m
        for m in json.loads((fam.bench / "manifest.json").read_text("utf-8"))
        if m["split"] == split
    ][:limit]
    source = FileFhirSource(fam.bundles)
    real = (
        Cassette(cassettes_for(family), llm_mod.structured, mode="auto")
        if which == "openai"
        else None
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    default = f"{which}-{split}" if family == "esi" else f"{family}-{which}-{split}"
    default += "" if variant == "full" else f"-{variant}"
    log_path = RESULTS / f"{name or default}.jsonl"
    done = load_done(log_path)
    if done:
        print(f"resuming {log_path.name}: {len(done)} cases already done")
    ran, start_usd = False, llm_mod.usage["cost_usd"]
    for m in manifest:
        if m["case_id"] in done:
            continue
        if llm_mod.usage["cost_usd"] - start_usd >= max_usd:
            print(f"stopping before {m['case_id']}: spent ${max_usd} this run (--max-usd)")
            break
        free, need = free_ram_gb(), MIN_FREE_GB_LOADED if ran else MIN_FREE_GB
        if free is not None and free < need:
            print(
                f"stopping before {m['case_id']}: only {free:.1f} GB RAM free (need "
                f"{need}). Close browsers/editors and rerun; finished cases are kept."
            )
            break
        facts = json.loads((fam.bench / f"{m['case_id']}.json").read_text("utf-8"))["facts"]
        case_uuid = await _case_row(m["case_id"], facts)
        inp = CaseInput(
            case_id=case_uuid,
            chart_ref=m["case_id"],
            tree=tree,
            patient_names=[facts["patient"]["name"]],
            ctx=CaseContext(
                order_date=date.fromisoformat(facts["order_date"]),
                service=fam.service,
                cpt=facts["cpt"],
                icd10=facts["icd10"],
            ),
        )
        llm = real if real else make_oracle(facts, tree)
        spent = llm_mod.usage["cost_usd"]
        t = time.perf_counter()
        if variant in BASELINES:
            res = await BASELINES[variant](inp, SessionLocal, source, llm)
        else:
            res = await run_case(inp, SessionLocal, source, llm, variant=VARIANTS[variant])
        seconds = time.perf_counter() - t
        pred = {k: r.verdict.verdict for k, r in res.leaves.items()}
        pairs = [(facts["gold"][k], pred.get(k, "insufficient")) for k in facts["gold"]]
        decision = "ready" if res.logic.state == "met" else "not_ready"
        rec = {
            "case_id": m["case_id"],
            "difficulty": m["difficulty"],
            "gold_decision": facts["decision"],
            "decision": decision,
            "readiness": res.readiness,
            "chunks": res.n_chunks,
            "seconds": round(seconds, 2),
            "cost_usd": round(llm_mod.usage["cost_usd"] - spent, 5),
            "misses": {
                k: f"{g}->{p}" for k, (g, p) in zip(facts["gold"], pairs, strict=True) if g != p
            },
            "downgrades": {
                k: r.verdict.downgraded for k, r in res.leaves.items() if r.verdict.downgraded
            },
            "leaf_pairs": pairs,
            **_citation_stats(res),
        }
        with log_path.open("a", encoding="utf-8", newline="\n") as f:  # durable per case
            f.write(json.dumps(rec) + "\n")
        done[m["case_id"]] = rec
        ran = True
        print(
            f"{m['case_id']} {m['difficulty']:13} gold={facts['decision']:9} "
            f"pred={decision:9} misses={len(rec['misses'])} {seconds:5.1f}s "
            f"${rec['cost_usd']:.4f}"
        )

    ids = [m["case_id"] for m in manifest]
    report = summarize([done[i] for i in ids if i in done], split, which)
    report["family"], report["variant"] = family, variant
    report["complete"] = all(i in done for i in ids)
    if real:
        report["cassette"] = {"hits": real.hits, "misses": real.misses}
    out = log_path.with_suffix(".json")
    out.write_text(json.dumps(report, indent=1) + "\n", "utf-8", newline="\n")
    print(
        json.dumps({k: v for k, v in report.items() if k not in ("cases", "confusion")}, indent=1)
    )
    print(f"wrote {out.relative_to(REPO)}")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default="esi", choices=FAMILIES)
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--variant", default="full", choices=[*VARIANTS, *BASELINES])
    ap.add_argument(
        "--max-usd", type=float, default=8.0, help="stop starting cases past this spend"
    )
    ap.add_argument("--llm", default="oracle", choices=["oracle", "openai"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--name", help="run log name (resume by reusing it); default <llm>-<split>")
    a = ap.parse_args()
    asyncio.run(main(a.split, a.llm, a.limit, a.name, a.family, a.variant, a.max_usd))
