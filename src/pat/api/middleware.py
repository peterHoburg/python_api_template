"""Middleware for the API to handle security and other cross-cutting concerns."""

import contextlib
import typing
from contextvars import ContextVar

import logfire
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from pat.utils.db import get_session

# Context variable to store the current session
request_session: ContextVar[AsyncSession | None] = ContextVar("request_session", default=None)


def get_request_session() -> AsyncSession | None:
    """Get the current session for the request.

    Returns:
        AsyncSession | None: The current session or None if not in a request context

    """
    return request_session.get()


def setup_cors_middleware(app: FastAPI) -> None:
    """Set up CORS middleware for the application.

    Args:
        app: The FastAPI application

    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, this should be restricted to specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    async def dispatch(self, request: Request, call_next: typing.Callable) -> Response:
        """Add security headers to the response.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response with added security headers

        """
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


def setup_security_headers_middleware(app: FastAPI) -> None:
    """Set up security headers middleware for the application.

    Args:
        app: The FastAPI application

    """
    app.add_middleware(SecurityHeadersMiddleware)


class SessionMiddleware(BaseHTTPMiddleware):
    """Middleware to manage database sessions for requests."""

    async def dispatch(self, request: Request, call_next: typing.Callable) -> Response:
        """Create a session for the request and clean it up afterward.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response: The response from the next middleware or route handler

        """
        # Create a new session for this request
        session_generator = get_session()
        try:
            session = await session_generator.__anext__()
            # Store the session in the context variable
            request_session.set(session)
            logfire.debug("Created database session for request", request_id=str(id(request)))

            # Process the request
            response = await call_next(request)
        except Exception as e:
            logfire.exception("Error processing request with session", exception=str(e))
            raise
        else:
            return response
        finally:
            # Clean up the session
            try:
                if session_generator:
                    with contextlib.suppress(StopAsyncIteration):
                        await session_generator.__anext__()
                logfire.debug("Cleaned up database session for request", request_id=str(id(request)))
            except (RuntimeError, AttributeError) as e:
                logfire.exception("Error cleaning up session", exception=str(e))
            # Reset the context variable
            request_session.set(None)


def setup_session_middleware(app: FastAPI) -> None:
    """Set up session middleware for the application.

    Args:
        app: The FastAPI application

    """
    app.add_middleware(SessionMiddleware)


def setup_middlewares(app: FastAPI) -> None:
    """Set up all middlewares for the application.

    Args:
        app: The FastAPI application

    """
    # Order matters: session middleware should be first to ensure it's available for all requests
    setup_session_middleware(app)
    setup_cors_middleware(app)
    setup_security_headers_middleware(app)
