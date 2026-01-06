from rest_framework import serializers
from .models import (
    CredentialVerification, UserQualification, BackgroundCheck,
    MembershipRequest, InvitationLink, PresetUserAccount
)
from Authentication.models import CustomUser


class CredentialVerificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    role_display = serializers.CharField(source='get_role_applying_for_display', read_only=True)
    
    class Meta:
        model = CredentialVerification
        fields = [
            'id', 'user', 'user_email', 'role_applying_for', 'role_display',
            'full_name', 'id_document', 'id_type', 'id_number',
            'date_of_birth', 'nationality',
            'qualification_documents', 'cv_resume', 'cover_letter',
            'years_of_experience', 'experience_documents', 'portfolio_url', 'linkedin_url',
            'highest_degree', 'field_of_study', 'alma_mater', 'graduation_year',
            'academic_transcripts', 'publications', 'google_scholar_url', 'orcid',
            'h_index', 'total_citations', 'professional_licenses', 'certifications',
            'references', 'status', 'status_display', 'submitted_at', 'reviewed_at',
            'reviewed_by', 'admin_notes', 'rejection_reason', 'additional_info_request',
            'approved_at', 'expires_at', 'supporting_documents'
        ]
        read_only_fields = ['id', 'submitted_at', 'reviewed_at', 'reviewed_by', 'approved_at']


class CredentialVerificationCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for credential submission"""
    
    class Meta:
        model = CredentialVerification
        fields = [
            'role_applying_for', 'full_name', 'id_document', 'id_type', 'id_number',
            'date_of_birth', 'nationality', 'qualification_documents', 'cv_resume',
            'cover_letter', 'years_of_experience', 'experience_documents',
            'portfolio_url', 'linkedin_url', 'highest_degree', 'field_of_study',
            'alma_mater', 'graduation_year', 'academic_transcripts', 'publications',
            'google_scholar_url', 'orcid', 'h_index', 'total_citations',
            'professional_licenses', 'certifications', 'references', 'supporting_documents'
        ]
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserQualificationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserQualification
        fields = [
            'id', 'user', 'user_email', 'verification', 'qualification_type',
            'title', 'institution', 'field', 'level', 'year_obtained',
            'expiry_date', 'verified', 'verified_at', 'verified_by',
            'document', 'credential_url'
        ]
        read_only_fields = ['id', 'verified_at', 'verified_by']


class BackgroundCheckSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    check_type_display = serializers.CharField(source='get_check_type_display', read_only=True)
    
    class Meta:
        model = BackgroundCheck
        fields = [
            'id', 'user', 'user_email', 'credential_verification',
            'check_type', 'check_type_display', 'status', 'result',
            'notes', 'details', 'requested_at', 'completed_at', 'conducted_by'
        ]
        read_only_fields = ['id', 'requested_at', 'completed_at']


class MembershipRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MembershipRequest
        fields = [
            'id', 'user', 'user_email', 'entity_type', 'entity_id', 'entity_name',
            'role_requested', 'message', 'credentials_submitted', 'approval_token',
            'status', 'status_display', 'requested_at', 'processed_at', 'processed_by',
            'admin_notes', 'rejection_reason'
        ]
        read_only_fields = ['id', 'requested_at', 'processed_at', 'processed_by']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class InvitationLinkSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = InvitationLink
        fields = [
            'id', 'created_by', 'created_by_email', 'entity_type', 'entity_id',
            'entity_name', 'token', 'role_granted', 'max_uses', 'uses_count',
            'expires_at', 'is_active', 'permissions', 'created_at', 'is_valid'
        ]
        read_only_fields = ['id', 'token', 'uses_count', 'created_at']


class InvitationLinkCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating invitations"""
    
    class Meta:
        model = InvitationLink
        fields = [
            'entity_type', 'entity_id', 'entity_name', 'role_granted',
            'max_uses', 'expires_at', 'permissions'
        ]
    
    def create(self, validated_data):
        import secrets
        validated_data['created_by'] = self.context['request'].user
        validated_data['token'] = secrets.token_urlsafe(32)
        return super().create(validated_data)


class PresetUserAccountSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    
    class Meta:
        model = PresetUserAccount
        fields = [
            'id', 'created_by', 'created_by_email', 'email', 'first_name', 'last_name',
            'role', 'preset_password', 'entity_type', 'entity_id', 'entity_name',
            'phone_number', 'user_type', 'activated', 'activated_at',
            'invitation_sent', 'invitation_sent_at', 'user', 'created_at', 'expires_at'
        ]
        read_only_fields = ['id', 'activated_at', 'invitation_sent_at', 'created_at']
        extra_kwargs = {'preset_password': {'write_only': True}}


class PresetUserAccountCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating preset accounts"""
    
    class Meta:
        model = PresetUserAccount
        fields = [
            'email', 'first_name', 'last_name', 'role', 'preset_password',
            'entity_type', 'entity_id', 'entity_name', 'phone_number',
            'user_type', 'expires_at'
        ]
        extra_kwargs = {'preset_password': {'write_only': True}}
    
    def create(self, validated_data):
        from django.contrib.auth.hashers import make_password
        validated_data['created_by'] = self.context['request'].user
        # Hash the preset password
        if 'preset_password' in validated_data:
            validated_data['preset_password'] = make_password(validated_data['preset_password'])
        return super().create(validated_data)