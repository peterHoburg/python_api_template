from enum import Enum

import logfire
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings that can be loaded from environment variables."""

    # Environment configuration
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT

    # Database configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "admin"
    postgres_password: str = "root"  # noqa: S105
    postgres_db: str = "test_db"
    postgres_uri: PostgresDsn | None = None  # pyright: ignore [reportAssignmentType]

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
