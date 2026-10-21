from flask import Blueprint, render_template, session
from routes.auth_routes import login_required, role_required
from database.db import get_db_connection
from services.sla_service import get_sla_status

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

        # Fetch Critical Emergency Escalations requiring immediate physical technician dispatch
        cursor.execute("""
            SELECT 
                i.issue_id, i.issue_type, i.location, i.description, 
                i.severity, i.priority, i.status, i.recurrence_risk,
                i.sla_deadline, i.created_at, i.resolved_at,
                t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE (i.priority = 'Critical' OR i.severity = 'Critical')
              AND i.status NOT IN ('Resolved', 'Closed')
            ORDER BY i.created_at ASC
            LIMIT 4
        """)
        critical_emergencies = [dict(r) for r in cursor.fetchall()]
        for c in critical_emergencies:
            c["sla"] = get_sla_status(c.get("sla_deadline"), c.get("status"), c.get("resolved_at"))

        # Fetch Kanban: 1. Awaiting Dispatch / Assigned
        cursor.execute("""
            SELECT i.issue_id, i.issue_type, i.location, i.description, i.priority, i.status, 
                   i.recurrence_risk, i.sla_deadline, i.created_at, i.resolved_at, t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE i.status = 'Assigned'
            ORDER BY i.created_at ASC
            LIMIT 8
        """)
        pending_issues = [dict(r) for r in cursor.fetchall()]
        for p in pending_issues:
            p["sla"] = get_sla_status(p.get("sla_deadline"), p.get("status"), p.get("resolved_at"))

        # Fetch Kanban: 2. Under Repair / In Progress
        cursor.execute("""
            SELECT i.issue_id, i.issue_type, i.location, i.description, i.priority, i.status, 
                   i.recurrence_risk, i.sla_deadline, i.created_at, i.resolved_at, t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE i.status = 'In Progress'
            ORDER BY i.created_at ASC
            LIMIT 8
        """)
        in_progress_issues = [dict(r) for r in cursor.fetchall()]
        for p in in_progress_issues:
            p["sla"] = get_sla_status(p.get("sla_deadline"), p.get("status"), p.get("resolved_at"))

        # Fetch Kanban: 3. Recently Resolved / Quality Verification
        cursor.execute("""
            SELECT i.issue_id, i.issue_type, i.location, i.description, i.priority, i.status, 
                   i.recurrence_risk, i.sla_deadline, i.created_at, i.resolved_at, t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE i.status IN ('Resolved', 'Closed')
            ORDER BY i.resolved_at DESC, i.created_at DESC
            LIMIT 8
        """)
        resolved_issues = [dict(r) for r in cursor.fetchall()]
        for r in resolved_issues:
            r["sla"] = get_sla_status(r.get("sla_deadline"), r.get("status"), r.get("resolved_at"))

        # Fetch Available Maintenance Teams
        cursor.execute("SELECT team_id, team_name FROM maintenance_teams ORDER BY team_name ASC")
        teams = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "maintenance/dashboard.html",
        stats=stats,
        critical_emergencies=critical_emergencies,
        pending_issues=pending_issues,
        in_progress_issues=in_progress_issues,
        resolved_issues=resolved_issues,
        teams=teams,
        user_name=session.get("name")
    )
