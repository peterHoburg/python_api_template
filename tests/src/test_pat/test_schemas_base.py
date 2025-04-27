"""Tests for base Pydantic models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from pat.schemas.base import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseSchema,
    BaseUpdateSchema,
    normalize_string,
    validate_email,
)


class TestBaseSchema:
    """Tests for the BaseSchema class."""

    def test_strip_strings(self):
        """Test that string values are automatically stripped."""

        class TestModel(BaseSchema):
            name: str
            description: str | None = None

        # Test stripping on initialization
        model = TestModel(name="  Test Name  ", description="  Test Description  ")
        assert model.name == "Test Name"
        assert model.description == "Test Description"

        # Test with None values
        model = TestModel(name="Test", description=None)
        assert model.description is None

    def test_camel_case_serialization(self):
        """Test that fields are serialized to camelCase."""

        class TestModel(BaseSchema):
            first_name: str
            last_name: str

        model = TestModel(first_name="John", last_name="Doe")
        data = model.model_dump(by_alias=True)
        assert "firstName" in data
        assert "lastName" in data
        assert "first_name" not in data
        assert "last_name" not in data

    def test_from_orm_compatibility(self):
        """Test the from_orm compatibility method."""

        class TestModel(BaseSchema):
            id: int
            name: str

        # Create a mock ORM object (could be any object with the right attributes)
        class MockORM:
            id = 1
            name = "Test"

        model = TestModel.from_orm(MockORM())
        assert model.id == 1
        assert model.name == "Test"

    def test_dict_compatibility(self):
        """Test the dict compatibility method."""

        class TestModel(BaseSchema):
            id: int
            name: str

        model = TestModel(id=1, name="Test")
        data = model.dict()
        assert data == {"id": 1, "name": "Test"}


class TestBaseCreateSchema:
    """Tests for the BaseCreateSchema class."""

    def test_inheritance(self):
        """Test that BaseCreateSchema inherits from BaseSchema."""

        class TestCreateModel(BaseCreateSchema):
            name: str
            email: str

        model = TestCreateModel(name="Test", email="test@example.com")
        assert model.name == "Test"
        assert model.email == "test@example.com"

        # Test that it inherits the string stripping behavior
        model = TestCreateModel(name="  Test  ", email="  test@example.com  ")
        assert model.name == "Test"
        assert model.email == "test@example.com"


class TestBaseUpdateSchema:
    """Tests for the BaseUpdateSchema class."""

    def test_optional_fields(self):
        """Test that fields in update schema can be omitted."""

        class TestUpdateModel(BaseUpdateSchema):
            name: str | None = None
            email: str | None = None
            age: int | None = None

        # Test with partial data
        model = TestUpdateModel(name="Test")
        assert model.name == "Test"
        assert model.email is None
        assert model.age is None

        # Test with no data
        model = TestUpdateModel()
        assert model.name is None
        assert model.email is None
        assert model.age is None

    def test_ignore_extra_fields(self):
        """Test that extra fields are ignored in update schema."""

        class TestUpdateModel(BaseUpdateSchema):
            name: str | None = None

        # Extra fields should be ignored
        data = {"name": "Test", "extra_field": "Extra"}
        model = TestUpdateModel.model_validate(data)
        assert model.name == "Test"
        assert not hasattr(model, "extra_field")


class TestBaseResponseSchema:
    """Tests for the BaseResponseSchema class."""

    def test_required_fields(self):
        """Test that required fields are enforced."""

        class TestResponseModel(BaseResponseSchema):
            name: str

        # Test with all required fields
        now = datetime.now(tz=UTC)
        model = TestResponseModel(id=1, created_at=now, updated_at=now, name="Test")
        assert model.id == 1
        assert model.created_at == now
        assert model.updated_at == now
        assert model.name == "Test"

        # Test missing required fields
        with pytest.raises(ValidationError):
            # Use model_validate_json to test validation with missing fields
            TestResponseModel.model_validate_json('{"name": "Test"}')


class TestValidationMethods:
    """Tests for the validation methods."""

    def test_validate_email(self):
        """Test the email validation function."""
        # Test valid email
        assert validate_email("test@example.com") == "test@example.com"

        # Test email with whitespace
        assert validate_email("  test@example.com  ") == "test@example.com"

        # Test email with uppercase
        assert validate_email("TEST@EXAMPLE.COM") == "test@example.com"

    def test_normalize_string(self):
        """Test the string normalization function."""
        # Test normal string
        assert normalize_string("Test") == "Test"

        # Test string with whitespace
        assert normalize_string("  Test  ") == "Test"

        # Test empty string
        assert normalize_string("") is None
        assert normalize_string("   ") is None

        # Test None
        assert normalize_string(None) is None
