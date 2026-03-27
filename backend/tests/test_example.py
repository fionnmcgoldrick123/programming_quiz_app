"""
Example test file for backend.
Run with: pytest
"""

import pytest
from fastapi.testclient import TestClient


# Example test — additional tests should be added to cover API endpoints.
def test_example():
    """Basic test example."""
    assert 1 + 1 == 2


# Uncomment the block below to test actual API endpoints.
# from main import app
# client = TestClient(app)
#
# def test_read_root():
#     """Test root endpoint."""
#     response = client.get("/")
#     assert response.status_code == 200
#
# def test_health_check():
#     """Test the health check endpoint."""
#     response = client.get("/health")
#     assert response.status_code == 200
