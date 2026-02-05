from django.contrib import admin
from .models import Gig, GigApplication, CareerOpportunity, CareerApplication, UserCareerPreference


@admin.register(Gig)
class GigAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'pay_amount', 'pay_timing', 'industry', 'status', 'created_at')
    search_fields = ('title', 'creator__email', 'description')
    list_filter = ('status', 'industry', 'pay_timing', 'is_remote', 'created_at')


@admin.register(GigApplication)
class GigApplicationAdmin(admin.ModelAdmin):
    list_display = ('gig', 'applicant', 'status', 'created_at')
    search_fields = ('gig__title', 'applicant__email')
    list_filter = ('status', 'created_at')


@admin.register(CareerOpportunity)
class CareerOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'company_name', 'job_type', 'experience_level', 'industry', 'is_active', 'created_at')
    search_fields = ('title', 'company_name', 'description')
    list_filter = ('job_type', 'experience_level', 'industry', 'is_remote', 'is_active', 'created_at')


@admin.register(CareerApplication)
class CareerApplicationAdmin(admin.ModelAdmin):
    list_display = ('career', 'applicant', 'status', 'created_at')
    search_fields = ('career__title', 'applicant__email')
    list_filter = ('status', 'created_at')


@admin.register(UserCareerPreference)
class UserCareerPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'interest_type', 'is_remote_only', 'updated_at')
    search_fields = ('user__email',)
    list_filter = ('interest_type', 'is_remote_only')
