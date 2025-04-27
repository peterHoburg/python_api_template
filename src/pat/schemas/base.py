"""Base Pydantic models for the application.

This module defines base Pydantic models that provide common functionality,
validation methods, and configuration for all schemas in the application.

The base models include:
- BaseSchema: A base model with common configuration and methods
- BaseCreateSchema: For create operations
- BaseUpdateSchema: For update operations (with all fields optional)
- BaseResponseSchema: For API responses

These models ensure consistent behavior and validation across the application.
"""

from datetime import datetime
from typing import Any, ClassVar, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

T = TypeVar("T", bound="BaseSchema")


class BaseSchema(BaseModel):
    """Base model for all schemas in the application.

    This model provides common configuration and utility methods for all schemas.
    It uses camelCase for JSON and snake_case for Python by default.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        alias_generator=to_camel,
        json_schema_extra={"example": {}},
    )

    @classmethod
    def from_orm(cls, obj: object) -> Self:
        """Create a model instance from an ORM object.

        This method is maintained for backward compatibility with Pydantic v1.
        In Pydantic v2, use `model_validate` instead.

        Args:
            obj: An ORM object

        Returns:
            An instance of this model

        """
        return cls.model_validate(obj)

    def dict(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ANN401
        """Convert the model to a dictionary.

        This method is maintained for backward compatibility with Pydantic v1.
        In Pydantic v2, use `model_dump` instead.

        Args:
            **kwargs: Additional arguments to pass to model_dump

        Returns:
            A dictionary representation of the model

        """
        return self.model_dump(**kwargs)

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v: object) -> object:
        """Strip whitespace from string values.

        Args:
            v: The value to process

        Returns:
            The processed value

        """
        if isinstance(v, str):
            return v.strip()
        return v


class BaseCreateSchema(BaseSchema):
    """Base model for create operations.

    This model is used for creating new resources and includes validation
    specific to creation operations.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        alias_generator=to_camel,
        json_schema_extra={"example": {}},
    )


class BaseUpdateSchema(BaseSchema):
    """Base model for update operations.

    This model is used for updating existing resources. All fields are optional
    to support partial updates.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        alias_generator=to_camel,
        json_schema_extra={"example": {}},
        extra="ignore",  # Ignore extra fields in update operations
    )


class BaseResponseSchema(BaseSchema):
    """Base model for API responses.

    This model is used for API responses and includes common fields for all responses.
    """

    id: int = Field(..., description="Unique identifier for the resource")
    created_at: datetime = Field(..., description="Timestamp when the resource was created")
    updated_at: datetime = Field(..., description="Timestamp when the resource was last updated")

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
        alias_generator=to_camel,
        json_schema_extra={"example": {}},
    )


# Common validation methods


def validate_email(email: str) -> str:
    """Validate and normalize an email address.

    Args:
        email: The email address to validate

    Returns:
        The normalized email address

    Raises:
        ValueError: If the email is invalid

    """
    # EmailStr already validates the email format
    return email.lower().strip()


def normalize_string(value: str | None) -> str | None:
    """Normalize a string by stripping whitespace and converting to None if empty.

    Args:
        value: The string to normalize

    Returns:
        The normalized string or None if empty

    """
    if value is None:
        return None

    normalized = value.strip()
    return normalized if normalized else None
