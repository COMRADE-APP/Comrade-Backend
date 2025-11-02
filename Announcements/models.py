from django.db import models
from datetime import datetime
from Authentication.models import StudentAdmin
# from django.contrib.auth.models import User
from Authentication.models import Student
from Resources.models import VIS_TYPES

# Create your models here.

ANN_STATUS = (
    ('pending', 'Pending'),
    ('scheduled', 'Scheduled'),
    ('sent', 'Sent'),
    ('not_sent', 'Not Sent')
)
VER_STATUS = (
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Disqualified'),
)

TASK_TYPE = (
    ('radio', 'Single Choice Answers'),
    ('check', 'Multiple Choice Answers'),
    ('text', 'Text Answers'),
    ('file', 'File Upload'),
)

class Text(models.Model):
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)
    content = models.CharField(max_length=5000, null=False)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    time_stamp = models.DateTimeField(default=datetime.now())
    # source = models.OneToOneField(User, on_delete=models.DO_NOTHING)

class Reply(models.Model):
    reference_text = models.OneToOneField(Text, on_delete=models.DO_NOTHING)
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)
    content = models.CharField(max_length=5000, null=False)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    time_stamp = models.DateTimeField(default=datetime.now())



class Announcements(models.Model):
    user = models.OneToOneField(StudentAdmin, on_delete=models.DO_NOTHING)
    heading = models.CharField(max_length=200, null=False)
    content = models.TextField(max_length=5000, null=False)
    visibility = models.CharField(max_length=200, null=False, choices=VIS_TYPES, default='private')
    schedule_time = models.DateTimeField(default=datetime.now())
    expiry_time = models.DateTimeField(default=datetime(year=9999, month=12, day=31))
    time_stamp = models.DateTimeField(default=datetime.now())
    send_status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    read_status = models.BooleanField(default=False)
    read_time = models.DateTimeField(null=True, blank=True)


class AnnouncementsRequest(models.Model):
    user = models.OneToOneField(Student, on_delete=models.DO_NOTHING)
    verified_by = models.OneToOneField(StudentAdmin, on_delete=models.DO_NOTHING)
    verification_status = models.CharField(max_length=200, null=False, choices=VER_STATUS, default='pending')
    heading = models.CharField(max_length=200, null=False)
    content = models.TextField(max_length=5000, null=False)
    visibility = models.CharField(max_length=200, null=False, choices=VIS_TYPES, default='private')
    time_stamp = models.DateTimeField(default=datetime.now())
    verification_time_stamp = models.DateTimeField(default=datetime.now())
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')

class Choice(models.Model):
    content = models.CharField(max_length=5000, null=False)
    is_correct = models.BooleanField(default=False)
    selected = models.BooleanField(default=False)

class Task(models.Model):
    user = models.OneToOneField(StudentAdmin, on_delete=models.DO_NOTHING)
    heading = models.CharField(max_length=200, null=False)
    content = models.TextField(max_length=5000, null=False)
    time_stamp = models.DateTimeField(default=datetime.now())
    answers_type = models.CharField(max_length=200, null=False, choices=TASK_TYPE, default='text')
    answer_text = models.ManyToManyField(Choice, blank=True)
    answer_file = models.FileField(upload_to=f'task_answers/', null=True, blank=True)
    visibility = models.CharField(max_length=200, null=False, choices=VIS_TYPES, default='private')
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    due_date = models.DateTimeField(default=datetime.now())
    is_completed = models.BooleanField(default=False)
    completed_on = models.DateTimeField(default=datetime.now())

    def mark_as_completed(self):
        self.is_completed = True
        self.completed_on = datetime.now()
        self.save()
    def mark_as_incomplete(self):
        self.is_completed = False
        self.completed_on = None
        self.save()
    def __str__(self):
        return self.heading

# Remember: Task files saving should be in terms of folders (Weekly, monthly or yearly, daily, or roomwise)
