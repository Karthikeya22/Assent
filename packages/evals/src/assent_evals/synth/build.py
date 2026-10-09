"""Build the ESI benchmark: fact sheets + notes (committed) and FHIR bundles (regenerable).

Run: `uv run python -m assent_evals.synth.build --n 50 --seed 7 --notes template|llm`
Needs the Synthea population first: `.\\scripts\\synthea.ps1`.
"""

import argparse
import asyncio
import json
import random
import re
from datetime import date
from pathlib import Path
from typing import Any

from assent_agents import llm as llm_mod
from assent_agents.policy.ingest import POLICY_DIR
from assent_agents.policy.tree import CriteriaTree
from assent_evals.synth import fhir_build
from assent_evals.synth.facts import EsiFacts, Patient, difficulty_plan, make_esi_case
from assent_evals.synth.notes import Note, check_notes, llm_note, slots_for, template_note

REPO = Path(__file__).resolve().parents[5]
SYNTHEA = REPO / ".data" / "synthea" / "fhir"
BENCH = REPO / "data" / "bench" / "esi"  # committed: facts, notes, gold
BUNDLES = REPO / ".data" / "bench" / "esi"  # regenerable: multi-MB FHIR bundles
GOLD_TREE = POLICY_DIR / "gold" / "L39240-v15.tree.json"
AS_OF = date(2026, 9, 1)


def synthea_patients(folder: Path = SYNTHEA) -> list[tuple[Patient, Path]]:
    out = []
    for p in sorted(folder.glob("*.json")):
        bundle = json.loads(p.read_text("utf-8"))
        pt = next(
            (e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Patient"),
            None,
        )
        if pt is None:
            continue
        n = pt["name"][0]
        name = re.sub(r"\d+", "", f"{n['given'][0]} {n['family']}")
        birth = date.fromisoformat(pt["birthDate"])
        if fhir_build.age_on(birth, AS_OF) >= 65:
            out.append(
                (Patient(fhir_id=pt["id"], name=name, sex=pt["gender"], birth_date=birth), p)
            )
    return out


async def build_case(
    case_id: str, seed: int, difficulty: Any, patient: Patient, tree: CriteriaTree, mode: str
) -> tuple[EsiFacts, list[Note]]:
    rng = random.Random(f"{seed}/{case_id}")
    facts = make_esi_case(rng, case_id, difficulty, patient, tree)
    nrng = random.Random(f"{seed}/{case_id}/notes")
    notes = [
        await llm_note(facts, s, nrng, llm_mod.structured)
        if mode == "llm"
        else template_note(facts, s, nrng)
        for s in slots_for(facts)
    ]
    if errs := check_notes(facts, notes):
        raise ValueError(f"{case_id}: {errs}")
    return facts, notes


async def main(n: int, seed: int, mode: str, test_frac: float = 0.32) -> None:
    tree = CriteriaTree.model_validate_json(GOLD_TREE.read_text("utf-8"))
    rng = random.Random(seed)
    pool = synthea_patients()
    if len(pool) < n:
        raise SystemExit(f"need {n} Medicare-age Synthea patients, have {len(pool)}")
    rng.shuffle(pool)
    plan = difficulty_plan(n, rng)
    ids = [f"esi-{i + 1:03d}" for i in range(n)]
    test = set(rng.sample(ids, round(n * test_frac)))
    BENCH.mkdir(parents=True, exist_ok=True)
    BUNDLES.mkdir(parents=True, exist_ok=True)
    manifest = []
    for cid, diff, (patient, src) in zip(ids, plan, pool, strict=False):
        facts, notes = await build_case(cid, seed, diff, patient, tree, mode)
        split = "test" if cid in test else "dev"
        record = {
            "split": split,
            "facts": facts.model_dump(mode="json"),
            "notes": [x.model_dump(mode="json") for x in notes],
        }
        (BENCH / f"{cid}.json").write_text(json.dumps(record, indent=1) + "\n", "utf-8")
        bundle = fhir_build.inject(json.loads(src.read_text("utf-8")), facts, notes)
        (BUNDLES / f"{cid}.bundle.json").write_text(json.dumps(bundle), "utf-8")
        manifest.append(
            {
                "case_id": cid,
                "split": split,
                "difficulty": diff,
                "decision": facts.decision,
                "notes": mode,
            }
        )
        print(f"{cid} {split:4} {diff:13} {facts.condition:11} {facts.decision}")
    (BENCH / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--notes", choices=["template", "llm"], default="llm")
    a = ap.parse_args()
    asyncio.run(main(a.n, a.seed, a.notes))
