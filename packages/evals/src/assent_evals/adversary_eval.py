"""Seeded-defect packets: does the payer adversary catch a planted weakness? (BUILD_PLAN §3)

Each packet is a gold-perfect "ready" case with exactly one met criterion corrupted:
- weak:  its only quote is irrelevant boilerplate from the chart
- wrong: its quote is real evidence, but for a different criterion
- none:  met with a rationale and no quote at all
Clean packets (no defect) measure how often the adversary objects anyway.

Run: `uv run python -m assent_evals.adversary_eval --per-family 20 --controls 5`
The adversary goes through cassettes in data/fixtures/cassettes/adversary, so re-runs are free.
"""

import argparse
import asyncio
import json
import random
from collections import Counter
from typing import Any

from assent_agents import llm as llm_mod
from assent_agents.adversary import run_adversary
from assent_agents.cassette import Cassette
from assent_agents.evidence.models import Citation, Verdict
from assent_evals.synth.build import FAMILIES, REPO
from assent_evals.synth.notes import SPECS

DEFECTS = ["weak", "wrong", "none"]
OUT = REPO / "data" / "bench" / "results"


def gold_verdicts(facts: dict[str, Any]) -> dict[str, Verdict]:
    """Verdicts exactly as gold, each met/not_met citing its own (current) fact sentence."""
    out = {}
    for key, g in facts["gold"].items():
        quotes = [s["text"] for s in facts["statements"] if s["leaf"] == key and not s["stale"]]
        out[key] = Verdict(
            criterion_key=key,
            verdict=g,
            confidence=0.9 if g != "insufficient" else 0.3,
            rationale="Supported by the cited chart text."
            if g != "insufficient"
            else "Not documented.",
            citations=[
                Citation(chunk_id="x", quote=q, claim=q, verbatim_ok=True, support=0.95)
                for q in quotes
            ],
        )
    return out


def seed(
    facts: dict[str, Any], family: str, defect: str, rng: random.Random
) -> tuple[dict[str, Verdict], str]:
    verdicts = gold_verdicts(facts)
    met = [k for k, v in verdicts.items() if v.verdict == "met" and v.citations]
    key = rng.choice(met)
    v = verdicts[key]
    if defect == "weak":
        boiler = rng.choice([s for lines in SPECS[family][2].values() for s in lines])
        cites = [Citation(chunk_id="x", quote=boiler, claim=boiler, verbatim_ok=True, support=0.95)]
    elif defect == "wrong":
        other = rng.choice([k for k in met if k != key])
        cites = verdicts[other].citations
    else:
        cites = []
    verdicts[key] = v.model_copy(update={"citations": cites})
    return verdicts, key


async def main(per_family: int, controls: int) -> dict[str, Any]:
    llm = Cassette(REPO / "data" / "fixtures" / "cassettes" / "adversary", llm_mod.structured)
    rows = []
    for name, fam in FAMILIES.items():
        rng = random.Random(f"adversary/{name}")
        manifest = json.loads((fam.bench / "manifest.json").read_text("utf-8"))
        ready = [m["case_id"] for m in manifest if m["split"] == "dev" and m["decision"] == "ready"]
        tree = fam.tree
        plan = [(cid, DEFECTS[i % 3]) for i, cid in enumerate(rng.choices(ready, k=per_family))]
        plan += [(cid, "control") for cid in rng.sample(ready, min(controls, len(ready)))]
        for cid, defect in plan:
            facts = json.loads((fam.bench / f"{cid}.json").read_text("utf-8"))["facts"]
            if defect == "control":
                verdicts, key = gold_verdicts(facts), None
            else:
                verdicts, key = seed(facts, name, defect, rng)
            obs = await run_adversary(tree, verdicts, "ready", llm)
            hit = {o.criterion_key for o in obs}
            rows.append(
                {
                    "family": name,
                    "case_id": cid,
                    "defect": defect,
                    "seeded_key": key,
                    "objected": sorted(hit),
                    "caught": key in hit if key else None,
                    "caught_high": any(o.criterion_key == key and o.severity == "high" for o in obs)
                    if key
                    else None,
                    "n_objections": len(obs),
                }
            )
            print(f"{name} {cid} {defect:7} key={key} objected={sorted(hit)}")
    seeded = [r for r in rows if r["defect"] != "control"]
    ctrl = [r for r in rows if r["defect"] == "control"]
    by_type = Counter(r["defect"] for r in seeded)
    caught = Counter(r["defect"] for r in seeded if r["caught"])
    report = {
        "n_seeded": len(seeded),
        "catch_rate": round(sum(r["caught"] for r in seeded) / len(seeded), 4),
        "catch_rate_high": round(sum(r["caught_high"] for r in seeded) / len(seeded), 4),
        "catch_rate_by_defect": {d: round(caught[d] / n, 4) for d, n in sorted(by_type.items())},
        "catch_rate_by_family": {
            f: round(
                sum(r["caught"] for r in seeded if r["family"] == f)
                / max(1, sum(r["family"] == f for r in seeded)),
                4,
            )
            for f in FAMILIES
        },
        "n_controls": len(ctrl),
        "objections_per_clean_packet": round(sum(r["n_objections"] for r in ctrl) / len(ctrl), 3)
        if ctrl
        else None,
        "cassette": {"hits": llm.hits, "misses": llm.misses},
        "cost_usd": round(llm_mod.usage["cost_usd"], 4),
        "rows": rows,
    }
    (OUT / "adversary-seeded.json").write_text(json.dumps(report, indent=1) + "\n", "utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=1))
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-family", type=int, default=20)
    ap.add_argument("--controls", type=int, default=5)
    a = ap.parse_args()
    asyncio.run(main(a.per_family, a.controls))
