import sqlite3
from datetime import datetime, timedelta
from notion_client import Client
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from convert_utilites import calculate_elapsed_time, hms_str_to_timedelta, timedelta_to_hms_str, \
    convert_iso_to_standard_format
from get_token_database_id import TOKEN, database_id, get_database_ids
from progress_paused_done_statuses import update_or_insert_task
from send_data_from_script_to_django_app import send_data_to_django
from tasks_utilites import update_task_in_notion, clear_priority_in_notion, load_tasks_status_from_db



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


def refresh_database_id_values():
    global database_id

    # Refresh database_id from SQLite database
    database_id = get_database_ids()


def fetch_data_from_notion():
    # Refresh TOKEN and database_id from SQLite
    refresh_database_id_values()

    logger.info(f"database_id_fetch_from_notion: {database_id}")

    fetched_task_ids = set()                                                                                    # This set will store the IDs of tasks fetched from Notion whose status is not "Done"

    for db_id, db_name in database_id.items():
        logging.info(f"Fetching data from database: {db_name}")
        tasks = client.databases.query(database_id=db_id)["results"]

        for task in tasks:
            task_name = task["properties"]["Name"]["title"][0]["text"]["content"] if task["properties"]["Name"][
                "title"] else None
            task_id = task["id"]

            # Retrieve the status from the Notion task
            status_property = task["properties"].get("Status", {}).get("select")
            status = status_property.get("name") if status_property else None

            if task_id and status:
                # Check if the time-related fields in Notion differ from those in the SQLite database
                existing_task = cursor.execute(
                    "SELECT start_time, paused_time, done_time, elapsed_time FROM tracking WHERE task_id=?",
                    (task_id,)).fetchone()

                if existing_task:
                    db_start_time, db_paused_time, db_done_time, db_elapsed_time = existing_task

                    # Extract and convert the Start time
                    start_time_data = task["properties"].get("Start time", {}).get("date")
                    start_time = start_time_data.get("start") if start_time_data else None
                    if start_time:
                        start_time = convert_iso_to_standard_format(start_time)

                    # Extract and convert the Paused time
                    paused_time_data = task["properties"].get("Paused time", {}).get("date")
                    paused_time = paused_time_data.get("start") if paused_time_data else None
                    if paused_time:
                        paused_time = convert_iso_to_standard_format(paused_time)

                    # Extract and convert the Done time
                    done_time_data = task["properties"].get("Done time", {}).get("date")
                    done_time = done_time_data.get("start") if done_time_data else None
                    if done_time:
                        done_time = convert_iso_to_standard_format(done_time)

                    # Extract the Elapsed time (this remains unchanged as it's not in ISO 8601 format)
                    elapsed_time_data = task["properties"].get("Elapsed time", {}).get("rich_text", [])
                    elapsed_time = elapsed_time_data[0].get("text", {}).get("content") if elapsed_time_data else None

                    # Update the SQLite database if any of the fields have changed
                    if start_time != db_start_time or paused_time != db_paused_time or done_time != db_done_time or elapsed_time != db_elapsed_time:
                        cursor.execute(
                            "UPDATE tracking SET start_time=?, paused_time=?, done_time=?, elapsed_time=? WHERE task_id=?",
                            (start_time, paused_time, done_time, elapsed_time, task_id))
                        conn.commit()

                # Insert or update the task in SQLite using the function
                update_or_insert_task(task_id, task_name, status)

                # Only add the task ID to the set if its status is not "Done"
                if status != "Done":
                    fetched_task_ids.add(task_id)
                    # logging.info(f"Added task ID {task_id} to fetched_task_ids set")

    logging.info(f"Fetched_task_ids set: {fetched_task_ids}")
    return fetched_task_ids


def main():
    global in_progress_tasks, paused_tasks

    print("Time_tracker run successfully")

    # Load tasks from the database
    in_progress_tasks, paused_tasks = load_tasks_status_from_db()

    while True:
        try:
            # Fetch tasks from Notion and get their IDs
            fetched_task_ids = fetch_data_from_notion()

            # Get all task IDs from the SQLite database
            all_db_task_ids = {task[0] for task in cursor.execute("SELECT task_id FROM tracking").fetchall()}

            # Find tasks that are in the SQLite database but not in the fetched tasks from Notion
            deleted_task_ids = all_db_task_ids - fetched_task_ids

            # Remove deleted tasks' IDs from the in_progress_tasks and paused_tasks sets
            in_progress_tasks -= deleted_task_ids
            paused_tasks -= deleted_task_ids

            start_time = datetime.now()
            fetch_data_from_notion()
            end_time = datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()
            logging.info(f"Data fetched in {elapsed_time} seconds.")
            time.sleep(1)
            logging.info(f"Current in-progress tasks: {in_progress_tasks}")
            logging.info(f"Current paused tasks: {paused_tasks}")
        except Exception as e:
            logging.error(f"Error during main loop", exc_info=True)
            time.sleep(20)

if __name__ == "__main__":
    main()
