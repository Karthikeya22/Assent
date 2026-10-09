import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from assent_api.models import Base
from assent_api.settings import get_settings

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# ALEMBIC_DATABASE_URL lets tests migrate the throwaway test database.
URL = os.environ.get("ALEMBIC_DATABASE_URL") or get_settings().database_url


def _run(conn: Connection) -> None:
    context.configure(connection=conn, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _main() -> None:
    engine = create_async_engine(URL)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


asyncio.run(_main())
