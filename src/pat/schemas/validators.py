"""Custom validators for Pydantic models.

This module provides a collection of custom validators for use with Pydantic models
in the application. These validators implement complex validation logic for common
data types and patterns.

The validators are designed to be reusable across different schemas and provide
clear error messages when validation fails.

Examples:
    ```python
    from pydantic import BaseModel, Field
    from pat.schemas.validators import (
        validate_phone_number,
        validate_url,
        validate_date_range,
    )

    class UserProfile(BaseModel):
        phone: str = Field(..., description="User's phone number")
        website: str = Field(None, description="User's website")
        start_date: date = Field(..., description="Start date")
        end_date: date = Field(None, description="End date")

        _validate_phone = validate_phone_number("phone")
        _validate_website = validate_url("website")
        _validate_dates = validate_date_range("start_date", "end_date")
    ```

Available validators:
    - Phone number validation
    - URL validation
    - Date and date range validation
    - Numeric range validation
    - Alphanumeric string validation
    - Enum value validation
    - Conditional validation
    - Cross-field validation
    - Collection validation
    - Dependent field validation

"""

import re
from collections.abc import Callable
from enum import Enum
from re import Pattern
from typing import Any, TypeVar
from urllib.parse import ParseResult, urlparse

from pydantic import field_validator, model_validator


def validate_phone_number(field_name: str) -> Any:  # noqa: ANN401
    """Validate a phone number field.

    This validator checks if a phone number is in a valid format.
    It supports various international formats.

    Args:
        field_name: The name of the field to validate

    Returns:
        A validator method that can be used as a field validator

    Examples:
        ```python
        class UserModel(BaseModel):
            phone: str = Field(..., description="User's phone number")

            _validate_phone = validate_phone_number("phone")
        ```

    """
    # Regex pattern for international phone numbers
    # Supports formats like:
    # +1 123-456-7890, (123) 456-7890, 123.456.7890, etc.
    pattern = re.compile(r"^\+?[0-9]{1,3}?[-. (]?\(?[0-9]{1,4}\)?[-. ]?[0-9]{1,4}[-. ]?[0-9]{1,9}$")

    @field_validator(field_name, mode="after")
    @classmethod
    def validate(_cls: type, v: str | None) -> str | None:
        if v is None:
            return None

        # Remove any whitespace
        v = v.strip()

        error_message = (
            "Invalid phone number format. Please provide a valid phone number (e.g., +1 123-456-7890, (123) 456-7890)."
        )

        if not pattern.match(v):
            raise ValueError(error_message)
        return v

    return validate


def validate_url(field_name: str, allowed_schemes: set[str] | None = None) -> Any:  # noqa: ANN401
    """Validate a URL field.

    This validator checks if a URL is in a valid format and uses an allowed scheme.

    Args:
        field_name: The name of the field to validate
        allowed_schemes: Optional set of allowed URL schemes (e.g., {'http', 'https'})
                         If None, defaults to {'http', 'https', 'ftp'}

    Returns:
        A validator method that can be used as a field validator

    Examples:
        ```python
        class WebsiteModel(BaseModel):
            url: str = Field(..., description="Website URL")

            # Only allow https URLs
            _validate_url = validate_url("url", allowed_schemes={"https"})
        ```

    """
    if allowed_schemes is None:
        allowed_schemes = {"http", "https", "ftp"}

    @field_validator(field_name, mode="after")
    @classmethod
    def validate(_cls: type, v: str | None) -> str | None:
        if v is None:
            return None

        # Remove any whitespace
        v = v.strip()

        scheme_error_message = "URL must include a scheme (e.g., http://, https://)"
        domain_error_message = "URL must include a valid domain"

        def validate_url_parts(parsed_url: ParseResult) -> None:
            if not parsed_url.scheme:
                raise ValueError(scheme_error_message)

            if parsed_url.scheme not in allowed_schemes:
                schemes_str = ", ".join(allowed_schemes)
                scheme_list_error = f"URL scheme must be one of: {schemes_str}"
                raise ValueError(scheme_list_error)

            if not parsed_url.netloc:
                raise ValueError(domain_error_message)

        try:
            result = urlparse(v)
            validate_url_parts(result)

        except ValueError:
            # Re-raise ValueError directly
            raise
        except Exception as e:
            # For other exceptions, create a new error message
            format_error_message = f"Invalid URL format: {e!s}"
            raise ValueError(format_error_message) from e

        return v

    return validate


