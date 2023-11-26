import sqlite3
from datetime import datetime
from notion_client import Client
import time
import logging
from logging.handlers import RotatingFileHandler
from fetch_data_from_notion import fetch_data_from_notion
from get_token_database_id import TOKEN
from progress_paused_done_statuses import ProgressPausedTaskManager
from tasks_utilites import load_tasks_status_from_db, remove_deleted_tasks_from_progress_paused_task_manager_sets

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=3)  # 5MB per log file, keep 3 old logs
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# SQLite setup
conn = sqlite3.connect('time_tracking.db')
cursor = conn.cursor()

# Create table if not exists for main data
cursor.execute('''
CREATE TABLE IF NOT EXISTS tracking (
    task_id TEXT PRIMARY KEY,
    task_name TEXT,
    start_time TEXT,
    start_time_origin TEXT,
    paused_time TEXT,
    elapsed_time TEXT,
    done_time TEXT,
    status TEXT,
    previous_status TEXT
)
''')

# Create table for token and database_id
cursor.execute('''
CREATE TABLE IF NOT EXISTS token (
    token_id TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS database_id (
    database_id TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Notion connect
client = Client(auth=TOKEN)

def main(progress_paused_task_manager):

    print("Time_tracker run successfully")

    # Load tasks from the database
    progress_paused_task_manager.in_progress_tasks, progress_paused_task_manager.paused_tasks = load_tasks_status_from_db()

    while True:
        try:
            # Fetch tasks from Notion and get their IDs
            fetched_task_ids = fetch_data_from_notion(progress_paused_task_manager)
            #
            # # Get all task IDs from the SQLite database
            # all_db_task_ids = {task[0] for task in cursor.execute("SELECT task_id FROM tracking").fetchall()}
            #
            # # Find tasks that are in the SQLite database but not in the fetched tasks from Notion
            # deleted_task_ids = all_db_task_ids - fetched_task_ids
            #
            # # Remove deleted tasks' IDs from the in_progress_tasks and paused_tasks sets
            # progress_paused_task_manager.in_progress_tasks -= deleted_task_ids
            # progress_paused_task_manager.paused_tasks -= deleted_task_ids

            # Remove deleted tasks from the tracking sets
            remove_deleted_tasks_from_progress_paused_task_manager_sets(fetched_task_ids, progress_paused_task_manager)

            start_time = datetime.now()
            end_time = datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()
            logging.info(f"Data fetched in {elapsed_time} seconds.")
            time.sleep(1)
            logging.info(f"Current in-progress tasks: {progress_paused_task_manager.in_progress_tasks}")
            logging.info(f"Current paused tasks: {progress_paused_task_manager.paused_tasks}")
        except Exception as e:
            logging.error(f"Error during main loop", exc_info=True)
            time.sleep(20)

if __name__ == "__main__":
    progress_paused_task_manager = ProgressPausedTaskManager()
    main(progress_paused_task_manager)
