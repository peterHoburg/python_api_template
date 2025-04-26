"""Helper functions for common database query patterns."""

from typing import Any, TypeVar

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from pat.models.base import Base
from pat.utils.db import execute_with_retry

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=Base)


async def get_by_field(
    session: AsyncSession,
    model_class: type[ModelType],
    field_name: str,
    field_value: Any,  # noqa: ANN401
) -> ModelType | None:
    """Get a record by a specific field value.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        field_name: The name of the field to filter by
        field_value: The value to filter for

    Returns:
        The record if found, None otherwise

    """
    if not hasattr(model_class, field_name):
        error_msg = f"Field {field_name} does not exist on model {model_class.__name__}"
        raise ValueError(error_msg)

    stmt = select(model_class).where(getattr(model_class, field_name) == field_value)
    result = await execute_with_retry(session, stmt)
    return result.scalars().first()


async def get_by_fields(
    session: AsyncSession,
    model_class: type[ModelType],
    filters: dict[str, Any],
) -> ModelType | None:
    """Get a record by multiple field values (AND condition).

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        filters: Dictionary of field names and values to filter by

    Returns:
        The record if found, None otherwise

    """
    stmt = select(model_class)

    for field_name, field_value in filters.items():
        if not hasattr(model_class, field_name):
            error_msg = f"Field {field_name} does not exist on model {model_class.__name__}"
            raise ValueError(error_msg)
        stmt = stmt.where(getattr(model_class, field_name) == field_value)

    result = await execute_with_retry(session, stmt)
    return result.scalars().first()


async def search(  # noqa: PLR0913
    session: AsyncSession,
    model_class: type[ModelType],
    search_term: str,
    fields: list[str],
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[ModelType]:
    """Search for records by a search term across multiple fields.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        search_term: The term to search for
        fields: List of field names to search in
        skip: The number of records to skip
        limit: The maximum number of records to return

    Returns:
        A list of matching records

    """
    # Validate fields
    for field_name in fields:
        if not hasattr(model_class, field_name):
            error_msg = f"Field {field_name} does not exist on model {model_class.__name__}"
            raise ValueError(error_msg)

    # Build OR conditions for each field
    conditions = []
    for field_name in fields:
        field = getattr(model_class, field_name)
        # Use LIKE for string fields
        conditions.append(field.ilike(f"%{search_term}%"))

    stmt = select(model_class).where(or_(*conditions)).offset(skip).limit(limit)
    result = await execute_with_retry(session, stmt)
    return list(result.scalars().all())


async def get_ordered(  # noqa: PLR0913
    session: AsyncSession,
    model_class: type[ModelType],
    *,
    order_by: str,
    descending: bool = False,
    skip: int = 0,
    limit: int = 100,
    filters: dict[str, Any] | None = None,
) -> list[ModelType]:
    """Get records with ordering, pagination, and filtering.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        order_by: The field to order by
        descending: Whether to order in descending order
        skip: The number of records to skip
        limit: The maximum number of records to return
        filters: Optional filters to apply

    Returns:
        A list of records

    """
    if not hasattr(model_class, order_by):
        error_msg = f"Field {order_by} does not exist on model {model_class.__name__}"
        raise ValueError(error_msg)

    order_field = getattr(model_class, order_by)
    order_func = desc if descending else asc

    stmt = select(model_class).order_by(order_func(order_field)).offset(skip).limit(limit)

    if filters:
        for field_name, field_value in filters.items():
            if not hasattr(model_class, field_name):
                error_msg = f"Field {field_name} does not exist on model {model_class.__name__}"
                raise ValueError(error_msg)
            stmt = stmt.where(getattr(model_class, field_name) == field_value)

    result = await execute_with_retry(session, stmt)
    return list(result.scalars().all())


async def get_latest(
    session: AsyncSession,
    model_class: type[ModelType],
    *,
    limit: int = 10,
    filters: dict[str, Any] | None = None,
) -> list[ModelType]:
    """Get the latest records by created_at timestamp.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        limit: The maximum number of records to return
        filters: Optional filters to apply

    Returns:
        A list of the latest records

    """
    return await get_ordered(
        session,
        model_class,
        order_by="created_at",
        descending=True,
        limit=limit,
        filters=filters,
    )


async def exists(
    session: AsyncSession,
    model_class: type[ModelType],
    filters: dict[str, Any],
) -> bool:
    """Check if a record exists with the given filters.

    Args:
        session: The database session
        model_class: The SQLAlchemy model class
        filters: Dictionary of field names and values to filter by

    Returns:
        True if a record exists, False otherwise

    """
    stmt = select(func.count()).select_from(model_class)

    for field_name, field_value in filters.items():
        if not hasattr(model_class, field_name):
            error_msg = f"Field {field_name} does not exist on model {model_class.__name__}"
            raise ValueError(error_msg)
        stmt = stmt.where(getattr(model_class, field_name) == field_value)

    result = await execute_with_retry(session, stmt)
    count = result.scalar_one()
    return count > 0
