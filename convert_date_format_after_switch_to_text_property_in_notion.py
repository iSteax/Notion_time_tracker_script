from notion_client import Client
from get_token_database_id import TOKEN, get_database_ids
from tasks_utilites import update_task_in_notion
from datetime import datetime
import sys

print("Starting fetch and update script...")

client = Client(auth=TOKEN)


def refresh_database_id_values():
    global database_id
    database_id = get_database_ids()
    print(f"Database IDs: {database_id}")


def extract_date_from_rich_text(rich_text_list):
    """
    Given a rich_text list from Notion, extract a raw date string.
    If the item type is "text", return its content.
    If the item type is "mention" with a date, return the 'start' field.
    Otherwise, return an empty string.
    """
    if not rich_text_list:
        return ""
    item = rich_text_list[0]
    if item.get("type") == "text":
        return item.get("text", {}).get("content", "")
    elif item.get("type") == "mention":
        mention = item.get("mention", {})
        if mention.get("type") == "date":
            return mention.get("date", {}).get("start", "")
    return ""


def convert_notion_date(notion_date_str):
    """
    Convert a date string to the target format "%d/%m/%Y %H:%M".

    - If the string is already in that format but includes seconds (e.g. "01/11/2024 17:51:00"),
      return it without the seconds (e.g. "01/11/2024 17:51").
    - If the string appears to be ISO (contains 'T'), use fromisoformat() to parse it.
    - Otherwise, assume it's in the original Notion format (e.g. "@November 1, 2024 5:51 PM")
      and convert it.
    """
    if not notion_date_str:
        return ""

    # First, try to parse with the target format including seconds.
    try:
        dt = datetime.strptime(notion_date_str, "%d/%m/%Y %H:%M:%S")
        # Remove seconds and return.
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        pass

    # Next, try to parse with the target format without seconds.
    try:
        datetime.strptime(notion_date_str, "%d/%m/%Y %H:%M")
        # Already in target format without seconds.
        return notion_date_str
    except ValueError:
        pass

    # If it looks like an ISO date (contains 'T'), try parsing it.
    if "T" in notion_date_str:
        try:
            dt = datetime.fromisoformat(notion_date_str.rstrip("Z"))
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception as e:
            print(f"Error parsing ISO date '{notion_date_str}': {e}", file=sys.stderr)
            return ""

    # Otherwise, assume it's in the original Notion format.
    try:
        cleaned = notion_date_str.lstrip('@').strip()
        dt = datetime.strptime(cleaned, "%B %d, %Y %I:%M %p")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception as e:
        print(f"Conversion error for '{notion_date_str}': {e}", file=sys.stderr)
        return ""


def fetch_and_update_notion_dates():
    refresh_database_id_values()

    count_converted = 0

    for db_id, db_name in database_id.items():
        try:
            print(f"Fetching data from database: {db_name}")
            tasks = client.databases.query(database_id=db_id)["results"]
        except Exception as e:
            print(f"Error fetching data from {db_name}: {e}")
            continue

        for task in tasks:
            task_id = task["id"]
            task_name = (task["properties"]["Name"]["title"][0]["text"]["content"]
                         if task["properties"]["Name"]["title"] else "No Name")

            # --- Process "Start time" ---
            raw_start_time = extract_date_from_rich_text(task["properties"].get("Start time", {}).get("rich_text", []))
            converted_start_time = convert_notion_date(raw_start_time)

            # --- Process "Paused time" ---
            raw_paused_time = extract_date_from_rich_text(
                task["properties"].get("Paused time", {}).get("rich_text", []))
            converted_paused_time = convert_notion_date(raw_paused_time)

            print(f"Task {task_id} - {task_name}")
            print(f"  Raw Start time: {raw_start_time if raw_start_time else 'None'}")
            print(f"  Converted Start time: {converted_start_time if converted_start_time else 'None'}")
            print(f"  Raw Paused time: {raw_paused_time if raw_paused_time else 'None'}")
            print(f"  Converted Paused time: {converted_paused_time if converted_paused_time else 'None'}")
            print("-" * 40)

            # Count conversion if raw != converted.
            if raw_start_time and converted_start_time and raw_start_time != converted_start_time:
                count_converted += 1
            if raw_paused_time and converted_paused_time and raw_paused_time != converted_paused_time:
                count_converted += 1

            # --- Update Notion with the converted values ---
            if converted_start_time:
                update_task_in_notion(task_id, "Start time", converted_start_time, value_type="text")
            if converted_paused_time:
                update_task_in_notion(task_id, "Paused time", converted_paused_time, value_type="text")

    print(f"Total dates converted: {count_converted}")


if __name__ == "__main__":
    fetch_and_update_notion_dates()








