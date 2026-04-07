from django.db import models
from django.conf import settings
from Rooms.models import Room, DefaultRoom, OPERATION_STATUS, TEXTING_STATUS
from Resources.models import Resource, Link
from Announcements.models import Task, Announcements, Reply, AnnouncementsRequest, Reposts, Text, Pin, FileResponse, CompletedTask, TaskResponse
from Authentication.models import Profile, CustomUser
from Events.models import Event
import uuid
from datetime import datetime
from Organisation.models import Organisation
from Institution.models import Institution



# Create your models here.

PARTICIPANTS = (
    ('individuals', 'Individuals'), 
    ('rooms', 'Rooms'), 
    ('rooms_and_individuals', 'Both Rooms and Individuals'),
)

class Stack(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=500, null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    created_by = models.ManyToManyField(Profile, related_name='stack_creators', blank=True)
    created_on = models.DateTimeField(default=datetime.now)
    resources = models.ManyToManyField(Resource, related_name='stack_resources', blank=True)
    tasks = models.ManyToManyField(Task, related_name='stack_tasks', blank=True)
    announcements = models.ManyToManyField(Announcements, related_name='stack_announcements', blank=True)
    events = models.ManyToManyField(Event, related_name='stack_events', blank=True)
    links = models.ManyToManyField(Link, related_name='stack_links', blank=True)
    members = models.ManyToManyField(Profile, blank=True, related_name='stack_members_collection')
    admins = models.ManyToManyField(Profile, blank=True, related_name='stack_admins_collections')
    moderator = models.ManyToManyField(Profile, blank=True, related_name='stack_moderators_collections')


    def __str__(self):
        return self.name
    
 
class Specialization(models.Model):
    name = models.CharField(max_length=255, unique=False)
    description = models.TextField(max_length=500, null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    
    LEARNING_TYPES = [
        ('specialization', 'Specialization'),
        ('course', 'Course'),
        ('masterclass', 'Masterclass')
    ]
    learning_type = models.CharField(max_length=50, choices=LEARNING_TYPES, default='specialization')
    is_paid = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_by = models.ManyToManyField(Profile, blank=True, related_name='created_specializations')
    created_on = models.DateTimeField(default=datetime.now)
    stacks = models.ManyToManyField(Stack, related_name='specialization_stacks', blank=True)
    members = models.ManyToManyField(Profile, blank=True, related_name='specialization_members_collection')
    admins = models.ManyToManyField(Profile, blank=True, related_name='specialization_admins_collections')
    moderator = models.ManyToManyField(Profile, blank=True, related_name='specialization_moderators_collections')
    
    def __str__(self):
        return self.name 

class PositionTracker(models.Model):
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    position = models.IntegerField()
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)

class SavedStack(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='saved_stacks')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='saved_by_profiles')
    saved_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} saved {self.stack.name}"

class SavedSpecialization(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='saved_specializations')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='saved_by_profiles')
    saved_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} saved {self.specialization.name}"
    
class SpecializationMembership(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='specialization_memberships')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    joined_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} is a member of {self.specialization.name}"
    
class StackMembership(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='stack_memberships')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    joined_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} is a member of {self.stack.name}"
    
class SpecializationAdmin(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='specialization_admin')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    assigned_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} is an admin of {self.specialization.name}"

class StackAdmin(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='stack_admin')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    assigned_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} is an admin of {self.stack.name}"
    
class SpecializationModerator(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='specialization_moderators')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='moderators')
    assigned_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} is a moderator of {self.specialization.name}"
    
class StackModerator(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='stack_moderators')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='moderators')
    assigned_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"{self.profile.username} is a moderator of {self.stack.name}"

