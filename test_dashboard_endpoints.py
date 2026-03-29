import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Authentication.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken
import json

user = CustomUser.objects.filter(email='jmbngugimbugua@gmail.com').first()
if user:
    token = str(RefreshToken.for_user(user).access_token)
    headers = {'Authorization': f'Bearer {token}'}
    
    # Simulate the exact Dashboard API calls
    endpoints = [
        'http://localhost:8000/api/opinions/feed/?type=announcements&limit=30',
        'http://localhost:8000/api/opinions/feed/?type=products&limit=30',
        'http://localhost:8000/api/announcements/',
        'http://localhost:8000/api/tasks/tasks/',
        'http://localhost:8000/api/events/events/',
        'http://localhost:8000/api/payments/groups/',
        'http://localhost:8000/api/payments/payment-groups/'
    ]
    
    for url in endpoints:
        print(f"\n--- Fetching: {url} ---")
        try:
            response = requests.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"Type: Dict. Keys: {list(data.keys())}")
                    if 'results' in data:
                        print(f"Results length: {len(data['results'])}")
                elif isinstance(data, list):
                    print(f"Type: List. Length: {len(data)}")
                else:
                    print(f"Type: {type(data)}")
            except json.JSONDecodeError:
                print("Failed to parse JSON. Raw response start:")
                print(response.text[:200])
                
        except Exception as e:
            print(f"Request failed: {e}")

else:
    print("User not found.")
