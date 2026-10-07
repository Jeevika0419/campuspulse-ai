from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db_connection
from services.notification_service import (
    create_notification,
    get_user_notifications,
    get_unread_count,
    mark_notification_as_read,
    mark_all_read
)

auth_bp = Blueprint("auth", __name__)

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to enforce role-based access control."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            
            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("Access denied. You do not have permissions for this section.", "danger")
                # Redirect to appropriate home dashboard
                if user_role == "admin":
                    return redirect(url_for("admin.dashboard"))
                elif user_role == "maintenance":
                    return redirect(url_for("maintenance.dashboard"))
                else:
                    return redirect(url_for("student.dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, redirect directly to dashboard
    if "user_id" in session:
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif role == "maintenance":
            return redirect(url_for("maintenance.dashboard"))
        return redirect(url_for("student.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("auth/login.html")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s", (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password"], password):
                # Set session variables
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                session["email"] = user["email"]
                session["role"] = user["role"]
                session.permanent = True

                flash(f"Welcome back, {user['name']}!", "success")

                # Respect redirect parameter if safe
                next_url = request.args.get("next")
                if next_url and next_url.startswith("/"):
                    return redirect(next_url)

                if user["role"] == "admin":
                    return redirect(url_for("admin.dashboard"))
                elif user["role"] == "maintenance":
                    return redirect(url_for("maintenance.dashboard"))
                else:
                    return redirect(url_for("student.dashboard"))
            else:
                flash("Invalid email or password. Please verify credentials.", "danger")
        except Exception as e:
            flash(f"Database error during authentication: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "student").strip().lower()

        # Input validation
        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if len(name) < 2:
            flash("Name must be at least 2 characters long.", "danger")
            return render_template("auth/register.html")

        if "@" not in email or "." not in email:
            flash("Please enter a valid academic/institutional email address.", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        # Allowed self-registration roles
        if role not in ["student", "maintenance", "admin"]:
            role = "student"

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Check if email is already taken
            cursor.execute("SELECT user_id FROM users WHERE LOWER(email) = %s", (email,))
            existing = cursor.fetchone()

            if existing:
                flash("An account with this email already exists. Please log in.", "warning")
                return render_template("auth/register.html")

            # Hash password securely
            hashed_password = generate_password_hash(password)

            cursor.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES (%s, %s, %s, %s)
            """, (name, email, hashed_password, role))
            conn.commit()
            new_user_id = cursor.lastrowid

            # Add welcome notification
            create_notification(
                user_id=new_user_id,
                title="Welcome to CampusPulse AI!",
                message=f"Hello {name}, your {role.capitalize()} account has been created. You can track and report infrastructure issues seamlessly."
            )

            # Auto-login after registration
            session["user_id"] = new_user_id
            session["name"] = name
            session["email"] = email
            session["role"] = role

            flash(f"Account successfully created! Welcome, {name}.", "success")

            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif role == "maintenance":
                return redirect(url_for("maintenance.dashboard"))
            else:
                return redirect(url_for("student.dashboard"))

        except Exception as e:
            conn.rollback()
            flash(f"Registration failed: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))


# Notification API endpoints for dynamic topbar/header
@auth_bp.route("/api/notifications/unread-count")
@login_required
def api_unread_count():
    count = get_unread_count(session["user_id"])
    return jsonify({"unread_count": count})


@auth_bp.route("/api/notifications")
@login_required
def api_notifications():
    notifications = get_user_notifications(session["user_id"], limit=8)
    return jsonify({"notifications": notifications})


@auth_bp.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def api_mark_read(notification_id):
    mark_notification_as_read(notification_id, session["user_id"])
    return jsonify({"success": True})


@auth_bp.route("/api/notifications/mark-all-read", methods=["POST"])
@login_required
def api_mark_all_read():
    mark_all_read(session["user_id"])
    return jsonify({"success": True})
