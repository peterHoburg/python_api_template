"""Tests for CRUD utility functions."""

import pytest
from sqlalchemy.future import select

from pat.models import User
from pat.utils.crud import count, create, delete_by_id, get, get_multi, update_by_id
from pat.utils.db import session_context

# Constants for test data
TOTAL_USERS_COUNT = 3


@pytest.mark.asyncio
async def test_create():
    """Test that create adds a record to the database."""
    async with session_context() as session:
        # Create a user
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
        }
        user = await create(session, User, user_data)

        # Verify the user was added
        assert user.id is not None
        assert user.first_name == "Test"
        assert user.last_name == "User"
        assert user.email == "test.user@example.com"

        # Verify the user is in the database
        db_user = (await session.execute(select(User).where(User.id == user.id))).scalar_one()
        assert db_user.id == user.id
        assert db_user.email == "test.user@example.com"


@pytest.mark.asyncio
async def test_get():
    """Test that get retrieves a record by ID."""
    async with session_context() as session:
        # Create a user
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
        }
        user = await create(session, User, user_data)

        # Get the user by ID
        retrieved_user = await get(session, User, user.id)

        # Verify the user was retrieved
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "test.user@example.com"

        # Try to get a non-existent user
        non_existent_user = await get(session, User, 9999)
        assert non_existent_user is None


@pytest.mark.asyncio
async def test_get_multi():
    """Test that get_multi retrieves multiple records with pagination and filtering."""
    async with session_context() as session:
        # Create multiple users
        users_data = [
            {
                "first_name": "Test1",
                "last_name": "User1",
                "email": "test1.user1@example.com",
            },
            {
                "first_name": "Test2",
                "last_name": "User2",
                "email": "test2.user2@example.com",
            },
            {
                "first_name": "Test3",
                "last_name": "User3",
                "email": "test3.user3@example.com",
            },
        ]

        for user_data in users_data:
            await create(session, User, user_data)

        # Get all users
        all_users = await get_multi(session, User)
        assert len(all_users) == TOTAL_USERS_COUNT

        # Get users with pagination
        paginated_users = await get_multi(session, User, skip=1, limit=1)
        assert len(paginated_users) == 1
        assert paginated_users[0].first_name == "Test2"

        # Get users with filtering
        filtered_users = await get_multi(session, User, filters={"first_name": "Test1"})
        assert len(filtered_users) == 1
        assert filtered_users[0].first_name == "Test1"


@pytest.mark.asyncio
async def test_update_by_id():
    """Test that update_by_id updates a record by ID."""
    async with session_context() as session:
        # Create a user
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
        }
        user = await create(session, User, user_data)

        # Update the user
        updated_data = {
            "first_name": "Updated",
            "email": "updated.user@example.com",
        }
        updated_user = await update_by_id(session, User, user.id, updated_data)

        # Verify the user was updated
        assert updated_user is not None
        assert updated_user.id == user.id
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "User"  # Unchanged
        assert updated_user.email == "updated.user@example.com"

        # Try to update a non-existent user
        non_existent_user = await update_by_id(session, User, 9999, updated_data)
        assert non_existent_user is None


@pytest.mark.asyncio
async def test_delete_by_id():
    """Test that delete_by_id deletes a record by ID."""
    async with session_context() as session:
        # Create a user
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
        }
        user = await create(session, User, user_data)

        # Delete the user
        result = await delete_by_id(session, User, user.id)

        # Verify the user was deleted
        assert result is True
        deleted_user = await get(session, User, user.id)
        assert deleted_user is None

        # Try to delete a non-existent user
        result = await delete_by_id(session, User, 9999)
        assert result is False


@pytest.mark.asyncio
async def test_count():
    """Test that count returns the number of records."""
    async with session_context() as session:
        # Create multiple users
        users_data = [
            {
                "first_name": "Test1",
                "last_name": "User1",
                "email": "test1.user1@example.com",
            },
            {
                "first_name": "Test2",
                "last_name": "User2",
                "email": "test2.user2@example.com",
            },
            {
                "first_name": "Test3",
                "last_name": "User3",
                "email": "test3.user3@example.com",
            },
        ]

        for user_data in users_data:
            await create(session, User, user_data)

        # Count all users
        total_count = await count(session, User)
        assert total_count == TOTAL_USERS_COUNT

        # Count users with filtering
        filtered_count = await count(session, User, filters={"first_name": "Test1"})
        assert filtered_count == 1
