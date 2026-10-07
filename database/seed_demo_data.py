import os
import sys
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db_connection
from services.priority_service import calculate_initial_priority
from services.sla_service import calculate_sla_deadline

DEMO_ISSUES = [
    # 1. Block A Issues (Hotspot Cluster)
    ("Wi-Fi & Network Connectivity", "Academic Block A - 3rd Floor", "High", "Repeated Wi-Fi signal loss during lectures in Hall 301 and 302.", 1, 1),
    ("Wi-Fi & Network Connectivity", "Academic Block A - 3rd Floor", "Medium", "Access point intermittent dropouts near faculty cabin 310.", 1, 1),
    ("Air Conditioning & Climate", "Academic Block A - 2nd Floor", "Medium", "Split AC leaking water droplets directly above student desks.", 3, 3),
    ("Electrical & Power Outlets", "Academic Block A - Ground Floor", "Critical", "Spark observed in main distribution switchboard near foyer.", 2, 2),
    ("Projector & Display AV", "Academic Block A - 2nd Floor", "High", "Ceiling projector shuts down due to overheating after 15 mins.", 4, 4),
    ("Lighting & Illumination", "Academic Block A - Ground Floor", "Low", "Three LED tube lights flickering in corridor walkway.", 2, 2),

    # 2. Science & Lab Issues
    ("Laboratory Instrumentation", "Science & Engineering Lab 1", "High", "Digital oscilloscope power unit tripping lab circuit breaker.", 2, 2),
    ("Air Conditioning & Climate", "Science & Engineering Lab 1", "High", "Central chiller unit failing to regulate ambient temperature for chemicals.", 3, 3),
    ("Electrical & Power Outlets", "Computing & Server Lab 2", "Critical", "UPS backup battery alarm sounding intermittently under server load.", 2, 2),
    ("Wi-Fi & Network Connectivity", "Computing & Server Lab 2", "Medium", "Gigabit switch port 18 failing to establish DHCP link.", 1, 1),

    # 3. Library Issues
    ("Air Conditioning & Climate", "Central Campus Library", "Medium", "Reading section AC unit blowing lukewarm air.", 3, 3),
    ("Wi-Fi & Network Connectivity", "Central Campus Library", "High", "Wi-Fi speeds throttled below 1 Mbps in quiet study mezzanine.", 1, 1),
    ("Lighting & Illumination", "Central Campus Library", "Low", "Table lamps in reference section stack 4 have blown bulbs.", 2, 2),

    # 4. Hostel Issues (Hotspot Cluster)
    ("Plumbing & Restroom Facilities", "Hostel Wing A (Men)", "High", "Main overhead tank pipe joint leaking heavily into 2nd floor corridor.", 5, 5),
    ("Plumbing & Restroom Facilities", "Hostel Wing A (Men)", "Medium", "Water pressure in ground floor washrooms extremely low.", 5, 5),
    ("Classroom Furniture & Equipment", "Hostel Wing A (Men)", "Low", "Study table hinges broken in room 114.", 6, 6),
    ("Electrical & Power Outlets", "Hostel Wing B (Women)", "Medium", "Geyser power outlet showing scorch marks.", 2, 2),
    ("Plumbing & Restroom Facilities", "Hostel Wing B (Women)", "High", "Drainage clog causing water logging in common washroom.", 5, 5),

    # 5. Auditorium & Facilities
    ("Projector & Display AV", "Main Auditorium", "Critical", "Main 4K stage projector HDMI matrix receiver dead before annual seminar.", 4, 4),
    ("Lighting & Illumination", "Main Auditorium", "Medium", "Stage spotlight dimmer channel 3 unresponsive.", 2, 2),
    ("Plumbing & Restroom Facilities", "Student Cafeteria", "Medium", "Kitchen wash basin tap broken, spraying water onto floor.", 5, 5)
]

