"""
Announcement System Enhancements
Permissions, service conversions, and subscription management
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from Authentication.models import CustomUser
from Announcements.models import Announcements
from datetime import datetime
import uuid


class AnnouncementPermission(models.Model):
    """Control who can create/manage announcements"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    announcement = models.ForeignKey(Announcements, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    # Permissions
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_moderate = models.BooleanField(default=False)
    
    # Role
    ROLES = (
        ('creator', 'Creator'),
        ('admin', 'Administrator'),
        ('moderator', 'Moderator'),
    )
    role = models.CharField(max_length=20, choices=ROLES)
    
    granted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='granted_announcement_permissions')
    granted_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['announcement', 'user']
    
    def __str__(self):
        return f"{self.user.email} - {self.role} - {self.announcement.id}"


class ServiceAnnouncementConversion(models.Model):
    """Track conversions from other services to announcements"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Source service (generic relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    source_service = GenericForeignKey('content_type', 'object_id')
    
    # Source details
    source_type = models.CharField(max_length=50)  # event, post, resource, task, etc.
    source_title = models.CharField(max_length=300)
    
    # Target announcement
    announcement = models.ForeignKey(Announcements, on_delete=models.CASCADE, related_name='conversions')
    
    # Conversion details
    converted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    retain_source = models.BooleanField(default=True)  # Keep original or archive
    
    # Content preservation
    original_content = models.JSONField(default=dict)  # Store original for reference
    
    converted_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['source_type', '-converted_at']),
        ]
    
    def __str__(self):
        return f"{self.source_type} → Announcement ({self.converted_at})"


class AnnouncementSubscription(models.Model):
    """Manage announcement subscriptions and notification preferences"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='announcement_subscriptions')
    announcement = models.ForeignKey(Announcements, on_delete=models.CASCADE, related_name='subscriptions')
    
    # Notification settings
    notification_enabled = models.BooleanField(default=True)
    
    NOTIFICATION_PERIODS = (
        ('immediate', 'Immediate'),
        ('hourly', 'Hourly Digest'),
        ('daily', 'Daily Digest'),
        ('weekly', 'Weekly Digest'),
        ('custom', 'Custom Period'),
    )
    notification_period = models.CharField(max_length=20, choices=NOTIFICATION_PERIODS, default='immediate')
    custom_period_hours = models.IntegerField(null=True, blank=True)  # For custom period
    
    # Notification channels
    notify_in_app = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=True)
    notify_push = models.BooleanField(default=True)  # Browser/mobile push
    
    # Offline notification support (only for announcements)
    offline_notification = models.BooleanField(default=True)
    
    # Subscription tracking
    subscribed_at = models.DateTimeField(default=datetime.now)
    last_notification_sent = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'announcement']
        indexes = [
            models.Index(fields=['user', 'notification_enabled']),
        ]
    
    def __str__(self):
        return f"{self.user.email} → {self.announcement.id} ({self.notification_period})"


class OfflineAnnouncementNotification(models.Model):
    """Queue for offline announcement notifications"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    subscription = models.ForeignKey(AnnouncementSubscription, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcements, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    # Notification details
    notification_type = models.CharField(max_length=20, choices=(
        ('new', 'New Announcement'),
        ('update', 'Announcement Updated'),
        ('reminder', 'Announcement Reminder'),
    ))
    
    # Delivery status
    queued = models.BooleanField(default=True)
    sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery channels
    sent_via_email = models.BooleanField(default=False)
    sent_via_push = models.BooleanField(default=False)
    sent_via_app = models.BooleanField(default=False)
    
    # Retry logic
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    scheduled_for = models.DateTimeField(default=datetime.now)  # When to send based on period
    
    class Meta:
        indexes = [
            models.Index(fields=['queued', 'scheduled_for']),
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['scheduled_for']
    
    def __str__(self):
        return f"Notification for {self.user.email} - {self.notification_type}"
