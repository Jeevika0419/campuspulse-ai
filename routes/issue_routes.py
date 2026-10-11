import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_from_directory, abort, jsonify
from routes.auth_routes import login_required, role_required
from database.db import get_db_connection
from services.priority_service import calculate_initial_priority
from services.sla_service import calculate_sla_deadline, get_sla_status
from services.upload_service import save_uploaded_file
from services.notification_service import create_notification
from services.ml_service import predict_recurrence_risk, update_issue_recurrence_risk
import config

issue_bp = Blueprint("issues", __name__)

CAMPUS_LOCATIONS = [
    "Academic Block A - Ground Floor",
    "Academic Block A - 2nd Floor",
    "Academic Block A - 3rd Floor",
    "Academic Block B - Lecture Halls",
    "Science & Engineering Lab 1",
    "Computing & Server Lab 2",
    "Central Campus Library",
    "Main Auditorium",
    "Student Cafeteria",
    "Hostel Wing A (Men)",
    "Hostel Wing B (Women)",
    "Administrative Block",
    "Sports Complex & Gym"
]

ISSUE_CATEGORIES = [
    "Wi-Fi & Network Connectivity",
    "Air Conditioning & Climate",
    "Electrical & Power Outlets",
    "Projector & Display AV",
    "Classroom Furniture & Equipment",
    "Plumbing & Restroom Facilities",
    "Lighting & Illumination",
    "Laboratory Instrumentation",
    "Hostel Infrastructure",
    "Other Campus Issue"
]

