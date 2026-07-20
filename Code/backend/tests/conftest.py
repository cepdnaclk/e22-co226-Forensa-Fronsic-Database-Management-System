import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture for API testing."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_auth_headers():
    """Bearer token headers for an authenticated test user."""
    return {"Authorization": "Bearer mock-token-testuser"}


@pytest.fixture
def invalid_auth_headers():
    """Invalid authorization headers."""
    return {"Authorization": "Bearer invalid-token-format"}
