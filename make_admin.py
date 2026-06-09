import sqlite3
from utils.config import SQLITE_DB_PATH

conn = sqlite3.connect(SQLITE_DB_PATH)
cursor = conn.cursor()

cursor.execute(
    "UPDATE users SET is_admin = 1 WHERE email = ?",
    ("ehtisham2406@gmail.com",)
)
conn.commit()

# Verify
cursor.execute("SELECT name, email, is_admin FROM users WHERE email = ?", ("ehtisham2406@gmail.com",))
user = cursor.fetchone()
print(f"✅ Updated: {user}")

conn.close()