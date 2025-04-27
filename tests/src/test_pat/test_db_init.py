"""Tests for database initialization utilities."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pat.config import EnvironmentType
from pat.utils.db_init import (
    _raise_error,
    apply_migrations,
    check_database_exists,
    check_migration_status,
    create_database,
    initialize_and_seed_database,
    initialize_database,
    register_seed_function,
    seed_database,
)

# Constants for test values
DB_OPERATIONS_COUNT = 2  # COMMIT and CREATE DATABASE
SUBPROCESS_CALLS_COUNT = 2  # alembic current and alembic history
MIGRATION_STATUS_CHECKS_COUNT = 2  # Before and after applying migrations
PENDING_MIGRATIONS_COUNT = 2  # Number of pending migrations in test


@pytest.mark.asyncio
async def test_check_database_exists():
    """Test the check_database_exists function."""
    # Mock the create_engine and connection.execute functions
    with patch("pat.utils.db_init.create_engine") as mock_create_engine:
        # Set up the mock to return a value for scalar()
        mock_connection = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1  # Database exists
        mock_connection.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        # Call the function
        result = await check_database_exists("test_db")

        # Verify the result
        assert result is True
        mock_create_engine.assert_called_once()
        mock_connection.execute.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_check_database_not_exists():
    """Test the check_database_exists function when the database doesn't exist."""
    # Mock the create_engine and connection.execute functions
    with patch("pat.utils.db_init.create_engine") as mock_create_engine:
        # Set up the mock to return a value for scalar()
        mock_connection = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # Database doesn't exist
        mock_connection.execute.return_value = mock_result
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        # Call the function
        result = await check_database_exists("test_db")

        # Verify the result
        assert result is False
        mock_create_engine.assert_called_once()
        mock_connection.execute.assert_called_once()
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_create_database_when_not_exists():
    """Test the create_database function when the database doesn't exist."""
    # Mock the check_database_exists and create_engine functions
    with (
        patch("pat.utils.db_init.check_database_exists") as mock_check_db,
        patch("pat.utils.db_init.create_engine") as mock_create_engine,
    ):
        # Set up the mocks
        mock_check_db.return_value = False  # Database doesn't exist
        mock_connection = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        # Call the function
        result = await create_database("test_db")

        # Verify the result
        assert result is True
        mock_check_db.assert_called_once_with("test_db")
        mock_create_engine.assert_called_once()
        assert mock_connection.execute.call_count == DB_OPERATIONS_COUNT  # COMMIT and CREATE DATABASE
        mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_create_database_when_exists():
    """Test the create_database function when the database already exists."""
    # Mock the check_database_exists function
    with patch("pat.utils.db_init.check_database_exists") as mock_check_db:
        # Set up the mock
        mock_check_db.return_value = True  # Database exists

        # Call the function
        result = await create_database("test_db")

        # Verify the result
        assert result is False
        mock_check_db.assert_called_once_with("test_db")


@pytest.mark.asyncio
async def test_check_migration_status():
    """Test the check_migration_status function."""
    # Mock the connection_manager and asyncio.create_subprocess_shell functions
    with (
        patch("pat.utils.db_init.connection_manager") as mock_conn_manager,
        patch("asyncio.create_subprocess_shell") as mock_create_subprocess,
    ):
        # Set up the mocks
        mock_conn_manager.check_health = AsyncMock()

        # Mock the subprocess for alembic current
        mock_current_process = AsyncMock()
        mock_current_process.communicate = AsyncMock(
            # Use the exact same format for current_revision as the first revision in history
            return_value=(b"1234abcd\n", b"")
        )

        # Mock the subprocess for alembic history
        mock_history_process = AsyncMock()
        mock_history_process.communicate = AsyncMock(
            return_value=(b"1234abcd -> 5678efgh (head)\n9876zyxw -> 1234abcd\n", b"")
        )

        # Set up the mock to return different values for each call
        mock_create_subprocess.side_effect = [mock_current_process, mock_history_process]

        # Call the function
        result = await check_migration_status()

        # Verify the result
        assert result["current_revision"] == "1234abcd"
        assert result["available_revisions"] == ["1234abcd", "9876zyxw"]
        assert result["is_latest"] is True
        # pending_migrations is calculated as len(revisions) - revisions.index(current_revision)
        # In this case, len(revisions) = 2 and revisions.index(current_revision) = 0, so pending_migrations = 2
        assert result["pending_migrations"] == PENDING_MIGRATIONS_COUNT
        mock_conn_manager.check_health.assert_called_once()
        assert mock_create_subprocess.call_count == SUBPROCESS_CALLS_COUNT


@pytest.mark.asyncio
async def test_apply_migrations_when_needed():
    """Test the apply_migrations function when migrations are needed."""
    # Mock the check_migration_status and asyncio.create_subprocess_shell functions
    with (
        patch("pat.utils.db_init.check_migration_status") as mock_check_status,
        patch("asyncio.create_subprocess_shell") as mock_create_subprocess,
    ):
        # Set up the mocks
        mock_check_status.side_effect = [
            # First call: not at latest revision
            {
                "current_revision": "9876zyxw",
                "available_revisions": ["1234abcd", "9876zyxw"],
                "is_latest": False,
                "pending_migrations": 1,
            },
            # Second call: at latest revision after applying migrations
            {
                "current_revision": "1234abcd",
                "available_revisions": ["1234abcd", "9876zyxw"],
                "is_latest": True,
                "pending_migrations": 0,
            },
        ]

        # Mock the subprocess for alembic upgrade
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Upgraded database to 1234abcd\n", b""))
        mock_create_subprocess.return_value = mock_process

        # Call the function
        result = await apply_migrations()

        # Verify the result
        assert result is True
        assert mock_check_status.call_count == MIGRATION_STATUS_CHECKS_COUNT
        mock_create_subprocess.assert_called_once_with(
            "alembic upgrade head", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )


