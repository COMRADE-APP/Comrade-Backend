import random
from datetime import datetime, timedelta, time as dtime
from django.core.management.base import BaseCommand
from django.utils import timezone
from Authentication.models import CustomUser, Profile

from Careers.models import CareerOpportunity, Gig
from Articles.models import Article
from Research.models import ResearchProject
from Resources.models import Resource
from Announcements.models import Task
from Events.models import Event

LOREM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris."
IMG = "https://loremflickr.com/800/600/{kw}?lock={lock}"


class Command(BaseCommand):
    help = 'Mass populate Careers, Gigs, Articles, Research, Resources, Tasks, Events'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting mass content population...'))
        user = CustomUser.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(self.style.ERROR('No active user. Create one first.'))
            return
        profile = Profile.objects.filter(user=user).first()
        N = 18

        self._careers(user, N)
        self._gigs(user, N)
        self._articles(user, N)
        self._research(user, N)
        self._resources(profile, N)
        self._tasks(user, N)
        self._events(user, N)

        self.stdout.write(self.style.SUCCESS(f'Done! Created {N*7} entries total.'))

    # ------ helpers ------
    def _img(self, kw):
        return IMG.format(kw=kw, lock=random.randint(1000, 9999))

    # ------ Careers ------
    def _careers(self, user, n):
        kws = ['office', 'team', 'corporate', 'business', 'interview', 'workplace']
        industries = ['tech', 'design', 'finance', 'education', 'healthcare', 'engineering', 'other']
        job_types = ['full_time', 'part_time', 'contract', 'internship', 'freelance']
        exp = ['entry', 'mid', 'senior', 'lead', 'executive']
        for i in range(n):
            CareerOpportunity.objects.create(
                posted_by=user,
                title=f"Career Opportunity #{i+1}",
                company_name=f"Company {chr(65 + (i % 26))}",
                location="Kigali, Rwanda",
                is_remote=random.choice([True, False]),
                job_type=random.choice(job_types),
                experience_level=random.choice(exp),
                industry=random.choice(industries),
                description=LOREM,
                requirements="1. Skill A\n2. Skill B\n3. Skill C",
                responsibilities="1. Task A\n2. Task B",
                salary_min=1000,
                salary_max=5000,
                application_deadline=timezone.now() + timedelta(days=30),
                image_url=self._img(random.choice(kws)),
            )
        self.stdout.write(self.style.SUCCESS(f'  [OK] {n} Career Opportunities'))

    # ------ Gigs ------
    def _gigs(self, user, n):
        kws = ['freelance', 'laptop', 'coffee', 'workspace', 'design', 'coding']
        industries = ['tech', 'design', 'writing', 'marketing', 'finance', 'education', 'engineering', 'other']
        pay_timings = ['before', 'after', 'milestone', 'negotiable']
        for i in range(n):
            Gig.objects.create(
                creator=user,
                title=f"Freelance Gig #{i+1}",
                description=LOREM,
                requirements="1. Strong communication\n2. Relevant experience\n3. Portfolio",
                industry=random.choice(industries),
                location="Remote / Hybrid",
                is_remote=random.choice([True, False]),
                pay_amount=random.randint(50, 1000),
                pay_timing=random.choice(pay_timings),
                deadline=timezone.now() + timedelta(days=14),
                image_url=self._img(random.choice(kws)),
            )
        self.stdout.write(self.style.SUCCESS(f'  [OK] {n} Gigs'))

    # ------ Articles ------
    def _articles(self, user, n):
        kws = ['news', 'magazine', 'reading', 'blog', 'journalism', 'article']
        categories = ['Technology', 'Science', 'Lifestyle', 'Politics', 'Entertainment', 'Education']
        for i in range(n):
            Article.objects.create(
                author=user,
                title=f"Insightful Article #{i+1}",
                content=LOREM * 3,
                status='published',
                published_at=timezone.now(),
                image_url=self._img(random.choice(kws)),
                category=random.choice(categories),
            )
        self.stdout.write(self.style.SUCCESS(f'  [OK] {n} Articles'))

    # ------ Research ------
    def _research(self, user, n):
        kws = ['laboratory', 'science', 'microscope', 'research', 'data', 'university']
        statuses = ['draft', 'seeking_participants', 'active', 'completed', 'published']
        for i in range(n):
            ResearchProject.objects.create(
                principal_investigator=user,
                title=f"Research Project #{i+1}",
                abstract=f"Abstract for research project #{i+1}. " + LOREM[:120],
                description=LOREM,
                status=random.choice(statuses),
                image_url=self._img(random.choice(kws)),
            )
        self.stdout.write(self.style.SUCCESS(f'  [OK] {n} Research Projects'))

    # ------ Resources ------
    def _resources(self, profile, n):
        kws = ['document', 'file', 'books', 'library', 'archive', 'learning']
        file_types = ['media_link', 'text']
        for i in range(n):
            ft = random.choice(file_types)
            Resource.objects.create(
                title=f"Resource #{i+1}",
                desc=f"Helpful resource #{i+1}. " + LOREM[:100],
                file_type=ft,
                res_link="https://example.com/resource" if ft == 'media_link' else None,
                res_text=LOREM if ft == 'text' else None,
                created_by=profile,
                image_url=self._img(random.choice(kws)),
                status='published',
                visibility='public',
            )
        self.stdout.write(self.style.SUCCESS(f'  [OK] {n} Resources'))

    # ------ Tasks ------
    def _tasks(self, user, n):
        kws = ['checklist', 'task', 'clipboard', 'planning', 'todo', 'agenda']
        for i in range(n):
            Task.objects.create(
                user=user,
                heading=f"Task #{i+1}",
                description=LOREM,
                is_activity=random.choice([True, False]),
                image_url=self._img(random.choice(kws)),
            )
        self.stdout.write(self.style.SUCCESS(f'  [OK] {n} Tasks'))

    # ------ Events ------
    def _events(self, user, n):
        kws = ['concert', 'conference', 'meeting', 'party', 'event', 'crowd']
        for i in range(n):
            Event.objects.create(
                created_by=user,
                name=f"Community Event #{i+1}",
                description=LOREM,
                location="City Convention Center",
                start_time=dtime(9, 0),
                end_time=dtime(17, 0),
                duration=timedelta(hours=8),
                capacity=random.randint(50, 500),
                event_location=random.choice(['online', 'physical', 'hybrid']),
                event_url="https://zoom.us/j/1234567890",
                image_url=self._img(random.choice(kws)),
            )
        self.stdout.write(self.style.SUCCESS(f'  [OK] {n} Events'))
