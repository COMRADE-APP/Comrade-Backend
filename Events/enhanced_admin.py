"""
Admin configuration for enhanced Events models
"""
from django.contrib import admin
from Events.enhanced_models import (
    EventRoom, EventResourceAccess, EventResourcePurchase,
    EventInterest, EventReaction, EventComment, EventPin,
    EventRepost, EventShare, EventSocialLink, EventBlock,
    EventUserReport, EventTicketPurchase, EventBrowserReminder,
    EventEmailReminder, EventToAnnouncementConversion,
    EventHelpRequest, EventHelpResponse, EventPermission
)


@admin.register(EventRoom)
class EventRoomAdmin(admin.ModelAdmin):
    list_display = ['event', 'room', 'is_active', 'expires_at', 'created_at']
    list_filter = ['is_active', 'auto_expire', 'requires_ticket']
    search_fields = ['event__name', 'room__name']
    date_hierarchy = 'created_at'


@admin.register(EventResourceAccess)
class EventResourceAccessAdmin(admin.ModelAdmin):
    list_display = ['event', 'resource', 'access_type', 'price', 'view_count', 'download_count']
    list_filter = ['access_type', 'payment_required']
    search_fields = ['event__name']


@admin.register(EventResourcePurchase)
class EventResourcePurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'resource_access', 'amount_paid', 'payment_option', 'purchased_at']
    list_filter = ['payment_option', 'purchased_at']
    search_fields = ['user__email']
    date_hierarchy = 'purchased_at'


@admin.register(EventInterest)
class EventInterestAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'interested', 'notify_updates', 'marked_at']
    list_filter = ['interested', 'notify_updates']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'marked_at'


@admin.register(EventReaction)
class EventReactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'reaction_type', 'created_at']
    list_filter = ['reaction_type']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'created_at'


@admin.register(EventComment)
class EventCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'content_preview', 'is_visible', 'is_pinned', 'created_at']
    list_filter = ['is_visible', 'is_pinned', 'is_edited']
    search_fields = ['user__email', 'event__name', 'content']
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(EventPin)
class EventPinAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'pinned_at']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'pinned_at'


@admin.register(EventRepost)
class EventRepostAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'caption_preview', 'reposted_at']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'reposted_at'
    
    def caption_preview(self, obj):
        return obj.caption[:30] + '...' if len(obj.caption) > 30 else obj.caption
    caption_preview.short_description = 'Caption'


@admin.register(EventShare)
class EventShareAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'share_type', 'shared_at']
    list_filter = ['share_type']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'shared_at'


@admin.register(EventSocialLink)
class EventSocialLinkAdmin(admin.ModelAdmin):
    list_display = ['event', 'platform', 'token_preview', 'clicks', 'created_at']
    list_filter = ['platform']
    search_fields = ['event__name', 'token']
    
    def token_preview(self, obj):
        return obj.token[:20] + '...' if len(obj.token) > 20 else obj.token
    token_preview.short_description = 'Token'


@admin.register(EventBlock)
class EventBlockAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'blocked_at']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'blocked_at'


@admin.register(EventUserReport)
class EventUserReportAdmin(admin.ModelAdmin):
    list_display = ['event', 'reporter', 'report_type', 'status', 'reported_at']
    list_filter = ['report_type', 'status']
    search_fields = ['event__name', 'reporter__email', 'description']
    date_hierarchy = 'reported_at'
    
    actions = ['mark_resolved', 'mark_dismissed']
    
    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved', reviewed_at=timezone.now(), reviewed_by=request.user)
    mark_resolved.short_description = 'Mark selected reports as resolved'
    
    def mark_dismissed(self, request, queryset):
        queryset.update(status='dismissed', reviewed_at=timezone.now(), reviewed_by=request.user)
    mark_dismissed.short_description = 'Mark selected reports as dismissed'


@admin.register(EventTicketPurchase)
class EventTicketPurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'ticket', 'quantity', 'total_price', 'payment_status', 'purchased_at']
    list_filter = ['payment_status', 'payment_option', 'is_used']
    search_fields = ['user__email', 'ticket__event__name']
    date_hierarchy = 'purchased_at'


@admin.register(EventBrowserReminder)
class EventBrowserReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'remind_at', 'sent', 'created_at']
    list_filter = ['sent']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'remind_at'


@admin.register(EventEmailReminder)
class EventEmailReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'remind_at', 'email_sent', 'created_at']
    list_filter = ['email_sent']
    search_fields = ['user__email', 'event__name']
    date_hierarchy = 'remind_at'


@admin.register(EventToAnnouncementConversion)
class EventConversionAdmin(admin.ModelAdmin):
    list_display = ['event', 'announcement', 'converted_by', 'retain_event', 'converted_at']
    list_filter = ['retain_event']
    search_fields = ['event__name']
    date_hierarchy = 'converted_at'


@admin.register(EventHelpRequest)
class EventHelpRequestAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'subject', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority']
    search_fields = ['event__name', 'user__email', 'subject', 'message']
    date_hierarchy = 'created_at'


@admin.register(EventHelpResponse)
class EventHelpResponseAdmin(admin.ModelAdmin):
    list_display = ['request', 'responder', 'is_solution', 'created_at']
    list_filter = ['is_solution']
    search_fields = ['request__subject', 'responder__email']
    date_hierarchy = 'created_at'


@admin.register(EventPermission)
class EventPermissionAdmin(admin.ModelAdmin):
    list_display = ['event', 'user', 'can_edit', 'can_manage_tickets', 'can_manage_room', 'granted_at']
    list_filter = ['can_edit', 'can_delete', 'can_manage_tickets', 'can_manage_room']
    search_fields = ['event__name', 'user__email']
    date_hierarchy = 'granted_at'


# Ensure timezone is imported
from django.utils import timezone
