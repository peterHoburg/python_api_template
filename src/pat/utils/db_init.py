"""Database initialization utilities.

This module provides functions for initializing and seeding the database.
It includes utilities for:
- Checking if the database exists and creating it if needed
- Applying migrations as part of the initialization process
- Seeding the database with environment-specific data
- Ensuring all operations are idempotent

All functions in this module are designed to be safe to run multiple times,
checking the current state before making changes to avoid duplicates or errors.
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import logfire
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from pat.config import SETTINGS
from pat.utils.db import connection_manager

# Type aliases for seed data
SeedData = dict[str, list[dict[str, Any]]]
SeedFunction = Callable[[], Coroutine[Any, Any, None]]
SeedRegistry = dict[str, SeedFunction]

# Global registry for seed functions
_seed_registry: SeedRegistry = {}


def _raise_error(message: str) -> None:
    """Raise a RuntimeError with the given message.

    This function is used to abstract the raise statement to satisfy linting rules.

    Args:
        message: The error message

    Raises:
        RuntimeError: Always raised with the given message

    """
    raise RuntimeError(message)


async def check_database_exists(database_name: str) -> bool:
    """Check if a database exists.

    Args:
        database_name: The name of the database to check

    Returns:
        bool: True if the database exists, False otherwise

    """
    # Create a connection to the postgres database to check if our target database exists
    uri = str(SETTINGS.postgres_uri)
    postgres_uri = uri.rsplit("/", 1)[0] + "/postgres"

    engine = None
    exists = False
    try:
        # Use a sync engine for simplicity in checking database existence
        engine = create_engine(postgres_uri)
        with engine.connect() as connection:
            # Use parameterized query to prevent SQL injection
            query = text("SELECT 1 FROM pg_database WHERE datname = :database_name")
            result = connection.execute(query, {"database_name": database_name})
            exists = result.scalar() == 1

        logfire.info(f"Database existence check: {database_name}", database=database_name, exists=exists)
    except Exception as e:
        logfire.exception(
            f"Error checking if database exists: {database_name}",
            exception=str(e),
            exception_type=type(e).__name__,
            database=database_name,
        )
        raise
    finally:
        if engine is not None:
            engine.dispose()

    return exists


async def create_database(database_name: str) -> bool:
    """Create a database if it doesn't exist.

    This function is idempotent and will not raise an error if the database already exists.

    Args:
        database_name: The name of the database to create

    Returns:
        bool: True if the database was created, False if it already existed

    """
    # First check if the database already exists
    exists = await check_database_exists(database_name)
    if exists:
        logfire.info(f"Database already exists, skipping creation: {database_name}", database=database_name)
        return False

    # Create a connection to the postgres database to create our target database
    uri = str(SETTINGS.postgres_uri)
    postgres_uri = uri.rsplit("/", 1)[0] + "/postgres"

    engine = None
    created = False
    try:
        # Use a sync engine for simplicity in database creation
        engine = create_engine(postgres_uri)
        with engine.connect() as connection:
            # Disconnect all users to allow database creation
            connection.execute(text("COMMIT"))
            connection.execute(text(f"CREATE DATABASE {database_name}"))

        logfire.info(f"Database created successfully: {database_name}", database=database_name)
        created = True
    except Exception as e:
        logfire.exception(
            f"Error creating database: {database_name}",
            exception=str(e),
            exception_type=type(e).__name__,
            database=database_name,
        )
        raise
    finally:
        if engine is not None:
            engine.dispose()

    return created


async def check_migration_status() -> dict[str, Any]:
    """Check the current migration status.

    Returns:
        Dict[str, Any]: Information about the current migration status

    """
    # Initialize the database connection if not already initialized
    try:
        # Use a public method to check connection health
        await connection_manager.check_health()
    except (SQLAlchemyError, RuntimeError, ConnectionError):
        # If health check fails, initialize the connection
        await connection_manager.initialize()

    # Use a subprocess to run alembic current to get the current revision
    current_process = None
    history_process = None
    status = {}
    try:
        # Run alembic current and capture the output
        current_process = await asyncio.create_subprocess_shell(
            "alembic current", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        current_stdout, current_stderr = await current_process.communicate()

        current_revision = current_stdout.decode().strip()
        if not current_revision or "No current revision" in current_revision:
            current_revision = None

        # Run alembic history to get all revisions
        history_process = await asyncio.create_subprocess_shell(
            "alembic history", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        history_stdout, history_stderr = await history_process.communicate()

        history = history_stdout.decode().strip()
        revisions = [line.split("->")[0].strip() for line in history.split("\n") if line.strip()]

        # Determine if we're at the latest revision
        is_latest = current_revision == revisions[0] if revisions and current_revision else False

        status = {
            "current_revision": current_revision,
            "available_revisions": revisions,
            "is_latest": is_latest,
            "pending_migrations": len(revisions)
            - (revisions.index(current_revision) if current_revision in revisions else len(revisions)),
        }

        logfire.info(
            "Migration status check",
            current_revision=current_revision,
            is_latest=is_latest,
            pending_migrations=status["pending_migrations"],
        )
    except Exception as e:
        logfire.exception("Error checking migration status", exception=str(e), exception_type=type(e).__name__)
        raise

    return status


async def apply_migrations() -> bool:
    """Apply all pending migrations.

    This function is idempotent and will not raise an error if there are no pending migrations.

    Returns:
        bool: True if migrations were applied, False if there were no pending migrations

    """
    # Check the current migration status
    status = await check_migration_status()

    # If we're already at the latest revision, no need to apply migrations
    if status["is_latest"]:
        logfire.info("No pending migrations to apply", current_revision=status["current_revision"])
        return False

    # Apply migrations
    process = None
    migrations_applied = False
    try:
        # Run alembic upgrade head
        process = await asyncio.create_subprocess_shell(
            "alembic upgrade head", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            logfire.error("Error applying migrations", error=error_msg, return_code=process.returncode)

            # Use the helper function to raise the error
            _raise_error("Error applying migrations")

        output = stdout.decode().strip()
        logfire.info("Migrations applied successfully", output=output, previous_revision=status["current_revision"])

        # Check the new migration status
        new_status = await check_migration_status()
        logfire.info(
            "New migration status after applying migrations",
            current_revision=new_status["current_revision"],
            is_latest=new_status["is_latest"],
        )

        migrations_applied = True
    except Exception as e:
        logfire.exception("Error applying migrations", exception=str(e), exception_type=type(e).__name__)
        raise
    finally:
        # No cleanup needed for the subprocess as communicate() already waits for it to complete
        pass

    return migrations_applied


async def initialize_database() -> bool:
    """Initialize the database.

    This function performs the following steps:
    1. Checks if the database exists and creates it if needed
    2. Applies all pending migrations

    This function is idempotent and can be safely run multiple times.

    Returns:
        bool: True if any initialization steps were performed, False if the database was already initialized

    """
    database_name = SETTINGS.postgres_db
    logfire.info(f"Initializing database: {database_name}", database=database_name, environment=SETTINGS.environment)

    # Track if any initialization steps were performed
    initialized = False

    # Step 1: Create the database if it doesn't exist
    created = await create_database(database_name)
    if created:
        initialized = True

    # Step 2: Apply migrations
    migrations_applied = await apply_migrations()
    if migrations_applied:
        initialized = True

    logfire.info(
        f"Database initialization {'performed' if initialized else 'skipped, already initialized'}: {database_name}",
        database=database_name,
        environment=SETTINGS.environment,
        initialized=initialized,
    )

    return initialized


def register_seed_function(environment: str, seed_func: SeedFunction) -> None:
    """Register a seed function for a specific environment.

    Args:
        environment: The environment for which to register the seed function
        seed_func: The seed function to register

    """
    _seed_registry[environment] = seed_func
    logfire.info(f"Registered seed function for environment: {environment}")


async def seed_database() -> bool:
    """Seed the database with environment-specific data.

    This function checks the current environment and calls the appropriate
    seed function if one is registered for that environment.

    This function is idempotent and can be safely run multiple times.

    Returns:
        bool: True if data was seeded, False if no seeding was performed

    """
    environment = SETTINGS.environment
    logfire.info(f"Seeding database for environment: {environment}")

    # Check if there's a seed function registered for this environment
    seed_func = _seed_registry.get(str(environment))
    if not seed_func:
        logfire.info(f"No seed function registered for environment: {environment}, skipping seeding")
        return False

    seeded = False
    try:
        # Call the seed function
        await seed_func()
        logfire.info(f"Database seeded successfully for environment: {environment}")
        seeded = True
    except Exception as e:
        logfire.exception(
            f"Error seeding database for environment: {environment}",
            exception=str(e),
            exception_type=type(e).__name__,
        )
        raise

    return seeded


async def initialize_and_seed_database() -> bool:
    """Initialize and seed the database.

    This function performs the following steps:
    1. Initializes the database (creates it if needed and applies migrations)
    2. Seeds the database with environment-specific data

    This function is idempotent and can be safely run multiple times.

    Returns:
        bool: True if any initialization or seeding steps were performed,
              False if the database was already initialized and seeded

    """
    # Initialize the database
    initialized = await initialize_database()

    # Seed the database
    seeded = await seed_database()

    return initialized or seeded


# Public API
__all__ = [
    "apply_migrations",
    "check_database_exists",
    "check_migration_status",
    "create_database",
    "initialize_and_seed_database",
    "initialize_database",
    "register_seed_function",
    "seed_database",
]
