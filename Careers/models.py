"""
Careers & Gigs Models
Provides models for gigs, career opportunities, and user preferences for recommendation
"""
from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
import uuid


class Gig(models.Model):
    """User-created gigs/freelance work"""
    PAY_TIMING_CHOICES = [
        ('before', 'Payment Before Work'),
        ('after', 'Payment After Completion'),
        ('milestone', 'Milestone-based Payment'),
        ('negotiable', 'Negotiable'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    INDUSTRY_CHOICES = [
        ('tech', 'Technology'),
        ('design', 'Design & Creative'),
        ('writing', 'Writing & Content'),
        ('marketing', 'Marketing'),
        ('finance', 'Finance & Accounting'),
        ('legal', 'Legal'),
        ('admin', 'Administrative'),
        ('education', 'Education & Training'),
        ('engineering', 'Engineering'),
        ('healthcare', 'Healthcare'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_gigs')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField(help_text="Skills and qualifications needed")
    
    pay_amount = models.DecimalField(max_digits=12, decimal_places=2)
    pay_timing = models.CharField(max_length=20, choices=PAY_TIMING_CHOICES)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    
    deadline = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, help_text="Remote or specific location")
    is_remote = models.BooleanField(default=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_gigs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tracking metrics
    views_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} - {self.pay_amount}"

    class Meta:
        ordering = ['-created_at']


class GigApplication(models.Model):
    """Applications for gigs"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gig = models.ForeignKey(Gig, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gig_applications')
    
    cover_letter = models.TextField()
    proposed_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['gig', 'applicant']


class CareerOpportunity(models.Model):
    """Company career/job postings"""
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
    ]

    EXPERIENCE_LEVEL_CHOICES = [
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior Level'),
        ('lead', 'Lead/Manager'),
        ('executive', 'Executive'),
    ]

    INDUSTRY_CHOICES = Gig.INDUSTRY_CHOICES  # Reuse from Gig

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to organization (using UUID for flexibility)
    organization_id = models.UUIDField(null=True, blank=True)
    institution_id = models.UUIDField(null=True, blank=True)
    company_name = models.CharField(max_length=255, help_text="Fallback if no org link")
    
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posted_careers')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField(blank=True)
    
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=10, default='USD')
    
    location = models.CharField(max_length=255)
    is_remote = models.BooleanField(default=False)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL_CHOICES)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    
    application_deadline = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Tracking metrics
    views_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.title} at {self.company_name}"

    class Meta:
        verbose_name_plural = "Career Opportunities"
        ordering = ['-created_at']

    @property
    def salary_range(self):
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,.0f}+"
        return "Negotiable"


class CareerApplication(models.Model):
    """Applications for career opportunities"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('reviewing', 'Under Review'),
        ('interview', 'Interview Scheduled'),
        ('offered', 'Offer Extended'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    career = models.ForeignKey(CareerOpportunity, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_applications')
    
    cover_letter = models.TextField()
    resume = models.FileField(upload_to='career_resumes/', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, help_text="Internal notes for reviewers")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['career', 'applicant']


class UserCareerPreference(models.Model):
    """User preferences for career/gig recommendations"""
    INTEREST_TYPE_CHOICES = [
        ('gig', 'Looking for Gigs'),
        ('employment', 'Looking for Employment'),
        ('recruit', 'Looking to Hire'),
        ('both', 'Both Gigs and Employment'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='career_preference')
    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPE_CHOICES)
    
    # Use JSONField as fallback for SQLite (ArrayField requires PostgreSQL)
    industries = models.JSONField(default=list, help_text="List of preferred industries")
    skills = models.JSONField(default=list, help_text="User's skills")
    
    preferred_pay_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preferred_pay_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preferred_job_types = models.JSONField(default=list, help_text="Full-time, part-time, etc.")
    
    is_remote_only = models.BooleanField(default=False)
    preferred_locations = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user}'s Career Preferences"
