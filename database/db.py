import os
import sys

# Ensure project root is in Python sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector
from werkzeug.security import generate_password_hash
import config

def get_db_connection():
    """Returns a new MySQL database connection."""
    return mysql.connector.connect(
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DATABASE,
        port=config.MYSQL_PORT
    )

def column_exists(cursor, table_name, column_name):
    """Checks if a column exists in a given table."""
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (config.MYSQL_DATABASE, table_name, column_name))
    return cursor.fetchone()[0] > 0

def init_db():
    """
    Initializes database schema enhancements safely and non-destructively.
    Preserves all existing tables and data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Ensure `users` has created_at
        if not column_exists(cursor, 'users', 'created_at'):
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        # 2. Ensure `issues` has auxiliary columns for full lifecycle
        issue_cols = [
            ("priority", "VARCHAR(20) DEFAULT 'Medium'"),
            ("image_path", "VARCHAR(255) DEFAULT NULL"),
            ("resolution_image", "VARCHAR(255) DEFAULT NULL"),
            ("recurrence_risk", "VARCHAR(20) DEFAULT 'Low'"),
            ("sla_deadline", "DATETIME DEFAULT NULL"),
            ("feedback_rating", "INT DEFAULT NULL"),
            ("feedback_comment", "TEXT DEFAULT NULL")
        ]
        for col_name, col_def in issue_cols:
            if not column_exists(cursor, 'issues', col_name):
                cursor.execute(f"ALTER TABLE issues ADD COLUMN {col_name} {col_def}")

        # 3. Create notifications table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(150) NOT NULL,
                message TEXT NOT NULL,
                is_read TINYINT(1) DEFAULT 0,
                issue_id INT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id),
                CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) 
                    REFERENCES users(user_id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """)

        # 4. Seed default maintenance teams if none exist
        cursor.execute("SELECT COUNT(*) FROM maintenance_teams")
        team_count = cursor.fetchone()[0]
        if team_count == 0:
            default_teams = [
                ("IT & Network Infrastructure", "Campus Wi-Fi, Ethernet, routers, switches, and server connectivity"),
                ("Electrical & Power Systems", "Classroom power outlets, wiring, lighting, MCBs, backup generators"),
                ("HVAC & Air Conditioning", "Auditorium, laboratory, and classroom cooling and climate systems"),
                ("AV & Classroom Display Equipment", "Smart boards, projectors, audio systems, HDMI feeds"),
                ("Plumbing & Water Facilities", "Restroom plumbing, drinking water coolers, pipeline leakage"),
                ("Civil & Hostel Facilities", "Structural repairs, hostel furniture, doors, windows, paintwork")
            ]
            cursor.executemany(
                "INSERT INTO maintenance_teams (team_name, team_description) VALUES (%s, %s)",
                default_teams
            )

        # 5. Seed default demo accounts if no users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        if user_count == 0:
            demo_users = [
                ("Admin Manager", "admin@campuspulse.edu", generate_password_hash("Admin@123"), "admin"),
                ("Chief Maintenance Officer", "staff@campuspulse.edu", generate_password_hash("Staff@123"), "maintenance"),
                ("Alex Rivera (Student)", "student@campuspulse.edu", generate_password_hash("Student@123"), "student")
            ]
            cursor.executemany(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                demo_users
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialization and verification completed successfully!")
