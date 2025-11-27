from django.db import models
from Authentication.models import CustomUser, Student, StudentAdmin, OrgStaff, OrgAdmin, InstAdmin, InstBranch
from Institution.models import Institution
from Organisation.models import Organisation
from Announcements.models import Task, Announcements, Reply, AnnouncementsRequest, Reposts, Text, Choice, Pin, FileResponse, CompletedTask, Question, QuestionResponse, SubQuestion, TaskResponse
from Events.models import Event
from datetime import datetime
import uuid
# from Resources.models import Resource

# Create your models here.
class Room(models.Model):
    name = models.CharField(max_length=255)
    room_code = models.CharField(max_length=200, unique=True, editable=False, default=uuid.uuid4().hex[:10].upper())
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    description = models.TextField(max_length=255, null=True)
    institutions = models.ManyToManyField(Institution, blank=True, related_name='institution_related_to_room')
    organisation = models.ManyToManyField(Institution, blank=True, related_name='organisation_related_to_room')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    created_on = models.DateTimeField(default=datetime.now)
    admins = models.ManyToManyField(CustomUser, related_name='room_admins', blank=True) # CustomUser can admin many rooms, a room can have many admins 
    moderators = models.ManyToManyField(CustomUser, related_name='room_moderators', blank=True) # CustomUser can moderator many rooms, a room can have many moderators 
    members = models.ManyToManyField(CustomUser, related_name='room_members', blank=True) # CustomUser can join many rooms, a room can have many CustomUsers
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
    resources = models.ManyToManyField('Resources.Resource', related_name='room_resources', blank=True)
    capacity_counter = models.IntegerField(default=0)
    capacity_quota = models.IntegerField(default=0)
    past_memmbers = models.ManyToManyField(CustomUser, blank=True, related_name="room_past_members")


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
    inst_or_org_name = models.CharField(max_length=255)
    reference_object_code = models.CharField(max_length=255, default='None')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    created_on = models.DateTimeField(default=datetime.now)
    rooms = models.ManyToManyField(Room, related_name='default_sub_rooms', blank=True) # A DefaultRoom can have many Rooms, a Room can belong to many DefaultRooms
    members = models.ManyToManyField(CustomUser, related_name='joined_default_rooms', blank=True) # CustomUser can join many rooms, a room can have many CustomUsers
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    admins = models.ManyToManyField(CustomUser, related_name='admin_default_rooms', blank=True) # CustomUser can admin many rooms, a room can have many admins 
    moderators = models.ManyToManyField(CustomUser, related_name='default_room_moderators', blank=True) # CustomUser can moderator many rooms, a room can have many moderators 
    text = models.ManyToManyField(Text, related_name='default_room_texts', blank=True)
    announcements = models.ManyToManyField(Announcements, related_name='default_room_announcements', blank=True)
    tasks = models.ManyToManyField(Task, related_name='default_room_tasks', blank=True)
    events = models.ManyToManyField(Event, related_name='default_room_events', blank=True)
    reposts = models.ManyToManyField(Reposts, related_name='default_room_reposts', blank=True)
    pins = models.ManyToManyField(Pin, related_name='default_room_pins', blank=True)
    file_responses = models.ManyToManyField(FileResponse, related_name='default_room_file_responses', blank=True)
    replies = models.ManyToManyField(Reply, related_name='default_room_replies', blank=True)
    announcements_requests = models.ManyToManyField(AnnouncementsRequest, related_name='default_room_announcements_requests', blank=True)
    completed_tasks = models.ManyToManyField(CompletedTask, related_name='default_room_completed_tasks', blank=True)
    task_responses = models.ManyToManyField(TaskResponse, related_name='default_room_task_responses', blank=True)
    resources = models.ManyToManyField('Resources.Resource', related_name='default_room_resources', blank=True)
    capacity_counter = models.IntegerField(default=0)
    past_memmbers = models.ManyToManyField(CustomUser, blank=True, related_name="default_room_past_members")
    
    def generate_invitation_code(self):
        return uuid.uuid4().hex[:10].upper()
    
    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = self.generate_invitation_code()
        super().save(*args, **kwargs)

    
    
    def __str__(self):
        return self.name
    
class DirectMessageRoom(models.Model):
    participants = models.ManyToManyField(CustomUser, related_name='dm_rooms')
    created_on = models.DateTimeField(default=datetime.now)
    texts = models.ManyToManyField(Text, related_name='dm_room_texts', blank=True)
    announcements = models.ManyToManyField(Announcements, related_name='dm_room_announcements', blank=True)
    tasks = models.ManyToManyField(Task, related_name='dm_room_tasks', blank=True)
    events = models.ManyToManyField(Event, related_name='dm_room_events', blank=True)
    reposts = models.ManyToManyField(Reposts, related_name='dm_room_reposts', blank=True)
    pins = models.ManyToManyField(Pin, related_name='dm_room_pins', blank=True)
    file_responses = models.ManyToManyField(FileResponse, related_name='dm_room_file_responses', blank=True)
    replies = models.ManyToManyField(Reply, related_name='dm_room_replies', blank=True)
    announcements_requests = models.ManyToManyField(AnnouncementsRequest, related_name='dm_room_announcements_requests', blank=True)
    completed_tasks = models.ManyToManyField(CompletedTask, related_name='dm_room_completed_tasks', blank=True)
    task_responses = models.ManyToManyField(TaskResponse, related_name='dm_room_task_responses', blank=True)
    forwarded_messages = models.ManyToManyField('DirectMessage', related_name='forwarded_in_dm_rooms', blank=True)
    links = models.ManyToManyField('DirectMessage', related_name='linked_in_dm_rooms', blank=True)
    resources = models.ManyToManyField('Resources.Resource', related_name='dm_room_resources', blank=True)

    def __str__(self):
        participant_usernames = ', '.join([user.username for user in self.participants.all()])
        return f"DM Room between: {participant_usernames}"


class DirectMessage(models.Model):
    sender = models.ForeignKey(CustomUser, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(CustomUser, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField(max_length=5000, null=False)
    file = models.FileField(upload_to='direct_messages/files', null=True, blank=True)
    dm_room = models.ForeignKey(DirectMessageRoom, related_name='messages', on_delete=models.CASCADE)
    status = models.CharField(max_length=200, choices=[('sent', 'Sent'), ('delivered', 'Delivered'), ('read', 'Read'), ('not_sent', 'Not Sent'), ('pending', 'Pending')], default='pending')
    message_type = models.CharField(max_length=50, choices=[('text', 'Text'), ('file', 'File'), ('link', 'Link'), ('announcement', 'Announcement'), ('task', 'Task')], default='text')
    message_origin = models.CharField(max_length=50, choices=[('original', 'Original'), ('forwarded', 'Forwarded')], default='original')
    time_stamp = models.DateTimeField(default=datetime.now)
    is_read = models.BooleanField(default=False)
    delivered_on = models.DateTimeField(default=datetime.now)
    read_on = models.DateTimeField(default=datetime.now)

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username} at {self.time_stamp}"
    
class ForwadingLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    direct_message = models.ForeignKey(DirectMessage, on_delete=models.DO_NOTHING)
    forwarded_on = models.DateTimeField(default=datetime.now)
