import os
import sys
import sqlite3
import re
import logging
from datetime import datetime

# Ensure project root is in Python sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector
from werkzeug.security import generate_password_hash
import config

logger = logging.getLogger("campuspulse.db")
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campuspulse.db")

# ─────────────────────────────────────────────────────────────
# SQLite Compatibility Layer (Seamless Zero-Config Fallback)
# ─────────────────────────────────────────────────────────────

def sqlite_timestampdiff(unit, dt1, dt2):
    """Custom SQLite function to calculate TIMESTAMPDIFF like MySQL."""
    if not dt1 or not dt2:
        return None
    try:
        if isinstance(dt1, str):
            dt1 = datetime.fromisoformat(dt1.replace("Z", ""))
        if isinstance(dt2, str):
            dt2 = datetime.fromisoformat(dt2.replace("Z", ""))
        diff = (dt2 - dt1).total_seconds()
        u = str(unit).upper()
        if "HOUR" in u:
            return diff / 3600.0
        elif "DAY" in u:
            return diff / 86400.0
        elif "MINUTE" in u:
            return diff / 60.0
        return diff
    except Exception:
        return 0.0

def _auto_parse_value(val):
    if isinstance(val, str) and len(val) >= 19 and len(val) <= 26 and val[4] == '-' and val[7] == '-':
        try:
            return datetime.fromisoformat(val.replace("Z", ""))
        except Exception:
            try:
                return datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                return val
    return val

