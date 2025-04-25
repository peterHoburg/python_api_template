"""Tests for middleware functionality."""

from fastapi.testclient import TestClient

from pat.main import app


def test_security_headers():
    """Test that security headers are added to responses."""
    client = TestClient(app)
    response = client.get("/")

    # Check that security headers are present
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"


def test_cors_headers():
    """Test that CORS headers are added to responses."""
    client = TestClient(app)

    # Send a preflight request
    response = client.options(
        "/",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    # Check that CORS headers are present
    assert response.headers.get("Access-Control-Allow-Origin")
    assert response.headers.get("Access-Control-Allow-Methods")
    assert response.headers.get("Access-Control-Allow-Headers")
