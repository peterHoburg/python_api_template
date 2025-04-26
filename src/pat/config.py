from enum import Enum

import logfire
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings that can be loaded from environment variables.

    Database Connection Configuration:
    - ENVIRONMENT: The environment type (development, testing, production)
    - POSTGRES_HOST: The PostgreSQL host (default: localhost)
    - POSTGRES_PORT: The PostgreSQL port (default: 5432)
    - POSTGRES_USER: The PostgreSQL user (default: admin)
    - POSTGRES_PASSWORD: The PostgreSQL password (default: root)
    - POSTGRES_DB: The PostgreSQL database name (default: test_db)
    - POSTGRES_URI: The full PostgreSQL URI (if provided, overrides individual components)

    Connection Pooling Configuration:
    - POSTGRES_POOL_SIZE: Number of connections to keep open in the pool
    - POSTGRES_MAX_OVERFLOW: Maximum number of connections to create above pool_size
    - POSTGRES_POOL_TIMEOUT: Seconds to wait before giving up on getting a connection
    - POSTGRES_POOL_RECYCLE: Seconds after which a connection is automatically recycled
    - POSTGRES_POOL_PRE_PING: Whether to verify connections before using them (default: True)

    Connection Retry Configuration:
    - POSTGRES_CONNECTION_RETRY_ATTEMPTS: Number of times to retry connecting to the database
    - POSTGRES_CONNECTION_RETRY_MAX_WAIT: Maximum seconds to wait between retry attempts

    If specific pooling or retry parameters are not provided, environment-specific defaults will be used.
    """

    # Environment configuration
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT

    # Database configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "admin"
    postgres_password: str = "root"  # noqa: S105
    postgres_db: str = "test_db"
    postgres_uri: PostgresDsn | None = None  # pyright: ignore [reportAssignmentType]

    # Database connection pooling configuration
    postgres_pool_size: int | None = None
    """
    Number of connections to keep open in the connection pool.
    Default values by environment:
    - development: 5
    - testing: 3
    - production: 10
    """

    postgres_max_overflow: int | None = None
    """
    Maximum number of connections to create above pool_size.
    Default values by environment:
    - development: 10
    - testing: 5
    - production: 20
    """

    postgres_pool_timeout: int | None = None
    """
    Number of seconds to wait before giving up on getting a connection from the pool.
    Default values by environment:
    - development: 30
    - testing: 10
    - production: 60
    """

    postgres_pool_recycle: int | None = None
    """
    Number of seconds after which a connection is automatically recycled (closed and replaced).
    Default values by environment:
    - development: 1800 (30 minutes)
    - testing: 300 (5 minutes)
    - production: 3600 (1 hour)
    """

    postgres_pool_pre_ping: bool = True
    """If True, the pool will emit a "ping" (SELECT 1) before using a connection to verify it's still alive."""

    # Connection retry configuration
    postgres_connection_retry_attempts: int | None = None
    """
    Number of times to retry connecting to the database before giving up.
    Default values by environment:
    - development: 20
    - testing: 10
    - production: 30
    """

    postgres_connection_retry_max_wait: int | None = None
    """
    Maximum number of seconds to wait between connection retry attempts.
    Default values by environment:
    - development: 30
    - testing: 10
    - production: 60
    """

    # Query retry configuration
    postgres_query_retry_attempts: int | None = None
    """
    Number of times to retry database queries before giving up.
    Default values by environment:
    - development: 5
    - testing: 3
    - production: 10
    """

    postgres_query_retry_max_wait: int | None = None
    """
    Maximum number of seconds to wait between query retry attempts.
    Default values by environment:
    - development: 10
    - testing: 5
    - production: 20
    """

    # Reconnection retry configuration
    postgres_reconnect_retry_attempts: int | None = None
    """
    Number of times to retry reconnecting to the database after a connection loss.
    Default values by environment:
    - development: 15
    - testing: 8
    - production: 25
    """

    postgres_reconnect_retry_max_wait: int | None = None
    """
    Maximum number of seconds to wait between reconnection retry attempts.
    Default values by environment:
    - development: 20
    - testing: 8
    - production: 45
    """

    # Circuit breaker configuration
    postgres_circuit_breaker_failure_threshold: int | None = None
    """
    Number of consecutive failures before the circuit breaker opens.
    Default values by environment:
    - development: 5
    - testing: 3
    - production: 10
    """

    postgres_circuit_breaker_recovery_time: int | None = None
    """
    Time in seconds to wait before attempting to close the circuit breaker.
    Default values by environment:
    - development: 30
    - testing: 15
    - production: 60
    """

    # Jitter configuration
    postgres_jitter_factor: float | None = None
    """
    Factor to apply to jitter (0.0-1.0) to randomize retry intervals.
    Default values by environment:
    - development: 0.3
    - testing: 0.2
    - production: 0.5
    """

    def get_pool_size(self) -> int:
        """Get the pool size based on the environment if not explicitly set."""
        if self.postgres_pool_size is not None:
            return self.postgres_pool_size

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 5
        if self.environment == EnvironmentType.TESTING:
            return 3
        if self.environment == EnvironmentType.PRODUCTION:
            return 10
        return 5  # Default fallback

    def get_max_overflow(self) -> int:
        """Get the max overflow based on the environment if not explicitly set."""
        if self.postgres_max_overflow is not None:
            return self.postgres_max_overflow

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 10
        if self.environment == EnvironmentType.TESTING:
            return 5
        if self.environment == EnvironmentType.PRODUCTION:
            return 20
        return 10  # Default fallback

    def get_pool_timeout(self) -> int:
        """Get the pool timeout based on the environment if not explicitly set."""
        if self.postgres_pool_timeout is not None:
            return self.postgres_pool_timeout

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 30
        if self.environment == EnvironmentType.TESTING:
            return 10
        if self.environment == EnvironmentType.PRODUCTION:
            return 60
        return 30  # Default fallback

    def get_pool_recycle(self) -> int:
        """Get the pool recycle time based on the environment if not explicitly set."""
        if self.postgres_pool_recycle is not None:
            return self.postgres_pool_recycle

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 1800  # 30 minutes
        if self.environment == EnvironmentType.TESTING:
            return 300  # 5 minutes
        if self.environment == EnvironmentType.PRODUCTION:
            return 3600  # 1 hour
        return 1800  # Default fallback

    def get_connection_retry_attempts(self) -> int:
        """Get the number of connection retry attempts based on the environment if not explicitly set."""
        if self.postgres_connection_retry_attempts is not None:
            return self.postgres_connection_retry_attempts

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 20
        if self.environment == EnvironmentType.TESTING:
            return 10
        if self.environment == EnvironmentType.PRODUCTION:
            return 30
        return 20  # Default fallback

    def get_connection_retry_max_wait(self) -> int:
        """Get the maximum wait time between connection retry attempts.

        Returns the value based on the environment if not explicitly set.
        """
        if self.postgres_connection_retry_max_wait is not None:
            return self.postgres_connection_retry_max_wait

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 30
        if self.environment == EnvironmentType.TESTING:
            return 10
        if self.environment == EnvironmentType.PRODUCTION:
            return 60
        return 30  # Default fallback

    def get_query_retry_attempts(self) -> int:
        """Get the number of query retry attempts based on the environment if not explicitly set."""
        if self.postgres_query_retry_attempts is not None:
            return self.postgres_query_retry_attempts

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 5
        if self.environment == EnvironmentType.TESTING:
            return 3
        if self.environment == EnvironmentType.PRODUCTION:
            return 10
        return 5  # Default fallback

    def get_query_retry_max_wait(self) -> int:
        """Get the maximum wait time between query retry attempts.

        Returns the value based on the environment if not explicitly set.
        """
        if self.postgres_query_retry_max_wait is not None:
            return self.postgres_query_retry_max_wait

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 10
        if self.environment == EnvironmentType.TESTING:
            return 5
        if self.environment == EnvironmentType.PRODUCTION:
            return 20
        return 10  # Default fallback

    def get_reconnect_retry_attempts(self) -> int:
        """Get the number of reconnection retry attempts based on the environment if not explicitly set."""
        if self.postgres_reconnect_retry_attempts is not None:
            return self.postgres_reconnect_retry_attempts

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 15
        if self.environment == EnvironmentType.TESTING:
            return 8
        if self.environment == EnvironmentType.PRODUCTION:
            return 25
        return 15  # Default fallback

    def get_reconnect_retry_max_wait(self) -> int:
        """Get the maximum wait time between reconnection retry attempts.

        Returns the value based on the environment if not explicitly set.
        """
        if self.postgres_reconnect_retry_max_wait is not None:
            return self.postgres_reconnect_retry_max_wait

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 20
        if self.environment == EnvironmentType.TESTING:
            return 8
        if self.environment == EnvironmentType.PRODUCTION:
            return 45
        return 20  # Default fallback

    def get_circuit_breaker_failure_threshold(self) -> int:
        """Get the circuit breaker failure threshold based on the environment if not explicitly set."""
        if self.postgres_circuit_breaker_failure_threshold is not None:
            return self.postgres_circuit_breaker_failure_threshold

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 5
        if self.environment == EnvironmentType.TESTING:
            return 3
        if self.environment == EnvironmentType.PRODUCTION:
            return 10
        return 5  # Default fallback

    def get_circuit_breaker_recovery_time(self) -> int:
        """Get the circuit breaker recovery time based on the environment if not explicitly set."""
        if self.postgres_circuit_breaker_recovery_time is not None:
            return self.postgres_circuit_breaker_recovery_time

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 30
        if self.environment == EnvironmentType.TESTING:
            return 15
        if self.environment == EnvironmentType.PRODUCTION:
            return 60
        return 30  # Default fallback

    def get_jitter_factor(self) -> float:
        """Get the jitter factor based on the environment if not explicitly set."""
        if self.postgres_jitter_factor is not None:
            return self.postgres_jitter_factor

        if self.environment == EnvironmentType.DEVELOPMENT:
            return 0.3
        if self.environment == EnvironmentType.TESTING:
            return 0.2
        if self.environment == EnvironmentType.PRODUCTION:
            return 0.5
        return 0.3  # Default fallback

    @field_validator("postgres_uri", mode="before")
    def assemble_postgres_uri(cls, v, values) -> str:  # noqa: N805, ANN001
        """Assemble the PostgreSQL URI from individual components if not provided."""
        if v:
            return v

        host = values.data.get("postgres_host")
        port = values.data.get("postgres_port")
        user = values.data.get("postgres_user")
        password = values.data.get("postgres_password")
        db = values.data.get("postgres_db")

        if all([host, user, password, db]):
            return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )


# Load settings from environment variables
SETTINGS = Settings()

# Configure logging
logfire.configure()
logfire.info(f"Starting application in {SETTINGS.environment} environment")