@pytest.mark.asyncio
async def test_apply_migrations_when_not_needed():
    """Test the apply_migrations function when no migrations are needed."""
    # Mock the check_migration_status function
    with patch("pat.utils.db_init.check_migration_status") as mock_check_status:
        # Set up the mock
        mock_check_status.return_value = {
            "current_revision": "1234abcd",
            "available_revisions": ["1234abcd", "9876zyxw"],
            "is_latest": True,
            "pending_migrations": 0,
        }

        # Call the function
        result = await apply_migrations()

        # Verify the result
        assert result is False
        mock_check_status.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_database():
    """Test the initialize_database function."""
    # Mock the create_database and apply_migrations functions
    with (
        patch("pat.utils.db_init.create_database") as mock_create_db,
        patch("pat.utils.db_init.apply_migrations") as mock_apply_migrations,
    ):
        # Set up the mocks
        mock_create_db.return_value = True  # Database was created
        mock_apply_migrations.return_value = True  # Migrations were applied

        # Call the function
        result = await initialize_database()

        # Verify the result
        assert result is True
        mock_create_db.assert_called_once()
        mock_apply_migrations.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_database_no_changes():
    """Test the initialize_database function when no changes are needed."""
    # Mock the create_database and apply_migrations functions
    with (
        patch("pat.utils.db_init.create_database") as mock_create_db,
        patch("pat.utils.db_init.apply_migrations") as mock_apply_migrations,
    ):
        # Set up the mocks
        mock_create_db.return_value = False  # Database already exists
        mock_apply_migrations.return_value = False  # No migrations needed

        # Call the function
        result = await initialize_database()

        # Verify the result
        assert result is False
        mock_create_db.assert_called_once()
        mock_apply_migrations.assert_called_once()


@pytest.mark.asyncio
async def test_seed_database_with_registered_function():
    """Test the seed_database function with a registered seed function."""
    # Create a mock seed function
    mock_seed_func = AsyncMock()

    # Register the mock seed function
    with (
        patch("pat.utils.db_init._seed_registry") as mock_registry,
        patch("pat.utils.db_init.SETTINGS") as mock_settings,
    ):
        # Set up the mocks
        mock_settings.environment = EnvironmentType.DEVELOPMENT
        mock_registry.get.return_value = mock_seed_func

        # Call the function
        result = await seed_database()

        # Verify the result
        assert result is True
        mock_registry.get.assert_called_once_with(str(EnvironmentType.DEVELOPMENT))
        mock_seed_func.assert_called_once()


@pytest.mark.asyncio
async def test_seed_database_no_registered_function():
    """Test the seed_database function with no registered seed function."""
    # Mock the _seed_registry and SETTINGS
    with (
        patch("pat.utils.db_init._seed_registry") as mock_registry,
        patch("pat.utils.db_init.SETTINGS") as mock_settings,
    ):
        # Set up the mocks
        mock_settings.environment = EnvironmentType.DEVELOPMENT
        mock_registry.get.return_value = None  # No seed function registered

        # Call the function
        result = await seed_database()

        # Verify the result
        assert result is False
        mock_registry.get.assert_called_once_with(str(EnvironmentType.DEVELOPMENT))


@pytest.mark.asyncio
async def test_initialize_and_seed_database():
    """Test the initialize_and_seed_database function."""
    # Mock the initialize_database and seed_database functions
    with (
        patch("pat.utils.db_init.initialize_database") as mock_init_db,
        patch("pat.utils.db_init.seed_database") as mock_seed_db,
    ):
        # Set up the mocks
        mock_init_db.return_value = True  # Database was initialized
        mock_seed_db.return_value = True  # Database was seeded

        # Call the function
        result = await initialize_and_seed_database()

        # Verify the result
        assert result is True
        mock_init_db.assert_called_once()
        mock_seed_db.assert_called_once()


@pytest.mark.asyncio
async def test_initialize_and_seed_database_no_changes():
    """Test the initialize_and_seed_database function when no changes are needed."""
    # Mock the initialize_database and seed_database functions
    with (
        patch("pat.utils.db_init.initialize_database") as mock_init_db,
        patch("pat.utils.db_init.seed_database") as mock_seed_db,
    ):
        # Set up the mocks
        mock_init_db.return_value = False  # No initialization needed
        mock_seed_db.return_value = False  # No seeding needed

        # Call the function
        result = await initialize_and_seed_database()

        # Verify the result
        assert result is False
        mock_init_db.assert_called_once()
        mock_seed_db.assert_called_once()


def test_register_seed_function():
    """Test the register_seed_function function."""
    # Create a mock seed function
    mock_seed_func = AsyncMock()

    # Mock the _seed_registry
    with patch("pat.utils.db_init._seed_registry", {}) as mock_registry:
        # Call the function
        register_seed_function("development", mock_seed_func)

        # Verify the result
        assert mock_registry["development"] == mock_seed_func


def test_raise_error():
    """Test the _raise_error function."""
    # Test that the function raises a RuntimeError with the given message
    with pytest.raises(RuntimeError) as excinfo:
        _raise_error("Test error message")

    # Verify the error message
    assert str(excinfo.value) == "Test error message"
