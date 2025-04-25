from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import logfire
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from tenacity import retry, stop_after_attempt, wait_fixed

from pat.config import SETTINGS

asyncio_engine = create_async_engine(str(SETTINGS.postgres_uri))


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(asyncio_engine) as session:
        yield session


@asynccontextmanager
async def session_context() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@retry(
    stop=stop_after_attempt(20),
    wait=wait_fixed(1),
)
async def init_con() -> None:
    try:
        async with session_context() as session:
            await session.execute(select(1))
    except Exception:
        logfire.exception("failed to init db con")
        raise
