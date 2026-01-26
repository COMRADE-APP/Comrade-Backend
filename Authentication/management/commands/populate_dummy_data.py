import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models.signals import post_save
from Authentication.models import CustomUser, Profile, Student
from Institution.models import Institution, InstBranch, Faculty, InstDepartment, Programme
from Organisation.models import Organisation, OrgBranch
from Events.models import Event
from Announcements.models import Task, Announcements, Question, Choice, TASK_TYPE, VIS_TYPES, ANN_STATUS, TASK_STATE
from Specialization.models import Stack, Specialization
from Rooms.models import Room
from Payment.models import Product, PaymentProfile
from Resources.models import Resource
from Rooms import auto_creation  # Import to disconnect signals

class Command(BaseCommand):
    help = 'Populates the database with dummy data for analysis.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting data population...'))

        # Disconnect broken signals to avoid AttributeError: 'Institution' object has no attribute 'creator'
        # The user requested not to change the code, so we bypass the bug here.
        post_save.disconnect(auto_creation.create_institution_default_rooms, sender=Institution)
        post_save.disconnect(auto_creation.create_organization_default_rooms, sender=Organisation)
        self.stdout.write('Disconnected broken signal handlers in Rooms/auto_creation.py')

        try:
            with transaction.atomic():
                # 1. Users and Profiles
                self.stdout.write('Creating/Getting creator user...')
                
                # Creator User (jmbngugimbugua@gmail.com)
                creator_email = 'jmbngugimbugua@gmail.com'
                creator, created = CustomUser.objects.get_or_create(
                    email=creator_email,
                    defaults={
                        'first_name': 'Jm',
                        'last_name': 'Bugua',
                        'user_type': 'admin',
                        'is_staff': True,
                        'is_superuser': True,
                        'is_active': True
                    }
                )
                if created:
                    creator.set_password('password123')
                    creator.save()
                    Profile.objects.get_or_create(user=creator, defaults={'bio': 'Creator Bio'})
                else:
                    # Ensure existing user has profile
                    Profile.objects.get_or_create(user=creator, defaults={'bio': 'Creator Bio'})
                
                creator_profile = Profile.objects.get(user=creator)
                
                # Other Users
                self.stdout.write('Creating other users...')
                users = []
                for i in range(5):
                    email = f'user{i}@example.com'
                    user, created = CustomUser.objects.get_or_create(
                        email=email,
                        defaults={
                            'first_name': f'User{i}',
                            'last_name': 'Test',
                            'user_type': 'student',
                            'is_active': True,
                        }
                    )
                    if created:
                        user.set_password('password123')
                        user.save()
                        Profile.objects.get_or_create(user=user, defaults={'bio': f'Bio for User{i}'})
                    users.append(user)

                # 2. Payment Profiles
                self.stdout.write('Creating payment profiles...')
                for user in users:
                    user_profile = Profile.objects.get(user=user)
                    PaymentProfile.objects.get_or_create(user=user_profile)
                PaymentProfile.objects.get_or_create(user=creator_profile)

                # 3. Institutions
                self.stdout.write('Creating institutions...')
                inst_types = ['university', 'college']
                institutions = []
                for i in range(3):
                    inst, _ = Institution.objects.get_or_create(
                        name=f'Dummy Institution {i}',
                        defaults={
                            'institution_type': random.choice(inst_types),
                            'email': f'info@inst{i}.com',
                            'country': 'Country',
                            'city': 'City',
                            'address': 'Address Line',
                            'status': 'verified',
                            'created_by': creator
                        }
                    )
                    institutions.append(inst)
                    
                    # Branches
                    branch, _ = InstBranch.objects.get_or_create(
                        institution=inst,
                        branch_code=f'BR{i}',
                        defaults={
                            'name': 'Main Campus',
                            'city': 'City',
                            'country': 'Country',
                            'address': 'Address'
                        }
                    )

                    # Faculty -> Dept -> Program
                    faculty, _ = Faculty.objects.get_or_create(
                        institution=inst,
                        faculty_code=f'FAC{i}',
                        defaults={'name': 'Faculty of Science', 'inst_branch': branch}
                    )
                    dept, _ = InstDepartment.objects.get_or_create(
                        faculty=faculty,
                        dep_code=f'DEP{i}',
                        defaults={'name': 'Computer Science Department'}
                    )
                    Programme.objects.get_or_create(
                        department=dept,
                        programme_code=f'PROG{i}',
                        defaults={'name': 'Computer Science'}
                    )


                # 4. Organisations
                self.stdout.write('Creating organisations...')
                organisations = []
                for i in range(3):
                    org, _ = Organisation.objects.get_or_create(
                        name=f'Dummy Corp {i}',
                        defaults={
                            'org_type': 'business',
                            'origin': 'Origin',
                            'abbreviation': f'DC{i}',
                            'address': 'Address',
                            'postal_code': '000',
                            'town': 'Town',
                            'city': 'City',
                            'industry': 'Tech'
                        }
                    )
                    organisations.append(org)
                    
                    OrgBranch.objects.get_or_create(
                        organisation=org,
                        branch_code=f'OBR{i}',
                        defaults={
                            'name': 'HQ',
                            'origin': 'Origin',
                            'region': 'Region',
                            'abbreviation': 'HQ',
                            'address': 'Address',
                            'postal_code': '000',
                            'town': 'Town',
                            'city': 'City'
                        }
                    )

                # 5. Resources
                self.stdout.write('Creating resources...')
                for i in range(5):
                    Resource.objects.get_or_create(
                        title=f'Resource {i}',
                        defaults={
                            'desc': 'Description here',
                            'file_type': 'text',
                            'res_text': 'This is dummy content for the resource.',
                            'visibility': 'public',
                            'created_by': creator_profile
                        }
                    )

                # 6. Events
                self.stdout.write('Creating events...')
                for i in range(5):
                    Event.objects.get_or_create(
                        name=f'Event {i}',
                        defaults={
                            'description': 'Event description',
                            'capacity': 100,
                            'duration': timedelta(hours=2),
                            'start_time': datetime.now().time(),
                            'end_time': (datetime.now() + timedelta(hours=2)).time(),
                            'event_date': datetime.now() + timedelta(days=i),
                            'location': 'Virtual',
                            'status': 'active',
                            'created_by': creator
                        }
                    )

                # 7. Products (Payment)
                self.stdout.write('Creating products...')
                for i in range(5):
                    Product.objects.get_or_create(
                        name=f'Product {i}',
                        defaults={
                            'description': 'Product description',
                            'price': 10.00 + i,
                            'product_type': 'digital',
                        }
                    )

                # 8. Tasks and Announcements
                self.stdout.write('Creating tasks and announcements...')
                for i in range(5):
                    Announcements.objects.get_or_create(
                        user=creator,
                        heading=f'Announcement {i}',
                        defaults={
                            'content': 'Announcement content',
                            'visibility': 'public',
                            'send_status': 'sent'
                        }
                    )
                    
                    task, _ = Task.objects.get_or_create(
                        user=creator,
                        heading=f'Task {i}',
                        defaults={
                            'description': 'Task description',
                            'visibility': 'public',
                            'status': 'sent',
                            'state': 'active',
                            'due_date': datetime.now() + timedelta(days=7)
                        }
                    )
                    
                    # Questions for Task
                    q, _ = Question.objects.get_or_create(
                        task=task,
                        heading=f'Question for Task {i}',
                        defaults={
                            'description': 'Solve this.',
                            'question_type': 'radio',
                            'position': 1
                        }
                    )
                    Choice.objects.get_or_create(question=q, content='Option A', defaults={'is_correct': True})
                    Choice.objects.get_or_create(question=q, content='Option B')

                # 9. Stacks and Specializations
                self.stdout.write('Creating stacks and specializations...')
                stacks = []
                for i, name in enumerate(['Frontend', 'Backend', 'DevOps']):
                    stack, _ = Stack.objects.get_or_create(name=name, defaults={'description': f'{name} Stack'})
                    stacks.append(stack)
                
                spec, _ = Specialization.objects.get_or_create(
                    name='Full Stack Developer',
                    defaults={'description': 'Master both frontend and backend.'}
                )
                spec.stacks.add(*stacks)

                # 10. Rooms
                self.stdout.write('Creating rooms...')
                import uuid
                def get_room_code():
                    return uuid.uuid4().hex[:10].upper()

                for i in range(3):
                    Room.objects.get_or_create(
                        name=f'Room {i}',
                        defaults={
                            'description': 'Discussion room',
                            'created_by': creator,
                            'operation_state': 'active',
                            'room_code': get_room_code() # Explicitly provide unique code
                        }
                    )

            self.stdout.write(self.style.SUCCESS('Successfully populated dummy data.'))
        finally:
             # Reconnect signals if needed (though script ends here)
             pass
