from django.db import models
from Authentication.models import Profile, CustomUser
from datetime import datetime
import uuid

# Create your models here.

RESEARCH_STATUS = (
    ('draft', 'Draft'),
    ('seeking_participants', 'Seeking Participants'),
    ('in_progress', 'In Progress'),
    ('data_collection', 'Data Collection'),
    ('analysis', 'Analysis'),
    ('peer_review', 'Peer Review'),
    ('published', 'Published'),
    ('completed', 'Completed'),
    ('archived', 'Archived'),
)

PARTICIPANT_STATUS = (
    ('invited', 'Invited'),
    ('accepted', 'Accepted'),
    ('active', 'Active'),
    ('completed', 'Completed'),
    ('withdrawn', 'Withdrawn'),
    ('disqualified', 'Disqualified'),
)

REVIEW_STATUS = (
    ('pending', 'Pending'),
    ('in_review', 'In Review'),
    ('approved', 'Approved'),
    ('revision_requested', 'Revision Requested'),
    ('rejected', 'Rejected'),
)

COMPENSATION_TYPE = (
    ('none', 'No Compensation'),
    ('monetary', 'Monetary'),
    ('course_credit', 'Course Credit'),
    ('certificate', 'Certificate'),
    ('other', 'Other'),
)

class ResearchProject(models.Model):
    """Main research project model for conducting research from planning to publication"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    description = models.TextField()
    
    # Researchers
    principal_investigator = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='led_research')
    co_investigators = models.ManyToManyField(CustomUser, related_name='co_research', blank=True)
    
    # Status and timeline
    status = models.CharField(max_length=50, choices=RESEARCH_STATUS, default='draft')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Ethics and compliance
    ethics_approved = models.BooleanField(default=False)
    ethics_approval_number = models.CharField(max_length=100, blank=True)
    consent_form = models.FileField(upload_to='research/consent_forms/', null=True, blank=True)
    irb_approval_document = models.FileField(upload_to='research/irb/', null=True, blank=True)
    
    # Publication
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    doi = models.CharField(max_length=200, blank=True)
    
    # Metrics
    views = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['principal_investigator']),
            models.Index(fields=['is_published']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class ParticipantRequirements(models.Model):
    """Requirements that participants must fulfill"""
    research = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='requirements')
    
    # Demographics
    min_age = models.IntegerField(null=True, blank=True)
    max_age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=50, blank=True, choices=(
        ('any', 'Any'),
        ('male', 'Male'),
        ('female', 'Female'),
        ('non_binary', 'Non-Binary'),
        ('other', 'Other'),
    ))
    
    # Academic criteria
    min_education_level = models.CharField(max_length=100, blank=True, choices=(
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor Degree'),
        ('master', 'Master Degree'),
        ('doctoral', 'Doctoral Degree'),
        ('any', 'Any'),
    ))
    required_skills = models.JSONField(default=list, blank=True)
    required_experience = models.TextField(blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    
    # Location and language
    location_requirements = models.TextField(blank=True)
    language_requirements = models.JSONField(default=list, blank=True)
    timezone_requirements = models.CharField(max_length=100, blank=True)
    
    # Technical requirements
    equipment_required = models.JSONField(default=list, blank=True)
    software_required = models.JSONField(default=list, blank=True)
    internet_speed = models.CharField(max_length=100, blank=True)
    
    # Commitment
    min_hours_per_week = models.FloatField(null=True, blank=True)
    total_estimated_hours = models.FloatField(null=True, blank=True)
    
    # Custom criteria
    custom_criteria = models.JSONField(default=dict, blank=True)
    
    # Participant counts
    target_participant_count = models.IntegerField(default=50)
    min_participant_count = models.IntegerField(default=30)
    max_participant_count = models.IntegerField(default=100)
    
    def __str__(self):
        return f"Requirements for {self.research.title}"


class ParticipantPosition(models.Model):
    """Open positions for research participants with optional compensation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    research = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='positions')
    
    title = models.CharField(max_length=300)
    description = models.TextField()
    requirements = models.ForeignKey(ParticipantRequirements, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Compensation
    compensation_type = models.CharField(max_length=50, choices=COMPENSATION_TYPE, default='none')
    compensation_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compensation_currency = models.CharField(max_length=3, default='USD')
    compensation_description = models.TextField(blank=True)
    
    # Timeline
    application_deadline = models.DateTimeField()
    start_date = models.DateField(null=True, blank=True)
    estimated_duration_hours = models.FloatField(help_text="Estimated time commitment in hours")
    estimated_duration_weeks = models.IntegerField(default=4)
    
    # Status
    is_active = models.BooleanField(default=True)
    slots_available = models.IntegerField(default=10)
    slots_filled = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['application_deadline']),
            models.Index(fields=['research']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.research.title}"
    
    @property
    def is_full(self):
        return self.slots_filled >= self.slots_available


