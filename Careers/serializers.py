"""
Careers Serializers
"""
from rest_framework import serializers
from .models import Gig, GigApplication, CareerOpportunity, CareerApplication, UserCareerPreference


class GigSerializer(serializers.ModelSerializer):
    creator_name = serializers.SerializerMethodField()
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = Gig
        fields = [
            'id', 'creator', 'creator_name', 'title', 'description', 'requirements',
            'pay_amount', 'pay_timing', 'industry', 'deadline', 'location',
            'is_remote', 'status', 'assigned_to', 'applications_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def get_creator_name(self, obj):
        return f"{obj.creator.first_name} {obj.creator.last_name}".strip() or obj.creator.email

    def get_applications_count(self, obj):
        return obj.applications.count()


class GigCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gig
        fields = ['id', 'title', 'description', 'requirements', 'pay_amount', 'pay_timing', 
                  'industry', 'deadline', 'location', 'is_remote']
        read_only_fields = ['id']


class GigApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = GigApplication
        fields = ['id', 'gig', 'applicant', 'applicant_name', 'cover_letter', 
                  'proposed_rate', 'status', 'created_at']
        read_only_fields = ['id', 'applicant', 'created_at']

    def get_applicant_name(self, obj):
        return f"{obj.applicant.first_name} {obj.applicant.last_name}".strip() or obj.applicant.email


class CareerOpportunitySerializer(serializers.ModelSerializer):
    salary_range = serializers.ReadOnlyField()
    applications_count = serializers.SerializerMethodField()

    class Meta:
        model = CareerOpportunity
        fields = [
            'id', 'organization_id', 'institution_id', 'company_name', 'posted_by',
            'title', 'description', 'requirements', 'responsibilities',
            'salary_min', 'salary_max', 'salary_currency', 'salary_range',
            'location', 'is_remote', 'job_type', 'experience_level', 'industry',
            'application_deadline', 'is_active', 'applications_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'posted_by', 'created_at', 'updated_at']

    def get_applications_count(self, obj):
        return obj.applications.count()


class CareerOpportunityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerOpportunity
        fields = [
            'id', 'organization_id', 'institution_id', 'company_name',
            'title', 'description', 'requirements', 'responsibilities',
            'salary_min', 'salary_max', 'salary_currency',
            'location', 'is_remote', 'job_type', 'experience_level', 'industry',
            'application_deadline'
        ]
        read_only_fields = ['id']


class CareerApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = CareerApplication
        fields = ['id', 'career', 'applicant', 'applicant_name', 'cover_letter', 
                  'resume', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'applicant', 'created_at', 'updated_at']

    def get_applicant_name(self, obj):
        return f"{obj.applicant.first_name} {obj.applicant.last_name}".strip() or obj.applicant.email


class UserCareerPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCareerPreference
        fields = [
            'interest_type', 'industries', 'skills', 'preferred_pay_min',
            'preferred_pay_max', 'preferred_job_types', 'is_remote_only',
            'preferred_locations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
