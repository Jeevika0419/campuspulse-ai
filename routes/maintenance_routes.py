from flask import Blueprint, render_template, session
from routes.auth_routes import login_required, role_required
from database.db import get_db_connection

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/maintenance")

@maintenance_bp.route("/dashboard")
@login_required
@role_required("maintenance")
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Maintenance KPI Metrics from real database
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_assigned,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'Assigned' THEN 1 ELSE 0 END) AS pending_start,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved,
                SUM(CASE WHEN severity = 'Critical' OR priority = 'Critical' THEN 1 ELSE 0 END) AS critical_count
            FROM issues
            WHERE assigned_team IS NOT NULL
        """)
        stats = cursor.fetchone() or {
            "total_assigned": 0,
            "in_progress": 0,
            "pending_start": 0,
            "resolved": 0,
            "critical_count": 0
        }

        # Null safety
        for k in stats:
            if stats[k] is None:
                stats[k] = 0

        # Assigned issues for maintenance staff to act upon
        cursor.execute("""
            SELECT 
                i.issue_id,
                i.issue_type,
                i.location,
                i.description,
                i.severity,
                i.priority,
                i.status,
                i.recurrence_risk,
                i.sla_deadline,
                i.created_at,
                u.name AS reporter_name,
                t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN users u ON i.reported_by = u.user_id
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE i.status IN ('Assigned', 'In Progress', 'On Hold')
            ORDER BY 
                CASE 
                    WHEN i.priority = 'Critical' THEN 1
                    WHEN i.priority = 'High' THEN 2
                    WHEN i.priority = 'Medium' THEN 3
                    ELSE 4
                END,
                i.created_at ASC
            LIMIT 15
        """)
        assigned_issues = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "maintenance/dashboard.html",
        stats=stats,
        assigned_issues=assigned_issues,
        user_name=session.get("name")
    )
