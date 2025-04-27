"""Pydantic schemas for the application.

This module contains Pydantic schemas for data validation and serialization.
These schemas are used for API requests and responses.
"""

from pydantic import EmailStr, Field

from pat.schemas.base import BaseCreateSchema, BaseResponseSchema, BaseSchema, BaseUpdateSchema


class UserBase(BaseSchema):
    """Base schema for User data."""

    first_name: str = Field(..., description="User's first name", max_length=100)
    last_name: str = Field(..., description="User's last name", max_length=100)
    email: EmailStr = Field(..., description="User's email address")


class UserCreate(BaseCreateSchema, UserBase):
    """Schema for creating a new User."""


class UserUpdate(BaseUpdateSchema):
    """Schema for updating an existing User."""

    first_name: str | None = Field(None, description="User's first name", max_length=100)
    last_name: str | None = Field(None, description="User's last name", max_length=100)
    email: EmailStr | None = Field(None, description="User's email address")


class UserResponse(BaseResponseSchema, UserBase):
    """Schema for User response data."""
