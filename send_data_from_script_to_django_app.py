from flask import Flask, jsonify, request
import requests
import logging
from SQliteDB_class import SQLiteDB
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'time_tracking.db')

logger = logging.getLogger()

app = Flask(__name__)

# Instantiate the SQLiteDB for further usage
db = SQLiteDB(DB_PATH)

def send_data_to_django():
    # Using the SQLiteDB class within a 'with' statement
    with SQLiteDB(DB_PATH) as db:
        tracking_data = db.fetch_all("SELECT * FROM tracking")
        token_data = db.fetch_all("SELECT * FROM token")
        database_id_data = db.fetch_all("SELECT * FROM database_id")

    payload = {
        'tracking_data': tracking_data,
        'token_data': token_data,
        'database_id_data': database_id_data,
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

if __name__ == '__main__':
    app.run(port=5000)
