from datetime import datetime
from database.db import get_db_connection
from services.sla_service import get_sla_status

def get_kpi_summary():
    """Computes executive level KPI metrics for admin console."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_issues,
                SUM(CASE WHEN status IN ('Reported', 'Under Review', 'Assigned', 'In Progress', 'On Hold', 'Reopened') THEN 1 ELSE 0 END) AS open_issues,
                SUM(CASE WHEN severity = 'Critical' OR priority = 'Critical' THEN 1 ELSE 0 END) AS critical_issues,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_issues,
                SUM(CASE WHEN recurrence_risk = 'High' THEN 1 ELSE 0 END) AS recurring_issues,
                ROUND(AVG(CASE WHEN resolved_at IS NOT NULL THEN TIMESTAMPDIFF(HOUR, created_at, resolved_at) ELSE NULL END), 1) AS avg_resolution_hours,
                ROUND(AVG(CASE WHEN feedback_rating IS NOT NULL THEN feedback_rating ELSE NULL END), 1) AS avg_satisfaction_rating
            FROM issues
        """)
        summary = cursor.fetchone() or {}

        for k in summary:
            if summary[k] is None:
                summary[k] = 0

        # Calculate SLA breaches dynamically
        cursor.execute("""
            SELECT status, sla_deadline, resolved_at 
            FROM issues 
            WHERE sla_deadline IS NOT NULL
        """)
        rows = cursor.fetchall()
        breaches_count = 0
        approaching_count = 0
        now = datetime.now()

        for r in rows:
            sla_info = get_sla_status(r["sla_deadline"], r["status"], r["resolved_at"])
            if sla_info["is_breached"]:
                breaches_count += 1
            elif not sla_info["is_breached"] and r["status"] not in ("Resolved", "Closed"):
                # Approaching if less than 2 hours remaining
                diff = r["sla_deadline"] - now
                if 0 <= diff.total_seconds() <= 7200:
                    approaching_count += 1

        summary["sla_breaches"] = breaches_count
        summary["sla_approaching"] = approaching_count
        return summary
    finally:
        cursor.close()
        conn.close()

def get_chart_data():
    """Extracts aggregated data formatted for Chart.js visualizations."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Category Distribution
        cursor.execute("""
            SELECT issue_type, COUNT(*) AS count
            FROM issues
            GROUP BY issue_type
            ORDER BY count DESC
        """)
        categories = cursor.fetchall()

        # 2. Severity Distribution
        cursor.execute("""
            SELECT severity, COUNT(*) AS count
            FROM issues
            GROUP BY severity
        """)
        severities = cursor.fetchall()

        # 3. Status Distribution
        cursor.execute("""
            SELECT status, COUNT(*) AS count
            FROM issues
            GROUP BY status
        """)
        statuses = cursor.fetchall()

        # 4. Monthly Trend (last 6 months)
        cursor.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%b %Y') AS month_label,
                COUNT(*) AS total_count,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_count
            FROM issues
            GROUP BY DATE_FORMAT(created_at, '%b %Y'), YEAR(created_at), MONTH(created_at)
            ORDER BY YEAR(created_at) ASC, MONTH(created_at) ASC
            LIMIT 6
        """)
        monthly_trends = cursor.fetchall()

        return {
            "categories": {
                "labels": [c["issue_type"] for c in categories],
                "data": [c["count"] for c in categories]
            },
            "severities": {
                "labels": [s["severity"] for s in severities],
                "data": [s["count"] for s in severities]
            },
            "statuses": {
                "labels": [st["status"] for st in statuses],
                "data": [st["count"] for st in statuses]
            },
            "trends": {
                "labels": [t["month_label"] for t in monthly_trends],
                "reported": [t["total_count"] for t in monthly_trends],
                "resolved": [t["resolved_count"] for t in monthly_trends]
            },
            "trend": {
                "labels": [t["month_label"] for t in monthly_trends],
                "reported": [t["total_count"] for t in monthly_trends],
                "resolved": [t["resolved_count"] for t in monthly_trends]
            }
        }
    finally:
        cursor.close()
        conn.close()

def get_hotspot_clusters():
    """Calculates campus hotspot density ranking with critical cluster count."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                location,
                COUNT(*) AS issue_count,
                SUM(CASE WHEN severity = 'Critical' OR priority = 'Critical' THEN 1 ELSE 0 END) AS critical_count,
                SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_count,
                SUM(CASE WHEN recurrence_risk = 'High' THEN 1 ELSE 0 END) AS recurring_count
            FROM issues
            GROUP BY location
            ORDER BY issue_count DESC
            LIMIT 8
        """)
        hotspots = cursor.fetchall()
        return hotspots
    finally:
        cursor.close()
        conn.close()

def get_team_performance_metrics():
    """Calculates team workload, resolution efficiency, and turnaround time."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                t.team_id,
                t.team_name,
                t.team_description,
                COUNT(i.issue_id) AS total_assigned,
                SUM(CASE WHEN i.status IN ('Assigned', 'In Progress', 'On Hold') THEN 1 ELSE 0 END) AS active_workload,
                SUM(CASE WHEN i.status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS completed_tasks,
                ROUND(AVG(CASE WHEN i.resolved_at IS NOT NULL THEN TIMESTAMPDIFF(HOUR, i.created_at, i.resolved_at) ELSE NULL END), 1) AS avg_turnaround_hours
            FROM maintenance_teams t
            LEFT JOIN issues i ON t.team_id = i.assigned_team
            GROUP BY t.team_id, t.team_name, t.team_description
            ORDER BY active_workload DESC
        """)
        teams = cursor.fetchall()
        for tm in teams:
            if tm["avg_turnaround_hours"] is None:
                tm["avg_turnaround_hours"] = 0.0
            tm["completion_rate"] = (
                round((tm["completed_tasks"] / tm["total_assigned"]) * 100, 1)
                if tm["total_assigned"] > 0 else 0.0
            )
        return teams
    finally:
        cursor.close()
        conn.close()
