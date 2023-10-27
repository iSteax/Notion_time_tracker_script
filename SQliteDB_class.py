import sqlite3
import logging
from logging.handlers import RotatingFileHandler


logger = logging.getLogger(__name__)  # Using __name__ instead of hard-coded name
logger.setLevel(logging.INFO)

handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class SQLiteDB:
    def __init__(self, db_name):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def fetch_one(self, query, params=()):
        try:
            return self.cursor.execute(query, params).fetchone()
        except sqlite3.Error as e:
            logging.error(f"SQLite error: {e}")
            return None

    def fetch_all(self, query, params=()):
        try:
            return self.cursor.execute(query, params).fetchall()
        except sqlite3.Error as e:
            logging.error(f"SQLite error: {e}")
            return []

    def execute(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"SQLite error: {e}")

    def update_or_insert_task(self, task_id, task_name, status):
        existing_task = self.fetch_one("SELECT * FROM tracking WHERE task_id=?", (task_id,))
        if existing_task:
            self.execute(
                "UPDATE tracking SET task_name=?, status=? WHERE task_id=?",
                (task_name, status, task_id))
        else:
            self.execute(
                "INSERT INTO tracking (task_id, task_name, status) VALUES (?, ?, ?)",
                (task_id, task_name, status))

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
