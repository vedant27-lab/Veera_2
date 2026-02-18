# logger_sql.py
import sqlite3
import os
# Assumes config.py is in the parent directory
import config

def setup_database():
    if os.path.exists(config.DB_FILE):
        print("Database already exists.")
        return
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            window_title TEXT,
            action_type TEXT,
            action_details TEXT,
            result TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database '{config.DB_FILE}' created successfully.")

if __name__ == "__main__":
    setup_database()