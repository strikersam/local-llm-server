import pytest
from fastapi.testclient import TestClient
from backend.server import app

@pytest.fixture
def client():
    return TestClient(app)
