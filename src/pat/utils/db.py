from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from typing import Annotated, Any, TypeVar

import logfire
from fastapi import Depends
from sqlalchemy import event, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool.base import _ConnectionRecord
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pat.config import SETTINGS

# Create async engine with connection pooling
# Get environment-specific connection pooling parameters
pool_size = SETTINGS.get_pool_size()
max_overflow = SETTINGS.get_max_overflow()
pool_timeout = SETTINGS.get_pool_timeout()
pool_recycle = SETTINGS.get_pool_recycle()
pool_pre_ping = SETTINGS.postgres_pool_pre_ping

logfire.info(
    "Creating database engine",
    environment=SETTINGS.environment,
    host=SETTINGS.postgres_host,
    port=SETTINGS.postgres_port,
    db=SETTINGS.postgres_db,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=pool_timeout,
    pool_recycle=pool_recycle,
    pool_pre_ping=pool_pre_ping,
)

asyncio_engine = create_async_engine(
    str(SETTINGS.postgres_uri),
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_timeout=pool_timeout,
    pool_recycle=pool_recycle,
    pool_pre_ping=pool_pre_ping,
)


# Set up logging for connection pool events
@event.listens_for(asyncio_engine.sync_engine, "connect")
def on_connect(dbapi_connection: Connection, connection_record: _ConnectionRecord) -> None:  # noqa: ARG001
    """Log when a connection is created.

    Args:
        dbapi_connection: The DBAPI connection
        connection_record: The connection record

    """
    logfire.info("Database connection established", connection_id=id(dbapi_connection))


@event.listens_for(asyncio_engine.sync_engine, "checkout")
def on_checkout(
    dbapi_connection: Connection,
    connection_record: _ConnectionRecord,  # noqa: ARG001
    connection_proxy: Connection,  # noqa: ARG001
) -> None:
    """Log when a connection is checked out from the pool.

    Args:
        dbapi_connection: The DBAPI connection
        connection_record: The connection record
        connection_proxy: The connection proxy

    """
    logfire.debug("Database connection checked out", connection_id=id(dbapi_connection))


@event.listens_for(asyncio_engine.sync_engine, "checkin")
def on_checkin(dbapi_connection: Connection, connection_record: _ConnectionRecord) -> None:  # noqa: ARG001
    """Log when a connection is checked back into the pool.

    Args:
        dbapi_connection: The DBAPI connection
        connection_record: The connection record

    """
    logfire.debug("Database connection checked in", connection_id=id(dbapi_connection))


