# ruff: noqa: E501  (fact sentences and labels are benchmark data)
"""HGNS (hypoglossal nerve stimulation) cases: fact sheets, fact sentences and note slots."""

import random
from datetime import date, timedelta

from assent_agents.logic import State
from assent_agents.policy.tree import CriteriaTree
from assent_evals.synth.case import CaseFacts, Obs, d, finish, stmt
from assent_evals.synth.facts import Difficulty, Patient, Statement

LEAVES = ["age", "bmi", "psg", "central", "ahi", "cpap", "dise", "anatomy", "contra"]
FAILABLE = ["bmi", "ahi", "central", "cpap", "dise", "anatomy", "contra", "psg"]
# psg can't be dropped: the PSG report that carries ahi/central dates itself.
DROPPABLE = ["bmi", "central", "ahi", "cpap", "dise", "anatomy", "contra"]
SLOTS = ["pcp", "psg", "sleepmd", "ent"]
TITLES = {
    "pcp": ("Primary Care Progress Note", "Primary care physician"),
    "psg": ("Polysomnography Report", "Sleep medicine physician"),
    "sleepmd": ("Sleep Medicine Consultation", "Sleep medicine physician"),
    "ent": ("Otolaryngology Consultation", "Otolaryngologist"),
}
FILLER = {
    "pcp": [
        "Vitals: BP 128/76, HR 70.",
        "Medications reconciled.",
        "Hyperlipidemia stable on statin.",
    ],
    "psg": [
        "Sleep efficiency 81%.",
        "Lowest oxygen saturation 84%.",
        "Periodic limb movements not significant.",
    ],
    "sleepmd": [
        "Reviewed sleep history and daytime sleepiness.",
        "Epworth Sleepiness Scale 14.",
        "Discussed treatment alternatives.",
    ],
    "ent": [
        "Referred by sleep medicine.",
        "Plan: request prior authorization for hypoglossal nerve stimulator implantation.",
    ],
}
AVOID = {
    "age": "the patient's age",
    "bmi": "weight, BMI or body habitus",
    "psg": "sleep study dates",
    "central": "central or mixed apneas",
    "ahi": "apnea-hypopnea index values",
    "cpap": "CPAP use, tolerance or adherence",
    "dise": "sleep endoscopy findings",
    "anatomy": "tonsils or oropharyngeal anatomy",
    "contra": "neuromuscular, cardiac or pulmonary disease, MRI needs, or ability to use the remote",
}
LOCAL = "http://assent.dev/fhir/obs"  # shortcut: local codes for sleep metrics; map to LOINC later


def make_case(
    rng: random.Random, case_id: str, difficulty: Difficulty, patient: Patient, tree: CriteriaTree
) -> CaseFacts:
    order = date(2026, 9, 1) + timedelta(days=rng.randrange(0, 30))
    gold: dict[str, State] = dict.fromkeys(LEAVES, "met")
    if difficulty in ("clean", "buried") and rng.random() < 0.3:
        gold[rng.choice(FAILABLE)] = "not_met"
    if difficulty in ("missing", "injection"):
        gold[rng.choice(DROPPABLE)] = "insufficient"
    sleepmd = order - timedelta(days=rng.randint(30, 60))
    psg_back = rng.randint(60, 540) if gold["psg"] == "met" else rng.randint(760, 1000)
    f = CaseFacts(
        family="hgns",
        case_id=case_id,
        difficulty=difficulty,
        order_date=order,
        patient=patient,
        condition=rng.choice(["cpap_intolerance", "cpap_intolerance", "cpap_failure"]),
        cpt="64582",
        cpt_text="Implantation of hypoglossal nerve neurostimulator array, pulse generator and respiratory sensor",
        icd10="G47.33",
        icd10_text="Obstructive sleep apnea (adult) (pediatric)",
        dates={
            "pcp": order - timedelta(days=rng.randint(90, 150)),
            "psg": sleepmd - timedelta(days=psg_back),
            "sleepmd": sleepmd,
            "ent": order - timedelta(days=2),
        },
        gold=gold,
    )
    return finish(f, tree, statements, rng)


