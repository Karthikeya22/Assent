# ruff: noqa: E501  (fact sentences and labels are benchmark data)
"""PVA (percutaneous vertebral augmentation) cases: fact sheets, fact sentences and note slots.

Three scenarios walk different branches of the tree: hospitalized (sym.hosp), outpatient with
worsening pain, and outpatient stable pain with 2-3 of the 4 structural features (the N_OF_M).
"""

import random
from datetime import date, timedelta

from assent_agents.logic import State
from assent_agents.policy.tree import CriteriaTree
from assent_evals.synth.case import CaseFacts, Obs, d, finish, stmt
from assent_evals.synth.facts import Difficulty, Patient, Statement

FEATURES = ["feat.progression", "feat.height", "feat.kyphosis", "feat.rdq"]
LEAVES = [
    "fx.acute",
    "fx.imaging",
    "sym.hosp",
    "sym.moderate",
    "sym.worsening",
    *FEATURES,
    "care.osteo",
    "contra",
]
DROPPABLE = ["fx.acute", "fx.imaging", "care.osteo", "contra"]
SLOTS = ["pcp", "inpatient", "radiology", "consult"]
TITLES = {
    "pcp": ("Primary Care Progress Note", "Primary care physician"),
    "inpatient": ("Hospital Admission History and Physical", "Hospitalist"),
    "radiology": ("Radiology Report", "Radiologist"),
    "consult": ("Spine Intervention Consultation", "Interventional radiologist"),
}
FILLER = {
    "pcp": [
        "Vitals: BP 126/74, HR 72.",
        "Medications reconciled.",
        "Hyperlipidemia stable on statin.",
    ],
    "inpatient": [
        "Admitted to the medicine service.",
        "Labs reviewed.",
        "Fall precautions ordered.",
    ],
    "radiology": [
        "Technique: multiplanar sequences including STIR.",
        "Comparison: prior studies reviewed.",
    ],
    "consult": [
        "Referred for evaluation of vertebral augmentation.",
        "Medications and allergies reviewed.",
        "Plan: request prior authorization for kyphoplasty.",
    ],
}
AVOID = {
    "fx.acute": "when the back pain started or how long it has lasted",
    "fx.imaging": "MRI, bone scan or CT findings",
    "sym.hosp": "hospital admission or inpatient status",
    "sym.moderate": "non-surgical treatments tried (medications, bracing, therapy)",
    "sym.worsening": "whether the pain is getting better or worse",
    "feat.progression": "change in vertebral height over time",
    "feat.height": "percentage of vertebral height loss",
    "feat.kyphosis": "kyphosis or spinal alignment",
    "feat.rdq": "disability questionnaires or functional scores",
    "care.osteo": "bone density testing or osteoporosis treatment",
    "contra": "fever, infection or other causes of the back pain",
}
LOINC = "http://loinc.org"
LOCAL = (
    "http://assent.dev/fhir/obs"  # shortcut: local codes for RDQ / height loss; map to LOINC later
)
MECHANISM = [
    "lifting a laundry basket",
    "a fall from standing height",
    "bending to pick up a grandchild",
]
MEDS = [
    "acetaminophen and tramadol",
    "acetaminophen and calcitonin nasal spray",
    "oxycodone 5 mg as needed",
]


