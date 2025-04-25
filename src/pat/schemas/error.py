"""Error response schemas"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
    request_id: str | None = Field(default=None, description="Unique identifier for the request")


class ValidationErrorDetail(BaseModel):
    """Details for a validation error."""

    loc: list[str] = Field(..., description="Location of the validation error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(ErrorResponse):
    """Error response for validation errors."""

    validation_details: list[ValidationErrorDetail] = Field(
        default_factory=list, description="Validation error details"
    )