def statements(f: CaseFacts, rng: random.Random) -> list[Statement]:
    g, buried, out = f.gold, f.difficulty == "buried", []
    age = (
        f.order_date.year
        - f.patient.birth_date.year
        - (
            (f.order_date.month, f.order_date.day)
            < (f.patient.birth_date.month, f.patient.birth_date.day)
        )
    )

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

    sex = "man" if f.patient.sex == "male" else "woman"
    add(
        "age",
        f"{age}-year-old {sex} referred for hypoglossal nerve stimulation evaluation.",
        f"{age}yo {sex[0].upper()} referred for HGNS eval.",
        "ent",
    )

    bmi = round(rng.uniform(24, 34.6) if g["bmi"] == "met" else rng.uniform(35.2, 39.5), 1)
    add("bmi", f"BMI {bmi} kg/m2.", f"Wt stable, BMI {bmi}.", "sleepmd", "pcp")
    if g["bmi"] != "insufficient":
        obs("39156-5", "http://loinc.org", "Body mass index", bmi, "kg/m2", "sleepmd")

    add(
        "psg",
        f"Diagnostic in-laboratory polysomnography performed {d(f.dates['psg'])}.",
        f"Attended PSG {d(f.dates['psg'])}.",
        "psg",
    )

    ahi = round(
        rng.uniform(18, 58)
        if g["ahi"] == "met"
        else rng.choice([rng.uniform(8, 13.9), rng.uniform(68, 84)]),
        1,
    )
    add("ahi", f"Total apnea-hypopnea index (AHI) {ahi} events/hour.", f"AHI {ahi}/h.", "psg")
    if g["ahi"] != "insufficient":
        obs("ahi", LOCAL, "Apnea-hypopnea index", ahi, "/h", "psg")

    central = rng.randint(2, 18) if g["central"] == "met" else rng.randint(28, 45)
    add(
        "central",
        f"Central and mixed apneas comprised {central}% of all events.",
        f"CA+MA {central}% of total AHI.",
        "psg",
    )

    if g["cpap"] == "met" and f.condition == "cpap_failure":
        r, p = round(rng.uniform(17, 30), 1), rng.randint(9, 14)
        add(
            "cpap",
            f"CPAP failure: residual AHI {r} events/hour on CPAP at {p} cmH2O despite consistent nightly use.",
            f"CPAP {p} cmH2O, residual AHI {r} despite nightly use = failure.",
            "sleepmd",
        )
    elif g["cpap"] == "met":
        h, pct = round(rng.uniform(1.0, 3.5), 1), rng.randint(20, 45)
        add(
            "cpap",
            f"CPAP intolerance: download shows average use {h} hours per night on {pct}% of nights despite mask "
            "refitting; shared decision-making with the patient documented that CPAP is not tolerated.",
            f"CPAP dl avg {h} h/night, {pct}% nights despite mask refit; SDM w/ pt: CPAP intolerant.",
            "sleepmd",
        )
    else:
        h, r = round(rng.uniform(6.1, 7.8), 1), round(rng.uniform(2, 4.5), 1)
        add(
            "cpap",
            f"Tolerating CPAP well with average use {h} hours per night and residual AHI {r} events/hour.",
            f"CPAP compliant, avg {h} h/night, residual AHI {r}.",
            "sleepmd",
        )

    dise = f.dates["ent"] - timedelta(days=rng.randint(7, 20))
    if g["dise"] == "met":
        add(
            "dise",
            f"Drug-induced sleep endoscopy {d(dise)}: anteroposterior collapse at the velum without complete "
            "concentric collapse.",
            f"DISE {d(dise)}: AP velum collapse, no CCC.",
            "ent",
        )
    else:
        add(
            "dise",
            f"Drug-induced sleep endoscopy {d(dise)}: complete concentric collapse at the velum.",
            f"DISE {d(dise)}: CCC at velum.",
            "ent",
        )

    add(
        "anatomy",
        "Oropharynx: tonsils size 1, no other anatomic obstruction."
        if g["anatomy"] == "met"
        else "Oropharynx: tonsils size 4, nearly obstructing the airway.",
        "Tonsils 1+, no other obstruction." if g["anatomy"] == "met" else "Tonsils 4+.",
        "ent",
    )

    if g["contra"] == "met":
        add(
            "contra",
            "No neuromuscular disease, hypoglossal palsy, severe cardiopulmonary disease or planned MRI; "
            "able to operate the sleep remote.",
            "No NM dz, no NYHA III/IV CHF, no MRI need, can use remote.",
            "ent",
            "pcp",
        )
    else:
        t = rng.choice(
            [
                "History of myasthenia gravis with bulbar weakness.",
                "NYHA class III heart failure on recent cardiology review.",
            ]
        )
        add("contra", t, t, "ent", "pcp")

    if f.difficulty == "contradictory":
        _contradict(f, out, rng)
    return out


def _contradict(f: CaseFacts, out: list[Statement], rng: random.Random) -> None:
    """Older BMI conflicts with the newest one; the newest (ENT consult) is authoritative."""
    from assent_evals.synth.facts import Statement

    newest_ok = rng.random() < 0.5
    new = round(rng.uniform(30, 34.5) if newest_ok else rng.uniform(35.2, 37.5), 1)
    old = round(rng.uniform(35.5, 38) if newest_ok else rng.uniform(31, 34), 1)
    f.gold["bmi"] = "met" if newest_ok else "not_met"
    f.observations = [o for o in f.observations if o.code != "39156-5"]
    out[:] = [s for s in out if s.leaf != "bmi"]
    out += [
        Statement(
            leaf="bmi",
            gold=f.gold["bmi"],
            slot="ent",
            text=f"Current BMI {new} kg/m2 measured today.",
        ),
        Statement(leaf="bmi", gold=f.gold["bmi"], slot="pcp", stale=True, text=f"BMI {old} kg/m2."),
    ]