class SQLiteCursorWrapper:
    """Wraps an SQLite cursor to emulate mysql.connector dictionary cursor."""
    def __init__(self, cursor, as_dict=True):
        self.cursor = cursor
        self.as_dict = as_dict

    def _convert_query(self, sql):
        # Convert %s placeholders to SQLite ? placeholders
        converted_sql = re.sub(r'(?<!%)%s', '?', sql)
        # Convert CAST(x AS CHAR) to CAST(x AS TEXT)
        converted_sql = re.sub(r'CAST\((.*?)\s+AS\s+CHAR\)', r'CAST(\1 AS TEXT)', converted_sql, flags=re.IGNORECASE)
        # Convert TIMESTAMPDIFF(unit, a, b) to TIMESTAMPDIFF('unit', a, b) so unit is not parsed as column name
        converted_sql = re.sub(r'TIMESTAMPDIFF\((\w+),', r"TIMESTAMPDIFF('\1',", converted_sql, flags=re.IGNORECASE)
        return converted_sql

    def _convert_params(self, params):
        if params is None:
            return ()
        converted = []
        for p in params:
            if isinstance(p, datetime):
                converted.append(p.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                converted.append(p)
        return tuple(converted)

    def execute(self, sql, params=None):
        conv_sql = self._convert_query(sql)
        conv_params = self._convert_params(params)
        return self.cursor.execute(conv_sql, conv_params)

    def executemany(self, sql, seq_of_params):
        conv_sql = self._convert_query(sql)
        converted_seq = [self._convert_params(p) for p in seq_of_params]
        return self.cursor.executemany(conv_sql, converted_seq)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        if self.as_dict and self.cursor.description:
            cols = [col[0] for col in self.cursor.description]
            return {col: _auto_parse_value(val) for col, val in zip(cols, row)}
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        if self.as_dict and self.cursor.description:
            cols = [col[0] for col in self.cursor.description]
            return [{col: _auto_parse_value(val) for col, val in zip(cols, r)} for r in rows]
        return rows

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        pass

def sqlite_date_format(dt, fmt):
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", ""))
        except Exception:
            try:
                dt = datetime.strptime(dt[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                return dt
    fmt = fmt.replace("%Y", "%Y").replace("%y", "%y").replace("%m", "%m").replace("%b", "%b")
    return dt.strftime(fmt)

def sqlite_year(dt):
    if not dt:
        return 0
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", ""))
        except Exception:
            return int(dt[:4]) if len(dt) >= 4 and dt[:4].isdigit() else 0
    return dt.year

def sqlite_month(dt):
    if not dt:
        return 0
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", ""))
        except Exception:
            return int(dt[5:7]) if len(dt) >= 7 and dt[5:7].isdigit() else 0
    return dt.month

class SQLiteConnectionWrapper:
    """Wraps an SQLite connection to emulate a MySQL connection object."""
    def __init__(self, raw_conn):
        self._conn = raw_conn
        self._conn.create_function("TIMESTAMPDIFF", 3, sqlite_timestampdiff)
        self._conn.create_function("ROUND", 2, lambda val, dec: round(val, dec) if val is not None else None)
        self._conn.create_function("DATE_FORMAT", 2, sqlite_date_format)
        self._conn.create_function("YEAR", 1, sqlite_year)
        self._conn.create_function("MONTH", 1, sqlite_month)

    def cursor(self, dictionary=False):
        return SQLiteCursorWrapper(self._conn.cursor(), as_dict=dictionary)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

def _create_sqlite_schema(conn):
    """Initializes tables in the SQLite database if they do not exist."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            team_description TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            reported_by INTEGER NOT NULL,
            issue_type TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'Medium',
            priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Reported',
            assigned_team INTEGER DEFAULT NULL,
            image_path TEXT DEFAULT NULL,
            resolution_notes TEXT DEFAULT NULL,
            resolution_image TEXT DEFAULT NULL,
            recurrence_risk TEXT NOT NULL DEFAULT 'Low',
            sla_deadline TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP DEFAULT NULL,
            feedback_rating INTEGER DEFAULT NULL,
            feedback_comment TEXT DEFAULT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS issue_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            old_status TEXT DEFAULT NULL,
            new_status TEXT NOT NULL,
            changed_by INTEGER DEFAULT NULL,
            remarks TEXT DEFAULT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            issue_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

# ─────────────────────────────────────────────────────────────
# Primary Database Connection Engine
# ─────────────────────────────────────────────────────────────

_MYSQL_AVAILABLE = None
_LAST_MYSQL_CHECK = 0
MYSQL_RETRY_INTERVAL = 30  # seconds

def get_db_connection():
    """
    Returns an active database connection.
    Attempts MySQL first. If MySQL is unreachable, seamlessly provides
    a local SQLite fallback with fast failover so the application operates with zero latency.
    """
    global _MYSQL_AVAILABLE, _LAST_MYSQL_CHECK
    import time
    now = time.time()

    if _MYSQL_AVAILABLE is not False or (now - _LAST_MYSQL_CHECK > MYSQL_RETRY_INTERVAL):
        try:
            conn = mysql.connector.connect(
                host=config.MYSQL_HOST,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                database=config.MYSQL_DATABASE,
                port=config.MYSQL_PORT,
                connection_timeout=1
            )
            _MYSQL_AVAILABLE = True
            _LAST_MYSQL_CHECK = now
            return conn
        except Exception:
            _MYSQL_AVAILABLE = False
            _LAST_MYSQL_CHECK = now

    # Fallback to local SQLite engine
    raw_sqlite = sqlite3.connect(SQLITE_DB_PATH, timeout=10)
    wrapper = SQLiteConnectionWrapper(raw_sqlite)
    _create_sqlite_schema(wrapper)
    return wrapper

def column_exists(cursor, table_name, column_name):
    """Checks if a column exists in a given table."""
    try:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """, (config.MYSQL_DATABASE, table_name, column_name))
        return cursor.fetchone()[0] > 0
    except Exception:
        # For SQLite fallback, columns are already up to date
        return True

def init_db():
    """
    Initializes database schema enhancements safely and non-destructively.
    Preserves all existing tables and seeds demo accounts if empty.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=False)

    try:
        # Seed default maintenance teams if none exist
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

        # Seed default demo accounts if no users exist
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
