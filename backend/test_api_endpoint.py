"""Test if the graph API endpoint is accessible."""

import requests

try:
    response = requests.get('http://localhost:8000/api/graph/data', params={'group_id': 'default', 'limit': 50})
    print(f'Status Code: {response.status_code}')
    print(f'Response: {response.text[:500]}')
except Exception as e:
    print(f'Error: {e}')
