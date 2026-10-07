"""
CampusPulse AI — Intelligent Recurrence Prediction Engine (Sprint 4)
=====================================================================
Rule-based + feature-weighted ML simulation for issue recurrence risk prediction.

For academic demonstration purposes, this module simulates an ML pipeline
using feature engineering + weighted scoring (analogous to a Random Forest
classifier). In a production AWS deployment this would load a trained
scikit-learn model from S3/local filesystem.

Recurrence Risk Levels:
  - High   → >70% weighted score
  - Medium → 40–70%
  - Low    → <40%
"""

from database.db import get_db_connection
from datetime import datetime, timedelta


# Feature weights (simulates trained feature importances in a Random Forest)
FEATURE_WEIGHTS = {
    "location_hotspot": 0.28,    # Highest weight: repeat locations matter most
    "category_prone":   0.22,    # Category has inherent recurrence likelihood
    "prior_issues":     0.20,    # History of prior issues at same location+category
    "severity_level":   0.15,    # Higher severity issues tend to reappear if not fixed properly
    "time_to_resolve":  0.10,    # Delayed resolution often means incomplete fix
    "reopen_history":   0.05,    # Was this category of issue reopened before?
}

# Known high-recurrence-risk categories (feature: category_prone)
HIGH_RECURRENCE_CATEGORIES = {
    "Wi-Fi & Network Connectivity",
    "Air Conditioning & Climate",
    "Plumbing & Restroom Facilities",
    "Lighting & Illumination",
}

MEDIUM_RECURRENCE_CATEGORIES = {
    "Electrical & Power Outlets",
    "Projector & Display AV",
}

# Known hotspot locations in campus infrastructure
HOTSPOT_LOCATIONS = [
    "Academic Block A",
    "Hostel Wing A",
    "Hostel Wing B",
    "Science & Engineering Lab",
    "Computing & Server Lab",
]


def _score_feature(feature_name: str, value: float) -> float:
    """Returns weighted contribution of a single feature to recurrence score."""
    return FEATURE_WEIGHTS.get(feature_name, 0.0) * min(value, 1.0)


