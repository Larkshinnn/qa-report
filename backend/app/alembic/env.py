import asyncio

from alembic import context
from sqlalchemy import Connection

from app.core import models as core_models  # noqa: F401
from app.core.database import Base, engine
from app.modules.qa_reports import models as qa_models  # noqa: F401


def migrate(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def online() -> None:
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()


asyncio.run(online())
