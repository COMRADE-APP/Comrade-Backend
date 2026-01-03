"""
Admin configuration for Verification app
"""
from django.contrib import admin
from Verification.models import (
    InstitutionVerificationRequest,
    OrganizationVerificationRequest,
    VerificationDocument,
    EmailVerification,
    WebsiteVerification,
    VerificationActivity,
)


@admin.register(InstitutionVerificationRequest)
class InstitutionVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['institution_name', 'institution_type', 'status', 'submitted_by', 'created_at']
    list_filter = ['status', 'institution_type', 'country']
    search_fields = ['institution_name', 'official_email', 'registration_number']
    readonly_fields = ['id', 'created_at', 'updated_at', 'submitted_at', 'reviewed_at', 'activated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('institution_name', 'institution_type', 'description')
        }),
        ('Location', {
            'fields': ('country', 'state', 'city', 'address', 'postal_code')
        }),
        ('Contact Information', {
            'fields': ('official_email', 'official_website', 'phone_number')
        }),
        ('Registration', {
            'fields': ('registration_number', 'year_established')
        }),
        ('Verification Status', {
            'fields': ('status', 'submitted_by', 'reviewer', 'reviewed_at', 'rejection_reason', 'additional_info_request')
        }),
        ('Activation', {
            'fields': ('institution', 'activated_at')
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        queryset.update(status='approved', reviewer=request.user)
    approve_requests.short_description = 'Approve selected verification requests'
    
    def reject_requests(self, request, queryset):
        queryset.update(status='rejected', reviewer=request.user)
    reject_requests.short_description = 'Reject selected verification requests'


@admin.register(OrganizationVerificationRequest)
class OrganizationVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['organization_name', 'organization_type', 'status', 'submitted_by', 'created_at']
    list_filter = ['status', 'organization_type', 'country']
    search_fields = ['organization_name', 'official_email', 'registration_number']
    readonly_fields = ['id', 'created_at', 'updated_at', 'submitted_at', 'reviewed_at', 'activated_at']
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        queryset.update(status='approved', reviewer=request.user)
    approve_requests.short_description = 'Approve selected verification requests'
    
    def reject_requests(self, request, queryset):
        queryset.update(status='rejected', reviewer=request.user)
    reject_requests.short_description = 'Reject selected verification requests'


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ['document_name', 'document_type', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'virus_scanned', 'is_safe']
    search_fields = ['document_name', 'file_hash']
    readonly_fields = ['file_hash', 'file_size', 'uploaded_at']


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
    list_display = ['action', 'performed_by', 'timestamp']
    list_filter = ['action']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        return False  # Activity is auto-generated
