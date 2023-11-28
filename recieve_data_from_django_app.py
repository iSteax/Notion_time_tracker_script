from flask import Flask, jsonify, request
import sqlite3
import requests
import logging
from datetime import datetime
import pytz

logger = logging.getLogger()

app = Flask(__name__)

@app.route('/receive_data/', methods=['GET','POST'])
def receive_data():
    try:
        logger.info(f"data come")
        data = request.json
        database_ids = data['django_database_id_data']
        tokens = data['django_token_data']

        # Connect to SQLite database
        conn = sqlite3.connect('time_tracking.db')
        cursor = conn.cursor()
        logger.info(f"connected to time_tracking.db")


        # Get current time in GMT-3
        # sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
        current_time = datetime.now()

        #delete data from token table
        cursor.execute("DELETE FROM token")
        cursor.execute("DELETE FROM database_id")
        conn.commit()
        logger.info(f"tokens were deleted")


        # Insert data into SQLite tables
        for item in database_ids:
            cursor.execute("INSERT OR IGNORE INTO database_id (database_id, description, created_at) VALUES (?, ?, ?)",(item['database_id'], item['description'], current_time))
            logger.info(f"database_id tabled populated")

        for item in tokens:
            cursor.execute("INSERT OR IGNORE INTO token (token_id, description, created_at) VALUES (?, ?, ?)",(item['token_id'], item['description'], current_time))
            logger.info(f"token tabled populated")

        # Commit changes and close connection
        conn.commit()
        conn.close()

        return jsonify({"message": "Data received by script successfully!"})


    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)