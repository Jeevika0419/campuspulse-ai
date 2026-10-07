from flask import Blueprint, render_template, session
from routes.auth_routes import login_required, role_required
from database.db import get_db_connection

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Global KPI Metrics from database
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_issues,
                SUM(CASE WHEN status IN ('Reported', 'Under Review', 'Assigned', 'In Progress', 'Reopened') THEN 1 ELSE 0 END) AS open_issues,
                SUM(CASE WHEN severity = 'Critical' OR priority = 'Critical' THEN 1 ELSE 0 END) AS critical_issues,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_issues,
                SUM(CASE WHEN recurrence_risk = 'High' THEN 1 ELSE 0 END) AS recurring_issues,
                ROUND(AVG(CASE WHEN resolved_at IS NOT NULL THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) ELSE NULL END), 1) AS avg_resolution_hours
            FROM issues
        """)
        stats = cursor.fetchone() or {
            "total_issues": 0,
            "open_issues": 0,
            "critical_issues": 0,
            "resolved_issues": 0,
            "recurring_issues": 0,
            "avg_resolution_hours": 0
        }

        # Null safety
        for k in stats:
            if stats[k] is None:
                stats[k] = 0

        # 2. Issues by Category
        cursor.execute("""
            SELECT issue_type, COUNT(*) AS count
            FROM issues
            GROUP BY issue_type
            ORDER BY count DESC
            LIMIT 6
        """)
        category_stats = cursor.fetchall()

        # 3. Problem Hotspots by Location
        cursor.execute("""
            SELECT location, COUNT(*) AS issue_count,
                   SUM(CASE WHEN severity = 'Critical' THEN 1 ELSE 0 END) AS critical_count
            FROM issues
            GROUP BY location
            ORDER BY issue_count DESC
            LIMIT 5
        """)
        hotspot_locations = cursor.fetchall()

        # 4. Recent Issues List with Reporter and Assigned Team
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
                i.created_at,
                u.name AS reporter_name,
                t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN users u ON i.reported_by = u.user_id
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            ORDER BY i.created_at DESC
            LIMIT 10
        """)
        recent_issues = cursor.fetchall()

        # 5. Maintenance Teams and Workload
        cursor.execute("""
            SELECT 
                t.team_id,
                t.team_name,
                t.team_description,
                COUNT(i.issue_id) AS active_tasks
            FROM maintenance_teams t
            LEFT JOIN issues i ON t.team_id = i.assigned_team AND i.status IN ('Assigned', 'In Progress')
            GROUP BY t.team_id, t.team_name, t.team_description
        """)
        teams = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        category_stats=category_stats,
        hotspot_locations=hotspot_locations,
        recent_issues=recent_issues,
        teams=teams,
        user_name=session.get("name")
    )