def validate_date_range(start_field: str, end_field: str, *, allow_equal: bool = True) -> Any:  # noqa: ANN401
    """Validate that a start date comes before an end date.

    This validator checks if the start date is before (or equal to) the end date.

    Args:
        start_field: The name of the start date field
        end_field: The name of the end date field
        allow_equal: Whether to allow the start and end dates to be equal

    Returns:
        A validator method that can be used as a model validator

    Examples:
        ```python
        class DateRangeModel(BaseModel):
            start_date: date = Field(..., description="Start date")
            end_date: date = Field(..., description="End date")

            _validate_dates = validate_date_range("start_date", "end_date")
        ```

    """

    @model_validator(mode="after")
    def validate(model: Any, _: Any) -> Any:  # noqa: ANN401
        start_date = getattr(model, start_field, None)
        end_date = getattr(model, end_field, None)

        if start_date is not None and end_date is not None:
            if allow_equal:
                if start_date > end_date:
                    error_message = f"{start_field} must be before or equal to {end_field}"
                    raise ValueError(error_message)
            elif start_date >= end_date:
                error_message = f"{start_field} must be before {end_field}"
                raise ValueError(error_message)

        return model

    return validate


def validate_numeric_range(field_name: str, min_value: float | None = None, max_value: float | None = None) -> Any:  # noqa: ANN401
    """Validate that a numeric value is within a specified range.

    Args:
        field_name: The name of the field to validate
        min_value: The minimum allowed value (inclusive)
        max_value: The maximum allowed value (inclusive)

    Returns:
        A validator method that can be used as a field validator

    Examples:
        ```python
        class ProductModel(BaseModel):
            price: float = Field(..., description="Product price")

            _validate_price = validate_numeric_range("price", min_value=0.01)
        ```

    """

    @field_validator(field_name, mode="after")
    @classmethod
    def validate(_cls: type, v: float | None) -> int | float | None:
        if v is None:
            return None

        if min_value is not None and v < min_value:
            if max_value is not None:
                error_message = f"Value must be between {min_value} and {max_value}"
                raise ValueError(error_message)
            error_message = f"Value must be greater than or equal to {min_value}"
            raise ValueError(error_message)

        if max_value is not None and v > max_value:
            if min_value is not None:
                error_message = f"Value must be between {min_value} and {max_value}"
                raise ValueError(error_message)
            error_message = f"Value must be less than or equal to {max_value}"
            raise ValueError(error_message)

        return v

    return validate


def validate_alphanumeric(field_name: str, pattern: Pattern | None = None, error_message: str | None = None) -> Any:  # noqa: ANN401
    """Validate that a string matches a specific pattern.

    Args:
        field_name: The name of the field to validate
        pattern: A compiled regex pattern to match against
        error_message: Custom error message to display on validation failure

    Returns:
        A validator method that can be used as a field validator

    Examples:
        ```python
        class UserModel(BaseModel):
            username: str = Field(..., description="Username")

            # Only allow alphanumeric usernames
            _validate_username = validate_alphanumeric(
                "username",
                pattern=re.compile(r"^[a-zA-Z0-9]+$"),
                error_message="Username must contain only letters and numbers"
            )
        ```

    """
    if pattern is None:
        # Default to alphanumeric pattern
        pattern = re.compile(r"^[a-zA-Z0-9]+$")

    if error_message is None:
        error_message = "Value must match the required pattern"

    @field_validator(field_name, mode="after")
    @classmethod
    def validate(_cls: type, v: str | None) -> str | None:
        if v is None:
            return None

        if not pattern.match(v):
            raise ValueError(error_message)

        return v

    return validate


T = TypeVar("T", bound=Enum)


def validate_enum_value(field_name: str, enum_class: type[T], *, case_insensitive: bool = False) -> Any:  # noqa: ANN401
    """Validate that a value is a valid enum value.

    Args:
        field_name: The name of the field to validate
        enum_class: The Enum class to validate against
        case_insensitive: Whether to perform case-insensitive matching for string values

    Returns:
        A validator method that can be used as a field validator

    Examples:
        ```python
        class UserRole(str, Enum):
            ADMIN = "admin"
            USER = "user"
            GUEST = "guest"

        class UserModel(BaseModel):
            role: str = Field(..., description="User role")

            _validate_role = validate_enum_value("role", UserRole, case_insensitive=True)
        ```

    """

    @field_validator(field_name, mode="before")
    @classmethod
    def validate(_cls: type, v: Any) -> Any:  # noqa: ANN401
        if v is None:
            return None

        # For case-insensitive matching with string enums
        if case_insensitive and isinstance(v, str):
            for enum_value in enum_class:
                if isinstance(enum_value.value, str) and v.lower() == enum_value.value.lower():
                    return enum_value.value

            # If we get here, no match was found
            valid_values = ", ".join(str(e.value) for e in enum_class)
            error_message = f"Value must be one of: {valid_values}"
            raise ValueError(error_message)

        # Standard enum validation
        try:
            return enum_class(v).value
        except (ValueError, TypeError) as e:
            valid_values = ", ".join(str(e.value) for e in enum_class)
            error_message = f"Value must be one of: {valid_values}"
            raise ValueError(error_message) from e

    return validate


