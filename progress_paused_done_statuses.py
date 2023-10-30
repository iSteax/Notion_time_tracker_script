import sqlite3
from datetime import datetime
from notion_client import Client
import logging
from send_data_from_script_to_django_app import send_data_to_django
from convert_utilites import calculate_elapsed_time, hms_str_to_timedelta, timedelta_to_hms_str
from get_token_database_id import TOKEN
from tasks_utilites import update_task_in_notion, clear_priority_in_notion



logger = logging.getLogger()

# SQLite setup
conn = sqlite3.connect('time_tracking.db')
cursor = conn.cursor()

# Notion connect
client = Client(auth=TOKEN)

in_progress_tasks = set()
paused_tasks = set()

def update_or_insert_task(task_id, task_name, status):
    """Insert or update a task in the SQLite database."""
    existing_task = cursor.execute("SELECT status FROM tracking WHERE task_id=?", (task_id,)).fetchone()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    previous_status = existing_task[0] if existing_task else None

    # If the status hasn't changed, there's no need to update the elapsed time
    if status == previous_status:
        return

    if status == "In progress" and task_id not in in_progress_tasks:
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if existing_task:  # If the task already exists in the database
            cursor.execute("UPDATE tracking SET status=?, start_time=?, task_name=? WHERE task_id=?",
                           (status, start_time, task_name, task_id))
        else:  # If it's a new task
            cursor.execute("INSERT INTO tracking (task_id, task_name, status, start_time) VALUES (?, ?, ?, ?)",
                           (task_id, task_name, status, start_time))
        update_task_in_notion(task_id, "Start time", start_time, value_type="date")
        in_progress_tasks.add(task_id)
        if task_id in paused_tasks:
            paused_tasks.remove(task_id)
        # send_data_to_django()

    elif status == "Paused" and task_id not in paused_tasks:
        result = cursor.execute("SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,)).fetchone()
        if result:
            start_time_str, previous_elapsed_time_str = result
        else:
            start_time_str, previous_elapsed_time_str = None, None

        if start_time_str:
            current_elapsed_time = calculate_elapsed_time(start_time_str, now)
            logging.info(f"Current Elapsed Time: {current_elapsed_time}")  # Debugging line
            if previous_elapsed_time_str:
                previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
                logging.info(f"Previous Elapsed Time: {previous_elapsed_time}")  # Debugging line
                total_elapsed_time = previous_elapsed_time + current_elapsed_time
            else:
                total_elapsed_time = current_elapsed_time
            elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
            logging.info(f"Total Elapsed Time: {elapsed_time_str}")  # Debugging line
            cursor.execute("UPDATE tracking SET status=?, paused_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
                           (status, now, elapsed_time_str, task_name, task_id))
            update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
            update_task_in_notion(task_id, "Paused time", now, value_type="date")
            if task_id in in_progress_tasks:
                in_progress_tasks.remove(task_id)
            paused_tasks.add(task_id)
        # send_data_to_django()

    elif status == "Done" and task_id in in_progress_tasks:
        if existing_task:
            cursor.execute("UPDATE tracking SET status=?, done_time=? WHERE task_id=?", (status, now, task_id))
        else:
            cursor.execute("INSERT INTO tracking (task_id, status, done_time) VALUES (?, ?, ?)", (task_id, status, now))
        start_time_str, previous_elapsed_time_str = cursor.execute(
            "SELECT start_time, elapsed_time FROM tracking WHERE task_id=?", (task_id,)).fetchone()
        if start_time_str:
            current_elapsed_time = calculate_elapsed_time(start_time_str, now)
            if previous_elapsed_time_str:
                previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
                total_elapsed_time = previous_elapsed_time + current_elapsed_time
            else:
                total_elapsed_time = current_elapsed_time
            elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
            cursor.execute("UPDATE tracking SET status=?, done_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
                           (status, now, elapsed_time_str, task_name, task_id))
            update_task_in_notion(task_id, "Elapsed time", elapsed_time_str, value_type="text")
            update_task_in_notion(task_id, "Done time", now, value_type="date")
            if task_id in in_progress_tasks:
                in_progress_tasks.remove(task_id)
        clear_priority_in_notion(task_id)
        # send_data_to_django()

    elif status == "Done" and task_id in paused_tasks:
        paused_time = cursor.execute("SELECT paused_time FROM tracking WHERE task_id=?", (task_id,)).fetchone()[0]
        if existing_task:
            cursor.execute("UPDATE tracking SET status=?, done_time=?, task_name=? WHERE task_id=?",
                           (status, paused_time, task_name, task_id))
        else:
            cursor.execute("INSERT INTO tracking (task_id, status, done_time) VALUES (?, ?, ?)",
                           (task_id, status, paused_time))
        update_task_in_notion(task_id, "Done time", paused_time, value_type="date")
        if task_id in paused_tasks:
            paused_tasks.remove(task_id)
        clear_priority_in_notion(task_id)
        # send_data_to_django()

    else:
        if existing_task:
            cursor.execute("UPDATE tracking SET status=?, task_name=? WHERE task_id=?", (status, task_name, task_id))
        else:
            cursor.execute("INSERT INTO tracking (task_id, task_name, status) VALUES (?, ?, ?)",
                           (task_id, task_name, status))
        # send_data_to_django()
    conn.commit()

    send_data_to_django()