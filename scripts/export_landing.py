"""Export real recorded data for the landing page (FRONTEND §5.1: "from a recorded run, not lorem").

Writes apps/web/content/agents-run.json (the Phase 4 live review: adversary objections, the
advocate's rebuttals, denial risk) and apps/web/public/evals/latest.json (the eval tables).
Run: `uv run python scripts/export_landing.py`
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from assent_api.db import SessionLocal
from assent_api.models import Case, CriteriaNode, Objection, Patient, Run

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"


async def agents() -> dict:  # type: ignore[type-arg]
    async with SessionLocal() as s:
        row = (
            await s.execute(
                select(Run, Case)
                .join(Case, Case.id == Run.case_id)
                .join(Objection, Objection.run_id == Run.id)
                .order_by(Run.started_at.desc())
                .limit(1)
            )
        ).first()
        if row is None:
            raise SystemExit("no run with objections; run a case with review first")
        run, case = row
        patient = await s.get(Patient, case.patient_id)
        obs = (
            await s.execute(
                select(Objection, CriteriaNode.label)
                .outerjoin(CriteriaNode, CriteriaNode.id == Objection.criterion_id)
                .where(Objection.run_id == run.id)
            )
        ).all()
        return {
            "case": {
                "service": case.service_family,
                "cpt": case.cpt_codes[0],
                "icd10": case.icd10_codes[0],
                "patient": patient.display_name_synthetic if patient else "",
            },
            "denial_risk": case.denial_risk,
            "objections": [
                {
                    "criterion": label or "General",
                    "severity": o.severity,
                    "text": o.text,
                    "status": o.status.value,
                    "rebuttal": o.rebuttal_text or "",
                }
                for o, label in obs
            ],
        }


def evals() -> dict:  # type: ignore[type-arg]
    res = ROOT / "data" / "bench" / "results"
    out = {}
    for split in ("dev", "test"):
        p = res / f"eval-table-{split}.json"
        if p.exists():
            out[split] = json.loads(p.read_text("utf-8"))
    return out


def glassbox() -> dict:  # type: ignore[type-arg]
    """A clean ESI benchmark consult note plus the criterion sentences it contains (gold)."""
    from assent_agents.policy.tree import CriteriaTree

    bench = ROOT / "data" / "bench" / "esi"
    tree = CriteriaTree.model_validate_json(
        (ROOT / "data" / "policies" / "gold" / "L39240-v15.tree.json").read_text("utf-8")
    )
    labels = {n.key: n.label for n in tree.leaves()}
    best = None
    for p in sorted(bench.glob("esi-*.json")):
        rec = json.loads(p.read_text("utf-8"))
        f = rec["facts"]
        if f["difficulty"] != "clean" or rec["split"] != "dev":
            continue
        note = next((n for n in rec["notes"] if n["slot"] == "consult" and n["source"] == "llm"), None)
        if note is None:
            continue
        rows = [
            {"key": st["leaf"], "label": labels[st["leaf"]], "gold": st["gold"], "quote": st["text"]}
            for st in f["statements"]
            if st["slot"] == "consult" and not st["stale"] and st["text"] in note["text"]
        ]
        if best is None or len(rows) > len(best["rows"]):
            best = {"case_id": f["case_id"], "note": note["text"], "rows": rows}
    assert best is not None
    best["rows"] = best["rows"][:5]
    # The amber row: a criterion this note really does not document (it lives in another note).
    shown = {r["key"] for r in best["rows"]}
    gap = next(k for k in ("dur.conservative", "contra", "dx.imaging", "freq") if k not in shown)
    best["missing"] = {"key": gap, "label": labels[gap]}
    return best


def _edges(node, parent=None):  # type: ignore[no-untyped-def]
    yield parent, node
    for c in node.children:
        yield from _edges(c, node)


def main() -> None:
    (WEB / "content").mkdir(exist_ok=True)
    (WEB / "public" / "evals").mkdir(parents=True, exist_ok=True)
    data = asyncio.run(agents())
    (WEB / "content" / "agents-run.json").write_text(json.dumps(data, indent=1) + "\n", "utf-8")
    (WEB / "public" / "evals" / "latest.json").write_text(
        json.dumps(evals(), indent=1) + "\n", "utf-8"
    )
    from assent_agents.policy.tree import CriteriaTree

    tree = CriteriaTree.model_validate_json(
        (ROOT / "data" / "policies" / "gold" / "L39240-v15.tree.json").read_text("utf-8")
    )
    nodes = [
        {"key": c.key, "kind": c.kind, "label": c.label, "parent": p.key if p else None}
        for p, c in _edges(tree.root)
    ]
    lattice = {"policy": f"{tree.source_id}", "nodes": nodes}
    (WEB / "content" / "lattice.json").write_text(json.dumps(lattice, indent=1) + "\n", "utf-8")
    gb = glassbox()
    (WEB / "content" / "glassbox.json").write_text(json.dumps(gb, indent=1) + "\n", "utf-8")
    print(f"{len(data['objections'])} objections, risk {data['denial_risk']}")
    print(f"glass box: {gb['case_id']} with {len(gb['rows'])} criteria")


if __name__ == "__main__":
    main()
