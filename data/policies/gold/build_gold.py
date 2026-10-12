"""Author the HGNS and PVA gold trees: one hand-written shape per family, quotes cut per LCD.

Each quote is (start, end) anchors: the quote is the LCD's own text from `start` (case-insensitive)
through the first `end` after it, so a gold tree can never drift from the verbatim LCD wording.
Run: `uv run python data/policies/gold/build_gold.py` (rewrites the 6 JSON files; review the diff).
ESI trees predate this script and stay hand-written JSON.
"""

# ruff: noqa: E501  (long labels are policy data)
from pathlib import Path
from typing import Any

from assent_agents.policy.ingest import load_snapshot
from assent_agents.policy.tree import CriteriaTree

GOLD = Path(__file__).parent
Q = tuple[str, str | None]


def cut(text: str, q: Q) -> str:
    start, end = q
    i = text.lower().find(start.lower())
    if i < 0:
        raise SystemExit(f"anchor not found: {start!r}")
    j = i + len(start) if end is None else text.find(end, i + len(start)) + len(end)
    if j < i + len(start):
        raise SystemExit(f"end anchor not found after {start!r}: {end!r}")
    return text[i:j]


def leaf(key: str, label: str, et: str, q: Q, **kw: Any) -> dict[str, Any]:
    return {"key": key, "kind": "LEAF", "label": label, "evidence_type": et, "q": q, **kw}


def node(key: str, kind: str, label: str, children: list[Any], q: Q | None = None, **kw: Any):
    return {"key": key, "kind": kind, "label": label, "children": children, "q": q, **kw}


HGNS = node(
    "hgns",
    "AND",
    "Hypoglossal nerve stimulation for moderate to severe OSA is medically reasonable and necessary",
    [
        leaf(
            "age",
            "Beneficiary is 22 years of age or older",
            "assessment",
            ("22 years of age or older", None),
            threshold={"min_years": 22},
        ),
        leaf(
            "bmi",
            "Body mass index under 35 kg/m2",
            "assessment",
            ("Body mass index (BMI) is less than 35", None),
            threshold={"max_exclusive": 35},
        ),
        leaf(
            "psg",
            "Polysomnography within 24 months of the first HGNS consultation",
            "procedure_history",
            ("A polysomnography (PSG) is performed within 24 months", "implant"),
            threshold={"window_months": 24},
        ),
        leaf(
            "central",
            "Predominantly obstructive events: central + mixed apneas under 25% of AHI",
            "assessment",
            ("predominantly obstructive events", "total AHI)"),
            threshold={"max_central_mixed_pct": 25},
        ),
        leaf(
            "ahi",
            "AHI 15 to 65 events per hour",
            "assessment",
            ("AHI is 15 to 65 events per hour", None),
            threshold={"min": 15, "max": 65},
        ),
        leaf(
            "cpap",
            "Documented CPAP failure (AHI > 15 on CPAP) or intolerance (< 4 h/night, 5 nights/wk, or returned), with shared decision making",
            "prior_therapy",
            ("documentation that demonstrates CPAP failure", "sleep expert"),
        ),
        leaf(
            "dise",
            "No complete concentric collapse at the soft palate on drug-induced sleep endoscopy",
            "imaging_finding",
            ("Absence of complete concentric collapse", "(DISE) procedure"),
        ),
        leaf(
            "anatomy",
            "No anatomical findings that would compromise the device (e.g. tonsil size 3 or 4)",
            "assessment",
            ("No other anatomical findings", "grading scale)"),
        ),
        leaf(
            "contra",
            "No contraindication (neuromuscular disease, hypoglossal palsy, severe pulmonary or cardiac disease, NYHA III/IV, recent MI, pregnancy, MRI need, cannot operate remote)",
            "contraindication",
            ("when any of the following contraindications are present", None),
        ),
    ],
    q=(
        "hypoglossal nerve neurostimulation is considered medically reasonable and necessary",
        "criteria are met",
    ),
)
HGNS_EXCLUDED = [
    (
        ("Non-FDA-approved hypoglossal nerve neurostimulation", None),
        "Device attribute on the order, not chart evidence.",
    ),
    (
        ("the inserting provider shall be certified", None),
        "Provider credentialing, not patient chart evidence.",
    ),
    (("must be performed by a qualified physician (MD or DO)", None), "Provider qualification."),
    (
        ("SDM , by definition", None),
        "Defines shared decision making; checked inside the cpap leaf.",
    ),
]

