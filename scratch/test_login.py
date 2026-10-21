import os
import sys
sys.path.insert(0, os.path.abspath("."))

from app import app
from database.db import get_db_connection

conn = get_db_connection()
cur = conn.cursor(dictionary=True)
cur.execute("SELECT * FROM users")
users = cur.fetchall()
print(f"Total users found: {len(users)}")
for u in users:
    print(f"User: {u['email']} | role: {u['role']}")

app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False
with app.test_client() as client:
    res = client.post("/login", data={"email": "admin@campuspulse.edu", "password": "Admin@123"}, follow_redirects=True)
    print("Status:", res.status_code)
    print("URL or redirect:", res.request.path)
    print("Content preview:", res.data[:300].decode("utf-8", errors="ignore"))
    res_dash = client.get("/admin/dashboard")
    print("Dashboard status:", res_dash.status_code)
    print("Dashboard len:", len(res_dash.data))
    if b"Executive Infrastructure Analytics" in res_dash.data:
        print("MATCH Executive Infrastructure Analytics!")
    else:
        print("NO MATCH! Data preview:", res_dash.data[:500].decode("utf-8", errors="ignore"))
