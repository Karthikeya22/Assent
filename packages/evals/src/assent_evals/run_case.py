"""Run one benchmark case end to end, persist it, and print the cited verdicts.

Run: `uv run python -m assent_evals.run_case esi-001 [--llm oracle|openai]`
"""

import argparse
import asyncio
import json
from datetime import date

from sqlalchemy import select

from assent_agents import llm as llm_mod
from assent_agents.case_graph import CaseInput, run_case
from assent_agents.cassette import Cassette
from assent_agents.evidence.agent import CaseContext
from assent_api.db import SessionLocal
from assent_api.models import Policy, PolicyVersion
from assent_api.services import runs
from assent_evals.bench import _case_row, cassettes_for
from assent_evals.oracle import make_oracle
from assent_evals.synth.build import family_of
from assent_fhir.source import FileFhirSource

GLYPH = {"met": "✓", "not_met": "✕", "insufficient": "○"}


async def main(case_id: str, which: str) -> None:
    fam = family_of(case_id)
    tree = fam.tree
    facts = json.loads((fam.bench / f"{case_id}.json").read_text("utf-8"))["facts"]
    case_uuid = await _case_row(case_id, facts)
    async with SessionLocal() as s:
        pv_id = await s.scalar(
            select(PolicyVersion.id)
            .join(Policy)
            .where(Policy.source_id == tree.source_id, PolicyVersion.version == str(tree.version))
        )
    if pv_id is None:
        raise SystemExit("policy not loaded; run `python -m assent_api.policy_load` first")
    llm = (
        Cassette(cassettes_for(fam.name), llm_mod.structured)
        if which == "openai"
        else make_oracle(facts, tree)
    )
    inp = CaseInput(
        case_id=case_uuid,
        chart_ref=case_id,
        tree=tree,
        patient_names=[facts["patient"]["name"]],
        ctx=CaseContext(
            order_date=date.fromisoformat(facts["order_date"]),
            service=fam.service,
            cpt=facts["cpt"],
            icd10=facts["icd10"],
        ),
    )
    res = await run_case(inp, SessionLocal, FileFhirSource(fam.bundles), llm)
    async with SessionLocal() as s:
        run = await runs.persist(s, case_uuid, pv_id, res, model=which)
        await s.commit()

    print(f"\n{case_id}  {facts['patient']['name']}  CPT {facts['cpt']}  ICD-10 {facts['icd10']}")
    print(
        f"decision: {res.logic.state}  readiness {res.readiness:.0%}  "
        f"({res.n_chunks} chunks, {res.seconds:.1f}s)  run {run.id}\n"
    )
    for leaf in tree.leaves():
        v = res.leaves[leaf.key].verdict
        gold = facts["gold"][leaf.key]
        mark = "" if gold == v.verdict else f"   (gold: {gold})"
        print(f" {GLYPH[v.verdict]} {leaf.key:17} {v.verdict:12}{mark}")
        for c in v.citations:
            ok = "verified" if c.verbatim_ok and (c.support or 0) >= 0.7 else "rejected"
            print(f"      “{c.quote[:96]}” [{ok}]")
        if v.downgraded:
            print(f"      downgraded: {v.downgraded}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("case_id")
    ap.add_argument("--llm", default="oracle", choices=["oracle", "openai"])
    a = ap.parse_args()
    asyncio.run(main(a.case_id, a.llm))