PVA = node(
    "pva",
    "AND",
    "Percutaneous vertebral augmentation for osteoporotic VCF is medically reasonable and necessary",
    [
        node(
            "fx",
            "AND",
            "Acute or subacute osteoporotic VCF confirmed by advanced imaging",
            [
                leaf(
                    "fx.acute",
                    "Osteoporotic VCF (T1-L5), acute (< 6 wk) or subacute (6-12 wk) from symptom onset",
                    "duration",
                    ("Acute (", "osteoporotic VCF"),
                    threshold={"max_weeks": 12},
                ),
                leaf(
                    "fx.imaging",
                    "Advanced imaging shows bone marrow edema on MRI or bone-scan/SPECT/CT uptake",
                    "imaging_finding",
                    ("bone marrow edema on", "uptake"),
                ),
            ],
        ),
        node(
            "sym",
            "OR",
            "Symptomatic",
            [
                leaf(
                    "sym.hosp",
                    "Hospitalized with severe pain (NRS or VAS >= 8)",
                    "assessment",
                    ("hospitalized with severe pain", "8)"),
                    threshold={"min_score": 8},
                ),
                node(
                    "sym.outpt",
                    "AND",
                    "Non-hospitalized: moderate-severe pain despite optimal non-surgical care, and a qualifying course",
                    [
                        leaf(
                            "sym.moderate",
                            "Pain NRS or VAS >= 5 despite optimal non-surgical management",
                            "prior_therapy",
                            ("moderate", "(NSM)"),
                            threshold={"min_score": 5},
                        ),
                        node(
                            "sym.course",
                            "OR",
                            "Worsening pain, or stable pain with two structural/functional features",
                            [
                                leaf(
                                    "sym.worsening",
                                    "Worsening pain",
                                    "assessment",
                                    ("Worsening pain", None),
                                ),
                                node(
                                    "sym.stable",
                                    "N_OF_M",
                                    "At least 2 of: height-loss progression, > 25% height reduction, kyphosis, RDQ > 17",
                                    [
                                        leaf(
                                            "feat.progression",
                                            "Progression of vertebral body height loss",
                                            "imaging_finding",
                                            ("Progression of vertebral body height loss", None),
                                        ),
                                        leaf(
                                            "feat.height",
                                            "More than 25% vertebral body height reduction",
                                            "imaging_finding",
                                            ("25% vertebral body height reduction", None),
                                        ),
                                        leaf(
                                            "feat.kyphosis",
                                            "Kyphotic deformity",
                                            "imaging_finding",
                                            ("Kyphotic deformity", None),
                                        ),
                                        leaf(
                                            "feat.rdq",
                                            "Severe functional impact: Roland Morris Disability Questionnaire > 17",
                                            "assessment",
                                            ("Severe impact of VCF", ">17"),
                                            threshold={"min_exclusive": 17},
                                        ),
                                    ],
                                    q=("Stable", "following"),
                                    n_required=2,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        leaf(
            "care.osteo",
            "Referred for bone density evaluation and osteoporosis treatment program",
            "prior_therapy",
            ("should be referred for evaluation of", "program"),
        ),
        leaf(
            "contra",
            "No absolute contraindication (pain not from the VCF, osteomyelitis/discitis/infection, pregnancy)",
            "contraindication",
            ("Current back pain is not primarily due", "Pregnancy"),
        ),
    ],
)
PVA_ROOT_Q = {
    "L34228": ("PVA (Percutaneous", "following criteria"),
    "L38201": ("PVA (percutaneous", "following criteria"),
    "L35130": ("Both PVP and PVA will be considered", "criteria are met"),
}
PVA_EXCLUDED = [
    (
        ("Relative contraindication", None),
        "Relative contraindications are clinical judgment, not a gate; surfaced by the payer adversary.",
    ),
    (
        ("osteolytic vertebral metasta", "myeloma"),
        "Separate malignant indication; v1 benchmark covers osteoporotic VCF.",
    ),
]


def build(shape: dict[str, Any], text: str, root_q: Q | None = None) -> dict[str, Any]:
    out = {k: v for k, v in shape.items() if k not in ("q", "children")}
    q = root_q or shape["q"]
    if q:
        out["source_quote"] = cut(text, q)
    if shape.get("children"):
        out["children"] = [build(c, text) for c in shape["children"]]
    return out


def main() -> None:
    for sid, ver, shape, excl in [
        ("L38307", 14, HGNS, HGNS_EXCLUDED),
        ("L38310", 11, HGNS, HGNS_EXCLUDED),
        ("L38385", 40, HGNS, HGNS_EXCLUDED),
        ("L34228", 54, PVA, PVA_EXCLUDED),
        ("L38201", 25, PVA, PVA_EXCLUDED),
        ("L35130", 66, PVA, PVA_EXCLUDED),
    ]:
        text = load_snapshot(sid, ver).raw_text
        root = build(shape, text, PVA_ROOT_Q.get(sid))
        excluded = []
        for q, reason in excl:
            try:
                excluded.append({"quote": cut(text, q), "reason": reason})
            except SystemExit:
                pass  # this LCD version doesn't have that passage
        tree = CriteriaTree.model_validate(
            {"source_id": sid, "version": ver, "root": root, "excluded": excluded}
        )
        assert tree.validate_against(text) == [], tree.validate_against(text)
        path = GOLD / f"{sid}-v{ver}.tree.json"
        path.write_text(
            tree.model_dump_json(indent=2, exclude_none=True, exclude_defaults=True) + "\n", "utf-8"
        )
        print(f"{path.name}: {len(tree.leaves())} leaves, {len(excluded)} excluded")


if __name__ == "__main__":
    main()
