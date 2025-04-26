"""Tests for database migrations."""

from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.future import Connection

from alembic import command
from alembic.config import Config
from tests.fixtures.consts import TEST_DB_HOST, TEST_DB_PASSWORD, TEST_DB_PORT, TEST_DB_USER


def get_alembic_config(connection: Connection | None = None) -> Config:
    """Get Alembic configuration.

    Args:
        connection: Optional database connection to use for migrations

    Returns:
        Config: Alembic configuration
    """
    project_root = Path(__file__).parent.parent.parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))

    if connection is not None:
        alembic_cfg.attributes["connection"] = connection

    return alembic_cfg


def get_test_db_url(db_name: str) -> str:
    """Get a test database URL for a specific database name.

    Args:
        db_name: Name of the test database

    Returns:
        str: Test database URL
    """
    return f"postgresql+psycopg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{db_name}"


def create_test_db(db_name: str) -> None:
    """Create a test database.

    Args:
        db_name: Name of the test database
    """
    # Connect to the postgres database to create/drop other databases
    postgres_url = f"postgresql+psycopg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/postgres"

    normal_engine: Engine = create_engine(
        postgres_url,
        future=True,
        echo=False,
    )

    with normal_engine.execution_options(autocommit=True, isolation_level="AUTOCOMMIT").connect() as normal_conn:
        normal_conn.execute(text(f"drop database if exists {db_name}"))
        normal_conn.execute(text(f"create database {db_name} with owner admin"))

    normal_engine.dispose()


def drop_test_db(db_name: str) -> None:
    """Drop a test database.

    Args:
        db_name: Name of the test database
    """
    # Connect to the postgres database to create/drop other databases
    postgres_url = f"postgresql+psycopg://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/postgres"

    normal_engine: Engine = create_engine(
        postgres_url,
        future=True,
        echo=False,
    )

    with normal_engine.execution_options(autocommit=True, isolation_level="AUTOCOMMIT").connect() as normal_conn:
        normal_conn.execute(text(f"drop database if exists {db_name}"))

    normal_engine.dispose()


def test_migration_upgrade_and_downgrade():
    """Test that migrations can be applied and rolled back."""
    # Create a test database
    test_db_name = "test_migrations"
    test_db_url = get_test_db_url(test_db_name)
    create_test_db(test_db_name)

    try:
        # Create an engine for the test database
        engine = create_engine(test_db_url, future=True, echo=False)

        # Apply migrations
        with engine.connect() as connection:
            alembic_cfg = get_alembic_config(connection)

            # Upgrade to the latest revision
            command.upgrade(alembic_cfg, "head")

            # Verify that the user table exists
            inspector = inspect(engine)
            assert "user" in inspector.get_table_names()

            # Verify that the user table has the expected columns
            columns = inspector.get_columns("user")
            column_names = [col["name"] for col in columns]
            assert "id" in column_names
            assert "first_name" in column_names
            assert "last_name" in column_names
            assert "email" in column_names
            assert "created_at" in column_names
            assert "updated_at" in column_names

            # Downgrade to the base revision
            command.downgrade(alembic_cfg, "base")

            # Verify that the user table no longer exists
            inspector = inspect(engine)
            assert "user" not in inspector.get_table_names()

            # Upgrade again to verify that the migrations can be reapplied
            command.upgrade(alembic_cfg, "head")

            # Verify that the user table exists again
            inspector = inspect(engine)
            assert "user" in inspector.get_table_names()

        engine.dispose()
    finally:
        # Clean up the test database
        drop_test_db(test_db_name)
