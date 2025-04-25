"""Tests for API versioning functionality."""

from fastapi import status
from fastapi.testclient import TestClient

from pat.main import app


def test_root_endpoint():
    """Test that the root endpoint returns the expected response."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Welcome to the Python API Template"}


def test_api_v1_health_endpoint():
    """Test that the v1 health endpoint returns the expected response."""
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


def test_api_docs_endpoint():
    """Test that the API docs endpoint is accessible."""
    client = TestClient(app)
    response = client.get("/api/docs")
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]


def test_api_redoc_endpoint():
    """Test that the API redoc endpoint is accessible."""
    client = TestClient(app)
    response = client.get("/api/redoc")
    assert response.status_code == status.HTTP_200_OK
    assert "text/html" in response.headers["content-type"]


def test_api_openapi_endpoint():
    """Test that the OpenAPI schema is accessible."""
    client = TestClient(app)
    response = client.get("/api/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/json"
    # Verify some expected keys in the OpenAPI schema
    openapi_schema = response.json()
    assert "openapi" in openapi_schema
    assert "paths" in openapi_schema
    # The path in the OpenAPI schema includes the API prefix
    assert "/api/v1/health" in openapi_schema["paths"]
