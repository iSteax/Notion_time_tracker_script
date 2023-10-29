import logging
from logging.handlers import RotatingFileHandler
import os
import sqlite3


logger = logging.getLogger()

def get_token():
    conn = sqlite3.connect('time_tracking.db')
    cursor = conn.cursor()
    token_value = cursor.execute("SELECT token_id FROM token").fetchone()
    conn.close()
    return token_value[0] if token_value else None

def get_database_ids():
    conn = sqlite3.connect('time_tracking.db')
    cursor = conn.cursor()
    db_data = cursor.execute("SELECT database_id, description FROM database_id").fetchall()
    conn.close()
    return {entry[0]: entry[1] if entry[1] else "Description not available" for entry in db_data}

TOKEN = get_token()
database_id = get_database_ids()

logger.info(f"TOKEN: {TOKEN}")
logger.info(f"database_id: {database_id}")


# def refresh_database_id_values():
#     global database_id
#
#     # Refresh database_id from SQLite database
#     database_id = get_database_ids()