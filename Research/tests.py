from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid
from unittest.mock import MagicMock

CustomUser = get_user_model()


class ResearchProjectModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcher@example.com',
            password='pass123',
            first_name='Research',
            last_name='User'
        )

    def test_create_research_project(self):
        from Research.models import ResearchProject
        project = ResearchProject.objects.create(
            title='Test Research Project',
            abstract='This is a test abstract.',
            description='This is a test description.',
            principal_investigator=self.user,
            status='draft'
        )
        self.assertEqual(project.title, 'Test Research Project')
        self.assertEqual(project.status, 'draft')
        self.assertEqual(project.principal_investigator, self.user)
        self.assertFalse(project.is_published)
        self.assertEqual(project.views, 0)

    def test_research_project_str(self):
        from Research.models import ResearchProject
        project = ResearchProject.objects.create(
            title='Test Project',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )
        self.assertEqual(str(project), 'Test Project')

    def test_research_project_status_choices(self):
        from Research.models import ResearchProject
        statuses = ['draft', 'seeking_participants', 'in_progress', 'data_collection', 
                    'analysis', 'peer_review', 'published', 'completed', 'archived']
        for status in statuses:
            project = ResearchProject.objects.create(
                title=f'Test {status}',
                abstract='Abstract',
                description='Description',
                principal_investigator=self.user,
                status=status
            )
            self.assertEqual(project.status, status)

    def test_research_project_ordering(self):
        from Research.models import ResearchProject
        project1 = ResearchProject.objects.create(
            title='First Project',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )
        project2 = ResearchProject.objects.create(
            title='Second Project',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )
        projects = list(ResearchProject.objects.all()[:2])
        self.assertEqual(projects[0], project2)
        self.assertEqual(projects[1], project1)

    def test_research_project_published_status(self):
        from Research.models import ResearchProject
        project = ResearchProject.objects.create(
            title='Published Project',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user,
            status='published',
            is_published=True
        )
        self.assertTrue(project.is_published)
        self.assertEqual(project.status, 'published')


class ParticipantRequirementsModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcher2@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Test Research',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )

    def test_create_participant_requirements(self):
        from Research.models import ParticipantRequirements
        reqs = ParticipantRequirements.objects.create(
            research=self.research,
            min_age=18,
            max_age=65,
            target_participant_count=50,
            min_participant_count=30,
            max_participant_count=100
        )
        self.assertEqual(reqs.research, self.research)
        self.assertEqual(reqs.min_age, 18)
        self.assertEqual(reqs.max_age, 65)
        self.assertEqual(reqs.target_participant_count, 50)

    def test_participant_requirements_str(self):
        from Research.models import ParticipantRequirements
        reqs = ParticipantRequirements.objects.create(
            research=self.research,
            target_participant_count=50
        )
        self.assertEqual(str(reqs), f'Requirements for {self.research.title}')

    def test_participant_requirements_education_choices(self):
        from Research.models import ParticipantRequirements
        education_levels = ['high_school', 'associate', 'bachelor', 'master', 'doctoral', 'any']
        for level in education_levels:
            reqs = ParticipantRequirements.objects.create(
                research=self.research,
                min_education_level=level
            )
            self.assertEqual(reqs.min_education_level, level)


class ParticipantPositionModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcher3@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Test Research Position',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )

    def test_create_participant_position(self):
        from Research.models import ParticipantPosition
        from django.utils import timezone
        deadline = timezone.now() + timedelta(days=30)
        position = ParticipantPosition.objects.create(
            research=self.research,
            title='Research Assistant',
            description='Help with data collection',
            application_deadline=deadline,
            slots_available=10,
            slots_filled=0
        )
        self.assertEqual(position.title, 'Research Assistant')
        self.assertEqual(position.slots_available, 10)
        self.assertTrue(position.is_active)

    def test_participant_position_str(self):
        from Research.models import ParticipantPosition
        from django.utils import timezone
        deadline = timezone.now() + timedelta(days=30)
        position = ParticipantPosition.objects.create(
            research=self.research,
            title='Test Position',
            description='Description',
            application_deadline=deadline
        )
        expected = f"Test Position - {self.research.title}"
        self.assertEqual(str(position), expected)

    def test_participant_position_is_full(self):
        from Research.models import ParticipantPosition
        from django.utils import timezone
        deadline = timezone.now() + timedelta(days=30)
        position = ParticipantPosition.objects.create(
            research=self.research,
            title='Full Position',
            description='Description',
            application_deadline=deadline,
            slots_available=5,
            slots_filled=5
        )
        self.assertTrue(position.is_full)

    def test_participant_position_not_full(self):
        from Research.models import ParticipantPosition
        from django.utils import timezone
        deadline = timezone.now() + timedelta(days=30)
        position = ParticipantPosition.objects.create(
            research=self.research,
            title='Available Position',
            description='Description',
            application_deadline=deadline,
            slots_available=10,
            slots_filled=3
        )
        self.assertFalse(position.is_full)


class ResearchParticipantModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='participant@example.com',
            password='pass123'
        )
        self.researcher = CustomUser.objects.create_user(
            email='researcher4@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject, ParticipantPosition
        from django.utils import timezone
        
        self.research = ResearchProject.objects.create(
            title='Participant Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.researcher
        )
        deadline = timezone.now() + timedelta(days=30)
        self.position = ParticipantPosition.objects.create(
            research=self.research,
            title='Study Position',
            description='Description',
            application_deadline=deadline
        )

    def test_create_research_participant(self):
        from Research.models import ResearchParticipant
        participant = ResearchParticipant.objects.create(
            research=self.research,
            user=self.user,
            status='invited'
        )
        self.assertEqual(participant.research, self.research)
        self.assertEqual(participant.user, self.user)
        self.assertEqual(participant.status, 'invited')
        self.assertFalse(participant.consent_given)

    def test_research_participant_str(self):
        from Research.models import ResearchParticipant
        participant = ResearchParticipant.objects.create(
            research=self.research,
            user=self.user
        )
        expected = f"{self.user.email} - {self.research.title}"
        self.assertEqual(str(participant), expected)

    def test_research_participant_status_choices(self):
        from Research.models import ResearchParticipant
        statuses = ['invited', 'accepted', 'active', 'completed', 'withdrawn', 'disqualified']
        for status in statuses:
            participant = ResearchParticipant.objects.create(
                research=self.research,
                user=self.user,
                status=status
            )
            self.assertEqual(participant.status, status)


class ParticipantMatchingModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='matchuser@example.com',
            password='pass123'
        )
        self.researcher = CustomUser.objects.create_user(
            email='researcher5@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Matching Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.researcher
        )

    def test_create_participant_matching(self):
        from Research.models import ParticipantMatching
        match = ParticipantMatching.objects.create(
            participant=self.user,
            research=self.research,
            match_score=85.5,
            age_match=90.0,
            education_match=80.0,
            experience_match=85.0,
            availability_match=95.0,
            location_match=80.0
        )
        self.assertEqual(match.participant, self.user)
        self.assertEqual(match.research, self.research)
        self.assertEqual(match.match_score, 85.5)

    def test_participant_matching_str(self):
        from Research.models import ParticipantMatching
        match = ParticipantMatching.objects.create(
            participant=self.user,
            research=self.research,
            match_score=75.0
        )
        expected = f"{self.user.email} - {self.research.title} (Score: 75.0)"
        self.assertEqual(str(match), expected)


class ResearchGuidelinesModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcher6@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Guidelines Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )

    def test_create_research_guidelines(self):
        from Research.models import ResearchGuidelines
        guidelines = ResearchGuidelines.objects.create(
            research=self.research,
            participant_guidelines='Follow all instructions.',
            data_collection_guidelines='Collect data accurately.',
            privacy_policy='Protect participant data.',
            withdrawal_policy='Participants can withdraw anytime.',
            communication_guidelines='Communicate professionally.',
            data_usage_policy='Use data only for research.'
        )
        self.assertEqual(guidelines.research, self.research)
        self.assertEqual(guidelines.participant_guidelines, 'Follow all instructions.')

    def test_research_guidelines_str(self):
        from Research.models import ResearchGuidelines
        guidelines = ResearchGuidelines.objects.create(
            research=self.research,
            participant_guidelines='Test'
        )
        expected = f"Guidelines for {self.research.title}"
        self.assertEqual(str(guidelines), expected)


class PeerReviewModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='reviewer@example.com',
            password='pass123'
        )
        self.researcher = CustomUser.objects.create_user(
            email='researcher7@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Review Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.researcher
        )

    def test_create_peer_review(self):
        from Research.models import PeerReview
        review = PeerReview.objects.create(
            research=self.research,
            reviewer=self.user,
            status='pending',
            overall_rating=4,
            recommendation='accept'
        )
        self.assertEqual(review.research, self.research)
        self.assertEqual(review.reviewer, self.user)
        self.assertEqual(review.status, 'pending')
        self.assertEqual(review.overall_rating, 4)

    def test_peer_review_str(self):
        from Research.models import PeerReview
        review = PeerReview.objects.create(
            research=self.research,
            reviewer=self.user
        )
        expected = f"Review by {self.user.email} for {self.research.title}"
        self.assertEqual(str(review), expected)


class ResearchPublicationModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcher8@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Publication Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )

    def test_create_research_publication(self):
        from Research.models import ResearchPublication
        pub = ResearchPublication.objects.create(
            research=self.research,
            title='Test Publication',
            abstract='Published abstract',
            keywords=['research', 'testing'],
            categories=['science'],
            access_level='restricted'
        )
        self.assertEqual(pub.title, 'Test Publication')
        self.assertEqual(pub.access_level, 'restricted')
        self.assertEqual(pub.views, 0)
        self.assertEqual(pub.downloads, 0)

    def test_research_publication_str(self):
        from Research.models import ResearchPublication
        pub = ResearchPublication.objects.create(
            research=self.research,
            title='My Publication'
        )
        self.assertEqual(str(pub), 'My Publication')


class ResearchMilestoneModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcher9@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Milestone Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )

    def test_create_research_milestone(self):
        from Research.models import ResearchMilestone
        from datetime import date
        milestone = ResearchMilestone.objects.create(
            research=self.research,
            title='Data Collection',
            description='Collect survey data',
            due_date=date.today(),
            sequence=1
        )
        self.assertEqual(milestone.title, 'Data Collection')
        self.assertFalse(milestone.completed)
        self.assertEqual(milestone.sequence, 1)

    def test_research_milestone_str(self):
        from Research.models import ResearchMilestone
        from datetime import date
        milestone = ResearchMilestone.objects.create(
            research=self.research,
            title='Test Milestone',
            due_date=date.today()
        )
        expected = f"{self.research.title} - Test Milestone"
        self.assertEqual(str(milestone), expected)


class ParticipantApplicationModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='applicant@example.com',
            password='pass123'
        )
        self.researcher = CustomUser.objects.create_user(
            email='researcher10@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject, ParticipantPosition
        from django.utils import timezone
        
        self.research = ResearchProject.objects.create(
            title='Application Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.researcher
        )
        deadline = timezone.now() + timedelta(days=30)
        self.position = ParticipantPosition.objects.create(
            research=self.research,
            title='Open Position',
            description='Description',
            application_deadline=deadline
        )

    def test_create_participant_application(self):
        from Research.models import ParticipantApplication
        app = ParticipantApplication.objects.create(
            position=self.position,
            applicant=self.user,
            cover_letter='I want to participate.',
            status='pending'
        )
        self.assertEqual(app.position, self.position)
        self.assertEqual(app.applicant, self.user)
        self.assertEqual(app.status, 'pending')

    def test_participant_application_str(self):
        from Research.models import ParticipantApplication
        app = ParticipantApplication.objects.create(
            position=self.position,
            applicant=self.user,
            status='pending'
        )
        expected = f"{self.user.email} -> {self.position.title} (pending)"
        self.assertEqual(str(app), expected)


class ResearchAnalyticsModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='analyticsuser@example.com',
            password='pass123'
        )
        self.researcher = CustomUser.objects.create_user(
            email='researcher11@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Analytics Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.researcher
        )

    def test_create_research_analytics(self):
        from Research.models import ResearchAnalytics
        analytics = ResearchAnalytics.objects.create(
            research=self.research,
            user=self.user,
            action='view'
        )
        self.assertEqual(analytics.research, self.research)
        self.assertEqual(analytics.action, 'view')

    def test_research_analytics_str(self):
        from Research.models import ResearchAnalytics
        analytics = ResearchAnalytics.objects.create(
            research=self.research,
            action='view'
        )
        expected = f"view on {self.research.title}"
        self.assertEqual(str(analytics), expected)


class RecruitmentPostModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcher12@example.com',
            password='pass123'
        )
        from Research.models import ResearchProject
        self.research = ResearchProject.objects.create(
            title='Recruitment Study',
            abstract='Abstract',
            description='Description',
            principal_investigator=self.user
        )

    def test_create_recruitment_post(self):
        from Research.models import RecruitmentPost
        post = RecruitmentPost.objects.create(
            research=self.research,
            title='Seeking Participants',
            description='We need 50 participants.',
            post_type='participants'
        )
        self.assertEqual(post.title, 'Seeking Participants')
        self.assertEqual(post.post_type, 'participants')
        self.assertTrue(post.is_active)

    def test_recruitment_post_str(self):
        from Research.models import RecruitmentPost
        post = RecruitmentPost.objects.create(
            research=self.research,
            title='Recruitment Post'
        )
        expected = f"Recruitment Post for {self.research.title}"
        self.assertEqual(str(post), expected)


class ResearcherApplicationModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='researcherapplicant@example.com',
            password='pass123'
        )

    def test_create_researcher_application(self):
        from Research.models import ResearcherApplication
        app = ResearcherApplication.objects.create(
            user=self.user,
            status='pending',
            qualifications='PhD in Computer Science'
        )
        self.assertEqual(app.user, self.user)
        self.assertEqual(app.status, 'pending')

    def test_researcher_application_str(self):
        from Research.models import ResearcherApplication
        app = ResearcherApplication.objects.create(
            user=self.user,
            status='pending'
        )
        expected = f"{self.user.email} - pending"
        self.assertEqual(str(app), expected)