def predict_recurrence_risk(issue_type: str, location: str, severity: str, issue_id: int = None) -> dict:
    """
    Predicts the recurrence risk for a given issue using engineered features.

    Parameters:
        issue_type: Category of infrastructure issue
        location: Campus location
        severity: Reported severity level
        issue_id: Optional existing issue_id for database lookups

    Returns:
        dict with keys: risk_level, confidence_score, explanation
    """
    score = 0.0
    explanations = []

    # Feature 1: Location Hotspot
    location_lower = location.lower()
    if any(h.lower() in location_lower for h in HOTSPOT_LOCATIONS):
        score += _score_feature("location_hotspot", 1.0)
        explanations.append(f"📍 Location '{location}' is a known infrastructure hotspot")
    else:
        score += _score_feature("location_hotspot", 0.2)

    # Feature 2: Category Recurrence Prone
    if issue_type in HIGH_RECURRENCE_CATEGORIES:
        score += _score_feature("category_prone", 1.0)
        explanations.append(f"🔄 Issue type '{issue_type}' has high historical recurrence")
    elif issue_type in MEDIUM_RECURRENCE_CATEGORIES:
        score += _score_feature("category_prone", 0.6)
        explanations.append(f"⚠️ Issue type '{issue_type}' shows moderate recurrence pattern")
    else:
        score += _score_feature("category_prone", 0.2)

    # Feature 3: Severity Level
    severity_scores = {"Critical": 1.0, "High": 0.75, "Medium": 0.4, "Low": 0.1}
    sev_score = severity_scores.get(severity.capitalize(), 0.3)
    score += _score_feature("severity_level", sev_score)
    if sev_score >= 0.75:
        explanations.append(f"🚨 High severity incidents have elevated recurrence probability")

    # Feature 4–6: Database-driven features (prior history, resolution speed, reopens)
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Prior issues at same location with same category
            cursor.execute("""
                SELECT COUNT(*) AS prior_count
                FROM issues
                WHERE location LIKE %s AND issue_type = %s
                AND (%s IS NULL OR issue_id != %s)
            """, (f"%{location.split('-')[0].strip()}%", issue_type, issue_id, issue_id))
            prior = cursor.fetchone()
            prior_count = prior["prior_count"] if prior else 0

            if prior_count >= 3:
                score += _score_feature("prior_issues", 1.0)
                explanations.append(f"📊 {prior_count} prior incidents recorded at this location for same category")
            elif prior_count >= 1:
                score += _score_feature("prior_issues", 0.5)
                explanations.append(f"📊 {prior_count} similar prior incident(s) found at this location")
            else:
                score += _score_feature("prior_issues", 0.0)

            # Average resolution time (slow resolution → incomplete fix → higher recurrence)
            cursor.execute("""
                SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, resolved_at)) AS avg_hours
                FROM issues
                WHERE issue_type = %s AND resolved_at IS NOT NULL
            """, (issue_type,))
            res_row = cursor.fetchone()
            avg_hours = res_row["avg_hours"] if res_row and res_row["avg_hours"] else 0

            if avg_hours > 48:
                score += _score_feature("time_to_resolve", 1.0)
                explanations.append(f"⏳ Avg resolution time for this category is {round(avg_hours, 1)}h — suggests systemic issue")
            elif avg_hours > 12:
                score += _score_feature("time_to_resolve", 0.5)
            else:
                score += _score_feature("time_to_resolve", 0.1)

            # Reopen history for same category
            cursor.execute("""
                SELECT COUNT(*) AS reopen_count
                FROM issues
                WHERE issue_type = %s AND status = 'Reopened'
            """, (issue_type,))
            reopen = cursor.fetchone()
            reopen_count = reopen["reopen_count"] if reopen else 0

            if reopen_count > 0:
                score += _score_feature("reopen_history", 1.0)
                explanations.append(f"🔁 {reopen_count} reopened issues for this category indicate incomplete fixes")
            else:
                score += _score_feature("reopen_history", 0.0)

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        # Graceful degradation if DB unavailable
        score += _score_feature("prior_issues", 0.3)
        explanations.append("⚡ Running in estimation mode (database query skipped)")

    # Convert raw score to risk level
    confidence_pct = round(score * 100, 1)

    if score >= 0.70:
        risk_level = "High"
        summary = "AI engine predicts HIGH likelihood of recurrence. Systemic fix strongly recommended."
    elif score >= 0.40:
        risk_level = "Medium"
        summary = "Moderate recurrence probability. Schedule preventive inspection within 30 days."
    else:
        risk_level = "Low"
        summary = "Low recurrence risk. Standard resolution procedure expected to be sufficient."

    return {
        "risk_level": risk_level,
        "confidence_score": confidence_pct,
        "feature_explanations": explanations,
        "summary": summary,
        "model_version": "CampusPulse-RF-v1.2",
        "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def update_issue_recurrence_risk(issue_id: int) -> str:
    """
    Runs the ML engine on an existing issue and persists the risk level to DB.
    Called after issue is resolved or closed to update the recurrence risk field.

    Returns: New risk level string ('High', 'Medium', 'Low')
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT issue_id, issue_type, location, severity 
            FROM issues WHERE issue_id = %s
        """, (issue_id,))
        issue = cursor.fetchone()
        if not issue:
            return "Low"

        prediction = predict_recurrence_risk(
            issue_type=issue["issue_type"],
            location=issue["location"],
            severity=issue["severity"],
            issue_id=issue_id
        )

        cursor.execute(
            "UPDATE issues SET recurrence_risk = %s WHERE issue_id = %s",
            (prediction["risk_level"], issue_id)
        )
        conn.commit()
        return prediction["risk_level"]
    finally:
        cursor.close()
        conn.close()


def get_campus_recurrence_analysis() -> dict:
    """
    Aggregated campus-wide recurrence analysis for admin dashboard intelligence panel.
    Returns summary statistics grouped by category and location.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # By category
        cursor.execute("""
            SELECT 
                issue_type,
                COUNT(*) AS total,
                SUM(CASE WHEN recurrence_risk = 'High' THEN 1 ELSE 0 END) AS high_risk,
                SUM(CASE WHEN status = 'Reopened' THEN 1 ELSE 0 END) AS reopened,
                ROUND(AVG(CASE WHEN resolved_at IS NOT NULL THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) ELSE NULL END), 1) AS avg_resolution_h
            FROM issues
            GROUP BY issue_type
            ORDER BY high_risk DESC, total DESC
        """)
        by_category = cursor.fetchall()

        # By location
        cursor.execute("""
            SELECT 
                location,
                COUNT(*) AS total,
                SUM(CASE WHEN recurrence_risk = 'High' THEN 1 ELSE 0 END) AS high_risk,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved
            FROM issues
            GROUP BY location
            ORDER BY high_risk DESC, total DESC
            LIMIT 8
        """)
        by_location = cursor.fetchall()

        # Fix None avg_resolution_h
        for row in by_category:
            if row["avg_resolution_h"] is None:
                row["avg_resolution_h"] = 0

        return {
            "by_category": by_category,
            "by_location": by_location
        }
    finally:
        cursor.close()
        conn.close()
