"""Tests for the health check endpoint and response model."""

import pytest
from fastapi.testclient import TestClient

from pat.main import app
from pat.schemas.schemas import HealthCheckResponse


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app.

    Returns:
        TestClient: A test client for the FastAPI app.
    """
    return TestClient(app)


def test_health_check_response_model() -> None:
    """Test the HealthCheckResponse model."""
    # Test valid data
    health_data = {"status": "healthy"}
    health_response = HealthCheckResponse(**health_data)
    assert health_response.status == "healthy"

    # Test model validation
    with pytest.raises(ValueError, match="1 validation error"):
        HealthCheckResponse()  # type: ignore[call-arg] # Missing required field


def test_health_check_endpoint(client: TestClient) -> None:
    """Test the health check endpoint."""
    # HTTP status code for OK
    http_200_ok = 200
    response = client.get("/api/v1/health")
    assert response.status_code == http_200_ok

    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["status"] == "healthy"
