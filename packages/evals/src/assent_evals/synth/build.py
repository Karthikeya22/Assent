"""Build a family's benchmark: fact sheets + notes (committed) and FHIR bundles (regenerable).

Run: `uv run python -m assent_evals.synth.build --family esi|hgns|pva --n 50 --seed 7 --notes llm`
Needs the Synthea population first: `.\\scripts\\synthea.ps1`.
"""

import argparse
import asyncio
import json
import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from assent_agents import llm as llm_mod
from assent_agents.policy.ingest import POLICY_DIR
from assent_agents.policy.tree import CriteriaTree
from assent_evals.synth import fhir_build, hgns, pva
from assent_evals.synth.case import Facts
from assent_evals.synth.facts import Patient, difficulty_plan, make_esi_case
from assent_evals.synth.notes import Note, check_notes, llm_note, slots_for, template_note

REPO = Path(__file__).resolve().parents[5]
SYNTHEA = REPO / ".data" / "synthea" / "fhir"
BENCH = REPO / "data" / "bench" / "esi"  # committed: facts, notes, gold
BUNDLES = REPO / ".data" / "bench" / "esi"  # regenerable: multi-MB FHIR bundles
GOLD_TREE = POLICY_DIR / "gold" / "L39240-v15.tree.json"
AS_OF = date(2026, 9, 1)


@dataclass(frozen=True)
class Family:
    name: str
    policy: str  # the gold tree the benchmark is labelled against
    service: str  # what the agent is told is being requested
    make: Callable[..., Facts]
    test_frac: float

    @property
    def bench(self) -> Path:
        return REPO / "data" / "bench" / self.name

    @property
    def bundles(self) -> Path:
        return REPO / ".data" / "bench" / self.name

    @property
    def tree(self) -> CriteriaTree:
        return CriteriaTree.model_validate_json(
            (POLICY_DIR / "gold" / f"{self.policy}.tree.json").read_text("utf-8")
        )


FAMILIES = {
    "esi": Family("esi", "L39240-v15", "Epidural steroid injection", make_esi_case, 0.32),
    "hgns": Family(
        "hgns",
        "L38307-v14",
        "Hypoglossal nerve stimulation for obstructive sleep apnea",
        hgns.make_case,
        0.34,
    ),
    "pva": Family(
        "pva",
        "L34228-v54",
        "Percutaneous vertebral augmentation (kyphoplasty)",
        pva.make_case,
        0.34,
    ),
}


def family_of(case_id: str) -> Family:
    return FAMILIES[case_id.split("-")[0]]


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
) -> tuple[Facts, list[Note]]:
    rng = random.Random(f"{seed}/{case_id}")
    facts = family_of(case_id).make(rng, case_id, difficulty, patient, tree)
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


async def main(n: int, seed: int, mode: str, family: str) -> None:
    fam = FAMILIES[family]
    tree, bench, bundles = fam.tree, fam.bench, fam.bundles
    rng = random.Random(seed if family == "esi" else f"{seed}/{family}")
    pool = synthea_patients()
    if len(pool) < n:
        raise SystemExit(f"need {n} Medicare-age Synthea patients, have {len(pool)}")
    rng.shuffle(pool)
    plan = difficulty_plan(n, rng)
    ids = [f"{family}-{i + 1:03d}" for i in range(n)]
    test = set(rng.sample(ids, round(n * fam.test_frac)))
    bench.mkdir(parents=True, exist_ok=True)
    bundles.mkdir(parents=True, exist_ok=True)
    manifest = []
    for cid, diff, (patient, src) in zip(ids, plan, pool, strict=False):
        facts, notes = await build_case(cid, seed, diff, patient, tree, mode)
        split = "test" if cid in test else "dev"
        record = {
            "split": split,
            "facts": facts.model_dump(mode="json"),
            "notes": [x.model_dump(mode="json") for x in notes],
        }
        (bench / f"{cid}.json").write_text(json.dumps(record, indent=1) + "\n", "utf-8")
        bundle = fhir_build.inject(json.loads(src.read_text("utf-8")), facts, notes)
        (bundles / f"{cid}.bundle.json").write_text(json.dumps(bundle), "utf-8")
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
    (bench / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", "utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=FAMILIES, default="esi")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--notes", choices=["template", "llm"], default="llm")
    a = ap.parse_args()
    asyncio.run(main(a.n, a.seed, a.notes, a.family))