def make_case(
    rng: random.Random, case_id: str, difficulty: Difficulty, patient: Patient, tree: CriteriaTree
) -> CaseFacts:
    order = date(2026, 9, 1) + timedelta(days=rng.randrange(0, 30))
    scenario = rng.choices(["hosp", "worsening", "stable"], [30, 35, 35])[0]
    gold: dict[str, State] = dict.fromkeys(LEAVES, "insufficient")
    gold.update({"fx.acute": "met", "fx.imaging": "met", "care.osteo": "met", "contra": "met"})
    if scenario == "hosp":
        gold["sym.hosp"] = "met"
    else:
        gold.update({"sym.hosp": "not_met", "sym.moderate": "met"})
        gold["sym.worsening"] = "met" if scenario == "worsening" else "not_met"
        if scenario == "stable":
            for k in rng.sample(FEATURES, rng.choice([2, 2, 3])):
                gold[k] = "met"
    if difficulty in ("clean", "buried") and rng.random() < 0.3:
        options = ["fx.acute", "fx.imaging", "contra"] + (
            ["sym.moderate"] if scenario != "hosp" else []
        )
        if scenario == "stable":
            options.append("one_feature")
        fail = rng.choice(options)
        if fail == "one_feature":  # only one feature documented: the 2-of-4 can't be shown
            for k in [k for k in FEATURES if gold[k] == "met"][1:]:
                gold[k] = "insufficient"
        else:
            gold[fail] = "not_met"
    if difficulty in ("missing", "injection"):
        key = {"hosp": "sym.hosp", "worsening": "sym.worsening", "stable": "fx.imaging"}[scenario]
        gold[rng.choice([*DROPPABLE, key])] = "insufficient"

    weeks = rng.randint(1, 3) if scenario == "hosp" else rng.randint(4, 10)
    if gold["fx.acute"] == "not_met":
        weeks = rng.randint(20, 36)
    onset = order - timedelta(weeks=weeks)
    level = rng.choice(["T11", "T12", "L1", "L2", "L3"])
    f = CaseFacts(
        family="pva",
        case_id=case_id,
        difficulty=difficulty,
        order_date=order,
        patient=patient,
        condition=scenario,
        cpt="22513" if level.startswith("T") else "22514",
        cpt_text=f"Percutaneous vertebral augmentation (kyphoplasty), {'thoracic' if level.startswith('T') else 'lumbar'}",
        icd10="M80.08XA",
        icd10_text="Age-related osteoporosis with current pathological fracture, vertebra(e), initial encounter",
        dates={
            "pcp": onset + timedelta(days=rng.randint(3, 10))
            if scenario != "hosp"
            else onset - timedelta(days=rng.randint(30, 90)),
            "inpatient": order - timedelta(days=rng.randint(2, 5)),
            "radiology": order - timedelta(days=rng.randint(3, 14)),
            "consult": order - timedelta(days=1),
        },
        gold=gold,
    )
    f.dates["onset"] = onset  # not a note slot; keeps the onset with the fact sheet
    f.dates["xray"] = onset + timedelta(days=rng.randint(2, 5))
    f.condition = f"{scenario}:{level}"  # the level rides on condition; statements read it back
    return finish(f, tree, statements, rng)


