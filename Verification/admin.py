"""
Admin configuration for Verification app
"""
from django.contrib import admin
from Verification.models import (
    EntityVerificationRequest,
    EntityBasicInfo,
    EntityLocation,
    EntityContact,
    EntityRegistration,
    EntityTaxInfo,
    EntityIdentification,
    VerificationDocument,
    VerificationActivity,
    LivenessVerification,
    VerificationVideo,
    VerificationChecklist,
    EmailVerification,
    WebsiteVerification,
)


@admin.register(EntityVerificationRequest)
class EntityVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['entity_type', 'status', 'submitted_by', 'created_at', 'is_verified']
    list_filter = ['status', 'entity_type', 'is_verified']
    search_fields = ['basic_info__name', 'contact__email', 'registration__registration_number']
    readonly_fields = ['id', 'created_at', 'updated_at', 'submitted_at', 'reviewed_at', 'verified_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('entity_type', 'verification_type')
        }),
        ('Status', {
            'fields': ('status', 'submitted_by', 'reviewer', 'reviewed_at', 'is_verified', 'verification_badge')
        }),
        ('Rejection/Notes', {
            'fields': ('rejection_reason', 'additional_info_request')
        }),
    )
    
    actions = ['approve_requests', 'reject_requests', 'mark_as_activated']
    
    def approve_requests(self, request, queryset):
        queryset.update(status='approved', is_verified=True, reviewer=request.user)
    approve_requests.short_description = 'Approve selected verification requests'
    
    def reject_requests(self, request, queryset):
        queryset.update(status='rejected', reviewer=request.user)
    reject_requests.short_description = 'Reject selected verification requests'
    
    def mark_as_activated(self, request, queryset):
        queryset.update(status='activated')
    mark_as_activated.short_description = 'Mark as activated'


@admin.register(EntityBasicInfo)
class EntityBasicInfoAdmin(admin.ModelAdmin):
    list_display = ['name', 'verification_request', 'created_at']
    search_fields = ['name']


@admin.register(EntityLocation)
class EntityLocationAdmin(admin.ModelAdmin):
    list_display = ['city', 'country', 'verification_request']
    list_filter = ['country', 'is_virtual']
    search_fields = ['city', 'address']


@admin.register(EntityContact)
class EntityContactAdmin(admin.ModelAdmin):
    list_display = ['email', 'phone_number', 'verification_request']
    search_fields = ['email', 'phone_number']


@admin.register(EntityRegistration)
class EntityRegistrationAdmin(admin.ModelAdmin):
    list_display = ['registration_number', 'verification_request']
    search_fields = ['registration_number', 'legal_name']


@admin.register(EntityTaxInfo)
class EntityTaxInfoAdmin(admin.ModelAdmin):
    list_display = ['tax_id', 'tax_system', 'verification_request']
    list_filter = ['tax_system', 'vat_registered', 'GST_registered']
    search_fields = ['tax_id', 'vat_number', 'GST_number']


@admin.register(EntityIdentification)
class EntityIdentificationAdmin(admin.ModelAdmin):
    list_display = ['document_number', 'identification_type', 'is_verified', 'verification_request']
    list_filter = ['identification_type', 'is_verified']
    search_fields = ['document_number']
    readonly_fields = ['is_verified', 'verified_by', 'verified_at']


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_name', 'document_type', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'virus_scanned', 'is_safe']
    search_fields = ['document_name', 'file_hash']
    readonly_fields = ['file_hash', 'file_size', 'uploaded_at']


@admin.register(LivenessVerification)
class LivenessVerificationAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'status', 'liveness_verified', 'verification_request', 'created_at']
    list_filter = ['status', 'liveness_verified', 'face_detected']
    readonly_fields = ['session_id', 'verification_token', 'created_at']


@admin.register(VerificationVideo)
class VerificationVideoAdmin(admin.ModelAdmin):
    list_display = ['title', 'video_type', 'is_processed', 'verification_request', 'uploaded_at']
    list_filter = ['video_type', 'is_processed']
    readonly_fields = ['uploaded_at']


@admin.register(VerificationChecklist)
class VerificationChecklistAdmin(admin.ModelAdmin):
    list_display = ['item', 'is_required', 'is_completed', 'verification_request']
    list_filter = ['is_required', 'is_completed']


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'verified', 'verification_attempts', 'expires_at']
    list_filter = ['verified']
    search_fields = ['email']
    readonly_fields = ['verification_token', 'verification_code', 'created_at']


@admin.register(WebsiteVerification)
class WebsiteVerificationAdmin(admin.ModelAdmin):
    list_display = ['website_url', 'verification_method', 'domain_verified', 'is_safe', 'verified_at']
    list_filter = ['verification_method', 'domain_verified', 'is_safe', 'has_ssl']
    search_fields = ['website_url']
    readonly_fields = ['verification_token', 'security_check_result', 'created_at']


@admin.register(VerificationActivity)
class VerificationActivityAdmin(admin.ModelAdmin):
    list_display = ['action', 'performed_by', 'timestamp', 'content_type']
    list_filter = ['action']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        return False