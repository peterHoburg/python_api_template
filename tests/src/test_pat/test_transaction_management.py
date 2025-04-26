"""Tests for transaction management utilities."""

import pytest
from sqlalchemy.future import select

from pat.schemas.schemas import User
from pat.utils.db import commit_transaction, in_transaction, rollback_transaction, session_context


@pytest.mark.asyncio
async def test_commit_transaction():
    """Test that commit_transaction commits changes to the database."""
    async with session_context() as session:
        # Create a user
        user = User(
            first_name="Test",
            last_name="User",
            email="test.user@example.com",
        )
        session.add(user)

        # Commit the transaction
        await commit_transaction(session)

        # Verify the user was added
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 1
        assert users[0].email == "test.user@example.com"


@pytest.mark.asyncio
async def test_rollback_transaction():
    """Test that rollback_transaction rolls back changes to the database."""
    async with session_context() as session:
        # Create a user
        user = User(
            first_name="Test",
            last_name="User",
            email="test.user@example.com",
        )
        session.add(user)

        # Rollback the transaction
        await rollback_transaction(session)

        # Verify the user was not added
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 0


@pytest.mark.asyncio
async def test_in_transaction_commit():
    """Test that in_transaction commits changes when the function succeeds."""
    async with session_context() as session:
        # Define a function that adds a user
        async def add_user() -> User:
            user = User(
                first_name="Test",
                last_name="User",
                email="test.user@example.com",
            )
            session.add(user)
            return user

        # Execute the function in a transaction
        user = await in_transaction(session, add_user)

        # Verify the user was added
        assert user.email == "test.user@example.com"
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 1
        assert users[0].email == "test.user@example.com"


@pytest.mark.asyncio
async def test_in_transaction_rollback():
    """Test that in_transaction rolls back changes when the function fails."""
    async with session_context() as session:
        # Define a function that adds a user and then raises an exception
        async def add_user_and_fail() -> None:
            user = User(
                first_name="Test",
                last_name="User",
                email="test.user@example.com",
            )
            session.add(user)
            error_msg = "Test exception"
            raise ValueError(error_msg)

        # Execute the function in a transaction
        with pytest.raises(ValueError, match="Test exception"):
            await in_transaction(session, add_user_and_fail)

        # Verify the user was not added
        users = (await session.execute(select(User))).scalars().all()
        assert len(users) == 0
