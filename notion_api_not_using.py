import requests
import json


# Your Notion API key and database ID
API_KEY = '****'
DATABASE_ID = '****'

# Endpoint URL
url = 'https://api.notion.com/v1/databases/****/query'

# Headers
headers = {
    'Authorization': f"Bearer {API_KEY}",
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

# Data payload
data = {

}

# Make the request
response = requests.post(url, headers=headers, json=data)

# Print the response
print(response.json())




