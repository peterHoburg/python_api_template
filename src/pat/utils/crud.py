"""CRUD utility functions for database operations."""

from typing import Any, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pat.models.base import Base
from pat.utils.db import execute_with_retry

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)


async def create(session: AsyncSession, model_class: type[ModelType], obj_in: dict[str, Any]) -> ModelType:
    """Create a new record in the database.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        obj_in: The data to create the record with

    Returns:
        The created record

    """
    db_obj = model_class.from_dict(obj_in)
    session.add(db_obj)
    await session.flush()
    await session.refresh(db_obj)
    # The type is correct at runtime, but we need to help the type checker
    return db_obj  # type: ignore[return-value]


async def get(session: AsyncSession, model_class: type[ModelType], record_id: int) -> ModelType | None:
    """Get a record by ID.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        record_id: The ID of the record to get

    Returns:
        The record if found, None otherwise

    """
    stmt = select(model_class).where(model_class.id == record_id)
    result = await execute_with_retry(session, stmt)
    return result.scalars().first()


async def get_multi(
    session: AsyncSession,
    model_class: type[ModelType],
    *,
    skip: int = 0,
    limit: int = 100,
    filters: dict[str, Any] | None = None,
) -> list[ModelType]:
    """Get multiple records with pagination and filtering.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        skip: The number of records to skip
        limit: The maximum number of records to return
        filters: Optional filters to apply

    Returns:
        A list of records

    """
    stmt = select(model_class).offset(skip).limit(limit)

    if filters:
        for field, value in filters.items():
            if hasattr(model_class, field):
                stmt = stmt.where(getattr(model_class, field) == value)

    result = await execute_with_retry(session, stmt)
    return list(result.scalars().all())


async def update_by_id(
    session: AsyncSession,
    model_class: type[ModelType],
    record_id: int,
    obj_in: dict[str, Any],
) -> ModelType | None:
    """Update a record by ID.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        record_id: The ID of the record to update
        obj_in: The data to update the record with

    Returns:
        The updated record if found, None otherwise

    """
    # First check if the record exists
    db_obj = await get(session, model_class, record_id)
    if not db_obj:
        return None

    # Update the record
    for field, value in obj_in.items():
        if hasattr(db_obj, field):
            setattr(db_obj, field, value)

    session.add(db_obj)
    await session.flush()
    await session.refresh(db_obj)
    return db_obj


async def delete_by_id(session: AsyncSession, model_class: type[ModelType], record_id: int) -> bool:
    """Delete a record by ID.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        record_id: The ID of the record to delete

    Returns:
        True if the record was deleted, False otherwise

    """
    stmt = delete(model_class).where(model_class.id == record_id)
    result = await execute_with_retry(session, stmt)
    return result.rowcount > 0


async def count(
    session: AsyncSession,
    model_class: type[ModelType],
    filters: dict[str, Any] | None = None,
) -> int:
    """Count the number of records.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        filters: Optional filters to apply

    Returns:
        The number of records

    """
    stmt = select(model_class)

    if filters:
        for field, value in filters.items():
            if hasattr(model_class, field):
                stmt = stmt.where(getattr(model_class, field) == value)

    result = await execute_with_retry(session, select(func.count()).select_from(stmt.subquery()))
    return result.scalar_one()
