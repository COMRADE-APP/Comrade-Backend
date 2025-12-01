from django.db import models
from Rooms.models import Room, DefaultRoom
from Resources.models import Resource, Links
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
    created_by = models.ManyToManyField(Profile, related_name='stack_creators', blank=True)
    created_on = models.DateTimeField(default=datetime.now)
    resources = models.ManyToManyField(Resource, related_name='stack_resources', blank=True)
    tasks = models.ManyToManyField(Task, related_name='stack_tasks', blank=True)
    announcements = models.ManyToManyField(Announcements, related_name='stack_announcements', blank=True)
    events = models.ManyToManyField(Event, related_name='stack_events', blank=True)
    links = models.ManyToManyField(Links, related_name='stack_links', blank=True)
    members = models.ManyToManyField(Profile, blank=True, related_name='stack_members_collection')
    admins = models.ManyToManyField(Profile, blank=True, related_name='stack_admins_collections')
    moderator = models.ManyToManyField(Profile, blank=True, related_name='stack_moderators_collections')


    def __str__(self):
        return self.name
    
 
class Specialization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=500, null=True, blank=True)
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