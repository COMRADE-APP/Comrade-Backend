from django.db import models
from django.conf import settings
import uuid


class UserActivity(models.Model):
    ACTIVITY_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('register', 'Register'),
        ('password_change', 'Password Change'),
        ('security', 'Security Update'),
        ('device', 'Device Management'),
        ('search', 'Search'),
        ('page_view', 'Page View'),
        ('interaction', 'User Interaction'),
        ('settings_change', 'Settings Change'),
        ('permission_change', 'Permission Change'),
        ('payment', 'Payment Activity'),
        ('group_action', 'Group Action'),
        ('profile_view', 'Profile View'),
        ('download', 'Download'),
        ('api_request', 'API Request'),
        ('other', 'Other'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='activities')
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # Extra context data
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # API tracking fields (populated by middleware)
    request_method = models.CharField(max_length=10, blank=True, default='')
    endpoint = models.CharField(max_length=500, blank=True, default='')
    status_code = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['endpoint']),
        ]
        
    def __str__(self):
        return f"{self.user} - {self.activity_type} - {self.timestamp}"


class ActionLog(models.Model):
    """Detailed log for specific actions"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']


class ActivitySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


# ============================================================================
# CONSENT & PRIVACY MODELS
# ============================================================================

class PermissionConsent(models.Model):
    """Tracks user consent for specific data collection categories"""
    PERMISSION_TYPES = (
        ('location', 'Location Tracking'),
        ('camera', 'Camera Access'),
        ('microphone', 'Microphone Access'),
        ('contacts', 'Contacts Access'),
        ('phone_number', 'Phone Number'),
        ('online_status', 'Online Status Tracking'),
        ('internet_connection', 'Internet Connection Info'),
        ('search_history', 'Search History'),
        ('activity_logging', 'Activity Logging'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consents')
    permission_type = models.CharField(max_length=50, choices=PERMISSION_TYPES)
    is_granted = models.BooleanField(default=False)
    granted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'permission_type']
        ordering = ['permission_type']
    
    def __str__(self):
        status = "Granted" if self.is_granted else "Revoked"
        return f"{self.user} - {self.permission_type}: {status}"


class DevicePermissionLog(models.Model):
    """Logs permission grants/revocations on user devices"""
    ACTION_CHOICES = (
        ('granted', 'Permission Granted'),
        ('revoked', 'Permission Revoked'),
        ('requested', 'Permission Requested'),
        ('denied', 'Permission Denied'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_permission_logs')
    permission_type = models.CharField(max_length=50)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    device_info = models.JSONField(default=dict, blank=True)  # Device name, OS, browser
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.permission_type} {self.action}"


class ConnectionSecurityLog(models.Model):
    """Tracks network/connection safety information"""
    SECURITY_LEVELS = (
        ('secure', 'Secure'),
        ('warning', 'Warning'),
        ('unsafe', 'Unsafe'),
        ('unknown', 'Unknown'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='connection_logs')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_https = models.BooleanField(default=False)
    is_vpn = models.BooleanField(default=False)
    is_proxy = models.BooleanField(default=False)
    security_level = models.CharField(max_length=20, choices=SECURITY_LEVELS, default='unknown')
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    isp = models.CharField(max_length=200, blank=True)
    user_agent = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"{self.user} - {self.security_level} ({self.ip_address})"


class SearchActivityLog(models.Model):
    """Tracks search queries and results (with consent only)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='search_logs')
    query = models.CharField(max_length=500)
    search_type = models.CharField(max_length=50, default='general')  # general, ai, product, user, etc.
    results_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # filters used, category, etc.
    searched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-searched_at']
    
    def __str__(self):
        return f"{self.user} searched: '{self.query}'"
