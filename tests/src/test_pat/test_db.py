import pytest
from sqlalchemy.future import select

from pat.models import User
from pat.utils.db import session_context


@pytest.mark.asyncio
async def test_database_fixture():
    """
    Test to make sure the session is working correctly
    """
    async with session_context() as session_test:
        user_1 = User(
            first_name="example first name",
            last_name="example last name",
            email="first.last@example.com",
        )
        session_test.add(user_1)
        await session_test.commit()
        await session_test.refresh(user_1)  # Add this line to refresh the instance
        _id = user_1.id
        assert isinstance(_id, int)

        users = (await session_test.execute(select(User))).all()
        assert len(users) == 1


@pytest.mark.asyncio
async def test_database_fixture_data_deleted_between_tests():
    """
    Test to make sure the test rollback is working correctly and data from other tests is not persisting past function
    run.
    """
    async with session_context() as session_test:
        users = (await session_test.execute(select(User))).all()
        assert len(users) == 0
