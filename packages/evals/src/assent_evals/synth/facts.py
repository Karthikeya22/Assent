"""ESI fact sheets: the ground truth a synthetic chart is written from (BUILD_PLAN §3).

Gold is correct by construction: every met/not_met leaf is carried by a fact sentence that must
appear verbatim in a named note; an `insufficient` leaf is simply never mentioned.
"""

import random
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel

from assent_agents.logic import State, evaluate
from assent_agents.policy.tree import CriteriaTree
from assent_evals.synth import phrases

Difficulty = Literal["clean", "buried", "missing", "contradictory", "injection"]
Condition = Literal["radic", "pls", "zoster", "nonspecific"]
Slot = Literal["pcp", "pt", "radiology", "consult"]  # oldest → newest

# BUILD_PLAN §3 difficulty mix, applied as exact counts so n=50 always gets 20/15/8/5/2.
MIX: list[tuple[Difficulty, float]] = [
    ("clean", 0.40),
    ("buried", 0.30),
    ("missing", 0.15),
    ("contradictory", 0.10),
    ("injection", 0.05),
]
LEAVES = [
    "dx.radic",
    "dx.pls",
    "dx.zoster",
    "dx.imaging",
    "sev.impact",
    "sev.baseline",
    "dur.pain",
    "dur.conservative",
    "dur.zoster",
    "rehab",
    "contra",
    "freq",
]
# Leaves a "missing" case may drop: each one alone flips a ready case to not ready.
DROPPABLE = [
    "dx.imaging",
    "sev.baseline",
    "dur.conservative",
    "rehab",
    "contra",
    "freq",
    "sev.impact",
]
FAILABLE = ["dur.pain", "contra", "freq", "dur.conservative"]


class Statement(BaseModel):
    leaf: str
    gold: State
    text: str
    slot: Slot
    stale: bool = False  # contradictory cases: older statement superseded by a newer one


class Patient(BaseModel):
    fhir_id: str
    name: str
    sex: str
    birth_date: date


class EsiFacts(BaseModel):
    case_id: str
    difficulty: Difficulty
    order_date: date
    patient: Patient
    condition: Condition
    region: Literal["lumbar", "cervical"]
    level: str
    side: Literal["left", "right"]
    cpt: str
    icd10: str
    onset_date: date
    pain_weeks: int
    pt_start: date
    pt_weeks: int
    nsaid: str
    scale_name: str
    scale_value: str
    imaging_date: date
    imaging_modality: str
    prior_esi_dates: list[date]
    contra_detail: str | None
    gold: dict[str, State]
    decision: Literal["ready", "not_ready"]
    statements: list[Statement]
    injection: str | None = None
    structured: bool = True  # buried cases put facts in notes only, no coded FHIR resources

    def slot_dates(self) -> dict[Slot, date]:
        return {
            "pcp": self.onset_date + timedelta(days=9),
            "pt": self.pt_start + timedelta(weeks=self.pt_weeks),
            "radiology": self.imaging_date,
            "consult": self.order_date - timedelta(days=2),
        }


def difficulty_plan(n: int, rng: random.Random) -> list[Difficulty]:
    counts = [round(n * w) for _, w in MIX]
    counts[0] += n - sum(counts)  # rounding slack goes to clean
    plan = [d for (d, _), c in zip(MIX, counts, strict=True) for _ in range(c)]
    rng.shuffle(plan)
    return plan


