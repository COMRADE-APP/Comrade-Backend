import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Authentication.models import CustomUser
from rest_framework_simplejwt.tokens import RefreshToken

user = CustomUser.objects.filter(email='jmbngugimbugua@gmail.com').first()
if user:
    token = str(RefreshToken.for_user(user).access_token)
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get('http://localhost:8000/api/opinions/feed/?type=all&limit=30', headers=headers)
    print(f"Status: {response.status_code}")
    print(response.text)
else:
    print("User not found.")
