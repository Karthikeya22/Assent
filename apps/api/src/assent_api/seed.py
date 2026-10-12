"""Idempotent dev seed: one org, one user per role. `uv run python -m assent_api.seed`"""

import asyncio

from sqlalchemy import select

from assent_api.db import SessionLocal
from assent_api.models import Organization, Role, User
from assent_api.security import hash_password

ORG = "Demo Health"
PASSWORD = "assent-dev"  # noqa: S105 (synthetic dev accounts only)


async def main() -> None:
    async with SessionLocal() as s:
        org = await s.scalar(select(Organization).where(Organization.name == ORG))
        if org is None:
            org = Organization(name=ORG)
            s.add(org)
            await s.flush()
        for role in Role:
            email = f"{role.value}@assent.dev"
            if await s.scalar(select(User).where(User.email == email)) is None:
                name = role.value.replace("_", " ").title()
                s.add(
                    User(
                        org_id=org.id,
                        email=email,
                        name=name,
                        role=role,
                        password_hash=hash_password(PASSWORD),
                    )
                )
                print(f"created {email}")
        await s.commit()


if __name__ == "__main__":
    asyncio.run(main())
