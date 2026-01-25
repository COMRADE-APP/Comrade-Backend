from django.db import models
from django.utils import timezone
from django.conf import settings


class Conversation(models.Model):
    """
    Represents a conversation between two or more users.
    For DMs, this will have exactly 2 participants.
    """
    CONVERSATION_TYPES = [
        ('dm', 'Direct Message'),
        ('group', 'Group Chat'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending Request'),
        ('archived', 'Archived'),
        ('blocked', 'Blocked'),
    ]
    
    conversation_type = models.CharField(max_length=10, choices=CONVERSATION_TYPES, default='dm')
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='dm_conversations'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For group chats
    name = models.CharField(max_length=100, blank=True)
    icon = models.ImageField(upload_to='chat_icons/', blank=True, null=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.conversation_type == 'dm':
            participants = list(self.participants.all()[:2])
            if len(participants) == 2:
                return f"DM: {participants[0].email} <-> {participants[1].email}"
        return f"Conversation {self.id}"
    
    def get_other_participant(self, user):
        """Get the other participant in a DM conversation"""
        return self.participants.exclude(id=user.id).first()
    
    def get_last_message(self):
        return self.messages.order_by('-created_at').first()


class ConversationParticipant(models.Model):
    """
    Stores per-user conversation settings and status
    """
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='participant_details'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='dm_participant_details'
    )
    
    # Request status - only relevant for the receiver
    is_request = models.BooleanField(default=False)  # True if this is a message request for this user
    request_accepted = models.BooleanField(default=False)
    
    # Muting and notifications
    is_muted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)
    
    # Pinned conversation
    is_pinned = models.BooleanField(default=False)
    
    # Archive status per user
    is_archived = models.BooleanField(default=False)
    
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['conversation', 'user']
    
    def __str__(self):
        return f"{self.user.email} in conversation {self.conversation.id}"
    
    def get_unread_count(self):
        if not self.last_read_at:
            return self.conversation.messages.exclude(sender=self.user).count()
        return self.conversation.messages.filter(
            created_at__gt=self.last_read_at
        ).exclude(sender=self.user).count()


class Message(models.Model):
    """
    Individual message within a conversation
    """
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('file', 'File'),
        ('system', 'System Message'),
    ]
    
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='sent_dm_messages'
    )
    
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True)
    
    # Media attachment
    media = models.FileField(upload_to='message_media/', blank=True, null=True)
    media_thumbnail = models.ImageField(upload_to='message_thumbnails/', blank=True, null=True)
    
    # Reply to another message
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    # Reactions (stored as JSON: {"emoji": [user_id, user_id]})
    reactions = models.JSONField(default=dict, blank=True)
    
    # Status
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender} at {self.created_at}"


class MessageRead(models.Model):
    """
    Tracks read receipts for messages
    """
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='read_receipts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    read_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['message', 'user']


class UserMessagingSettings(models.Model):
    """
    User's messaging preferences
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messaging_settings'
    )
    
    # Who can send messages
    MESSAGE_PERMISSION_CHOICES = [
        ('everyone', 'Everyone'),
        ('followers', 'Followers Only'),
        ('following', 'People I Follow'),
        ('mutual', 'Mutual Followers Only'),
        ('nobody', 'Nobody'),
    ]
    
    allow_messages_from = models.CharField(
        max_length=20, 
        choices=MESSAGE_PERMISSION_CHOICES, 
        default='everyone'
    )
    
    # Read receipts
    show_read_receipts = models.BooleanField(default=True)
    
    # Online status
    show_online_status = models.BooleanField(default=True)
    
    # Auto-accept from circles (mutual followers)
    auto_accept_circles = models.BooleanField(default=True)
    
    # Notification sound
    notification_sound = models.CharField(max_length=50, default='default')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Messaging settings for {self.user.email}"
