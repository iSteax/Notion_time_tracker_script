#!/bin/bash

# Start the Flask server
python recieve_data_from_django_app.py &

# Start the main script
python main.py