class SpecializationRoom(models.Model):
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='specialization_room_specialization')
    name = models.CharField(max_length=255, default='None')
    room_code = models.CharField(max_length=200, unique=True, editable=False, default=uuid.uuid4().hex[:10].upper())
    invitation_code = models.CharField(max_length=10, unique=True, default='')
    related_rooms = models.ManyToManyField(Room, blank=True, related_name='related_rooms')
    related_default_rooms = models.ManyToManyField(DefaultRoom, blank=True, related_name='related_default_rooms')
    related_specialization_rooms = models.ManyToManyField('self', blank=True)
    description = models.TextField(max_length=255, null=True)
    institutions = models.ManyToManyField(Institution, blank=True, related_name='institution_related_to_specialization_room')
    organisation = models.ManyToManyField(Organisation, blank=True, related_name='organisation_related_to_specialization_room')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    created_on = models.DateTimeField(default=datetime.now)
    admins = models.ManyToManyField(CustomUser, related_name='specialization_room_admins', blank=True) # CustomUser can admin many rooms, a room can have many admins 
    moderators = models.ManyToManyField(CustomUser, related_name='specialization_room_moderators', blank=True) # CustomUser can moderator many rooms, a room can have many moderators 
    members = models.ManyToManyField(CustomUser, related_name='specialization_room_members', blank=True) # CustomUser can join many rooms, a room can have many CustomUsers
    text = models.ManyToManyField(Text, related_name='specialization_room_texts', blank=True)
    announcements = models.ManyToManyField(Announcements, related_name='specialization_room_announcements', blank=True)
    tasks = models.ManyToManyField(Task, related_name='specialization_room_tasks', blank=True)
    events = models.ManyToManyField(Event, related_name='specialization_room_events', blank=True)
    reposts = models.ManyToManyField(Reposts, related_name='specialization_room_reposts', blank=True)
    pins = models.ManyToManyField(Pin, related_name='specialization_room_pins', blank=True)
    file_responses = models.ManyToManyField(FileResponse, related_name='specialization_room_file_responses', blank=True)
    replies = models.ManyToManyField(Reply, related_name='specialization_room_replies', blank=True)
    announcements_requests = models.ManyToManyField(AnnouncementsRequest, related_name='specialization_room_announcements_requests', blank=True)
    completed_tasks = models.ManyToManyField(CompletedTask, related_name='specialization_room_completed_tasks', blank=True)
    task_responses = models.ManyToManyField(TaskResponse, related_name='specialization_room_task_responses', blank=True)
    resources = models.ManyToManyField('Resources.Resource', related_name='specialization_room_resources', blank=True)
    capacity_counter = models.IntegerField(default=0)
    capacity_quota = models.IntegerField(default=0)
    past_memmbers = models.ManyToManyField(CustomUser, blank=True, related_name="specialization_room_past_members")
    members_type = models.CharField(max_length=200, choices=PARTICIPANTS, default='individuals')
    operation_state = models.CharField(max_length=200, choices=OPERATION_STATUS, default='pending')
    text_priority = models.CharField(max_length=200, choices=TEXTING_STATUS, default='creator')


    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        super().save(*args, **kwargs)
    
    def generate_invitation_code(self):
        return uuid.uuid4().hex[:10].upper()

    def __str__(self):
        return f"Room {self.room.name} for Specialization {self.specialization.name}"
    

class CompletedStack(models.Model):
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='completed_stack')
    completed_on = models.DateTimeField(default=datetime.now)
    completed_by = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return f"Completed Stack {self.stack.name} by {self.completed_by}"
    
class CompletedSpecialization(models.Model):
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='completed_specialization')
    completed_on = models.DateTimeField(default=datetime.now)
    completed_by = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return f"Completed Stack {self.specialization.name} by {self.completed_by}"


# ============================================================================
# LESSON & CONTENT SYSTEM
# ============================================================================

CONTENT_TYPES = [
    ('video', 'Video'),
    ('text', 'Text / Article'),
    ('audio', 'Audio / Podcast'),
    ('image', 'Image / Infographic'),
    ('code', 'Code Snippet'),
    ('file', 'Downloadable File'),
    ('embed', 'External Embed'),
]

class Lesson(models.Model):
    """Individual content unit within a Stack (module)."""
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPES, default='text')
    content_text = models.TextField(blank=True, help_text="Rich text / markdown content")
    video_url = models.URLField(max_length=500, blank=True, help_text="YouTube / Vimeo / direct link")
    audio_url = models.URLField(max_length=500, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    file_upload = models.FileField(upload_to='specialization/lessons/files/', blank=True, null=True)
    code_snippet = models.TextField(blank=True, help_text="Code content with language tag")
    code_language = models.CharField(max_length=50, blank=True, default='python')
    external_url = models.URLField(max_length=500, blank=True, help_text="External resource link")
    order = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=10)
    is_preview = models.BooleanField(default=False, help_text="Can be viewed without enrollment")
    is_locked = models.BooleanField(default=False, help_text="Requires payment to unlock")
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['stack', 'order']

    def __str__(self):
        return f"{self.stack.name} → {self.title}"


