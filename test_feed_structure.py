import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Authentication.models import CustomUser
from rest_framework.test import APIRequestFactory, force_authenticate
from Opinions.views import UnifiedFeedView

factory = APIRequestFactory()
user = CustomUser.objects.filter(email='jmbngugimbugua@gmail.com').first()

if user:
    view = UnifiedFeedView.as_view()
    
    # Test opinions feed with user authenticatied
    request = factory.get('/api/opinions/feed/?type=all&limit=30')
    force_authenticate(request, user=user)
    
    response = view(request)
    
    # Inspect first 3 items to check data structure vs React expectations
    if hasattr(response, 'data') and 'results' in response.data:
        results = response.data['results']
        print(f"Total results: {len(results)}")
        for i, item in enumerate(results[:3]):
            print(f"\nItem {i+1} Type: {item.get('content_type')}")
            print(f"ID: {item.get('id')}")
            print(f"User attached? {'yes' if item.get('user') else 'no'}")
            print(f"Content length: {len(str(item.get('content', '')))}")
            if item.get('content_type') == 'research':
                print(f"Creator attached? {'yes' if item.get('creator') else 'no'}")
else:
    print("User not found.")
