import os
import typing
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.future import Engine, create_engine

from alembic import command
from alembic.config import Config
from pat.utils import db
from tests.fixtures.consts import TEST_DB_URL


def _drop_test_db_if_exists(test_db_name: str, recreate: bool = False) -> None:  # noqa: FBT001, FBT002
    db_root_url = os.path.dirname(TEST_DB_URL)  # noqa: PTH120
    normal_db_url = os.path.join(db_root_url, "postgres")  # noqa: PTH118

    normal_engine: Engine = create_engine(
        normal_db_url,
        future=True,
        echo=False,
    )

    with normal_engine.execution_options(autocommit=True, isolation_level="AUTOCOMMIT").connect() as normal_conn:
        normal_conn.execute(text(f"drop database if exists {test_db_name}"))
        if recreate is True:
            normal_conn.execute(text(f"create database {test_db_name} with owner admin"))

    normal_engine.dispose()


def _run_alembic(test_db_url) -> None:
    project_root = Path(__file__).parent.parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))

    test_engine: Engine = create_engine(
        test_db_url,
        future=True,
        echo=False,
    )
    with test_engine.connect() as test_conn:
        alembic_cfg.attributes["connection"] = test_conn
        command.upgrade(alembic_cfg, "head")
    test_engine.dispose()


@pytest.fixture(autouse=True)
async def db_engine() -> typing.AsyncIterable[AsyncEngine]:
    test_db_name = "test_" + str(uuid.uuid4()).replace("-", "")
    _drop_test_db_if_exists(test_db_name=test_db_name, recreate=True)

    db_root_url = os.path.dirname(TEST_DB_URL)  # noqa: PTH120
    test_db_url = os.path.join(db_root_url, test_db_name)  # noqa: PTH118
    _run_alembic(test_db_url)

    async_test_engine = create_async_engine(
        test_db_url,
        future=True,
        echo=True,
    )
    try:
        yield async_test_engine
    finally:
        await async_test_engine.dispose()
        _drop_test_db_if_exists(test_db_name=test_db_name, recreate=False)


@pytest.fixture(autouse=True)
async def async_session_maker_test(
    db_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> typing.AsyncIterator[None]:
    connection = await db_engine.connect()
    transaction = await connection.begin_nested()
    async_session = AsyncSession(
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        bind=connection,
        future=True,
    )

    monkeypatch.setattr(db, "asyncio_engine", db_engine)

    print("BEFORE SESSION")
    yield
    print("AFTER SESSION")

    await async_session.rollback()
    await async_session.close()
    await transaction.rollback()
    await connection.close()
