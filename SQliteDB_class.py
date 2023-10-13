import sqlite3


class SQLiteDB:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

    def fetch_one(self, query, params=()):
        return self.cursor.execute(query, params).fetchone()

    def fetch_all(self, query, params=()):
        return self.cursor.execute(query, params).fetchall()

    def execute(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()

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
        self.cursor.close()
        self.conn.close()