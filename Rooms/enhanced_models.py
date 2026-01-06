from django.db import models
from Authentication.models import CustomUser
from Rooms.models import Room
from datetime import datetime
import uuid


class RoomMembership(models.Model):
    """Enhanced room membership with detailed roles and permissions"""
    
    ROOM_ROLES = (
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
        ('viewer', 'Viewer'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='detailed_memberships')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='detailed_room_memberships')
    
    role = models.CharField(max_length=50, choices=ROOM_ROLES, default='member')
    
    # Granular Permissions
    can_post_text = models.BooleanField(default=True)
    can_post_announcements = models.BooleanField(default=False)
    can_create_tasks = models.BooleanField(default=False)
    can_create_events = models.BooleanField(default=False)
    can_upload_resources = models.BooleanField(default=False)
    can_pin = models.BooleanField(default=False)
    can_delete_own = models.BooleanField(default=True)
    can_delete_others = models.BooleanField(default=False)
    can_invite_members = models.BooleanField(default=False)
    can_remove_members = models.BooleanField(default=False)
    can_change_roles = models.BooleanField(default=False)
    can_moderate_chat = models.BooleanField(default=False)
    can_manage_room_settings = models.BooleanField(default=False)
    
    # Status
    joined_at = models.DateTimeField(default=datetime.now)
    invited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='room_invites_sent')
    
    class Meta:
        unique_together = ['room', 'user']
        indexes = [
            models.Index(fields=['room', 'role']),
            models.Index(fields=['user', 'joined_at']),
        ]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.room.name} ({self.get_role_display()})"


class RoomAccessControl(models.Model):
    """Password and access control for rooms"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name='access_control')
    
    # Access Level
    access_level = models.CharField(max_length=50, choices=(
        ('public', 'Public - Anyone can join'),
        ('members_only', 'Members Only'),
        ('invite_only', 'Invite Only'),
        ('password_protected', 'Password Protected'),
        ('approval_required', 'Requires Admin Approval'),
    ), default='members_only')
    
    # Password Protection
    requires_password = models.BooleanField(default=False)
    access_password = models.CharField(max_length=255, blank=True)  # Hashed password
    password_hint = models.CharField(max_length=200, blank=True)
    
    # IP Restrictions (optional)
    allowed_ip_ranges = models.JSONField(default=list, blank=True)
    blocked_ip_addresses = models.JSONField(default=list, blank=True)
    
    # Time-based access
    access_schedule = models.JSONField(default=dict, blank=True)  # {days: [], hours: []}
    
    # Verification requirements
    requires_verified_email = models.BooleanField(default=False)
    requires_verified_credentials = models.BooleanField(default=False)
    minimum_account_age_days = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.room.name} - {self.get_access_level_display()}"


class RoomPasswordAccess(models.Model):
    """Track password-based room access attempts"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='password_accesses')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    success = models.BooleanField(default=False)
    accessed_at = models.DateTimeField(default=datetime.now)
    ip_address = models.GenericIPAddressField()
    
    class Meta:
        indexes = [
            models.Index(fields=['room', 'success']),
            models.Index(fields=['user', 'accessed_at']),
        ]
        ordering = ['-accessed_at']


class RoomFeatureSettings(models.Model):
    """Control which features are enabled for a room"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.OneToOneField(Room, on_delete=models.CASCADE, related_name='feature_settings')
    
    # Feature Toggles
    has_chat = models.BooleanField(default=True)
    has_announcements = models.BooleanField(default=True)
    has_tasks = models.BooleanField(default=True)
    has_events = models.BooleanField(default=True)
    has_resources = models.BooleanField(default=True)
    has_polls = models.BooleanField(default=True)
    has_file_sharing = models.BooleanField(default=True)
    has_voice_chat = models.BooleanField(default=False)
    has_video_chat = models.BooleanField(default=False)
    has_screen_sharing = models.BooleanField(default=False)
    
    # Chat Settings
    chat_history_visible = models.BooleanField(default=True)
    chat_history_retention_days = models.IntegerField(default=365)
    max_message_length = models.IntegerField(default=5000)
    allow_message_editing = models.BooleanField(default=True)
    allow_message_deletion = models.BooleanField(default=True)
    
    # File Sharing Settings
    max_file_size_mb = models.IntegerField(default=50)
    allowed_file_types = models.JSONField(default=list, blank=True)
    
    # Moderation
    profanity_filter_enabled = models.BooleanField(default=False)
    requires_message_approval = models.BooleanField(default=False)
    slow_mode_seconds = models.IntegerField(default=0)  # 0 = disabled
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Features for {self.room.name}"


class RoomHierarchy(models.Model):
    """Manage parent-child relationships between rooms"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent_room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='child_relationships')
    child_room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='parent_relationships')
    
    relationship_type = models.CharField(max_length=50, choices=(
        ('subcategory', 'Subcategory'),
        ('related', 'Related Topic'),
        ('departmental', 'Department Child'),
        ('project', 'Project Room'),
    ), default='subcategory')
    
    inherit_members = models.BooleanField(default=False)
    inherit_permissions = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['parent_room', 'child_room']
        indexes = [
            models.Index(fields=['parent_room']),
            models.Index(fields=['child_room']),
        ]
    
    def __str__(self):
        return f"{self.parent_room.name} > {self.child_room.name}"


class RoomResource(models.Model):
    """Room-specific resource association with access control"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='private_room_resources')
    resource = models.ForeignKey('Resources.Resource', on_delete=models.CASCADE)
    
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(default=datetime.now)
    
    access_level = models.CharField(max_length=50, choices=(
        ('admins', 'Admins Only'),
        ('moderators', 'Admins & Moderators'),
        ('members', 'All Members'),
        ('public', 'Public'),
    ), default='members')
    
    is_pinned = models.BooleanField(default=False)
    pin_order = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['room', 'resource']
        indexes = [
            models.Index(fields=['room', 'is_pinned']),
            models.Index(fields=['room', 'uploaded_at']),
        ]
        ordering = ['-is_pinned', '-pin_order', '-uploaded_at']
    
    def __str__(self):
        return f"{self.resource} in {self.room.name}"


class RoomAnnouncement(models.Model):
    """Room-specific announcement tracking"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_announcement_items')
    announcement = models.ForeignKey('Announcements.Announcements', on_delete=models.CASCADE)
    
    pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)
    pinned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='pinned_announcements')
    
    posted_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['room', 'announcement']
        indexes = [
            models.Index(fields=['room', 'pinned', '-posted_at']),
        ]
        ordering = ['-pinned', '-posted_at']


class RoomEvent(models.Model):
    """Room-specific event association"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_event_items')
    event = models.ForeignKey('Events.Event', on_delete=models.CASCADE)
    
    is_private = models.BooleanField(default=False)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['room', 'event']
        indexes = [
            models.Index(fields=['room', 'is_private']),
        ]


class RoomTask(models.Model):
    """Room-specific task association"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_task_items')
    task = models.ForeignKey('Announcements.Task', on_delete=models.CASCADE)
    
    assigned_roles = models.JSONField(default=list, blank=True)  # ['admin', 'member', etc.]
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['room', 'task']
        indexes = [
            models.Index(fields=['room', 'created_at']),
        ]
