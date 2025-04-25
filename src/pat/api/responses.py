"""Standardized response models and error handling for the API."""

from typing import Any, Generic, TypeVar

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Type variable for generic response models
T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    status: str = Field("error", description="Error status indicator")
    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response model."""

    status: str = Field("success", description="Success status indicator")
    data: T = Field(..., description="Response data")


async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions and return standardized error responses.

    Args:
        _request: The request that caused the exception (unused)
        exc: The HTTP exception

    Returns:
        JSONResponse: A standardized error response

    """
    error_response = ErrorResponse(
        status="error",
        code=exc.status_code,
        message=exc.detail,
        details=getattr(exc, "details", None),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation exceptions and return standardized error responses.

    Args:
        _request: The request that caused the exception (unused)
        exc: The validation exception

    Returns:
        JSONResponse: A standardized error response

    """
    error_response = ErrorResponse(
        status="error",
        code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        details={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )
