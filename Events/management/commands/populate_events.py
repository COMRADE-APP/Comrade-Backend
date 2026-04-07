"""
Populate 7 sample events with different cover images for testing.
Usage: python manage.py populate_events
"""
from django.core.management.base import BaseCommand
from django.core.files import File
from django.utils import timezone
from datetime import timedelta, datetime
import os


class Command(BaseCommand):
    help = 'Create 7 sample events with cover images'

    def handle(self, *args, **options):
        from Events.models import Event
        from Authentication.models import CustomUser

        # Get the first admin/staff user as event creator
        creator = CustomUser.objects.filter(is_staff=True).first()
        if not creator:
            creator = CustomUser.objects.first()
        if not creator:
            self.stderr.write('No users found — create a user first.')
            return

        media_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        ))), 'media', 'event_covers')

        now = timezone.now()

        events_data = [
            {
                'name': 'Comrade Tech Summit 2026',
                'description': 'A full-day tech conference featuring keynotes on AI, blockchain, and fintech innovation. Network with industry leaders, participate in workshops, and discover the latest trends shaping the technology landscape across Africa.',
                'cover_file': 'tech_conf.png',
                'capacity': 500,
                'event_type': 'public',
                'event_location': 'physical',
                'location': 'Nairobi, KICC Convention Center',
                'start_time': '09:00:00',
                'end_time': '18:00:00',
                'event_date': now + timedelta(days=14),
                'booking_deadline': now + timedelta(days=12),
                'price': 25.00,
                'complexity_level': 'sophisticated',
            },
            {
                'name': 'Afrobeats Live Music Festival',
                'description': 'Experience the best Afrobeats artists live! Three stages, 20+ artists, food vendors, and a vibrant community celebration. Early bird tickets available. VIP areas with premium viewing and backstage access.',
                'cover_file': 'music_fest.png',
                'capacity': 2000,
                'event_type': 'public',
                'event_location': 'physical',
                'location': 'Uhuru Gardens, Nairobi',
                'start_time': '14:00:00',
                'end_time': '23:00:00',
                'event_date': now + timedelta(days=21),
                'booking_deadline': now + timedelta(days=19),
                'price': 15.00,
                'complexity_level': 'sophisticated',
            },
            {
                'name': 'Creative Design Workshop',
                'description': 'Hands-on workshop covering UI/UX design principles, Figma mastery, and design systems. Bring your laptop and leave with a professional portfolio piece. Limited seats for a personalised experience.',
                'cover_file': 'workshop.png',
                'capacity': 30,
                'event_type': 'public',
                'event_location': 'physical',
                'location': 'iHub, Nairobi',
                'start_time': '10:00:00',
                'end_time': '16:00:00',
                'event_date': now + timedelta(days=7),
                'booking_deadline': now + timedelta(days=5),
                'price': 10.00,
                'complexity_level': 'small',
            },
            {
                'name': 'East African Food Festival',
                'description': 'Savour cuisines from Kenya, Tanzania, Uganda, Rwanda and beyond. Live cooking demos, competitions, and tastings. Family-friendly with a dedicated kids zone and entertainment.',
                'cover_file': 'food_fest.png',
                'capacity': 800,
                'event_type': 'public',
                'event_location': 'physical',
                'location': 'Carnivore Grounds, Nairobi',
                'start_time': '11:00:00',
                'end_time': '21:00:00',
                'event_date': now + timedelta(days=10),
                'booking_deadline': now + timedelta(days=8),
                'price': 0,
                'complexity_level': 'midlevel',
            },
            {
                'name': 'Inter-University Sports Championship',
                'description': 'Annual inter-university sports competition featuring basketball, football, athletics, and swimming. Join as a participant or spectator. Prizes for top performers. Live streaming available.',
                'cover_file': 'sports_tourney.png',
                'capacity': 1200,
                'event_type': 'public',
                'event_location': 'hybrid',
                'event_url': 'https://stream.comrade.app/sports-championship',
                'location': 'Kasarani Stadium, Nairobi',
                'start_time': '08:00:00',
                'end_time': '17:00:00',
                'event_date': now + timedelta(days=28),
                'booking_deadline': now + timedelta(days=25),
                'price': 5.00,
                'complexity_level': 'sophisticated',
            },
            {
                'name': 'Comrade Charity Gala Evening',
                'description': 'An elegant evening of fine dining, live performances, and silent auctions. All proceeds support education initiatives for underprivileged youth. Black-tie dress code. Includes a 4-course dinner.',
                'cover_file': 'charity_gala.png',
                'capacity': 200,
                'event_type': 'private',
                'event_location': 'physical',
                'location': 'Radisson Blu, Nairobi',
                'start_time': '18:30:00',
                'end_time': '23:30:00',
                'event_date': now + timedelta(days=35),
                'booking_deadline': now + timedelta(days=30),
                'price': 50.00,
                'complexity_level': 'sophisticated',
            },
            {
                'name': 'Virtual Startup Pitch Night',
                'description': 'Watch 10 early-stage startups pitch to a panel of venture capitalists. Interactive Q&A, networking rooms, and a People\'s Choice vote. Join from anywhere via Zoom.',
                'image_url': 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800',
                'capacity': 500,
                'event_type': 'public',
                'event_location': 'online',
                'event_url': 'https://zoom.us/j/pitch-night-2026',
                'location': 'Online (Zoom)',
                'start_time': '19:00:00',
                'end_time': '21:30:00',
                'event_date': now + timedelta(days=5),
                'booking_deadline': now + timedelta(days=4),
                'price': 0,
                'complexity_level': 'midlevel',
            },
        ]

        created_count = 0
        for data in events_data:
            cover_file = data.pop('cover_file', None)
            image_url = data.pop('image_url', None)
            price = data.pop('price', 0)

            # Build the event
            event = Event(
                created_by=creator,
                duration=timedelta(hours=4),
                status='active',
                **data
            )

            # Attach cover image
            if cover_file:
                cover_path = os.path.join(media_root, cover_file)
                if os.path.exists(cover_path):
                    with open(cover_path, 'rb') as f:
                        event.cover_image.save(cover_file, File(f), save=False)
                else:
                    self.stderr.write(f'  Cover not found: {cover_path}')
            elif image_url:
                event.image_url = image_url

            event.save()
            created_count += 1
            self.stdout.write(f'  * {event.name}')

        self.stdout.write(self.style.SUCCESS(f'\nCreated {created_count} events!'))