def statements(f: CaseFacts, rng: random.Random) -> list[Statement]:
    g, buried, out = f.gold, f.difficulty == "buried", []
    scenario, level = f.condition.split(":")
    hosp = scenario == "hosp"
    onset = f.dates["onset"]

    def add(leaf: str, clean: str, short: str, slot: str, bslot: str | None = None) -> None:
        if g[leaf] != "insufficient":
            out.append(
                stmt(f, leaf, short if buried else clean, (bslot or slot) if buried else slot)
            )

    def obs(code: str, system: str, display: str, value: float, unit: str, slot: str) -> None:
        f.observations.append(
            Obs(
                code=code,
                system=system,
                display=display,
                value=value,
                unit=unit,
                date=f.dates[slot],
            )
        )

    weeks = (f.order_date - onset).days // 7
    mech = rng.choice(MECHANISM)
    early = "inpatient" if hosp else "pcp"
    if g["fx.acute"] == "met":
        add(
            "fx.acute",
            f"Back pain began {d(onset)} after {mech}, {weeks} weeks before this visit.",
            f"Back pain since {d(onset)} after {mech}.",
            "consult",
            early,
        )
    else:
        add(
            "fx.acute",
            f"Back pain began {d(onset)} after {mech}, about {weeks // 4} months ago.",
            f"Chronic back pain since {d(onset)}.",
            "consult",
        )

    img = f.dates["radiology"]
    add(
        "fx.imaging",
        f"MRI thoracolumbar spine {d(img)}: acute osteoporotic {level} compression fracture with bone "
        "marrow edema on STIR imaging."
        if g["fx.imaging"] == "met"
        else f"MRI thoracolumbar spine {d(img)}: chronic-appearing {level} compression deformity without bone marrow edema.",
        f"MRI {d(img)}: {level} compression fx, marrow edema on STIR."
        if g["fx.imaging"] == "met"
        else f"MRI {d(img)}: old {level} compression deformity, no marrow edema.",
        "radiology",
    )

    if g["sym.hosp"] == "met":
        n = rng.randint(8, 10)
        add(
            "sym.hosp",
            f"Admitted {d(f.dates['inpatient'])} for intractable back pain, NRS {n}/10 despite IV analgesia.",
            f"Adm {d(f.dates['inpatient'])} intractable back pain, NRS {n}/10 on IV opioids.",
            "inpatient",
        )
        obs("72514-3", LOINC, "Pain severity 0-10 numeric rating", n, "{score}", "inpatient")
    else:
        add(
            "sym.hosp",
            "Seen in the outpatient spine clinic; not hospitalized for this fracture.",
            "Outpt, not admitted.",
            "consult",
        )

    med, nsm_weeks = rng.choice(MEDS), max(2, weeks - 1)
    if g["sym.moderate"] == "met":
        n = rng.randint(5, 8)
        add(
            "sym.moderate",
            f"Pain NRS {n}/10 despite {nsm_weeks} weeks of optimal non-surgical management with {med}, "
            "a thoracolumbar brace and activity modification.",
            f"NRS {n}/10 despite {nsm_weeks} wks NSM ({med}, TLSO brace).",
            "consult",
        )
        obs("72514-3", LOINC, "Pain severity 0-10 numeric rating", n, "{score}", "consult")
    elif g["sym.moderate"] == "not_met":
        n = rng.randint(2, 4)
        add(
            "sym.moderate",
            f"Pain now NRS {n}/10 with {med} and bracing.",
            f"NRS {n}/10 on {med} + brace.",
            "consult",
        )

    add(
        "sym.worsening",
        "Pain has worsened over the past two weeks despite bracing."
        if g["sym.worsening"] == "met"
        else "Pain has been stable to slightly improved since the fracture.",
        "Pain worse x2 wks despite brace."
        if g["sym.worsening"] == "met"
        else "Pain stable/slightly better.",
        "consult",
    )

    t = f"Interval increase in {level} vertebral body height loss compared with radiographs from {d(f.dates['xray'])}."
    add("feat.progression", t, t, "radiology")
    p = rng.randint(30, 48)
    add(
        "feat.height",
        f"Approximately {p}% loss of {level} vertebral body height.",
        f"~{p}% {level} height loss.",
        "radiology",
    )
    if g["feat.height"] != "insufficient":
        obs("vb-height-loss", LOCAL, "Vertebral body height loss", p, "%", "radiology")
    deg = rng.randint(15, 28)
    add(
        "feat.kyphosis",
        f"Focal kyphotic deformity at {level} measuring {deg} degrees.",
        f"Focal kyphosis {level} {deg} deg.",
        "radiology",
    )
    s = rng.randint(18, 23)
    add(
        "feat.rdq",
        f"Roland Morris Disability Questionnaire score {s}/24.",
        f"RDQ {s}/24.",
        "consult",
    )
    if g["feat.rdq"] != "insufficient":
        obs("rdq", LOCAL, "Roland Morris Disability Questionnaire", s, "{score}", "consult")

    add(
        "care.osteo",
        "Referred for DEXA bone density testing and osteoporosis education; enrolled in the osteoporosis "
        "treatment program.",
        "Referred for DEXA + osteoporosis program.",
        "consult",
    )
    if g["contra"] == "met":
        add(
            "contra",
            "Back pain localizes to the fractured level; afebrile with no signs of infection or discitis.",
            "Pain at fx level; afebrile, no infx signs.",
            "consult",
        )
    else:
        t = rng.choice(
            [
                "Fever to 38.9 C with elevated CRP; discitis at the fracture level is suspected.",
                "Back pain is primarily from lumbar spinal stenosis rather than the fracture.",
            ]
        )
        add("contra", t, t, "consult")

    if f.difficulty == "contradictory" and g["fx.acute"] != "insufficient":
        _contradict(f, out, rng, early, mech)
    return out


def _contradict(
    f: CaseFacts, out: list[Statement], rng: random.Random, early: str, mech: str
) -> None:
    """An older note misdates the onset; the newest (consult) note is authoritative."""
    onset = f.dates["onset"]
    if rng.random() < 0.5 or f.gold["fx.acute"] == "not_met":
        out.append(
            Statement(
                leaf="fx.acute",
                gold=f.gold["fx.acute"],
                slot=early,
                stale=True,
                text="Reports back pain for about six months."
                if f.gold["fx.acute"] == "met"
                else "Back pain began two weeks ago.",
            )
        )
    else:
        f.gold["fx.acute"] = "not_met"
        out[:] = [s for s in out if s.leaf != "fx.acute"]
        out += [
            Statement(
                leaf="fx.acute",
                gold="not_met",
                slot="consult",
                text=f"On re-interview, the back pain began about six months ago, long before the {d(onset)} "
                f"episode of {mech}; the earlier history was inaccurate.",
            ),
            Statement(
                leaf="fx.acute",
                gold="not_met",
                slot=early,
                stale=True,
                text=f"Back pain began {d(onset)} after {mech}.",
            ),
        ]