def seed_realistic_demo_data():
    """Seeds realistic academic demo issues and audit logs for rich dashboard demonstration."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if demo records already exist
        cursor.execute("SELECT COUNT(*) AS cnt FROM issues")
        count = cursor.fetchone()["cnt"]
        if count >= 10:
            return {"status": "skipped", "message": f"Database already contains {count} issues."}

        # Fetch valid student user_id
        cursor.execute("SELECT user_id FROM users WHERE role = 'student' LIMIT 1")
        student_row = cursor.fetchone()
        student_id = student_row["user_id"] if student_row else 1

        # Fetch admin user_id
        cursor.execute("SELECT user_id FROM users WHERE role = 'admin' LIMIT 1")
        admin_row = cursor.fetchone()
        admin_id = admin_row["user_id"] if admin_row else 1

        now = datetime.now()
        statuses_cycle = ["Reported", "Assigned", "In Progress", "Resolved", "Closed", "In Progress", "Resolved"]

        seeded_count = 0
        for i, (cat, loc, sev, desc, team_id, _) in enumerate(DEMO_ISSUES):
            status = statuses_cycle[i % len(statuses_cycle)]
            priority = calculate_initial_priority(sev, loc, cat)

            # Generate staggered creation timestamps over the last 14 days
            days_ago = random.randint(1, 14)
            hours_ago = random.randint(1, 23)
            created_at = now - timedelta(days=days_ago, hours=hours_ago)
            sla_deadline = calculate_sla_deadline(priority, start_time=created_at)

            resolved_at = None
            feedback_rating = None
            feedback_comment = None

            if status in ("Resolved", "Closed"):
                # Resolved between 2 to 18 hours after creation
                resolved_hours = random.randint(2, 18)
                resolved_at = created_at + timedelta(hours=resolved_hours)
                feedback_rating = random.choice([4, 5, 5, 3])
                feedback_comment = "Repaired promptly by maintenance team."

            # Recurrence risk indicator
            recurrence_risk = "High" if "Block A" in loc or "Wi-Fi" in cat else ("Medium" if "Hostel" in loc else "Low")

            cursor.execute("""
                INSERT INTO issues 
                (reported_by, issue_type, location, description, severity, priority, status, assigned_team, recurrence_risk, sla_deadline, created_at, resolved_at, feedback_rating, feedback_comment)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                student_id, cat, loc, desc, sev, priority, status, team_id,
                recurrence_risk, sla_deadline, created_at, resolved_at, feedback_rating, feedback_comment
            ))
            issue_id = cursor.lastrowid

            # Seed initial audit log
            cursor.execute("""
                INSERT INTO issue_history (issue_id, old_status, new_status, changed_by, changed_at, remarks)
                VALUES (%s, NULL, 'Reported', %s, %s, 'Issue logged by student')
            """, (issue_id, student_id, created_at))

            # If assigned or beyond
            if status != "Reported":
                assigned_time = created_at + timedelta(minutes=random.randint(15, 60))
                cursor.execute("""
                    INSERT INTO issue_history (issue_id, old_status, new_status, changed_by, changed_at, remarks)
                    VALUES (%s, 'Reported', 'Assigned', %s, %s, 'Dispatched to specialized engineering crew')
                """, (issue_id, admin_id, assigned_time))

            if status in ("In Progress", "Resolved", "Closed"):
                progress_time = created_at + timedelta(hours=random.randint(1, 3))
                cursor.execute("""
                    INSERT INTO issue_history (issue_id, old_status, new_status, changed_by, changed_at, remarks)
                    VALUES (%s, 'Assigned', 'In Progress', %s, %s, 'Technician commenced diagnostic testing')
                """, (issue_id, admin_id, progress_time))

            if status in ("Resolved", "Closed") and resolved_at:
                cursor.execute("""
                    INSERT INTO issue_history (issue_id, old_status, new_status, changed_by, changed_at, remarks)
                    VALUES (%s, 'In Progress', %s, %s, %s, 'Component replaced and full operational test passed')
                """, (issue_id, status, admin_id, resolved_at))

            seeded_count += 1

        conn.commit()
        return {"status": "success", "count": seeded_count, "message": f"Successfully seeded {seeded_count} academic demo issues."}

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    result = seed_realistic_demo_data()
    print("Seed Result:", result)
