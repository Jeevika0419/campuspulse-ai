import pytest
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database.db import get_db_connection
from werkzeug.security import check_password_hash

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client

def test_database_endpoint(client):
    """Verifies that the /test-db endpoint returns database connection status."""
    response = client.get("/test-db")
    assert response.status_code == 200
    assert b"Database connected successfully" in response.data

def test_unauthenticated_redirect(client):
    """Unauthenticated users at / should be redirected to /login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_login_page_renders(client):
    """The /login route should return 200 and display CampusPulse branding."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"CampusPulse AI" in response.data
    assert b"Institutional Email" in response.data

def test_register_page_renders(client):
    """The /register route should return 200 and role selectors."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create Account" in response.data
    assert b"Student" in response.data

def test_invalid_login(client):
    """Invalid credentials should show error message and not establish session."""
    response = client.post("/login", data={
        "email": "invalid_user@nowhere.edu",
        "password": "WrongPassword123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_admin_login_and_dashboard(client):
    """Admin user should authenticate successfully and land on admin dashboard."""
    response = client.post("/login", data={
        "email": "admin@campuspulse.edu",
        "password": "Admin@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Admin Center" in response.data or b"Executive Infrastructure Analytics" in response.data

def test_maintenance_login_and_dashboard(client):
    """Maintenance user should authenticate successfully and land on maintenance dashboard."""
    response = client.post("/login", data={
        "email": "staff@campuspulse.edu",
        "password": "Staff@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Field Engineering & Ops Dispatch" in response.data

def test_student_login_and_dashboard(client):
    """Student user should authenticate successfully and land on student hub."""
    response = client.post("/login", data={
        "email": "student@campuspulse.edu",
        "password": "Student@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Student Portal" in response.data or b"Student Hub" in response.data

def test_role_authorization_enforcement(client):
    """A student attempting to access admin dashboard should be blocked and redirected."""
    # Log in as student
    client.post("/login", data={
        "email": "student@campuspulse.edu",
        "password": "Student@123"
    })
    
    # Attempt to access admin dashboard
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 200
    # Should be redirected to student dashboard with access denied flash
    assert b"Access denied" in response.data or b"Student Portal" in response.data

def test_user_registration_and_hash(client):
    """New user registration must hash passwords and allow immediate login."""
    test_email = "test.newstudent@campuspulse.edu"

    # Cleanup test user if previously existing
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = %s", (test_email,))
    conn.commit()
    cursor.close()
    conn.close()

    response = client.post("/register", data={
        "name": "Jordan Taylor",
        "email": test_email,
        "password": "Password@456",
        "confirm_password": "Password@456",
        "role": "student"
    }, follow_redirects=True)
    assert response.status_code == 200

    # Verify database entry has hashed password
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT password, role FROM users WHERE email = %s", (test_email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    assert user is not None
    assert user["password"] != "Password@456"  # Must NOT be plaintext
    assert check_password_hash(user["password"], "Password@456") is True
    assert user["role"] == "student"

def test_logout(client):
    """Logout should clear the session and redirect back to login."""
    client.post("/login", data={
        "email": "student@campuspulse.edu",
        "password": "Student@123"
    })
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"logged out" in response.data
