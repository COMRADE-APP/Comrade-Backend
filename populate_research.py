
import os
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Authentication.models import CustomUser
from Research.models import (
    ResearchProject, ParticipantRequirements, ParticipantPosition, 
    ResearchMilestone
)
from Institution.models import Institution
from Organisation.models import Organisation

def populate():
    print("Populating Research Data...")

    # Get a user (create if not exists)
    user = CustomUser.objects.first()
    if not user:
        print("No users found. Please create a user first.")
        return

    print(f"Using user: {user.email}")

    # Create Research Project 1: Published
    project1, created = ResearchProject.objects.get_or_create(
        title="Validating AI in Remote Health Monitoring",
        defaults={
            'abstract': "This study aims to validate the effectiveness of AI-driven remote health monitoring systems in improving patient outcomes for chronic diseases.",
            'description': "Full description of the project goes here. We are testing a new algorithm for detecting anomalies in vital signs...",
            'principal_investigator': user,
            'status': 'published',
            'is_published': True,
            'start_date': datetime.now().date() - timedelta(days=365),
            'end_date': datetime.now().date() - timedelta(days=30),
            'views': 1205
        }
    )
    if created:
        print(f"Created Project: {project1.title}")

    # Create Research Project 2: Seeking Participants
    project2, created = ResearchProject.objects.get_or_create(
        title="Urban Sustainability and Smart City Infrastructure",
        defaults={
            'abstract': "Investigating the impact of smart city technologies on urban sustainability and citizen quality of life.",
            'description': "We are looking for participants to test our new mobile app for reporting urban issues...",
            'principal_investigator': user,
            'status': 'seeking_participants',
            'start_date': datetime.now().date(),
            'end_date': datetime.now().date() + timedelta(days=180),
            'views': 450
        }
    )
    if created:
        print(f"Created Project: {project2.title}")
        
        # Add Requirements
        ParticipantRequirements.objects.create(
            research=project2,
            min_age=18,
            max_age=65,
            gender='any',
            min_education_level='high_school',
            required_skills=['Smartphone usage', 'English proficiency'],
            location_requirements="Must live in a major city"
        )
        
        # Add Positions
        ParticipantPosition.objects.create(
            research=project2,
            title="Beta Tester",
            description="Test the mobile app and report bugs over a 2-week period.",
            compensation_type='monetary',
            compensation_amount=50.00,
            slots_available=20,
            application_deadline=datetime.now() + timedelta(days=30),
            estimated_duration_hours=10
        )
        
        ParticipantPosition.objects.create(
            research=project2,
            title="Interview Participant",
            description="Participate in a 1-hour interview about your experience with smart city tech.",
            compensation_type='monetary',
            compensation_amount=30.00,
            slots_available=10,
            application_deadline=datetime.now() + timedelta(days=15),
            estimated_duration_hours=1
        )

        # Add Milestones
        ResearchMilestone.objects.create(
            research=project2,
            title="Participant Recruitment",
            description="Recruit 30 participants for the study.",
            due_date=datetime.now().date() + timedelta(days=30),
            sequence=1
        )
        ResearchMilestone.objects.create(
            research=project2,
            title="Data Collection Phase 1",
            description="Collect initial data from beta testers.",
            due_date=datetime.now().date() + timedelta(days=60),
            sequence=2
        )

    # Create Research Project 3: Draft
    project3, created = ResearchProject.objects.get_or_create(
        title="The Future of Work: Remote vs Office",
        defaults={
            'abstract': "Analyzing productivity and employee satisfaction in hybrid work models.",
            'description': "Drafting the proposal...",
            'principal_investigator': user,
            'status': 'draft',
            'start_date': datetime.now().date() + timedelta(days=60),
        }
    )
    if created:
        print(f"Created Project: {project3.title}")

    print("Done!")

if __name__ == '__main__':
    populate()
