"""Middleware for the API to handle security and other cross-cutting concerns."""

import typing

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


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


def setup_middlewares(app: FastAPI) -> None:
    """Set up all middlewares for the application.

    Args:
        app: The FastAPI application

    """
    setup_cors_middleware(app)
    setup_security_headers_middleware(app)
