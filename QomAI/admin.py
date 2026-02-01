from django.contrib import admin
from .models import Conversation, Message, UserPreference, ContentAnalysis


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['user__email', 'title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'created_at', 'tokens_used']
    list_filter = ['role', 'created_at']
    search_fields = ['content']
    readonly_fields = ['id', 'created_at']


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'preferred_model', 'context_length', 'temperature']
    search_fields = ['user__email']


@admin.register(ContentAnalysis)
class ContentAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'analysis_type', 'confidence_score', 'created_at']
    list_filter = ['analysis_type', 'created_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at']
