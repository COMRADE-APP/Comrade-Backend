from django.db import models
from django.conf import settings
import hashlib

class UserDevice(models.Model):
    TRUST_LEVELS = (
        ('trusted', 'Trusted'),
        ('untrusted', 'Untrusted'),
        ('blocked', 'Blocked'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices')
    device_fingerprint = models.CharField(max_length=255, db_index=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Device Info
    device_type = models.CharField(max_length=50, default='unknown')
    browser = models.CharField(max_length=100, blank=True)
    browser_version = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    user_agent = models.TextField()
    
    # Activity
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    last_seen = models.DateTimeField(auto_now=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    trust_level = models.CharField(max_length=20, choices=TRUST_LEVELS, default='untrusted')
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'device_fingerprint')
        
    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.browser})"


class DeviceVerification(models.Model):
    device = models.ForeignKey(UserDevice, on_delete=models.CASCADE)
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)


class DeviceTrustLevel(models.Model):
    """For future dynamic trust scoring"""
    name = models.CharField(max_length=50)
    score_threshold = models.IntegerField(default=0)
