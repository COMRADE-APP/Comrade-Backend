"""
QomAI Models
Stores chat history, conversations, and user preferences
"""
import uuid
from django.db import models
from django.conf import settings


class Conversation(models.Model):
    """Stores a chat conversation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qomai_conversations'
    )
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.title or 'Untitled'}"


class Message(models.Model):
    """Individual messages in a conversation"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional metadata
    tokens_used = models.IntegerField(null=True, blank=True)
    model_used = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['created_at']


class UserPreference(models.Model):
    """User preferences for QomAI"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qomai_preferences'
    )
    preferred_model = models.CharField(max_length=255, default='qwen-7b')
    context_length = models.IntegerField(default=10)  # How many previous messages to include
    temperature = models.FloatField(default=0.7)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ContentAnalysis(models.Model):
    """Stores results of ML analyses (e.g., fake news detection)"""
    ANALYSIS_TYPES = [
        ('fake_news', 'Fake News Detection'),
        ('sentiment', 'Sentiment Analysis'),
        ('topic', 'Topic Classification'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_analyses'
    )
    analysis_type = models.CharField(max_length=50, choices=ANALYSIS_TYPES)
    input_content = models.TextField()
    result = models.JSONField()
    confidence_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Content analyses'
