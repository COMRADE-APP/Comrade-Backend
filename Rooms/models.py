from django.db import models
from Authentication.models import CustomUser, Student, StudentAdmin, OrgStaff, OrgAdmin, InstAdmin, InstBranch
from Announcements.models import Task, Announcements, Reply, AnnouncementsRequest, Reposts, Text, Choice, Pin, FileResponse, CompletedTask, Question, QuestionResponse, SubQuestion, TaskResponse
from Events.models import Event
from datetime import datetime
import uuid

# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    room_code = models.CharField(max_length=200, unique=True, editable=False, default=uuid.uuid4().hex[:10].upper())
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    description = models.TextField(max_length=255, null=True)
    institution = models.CharField(max_length=255)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    admins = models.ManyToManyField(CustomUser, related_name='admin_rooms', blank=True) # CustomUser can admin many rooms, a room can have many admins 
    members = models.ManyToManyField(CustomUser, related_name='joined_rooms', blank=True) # CustomUser can join many rooms, a room can have many CustomUsers
    text = models.ManyToManyField(Text, related_name='room_texts', blank=True)
    announcements = models.ManyToManyField(Announcements, related_name='room_announcements', blank=True)
    tasks = models.ManyToManyField(Task, related_name='room_tasks', blank=True)
    events = models.ManyToManyField(Event, related_name='room_events', blank=True)
    reposts = models.ManyToManyField(Reposts, related_name='room_reposts', blank=True)
    pins = models.ManyToManyField(Pin, related_name='room_pins', blank=True)
    file_responses = models.ManyToManyField(FileResponse, related_name='room_file_responses', blank=True)
    replies = models.ManyToManyField(Reply, related_name='room_replies', blank=True)
    announcements_requests = models.ManyToManyField(AnnouncementsRequest, related_name='room_announcements_requests', blank=True)
    completed_tasks = models.ManyToManyField(CompletedTask, related_name='room_completed_tasks', blank=True)
    task_responses = models.ManyToManyField(TaskResponse, related_name='room_task_responses', blank=True)
    


    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        super().save(*args, **kwargs)
    
    def generate_invitation_code(self):
        return uuid.uuid4().hex[:10].upper()
    
    def __str__(self):
        return self.name
    
class DefaultRoom(models.Model):
    name = models.CharField(max_length=255)
    room_code = models.CharField(max_length=200, unique=True, default=uuid.uuid4().hex[:10].upper(), editable=False)
    description = models.TextField(max_length=255, null=True)
    institution = models.CharField(max_length=255)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_on = models.DateTimeField(auto_now_add=True)
    members = models.ManyToManyField(CustomUser, related_name='joined_default_rooms', blank=True) # CustomUser can join many rooms, a room can have many CustomUsers
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    
    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        super().save(*args, **kwargs)
    def generate_invitation_code(self):
        return uuid.uuid4().hex[:10].upper()
    
    def __str__(self):
        return self.name


    
