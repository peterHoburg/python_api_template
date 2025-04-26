"""Main application file for the Python API Template."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import logfire
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from pat.api.middleware import setup_middlewares
from pat.api.responses import http_exception_handler, validation_exception_handler
from pat.api.router import api_router
from pat.utils.db import asyncio_engine, connection_manager


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, Any]:
    """Lifespan context manager for the FastAPI application.

    This handles startup and shutdown events for the application.
    During startup, it initializes the database connection manager,
    which provides robust connection handling with retries and health checks.

    Args:
        _app: The FastAPI application

    Yields:
        None

    """
    logfire.info("Starting application")
    try:
        # Initialize the connection manager, which handles retries and health checks
        await connection_manager.initialize()
        logfire.info("Database connection manager initialized successfully")
        yield
    except Exception as e:
        logfire.exception("Failed to initialize application", exception=str(e), exception_type=type(e).__name__)
        raise
    finally:
        logfire.info("Shutting down application")
        await asyncio_engine.dispose()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured FastAPI application

    """
    # Create the FastAPI application
    application = FastAPI(
        title="Python API Template",
        description="A template for building FastAPI applications",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Set up exception handlers
    application.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[reportArgumentType]
    application.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[reportArgumentType]
    # Register exception handlers for specific status codes
    application.add_exception_handler(404, http_exception_handler)  # type: ignore[reportArgumentType]
    application.add_exception_handler(422, validation_exception_handler)  # type: ignore[reportArgumentType]

    # Set up middleware
    setup_middlewares(application)

    # Include the API router with a prefix
    application.include_router(api_router, prefix="/api")

    # Add a root endpoint for basic health check
    @application.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint for basic health check.

        Returns:
            dict: A dictionary with a welcome message

        """
        return {"message": "Welcome to the Python API Template"}

    return application


# Create the FastAPI application
app = create_application()
