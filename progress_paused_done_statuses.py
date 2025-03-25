import sqlite3
from datetime import datetime
from notion_client import Client
import logging
from send_data_from_script_to_django_app import send_data_to_django
from convert_utilites import (calculate_elapsed_time, hms_str_to_timedelta, timedelta_to_hms_str,
      convert_text_to_iso, remove_seconds_for_notion, get_last_full_timestamp_from_db)
from get_token_database_id import TOKEN
from tasks_utilites import update_task_in_notion, clear_priority_in_notion



logger = logging.getLogger()

# SQLite setup
conn = sqlite3.connect('time_tracking.db')
cursor = conn.cursor()

# Notion connect
client = Client(auth=TOKEN)

# in_progress_tasks = set()
# paused_tasks = set()

class ProgressPausedTaskManager:
    def __init__(self):
        self.in_progress_tasks = set()
        self.paused_tasks = set()


def update_or_insert_task(progress_paused_task_manager, task_id, task_name, status, start_time_origin):
    """Insert or update a task in the SQLite database."""
    # Retrieve existing fields including paused_time and elapsed_time
    existing_task = cursor.execute(
        "SELECT status, start_time, paused_time, elapsed_time, start_time_origin FROM tracking WHERE task_id=?",
        (task_id,)
    ).fetchone()
    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    previous_status = existing_task[0] if existing_task else None

    # If the status hasn't changed, no update is needed.
    if status == previous_status:
        return

    if status == "In progress":
        start_time = now  # new timestamp as a string
        if existing_task:
            current_start_time = existing_task[1]  # may include multiple lines
            # Append new start time with newline
            new_start_time_value = f"{current_start_time}\n{start_time}" if current_start_time else start_time
            # If start_time_origin is not set, update it with the new start time
            if not existing_task[4]:
                start_time_origin = start_time
                cursor.execute("UPDATE tracking SET start_time_origin=? WHERE task_id=?", (start_time_origin, task_id))
            cursor.execute(
                "UPDATE tracking SET status=?, start_time=?, task_name=? WHERE task_id=?",
                (status, new_start_time_value, task_name, task_id)
            )
        else:
            # For a new task, set start_time_origin to the current time.
            start_time_origin = start_time
            new_start_time_value = start_time
            cursor.execute(
                "INSERT INTO tracking (task_id, task_name, status, start_time, start_time_origin) VALUES (?, ?, ?, ?, ?)",
                (task_id, task_name, status, new_start_time_value, start_time_origin)
            )
        # Update Notion's "Start time" with the concatenated start times.
        update_task_in_notion(task_id, "Start time", remove_seconds_for_notion(new_start_time_value), value_type="text")

    elif status == "Paused":
        result = cursor.execute(
            "SELECT start_time, paused_time, elapsed_time, start_time_origin FROM tracking WHERE task_id=?",
            (task_id,)
        ).fetchone()
        if result:
            start_time_str, existing_paused_time, previous_elapsed_time_str, start_time_origin = result
        else:
            start_time_str, existing_paused_time, previous_elapsed_time_str, start_time_origin = None, None, None, None

        if start_time_str:
            # Use the last start time from the multi-line field for the current pause period
            latest_start_time = get_last_full_timestamp_from_db(start_time_str)
            current_elapsed_time = calculate_elapsed_time(latest_start_time, now)
            logging.info(f"Current Elapsed Time: {current_elapsed_time}")
            if previous_elapsed_time_str:
                previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
                total_elapsed_time = previous_elapsed_time + current_elapsed_time
            else:
                total_elapsed_time = current_elapsed_time
            elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
            logging.info(f"Total Elapsed Time: {elapsed_time_str}")
        else:
            elapsed_time_str = ""  # default to empty string if no elapsed time is calculated

        # Append the new paused time to any existing paused_time using a newline.
        new_paused_time = now
        new_paused_time_value = f"{existing_paused_time}\n{new_paused_time}" if existing_paused_time else new_paused_time

        cursor.execute(
            "UPDATE tracking SET status=?, paused_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
            (status, new_paused_time_value, elapsed_time_str, task_name, task_id)
        )
        # Ensure we send a string (or empty string) for elapsed time
        update_task_in_notion(task_id, "Elapsed time", elapsed_time_str if elapsed_time_str is not None else "", value_type="text")
        # For multi-line paused times, Notion property must be text.
        update_task_in_notion(task_id, "Paused time", remove_seconds_for_notion(new_paused_time_value), value_type="text")
        # Preserve the full multi-line start_time in Notion.
        if start_time_str:
            update_task_in_notion(task_id, "Start time", remove_seconds_for_notion(start_time_str), value_type="text")
        elif start_time_origin:
            update_task_in_notion(task_id, "Start time", remove_seconds_for_notion(start_time_origin), value_type="text")

    elif status == "Done" and previous_status == "In progress":
        if existing_task:
            cursor.execute("UPDATE tracking SET status=?, done_time=? WHERE task_id=?", (status, now, task_id))
        else:
            cursor.execute("INSERT INTO tracking (task_id, status, done_time) VALUES (?, ?, ?)", (task_id, status, now))
        result = cursor.execute(
            "SELECT start_time, elapsed_time, start_time_origin FROM tracking WHERE task_id=?",
            (task_id,)
        ).fetchone()
        if result:
            start_time_str, previous_elapsed_time_str, start_time_origin = result
        else:
            start_time_str, previous_elapsed_time_str, start_time_origin = None, None, None

        if start_time_str:
            latest_start_time = start_time_str.split('\n')[-1]
            current_elapsed_time = calculate_elapsed_time(latest_start_time, now)
            if previous_elapsed_time_str:
                previous_elapsed_time = hms_str_to_timedelta(previous_elapsed_time_str)
                total_elapsed_time = previous_elapsed_time + current_elapsed_time
            else:
                total_elapsed_time = current_elapsed_time
            elapsed_time_str = timedelta_to_hms_str(total_elapsed_time)
        else:
            elapsed_time_str = ""

        cursor.execute(
            "UPDATE tracking SET status=?, done_time=?, elapsed_time=?, task_name=? WHERE task_id=?",
            (status, now, elapsed_time_str, task_name, task_id)
        )
        update_task_in_notion(task_id, "Elapsed time", elapsed_time_str if elapsed_time_str is not None else "", value_type="text")
        update_task_in_notion(task_id, "Done time", convert_text_to_iso(now), value_type="date")
        if start_time_str:
            update_task_in_notion(task_id, "Start time", start_time_str, value_type="text")
        elif start_time_origin:
            update_task_in_notion(task_id, "Start time", start_time_origin, value_type="text")
        clear_priority_in_notion(task_id)

    elif status == "Done" and previous_status == "Paused":
        paused_time = cursor.execute("SELECT paused_time FROM tracking WHERE task_id=?", (task_id,)).fetchone()[0]
        if existing_task:
            cursor.execute("UPDATE tracking SET status=?, done_time=?, task_name=? WHERE task_id=?",
                           (status, paused_time, task_name, task_id))
        else:
            cursor.execute("INSERT INTO tracking (task_id, status, done_time) VALUES (?, ?, ?)",
                           (task_id, status, paused_time))
        update_task_in_notion(task_id, "Done time", convert_text_to_iso(paused_time), value_type="date")
        clear_priority_in_notion(task_id)

    else:
        if existing_task:
            cursor.execute("UPDATE tracking SET status=?, task_name=? WHERE task_id=?", (status, task_name, task_id))
        else:
            cursor.execute("INSERT INTO tracking (task_id, task_name, status) VALUES (?, ?, ?)",
                           (task_id, task_name, status))
    conn.commit()
    send_data_to_django()





