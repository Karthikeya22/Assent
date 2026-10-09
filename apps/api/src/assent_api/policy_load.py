"""Load every LCD snapshot that has a gold tree into the DB, approved by the seeded policy admin.

Run: `uv run python -m assent_api.policy_load`
"""

import asyncio
import json

from sqlalchemy import select

from assent_agents.policy.ingest import POLICY_DIR, LcdSnapshot
from assent_agents.policy.tree import CriteriaTree
from assent_api.db import SessionLocal
from assent_api.models import Role, User
from assent_api.services import policies

GOLD_DIR = POLICY_DIR / "gold"

SERVICE_FAMILY = {
    **dict.fromkeys(["L39015", "L39240", "L36920"], "esi"),
    **dict.fromkeys(["L38307", "L38310", "L38385"], "hgns"),
    **dict.fromkeys(["L34228", "L38201", "L35130"], "pva"),
}


async def main() -> None:
    async with SessionLocal() as s:
        admin = await s.scalar(select(User).where(User.role == Role.policy_admin).limit(1))
        if admin is None:
            raise SystemExit("no policy_admin user; run `python -m assent_api.seed` first")
        for path in sorted(GOLD_DIR.glob("*.tree.json")):
            tree = CriteriaTree.model_validate_json(path.read_text("utf-8"))
            snap_path = POLICY_DIR / f"{tree.source_id}-v{tree.version}.json"
            snap = LcdSnapshot(**json.loads(snap_path.read_text("utf-8")))
            pv = await policies.upsert_version(
                s, snap, service_family=SERVICE_FAMILY[snap.source_id]
            )
            await policies.replace_tree(s, pv, tree, approved_by=admin.id)
            print(f"{snap.source_id} v{snap.version}: {len(tree.leaves())} leaves, approved")
        await s.commit()


if __name__ == "__main__":
    asyncio.run(main())
