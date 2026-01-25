from django.contrib import admin
from .models import (
    ResearchProject, ParticipantRequirements, ParticipantPosition,
    ResearchParticipant, ParticipantMatching, ResearchGuidelines,
    PeerReview, ResearchPublication, ResearchMilestone
)


@admin.register(ResearchProject)
class ResearchProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'principal_investigator', 'status', 'is_published', 'created_at']
    list_filter = ['status', 'is_published', 'ethics_approved']
    search_fields = ['title', 'abstract', 'principal_investigator__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    filter_horizontal = ['co_investigators']


@admin.register(ParticipantRequirements)
class ParticipantRequirementsAdmin(admin.ModelAdmin):
    list_display = ['research', 'target_participant_count', 'min_age', 'max_age', 'gender']
    list_filter = ['gender', 'min_education_level']
    search_fields = ['research__title']


@admin.register(ParticipantPosition)
class ParticipantPositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'research', 'is_active', 'slots_available', 'slots_filled', 'application_deadline']
    list_filter = ['is_active', 'compensation_type']
    search_fields = ['title', 'research__title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ResearchParticipant)
class ResearchParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'research', 'status', 'consent_given', 'joined_at']
    list_filter = ['status', 'consent_given', 'compensation_paid']
    search_fields = ['user__email', 'research__title']
    readonly_fields = ['id', 'joined_at']


@admin.register(ParticipantMatching)
class ParticipantMatchingAdmin(admin.ModelAdmin):
    list_display = ['participant', 'research', 'match_score', 'notification_sent', 'participant_applied']
    list_filter = ['notification_sent', 'participant_applied']
    search_fields = ['participant__email', 'research__title']
    ordering = ['-match_score']


@admin.register(ResearchGuidelines)
class ResearchGuidelinesAdmin(admin.ModelAdmin):
    list_display = ['research', 'created_at', 'updated_at']
    search_fields = ['research__title']


@admin.register(PeerReview)
class PeerReviewAdmin(admin.ModelAdmin):
    list_display = ['research', 'reviewer', 'status', 'overall_rating', 'recommendation', 'assigned_at']
    list_filter = ['status', 'recommendation']
    search_fields = ['research__title', 'reviewer__email']
    readonly_fields = ['id', 'assigned_at']


@admin.register(ResearchPublication)
class ResearchPublicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'research', 'is_public', 'access_level', 'views', 'downloads', 'published_at']
    list_filter = ['is_public', 'access_level']
    search_fields = ['title', 'research__title']
    readonly_fields = ['id', 'published_at', 'updated_at']


@admin.register(ResearchMilestone)
class ResearchMilestoneAdmin(admin.ModelAdmin):
    list_display = ['title', 'research', 'due_date', 'completed', 'sequence']
    list_filter = ['completed']
    search_fields = ['title', 'research__title']
    ordering = ['research', 'sequence']
