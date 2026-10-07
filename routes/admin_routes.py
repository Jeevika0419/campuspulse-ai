import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from routes.auth_routes import login_required, role_required
from database.db import get_db_connection
from services.analytics_service import (
    get_kpi_summary,
    get_chart_data,
    get_hotspot_clusters,
    get_team_performance_metrics
)
from services.sla_service import get_sla_status
from database.seed_demo_data import seed_realistic_demo_data

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    stats = get_kpi_summary()
    chart_data = get_chart_data()
    hotspot_clusters = get_hotspot_clusters()
    teams = get_team_performance_metrics()

    # Recent issues stream
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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
                i.resolved_at,
                u.name AS reporter_name,
                t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN users u ON i.reported_by = u.user_id
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            ORDER BY i.created_at DESC
            LIMIT 10
        """)
        raw_issues = cursor.fetchall()
        recent_issues = []
        for issue in raw_issues:
            issue_dict = dict(issue)
            issue_dict["sla"] = get_sla_status(issue["sla_deadline"], issue["status"], issue["resolved_at"])
            recent_issues.append(issue_dict)
    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        chart_data=chart_data,
        hotspot_clusters=hotspot_clusters,
        teams=teams,
        recent_issues=recent_issues,
        user_name=session.get("name")
    )


@admin_bp.route("/teams", methods=["GET", "POST"])
@login_required
@role_required("admin")
def manage_teams():
    if request.method == "POST":
        team_name = request.form.get("team_name", "").strip()
        team_description = request.form.get("team_description", "").strip()

        if not team_name:
            flash("Team name is required.", "danger")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO maintenance_teams (team_name, team_description)
                    VALUES (%s, %s)
                """, (team_name, team_description))
                conn.commit()
                flash(f"Maintenance team '{team_name}' created successfully!", "success")
            except Exception as e:
                conn.rollback()
                flash(f"Error creating team: {str(e)}", "danger")
            finally:
                cursor.close()
                conn.close()
        return redirect(url_for("admin.manage_teams"))

    teams = get_team_performance_metrics()
    return render_template("admin/teams.html", teams=teams)


@admin_bp.route("/sla-monitoring")
@login_required
@role_required("admin")
def sla_monitoring():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                i.issue_id,
                i.issue_type,
                i.location,
                i.severity,
                i.priority,
                i.status,
                i.sla_deadline,
                i.created_at,
                i.resolved_at,
                u.name AS reporter_name,
                t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN users u ON i.reported_by = u.user_id
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE i.sla_deadline IS NOT NULL
            ORDER BY 
                CASE WHEN i.status IN ('Resolved', 'Closed') THEN 2 ELSE 1 END,
                i.sla_deadline ASC
        """)
        raw_issues = cursor.fetchall()

        issues = []
        breached_issues = []
        approaching_issues = []

        for issue in raw_issues:
            issue_dict = dict(issue)
            issue_dict["sla"] = get_sla_status(issue["sla_deadline"], issue["status"], issue["resolved_at"])
            issues.append(issue_dict)

            if issue_dict["sla"]["is_breached"]:
                breached_issues.append(issue_dict)
            elif issue_dict["sla"]["badge"] == "warning" and issue["status"] not in ("Resolved", "Closed"):
                approaching_issues.append(issue_dict)

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "admin/sla_monitor.html",
        issues=issues,
        breached_issues=breached_issues,
        approaching_issues=approaching_issues,
        total_tracked=len(issues)
    )


@admin_bp.route("/export/csv")
@login_required
@role_required("admin")
def export_csv():
    """Generates an audit-ready CSV export of all recorded campus issues."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
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
                i.feedback_rating,
                i.feedback_comment,
                i.created_at,
                i.resolved_at,
                u.name AS reporter_name,
                u.email AS reporter_email,
                t.team_name AS assigned_team_name
            FROM issues i
            LEFT JOIN users u ON i.reported_by = u.user_id
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            ORDER BY i.issue_id ASC
        """)
        issues = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # CSV Header
    writer.writerow([
        "Issue ID", "Category", "Location", "Description", "Severity", "Priority",
        "Status", "Recurrence Risk", "SLA Deadline", "SLA Status",
        "Reporter Name", "Reporter Email", "Assigned Team",
        "Created At", "Resolved At", "Rating (1-5)", "Feedback Remarks"
    ])

    for row in issues:
        sla_info = get_sla_status(row["sla_deadline"], row["status"], row["resolved_at"])
        writer.writerow([
            row["issue_id"],
            row["issue_type"],
            row["location"],
            row["description"].replace("\n", " ") if row["description"] else "",
            row["severity"],
            row["priority"],
            row["status"],
            row["recurrence_risk"] or "Low",
            row["sla_deadline"].strftime('%Y-%m-%d %H:%M') if row["sla_deadline"] else "N/A",
            sla_info["label"],
            row["reporter_name"] or "Anonymous",
            row["reporter_email"] or "",
            row["assigned_team_name"] or "Unassigned",
            row["created_at"].strftime('%Y-%m-%d %H:%M') if row["created_at"] else "",
            row["resolved_at"].strftime('%Y-%m-%d %H:%M') if row["resolved_at"] else "",
            row["feedback_rating"] or "",
            row["feedback_comment"] or ""
        ])

    csv_data = output.getvalue()
    filename = f"campuspulse_issues_export_{int(datetime.now().timestamp())}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@admin_bp.route("/seed-demo-data", methods=["POST"])
@login_required
@role_required("admin")
def seed_data_route():
    result = seed_realistic_demo_data()
    flash(result.get("message", "Demo data processed."), "info")
    return redirect(url_for("admin.dashboard"))
