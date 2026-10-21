from flask import Blueprint, render_template, session
from routes.auth_routes import login_required, role_required
from database.db import get_db_connection
from services.notification_service import get_user_notifications

student_bp = Blueprint("student", __name__, url_prefix="/student")

@student_bp.route("/dashboard")
@login_required
@role_required("student")
def dashboard():
    user_id = session.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch Student KPI Metrics from real database
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_reported,
                SUM(CASE WHEN status IN ('Reported', 'Under Review', 'Assigned', 'In Progress', 'Reopened') THEN 1 ELSE 0 END) AS open_issues,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_issues,
                SUM(CASE WHEN status = 'Reopened' THEN 1 ELSE 0 END) AS reopened_issues
            FROM issues
            WHERE reported_by = %s
        """, (user_id,))
        stats = cursor.fetchone() or {
            "total_reported": 0,
            "open_issues": 0,
            "resolved_issues": 0,
            "reopened_issues": 0
        }

        # Handle None values if table has no rows
        stats["total_reported"] = stats["total_reported"] or 0
        stats["open_issues"] = stats["open_issues"] or 0
        stats["resolved_issues"] = stats["resolved_issues"] or 0
        stats["reopened_issues"] = stats["reopened_issues"] or 0

        # Fetch Recent Issues reported by this student
        cursor.execute("""
            SELECT 
                i.issue_id,
                i.issue_type,
                i.location,
                i.description,
                i.severity,
                i.priority,
                i.status,
                i.created_at,
                i.resolved_at,
                t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE i.reported_by = %s
            ORDER BY i.created_at DESC
            LIMIT 10
        """, (user_id,))
        recent_issues = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    notifications = get_user_notifications(user_id, limit=5)
    active_issue = next((dict(i) for i in recent_issues if i.get("status") in ("Reported", "Under Review", "Assigned", "In Progress")), None)

    return render_template(
        "student/dashboard.html",
        stats=stats,
        recent_issues=recent_issues,
        active_issue=active_issue,
        notifications=notifications,
        user_name=session.get("name")
    )
