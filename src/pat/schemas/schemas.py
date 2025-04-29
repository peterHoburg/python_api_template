"""Pydantic schemas for the application.

This module contains Pydantic schemas for data validation and serialization.
These schemas are used for API requests and responses.
"""

from typing import Any, Generic, TypeVar

from pydantic import EmailStr, Field

from pat.schemas.base import BaseCreateSchema, BaseResponseSchema, BaseSchema, BaseUpdateSchema

T = TypeVar("T")


class HealthCheckResponse(BaseSchema):
    """Response schema for health check endpoint."""

    status: str = Field(..., description="Health status of the service")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Response schema for paginated results."""

    items: list[T] = Field(..., description="List of items in the current page")
    total: int = Field(..., description="Total number of items across all pages", ge=0)
    page: int = Field(..., description="Current page number (1-based)", ge=1)
    size: int = Field(..., description="Number of items per page", gt=0)
    pages: int = Field(..., description="Total number of pages", ge=0)


class MessageResponse(BaseSchema):
    """Response schema for simple message responses."""

    message: str = Field(..., description="Message text")
    details: dict[str, Any] | None = Field(None, description="Additional details")


class UserBase(BaseSchema):
    """Base schema for User data.

    This schema defines the common fields and validation rules for User data.
    It is used as a base for other User-related schemas.
    """

    first_name: str = Field(..., description="User's first name", max_length=100, min_length=1, examples=["John"])
    last_name: str = Field(..., description="User's last name", max_length=100, min_length=1, examples=["Doe"])
    email: EmailStr = Field(..., description="User's email address", examples=["john.doe@example.com"])


class UserCreate(BaseCreateSchema, UserBase):
    """Schema for creating a new User.

    This schema is used for validating data when creating a new User.
    It inherits from BaseCreateSchema for create-specific behavior and UserBase for common fields.
    """


class UserUpdate(BaseUpdateSchema):
    """Schema for updating an existing User.

    This schema is used for validating data when updating an existing User.
    All fields are optional to support partial updates.
    It inherits from BaseUpdateSchema which configures the model for update operations.
    """

    first_name: str | None = Field(None, description="User's first name", max_length=100)
    last_name: str | None = Field(None, description="User's last name", max_length=100)
    email: EmailStr | None = Field(None, description="User's email address")


class UserResponse(BaseResponseSchema, UserBase):
    """Schema for User response data.

    This schema is used for returning User data in API responses.
    It inherits from BaseResponseSchema which adds common response fields (id, created_at, updated_at)
    and from UserBase for the core User fields.
    """


class UserListResponse(BaseSchema):
    """Schema for a list of users, typically used with PaginatedResponse.

    This schema is used for returning a collection of User objects in API responses.
    It can be wrapped in a PaginatedResponse for paginated list endpoints.
    """

    users: list[UserResponse] = Field(..., description="List of users")


class UserDetailResponse(UserResponse):
    """Schema for detailed user information.

    This schema extends UserResponse to provide more detailed information about a user.
    It can be used for endpoints that return comprehensive user data, such as user profile pages.
    Additional fields can be added here to provide more detailed user information beyond
    the basic fields from UserResponse.
    """


class UserFilter(BaseSchema):
    """Schema for filtering users in list operations.

    This schema defines the parameters that can be used to filter user listings.
    It is typically used for GET endpoints that return lists of users, allowing
    clients to filter the results based on various criteria.
    """

    first_name: str | None = Field(None, description="Filter by first name")
    last_name: str | None = Field(None, description="Filter by last name")
    email: str | None = Field(None, description="Filter by email")
    sort_by: str | None = Field(None, description="Field to sort by")
    sort_order: str | None = Field(None, description="Sort order (asc or desc)")
