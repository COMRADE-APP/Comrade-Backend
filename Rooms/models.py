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

OPERATION_STATUS = (
    ('active', 'Active'),
    ('deactivated', 'Deactivated'),
    ('deleted', 'Deleted'),
    ('suspended', 'Suspended'),
    ('under_review', 'Under Review'),
    ('draft', 'Draft'),
    ('pending', 'Pending'),
    ('sensored', 'Sensored'),
    ('blocked', 'Blocked'),
)

TEXTING_STATUS = (
    ('admins_only', 'Admins Only'),
    ('admins_moderators_only', 'Admins and Moderators Only'),
    ('all_members', 'All Members'),
    ('creator_only', 'Creator Only'),
)



class Room(models.Model):
    name = models.CharField(max_length=255)
    room_code = models.CharField(max_length=200, unique=True, editable=False, default=uuid.uuid4)
    invitation_code = models.CharField(max_length=10, unique=True, editable=False)
    description = models.TextField(max_length=255, null=True)
    avatar = models.ImageField(upload_to='room_avatars/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='room_covers/', null=True, blank=True)
    institutions = models.ManyToManyField(Institution, blank=True, related_name='institution_related_to_room')
    organisation = models.ManyToManyField('Organisation.Organisation', blank=True, related_name='organisation_related_to_room')
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
    operation_state = models.CharField(max_length=200, choices=OPERATION_STATUS, default='pending')
    text_priority = models.CharField(max_length=200, choices=TEXTING_STATUS, default='creator')


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
    room_code = models.CharField(max_length=200, unique=True, default=uuid.uuid4, editable=False)
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
    operation_state = models.CharField(max_length=200, choices=OPERATION_STATUS, default='pending')
    text_priority = models.CharField(max_length=200, choices=TEXTING_STATUS, default='creator')
    
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




# WhatsApp-like Room Settings
CHAT_PERMISSION_CHOICES = (
    ('admins_only', 'Admins Only'),
    ('admins_moderators', 'Admins and Moderators'),
    ('all_members', 'All Members'),
)

MEMBER_PERMISSION_CHOICES = (
    ('admins_only', 'Admins Only'),
    ('admins_moderators', 'Admins and Moderators'),
    ('all_members', 'All Members'),
)


class RoomSettings(models.Model):
    """WhatsApp-like settings for rooms"""
    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name='settings')
    
    # Chat settings
    chat_enabled = models.BooleanField(default=True)
    chat_permission = models.CharField(max_length=50, choices=CHAT_PERMISSION_CHOICES, default='all_members')
    
    # Member permissions
    who_can_add_members = models.CharField(max_length=50, choices=MEMBER_PERMISSION_CHOICES, default='admins_only')
    who_can_edit_info = models.CharField(max_length=50, choices=MEMBER_PERMISSION_CHOICES, default='admins_only')
    who_can_send_media = models.CharField(max_length=50, choices=CHAT_PERMISSION_CHOICES, default='all_members')
    
    # Tagging & Forwarding
    allow_opinion_tagging = models.BooleanField(default=True)
    allow_message_forwarding = models.BooleanField(default=True)
    show_forward_source = models.BooleanField(default=True)
    
    # Visibility
    is_discoverable = models.BooleanField(default=True)
    require_approval_to_join = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Settings for {self.room.name}"


class RoomChatFile(models.Model):
    """File attachments for room chat messages"""
    file = models.FileField(upload_to='room_chat_files/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(default=datetime.now)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.file_name


MESSAGE_STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('sent', 'Sent'),
    ('delivered', 'Delivered'),
    ('read', 'Read'),
    ('failed', 'Failed'),
)

MESSAGE_TYPE_CHOICES = (
    ('text', 'Text'),
    ('file', 'File'),
    ('image', 'Image'),
    ('video', 'Video'),
    ('audio', 'Audio'),
    ('event', 'Event'),
    ('task', 'Task'),
    ('resource', 'Resource'),
    ('announcement', 'Announcement'),
)


class RoomChat(models.Model):
    """Chat messages for rooms - WhatsApp-like functionality"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='chats')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='room_chats')
    
    content = models.TextField(max_length=5000, blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    status = models.CharField(max_length=20, choices=MESSAGE_STATUS_CHOICES, default='sent')
    
    # Files (supports multiple)
    files = models.ManyToManyField(RoomChatFile, blank=True, related_name='chat_messages')
    
    # Entity references for sharing
    event = models.ForeignKey('Events.Event', null=True, blank=True, on_delete=models.SET_NULL, related_name='shared_in_chats')
    task = models.ForeignKey('Announcements.Task', null=True, blank=True, on_delete=models.SET_NULL, related_name='shared_in_chats')
    resource = models.ForeignKey('Resources.Resource', null=True, blank=True, on_delete=models.SET_NULL, related_name='shared_in_chats')
    announcement = models.ForeignKey('Announcements.Announcements', null=True, blank=True, on_delete=models.SET_NULL, related_name='shared_in_chats')
    
    # Forwarding info
    is_forwarded = models.BooleanField(default=False)
    forwarded_from_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name='forwarded_chats')
    forwarded_from_user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='forwarded_by_user')
    original_chat = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='forwards')
    
    # Reply to another message
    reply_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    
    # Timestamps
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Read tracking - for delivery/read receipts
    read_by = models.ManyToManyField(CustomUser, blank=True, related_name='read_room_chats')
    delivered_to = models.ManyToManyField(CustomUser, blank=True, related_name='delivered_room_chats')
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['room', 'is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.sender.first_name} in {self.room.name}: {self.content[:50]}..."
