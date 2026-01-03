from django.contrib import admin
from .models import UserActivity, ActionLog, ActivitySession


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'description', 'ip_address', 'timestamp']
    list_filter = ['activity_type', 'timestamp']
    search_fields = ['user__email', 'ip_address', 'description']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('User & Activity', {
            'fields': ('user', 'activity_type', 'description')
        }),
        ('Network Information', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'timestamp']
    list_filter = ['timestamp', 'action']
    search_fields = ['user__email', 'action', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Action Details', {
            'fields': ('user', 'action', 'details')
        }),
        ('Network Information', {
            'fields': ('ip_address',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )


@admin.register(ActivitySession)
class ActivitySessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'start_time', 'end_time', 'is_active', 'ip_address']
    list_filter = ['is_active', 'start_time']
    search_fields = ['user__email', 'session_key', 'ip_address']
    readonly_fields = ['start_time']
    date_hierarchy = 'start_time'

