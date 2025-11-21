from django.db import models
from Rooms.models import Room, DefaultRoom
from Resources.models import Resource, Links
from Announcements.models import Announcements, Task
from Authentication.models import Profile
from Events.models import Event


# Create your models here.


class Stack(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=500, null=True, blank=True)
    created_by = models.ManyToManyField(Profile, related_name='stack_creators', blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    resources = models.ManyToManyField(Resource, related_name='stack_resources', blank=True)
    tasks = models.ManyToManyField(Task, related_name='stack_tasks', blank=True)
    announcements = models.ManyToManyField(Announcements, related_name='stack_announcements', blank=True)
    events = models.ManyToManyField(Event, related_name='stack_events', blank=True)
    links = models.ManyToManyField(Links, related_name='stack_links', blank=True)

    def __str__(self):
        return self.name
 
class Specialization(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=500, null=True, blank=True)
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='created_specializations')
    created_on = models.DateTimeField(auto_now_add=True)
    stacks = models.ManyToManyField(Stack, related_name='specialization_stacks', blank=True)

    def __str__(self):
        return self.name   

class SavedStack(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='saved_stacks')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='saved_by_profiles')
    saved_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} saved {self.stack.name}"

class SavedSpecialization(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='saved_specializations')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='saved_by_profiles')
    saved_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} saved {self.specialization.name}"
    
class SpecializationMembership(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='specialization_memberships')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='members')
    joined_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} is a member of {self.specialization.name}"
    
class StackMembership(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='stack_memberships')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='members')
    joined_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} is a member of {self.stack.name}"
    
class SpecializationAdmin(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='specialization_admins')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='admins')
    assigned_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} is an admin of {self.specialization.name}"

class StackAdmin(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='stack_admins')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='admins')
    assigned_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} is an admin of {self.stack.name}"
    
class SpecializationModerator(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='specialization_moderators')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='moderators')
    assigned_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} is a moderator of {self.specialization.name}"
    
class StackModerator(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='stack_moderators')
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE, related_name='moderators')
    assigned_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.username} is a moderator of {self.stack.name}"

class SpecializationRoom(models.Model):
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE, related_name='room_specialization')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='specialization_rooms')
    added_on = models.DateTimeField(auto_now_add=True)
    related_rooms = models.ManyToManyField(Room, blank=True, related_name='related_rooms')
    related_default_rooms = models.ManyToManyField(DefaultRoom, blank=True, related_name='related_default_rooms')

    def __str__(self):
        return f"Room {self.room.name} for Specialization {self.specialization.name}"
    

class CompletedStacks(models.Model):
