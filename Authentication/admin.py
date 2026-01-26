from django.contrib import admin
from .models import (
    CustomUser, Student, StudentAdmin, Lecturer, 
    OrgStaff, OrgAdmin, InstStaff, InstAdmin, 
    Profile, ComradeAdmin, Author, Editor, Moderator,
    UserProfile, AccountDeletionRequest, ArchivedUserData, RoleChangeRequest
)


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'account_status', 'is_active']
    list_filter = ['user_type', 'is_staff', 'is_active', 'account_status']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['deletion_requested_at', 'deactivated_at']


class StudentModelAdmin(admin.ModelAdmin):  # Renamed to avoid collision
    list_display = ['admission_number', 'user', 'year_of_study', 'institution', 'course']
    list_filter = ['year_of_study', 'institution']
    search_fields = ['admission_number', 'user__email']


class StudentAdminModelAdmin(admin.ModelAdmin):  # Renamed
    list_display = ['student', 'created_on', 'created_by']
    list_filter = ['created_on']
    search_fields = ['student__user__email']


class LecturerAdmin(admin.ModelAdmin):
    list_display = ['lecturer_id', 'user', 'department', 'institution']
    list_filter = ['institution', 'department']
    search_fields = ['lecturer_id', 'user__email']


class OrgStaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'user', 'current_organisation', 'staff_role']
    list_filter = ['current_organisation', 'staff_role']
    search_fields = ['staff_id', 'user__email']


class OrgAdminModelAdmin(admin.ModelAdmin):  # Renamed
    list_display = ['staff', 'created_on', 'created_by']
    list_filter = ['created_on']
    search_fields = ['staff__user__email']


class InstStaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'user', 'institution', 'staff_role']
    list_filter = ['institution', 'staff_role']
    search_fields = ['staff_id', 'user__email']


class InstAdminModelAdmin(admin.ModelAdmin):  # Renamed
    list_display = ['staff', 'created_on', 'created_by']
    list_filter = ['created_on']
    search_fields = ['staff__user__email']


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user__phone_number', 'location']
    search_fields = ['user__email', 'user__phone_number']


class AuthorAdmin(admin.ModelAdmin):
    list_display = ['user', 'verified', 'created_on']
    list_filter = ['verified', 'created_on']
    search_fields = ['user__email']


class EditorAdmin(admin.ModelAdmin):
    list_display = ['user', 'verified', 'created_on']
    list_filter = ['verified', 'created_on']
    search_fields = ['user__email']


class ModeratorAdmin(admin.ModelAdmin):
    list_display = ['user', 'verified', 'created_on']
    list_filter = ['verified', 'created_on']
    search_fields = ['user__email']


class ComradeAdminAdmin(admin.ModelAdmin):  # Renamed
    list_display = ['user', 'created_on', 'created_by']
    list_filter = ['created_on']
    search_fields = ['user__email']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'location', 'occupation', 'show_email', 'allow_messages', 'updated_at']
    list_filter = ['show_email', 'allow_messages', 'show_activity_status']
    search_fields = ['user__email', 'user__first_name', 'bio', 'location']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ['email', 'user_type', 'status', 'requested_at', 'scheduled_deletion_date', 'reviewed_by']
    list_filter = ['status', 'requested_at']
    search_fields = ['email', 'reason']
    readonly_fields = ['requested_at']
    
    actions = ['approve_deletion', 'reject_deletion']
    
    def approve_deletion(self, request, queryset):
        queryset.update(status='approved', reviewed_by=request.user)
    approve_deletion.short_description = "Approve selected deletion requests"
    
    def reject_deletion(self, request, queryset):
        queryset.update(status='rejected', reviewed_by=request.user)
    reject_deletion.short_description = "Reject selected deletion requests"


@admin.register(ArchivedUserData)
class ArchivedUserDataAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'archived_at', 'archived_by']
    list_filter = ['user_type', 'archived_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['archived_at']


@admin.register(RoleChangeRequest)
class RoleChangeRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_role', 'requested_role', 'status', 'created_on', 'reviewed_by']
    list_filter = ['status', 'requested_role', 'created_on']
    search_fields = ['user__email', 'reason']
    readonly_fields = ['created_on']


# Register all models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Student, StudentModelAdmin)
admin.site.register(StudentAdmin, StudentAdminModelAdmin)
admin.site.register(Lecturer, LecturerAdmin)
admin.site.register(OrgStaff, OrgStaffAdmin)
admin.site.register(OrgAdmin, OrgAdminModelAdmin)
admin.site.register(InstStaff, InstStaffAdmin)
admin.site.register(InstAdmin, InstAdminModelAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Author, AuthorAdmin)
admin.site.register(Editor, EditorAdmin)
admin.site.register(Moderator, ModeratorAdmin)
admin.site.register(ComradeAdmin, ComradeAdminAdmin)