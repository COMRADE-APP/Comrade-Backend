import django
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Comrade.settings")
django.setup()

from Events.serializers import EventSerializer

data = {
    'name': 'Test Event',
    'description': 'Test Event Description',
    'event_location': 'physical',
    'event_type': 'public',
    'location': 'Nairobi',
    'event_url': '',
    'event_date': '2026-03-25T09:00:00Z',
    'start_time': '09:00:00',
    'end_time': '17:00:00',
    'booking_deadline': '2026-03-25T09:00:00Z',
    'capacity': 100,
    'duration': '08:00:00',
    'complexity_level': 'small',
    'booking_status': 'open',
    'is_ticketed': False,
    'seeking_sponsors': False,
    'seeking_partners': False,
    'status': 'active',
    'scheduled_time': '2026-03-25T09:00:00Z'
}
serializer = EventSerializer(data=data)
if not serializer.is_valid():
    print("ERRORS:", serializer.errors)
else:
    print("VALID!")
