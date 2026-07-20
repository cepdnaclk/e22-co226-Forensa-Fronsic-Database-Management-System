"""
Tests for health check endpoints and static frontend page serving.
"""

def test_health_check(client):
    """Test /api/health endpoint returns status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "database" in data


def test_root_frontend_serving(client):
    """Test root endpoint / serves index.html."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Forensic" in response.text or "Ministry of Health" in response.text


def test_public_pages(client):
    """Test fetching public static HTML page fragments."""
    for page in ["about_us", "contact_us", "login", "signup"]:
        response = client.get(f"/api/pages/{page}")
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/html")
