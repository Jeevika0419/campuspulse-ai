import io
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database.db import get_db_connection

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client

def login_user(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

def test_student_report_issue(client):
    """Verifies that a student can report an issue with priority and SLA calculation."""
    login_user(client, "student@campuspulse.edu", "Student@123")

    # Create dummy image
    image_data = (io.BytesIO(b"fake image bytes content"), "broken_projector.jpg")

    response = client.post("/issues/report", data={
        "issue_type": "Projector & Display AV",
        "location": "Academic Block A - 2nd Floor",
        "severity": "High",
        "description": "HDMI feed not detecting laptops; projector bulb flashing orange.",
        "image": image_data
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"reported successfully" in response.data or b"Work Order" in response.data

    # Check database entry
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT issue_id, status, priority, image_path, sla_deadline 
        FROM issues 
        WHERE description LIKE '%HDMI feed not detecting%'
        ORDER BY issue_id DESC LIMIT 1
    """)
    issue = cursor.fetchone()

    # Check audit log
    cursor.execute("SELECT * FROM issue_history WHERE issue_id = %s", (issue["issue_id"],))
    history = cursor.fetchall()

    cursor.close()
    conn.close()

    assert issue is not None
    assert issue["status"] == "Reported"
    assert issue["priority"] == "High"
    assert issue["image_path"] is not None
    assert issue["sla_deadline"] is not None
    assert len(history) >= 1

def test_admin_assign_team(client):
    """Verifies that an admin can assign a maintenance team to an issue."""
    # Find latest reported issue
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT issue_id FROM issues ORDER BY issue_id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    assert row is not None
    issue_id = row["issue_id"]

    login_user(client, "admin@campuspulse.edu", "Admin@123")

    response = client.post(f"/issues/{issue_id}/assign", data={
        "team_id": "4",  # AV team
        "priority": "Critical",
        "remarks": "Assigned to AV team for urgent lab replacement."
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"successfully assigned" in response.data or b"Assigned" in response.data

    # Verify database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT assigned_team, status, priority FROM issues WHERE issue_id = %s", (issue_id,))
    updated_issue = cursor.fetchone()
    cursor.close()
    conn.close()

    assert updated_issue["assigned_team"] == 4
    assert updated_issue["status"] == "Assigned"
    assert updated_issue["priority"] == "Critical"

def test_maintenance_status_transition(client):
    """Verifies that maintenance staff can update issue status and upload resolution proof."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT issue_id FROM issues ORDER BY issue_id DESC LIMIT 1")
    issue_id = cursor.fetchone()["issue_id"]
    cursor.close()
    conn.close()

    login_user(client, "staff@campuspulse.edu", "Staff@123")

    # 1. Update to In Progress
    client.post(f"/issues/{issue_id}/update-status", data={
        "status": "In Progress",
        "remarks": "Technician on site inspecting projector cables."
    }, follow_redirects=True)

    # 2. Update to Resolved with proof
    proof_image = (io.BytesIO(b"fake proof image bytes"), "resolution_proof.png")
    response = client.post(f"/issues/{issue_id}/update-status", data={
        "status": "Resolved",
        "remarks": "Replaced faulty HDMI transmitter; projector display confirmed working.",
        "resolution_image": proof_image
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"status updated to Resolved" in response.data or b"Resolved" in response.data

    # Verify resolved_at and resolution_image in database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status, resolved_at, resolution_image FROM issues WHERE issue_id = %s", (issue_id,))
    resolved_issue = cursor.fetchone()
    cursor.close()
    conn.close()

    assert resolved_issue["status"] == "Resolved"
    assert resolved_issue["resolved_at"] is not None
    assert resolved_issue["resolution_image"] is not None

def test_student_feedback_and_rating(client):
    """Verifies student can rate the resolution of their issue."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT issue_id, reported_by FROM issues ORDER BY issue_id DESC LIMIT 1")
    issue = cursor.fetchone()
    cursor.close()
    conn.close()

    # Log in as student
    login_user(client, "student@campuspulse.edu", "Student@123")

    response = client.post(f"/issues/{issue['issue_id']}/feedback", data={
        "rating": "5",
        "comment": "Quick turnaround! Projector works perfectly now."
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"feedback have been recorded" in response.data or b"Student Resolution Rating" in response.data

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT feedback_rating, feedback_comment FROM issues WHERE issue_id = %s", (issue["issue_id"],))
    rated_issue = cursor.fetchone()
    cursor.close()
    conn.close()

    assert rated_issue["feedback_rating"] == 5
    assert "Quick turnaround" in rated_issue["feedback_comment"]

def test_reopen_issue_workflow(client):
    """Verifies student can reopen an issue if the fix did not last."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT issue_id FROM issues ORDER BY issue_id DESC LIMIT 1")
    issue_id = cursor.fetchone()["issue_id"]
    cursor.close()
    conn.close()

    login_user(client, "student@campuspulse.edu", "Student@123")

    response = client.post(f"/issues/{issue_id}/reopen", data={
        "remarks": "Display started blinking again during afternoon lecture."
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"reopened" in response.data

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status, resolved_at FROM issues WHERE issue_id = %s", (issue_id,))
    reopened_issue = cursor.fetchone()
    cursor.close()
    conn.close()

    assert reopened_issue["status"] == "Reopened"
    assert reopened_issue["resolved_at"] is None

def test_unauthorized_admin_action_blocked(client):
    """A student must NOT be able to assign teams or perform admin overrides."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT issue_id FROM issues ORDER BY issue_id DESC LIMIT 1")
    issue_id = cursor.fetchone()["issue_id"]
    cursor.close()
    conn.close()

    login_user(client, "student@campuspulse.edu", "Student@123")

    response = client.post(f"/issues/{issue_id}/assign", data={
        "team_id": "1",
        "priority": "Low"
    }, follow_redirects=True)

    # Should be blocked and redirected
    assert response.status_code == 200
    assert b"Access denied" in response.data or b"Student Portal" in response.data
