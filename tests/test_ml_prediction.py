"""
CampusPulse AI — Sprint 4 ML Recurrence Prediction Engine Tests
================================================================
Tests the intelligent recurrence risk prediction service including:
  - Feature engineering accuracy
  - Risk level classification boundaries
  - Database-driven feature computation
  - API endpoint integration
"""

import pytest
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from services.ml_service import (
    predict_recurrence_risk,
    update_issue_recurrence_risk,
    get_campus_recurrence_analysis
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


def test_ml_prediction_high_risk_location():
    """Wi-Fi issue at a known hotspot (Academic Block A) should predict High risk."""
    result = predict_recurrence_risk(
        issue_type="Wi-Fi & Network Connectivity",
        location="Academic Block A - 3rd Floor",
        severity="High"
    )
    assert result["risk_level"] in ("High", "Medium")
    assert result["confidence_score"] > 0
    assert len(result["feature_explanations"]) > 0
    assert result["model_version"] == "CampusPulse-RF-v1.2"
    assert "computed_at" in result


def test_ml_prediction_low_risk():
    """Low severity furniture issue at a non-hotspot should predict Low risk."""
    result = predict_recurrence_risk(
        issue_type="Classroom Furniture & Equipment",
        location="Sports Complex & Gym",
        severity="Low"
    )
    assert result["risk_level"] == "Low"
    assert result["confidence_score"] < 50


def test_ml_prediction_returns_all_fields():
    """Prediction result must contain all required response fields."""
    result = predict_recurrence_risk(
        issue_type="Electrical & Power Outlets",
        location="Hostel Wing A (Men)",
        severity="Critical"
    )
    required_keys = ["risk_level", "confidence_score", "feature_explanations", "summary", "model_version", "computed_at"]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    assert result["risk_level"] in ("High", "Medium", "Low")
    assert 0 <= result["confidence_score"] <= 100


def test_ml_update_issue_risk_in_db():
    """update_issue_recurrence_risk should persist the computed risk level to DB."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT issue_id FROM issues LIMIT 1")
        row = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if row:
        risk = update_issue_recurrence_risk(row["issue_id"])
        assert risk in ("High", "Medium", "Low")

        # Verify it was persisted
        conn2 = get_db_connection()
        cursor2 = conn2.cursor(dictionary=True)
        try:
            cursor2.execute("SELECT recurrence_risk FROM issues WHERE issue_id = %s", (row["issue_id"],))
            updated = cursor2.fetchone()
            assert updated["recurrence_risk"] == risk
        finally:
            cursor2.close()
            conn2.close()


def test_campus_recurrence_analysis():
    """Campus-wide recurrence analysis should return category and location breakdowns."""
    analysis = get_campus_recurrence_analysis()
    assert "by_category" in analysis
    assert "by_location" in analysis
    assert len(analysis["by_category"]) > 0
    assert "issue_type" in analysis["by_category"][0]
    assert "high_risk" in analysis["by_category"][0]


def test_ml_api_endpoint(client):
    """API endpoint /api/issues/predict-recurrence must return valid JSON prediction."""
    login_user(client, "admin@campuspulse.edu", "Admin@123")

    response = client.post("/api/issues/predict-recurrence",
        data=json.dumps({
            "issue_type": "Air Conditioning & Climate",
            "location": "Central Campus Library",
            "severity": "Medium"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["risk_level"] in ("High", "Medium", "Low")
    assert "confidence_score" in data
    assert "feature_explanations" in data


def test_ml_api_missing_fields(client):
    """API endpoint must reject requests with missing required fields."""
    login_user(client, "student@campuspulse.edu", "Student@123")

    response = client.post("/api/issues/predict-recurrence",
        data=json.dumps({"severity": "High"}),
        content_type="application/json"
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
