from flask import Flask, jsonify, request
import sqlite3
import requests
import logging
from datetime import datetime
import pytz


logger = logging.getLogger()

app = Flask(__name__)

def send_data_to_django():
    conn = sqlite3.connect('time_tracking.db')
    cursor = conn.cursor()
    tracking_data = cursor.execute("SELECT * FROM tracking").fetchall()
    token_data = cursor.execute("SELECT * FROM token").fetchall()
    database_id_data = cursor.execute("SELECT * FROM database_id").fetchall()
    conn.close()

    payload = {
        'tracking_data': tracking_data,
        'token_data': token_data,
        'database_id_data':database_id_data,
    }

    # Send data to Django app
    response = requests.post('http://127.0.0.1:8000/receive_data/', json=payload)
    print(response.content)

    # Log the response message
    response_data = response.json()
    message = response_data.get('message', response_data.get('error', 'Unknown response'))
    logger.info(message)


    if response.status_code == 200:
        logger.info(f"Data sent to django app successfully!")
        return True
    else:
        logger.error(f"Failed to send data to django app. Response: {response.content}")
        return False

@app.route('/send_data', methods=['GET','POST'])
def send_data_to_django_web():
    success = send_data_to_django()
    if success:
        return jsonify({"message": "Data sent to django app successfully!"}), 200
    else:
        return jsonify({"error": "Failed to send data to django app."}), 500


@app.route('/receive_data/', methods=['GET','POST'])
def receive_data():
    try:
        data = request.json
        database_ids = data['django_database_id_data']
        tokens = data['django_token_data']

        # Connect to SQLite database
        conn = sqlite3.connect('time_tracking.db')
        cursor = conn.cursor()

        # Get current time in GMT-3
        sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
        current_time = datetime.now(sao_paulo_tz)

        # Insert data into SQLite tables
        for item in database_ids:
            cursor.execute("INSERT OR IGNORE INTO database_id (database_id, description, created_at) VALUES (?, ?, ?)",
                           (item['database_id'], item['description'], current_time))

        for item in tokens:
            cursor.execute("INSERT OR IGNORE INTO token (token_id, description, created_at) VALUES (?, ?, ?)",
                           (item['token_id'], item['description'], current_time))

        # Commit changes and close connection
        conn.commit()
        conn.close()

        return jsonify({"message": "Data received by script successfully!"})


    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)