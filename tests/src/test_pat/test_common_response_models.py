"""Tests for common response models."""

from datetime import UTC, datetime

import pytest

from pat.schemas.schemas import MessageResponse, PaginatedResponse, UserResponse


def test_paginated_response_model() -> None:
    """Test the PaginatedResponse model."""
    # Constants for test data
    total_items = 10
    page_number = 1
    page_size = 2
    total_pages = 5
    first_user_id = 1
    second_user_id = 2
    invalid_page_number = 0

    # Create some sample items
    items = [
        UserResponse(
            id=first_user_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            created_at=datetime(2023, 1, 1, tzinfo=UTC),
            updated_at=datetime(2023, 1, 1, tzinfo=UTC),
        ),
        UserResponse(
            id=second_user_id,
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            created_at=datetime(2023, 1, 2, tzinfo=UTC),
            updated_at=datetime(2023, 1, 2, tzinfo=UTC),
        ),
    ]

    # Test valid data
    paginated_data = {
        "items": items,
        "total": total_items,
        "page": page_number,
        "size": page_size,
        "pages": total_pages,
    }
    paginated_response = PaginatedResponse[UserResponse](**paginated_data)
    assert paginated_response.total == total_items
    assert paginated_response.page == page_number
    assert paginated_response.size == page_size
    assert paginated_response.pages == total_pages
    assert len(paginated_response.items) == page_size
    assert paginated_response.items[0].id == first_user_id
    assert paginated_response.items[1].id == second_user_id

    # Test model validation
    with pytest.raises(ValueError, match="5 validation errors"):
        PaginatedResponse[UserResponse]()  # type: ignore[call-arg] # Missing required fields

    with pytest.raises(ValueError, match="1 validation error"):
        PaginatedResponse[UserResponse](
            items=items,
            total=total_items,
            page=invalid_page_number,  # Invalid page number (should be >= 1)
            size=page_size,
            pages=total_pages,
        )


def test_message_response_model() -> None:
    """Test the MessageResponse model."""
    # Test valid data with only message
    message_response = MessageResponse(message="Operation successful", details=None)
    assert message_response.message == "Operation successful"
    assert message_response.details is None

    # Test valid data with message and details
    message_data_with_details = {
        "message": "Operation successful",
        "details": {"id": 123, "status": "completed"},
    }
    message_response = MessageResponse(**message_data_with_details)
    assert message_response.message == "Operation successful"
    assert message_response.details == {"id": 123, "status": "completed"}

    # Test model validation
    with pytest.raises(ValueError, match="1 validation error"):
        MessageResponse()  # type: ignore[call-arg] # Missing required field

    with pytest.raises(ValueError, match="1 validation error"):
        MessageResponse(details={"id": 123})  # type: ignore[call-arg] # Missing message field
