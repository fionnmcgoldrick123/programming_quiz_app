"""
Example test file for backend.
Run with: pytest
"""

import pytest
from fastapi.testclient import TestClient


# Example test - you can add actual tests based on your endpoints
def test_example():
    """Basic test example."""
    assert 1 + 1 == 2


# Uncomment when you want to test actual endpoints
# from main import app
# client = TestClient(app)
#
# def test_read_root():
#     """Test root endpoint."""
#     response = client.get("/")
#     assert response.status_code == 200
#
# def test_health_check():
#     """Test health check endpoint if you have one."""
#     response = client.get("/health")
#     assert response.status_code == 200
