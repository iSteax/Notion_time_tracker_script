import sqlite3
from datetime import datetime, timedelta
from notion_client import Client
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from send_data_from_script_to_django_app import send_data_to_django
from config import database_id, TOKEN
from SQliteDB_class import SQLiteDB


logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=3)  # 5MB per log file, keep 3 old logs
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# Instantiate the SQLiteDB for further usage
db = SQLiteDB('time_tracking.db')

# Create table if not exists for main data
db.execute('''
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
db.execute('''
CREATE TABLE IF NOT EXISTS token (
    token_id TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

db.execute('''
CREATE TABLE IF NOT EXISTS database_id (
    database_id TEXT PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Insert TOKEN data
for token_id, description in TOKEN.items():
    db.execute("INSERT OR IGNORE INTO token (token_id, description) VALUES (?, ?)", (token_id, description))

# Insert database_id data
for db_id, description in database_id.items():
    db.execute("INSERT OR IGNORE INTO database_id (database_id, description) VALUES (?, ?)", (db_id, description))


#get token and database_id from the table

def get_token():
    token_value = db.fetch_one("SELECT token_id FROM token")
    return token_value[0] if token_value else None

def get_database_ids():
    db_data = db.fetch_all("SELECT database_id, description FROM database_id")
    return {entry[0]: entry[1] if entry[1] else "Description not available" for entry in db_data}


TOKEN = get_token()
database_id = get_database_ids()

logger.info(f"TOKEN: {TOKEN}")
logger.info(f"database_id: {database_id}")

# Notion connect
client = Client(auth=TOKEN)

def timedelta_to_hms_str(td):
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))


def hms_str_to_timedelta(hms_str):
    parts = list(map(int, hms_str.split(':')))
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, minutes = parts
        seconds = 0
    else:
        raise ValueError(f"Invalid format for hms_str: {hms_str}")
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def clear_priority_in_notion(task_id):
    try:
        logging.info(f"Attempting to clear 'Priority' for task '{task_id}' in Notion")

        properties = {
            "Priority": None  # Clearing the Priority column
        }

        response = client.pages.update(page_id=task_id, properties=properties)
        logging.info(f"Response from Notion API: {response}")
        logging.info(f"Cleared 'Priority' for task '{task_id}' in Notion")
    except Exception as e:
        logging.error(f"Error clearing 'Priority' for task '{task_id}' in Notion", exc_info=True)


def load_tasks_status_from_db():
    global in_progress_tasks, paused_tasks, db

    # Fetch tasks with "In progress" status
    in_progress_from_db = db.fetch_all("SELECT task_id FROM tracking WHERE status=?", ("In progress",))
    in_progress_tasks = {task[0] for task in in_progress_from_db}

    # Fetch tasks with "Paused" status
    paused_from_db = db.fetch_all("SELECT task_id FROM tracking WHERE status=?", ("Paused",))
    paused_tasks = {task[0] for task in paused_from_db}


def update_task_in_notion(task_id, column_name, value, value_type="date"):
    try:
        logging.info(f"Attempting to update task '{task_id}' in Notion: {column_name} = {value}")

        if value_type == "date":
            properties = {
                column_name: {
                    "type": "date",
                    "date": {
                        "start": value,
                        "time_zone": "America/Sao_Paulo"
                    }
                }
            }
        elif value_type == "text":
            properties = {
                column_name: {
                    "type": "rich_text",
                    "rich_text": [{"type": "text", "text": {"content": value}}]
                }
            }
        else:
            raise ValueError(f"Unsupported value type: {value_type}")

        response = client.pages.update(page_id=task_id, properties=properties)
        logging.info(f"Response from Notion API: {response}")
        logging.info(f"Updated task '{task_id}' in Notion: {column_name} = {value}")
    except Exception as e:
        logging.error(f"Error updating task '{task_id}' in Notion", exc_info=True)


def get_task_status(task_id):
    page = client.pages.retrieve(page_id=task_id)
    status_property = page["properties"].get("Status", {}).get("select")
    if status_property:
        return status_property.get("name")
    return None


def calculate_elapsed_time(start_time_str, paused_time_str):
    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
    paused_time = datetime.strptime(paused_time_str, '%Y-%m-%d %H:%M:%S')
    return paused_time - start_time


def update_or_insert_task(task_id, task_name, status):
    """Insert or update a task in the SQLite database."""
    existing_task = db.fetch_one("SELECT status FROM tracking WHERE task_id=?", (task_id,))
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    previous_status = existing_task[0] if existing_task else None

    # If the status hasn't changed, there's no need to update the elapsed time
    if status == previous_status:
        return

    if status == "In progress" and task_id not in in_progress_tasks:
        start_time = now
        if existing_task:
            db.execute("UPDATE tracking SET status=?, start_time=?, task_name=? WHERE task_id=?",
                             (status, start_time, task_name, task_id))
        else:
            db.execute("INSERT INTO tracking (task_id, task_name, status, start_time) VALUES (?, ?, ?, ?)",
                             (task_id, task_name, status, start_time))
        update_task_in_notion(task_id, "Start time", start_time, value_type="date")
        in_progress_tasks.add(task_id)
        if task_id in paused_tasks:
            paused_tasks.remove(task_id)

    elif status == "Paused" and task_id not in paused_tasks:
        result = db.fetch_one("SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))
        start_time_str, previous_elapsed_time_str = result if result else (None, None)
        if start_time_str:
            current_elapsed_time = calculate_elapsed_time(start_time_str, now)
            if previous_elapsed_time_str:
                previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
                total_elapsed_time = previous_elapsed_time + current_elapsed_time
            else:
                total_elapsed_time = current_elapsed_time
            elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
            db.execute("UPDATE tracking SET status=?, paused_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
                             (status, now, elapsed_time_str, task_name, task_id))
            update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
            update_task_in_notion(task_id, "Paused time", now, value_type="date")
            if task_id in in_progress_tasks:
                in_progress_tasks.remove(task_id)
            paused_tasks.add(task_id)

    elif status == "Done":
        if task_id in in_progress_tasks:
            start_time_str, previous_elapsed_time_str = db.fetch_one(
                "SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))
            current_elapsed_time = calculate_elapsed_time(start_time_str, now)
            if previous_elapsed_time_str:
                previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
                total_elapsed_time = previous_elapsed_time + current_elapsed_time
            else:
                total_elapsed_time = current_elapsed_time
            elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
            db.execute("UPDATE tracking SET status=?, done_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
                             (status, now, elapsed_time_str, task_name, task_id))
            update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
            update_task_in_notion(task_id, "Done time", now, value_type="date")
            in_progress_tasks.remove(task_id)
            clear_priority_in_notion(task_id)

        elif task_id in paused_tasks:
            paused_time = db.fetch_one("SELECT paused_time FROM tracking WHERE task_id=?", (task_id,))[0]
            db.execute("UPDATE tracking SET status=?, done_time=?, task_name=? WHERE task_id=?",
                             (status, paused_time, task_name, task_id))
            update_task_in_notion(task_id, "Done time", paused_time, value_type="date")
            paused_tasks.remove(task_id)
            clear_priority_in_notion(task_id)

    else:
        if existing_task:
            db.execute("UPDATE tracking SET status=?, task_name=? WHERE task_id=?",
                             (status, task_name, task_id))
        else:
            db.execute("INSERT INTO tracking (task_id, task_name, status) VALUES (?, ?, ?)",
                             (task_id, task_name, status))

    send_data_to_django()


def convert_iso_to_standard_format(iso_time_str):
    dt = datetime.fromisoformat(iso_time_str)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def refresh_database_id_values():
    global database_id

    # Refresh database_id from SQLite database
    database_id = get_database_ids()

def fetch_data_from_notion():
    # Refresh TOKEN and database_id from SQLite
    refresh_database_id_values()

    logger.info(f"database_id_fetch_from_notion: {database_id}")

    fetched_task_ids = set()  # This set will store the IDs of tasks fetched from Notion whose status is not "Done"

    for db_id, db_name in database_id.items():
        logging.info(f"Fetching data from database: {db_name}")
        tasks = client.databases.query(database_id=db_id)["results"]

        for task in tasks:
            task_name = task["properties"]["Name"]["title"][0]["text"]["content"] if task["properties"]["Name"]["title"] else None
            task_id = task["id"]

            # Retrieve the status from the Notion task
            status_property = task["properties"].get("Status", {}).get("select")
            status = status_property.get("name") if status_property else None

            if task_id and status:
                # Check if the time-related fields in Notion differ from those in the SQLite database
                existing_task = db.fetch_one("SELECT start_time, paused_time, done_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,))

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
                        db.execute("UPDATE tracking SET start_time=?, paused_time=?, done_time=?, elapsed_time=? WHERE task_id=?",
                            (start_time, paused_time, done_time, elapsed_time, task_id))

                # Insert or update the task in SQLite using the function
                update_or_insert_task(task_id, task_name, status)  # Assuming this function will also be updated to use the SQLiteDB class

                # Only add the task ID to the set if its status is not "Done"
                if status != "Done":
                    fetched_task_ids.add(task_id)
                    # logging.info(f"Added task ID {task_id} to fetched_task_ids set")

    logging.info(f"Fetched_task_ids set: {fetched_task_ids}")
    return fetched_task_ids


def main():
    global in_progress_tasks, paused_tasks, db

    print("Time_tracker run successfully")

    # Load tasks from the database
    load_tasks_status_from_db()

    while True:
        try:
            # Fetch tasks from Notion and get their IDs
            fetched_task_ids = fetch_data_from_notion()

            # Get all task IDs from the SQLite database
            all_db_task_ids = {task[0] for task in db.fetch_all("SELECT task_id FROM tracking")}

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

