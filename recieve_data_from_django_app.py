from flask import Flask, jsonify, request
import requests
import logging
from datetime import datetime
import pytz
from SQliteDB_class import SQLiteDB

logger = logging.getLogger()

app = Flask(__name__)

# Instantiate the SQLiteDB for further usage
db = SQLiteDB('time_tracking.db')

@app.route('/receive_data/', methods=['GET','POST'])
def receive_data():
    try:
        logger.info(f"data come")
        data = request.json
        database_ids = data['django_database_id_data']
        tokens = data['django_token_data']

        # Get current time in GMT-3
        sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
        current_time = datetime.now(sao_paulo_tz)

        # Delete data from token and database_id tables using SQLiteDB class
        db.execute("DELETE FROM token")
        db.execute("DELETE FROM database_id")
        logger.info(f"tokens and database IDs were deleted")

        # Insert data into SQLite tables using SQLiteDB class
        for item in database_ids:
            db.execute("INSERT OR IGNORE INTO database_id (database_id, description, created_at) VALUES (?, ?, ?)",
                       (item['database_id'], item['description'], current_time))
            logger.info(f"database_id table populated")

        for item in tokens:
            db.execute("INSERT OR IGNORE INTO token (token_id, description, created_at) VALUES (?, ?, ?)",
                       (item['token_id'], item['description'], current_time))
            logger.info(f"token table populated")

        return jsonify({"message": "Data received by script successfully!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000,threaded=False)
