from fastapi import status
from fastapi.testclient import TestClient

from pat.main import app


def test_root_endpoint():
    """Test that the root endpoint returns the expected response."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Welcome to the Python API Template"}
