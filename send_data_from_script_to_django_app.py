from flask import Flask, jsonify, request
import sqlite3
import requests
import logging


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
    Authorization =  'dlvifgsjvyf157desa'
    headers = {
        'Authorization': Authorization,
    }

    response = requests.post('http://127.0.0.1:8000/receive_data/', json=payload,headers=headers)
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
    app.run(port=5050)