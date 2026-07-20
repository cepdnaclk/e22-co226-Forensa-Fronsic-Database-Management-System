"""
Tests for authentication & authorization endpoints (/api/auth/signup, /api/auth/login).
"""

from unittest.mock import patch


def test_signup_validation_error(client):
    """Test signup with short password fails Pydantic validation (422)."""
    payload = {
        "username": "testuser",
        "full_name": "Test User",
        "role": "Senior Pathologist",
        "password": "123"  # Password length must be >= 6
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 422


def test_signup_empty_username(client):
    """Test signup with empty username fails (400)."""
    payload = {
        "username": "   ",
        "full_name": "Test User",
        "role": "Senior Pathologist",
        "password": "password123"
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 400
    assert "Username cannot be empty" in response.json()["detail"]


@patch("app.execute_query")
def test_signup_duplicate_user(mock_execute_query, client):
    """Test signing up an existing username returns 400 Bad Request."""
    # Return user found on check_user query
    mock_execute_query.return_value = [{"UserID": 1}]

    payload = {
        "username": "existinguser",
        "full_name": "Existing User",
        "role": "Senior Pathologist",
        "password": "password123"
    }
    response = client.post("/api/auth/signup", json=payload)
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]


@patch("app.execute_query")
def test_login_invalid_credentials(mock_execute_query, client):
    """Test login with wrong password returns 401 Unauthorized."""
    # Return user with password "correctpass"
    mock_execute_query.return_value = [{"Username": "john", "Password": "correctpass", "StaffName": "John", "UserRole": "JMO"}]

    payload = {
        "username": "john",
        "password": "wrongpassword"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


@patch("app.execute_query")
def test_login_success(mock_execute_query, client):
    """Test successful login returns token and user info."""
    mock_execute_query.return_value = [{"Username": "john", "Password": "password123", "StaffName": "Dr. John", "UserRole": "JMO"}]

    payload = {
        "username": "john",
        "password": "password123"
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["username"] == "john"
    assert data["token"].startswith("mock-token-")


def test_protected_route_without_token(client):
    """Test accessing protected cases endpoint without Authorization header fails with 401."""
    response = client.get("/api/cases")
    assert response.status_code == 401
    assert "Missing or invalid authentication token" in response.json()["detail"]


def test_protected_route_invalid_token(client):
    """Test accessing protected route with malformed token returns 401."""
    headers = {"Authorization": "Bearer invalid-token-string"}
    response = client.get("/api/cases", headers=headers)
    assert response.status_code == 401
    assert "Invalid token format" in response.json()["detail"]
