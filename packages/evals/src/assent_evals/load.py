"""Load benchmark cases into eval_cases (replacing that service family's rows).

Run: `uv run python -m assent_evals.load esi|hgns|pva|all`
"""

import asyncio
import json
import sys

from sqlalchemy import delete

from assent_api.db import SessionLocal
from assent_api.models import EvalCase, Split
from assent_evals.synth.build import FAMILIES


async def main(service: str) -> None:
    root = FAMILIES[service].bench
    manifest = json.loads((root / "manifest.json").read_text("utf-8"))
    async with SessionLocal() as s:
        await s.execute(delete(EvalCase).where(EvalCase.service_family == service))
        for m in manifest:
            f = json.loads((root / f"{m['case_id']}.json").read_text("utf-8"))["facts"]
            s.add(
                EvalCase(
                    service_family=service,
                    split=Split(m["split"]),
                    seeded_defects_json=None,
                    gold_json={
                        "case_id": f["case_id"],
                        "gold": f["gold"],
                        "decision": f["decision"],
                        "difficulty": f["difficulty"],
                        "condition": f["condition"],
                        "policy": FAMILIES[service].policy.split("-")[0],
                    },
                )
            )
        await s.commit()
    print(f"{len(manifest)} {service} eval cases loaded")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "esi"
    for fam in FAMILIES if arg == "all" else [arg]:
        asyncio.run(main(fam))
