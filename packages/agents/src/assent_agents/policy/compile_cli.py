"""Compile an LCD snapshot and score it against its gold tree.

Run: `uv run python -m assent_agents.policy.compile_cli L39240 15`
Writes the draft to data/policies/compiled/<id>-v<ver>.tree.json; a human approves it.
"""

import asyncio
import json
import sys

from assent_agents.policy.compiler import compare_trees, compile_policy
from assent_agents.policy.ingest import POLICY_DIR, load_snapshot
from assent_agents.policy.tree import CriteriaTree


async def main(source_id: str, version: int) -> None:
    snap = load_snapshot(source_id, version)
    res = await compile_policy(snap)
    out = POLICY_DIR / "compiled" / f"{source_id}-v{version}.tree.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(res.tree.model_dump_json(indent=2, exclude_none=True) + "\n", "utf-8")
    print(f"{out.name}: {len(res.tree.leaves())} leaves from {res.samples_ok} samples")
    for d in res.dropped:
        print("  dropped:", d)
    gold = POLICY_DIR / "gold" / f"{source_id}-v{version}.tree.json"
    if gold.exists():
        score = compare_trees(
            CriteriaTree.model_validate_json(gold.read_text("utf-8")), res.tree, snap.raw_text
        )
        print(json.dumps({k: round(v, 3) for k, v in score.items() if k != "pairs"}))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2])))