class ResearchParticipant(models.Model):
    """Participants in research projects"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    research = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='participants')
    position = models.ForeignKey(ParticipantPosition, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='research_participations')
    
    # Status
    status = models.CharField(max_length=50, choices=PARTICIPANT_STATUS, default='invited')
    consent_given = models.BooleanField(default=False)
    consent_date = models.DateTimeField(null=True, blank=True)
    consent_signature = models.CharField(max_length=500, blank=True)
    
    # Engagement
    joined_at = models.DateTimeField(default=datetime.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    hours_contributed = models.FloatField(default=0)
    tasks_completed = models.IntegerField(default=0)
    
    # Compensation tracking
    compensation_paid = models.BooleanField(default=False)
    compensation_date = models.DateTimeField(null=True, blank=True)
    compensation_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Performance and feedback
    researcher_rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating by researcher")
    participant_feedback = models.TextField(blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    withdrawal_reason = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['research', 'user']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['research', 'status']),
            models.Index(fields=['user']),
        ]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.research.title}"


class ParticipantMatching(models.Model):
    """Algorithm-based matching of participants to research"""
    participant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='research_matches')
    research = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='participant_matches')
    
    # Matching algorithm results
    match_score = models.FloatField(help_text="0-100 compatibility score")
    matching_criteria = models.JSONField(default=dict)
    
    # Criteria scores
    age_match = models.FloatField(default=0)
    education_match = models.FloatField(default=0)
    experience_match = models.FloatField(default=0)
    availability_match = models.FloatField(default=0)
    location_match = models.FloatField(default=0)
    
    matched_at = models.DateTimeField(default=datetime.now)
    
    # Notification and engagement
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    participant_viewed = models.BooleanField(default=False)
    participant_applied = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['participant', 'research']
        indexes = [
            models.Index(fields=['-match_score']),
            models.Index(fields=['participant', '-match_score']),
            models.Index(fields=['research', '-match_score']),
        ]
        ordering = ['-match_score']
    
    def __str__(self):
        return f"{self.participant.email} - {self.research.title} (Score: {self.match_score})"


class ResearchGuidelines(models.Model):
    """Guidelines and policies for research participants"""
    research = models.OneToOneField(ResearchProject, on_delete=models.CASCADE, related_name='guidelines')
    
    participant_guidelines = models.TextField()
    data_collection_guidelines = models.TextField()
    privacy_policy = models.TextField()
    withdrawal_policy = models.TextField()
    communication_guidelines = models.TextField()
    compensation_policy = models.TextField(blank=True)
    data_usage_policy = models.TextField()
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Guidelines for {self.research.title}"


class PeerReview(models.Model):
    """Peer review process for research quality assurance"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    research = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='conducted_reviews')
    
    # Review details
    status = models.CharField(max_length=50, choices=REVIEW_STATUS, default='pending')
    overall_rating = models.IntegerField(null=True, blank=True, help_text="1-5 rating")
    
    # Review sections
    methodology_rating = models.IntegerField(null=True, blank=True)
    methodology_feedback = models.TextField(blank=True)
    
    results_rating = models.IntegerField(null=True, blank=True)
    results_feedback = models.TextField(blank=True)
    
    conclusion_rating = models.IntegerField(null=True, blank=True)
    conclusion_feedback = models.TextField(blank=True)
    
    ethics_rating = models.IntegerField(null=True, blank=True)
    ethics_feedback = models.TextField(blank=True)
    
    general_comments = models.TextField(blank=True)
    confidential_comments = models.TextField(blank=True)
    
    # Recommendation
    recommendation = models.CharField(max_length=50, choices=(
        ('accept', 'Accept'),
        ('minor_revision', 'Minor Revision'),
        ('major_revision', 'Major Revision'),
        ('reject', 'Reject'),
    ), blank=True)
    
    # Timestamps
    assigned_at = models.DateTimeField(default=datetime.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['research', 'status']),
            models.Index(fields=['reviewer']),
            models.Index(fields=['status']),
        ]
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"Review by {self.reviewer.email} for {self.research.title}"


class ResearchPublication(models.Model):
    """Published research papers"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    research = models.OneToOneField(ResearchProject, on_delete=models.CASCADE, related_name='publication')
    
    # Publication details
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    full_paper = models.FileField(upload_to='research/publications/')
    supplementary_materials = models.FileField(upload_to='research/supplementary/', null=True, blank=True)
    
    # Metadata
    keywords = models.JSONField(default=list)
    categories = models.JSONField(default=list)
    authors = models.JSONField(default=list)
    
    # Visibility
    is_public = models.BooleanField(default=False)
    access_level = models.CharField(max_length=50, choices=(
        ('open_access', 'Open Access'),
        ('institutional', 'Institutional Access'),
        ('restricted', 'Restricted'),
        ('private', 'Private'),
    ), default='restricted')
    
    # DOI and identifiers
    doi = models.CharField(max_length=200, blank=True, unique=True, null=True)
    isbn = models.CharField(max_length=20, blank=True)
    
    # Metrics
    views = models.IntegerField(default=0)
    downloads = models.IntegerField(default=0)
    citations = models.IntegerField(default=0)
    
    # Timestamps
    published_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['is_public']),
            models.Index(fields=['access_level']),
        ]
        ordering = ['-published_at']
    
    def __str__(self):
        return self.title


class ResearchMilestone(models.Model):
    """Track research project milestones"""
    research = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='milestones')
    
    title = models.CharField(max_length=300)
    description = models.TextField()
    due_date = models.DateField()
    completed = models.BooleanField(default=False)
    completed_date = models.DateField(null=True, blank=True)
    
    # Order
    sequence = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        ordering = ['sequence', 'due_date']
        indexes = [
            models.Index(fields=['research', 'sequence']),
        ]
    
    def __str__(self):
        return f"{self.research.title} - {self.title}"
