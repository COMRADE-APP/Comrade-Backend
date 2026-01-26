from django.contrib import admin
from .models import Conversation, ConversationParticipant, Message, MessageRead, UserMessagingSettings


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation_type', 'created_at', 'updated_at']
    list_filter = ['conversation_type']
    search_fields = ['participants__email', 'name']
    filter_horizontal = ['participants']


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'user', 'is_request', 'request_accepted', 'is_muted', 'is_pinned']
    list_filter = ['is_request', 'request_accepted', 'is_muted', 'is_pinned', 'is_archived']
    search_fields = ['user__email']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'message_type', 'content_preview', 'created_at']
    list_filter = ['message_type', 'is_deleted', 'is_edited']
    search_fields = ['content', 'sender__email']
    
    def content_preview(self, obj):
        return obj.content[:50] if obj.content else ''
    content_preview.short_description = 'Content'


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'user', 'read_at']
    search_fields = ['user__email']


@admin.register(UserMessagingSettings)
class UserMessagingSettingsAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'allow_messages_from', 'auto_accept_circles']
    list_filter = ['allow_messages_from', 'auto_accept_circles']
    search_fields = ['user__email']
