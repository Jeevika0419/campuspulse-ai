import os
from flask import Flask, redirect, url_for, session, render_template
import config
from database.db import get_db_connection, init_db
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.admin_routes import admin_bp
from routes.maintenance_routes import maintenance_bp
from services.notification_service import get_unread_count

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Ensure uploads directory exists
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(maintenance_bp)

# Global context processor to make auth status & notification count available in all templates
@app.context_processor
def inject_global_context():
    unread_count = 0
    if "user_id" in session:
        try:
            unread_count = get_unread_count(session["user_id"])
        except Exception:
            unread_count = 0
    return {
        "current_user_name": session.get("name"),
        "current_user_role": session.get("role"),
        "current_user_id": session.get("user_id"),
        "unread_notifications_count": unread_count,
        "app_brand": "CampusPulse AI",
        "app_tagline": "Smarter Campus. Faster Resolution. Predictive Maintenance."
    }

@app.route("/")
def home():
    """Root route: Redirect to role-specific dashboard or login."""
    if "user_id" in session:
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif role == "maintenance":
            return redirect(url_for("maintenance.dashboard"))
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("auth.login"))

@app.route("/test-db")
def test_db():
    """Diagnostic database connection test endpoint (preserved from initial setup)."""
    try:
        connection = get_db_connection()
        connection.close()
        return "<h2 style='color:#10b981;font-family:sans-serif;'>Database connected successfully! (campus_issue_system)</h2>"
    except Exception as e:
        return f"<h2 style='color:#ef4444;font-family:sans-serif;'>Database connection failed:</h2><p>{e}</p>"

@app.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(403)
def access_forbidden(e):
    return render_template("errors/403.html"), 403

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500

# Automatically verify/initialize DB schema upon startup
try:
    init_db()
except Exception as err:
    print(f"[WARNING] Database auto-init error: {err}")

if __name__ == "__main__":
    app.run(debug=config.DEBUG, host="0.0.0.0", port=5000)