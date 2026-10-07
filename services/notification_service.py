from database.db import get_db_connection

def create_notification(user_id, title, message, issue_id=None):
    """Creates a notification record for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, issue_id)
            VALUES (%s, %s, %s, %s)
        """, (user_id, title, message, issue_id))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def get_user_notifications(user_id, limit=10, unread_only=False):
    """Retrieves notifications for a user."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT notification_id, title, message, is_read, issue_id, created_at
            FROM notifications
            WHERE user_id = %s
        """
        params = [user_id]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_unread_count(user_id):
    """Returns the count of unread notifications for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    finally:
        cursor.close()
        conn.close()

def mark_notification_as_read(notification_id, user_id):
    """Marks a single notification as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE notifications 
            SET is_read = 1 
            WHERE notification_id = %s AND user_id = %s
        """, (notification_id, user_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def mark_all_read(user_id):
    """Marks all notifications for a user as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
