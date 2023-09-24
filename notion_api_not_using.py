import requests
import json


# Your Notion API key and database ID
API_KEY = 'secret_T5YjPnpQAocyzKzVTr5TXk1mg30CXs2I4KtN5xUlVsy'
DATABASE_ID = 'dd9097c4-ba75-41a5-87e9-ddfab6fe8b14'

# Endpoint URL
url = 'https://api.notion.com/v1/databases/dd9097c4-ba75-41a5-87e9-ddfab6fe8b14/query'

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




