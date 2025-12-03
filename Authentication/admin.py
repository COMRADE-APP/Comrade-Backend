from django.contrib import admin
from .models import (
    CustomUser, Student, StudentAdmin, Lecturer, 
    OrgStaff, OrgAdmin, InstStaff, InstAdmin, 
    Profile, ComradeAdmin, Author, Editor, Moderator
)


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type']
    list_filter = ['user_type', 'is_staff', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']


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