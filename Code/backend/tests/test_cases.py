"""
Tests for case management API endpoints (/api/cases, /api/incidents).
"""

from unittest.mock import patch


@patch("app.execute_query")
def test_list_cases(mock_execute_query, client, valid_auth_headers):
    """Test GET /api/cases returns list of cases for authenticated user."""
    mock_execute_query.side_effect = [
        # get_current_user query result
        [{"Username": "testuser", "StaffName": "Test User", "UserRole": "JMO"}],
        # list_cases query result
        [
            {
                "CaseID": 1,
                "CaseNumber": "FC-2026-001",
                "CaseType": "Homicide",
                "IncidentDate": "2026-07-10",
                "CaseDescription": "Test Case Title -- Detailed description",
                "Status": "Active",
                "AssignedStaff": "Dr. R. Gunawardena"
            }
        ]
    ]

    response = client.get("/api/cases", headers=valid_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["case_number"] == "FC-2026-001"
    assert data[0]["title"] == "Test Case Title"


@patch("app.check_permission")
@patch("app.execute_query")
def test_create_case_permission_denied(mock_execute, mock_perm, client, valid_auth_headers):
    """Test POST /api/cases without permission returns 403 Forbidden."""
    mock_execute.return_value = [{"Username": "testuser", "StaffName": "Test User", "UserRole": "Observer"}]
    mock_perm.return_value = False

    payload = {
        "case_number": "FC-2026-999",
        "title": "Unauthorized Case",
        "case_type": "Homicide",
        "status": "Active",
        "opened_date": "2026-07-20",
        "description": "Test"
    }
    response = client.post("/api/cases", json=payload, headers=valid_auth_headers)
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]


@patch("app.check_permission")
@patch("app.execute_query")
def test_create_case_duplicate_number(mock_execute, mock_perm, client, valid_auth_headers):
    """Test POST /api/cases with duplicate case number returns 409 Conflict."""
    mock_execute.side_effect = [
        # get_current_user query
        [{"Username": "testuser", "StaffName": "Test User", "UserRole": "JMO"}],
        # check_query (case exists)
        [{"CaseID": 10}]
    ]
    mock_perm.return_value = True

    payload = {
        "case_number": "FC-2026-001",
        "title": "Duplicate Case",
        "case_type": "Homicide",
        "status": "Active",
        "opened_date": "2026-07-20",
        "description": "Test description"
    }
    response = client.post("/api/cases", json=payload, headers=valid_auth_headers)
    assert response.status_code == 409
    assert "Case number already exists" in response.json()["detail"]


@patch("app.find_case")
@patch("app.check_permission")
@patch("app.execute_query")
def test_delete_case_success(mock_execute, mock_perm, mock_find, client, valid_auth_headers):
    """Test DELETE /api/cases/{case_id} succeeds with 204 No Content."""
    def mock_query_fn(query, params=None, fetch=True):
        if "UserAccount" in query:
            return [{"Username": "testuser", "UserID": 1, "StaffName": "Test User", "UserRole": "JMO"}]
        return []

    mock_execute.side_effect = mock_query_fn
    mock_perm.return_value = True
    mock_find.return_value = {"id": 1, "case_number": "FC-2026-001"}

    response = client.delete("/api/cases/1", headers=valid_auth_headers)
    assert response.status_code == 204

