from enum import Enum
from typing import ClassVar

import logfire
from pydantic import AnyHttpUrl, PostgresDsn, SecretStr, ValidationInfo, field_validator
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

    # Error messages
    AUTH0_DOMAIN_NOT_CONFIGURED: ClassVar[str] = "Auth0 domain is not configured"
    AUTH0_CLIENT_ID_NOT_CONFIGURED: ClassVar[str] = "Auth0 client ID is not configured"
    # Using noqa to ignore S105 warning for this specific case
    AUTH0_CLIENT_SECRET_NOT_CONFIGURED: ClassVar[str] = "Auth0 client secret is not configured"  # noqa: S105
    AUTH0_AUDIENCE_NOT_CONFIGURED: ClassVar[str] = "Auth0 audience is not configured"
    AUTH0_CALLBACK_URL_NOT_CONFIGURED: ClassVar[str] = "Auth0 callback URL is not configured"

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

    # Auth0 configuration
    auth0_domain: str | None = None
    """
    Auth0 domain (e.g., 'your-tenant.auth0.com').
    Required for Auth0 integration.
    """

    auth0_client_id: str | None = None
    """
    Auth0 client ID.
    Required for Auth0 integration.
    """

    auth0_client_secret: SecretStr | None = None
    """
    Auth0 client secret.
    Required for Auth0 integration.
    """

    auth0_audience: str | None = None
    """
    Auth0 API audience (identifier).
    Required for Auth0 integration.
    """

    auth0_callback_url: AnyHttpUrl | None = None  # pyright: ignore [reportAssignmentType]
    """
    URL to redirect to after authentication.
    Required for Auth0 integration.
    """

    def is_auth0_enabled(self) -> bool:
        """Check if Auth0 integration is enabled by verifying all required settings are provided."""
        return all(
            [
                self.auth0_domain,
                self.auth0_client_id,
                self.auth0_client_secret,
                self.auth0_audience,
                self.auth0_callback_url,
            ]
        )

    def get_auth0_domain(self) -> str:
        """Get the Auth0 domain, raising an error if not configured."""
        if not self.auth0_domain:
            raise ValueError(self.AUTH0_DOMAIN_NOT_CONFIGURED)
        return self.auth0_domain

    def get_auth0_client_id(self) -> str:
        """Get the Auth0 client ID, raising an error if not configured."""
        if not self.auth0_client_id:
            raise ValueError(self.AUTH0_CLIENT_ID_NOT_CONFIGURED)
        return self.auth0_client_id

    def get_auth0_client_secret(self) -> str:
        """Get the Auth0 client secret, raising an error if not configured."""
        if not self.auth0_client_secret:
            raise ValueError(self.AUTH0_CLIENT_SECRET_NOT_CONFIGURED)
        return self.auth0_client_secret.get_secret_value()

    def get_auth0_audience(self) -> str:
        """Get the Auth0 audience, raising an error if not configured."""
        if not self.auth0_audience:
            raise ValueError(self.AUTH0_AUDIENCE_NOT_CONFIGURED)
        return self.auth0_audience

    def get_auth0_callback_url(self) -> str:
        """Get the Auth0 callback URL, raising an error if not configured."""
        if not self.auth0_callback_url:
            raise ValueError(self.AUTH0_CALLBACK_URL_NOT_CONFIGURED)
        return str(self.auth0_callback_url)

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
    def assemble_postgres_uri(cls, v: str | None, values: ValidationInfo) -> str | None:  # noqa: N805
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

    @field_validator("auth0_domain", "auth0_client_id", "auth0_client_secret", "auth0_audience", "auth0_callback_url")
    def validate_auth0_settings(
        cls,  # noqa: N805
        v: str | SecretStr | AnyHttpUrl | None,
        info: ValidationInfo,
    ) -> str | SecretStr | AnyHttpUrl | None:
        """Validate that all Auth0 settings are provided if any are provided."""
        # If this specific field is not set, just return it
        if v is None:
            return v

        # Get all Auth0 settings
        values = info.data
        auth0_settings = {
            "auth0_domain": values.get("auth0_domain"),
            "auth0_client_id": values.get("auth0_client_id"),
            "auth0_client_secret": values.get("auth0_client_secret"),
            "auth0_audience": values.get("auth0_audience"),
            "auth0_callback_url": values.get("auth0_callback_url"),
        }

        # Check if any Auth0 settings are provided
        if any(auth0_settings.values()):
            # If any are provided, all must be provided
            missing = [k for k, v in auth0_settings.items() if v is None]
            if missing:
                missing_fields = ", ".join(missing)
                error_message = (
                    f"Auth0 integration requires all Auth0 settings to be provided. Missing: {missing_fields}"
                )
                raise ValueError(error_message)

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
environment_name = str(SETTINGS.environment)
logfire.info(f"Starting application in {environment_name} environment")
