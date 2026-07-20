"""
Tests for generic resource listing endpoints (/api/{resource_name}).
"""

from unittest.mock import patch


def test_invalid_resource_name(client, valid_auth_headers):
    """Test accessing an unknown resource name returns 404 Not Found."""
    with patch("app.execute_query") as mock_execute:
        mock_execute.return_value = [{"Username": "testuser", "StaffName": "Test", "UserRole": "JMO"}]
        response = client.get("/api/unknown-resource-xyz", headers=valid_auth_headers)
        assert response.status_code == 404
        assert "Resource not found" in response.json()["detail"]


@patch("app.check_permission")
@patch("app.execute_query")
def test_list_staff_resource(mock_execute, mock_perm, client, valid_auth_headers):
    """Test listing staff resources with permission."""
    mock_execute.side_effect = [
        # user query
        [{"Username": "testuser", "StaffName": "Test User", "UserRole": "JMO"}],
        # staff table select
        [
            {"StaffID": 1, "StaffName": "Dr. R. Gunawardena", "Role": "Senior Pathologist", "ContactNo": "011-2345678", "Email": "dr.gunawardena@forensic.lk"}
        ]
    ]
    mock_perm.return_value = True

    response = client.get("/api/staff", headers=valid_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["full_name"] == "Dr. R. Gunawardena"
    assert data[0]["employee_number"] == "EMP-1"


@patch("app.check_permission")
@patch("app.execute_query")
def test_resource_permission_denied(mock_execute, mock_perm, client, valid_auth_headers):
    """Test accessing resource without permission returns 403 Forbidden."""
    mock_execute.return_value = [{"Username": "testuser", "StaffName": "Test User", "UserRole": "Observer"}]
    mock_perm.return_value = False

    response = client.get("/api/audit-logs", headers=valid_auth_headers)
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]
