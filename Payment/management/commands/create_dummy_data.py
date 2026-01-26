"""
Management command to create dummy data for testing the platform.
Run with: python manage.py create_dummy_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Creates dummy data for testing the platform'

    def handle(self, *args, **options):
        self.stdout.write('Creating dummy data...')
        
        # Import models
        from Authentication.models import CustomUser, Profile
        from Payment.models import Partner, PartnerApplication, Product
        from Events.models import Event
        from Research.models import ResearchProject, ResearchPublication
        
        # Create test users if they don't exist
        test_users = []
        for i in range(1, 6):
            email = f'testuser{i}@example.com'
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': f'testuser{i}',
                    'first_name': f'Test{i}',
                    'last_name': f'User{i}',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(f'  Created user: {email}')
            test_users.append(user)
        
        # Get or create profiles
        profiles = []
        for user in test_users:
            profile, _ = Profile.objects.get_or_create(user=user)
            profiles.append(profile)
        
        # Create Partners
        partner_data = [
            {'partner_type': 'distributor', 'business_name': 'Global Books Distribution', 'city': 'New York', 'country': 'USA'},
            {'partner_type': 'publisher', 'business_name': 'Academic Press International', 'city': 'London', 'country': 'UK'},
            {'partner_type': 'author', 'business_name': 'Dr. Jane Smith - Author', 'city': 'Toronto', 'country': 'Canada'},
            {'partner_type': 'supplier', 'business_name': 'EduTech Supplies Ltd', 'city': 'Sydney', 'country': 'Australia'},
            {'partner_type': 'content_creator', 'business_name': 'LearnHub Studios', 'city': 'Berlin', 'country': 'Germany'},
        ]
        
        for i, data in enumerate(partner_data):
            partner, created = Partner.objects.get_or_create(
                user=profiles[i],
                business_name=data['business_name'],
                defaults={
                    'partner_type': data['partner_type'],
                    'contact_email': f'contact@{data["business_name"].lower().replace(" ", "")}.com',
                    'city': data['city'],
                    'country': data['country'],
                    'status': 'approved',
                    'verified': True,
                    'commission_rate': Decimal(str(random.randint(5, 20))),
                    'description': f'A leading {data["partner_type"]} in the education industry.',
                }
            )
            if created:
                self.stdout.write(f'  Created partner: {data["business_name"]}')
        
        # Create Products
        product_data = [
            {'name': 'Introduction to Python Programming', 'price': '29.99', 'type': 'digital', 'desc': 'Comprehensive Python course for beginners'},
            {'name': 'Advanced Mathematics Textbook', 'price': '49.99', 'type': 'physical', 'desc': 'University-level mathematics textbook'},
            {'name': 'Data Science Certification', 'price': '199.99', 'type': 'subscription', 'desc': '6-month data science certification program'},
            {'name': 'Study Planner Pro', 'price': '14.99', 'type': 'digital', 'desc': 'Digital study planning tool'},
            {'name': 'Lab Equipment Kit', 'price': '89.99', 'type': 'physical', 'desc': 'Complete lab equipment kit for science students'},
            {'name': 'Online Tutoring - 1 Hour', 'price': '35.00', 'type': 'service', 'desc': 'One-on-one online tutoring session'},
        ]
        
        for data in product_data:
            product, created = Product.objects.get_or_create(
                name=data['name'],
                defaults={
                    'description': data['desc'],
                    'price': Decimal(data['price']),
                    'product_type': data['type'],
                    'is_sharable': True,
                }
            )
            if created:
                self.stdout.write(f'  Created product: {data["name"]}')
        
        # Create Events
        try:
            event_data = [
                {'name': 'Annual Tech Conference 2026', 'location': 'Convention Center, New York'},
                {'name': 'Student Networking Mixer', 'location': 'University Hall'},
                {'name': 'AI in Education Workshop', 'location': 'Online'},
                {'name': 'Career Fair Spring 2026', 'location': 'Campus Main Building'},
            ]
            
            for i, data in enumerate(event_data):
                Event.objects.get_or_create(
                    name=data['name'],
                    defaults={
                        'description': f'Join us for {data["name"]}. A great opportunity to learn and connect.',
                        'location': data['location'],
                        'event_date': timezone.now().date() + timedelta(days=30 + i*7),
                        'start_time': '09:00:00',
                        'end_time': '17:00:00',
                        'capacity': random.randint(50, 500),
                        'visibility': 'public',
                        'status': 'active',
                        'organizer': profiles[0],
                    }
                )
                self.stdout.write(f'  Created event: {data["name"]}')
        except Exception as e:
            self.stdout.write(f'  Skipping events: {e}')
        
        # Create Research Projects
        try:
            research_data = [
                {'title': 'Impact of AI on Student Learning Outcomes', 'status': 'published'},
                {'title': 'Sustainable Campus Initiatives: A Case Study', 'status': 'in_progress'},
                {'title': 'Mental Health Among Graduate Students', 'status': 'peer_review'},
            ]
            
            for i, data in enumerate(research_data):
                project, created = ResearchProject.objects.get_or_create(
                    title=data['title'],
                    defaults={
                        'abstract': f'This research investigates {data["title"].lower()}. Our methodology includes comprehensive data analysis and surveys.',
                        'description': f'A detailed study on {data["title"].lower()} with significant implications for education policy.',
                        'principal_investigator': test_users[i],
                        'status': data['status'],
                        'ethics_approved': True,
                    }
                )
                if created:
                    self.stdout.write(f'  Created research: {data["title"]}')
        except Exception as e:
            self.stdout.write(f'  Skipping research: {e}')
        
        self.stdout.write(self.style.SUCCESS('✅ Dummy data created successfully!'))
