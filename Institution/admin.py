"""
Institution Admin Configuration
Registers all verification and hierarchical models for Django admin
"""
from django.contrib import admin
from Institution.models import (
    # Verification System Models
    Institution,
    InstitutionVerificationDocument,
    InstitutionMember,
    InstitutionVerificationLog,
    WebsiteVerificationRequest,
    Organization,
    # Hierarchical Structure Models
    InstBranch,
    VCOffice,
    Faculty,
    InstDepartment,
    Programme,
    AdminDep,
    RegistrarOffice,
    HR,
    ICT,
    Finance,
    Marketing,
    Legal,
    StudentAffairs,
    Admissions,
    CareerOffice,
    Counselling,
    SupportServices,
    Security,
    Transport,
    Library,
    Cafeteria,
    Hostel,
    HealthServices,
    OtherInstitutionUnit,
)


# ============================================================================
# VERIFICATION SYSTEM ADMIN
# ============================================================================

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ['name', 'institution_type', 'status', 'email_verified', 'created_at']
    list_filter = ['status', 'institution_type', 'email_verified', 'is_active']
    search_fields = ['name', 'email', 'registration_number']
    readonly_fields = ['created_at', 'updated_at', 'verified_at', 'submitted_at']


@admin.register(InstitutionVerificationDocument)
class InstitutionVerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ['institution', 'document_type', 'verified', 'uploaded_at']
    list_filter = ['verified', 'document_type', 'virus_scan_result']
    search_fields = ['institution__name', 'file_name']
    readonly_fields = ['uploaded_at', 'verified_at']


@admin.register(InstitutionMember)
class InstitutionMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'institution', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'invitation_accepted']
    search_fields = ['user__email', 'institution__name']
    readonly_fields = ['joined_at', 'updated_at']


@admin.register(InstitutionVerificationLog)
class InstitutionVerificationLogAdmin(admin.ModelAdmin):
    list_display = ['institution', 'action', 'performed_by', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['institution__name', 'notes']
    readonly_fields = ['timestamp']


@admin.register(WebsiteVerificationRequest)
class WebsiteVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['institution', 'method', 'verified', 'created_at']
    list_filter = ['verified', 'method', 'ssl_valid']
    readonly_fields = ['created_at', 'verified_at']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization_type', 'status', 'email_verified', 'created_at']
    list_filter = ['status', 'organization_type', 'email_verified']
    search_fields = ['name', 'email', 'registration_number']


# ============================================================================
# HIERARCHICAL STRUCTURE ADMIN
# ============================================================================

admin.site.register(InstBranch)
admin.site.register(VCOffice)
admin.site.register(Faculty)
admin.site.register(InstDepartment)
admin.site.register(Programme)
admin.site.register(AdminDep)
admin.site.register(RegistrarOffice)
admin.site.register(HR)
admin.site.register(ICT)
admin.site.register(Finance)
admin.site.register(Marketing)
admin.site.register(Legal)
admin.site.register(StudentAffairs)
admin.site.register(Admissions)
admin.site.register(CareerOffice)
admin.site.register(Counselling)
admin.site.register(SupportServices)
admin.site.register(Security)
admin.site.register(Transport)
admin.site.register(Library)
admin.site.register(Cafeteria)
admin.site.register(Hostel)
admin.site.register(HealthServices)
admin.site.register(OtherInstitutionUnit)
