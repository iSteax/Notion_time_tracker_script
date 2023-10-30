import sqlite3
from notion_client import Client
import logging
from convert_utilites import convert_iso_to_standard_format
from get_token_database_id import TOKEN, get_database_ids
from progress_paused_done_statuses import update_or_insert_task



logger = logging.getLogger()

# SQLite setup
conn = sqlite3.connect('time_tracking.db')
cursor = conn.cursor()

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