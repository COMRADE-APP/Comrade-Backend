from django.contrib import admin
from .models import UserDevice, DeviceVerification, DeviceTrustLevel


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_name', 'device_type', 'trust_level', 'is_verified', 'last_seen', 'first_seen']
    list_filter = ['trust_level', 'is_verified', 'is_active', 'device_type', 'first_seen']
    search_fields = ['user__email', 'device_name', 'device_fingerprint', 'last_ip', 'browser']
    readonly_fields = ['device_fingerprint', 'user_agent', 'first_seen', 'last_seen']
    
    fieldsets = (
        ('Device Information', {
            'fields': ('user', 'device_name', 'device_type', 'device_fingerprint', 'user_agent')
        }),
        ('Browser & OS', {
            'fields': ('browser', 'browser_version', 'os', 'os_version')
        }),
        ('Trust & Security', {
            'fields': ('trust_level', 'is_verified', 'verified_at', 'revoked_at')
        }),
        ('Network & Activity', {
            'fields': ('last_ip', 'last_seen', 'first_seen', 'is_active')
        }),
    )


@admin.register(DeviceVerification)
class DeviceVerificationAdmin(admin.ModelAdmin):
    list_display = ['device', 'verification_code', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['device__user__email', 'verification_code']
    readonly_fields = ['created_at']


@admin.register(DeviceTrustLevel)
class DeviceTrustLevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'score_threshold']
    search_fields = ['name']

