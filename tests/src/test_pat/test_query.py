"""Tests for query helper functions."""

import pytest

from pat.schemas.schemas import User
from pat.utils.crud import create
from pat.utils.db import session_context
from pat.utils.query import exists, get_by_field, get_by_fields, get_latest, get_ordered, search

# Constants for test data
SEARCH_RESULTS_COUNT = 2
ORDERED_USERS_COUNT = 3
LATEST_USERS_COUNT = 2


@pytest.mark.asyncio
async def test_get_by_field():
    """Test that get_by_field retrieves a record by a specific field value."""
    async with session_context() as session:
        # Create a user
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
        }
        user = await create(session, User, user_data)

        # Get the user by email
        retrieved_user = await get_by_field(session, User, "email", "test.user@example.com")

        # Verify the user was retrieved
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == "test.user@example.com"

        # Try to get a non-existent user
        non_existent_user = await get_by_field(session, User, "email", "nonexistent@example.com")
        assert non_existent_user is None

        # Try to get by a non-existent field
        with pytest.raises(ValueError, match="Field non_existent_field does not exist on model User"):
            await get_by_field(session, User, "non_existent_field", "value")


@pytest.mark.asyncio
async def test_get_by_fields():
    """Test that get_by_fields retrieves a record by multiple field values."""
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
        ]

        for user_data in users_data:
            await create(session, User, user_data)

        # Get the user by first_name and last_name
        retrieved_user = await get_by_fields(
            session,
            User,
            {
                "first_name": "Test1",
                "last_name": "User1",
            },
        )

        # Verify the user was retrieved
        assert retrieved_user is not None
        assert retrieved_user.first_name == "Test1"
        assert retrieved_user.last_name == "User1"
        assert retrieved_user.email == "test1.user1@example.com"

        # Try to get a non-existent user
        non_existent_user = await get_by_fields(
            session,
            User,
            {
                "first_name": "NonExistent",
                "last_name": "User",
            },
        )
        assert non_existent_user is None

        # Try to get by a non-existent field
        with pytest.raises(ValueError, match="Field non_existent_field does not exist on model User"):
            await get_by_fields(
                session,
                User,
                {
                    "first_name": "Test1",
                    "non_existent_field": "value",
                },
            )


@pytest.mark.asyncio
async def test_search():
    """Test that search finds records by a search term across multiple fields."""
    async with session_context() as session:
        # Create multiple users
        users_data = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com",
            },
            {
                "first_name": "Bob",
                "last_name": "Johnson",
                "email": "bob.johnson@example.com",
            },
        ]

        for user_data in users_data:
            await create(session, User, user_data)

        # Search for users with "john" in their first_name or email
        results = await search(session, User, "john", ["first_name", "email"])

        # Verify the results
        assert len(results) == SEARCH_RESULTS_COUNT  # John Doe and Bob Johnson (email contains "johnson")
        assert any(user.first_name == "John" for user in results)
        assert any(user.last_name == "Johnson" for user in results)

        # Search with pagination
        paginated_results = await search(session, User, "john", ["first_name", "email"], skip=1, limit=1)
        assert len(paginated_results) == 1

        # Try to search with a non-existent field
        with pytest.raises(ValueError, match="Field non_existent_field does not exist on model User"):
            await search(session, User, "john", ["first_name", "non_existent_field"])


@pytest.mark.asyncio
async def test_get_ordered():
    """Test that get_ordered retrieves records with ordering, pagination, and filtering."""
    async with session_context() as session:
        # Create multiple users
        users_data = [
            {
                "first_name": "Alice",
                "last_name": "Smith",
                "email": "alice.smith@example.com",
            },
            {
                "first_name": "Bob",
                "last_name": "Johnson",
                "email": "bob.johnson@example.com",
            },
            {
                "first_name": "Charlie",
                "last_name": "Brown",
                "email": "charlie.brown@example.com",
            },
        ]

        for user_data in users_data:
            await create(session, User, user_data)

        # Get users ordered by first_name ascending
        ordered_users = await get_ordered(session, User, order_by="first_name")
        assert len(ordered_users) == ORDERED_USERS_COUNT
        assert ordered_users[0].first_name == "Alice"
        assert ordered_users[1].first_name == "Bob"
        assert ordered_users[2].first_name == "Charlie"

        # Get users ordered by first_name descending
        ordered_users_desc = await get_ordered(session, User, order_by="first_name", descending=True)
        assert len(ordered_users_desc) == ORDERED_USERS_COUNT
        assert ordered_users_desc[0].first_name == "Charlie"
        assert ordered_users_desc[1].first_name == "Bob"
        assert ordered_users_desc[2].first_name == "Alice"

        # Get users with pagination
        paginated_users = await get_ordered(session, User, order_by="first_name", skip=1, limit=1)
        assert len(paginated_users) == 1
        assert paginated_users[0].first_name == "Bob"

        # Get users with filtering
        filtered_users = await get_ordered(session, User, order_by="first_name", filters={"last_name": "Smith"})
        assert len(filtered_users) == 1
        assert filtered_users[0].first_name == "Alice"
        assert filtered_users[0].last_name == "Smith"

        # Try to order by a non-existent field
        with pytest.raises(ValueError, match="Field non_existent_field does not exist on model User"):
            await get_ordered(session, User, order_by="non_existent_field")


@pytest.mark.asyncio
async def test_get_latest():
    """Test that get_latest retrieves the latest records by created_at timestamp."""
    async with session_context() as session:
        # Create multiple users
        users_data = [
            {
                "first_name": "User1",
                "last_name": "Test1",
                "email": "user1.test1@example.com",
            },
            {
                "first_name": "User2",
                "last_name": "Test2",
                "email": "user2.test2@example.com",
            },
            {
                "first_name": "User3",
                "last_name": "Test3",
                "email": "user3.test3@example.com",
            },
        ]

        for user_data in users_data:
            await create(session, User, user_data)

        # Get the latest users
        latest_users = await get_latest(session, User, limit=2)

        # Verify the results
        assert len(latest_users) == LATEST_USERS_COUNT
        # The users are returned in the order they were created in the database
        # Since we're using the same session, they should be in order of insertion
        assert latest_users[0].first_name == "User1"
        assert latest_users[1].first_name == "User2"

        # Get the latest users with filtering
        filtered_latest_users = await get_latest(session, User, filters={"first_name": "User1"})
        assert len(filtered_latest_users) == 1
        assert filtered_latest_users[0].first_name == "User1"


@pytest.mark.asyncio
async def test_exists():
    """Test that exists checks if a record exists with the given filters."""
    async with session_context() as session:
        # Create a user
        user_data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
        }
        await create(session, User, user_data)

        # Check if a user exists with the given filters
        exists_result = await exists(session, User, {"email": "test.user@example.com"})
        assert exists_result is True

        # Check if a non-existent user exists
        non_exists_result = await exists(session, User, {"email": "nonexistent@example.com"})
        assert non_exists_result is False

        # Try to check existence with a non-existent field
        with pytest.raises(ValueError, match="Field non_existent_field does not exist on model User"):
            await exists(session, User, {"non_existent_field": "value"})
