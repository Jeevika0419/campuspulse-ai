import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from services.analytics_service import (
    get_kpi_summary,
    get_chart_data,
    get_hotspot_clusters,
    get_team_performance_metrics
)
from database.db import get_db_connection

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client

def login_user(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

def test_analytics_service_metrics():
    """Verifies that analytics service computes KPI summary and chart feeds from DB."""
    summary = get_kpi_summary()
    assert "total_issues" in summary
    assert "open_issues" in summary
    assert "sla_breaches" in summary
    assert summary["total_issues"] >= 10

    charts = get_chart_data()
    assert "categories" in charts
    assert "severities" in charts
    assert "statuses" in charts
    assert len(charts["categories"]["labels"]) > 0

    hotspots = get_hotspot_clusters()
    assert len(hotspots) > 0
    assert "location" in hotspots[0]
    assert "issue_count" in hotspots[0]

    teams = get_team_performance_metrics()
    assert len(teams) > 0
    assert "team_name" in teams[0]
    assert "completion_rate" in teams[0]

def test_admin_dashboard_renders_analytics(client):
    """Verifies admin dashboard renders with KPI metrics and chart canvases."""
    login_user(client, "admin@campuspulse.edu", "Admin@123")
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Executive Infrastructure Analytics" in response.data
    assert b"categoryChart" in response.data
    assert b"trendChart" in response.data
    assert b"Problem Hotspots" in response.data

def test_admin_teams_management(client):
    """Verifies admin can view and create new maintenance teams."""
    login_user(client, "admin@campuspulse.edu", "Admin@123")
    
    # 1. View teams page
    response = client.get("/admin/teams")
    assert response.status_code == 200
    assert b"Maintenance Teams" in response.data

    # 2. Add new team
    new_team_name = "Smart IoT Sensors Automation"
    response = client.post("/admin/teams", data={
        "team_name": new_team_name,
        "team_description": "Managing classroom occupancy sensors and energy metering."
    }, follow_redirects=True)
    assert response.status_code == 200
    assert new_team_name.encode() in response.data

    # Verify in DB
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT team_id FROM maintenance_teams WHERE team_name = %s", (new_team_name,))
    team = cursor.fetchone()
    # Consume any remaining results before closing to prevent InternalError
    try:
        cursor.fetchall()
    except Exception:
        pass
    cursor.close()
    conn.close()
    assert team is not None

def test_admin_sla_monitoring_view(client):
    """Verifies SLA monitoring console loads active trackings and countdowns."""
    login_user(client, "admin@campuspulse.edu", "Admin@123")
    response = client.get("/admin/sla-monitoring")
    assert response.status_code == 200
    assert b"SLA &amp; Resolution Escalation Monitor" in response.data or b"SLA & Resolution Escalation Monitor" in response.data
    assert b"Total Tracked Work Orders" in response.data

def test_admin_csv_export(client):
    """Verifies that CSV export endpoint produces a valid formatted CSV file."""
    login_user(client, "admin@campuspulse.edu", "Admin@123")
    response = client.get("/admin/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "attachment; filename=" in response.headers.get("Content-Disposition", "")
    assert b"Issue ID,Category,Location,Description" in response.data

def test_unauthorized_user_blocked_from_admin_analytics(client):
    """Student must be blocked from admin analytics and CSV export."""
    login_user(client, "student@campuspulse.edu", "Student@123")
    
    # Attempt CSV export
    response = client.get("/admin/export/csv", follow_redirects=True)
    assert response.status_code == 200
    assert b"Access denied" in response.data or b"Student Portal" in response.data

    # Attempt teams management
    response = client.get("/admin/teams", follow_redirects=True)
    assert response.status_code == 200
    assert b"Access denied" in response.data or b"Student Portal" in response.data
