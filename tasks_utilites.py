import logging
from logging.handlers import RotatingFileHandler
from notion_client import Client
from get_token_database_id import TOKEN, get_database_ids
import os
import sqlite3


# Notion connect
client = Client(auth=TOKEN)


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
    try:
        conn = sqlite3.connect('time_tracking.db')
        cursor = conn.cursor()

        # Fetch tasks with "In progress" status
        in_progress_from_db = cursor.execute("SELECT task_id FROM tracking WHERE status=?", ("In progress",)).fetchall()
        in_progress_tasks = {task[0] for task in in_progress_from_db}

        # Fetch tasks with "Paused" status
        paused_from_db = cursor.execute("SELECT task_id FROM tracking WHERE status=?", ("Paused",)).fetchall()
        paused_tasks = {task[0] for task in paused_from_db}

    except Exception as e:
        print("An error occurred:", e)
        in_progress_tasks = set()
        paused_tasks = set()
    finally:
        conn.close()

    return in_progress_tasks, paused_tasks


def update_task_in_notion(task_id, column_name, value, value_type="date"):
    try:
        logging.info(f"Attempting to update task '{task_id}' in Notion: {column_name} = {value}")

        if value_type == "date":
            properties = {
                column_name: {
                    "type": "date",
                    "date": {
                        "start": value,
                        # "time_zone": "America/Sao_Paulo"
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