@event.listens_for(asyncio_engine.sync_engine, "close")
def on_close(dbapi_connection: Connection, connection_record: _ConnectionRecord) -> None:  # noqa: ARG001
    """Log when a connection is closed.

    Args:
        dbapi_connection: The DBAPI connection
        connection_record: The connection record

    """
    logfire.info("Database connection closed", connection_id=id(dbapi_connection))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session from the session factory.

    This function creates a new session for each request and closes it when the request is complete.

    Yields:
        AsyncSession: An async SQLAlchemy session

    """
    async with AsyncSession(
        asyncio_engine,
        expire_on_commit=False,  # Don't expire objects after commit
        autoflush=False,  # Don't flush automatically
        autocommit=False,  # Don't autocommit
    ) as session:
        try:
            yield session
        except Exception as e:
            # Rollback on exception
            await session.rollback()
            logfire.exception("Session error, rolling back", exception=str(e))
            raise


@asynccontextmanager
async def session_context() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Type variable for transaction management utilities
T = TypeVar("T")


async def commit_transaction(session: AsyncSession) -> None:
    """Commit the current transaction.

    Args:
        session: The SQLAlchemy session

    Raises:
        SQLAlchemyError: If the commit fails

    """
    try:
        await session.commit()
        logfire.debug("Transaction committed successfully")
    except SQLAlchemyError as e:
        await session.rollback()
        logfire.exception("Failed to commit transaction", exception=str(e))
        raise


async def rollback_transaction(session: AsyncSession) -> None:
    """Rollback the current transaction.

    Args:
        session: The SQLAlchemy session

    """
    try:
        await session.rollback()
        logfire.debug("Transaction rolled back successfully")
    except SQLAlchemyError as e:
        logfire.exception("Failed to rollback transaction", exception=str(e))
        raise


async def in_transaction(
    session: AsyncSession,
    func: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,  # noqa: ANN401
    **kwargs: Any,  # noqa: ANN401
) -> T:
    """Execute a function within a transaction.

    The transaction will be committed if the function succeeds,
    or rolled back if it raises an exception.

    Args:
        session: The SQLAlchemy session
        func: The async function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function

    Raises:
        Exception: Any exception raised by the function

    """
    try:
        result = await func(*args, **kwargs)
    except Exception as e:
        await rollback_transaction(session)
        logfire.exception("Transaction failed", exception=str(e))
        raise
    else:
        await commit_transaction(session)
        return result


# Define retry configurations for different types of operations
RETRY_TRANSIENT_DB_ERRORS = {
    "stop": stop_after_attempt(5),
    "wait": wait_exponential(multiplier=1, min=1, max=10),
    "retry": retry_if_exception_type((OperationalError, DBAPIError)),
    "reraise": True,
}

# Configuration for connection retries
# More aggressive retry for initial connection to handle startup scenarios
RETRY_CONNECTION = {
    "stop": stop_after_attempt(SETTINGS.get_connection_retry_attempts()),
    "wait": wait_exponential(multiplier=0.5, min=1, max=SETTINGS.get_connection_retry_max_wait()),
    "reraise": True,
}


async def execute_with_retry(session: AsyncSession, statement: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """Execute a SQL statement with retry logic for transient errors.

    Args:
        session: The SQLAlchemy session
        statement: The SQL statement to execute
        *args: Positional arguments to pass to execute
        **kwargs: Keyword arguments to pass to execute

    Returns:
        The result of the execution

    Raises:
        SQLAlchemyError: If the execution fails after retries

    """

    @retry(**RETRY_TRANSIENT_DB_ERRORS)
    async def _execute_with_retry() -> Any:  # noqa: ANN401
        try:
            return await session.execute(statement, *args, **kwargs)
        except IntegrityError as e:
            # Don't retry integrity errors as they're usually not transient
            logfire.error("Integrity error in database operation", exception=str(e), statement=str(statement))
            raise
        except OperationalError as e:
            logfire.warning("Transient database error, retrying", exception=str(e), statement=str(statement))
            raise
        except DBAPIError as e:
            logfire.warning("Transient database error, retrying", exception=str(e), statement=str(statement))
            raise
        except SQLAlchemyError as e:
            logfire.error("Database error", exception=str(e), statement=str(statement))
            raise

    return await _execute_with_retry()


@retry(**RETRY_CONNECTION)
async def init_con() -> None:
    """Initialize the database connection with retries.

    This function is called during application startup to ensure
    the database is available. It uses an exponential backoff strategy
    to retry connections, with environment-specific retry parameters.

    Raises:
        Exception: If the connection cannot be established after retries

    """
    try:
        logfire.info(
            "Initializing database connection",
            environment=SETTINGS.environment,
            host=SETTINGS.postgres_host,
            port=SETTINGS.postgres_port,
            db=SETTINGS.postgres_db,
            retry_attempts=SETTINGS.get_connection_retry_attempts(),
            retry_max_wait=SETTINGS.get_connection_retry_max_wait(),
        )

        async with session_context() as session:
            result = await session.execute(select(1))
            value = result.scalar_one()
            if value == 1:
                logfire.info("Database connection successfully established")
            else:
                logfire.error(f"Unexpected result from database ping: {value}")
                # Define error message as a variable to satisfy linting rules
                error_msg = "Database connection test failed"

                def _raise_connection_error() -> None:
                    """Raise a RuntimeError with the connection error message."""
                    raise RuntimeError(error_msg)

                _raise_connection_error()
    except OperationalError as e:
        logfire.exception(
            "Database connection failed due to operational error",
            exception=str(e),
            error_code=getattr(e, "code", None),
        )
        raise
    except DBAPIError as e:
        logfire.exception(
            "Database connection failed due to DBAPI error",
            exception=str(e),
            error_code=getattr(e, "code", None),
        )
        raise
    except Exception as e:
        logfire.exception(
            "Failed to initialize database connection",
            exception=str(e),
            exception_type=type(e).__name__,
        )
        raise
