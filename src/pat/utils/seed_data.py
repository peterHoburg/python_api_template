"""Seed data for database initialization.

This module provides seed functions for different environments.
Each seed function is registered with the database initialization
module and will be called when seeding the database for that environment.

Example usage:
    # Register seed functions
    register_seed_function("development", seed_development_data)
    register_seed_function("testing", seed_testing_data)

    # Seed the database
    await seed_database()
"""

import logfire
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pat.config import EnvironmentType
from pat.utils.db import session_context
from pat.utils.db_init import register_seed_function


async def seed_development_data() -> None:
    """Seed data for development environment.

    This function seeds the database with sample data for development.
    It is idempotent and can be safely run multiple times.
    """
    logfire.info("Seeding development data")

    async with session_context() as session:
        # Check if data already exists to ensure idempotence
        if await _check_if_data_exists(session, "development"):
            logfire.info("Development data already exists, skipping seeding")
            return

        # Example: Create sample users
        await session.execute(
            text(
                """
                INSERT INTO users (name, email, created_at)
                VALUES
                ('Admin User', 'admin@example.com', NOW()),
                ('Test User', 'test@example.com', NOW())
                ON CONFLICT DO NOTHING
                """
            )
        )

        # Example: Create sample items
        await session.execute(
            text(
                """
                INSERT INTO items (name, description, owner_id)
                VALUES
                ('Sample Item 1', 'Description for sample item 1', 1),
                ('Sample Item 2', 'Description for sample item 2', 1),
                ('Sample Item 3', 'Description for sample item 3', 2)
                ON CONFLICT DO NOTHING
                """
            )
        )

        await session.commit()
        logfire.info("Development data seeded successfully")


async def seed_testing_data() -> None:
    """Seed data for testing environment.

    This function seeds the database with minimal data for testing.
    It is idempotent and can be safely run multiple times.
    """
    logfire.info("Seeding testing data")

    async with session_context() as session:
        # Check if data already exists to ensure idempotence
        if await _check_if_data_exists(session, "testing"):
            logfire.info("Testing data already exists, skipping seeding")
            return

        # Example: Create test user
        await session.execute(
            text(
                """
                INSERT INTO users (name, email, created_at)
                VALUES ('Test User', 'test@example.com', NOW())
                ON CONFLICT DO NOTHING
                """
            )
        )

        # Example: Create test item
        await session.execute(
            text(
                """
                INSERT INTO items (name, description, owner_id)
                VALUES ('Test Item', 'Description for test item', 1)
                ON CONFLICT DO NOTHING
                """
            )
        )

        await session.commit()
        logfire.info("Testing data seeded successfully")


async def _check_if_data_exists(session: AsyncSession, environment: str) -> bool:
    """Check if seed data already exists for the given environment.

    Args:
        session: The database session
        environment: The environment to check

    Returns:
        bool: True if data exists, False otherwise

    """
    # This is a simplified example. In a real application, you would check
    # for specific records or use a more sophisticated approach.

    # Example: Check if users table has records
    result = await session.execute(text("SELECT COUNT(*) FROM users"))
    user_count = result.scalar()

    if user_count and user_count > 0:
        logfire.info(f"Found existing data for {environment} environment: {user_count} users")
        return True

    return False


# Register seed functions based on environment
def register_environment_seed_functions() -> None:
    """Register seed functions for different environments."""
    register_seed_function(str(EnvironmentType.DEVELOPMENT), seed_development_data)
    register_seed_function(str(EnvironmentType.TESTING), seed_testing_data)
    logfire.info("Registered environment-specific seed functions")


# Register seed functions when module is imported
register_environment_seed_functions()
