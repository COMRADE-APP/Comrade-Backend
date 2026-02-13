from django.db import models
from datetime import datetime
from Authentication.models import CustomUser
# from django.contrib.auth.models import User
from Authentication.models import Student
from Events.models import Event

# Create your models here.

ANN_STATUS = (
    ('pending', 'Pending'),
    ('scheduled', 'Scheduled'),
    ('sent', 'Sent'),
    ('not_sent', 'Not Sent'),
    ('draft', 'Draft')
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

TASK_STATE = (
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('full', 'Full'),
    ('unavailable', 'Unavalible')
)

VIS_TYPES = (
    ('public', 'Public'),
    ('private', 'Private'),
    ('only_me', 'Only Me'),
    ('course', 'Your Course or Class'),
    ('faculty', 'Your Faculty or School'),
    ('institutional', 'Your Institution'),
    ('organisational', 'Your Organisation'),
    ('group', 'Your Group or Section')
)



# Creator's Side of the platform
"""Admins and Moderator's models implemetations inside and outside rooms"""
class Announcements(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    # Entity Authorship
    institution = models.ForeignKey('Institution.Institution', on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    organisation = models.ForeignKey('Organisation.Organisation', on_delete=models.CASCADE, null=True, blank=True, related_name='announcements')
    heading = models.CharField(max_length=200, null=False)
    content = models.TextField(max_length=5000, null=False)
    visibility = models.CharField(max_length=200, null=False, choices=VIS_TYPES, default='private')
    schedule_time = models.DateTimeField(default=datetime.now)
    expiry_time = models.DateTimeField(default=datetime(year=9999, month=12, day=31))
    send_status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    read_status = models.BooleanField(default=False)
    read_time = models.DateTimeField(null=True, blank=True)
    time_stamp = models.DateTimeField(default=datetime.now)


class AnnouncementsRequest(models.Model):
    user = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    verification_status = models.CharField(max_length=200, null=False, choices=VER_STATUS, default='pending')
    heading = models.CharField(max_length=200, null=False)
    content = models.TextField(max_length=5000, null=False)
    visibility = models.CharField(max_length=200, null=False, choices=VIS_TYPES, default='private')
    verification_time_stamp = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, default='pending')
    time_stamp = models.DateTimeField(default=datetime.now)

class Task(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    # Entity Authorship
    institution = models.ForeignKey('Institution.Institution', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    organisation = models.ForeignKey('Organisation.Organisation', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks')
    heading = models.CharField(max_length=200, null=False)
    description = models.TextField(max_length=5000, null=False)
    visibility = models.CharField(max_length=200, null=False, choices=VIS_TYPES, default='private')
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    state = models.CharField(max_length=200, choices=TASK_STATE, default='active')
    due_date = models.DateTimeField(default=datetime.now)
    time_stamp = models.DateTimeField(default=datetime.now)

class Question(models.Model):
    task = models.ForeignKey(Task, on_delete=models.DO_NOTHING)
    heading = models.CharField(max_length=200, null=False)
    position = models.IntegerField(default=1)
    description = models.TextField(max_length=5000, null=False)
    question_type = models.CharField(max_length=200, null=False, choices=TASK_TYPE, default='text')
    has_subquestion = models.BooleanField(default=False)
    time_stamp = models.DateTimeField(default=datetime.now)

class SubQuestion(models.Model):
    question = models.OneToOneField(Question, on_delete=models.DO_NOTHING)
    heading = models.CharField(max_length=200, null=False)
    position = models.IntegerField(default=1)
    description = models.TextField(max_length=5000, null=False)
    question_type = models.CharField(max_length=200, null=False, choices=TASK_TYPE, default='text')
    time_stamp = models.DateTimeField(default=datetime.now)

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING, null=True)
    sub_question = models.ForeignKey(SubQuestion, on_delete=models.DO_NOTHING, null=True, blank=True)
    content = models.CharField(max_length=5000, null=False)
    is_correct = models.BooleanField(default=False)
    selected = models.BooleanField(default=False)
    time_stamp = models.DateTimeField(default=datetime.now)

class FileResponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    sub_question = models.ForeignKey(SubQuestion, on_delete=models.DO_NOTHING, null=True, blank=True)
    position = models.IntegerField(default=1)
    description = models.TextField(max_length=5000, null=True, blank=True)
    content = models.FileField(upload_to='task_files/')
    time_stamp = models.DateTimeField(default=datetime.now)



# class SubTask(models.Model):
#     user = models.ForeignKey(Task, on_delete=models.DO_NOTHING)
#     description = models.TextField(max_length=5000, null=False)
#     time_stamp = models.DateTimeField(default=datetime.now)
#     task_type = models.CharField(max_length=200, null=False, choices=TASK_TYPE, default='text')
#     task_text = models.ManyToManyField(Choice, blank=True)
#     task_file = models.ManyToManyField(FileResponse, blank=True)
#     status = models.CharField(max_length=200, choices=ANN_STATUS, 
#     default='pending')
#     state = models.CharField(max_length=200, choices=TASK_STATE, default='active')

    # def mark_as_completed(self):
    #     self.is_completed = True
    #     self.completed_on = datetime.now()
    #     self.save()
    # def mark_as_incomplete(self):
    #     self.is_completed = False
    #     self.completed_on = None
    #     self.save()
    # def __str__(self):
    #     return self.heading

"""Student's models implemetations"""
class Text(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    content = models.CharField(max_length=5000, null=False)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    time_stamp = models.DateTimeField(default=datetime.now)
    # source = models.ForeignKey(User, on_delete=models.DO_NOTHING)

class Reply(models.Model):
    reference_text = models.ForeignKey(Text, on_delete=models.DO_NOTHING)
    reference_reply = models.ForeignKey('self', on_delete=models.DO_NOTHING, null=True)
    user = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    content = models.CharField(max_length=5000, null=False)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')
    time_stamp = models.DateTimeField(default=datetime.now)

class Reposts(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    announcement = models.ForeignKey(Announcements, blank=True, on_delete=models.DO_NOTHING, null=True)
    task = models.ForeignKey(Task, blank=True, on_delete=models.DO_NOTHING, null=True)
    event = models.ForeignKey(Event, blank=True, on_delete=models.DO_NOTHING, null=True)
    caption = models.TextField(default='', max_length=5000)
    image = models.FileField(upload_to='reposts/images', null=True, blank=True)
    video = models.FileField(upload_to='reposts/videos', null=True, blank=True)
    time_stamp = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')

class Pin(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    announcements = models.ManyToManyField(Announcements, related_name='pinned_announcements', blank=True)
    tasks = models.ManyToManyField(Task, related_name='pinned_tasks', blank=True)
    events = models.ManyToManyField(Event, related_name='pinned_events', blank=True)
    reposts = models.ManyToManyField(Reposts, related_name='pinned_reposts', blank=True)
    time_stamp = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, 
    default='pending')

class CompletedTask(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    task = models.ForeignKey(Task, on_delete=models.DO_NOTHING)
    is_completed = models.BooleanField(default=False)
    completed_on = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, default='pending')


class QuestionResponse(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    task = models.ForeignKey(Task, on_delete=models.DO_NOTHING)
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    sub_question = models.ForeignKey(SubQuestion, on_delete=models.DO_NOTHING, null=True, blank=True)
    answer_text = models.TextField(max_length=5000, null=False)
    answer_choice = models.ForeignKey(Choice, on_delete=models.DO_NOTHING)
    answer_file = models.FileField(upload_to='task_answers/')
    score = models.FloatField(default=0.0)
    time_stamp = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, default='pending')

class TaskResponse(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    task = models.ForeignKey(Task, on_delete=models.DO_NOTHING)
    question_responses = models.ManyToManyField(QuestionResponse, blank=True)
    total_score = models.FloatField(default=0.0)
    time_stamp = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, default='pending')

# Remember: Task files saving should be in terms of folders (Weekly, monthly or yearly, daily, or roomwise)
# FileResponse, CompletedTask, Question, QuestionResponse
class Reaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    announcement = models.ForeignKey(Announcements, blank=True, on_delete=models.DO_NOTHING, null=True)
    task = models.ForeignKey(Task, blank=True, on_delete=models.DO_NOTHING, null=True)
    text = models.ForeignKey(Text, blank=True, on_delete=models.DO_NOTHING, null=True)
    dm = models.ForeignKey('Rooms.DirectMessage', blank=True, on_delete=models.DO_NOTHING, null=True)
    reaction_type = models.CharField(max_length=100, null=False)
    time_stamp = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, default='pending')

class Comment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    announcement = models.ForeignKey(Announcements, blank=True, on_delete=models.DO_NOTHING, null=True)
    task = models.ForeignKey(Task, blank=True, on_delete=models.DO_NOTHING, null=True)
    text = models.ForeignKey(Text, blank=True, on_delete=models.DO_NOTHING, null=True)
    dm = models.ForeignKey('Rooms.DirectMessage', blank=True, on_delete=models.DO_NOTHING, null=True)
    content = models.TextField(max_length=5000, null=False)
    time_stamp = models.DateTimeField(default=datetime.now)
    status = models.CharField(max_length=200, choices=ANN_STATUS, default='pending')

# Import enhanced announcement models
from .enhanced_models import *