def validate_conditional_required(field_name: str, condition_field: str, condition_value: Any) -> Any:  # noqa: ANN401
    """Make a field required only when another field has a specific value.

    Args:
        field_name: The name of the field to conditionally require
        condition_field: The name of the field that determines the requirement
        condition_value: The value of condition_field that makes field_name required

    Returns:
        A validator method that can be used as a model validator

    Examples:
        ```python
        class ShippingModel(BaseModel):
            shipping_method: str = Field(..., description="Shipping method")
            tracking_number: Optional[str] = Field(None, description="Tracking number")

            # Require tracking_number when shipping_method is "express"
            _validate_tracking = validate_conditional_required(
                "tracking_number", "shipping_method", "express"
            )
        ```

    """

    @model_validator(mode="after")
    def validate(model: Any, _: Any) -> Any:  # noqa: ANN401
        condition_value_actual = getattr(model, condition_field, None)
        field_value = getattr(model, field_name, None)

        if condition_value_actual == condition_value and field_value is None:
            error_message = f"Field '{field_name}' is required when '{condition_field}' is '{condition_value}'"
            raise ValueError(error_message)

        return model

    return validate


def validate_cross_fields(fields: list[str], validator_func: Callable[[dict[str, Any]], None]) -> Any:  # noqa: ANN401
    """Apply custom validation across multiple fields.

    Args:
        fields: List of field names involved in the validation
        validator_func: Function that performs the validation
                        It should raise ValueError if validation fails

    Returns:
        A validator method that can be used as a model validator

    Examples:
        ```python
        def validate_address_fields(values: Dict[str, Any]) -> None:
            # Either both street and city must be provided, or neither
            has_street = values.get("street") is not None
            has_city = values.get("city") is not None

            if has_street != has_city:
                raise ValueError("Street and city must be provided together")

        class AddressModel(BaseModel):
            street: Optional[str] = Field(None, description="Street address")
            city: Optional[str] = Field(None, description="City")

            _validate_address = validate_cross_fields(
                ["street", "city"], validate_address_fields
            )
        ```

    """

    @model_validator(mode="after")
    def validate(model: Any, _: Any) -> Any:  # noqa: ANN401
        # Extract only the fields we need for validation
        fields_dict = {field: getattr(model, field, None) for field in fields}

        # Apply the custom validation function
        validator_func(fields_dict)

        return model

    return validate


def validate_collection(
    field_name: str, item_validator: Callable[[Any], Any], *, error_prefix: str = "Item validation failed"
) -> Any:  # noqa: ANN401
    """Validate each item in a collection field.

    Args:
        field_name: The name of the collection field to validate
        item_validator: Function that validates each item
                        Should raise ValueError if validation fails
        error_prefix: Prefix for error messages

    Returns:
        A validator method that can be used as a field validator

    Examples:
        ```python
        def validate_tag(tag: str) -> str:
            if not re.match(r"^[a-z0-9-]+$", tag):
                raise ValueError("Tag must contain only lowercase letters, numbers, and hyphens")
            return tag

        class ArticleModel(BaseModel):
            tags: List[str] = Field(default_factory=list, description="Article tags")

            _validate_tags = validate_collection("tags", validate_tag)
        ```

    """

    @field_validator(field_name, mode="after")
    @classmethod
    def validate(_cls: type, v: list[Any] | None) -> list[Any] | None:
        if v is None:
            return None

        result = []
        errors = []

        for i, item in enumerate(v):
            try:
                validated_item = item_validator(item)
                result.append(validated_item)
            except ValueError as e:
                errors.append(f"Item {i}: {e!s}")

        if errors:
            error_message = f"{error_prefix}: {'; '.join(errors)}"
            raise ValueError(error_message)

        return result

    return validate


def validate_dependent_fields(
    primary_field: str, dependent_fields: list[str], validator_func: Callable[[Any, dict[str, Any]], None]
) -> Any:  # noqa: ANN401
    """Validate dependent fields based on a primary field.

    Args:
        primary_field: The name of the primary field
        dependent_fields: List of dependent field names
        validator_func: Function that validates the relationship
                        It receives the primary field value and a dict of dependent fields
                        Should raise ValueError if validation fails

    Returns:
        A validator method that can be used as a model validator

    Examples:
        ```python
        def validate_payment_fields(payment_type: str, fields: Dict[str, Any]) -> None:
            if payment_type == "credit_card":
                if not fields.get("card_number"):
                    raise ValueError("Card number is required for credit card payments")
            elif payment_type == "bank_transfer":
                if not fields.get("account_number"):
                    raise ValueError("Account number is required for bank transfers")

        class PaymentModel(BaseModel):
            payment_type: str = Field(..., description="Payment type")
            card_number: Optional[str] = Field(None, description="Credit card number")
            account_number: Optional[str] = Field(None, description="Bank account number")

            _validate_payment = validate_dependent_fields(
                "payment_type",
                ["card_number", "account_number"],
                validate_payment_fields
            )
        ```

    """

    @model_validator(mode="after")
    def validate(model: Any, _: Any) -> Any:  # noqa: ANN401
        primary_value = getattr(model, primary_field, None)

        if primary_value is not None:
            # Extract dependent fields
            dependent_values = {field: getattr(model, field, None) for field in dependent_fields}

            # Apply validation
            validator_func(primary_value, dependent_values)

        return model

    return validate