# ============================================================================
# QUIZ & ASSESSMENT SYSTEM
# ============================================================================

QUESTION_TYPES = [
    ('multiple_choice', 'Multiple Choice'),
    ('true_false', 'True / False'),
    ('short_answer', 'Short Answer'),
    ('code_challenge', 'Code Challenge'),
]

class Quiz(models.Model):
    """Assessment attached to a Stack (end-of-module) or Lesson (mid-lesson check)."""
    QUIZ_PLACEMENT = [
        ('after_lesson', 'After a Lesson'),
        ('end_of_module', 'End of Module Test'),
        ('final_exam', 'Final Exam for Specialization'),
    ]
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    placement = models.CharField(max_length=20, choices=QUIZ_PLACEMENT, default='end_of_module')
    passing_score = models.PositiveIntegerField(default=70, help_text="Minimum % to pass")
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=3)
    order = models.PositiveIntegerField(default=0)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    """Question within a quiz."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    # JSON: [{"label": "A", "text": "Answer A", "is_correct": true}, ...]
    choices = models.JSONField(default=list, blank=True, help_text="List of choice objects for MC/TF")
    correct_answer = models.TextField(blank=True, help_text="For short answer / code challenge")
    explanation = models.TextField(blank=True, help_text="Shown after answering")
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    code_template = models.TextField(blank=True, help_text="Starter code for code challenges")
    code_language = models.CharField(max_length=50, blank=True, default='python')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:60]}"


class QuizAttempt(models.Model):
    """Record of a user's attempt at a quiz."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    # JSON: [{"question_id": 1, "answer": "A", "is_correct": true}, ...]
    answers = models.JSONField(default=list)
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user} attempt #{self.attempt_number} on {self.quiz.title}"


# ============================================================================
# ENROLLMENT & PROGRESS TRACKING
# ============================================================================

class Enrollment(models.Model):
    """Tracks user enrollment in a specialization/course/masterclass."""
    ENROLLMENT_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('paused', 'Paused'),
    ]
    PAYMENT_STATUS = [
        ('free', 'Free Access'),
        ('paid', 'Paid & Unlocked'),
        ('locked', 'Payment Required'),
        ('trial', 'Trial Access'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS, default='active')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='free')
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'specialization']

    def __str__(self):
        return f"{self.user} enrolled in {self.specialization.name}"


class LearnerProgress(models.Model):
    """Per-user per-lesson completion tracking."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['user', 'lesson']

    def __str__(self):
        status = "✓" if self.completed else "○"
        return f"{status} {self.user} → {self.lesson.title}"


# ============================================================================
# CERTIFICATE SYSTEM (Updated)
# ============================================================================

class Certificate(models.Model):
    """Certificate template — can be auto-generated or custom uploaded."""
    CERT_TYPES = [
        ('completion', 'Certificate of Completion'),
        ('distinction', 'Certificate with Distinction'),
        ('custom', 'Custom Certificate'),
    ]
    specialization = models.ManyToManyField(Specialization, blank=True)
    stack = models.ManyToManyField(Stack, blank=True)
    issuer_name = models.CharField(max_length=500)
    certificate_file = models.FileField(upload_to='specialization/certificates/', blank=True, null=True)
    template_html = models.TextField(blank=True, help_text="HTML template for auto-generated certs")
    certificate_type = models.CharField(max_length=20, choices=CERT_TYPES, default='completion')
    auto_generate = models.BooleanField(default=True, help_text="Auto-issue on completion")
    min_score = models.PositiveIntegerField(default=70, help_text="Min quiz score for distinction")
    created_on = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(Profile, on_delete=models.DO_NOTHING, null=True)

    def __str__(self):
        return f"Certificate: {self.issuer_name} ({self.certificate_type})"


class IssuedCertificate(models.Model):
    """Issued certificate instance for a specific user."""
    specialization = models.ManyToManyField(Specialization, blank=True)
    stack = models.ManyToManyField(Stack, blank=True)
    issued_to = models.ForeignKey(Profile, on_delete=models.DO_NOTHING, null=False, related_name='received_certificates')
    certificate = models.ForeignKey(Certificate, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_instances')
    certificate_file = models.FileField(upload_to='specialization/certificates/issued/', blank=True, null=True)
    verification_code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    grade = models.CharField(max_length=10, blank=True, help_text="e.g. A, B+, Pass")
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    hours_completed = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    issued_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"Cert {self.verification_code} → {self.issued_to}"

