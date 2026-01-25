"""
Notification Models
Handles notifications for user interactions (likes, comments, follows, etc.)
"""
from django.db import models
from django.utils import timezone
from Authentication.models import CustomUser


NOTIFICATION_TYPES = (
    ('like', 'Like'),
    ('comment', 'Comment'),
    ('follow', 'Follow'),
    ('repost', 'Repost'),
    ('mention', 'Mention'),
    ('reply', 'Reply'),
    ('research_update', 'Research Update'),
    ('article_published', 'Article Published'),
    ('product_update', 'Product Update'),
    ('system', 'System'),
    ('announcement', 'Announcement'),
)


class Notification(models.Model):
    """
    Core notification model for all user notifications
    """
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='actions',
        null=True,
        blank=True
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='system'
    )
    title = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    
    # Generic relation to any content
    content_type = models.CharField(max_length=100, blank=True)  # e.g., 'opinion', 'research', 'article'
    content_id = models.CharField(max_length=100, blank=True)  # ID of the related content
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action URL (where to navigate when clicked)
    action_url = models.CharField(max_length=500, blank=True)
    
    # Metadata
    extra_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} notification for {self.recipient.email}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NotificationPreference(models.Model):
    """
    User preferences for notifications
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notifications
    email_likes = models.BooleanField(default=True)
    email_comments = models.BooleanField(default=True)
    email_follows = models.BooleanField(default=True)
    email_mentions = models.BooleanField(default=True)
    email_reposts = models.BooleanField(default=True)
    email_announcements = models.BooleanField(default=True)
    
    # Push notifications (in-app)
    push_likes = models.BooleanField(default=True)
    push_comments = models.BooleanField(default=True)
    push_follows = models.BooleanField(default=True)
    push_mentions = models.BooleanField(default=True)
    push_reposts = models.BooleanField(default=True)
    push_announcements = models.BooleanField(default=True)
    
    # Digest settings
    email_digest = models.BooleanField(default=False)  # Send daily digest instead of individual emails
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"


# Notification creation helper
def create_notification(
    recipient,
    notification_type,
    message,
    actor=None,
    content_type='',
    content_id='',
    title='',
    action_url='',
    extra_data=None
):
    """
    Helper function to create notifications
    """
    # Don't notify yourself
    if actor and actor.id == recipient.id:
        return None
    
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        content_type=content_type,
        content_id=str(content_id) if content_id else '',
        action_url=action_url,
        extra_data=extra_data or {}
    )
    
    return notification
