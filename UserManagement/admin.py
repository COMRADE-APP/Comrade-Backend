from django.contrib import admin
from .models import (
    CredentialVerification, UserQualification, BackgroundCheck,
    MembershipRequest, InvitationLink, PresetUserAccount
)


@admin.register(CredentialVerification)
class CredentialVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'role_applying_for', 'status', 'submitted_at', 'reviewed_by']
    list_filter = ['status', 'role_applying_for', 'submitted_at']
    search_fields = ['user__email', 'full_name', 'id_number']
    readonly_fields = ['id', 'submitted_at', 'approved_at']
    date_hierarchy = 'submitted_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role_applying_for', 'full_name')
        }),
        ('Identity Verification', {
            'fields': ('id_type', 'id_number', 'id_document', 'date_of_birth', 'nationality')
        }),
        ('Qualifications', {
            'fields': ('cv_resume', 'cover_letter', 'qualification_documents', 'supporting_documents')
        }),
        ('Experience', {
            'fields': ('years_of_experience', 'experience_documents', 'portfolio_url', 'linkedin_url', 'references')
        }),
        ('Academic Credentials', {
            'fields': ('highest_degree', 'field_of_study', 'alma_mater', 'graduation_year', 'academic_transcripts'),
            'classes': ('collapse',)
        }),
        ('Publications & Research', {
            'fields': ('publications', 'google_scholar_url', 'orcid', 'h_index', 'total_citations'),
            'classes': ('collapse',)
        }),
        ('Professional Licenses', {
            'fields': ('professional_licenses', 'certifications'),
            'classes': ('collapse',)
        }),
        ('Verification Status', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'approved_at', 'expires_at')
        }),
        ('Feedback', {
            'fields': ('admin_notes', 'rejection_reason', 'additional_info_request'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_credentials', 'reject_credentials', 'request_additional_info']
    
    def approve_credentials(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', reviewed_by=request.user, reviewed_at=timezone.now(), approved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} credential(s) approved successfully.")
    approve_credentials.short_description = "Approve selected credentials"
    
    def reject_credentials(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} credential(s) rejected.")
    reject_credentials.short_description = "Reject selected credentials"
    
    def request_additional_info(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='additional_info_required', reviewed_by=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"Additional info requested for {queryset.count()} credential(s).")
    request_additional_info.short_description = "Request additional information"


@admin.register(UserQualification)
class UserQualificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'qualification_type', 'institution', 'year_obtained', 'verified']
    list_filter = ['qualification_type', 'verified', 'level']
    search_fields = ['user__email', 'title', 'institution']
    readonly_fields = ['id', 'verified_at']
    
    fieldsets = (
        ('Qualification Details', {
            'fields': ('user', 'verification', 'qualification_type', 'title')
        }),
        ('Institution & Field', {
            'fields': ('institution', 'field', 'level', 'year_obtained', 'expiry_date')
        }),
        ('Verification', {
            'fields': ('verified', 'verified_at', 'verified_by', 'document', 'credential_url')
        }),
    )


@admin.register(BackgroundCheck)
class BackgroundCheckAdmin(admin.ModelAdmin):
    list_display = ['user', 'check_type', 'status', 'result', 'requested_at', 'completed_at']
    list_filter = ['check_type', 'status', 'result']
    search_fields = ['user__email']
    readonly_fields = ['id', 'requested_at', 'completed_at']
    date_hierarchy = 'requested_at'
    
    fieldsets = (
        ('Check Details', {
            'fields': ('user', 'credential_verification', 'check_type')
        }),
        ('Status & Results', {
            'fields': ('status', 'result', 'notes', 'details')
        }),
        ('Timeline', {
            'fields': ('requested_at', 'completed_at', 'conducted_by')
        }),
    )


@admin.register(MembershipRequest)
class MembershipRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'entity_name', 'entity_type', 'role_requested', 'status', 'requested_at']
    list_filter = ['entity_type', 'status', 'requested_at']
    search_fields = ['user__email', 'entity_name', 'approval_token']
    readonly_fields = ['id', 'requested_at', 'processed_at']
    
    fieldsets = (
        ('Request Details', {
            'fields': ('user', 'entity_type', 'entity_id', 'entity_name', 'role_requested')
        }),
        ('Message & Credentials', {
            'fields': ('message', 'credentials_submitted', 'approval_token')
        }),
        ('Status', {
            'fields': ('status', 'processed_by', 'processed_at')
        }),
        ('Response', {
            'fields': ('admin_notes', 'rejection_reason')
        }),
    )
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', processed_by=request.user, processed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} request(s) approved.")
    approve_requests.short_description = "Approve selected requests"
    
    def reject_requests(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', processed_by=request.user, processed_at=timezone.now())
        self.message_user(request, f"{queryset.count()} request(s) rejected.")
    reject_requests.short_description = "Reject selected requests"


@admin.register(InvitationLink)
class InvitationLinkAdmin(admin.ModelAdmin):
    list_display = ['entity_name', 'role_granted', 'token', 'uses_count', 'max_uses', 'is_active', 'expires_at']
    list_filter = ['entity_type', 'is_active', 'created_at']
    search_fields = ['entity_name', 'token', 'created_by__email']
    readonly_fields = ['id', 'token', 'created_at']
    
    fieldsets = (
        ('Entity', {
            'fields': ('entity_type', 'entity_id', 'entity_name')
        }),
        ('Invitation Details', {
            'fields': ('created_by', 'role_granted', 'token', 'permissions')
        }),
        ('Usage & Validity', {
            'fields': ('uses_count', 'max_uses', 'expires_at', 'is_active')
        }),
        ('Timeline', {
            'fields': ('created_at',)
        }),
    )


@admin.register(PresetUserAccount)
class PresetUserAccountAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'entity_name', 'activated', 'invitation_sent']
    list_filter = ['activated', 'invitation_sent', 'entity_type', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'entity_name']
    readonly_fields = ['id', 'created_at', 'activated_at', 'invitation_sent_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'user_type', 'role')
        }),
        ('Entity Assignment', {
            'fields': ('entity_type', 'entity_id', 'entity_name')
        }),
        ('Credentials', {
            'fields': ('preset_password',)
        }),
        ('Status', {
            'fields': ('activated', 'activated_at', 'invitation_sent', 'invitation_sent_at', 'user')
        }),
        ('Timeline', {
            'fields': ('created_by', 'created_at', 'expires_at')
        }),
    )