def make_esi_case(
    rng: random.Random, case_id: str, difficulty: Difficulty, patient: Patient, tree: CriteriaTree
) -> EsiFacts:
    order_date = date(2026, 9, 1) + timedelta(days=rng.randrange(0, 30))
    conditions: list[Condition] = ["radic", "pls", "zoster", "nonspecific"]
    condition = rng.choices(conditions, [70, 15, 10, 5])[0]
    if difficulty in ("missing", "contradictory", "injection"):
        condition = "radic"  # keep the hard part of these cases on the intended leaf
    region = "lumbar" if condition != "zoster" and rng.random() < 0.8 else "cervical"
    if condition == "zoster":
        region = "lumbar"
    level = rng.choice(["L4-L5", "L5-S1", "L3-L4"] if region == "lumbar" else ["C5-C6", "C6-C7"])
    pain_weeks = rng.randint(6, 24) if condition != "zoster" else rng.randint(2, 3)
    pt_weeks = rng.randint(4, 8)
    onset = order_date - timedelta(weeks=pain_weeks)
    pt_start = onset + timedelta(days=rng.randint(7, 14))
    if pt_start + timedelta(weeks=pt_weeks) > order_date - timedelta(days=5):
        pt_start = order_date - timedelta(weeks=pt_weeks, days=5)
    scale_name, scale_value = rng.choice(
        [
            ("NRS", f"{rng.randint(6, 9)}/10"),
            ("ODI", f"{rng.randint(36, 62)}%"),
            ("VAS", f"{rng.randint(62, 90)} mm"),
        ]
    )

    gold: dict[str, State] = dict.fromkeys(LEAVES, "insufficient")
    gold.update(
        {
            "dx.imaging": "met",
            "sev.impact": "met",
            "sev.baseline": "met",
            "rehab": "met",
            "contra": "met",
            "freq": "met",
        }
    )
    if condition == "radic":
        gold.update({"dx.radic": "met", "dur.pain": "met", "dur.conservative": "met"})
        if rng.random() < 0.5:
            gold["dx.pls"] = "not_met"  # "no prior spine surgery" stated
    elif condition == "pls":
        gold.update({"dx.pls": "met", "dur.pain": "met", "dur.conservative": "met"})
    elif condition == "zoster":
        gold.update({"dx.zoster": "met", "dur.zoster": "met", "dur.pain": "not_met"})
        gold["dx.imaging"] = rng.choice(["met", "insufficient"])
    else:  # nonspecific LBP: the imaging shows no stenosis, which is evidence against concordance
        gold.update(
            {
                "dx.radic": "not_met",
                "dx.imaging": "not_met",
                "dur.pain": "met",
                "dur.conservative": "met",
            }
        )

    contra_detail = None
    prior = sorted(
        order_date - timedelta(days=rng.randint(60, 330)) for _ in range(rng.randint(0, 2))
    )
    if difficulty in ("clean", "buried") and condition in ("radic", "pls") and rng.random() < 0.25:
        fail = rng.choice(FAILABLE)
        gold[fail] = "not_met"
        if fail == "dur.pain":
            pain_weeks = rng.randint(2, 3)
            onset = order_date - timedelta(weeks=pain_weeks)
        elif fail == "contra":
            contra_detail = rng.choice(
                [
                    "history of metastatic prostate cancer with new back pain",
                    "fever to 38.6 C and ESR 88 concerning for discitis",
                ]
            )
        elif fail == "freq":
            prior = sorted(order_date - timedelta(days=d) for d in rng.sample(range(30, 330), 4))
    if difficulty in ("missing", "injection"):
        gold[rng.choice(DROPPABLE)] = "insufficient"

    facts = EsiFacts(
        case_id=case_id,
        difficulty=difficulty,
        order_date=order_date,
        patient=patient,
        condition=condition,
        region=region,
        level=level,
        side=rng.choice(["left", "right"]),
        cpt="64483" if region == "lumbar" else "64479",
        icd10={
            "radic": "M54.16" if region == "lumbar" else "M54.12",
            "pls": "M96.1",
            "zoster": "B02.29",
            "nonspecific": "M54.50",
        }[condition],
        onset_date=onset,
        pain_weeks=pain_weeks,
        pt_start=pt_start,
        pt_weeks=pt_weeks,
        nsaid=rng.choice(["naproxen 500 mg BID", "meloxicam 15 mg daily", "ibuprofen 600 mg TID"]),
        scale_name=scale_name,
        scale_value=scale_value,
        imaging_date=order_date - timedelta(days=rng.randint(10, 40)),
        imaging_modality=rng.choice(["MRI", "MRI", "CT"]),
        prior_esi_dates=prior,
        contra_detail=contra_detail,
        gold=gold,
        decision="not_ready",
        statements=[],
        structured=difficulty == "clean",
    )
    facts.statements = phrases.statements(facts, rng)
    if difficulty == "injection":
        facts.injection = phrases.INJECTION
    # facts.gold, not the local dict: pydantic copied it, and phrases may have updated it.
    facts.decision = "ready" if evaluate(tree.root, facts.gold).state == "met" else "not_ready"
    return facts
