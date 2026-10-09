"""Load benchmark cases into eval_cases (replacing that service family's rows).

Run: `uv run python -m assent_evals.load esi`
"""

import asyncio
import json
import sys

from sqlalchemy import delete

from assent_api.db import SessionLocal
from assent_api.models import EvalCase, Split
from assent_evals.synth.build import REPO


async def main(service: str) -> None:
    root = REPO / "data" / "bench" / service
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
                        "policy": "L39240",
                    },
                )
            )
        await s.commit()
    print(f"{len(manifest)} {service} eval cases loaded")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "esi"))
