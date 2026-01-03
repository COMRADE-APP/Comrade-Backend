"""
Admin configuration for enhanced Announcement models
"""
from django.contrib import admin
from Announcements.enhanced_models import (
    AnnouncementPermission,
    ServiceAnnouncementConversion,
    AnnouncementSubscription,
    OfflineAnnouncementNotification,
)


@admin.register(AnnouncementPermission)
class AnnouncementPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'role', 'can_create', 'can_edit', 'can_delete']
    list_filter = ['role']
    search_fields = ['user__email']


@admin.register(ServiceAnnouncementConversion)
class ServiceAnnouncementConversionAdmin(admin.ModelAdmin):
    list_display = ['source_type', 'source_title', 'announcement', 'converted_by', 'converted_at']
    list_filter = ['source_type', 'retain_source']
    search_fields = ['source_title']
    date_hierarchy = 'converted_at'


@admin.register(AnnouncementSubscription)
class AnnouncementSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'notification_period', 'notification_enabled', 'subscribed_at']
    list_filter = ['notification_enabled', 'notification_period']
    search_fields = ['user__email']


@admin.register(OfflineAnnouncementNotification)
class OfflineAnnouncementNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'queued', 'sent', 'scheduled_for']
    list_filter = ['queued', 'sent', 'notification_type']
    search_fields = ['user__email']
    date_hierarchy = 'scheduled_for'
