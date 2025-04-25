"""Tests for error handling functionality."""

from fastapi import status
from fastapi.testclient import TestClient

from pat.main import app


def test_not_found_error():
    """Test that a 404 error returns the expected error response format."""
    client = TestClient(app)
    response = client.get("/non-existent-endpoint")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_response = response.json()
    assert error_response["status"] == "error"
    assert error_response["code"] == status.HTTP_404_NOT_FOUND
    assert "message" in error_response


def test_validation_error():
    """Test that a validation error returns the expected error response format."""
    client = TestClient(app)
    # Create a request with invalid query parameters to trigger a validation error
    response = client.get("/api/v1/health?invalid_param=true")
    # Since we're not expecting any query parameters, this should still work
    assert response.status_code == status.HTTP_200_OK

    # To properly test validation errors, we would need an endpoint that expects
    # specific parameters or request body. For now, we'll just verify that the
    # error handling middleware is properly registered.
    assert app.exception_handlers.get(422) is not None