@issue_bp.route("/issues")
@login_required
def list_issues():
    user_id = session.get("user_id")
    user_role = session.get("role")

    # Filter parameters
    search_q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    severity_filter = request.args.get("severity", "").strip()
    category_filter = request.args.get("category", "").strip()
    location_filter = request.args.get("location", "").strip()
    view_scope = request.args.get("scope", "all" if user_role in ("admin", "maintenance") else "my")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            SELECT 
                i.issue_id,
                i.reported_by,
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
            WHERE 1=1
        """
        params = []

        if view_scope == "my" and user_role == "student":
            query += " AND i.reported_by = %s"
            params.append(user_id)

        if search_q:
            query += " AND (i.description LIKE %s OR i.location LIKE %s OR i.issue_type LIKE %s OR CAST(i.issue_id AS CHAR) = %s)"
            wildcard = f"%{search_q}%"
            params.extend([wildcard, wildcard, wildcard, search_q])

        if status_filter:
            query += " AND i.status = %s"
            params.append(status_filter)

        if severity_filter:
            query += " AND i.severity = %s"
            params.append(severity_filter)

        if category_filter:
            query += " AND i.issue_type = %s"
            params.append(category_filter)

        if location_filter:
            query += " AND i.location LIKE %s"
            params.append(f"%{location_filter}%")

        query += " ORDER BY i.created_at DESC"

        cursor.execute(query, tuple(params))
        raw_issues = cursor.fetchall()

        # Augment with dynamic SLA status
        issues = []
        for issue in raw_issues:
            issue_dict = dict(issue)
            issue_dict["sla"] = get_sla_status(
                issue["sla_deadline"],
                issue["status"],
                issue["resolved_at"]
            )
            issues.append(issue_dict)

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "issues/list.html",
        issues=issues,
        locations=CAMPUS_LOCATIONS,
        categories=ISSUE_CATEGORIES,
        current_filters={
            "q": search_q,
            "status": status_filter,
            "severity": severity_filter,
            "category": category_filter,
            "location": location_filter,
            "scope": view_scope
        }
    )


@issue_bp.route("/issues/report", methods=["GET", "POST"])
@login_required
def report_issue():
    if request.method == "POST":
        issue_type = request.form.get("issue_type", "").strip()
        location = request.form.get("location", "").strip()
        severity = request.form.get("severity", "Medium").strip()
        description = request.form.get("description", "").strip()
        image_file = request.files.get("image")

        if not issue_type or not location or not description:
            flash("Please fill in all required fields (category, location, and description).", "danger")
            return render_template("issues/report.html", locations=CAMPUS_LOCATIONS, categories=ISSUE_CATEGORIES)

        # Handle image upload if provided
        image_filename = None
        if image_file and image_file.filename:
            try:
                image_filename = save_uploaded_file(image_file, subfolder="reported")
            except ValueError as ve:
                flash(str(ve), "danger")
                return render_template("issues/report.html", locations=CAMPUS_LOCATIONS, categories=ISSUE_CATEGORIES)

        # Smart priority and SLA calculation
        priority = calculate_initial_priority(severity, location, issue_type)
        sla_deadline = calculate_sla_deadline(priority)
        user_id = session.get("user_id")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Insert issue
            cursor.execute("""
                INSERT INTO issues 
                (reported_by, issue_type, location, description, severity, priority, status, image_path, sla_deadline)
                VALUES (%s, %s, %s, %s, %s, %s, 'Reported', %s, %s)
            """, (user_id, issue_type, location, description, severity, priority, image_filename, sla_deadline))
            
            issue_id = cursor.lastrowid

            # Insert initial audit log into issue_history
            cursor.execute("""
                INSERT INTO issue_history 
                (issue_id, old_status, new_status, changed_by, remarks)
                VALUES (%s, NULL, 'Reported', %s, 'Issue submitted by user')
            """, (issue_id, user_id))

            conn.commit()

            # Create in-app notification for the user
            create_notification(
                user_id=user_id,
                title="Issue Submitted",
                message=f"Issue #{issue_id} ({issue_type}) at {location} has been successfully logged with {priority} priority.",
                issue_id=issue_id
            )

            # If Critical, notify admins
            if priority == "Critical":
                cursor.execute("SELECT user_id FROM users WHERE role = 'admin'")
                admins = cursor.fetchall()
                for admin in admins:
                    create_notification(
                        user_id=admin["user_id"],
                        title="🚨 CRITICAL Hazard Alert",
                        message=f"Urgent: Issue #{issue_id} ({issue_type}) reported at {location}. Requires immediate attention.",
                        issue_id=issue_id
                    )

            # Trigger AWS Cloud Integration (SNS Alert + CloudWatch Metric)
            try:
                from services.aws_service import aws_service
                aws_service.log_issue_reported_metric(issue_type, priority)
                if priority == "Critical":
                    aws_service.send_critical_issue_alert(issue_id, issue_type, location, priority)
            except Exception:
                pass

            flash(f"Issue #{issue_id} reported successfully! Maintenance teams will be dispatched shortly.", "success")
            return redirect(url_for("issues.view_issue", issue_id=issue_id))

        except Exception as e:
            conn.rollback()
            flash(f"Error submitting issue: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        "issues/report.html",
        locations=CAMPUS_LOCATIONS,
        categories=ISSUE_CATEGORIES
    )


@issue_bp.route("/issues/<int:issue_id>")
@login_required
def view_issue(issue_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch issue details
        cursor.execute("""
            SELECT 
                i.*,
                u.name AS reporter_name,
                u.email AS reporter_email,
                t.team_name AS assigned_team_name,
                t.team_description AS assigned_team_description
            FROM issues i
            LEFT JOIN users u ON i.reported_by = u.user_id
            LEFT JOIN maintenance_teams t ON i.assigned_team = t.team_id
            WHERE i.issue_id = %s
        """, (issue_id,))
        issue = cursor.fetchone()

        if not issue:
            abort(404)

        # Calculate SLA
        sla_info = get_sla_status(issue["sla_deadline"], issue["status"], issue["resolved_at"])

        # Fetch audit history
        cursor.execute("""
            SELECT 
                h.*,
                u.name AS changer_name,
                u.role AS changer_role
            FROM issue_history h
            LEFT JOIN users u ON h.changed_by = u.user_id
            WHERE h.issue_id = %s
            ORDER BY h.changed_at ASC
        """, (issue_id,))
        history = cursor.fetchall()

        # Fetch all maintenance teams for assignment dropdown
        cursor.execute("SELECT * FROM maintenance_teams ORDER BY team_name ASC")
        teams = cursor.fetchall()

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "issues/details.html",
        issue=issue,
        sla_info=sla_info,
        history=history,
        teams=teams,
        current_user_id=session.get("user_id"),
        current_user_role=session.get("role")
    )


@issue_bp.route("/issues/<int:issue_id>/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_issue(issue_id):
    team_id = request.form.get("team_id")
    new_priority = request.form.get("priority")
    remarks = request.form.get("remarks", "").strip()

    if not team_id:
        flash("Please select a maintenance team.", "danger")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT status, priority, reported_by FROM issues WHERE issue_id = %s", (issue_id,))
        issue = cursor.fetchone()
        if not issue:
            abort(404)

        old_status = issue["status"]
        new_status = "Assigned" if old_status in ("Reported", "Under Review") else old_status
        assigned_priority = new_priority if new_priority else issue["priority"]

        # Recalculate SLA if priority changed
        sla_deadline = calculate_sla_deadline(assigned_priority) if new_priority else None

        cursor.execute("SELECT team_name FROM maintenance_teams WHERE team_id = %s", (team_id,))
        team_row = cursor.fetchone()
        team_name = team_row["team_name"] if team_row else "Team"

        # Update issue record
        if sla_deadline:
            cursor.execute("""
                UPDATE issues 
                SET assigned_team = %s, status = %s, priority = %s, sla_deadline = %s 
                WHERE issue_id = %s
            """, (team_id, new_status, assigned_priority, sla_deadline, issue_id))
        else:
            cursor.execute("""
                UPDATE issues 
                SET assigned_team = %s, status = %s, priority = %s 
                WHERE issue_id = %s
            """, (team_id, new_status, assigned_priority, issue_id))

        # Add audit log
        audit_remarks = remarks or f"Assigned to {team_name} by Administration"
        cursor.execute("""
            INSERT INTO issue_history (issue_id, old_status, new_status, changed_by, remarks)
            VALUES (%s, %s, %s, %s, %s)
        """, (issue_id, old_status, new_status, session.get("user_id"), audit_remarks))

        conn.commit()

        # Notify reporter
        create_notification(
            user_id=issue["reported_by"],
            title=f"Issue #{issue_id} Assigned",
            message=f"Your issue has been assigned to {team_name}. Current status: {new_status}.",
            issue_id=issue_id
        )

        flash(f"Issue #{issue_id} successfully assigned to {team_name}!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Error assigning team: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issue_bp.route("/issues/<int:issue_id>/update-status", methods=["POST"])
@login_required
@role_required("maintenance", "admin")
def update_status(issue_id):
    new_status = request.form.get("status", "").strip()
    remarks = request.form.get("remarks", "").strip()
    proof_image = request.files.get("resolution_image")

    allowed_statuses = ["Under Review", "In Progress", "On Hold", "Resolved", "Closed"]
    if new_status not in allowed_statuses:
        flash("Invalid status selected.", "danger")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))

    # Optional resolution proof image
    proof_filename = None
    if proof_image and proof_image.filename:
        try:
            proof_filename = save_uploaded_file(proof_image, subfolder="resolved")
        except ValueError as ve:
            flash(str(ve), "danger")
            return redirect(url_for("issues.view_issue", issue_id=issue_id))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT status, reported_by FROM issues WHERE issue_id = %s", (issue_id,))
        issue = cursor.fetchone()
        if not issue:
            abort(404)

        old_status = issue["status"]
        resolved_at = datetime.now() if new_status in ("Resolved", "Closed") else None

        # Update SQL
        update_query = "UPDATE issues SET status = %s"
        params = [new_status]

        if resolved_at:
            update_query += ", resolved_at = %s"
            params.append(resolved_at)

        if proof_filename:
            update_query += ", resolution_image = %s"
            params.append(proof_filename)

        update_query += " WHERE issue_id = %s"
        params.append(issue_id)

        cursor.execute(update_query, tuple(params))

        # Record in audit log
        log_remarks = remarks or f"Status transitioned to {new_status}"
        cursor.execute("""
            INSERT INTO issue_history (issue_id, old_status, new_status, changed_by, remarks)
            VALUES (%s, %s, %s, %s, %s)
        """, (issue_id, old_status, new_status, session.get("user_id"), log_remarks))

        conn.commit()

        # Auto-run ML recurrence engine when resolved/closed (Sprint 4)
        if new_status in ("Resolved", "Closed"):
            try:
                risk_level = update_issue_recurrence_risk(issue_id)
            except Exception:
                risk_level = "N/A"

            # Log AWS CloudWatch metric
            try:
                from services.aws_service import aws_service
                aws_service.put_metric_data("IssuesResolvedCount", 1, "Count")
            except Exception:
                pass

        # Notify reporter
        create_notification(
            user_id=issue["reported_by"],
            title=f"Status Update: Issue #{issue_id}",
            message=f"Status updated to '{new_status}'. Remarks: {log_remarks}",
            issue_id=issue_id
        )

        flash(f"Issue #{issue_id} status updated to {new_status}.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Failed to update status: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issue_bp.route("/issues/<int:issue_id>/reopen", methods=["POST"])
@login_required
def reopen_issue(issue_id):
    remarks = request.form.get("remarks", "").strip()
    if not remarks:
        flash("Please provide a reason for reopening the issue.", "warning")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))

    user_id = session.get("user_id")
    user_role = session.get("role")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT status, reported_by, priority FROM issues WHERE issue_id = %s", (issue_id,))
        issue = cursor.fetchone()
        if not issue:
            abort(404)

        # Allow if student is the reporter or user is admin
        if user_role != "admin" and issue["reported_by"] != user_id:
            flash("You do not have permission to reopen this issue.", "danger")
            return redirect(url_for("issues.view_issue", issue_id=issue_id))

        old_status = issue["status"]
        # Reset SLA with expedited priority
        new_priority = "High" if issue["priority"] in ("Low", "Medium") else issue["priority"]
        new_sla = calculate_sla_deadline(new_priority)

        cursor.execute("""
            UPDATE issues 
            SET status = 'Reopened', priority = %s, sla_deadline = %s, resolved_at = NULL 
            WHERE issue_id = %s
        """, (new_priority, new_sla, issue_id))

        cursor.execute("""
            INSERT INTO issue_history (issue_id, old_status, new_status, changed_by, remarks)
            VALUES (%s, %s, 'Reopened', %s, %s)
        """, (issue_id, old_status, user_id, f"Issue reopened: {remarks}"))

        conn.commit()

        # Notify admin of reopened issue
        cursor.execute("SELECT user_id FROM users WHERE role = 'admin'")
        admins = cursor.fetchall()
        for a in admins:
            create_notification(
                user_id=a["user_id"],
                title=f"⚠️ Issue #{issue_id} Reopened",
                message=f"Student indicated unresolved problem: {remarks}",
                issue_id=issue_id
            )

        flash(f"Issue #{issue_id} has been reopened with priority '{new_priority}'. Maintenance has been alerted.", "warning")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issue_bp.route("/issues/<int:issue_id>/feedback", methods=["POST"])
@login_required
def submit_feedback(issue_id):
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()

    if not rating or rating < 1 or rating > 5:
        flash("Please provide a valid rating between 1 and 5 stars.", "danger")
        return redirect(url_for("issues.view_issue", issue_id=issue_id))

    user_id = session.get("user_id")
    user_role = session.get("role")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT reported_by FROM issues WHERE issue_id = %s", (issue_id,))
        issue = cursor.fetchone()
        if not issue:
            abort(404)

        if user_role != "admin" and issue["reported_by"] != user_id:
            flash("Only the reporting user can submit resolution feedback.", "danger")
            return redirect(url_for("issues.view_issue", issue_id=issue_id))

        cursor.execute("""
            UPDATE issues 
            SET feedback_rating = %s, feedback_comment = %s 
            WHERE issue_id = %s
        """, (rating, comment, issue_id))
        conn.commit()

        flash("Thank you! Your resolution rating and feedback have been recorded.", "success")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("issues.view_issue", issue_id=issue_id))


@issue_bp.route("/api/issues/predict-recurrence", methods=["POST"])
@login_required
def api_predict_recurrence():
    """
    Sprint 4 — AI Recurrence Prediction Endpoint
    Accepts: { issue_type, location, severity, issue_id? }
    Returns: { risk_level, confidence_score, feature_explanations, summary }
    """
    data = request.get_json(silent=True) or {}
    issue_type = data.get("issue_type") or request.form.get("issue_type", "")
    location = data.get("location") or request.form.get("location", "")
    severity = data.get("severity") or request.form.get("severity", "Medium")
    issue_id = data.get("issue_id") or request.form.get("issue_id")

    if not issue_type or not location:
        return jsonify({"error": "issue_type and location are required"}), 400

    try:
        prediction = predict_recurrence_risk(
            issue_type=issue_type,
            location=location,
            severity=severity,
            issue_id=int(issue_id) if issue_id else None
        )
        return jsonify(prediction)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@issue_bp.route("/uploads/<filename>")
@login_required
def uploaded_file(filename):
    """Safely serves uploaded evidence and resolution images."""
    return send_from_directory(config.UPLOAD_FOLDER, filename)
