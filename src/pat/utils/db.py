from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any, TypeVar

import logfire
from fastapi import Depends
from sqlalchemy import event, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool.base import _ConnectionRecord
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
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
    """Get a database session from the connection manager.

    This function creates a new session for each request using the connection manager,
    which provides health checks, reconnection, and retry logic. The session is closed
    when the request is complete.

    Yields:
        AsyncSession: An async SQLAlchemy session with retry and recovery capabilities

    """
    session = await connection_manager.get_session()
    try:
        yield session
    except Exception as e:
        # Rollback on exception
        await session.rollback()
        logfire.exception(
            "Session error, rolling back",
            exception=str(e),
            exception_type=type(e).__name__,
            connection_id=id(session),
        )
        raise
    finally:
        await connection_manager.release_session(session)


@asynccontextmanager
async def session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions.

    This function provides a context manager that automatically acquires and releases sessions
    using the connection manager, which handles health checks, reconnection, and retry logic.

    Yields:
        AsyncSession: An async SQLAlchemy session with retry and recovery capabilities

    """
    async with connection_manager.session_context() as session:
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

# Get jitter factor from settings
jitter_factor = SETTINGS.get_jitter_factor()

# Configuration for initial connection retries
# More aggressive retry for initial connection to handle startup scenarios
RETRY_CONNECTION = {
    "stop": stop_after_attempt(SETTINGS.get_connection_retry_attempts()),
    "wait": wait_random_exponential(
        multiplier=0.5,
        min=1,
        max=SETTINGS.get_connection_retry_max_wait(),
        exp_base=2 + jitter_factor,  # Add jitter to prevent thundering herd
    ),
    "retry": retry_if_exception_type((OperationalError, DBAPIError)),
    "reraise": True,
}

# Configuration for reconnection retries after connection loss
RETRY_RECONNECTION = {
    "stop": stop_after_attempt(SETTINGS.get_reconnect_retry_attempts()),
    "wait": wait_random_exponential(
        multiplier=0.75,
        min=1,
        max=SETTINGS.get_reconnect_retry_max_wait(),
        exp_base=2 + jitter_factor,  # Add jitter to prevent thundering herd
    ),
    "retry": retry_if_exception_type((OperationalError, DBAPIError)),
    "reraise": True,
}

# Configuration for query retries (transient errors during query execution)
RETRY_QUERY = {
    "stop": stop_after_attempt(SETTINGS.get_query_retry_attempts()),
    "wait": wait_random_exponential(
        multiplier=1,
        min=1,
        max=SETTINGS.get_query_retry_max_wait(),
        exp_base=2 + jitter_factor,  # Add jitter to prevent thundering herd
    ),
    "retry": retry_if_exception_type((OperationalError, DBAPIError)),
    "reraise": True,
}

# Configuration for integrity errors (non-retryable, but logged differently)
RETRY_INTEGRITY_ERROR = {
    "stop": stop_after_attempt(1),  # Don't retry integrity errors
    "wait": wait_exponential(multiplier=0, min=0, max=0),
    "retry": retry_if_exception_type(IntegrityError),
    "reraise": True,
}

# Circuit breaker state
circuit_breaker = {
    "failures": 0,
    "open": False,
    "last_failure_time": None,
    "threshold": SETTINGS.get_circuit_breaker_failure_threshold(),
    "recovery_time": SETTINGS.get_circuit_breaker_recovery_time(),
}


async def execute_with_retry(session: AsyncSession, statement: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """Execute a SQL statement with retry logic for transient errors.

    This function uses different retry strategies based on the type of error encountered:
    - For integrity errors: No retries (RETRY_INTEGRITY_ERROR)
    - For operational errors and DBAPI errors: Retry with exponential backoff (RETRY_QUERY)
    - For other SQLAlchemy errors: No retries, but logged

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

    # Define a function to handle integrity errors separately
    @retry(**RETRY_INTEGRITY_ERROR)
    async def _execute_with_integrity_error_handling() -> Any:  # noqa: ANN401
        try:
            return await session.execute(statement, *args, **kwargs)
        except IntegrityError as e:
            # Don't retry integrity errors as they're usually not transient
            logfire.error(
                "Integrity error in database operation",
                exception=str(e),
                statement=str(statement),
                error_type="integrity_error",
            )
            raise
        except (OperationalError, DBAPIError) as e:
            # For transient errors, use the query retry strategy
            logfire.warning(
                "Transient database error, will retry with query strategy",
                exception=str(e),
                statement=str(statement),
                error_type="transient_error",
            )
            return await _execute_with_query_retry()
        except SQLAlchemyError as e:
            logfire.error("Database error", exception=str(e), statement=str(statement), error_type="sqlalchemy_error")
            raise

    # Define a function to handle transient errors with retries
    @retry(**RETRY_QUERY)
    async def _execute_with_query_retry() -> Any:  # noqa: ANN401
        try:
            return await session.execute(statement, *args, **kwargs)
        except (OperationalError, DBAPIError) as e:
            logfire.warning(
                "Transient database error during query, retrying",
                exception=str(e),
                statement=str(statement),
                retry_config="RETRY_QUERY",
                max_attempts=SETTINGS.get_query_retry_attempts(),
                max_wait=SETTINGS.get_query_retry_max_wait(),
            )
            raise
        except SQLAlchemyError as e:
            logfire.error(
                "Non-retryable database error during query",
                exception=str(e),
                statement=str(statement),
                error_type="non_retryable",
            )
            raise

    # Start with integrity error handling, which will delegate to query retry if needed
    return await _execute_with_integrity_error_handling()


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
            retry_config="RETRY_CONNECTION",
            retry_attempts=SETTINGS.get_connection_retry_attempts(),
            retry_max_wait=SETTINGS.get_connection_retry_max_wait(),
        )

        # Create a direct session to avoid potential recursion through session_context
        session = AsyncSession(
            asyncio_engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        try:
            result = await session.execute(select(1))
            value = result.scalar_one()
            if value == 1:
                logfire.info(
                    "Database connection successfully established",
                    connection_id=id(session),
                    environment=SETTINGS.environment,
                )
            else:
                logfire.error(
                    f"Unexpected result from database ping: {value}",
                    expected=1,
                    actual=value,
                    connection_id=id(session),
                )
                # Define error message as a variable to satisfy linting rules
                error_msg = "Database connection test failed"

                def _raise_connection_error() -> None:
                    """Raise a RuntimeError with the connection error message."""
                    raise RuntimeError(error_msg)

                _raise_connection_error()
        finally:
            await session.close()
    except OperationalError as e:
        logfire.exception(
            "Database connection failed due to operational error",
            exception=str(e),
            error_code=getattr(e, "code", None),
            error_type="operational_error",
            retry_attempts=SETTINGS.get_connection_retry_attempts(),
        )
        raise
    except DBAPIError as e:
        logfire.exception(
            "Database connection failed due to DBAPI error",
            exception=str(e),
            error_code=getattr(e, "code", None),
            error_type="dbapi_error",
            retry_attempts=SETTINGS.get_connection_retry_attempts(),
        )
        raise
    except Exception as e:
        logfire.exception(
            "Failed to initialize database connection",
            exception=str(e),
            exception_type=type(e).__name__,
            error_type="unexpected_error",
            retry_attempts=SETTINGS.get_connection_retry_attempts(),
        )
        raise


@retry(**RETRY_RECONNECTION)
async def reconnect_db() -> None:
    """Reconnect to the database with retries after a connection loss.

    This function is used when a connection loss is detected during
    application operation. It uses a different retry strategy than
    the initial connection, optimized for reconnection scenarios.

    Raises:
        Exception: If the reconnection cannot be established after retries

    """
    try:
        logfire.info(
            "Attempting to reconnect to database",
            environment=SETTINGS.environment,
            host=SETTINGS.postgres_host,
            port=SETTINGS.postgres_port,
            db=SETTINGS.postgres_db,
            retry_config="RETRY_RECONNECTION",
            retry_attempts=SETTINGS.get_reconnect_retry_attempts(),
            retry_max_wait=SETTINGS.get_reconnect_retry_max_wait(),
        )

        # Create a direct session to avoid potential recursion through session_context
        session = AsyncSession(
            asyncio_engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        try:
            result = await session.execute(select(1))
            value = result.scalar_one()
            if value == 1:
                logfire.info(
                    "Database reconnection successfully established",
                    connection_id=id(session),
                    environment=SETTINGS.environment,
                )
            else:
                logfire.error(
                    f"Unexpected result from database ping during reconnection: {value}",
                    expected=1,
                    actual=value,
                    connection_id=id(session),
                )
                error_msg = "Database reconnection test failed"
                raise RuntimeError(error_msg)
        finally:
            await session.close()
    except OperationalError as e:
        logfire.exception(
            "Database reconnection failed due to operational error",
            exception=str(e),
            error_code=getattr(e, "code", None),
            error_type="operational_error",
            retry_attempts=SETTINGS.get_reconnect_retry_attempts(),
        )
        raise
    except DBAPIError as e:
        logfire.exception(
            "Database reconnection failed due to DBAPI error",
            exception=str(e),
            error_code=getattr(e, "code", None),
            error_type="dbapi_error",
            retry_attempts=SETTINGS.get_reconnect_retry_attempts(),
        )
        raise
    except Exception as e:
        logfire.exception(
            "Failed to reconnect to database",
            exception=str(e),
            exception_type=type(e).__name__,
            error_type="unexpected_error",
            retry_attempts=SETTINGS.get_reconnect_retry_attempts(),
        )
        raise


class ConnectionManager:
    """Manages database connections with robust retry and recovery mechanisms.

    This class provides methods for connection acquisition, release, and health checks,
    with retry logic for handling connection issues. It also monitors connection health
    and automatically attempts to recover from connection failures.

    It implements a circuit breaker pattern to prevent repeated attempts to connect
    to a database that is unavailable for an extended period, which can help prevent
    cascading failures and improve system resilience.

    Attributes:
        _last_health_check: Timestamp of the last successful health check
        _health_check_interval: Interval in seconds between health checks
        _is_healthy: Flag indicating if the connection is currently healthy
        _connection_attempts: Counter for connection attempts
        _connection_failures: Counter for connection failures
        _consecutive_failures: Counter for consecutive failures (for circuit breaker)
        _circuit_open: Flag indicating if the circuit breaker is open
        _last_failure_time: Timestamp of the last failure

    """

    def __init__(self, health_check_interval: int = 60) -> None:
        """Initialize the connection manager.

        Args:
            health_check_interval: Interval in seconds between health checks (default: 60)

        """
        self._last_health_check = datetime.now(UTC)
        self._health_check_interval = health_check_interval
        self._is_healthy = False
        self._connection_attempts = 0
        self._connection_failures = 0
        self._connection_id = None

        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open = False
        self._last_failure_time = None
        self._circuit_threshold = SETTINGS.get_circuit_breaker_failure_threshold()
        self._circuit_recovery_time = SETTINGS.get_circuit_breaker_recovery_time()

    async def initialize(self) -> None:
        """Initialize the database connection.

        This method should be called during application startup to ensure
        the database is available. It uses the init_con function with retry logic.
        It also initializes the circuit breaker state.

        Raises:
            Exception: If the connection cannot be established after retries

        """
        # Reset circuit breaker state on initialization
        self._consecutive_failures = 0
        self._circuit_open = False
        self._last_failure_time = None

        try:
            self._connection_attempts += 1
            await init_con()
            self._is_healthy = True
            self._last_health_check = datetime.now(UTC)
            logfire.info(
                "Connection manager initialized successfully",
                health_check_interval=self._health_check_interval,
                circuit_threshold=self._circuit_threshold,
                circuit_recovery_time=self._circuit_recovery_time,
            )
        except RetryError as e:
            # Handle retry exhaustion specifically
            self._connection_failures += 1
            self._is_healthy = False
            self._update_circuit_failure()
            logfire.exception(
                "Initialization retry attempts exhausted",
                exception=str(e),
                exception_type=type(e).__name__,
                connection_attempts=self._connection_attempts,
                connection_failures=self._connection_failures,
                circuit_open=self._circuit_open,
                consecutive_failures=self._consecutive_failures,
                retry_attempts=SETTINGS.get_connection_retry_attempts(),
            )
            raise
        except Exception as e:
            self._connection_failures += 1
            self._is_healthy = False
            self._update_circuit_failure()
            logfire.exception(
                "Failed to initialize connection manager",
                exception=str(e),
                exception_type=type(e).__name__,
                connection_attempts=self._connection_attempts,
                connection_failures=self._connection_failures,
                circuit_open=self._circuit_open,
                consecutive_failures=self._consecutive_failures,
            )
            raise

    async def get_session(self) -> AsyncSession:
        """Get a database session with health check and retry logic.

        This method performs a health check if needed and returns a session.
        If the connection is unhealthy, it attempts to reconnect before returning a session.
        It also implements circuit breaker logic to prevent repeated attempts to connect
        to a database that is unavailable for an extended period.

        Returns:
            AsyncSession: An async SQLAlchemy session

        Raises:
            Exception: If a session cannot be acquired after retries
            RuntimeError: If the circuit breaker is open

        """
        # Check if circuit breaker is open
        if self._is_circuit_open():
            # Check if it's time to try closing the circuit
            if self._should_attempt_circuit_reset():
                logfire.info(
                    "Attempting to close circuit breaker",
                    last_failure=self._last_failure_time,
                    recovery_time=self._circuit_recovery_time,
                    consecutive_failures=self._consecutive_failures,
                )
                # Try to reset the circuit by performing a health check
                if await self.check_health():
                    self._reset_circuit()
                    logfire.info("Circuit breaker closed successfully")
                else:
                    # Health check failed, keep circuit open
                    self._update_circuit_failure()
                    logfire.warning(
                        "Circuit breaker remains open after failed health check",
                        consecutive_failures=self._consecutive_failures,
                        threshold=self._circuit_threshold,
                    )
                    error_msg = "Database connection unavailable: circuit breaker open"
                    raise RuntimeError(error_msg)
            else:
                # Circuit is open and it's not time to try closing it
                logfire.warning(
                    "Circuit breaker is open, database connection unavailable",
                    last_failure=self._last_failure_time,
                    recovery_time=self._circuit_recovery_time,
                    consecutive_failures=self._consecutive_failures,
                )
                error_msg = "Database connection unavailable: circuit breaker open"
                raise RuntimeError(error_msg)

        # Check if health check is needed
        if self._should_perform_health_check():
            await self.check_health()

        # If connection is unhealthy, attempt to reconnect
        if not self._is_healthy:
            try:
                await self.reconnect()
            except Exception as e:
                self._update_circuit_failure()
                if self._is_circuit_open():
                    logfire.error(
                        "Circuit breaker opened after reconnection failure",
                        exception=str(e),
                        exception_type=type(e).__name__,
                        consecutive_failures=self._consecutive_failures,
                        threshold=self._circuit_threshold,
                    )
                raise

        # Create and return a session
        try:
            session = AsyncSession(
                asyncio_engine,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            self._connection_id = id(session)
            # Connection successful, reset circuit breaker failures
            self._reset_circuit_failures()
            logfire.debug(
                "Session acquired from connection manager",
                connection_id=self._connection_id,
            )
            return session  # noqa: TRY300
        except Exception as e:
            self._update_circuit_failure()
            logfire.exception(
                "Failed to create session",
                exception=str(e),
                exception_type=type(e).__name__,
                consecutive_failures=self._consecutive_failures,
            )
            raise

    async def release_session(self, session: AsyncSession) -> None:
        """Release a database session.

        This method closes the session and performs cleanup.

        Args:
            session: The SQLAlchemy session to release

        """
        try:
            await session.close()
            logfire.debug(
                "Session released",
                connection_id=id(session),
            )
        except Exception as e:  # noqa: BLE001
            logfire.exception(
                "Error releasing session",
                exception=str(e),
                exception_type=type(e).__name__,
                connection_id=id(session),
            )
            # Mark as unhealthy to trigger reconnect on next use
            self._is_healthy = False

    @asynccontextmanager
    async def session_context(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database sessions.

        This method provides a context manager that automatically acquires and releases sessions.

        Yields:
            AsyncSession: An async SQLAlchemy session

        """
        # Create a session directly to avoid potential recursion through get_session
        session = AsyncSession(
            asyncio_engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        try:
            # Reset circuit breaker failures on successful session creation
            self._reset_circuit_failures()
            yield session
        except Exception as e:
            self._update_circuit_failure()
            logfire.exception(
                "Session error in context manager",
                exception=str(e),
                exception_type=type(e).__name__,
                connection_id=id(session),
            )
            raise
        finally:
            await self.release_session(session)

    async def check_health(self) -> bool:
        """Check the health of the database connection.

        This method executes a simple query to verify the connection is working.
        It updates the _is_healthy flag and _last_health_check timestamp.
        It also updates the circuit breaker state based on the health check result.

        Returns:
            bool: True if the connection is healthy, False otherwise

        """
        try:
            # Use a direct session instead of session_context to avoid recursion
            session = AsyncSession(
                asyncio_engine,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            try:
                result = await session.execute(select(1))
                value = result.scalar_one()
                if value == 1:
                    self._is_healthy = True
                    self._last_health_check = datetime.now(UTC)
                    # Reset circuit breaker failures on successful health check
                    self._reset_circuit_failures()
                    logfire.debug(
                        "Database connection health check passed",
                        connection_id=id(session),
                        circuit_open=self._circuit_open,
                        consecutive_failures=self._consecutive_failures,
                    )
                    return True
                self._is_healthy = False
                # Update circuit breaker on failed health check
                self._update_circuit_failure()
                logfire.warning(
                    f"Database health check failed: unexpected value {value}",
                    expected=1,
                    actual=value,
                    connection_id=id(session),
                    circuit_open=self._circuit_open,
                    consecutive_failures=self._consecutive_failures,
                )
                return False
            finally:
                await session.close()
        except Exception as e:  # noqa: BLE001
            self._is_healthy = False
            # Update circuit breaker on exception
            self._update_circuit_failure()
            logfire.exception(
                "Database health check failed",
                exception=str(e),
                exception_type=type(e).__name__,
                circuit_open=self._circuit_open,
                consecutive_failures=self._consecutive_failures,
            )
            return False

    async def reconnect(self) -> None:
        """Attempt to reconnect to the database.

        This method uses the reconnect function with retry logic to
        reestablish the database connection after a failure.
        It also updates the circuit breaker state based on the reconnection result.

        Raises:
            Exception: If the reconnection cannot be established after retries
            RuntimeError: If the circuit breaker is open

        """
        # Check if circuit breaker is open
        if self._is_circuit_open():
            # Check if it's time to try closing the circuit
            if self._should_attempt_circuit_reset():
                logfire.info(
                    "Circuit breaker is open but attempting reconnection after recovery time",
                    last_failure=self._last_failure_time,
                    recovery_time=self._circuit_recovery_time,
                    consecutive_failures=self._consecutive_failures,
                )
                # Continue with reconnection attempt
            else:
                # Circuit is open and it's not time to try closing it
                logfire.warning(
                    "Circuit breaker is open, skipping reconnection attempt",
                    last_failure=self._last_failure_time,
                    recovery_time=self._circuit_recovery_time,
                    consecutive_failures=self._consecutive_failures,
                )
                error_msg = "Database reconnection unavailable: circuit breaker open"
                raise RuntimeError(error_msg)

        # Attempt to reconnect to the database with retry logic
        reconnection_attempt = "Attempting database reconnection"
        logfire.debug(reconnection_attempt)
        try:
            self._connection_attempts += 1
            await reconnect_db()
            self._is_healthy = True
            self._last_health_check = datetime.now(UTC)
            # Reset circuit breaker on successful reconnection
            self._reset_circuit()
            logfire.info(
                "Successfully reconnected to database",
                connection_attempts=self._connection_attempts,
                connection_failures=self._connection_failures,
                circuit_open=self._circuit_open,
                consecutive_failures=self._consecutive_failures,
            )
        except RetryError as e:
            # Handle retry exhaustion specifically
            self._connection_failures += 1
            self._is_healthy = False
            self._update_circuit_failure()
            logfire.exception(
                "Reconnection retry attempts exhausted",
                exception=str(e),
                exception_type=type(e).__name__,
                connection_attempts=self._connection_attempts,
                connection_failures=self._connection_failures,
                circuit_open=self._circuit_open,
                consecutive_failures=self._consecutive_failures,
                retry_attempts=SETTINGS.get_reconnect_retry_attempts(),
            )
            raise
        except Exception as e:
            self._connection_failures += 1
            self._is_healthy = False
            self._update_circuit_failure()
            logfire.exception(
                "Failed to reconnect to database",
                exception=str(e),
                exception_type=type(e).__name__,
                connection_attempts=self._connection_attempts,
                connection_failures=self._connection_failures,
                circuit_open=self._circuit_open,
                consecutive_failures=self._consecutive_failures,
            )
            raise

    def _should_perform_health_check(self) -> bool:
        """Determine if a health check should be performed.

        This method checks if the health check interval has elapsed since the last check.

        Returns:
            bool: True if a health check should be performed, False otherwise

        """
        time_since_last_check = (datetime.now(UTC) - self._last_health_check).total_seconds()
        return time_since_last_check >= self._health_check_interval

    def _is_circuit_open(self) -> bool:
        """Check if the circuit breaker is open.

        Returns:
            bool: True if the circuit breaker is open, False otherwise

        """
        return self._circuit_open

    def _should_attempt_circuit_reset(self) -> bool:
        """Determine if an attempt should be made to reset the circuit breaker.

        This method checks if enough time has passed since the last failure
        to attempt to close the circuit breaker.

        Returns:
            bool: True if a reset attempt should be made, False otherwise

        """
        if not self._last_failure_time:
            return True

        time_since_failure = (datetime.now(UTC) - self._last_failure_time).total_seconds()
        return time_since_failure >= self._circuit_recovery_time

    def _update_circuit_failure(self) -> None:
        """Update the circuit breaker state after a failure.

        This method increments the consecutive failures counter and
        updates the last failure timestamp. If the number of consecutive
        failures exceeds the threshold, it opens the circuit breaker.
        """
        self._consecutive_failures += 1
        self._last_failure_time = datetime.now(UTC)

        # Check if we should open the circuit
        if self._consecutive_failures >= self._circuit_threshold:
            self._circuit_open = True
            logfire.warning(
                "Circuit breaker opened due to consecutive failures",
                consecutive_failures=self._consecutive_failures,
                threshold=self._circuit_threshold,
            )

    def _reset_circuit_failures(self) -> None:
        """Reset the consecutive failures counter.

        This method is called after a successful operation to reset
        the consecutive failures counter, but does not close the circuit
        if it is already open.
        """
        self._consecutive_failures = 0

    def _reset_circuit(self) -> None:
        """Reset the circuit breaker to a closed state.

        This method resets the consecutive failures counter and
        closes the circuit breaker.
        """
        self._consecutive_failures = 0
        self._circuit_open = False
        self._last_failure_time = None


# Create a global connection manager instance
connection_manager = ConnectionManager()
