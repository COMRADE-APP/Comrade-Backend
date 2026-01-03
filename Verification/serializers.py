from rest_framework import serializers
from Verification.models import (
    InstitutionVerificationRequest,
    OrganizationVerificationRequest,
    VerificationDocument,
    EmailVerification,
    WebsiteVerification,
    VerificationActivity
)
from Authentication.models import CustomUser


class VerificationDocumentSerializer(serializers.ModelSerializer):
    """Serializer for verification documents"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = VerificationDocument
        fields = [
            'id', 'file', 'file_url', 'document_type', 'file_name', 
            'file_size', 'mime_type', 'file_hash', 'is_verified', 
            'is_safe', 'uploaded_at'
        ]
        read_only_fields = ['file_hash', 'file_size', 'mime_type', 'is_verified', 'is_safe', 'uploaded_at']
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class EmailVerificationSerializer(serializers.ModelSerializer):
    """Serializer for email verification"""
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailVerification
        fields = [
            'id', 'email', 'verification_token', 'verification_code',
            'is_verified', 'verified_at', 'expires_at', 'attempts',
            'max_attempts', 'is_expired', 'created_at'
        ]
        read_only_fields = ['verification_token', 'verification_code', 'is_verified', 'verified_at', 'attempts', 'created_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()


class WebsiteVerificationSerializer(serializers.ModelSerializer):
    """Serializer for website verification"""
    
    class Meta:
        model = WebsiteVerification
        fields = [
            'id', 'website_url', 'verification_method', 'verification_token',
            'dns_record_name', 'dns_record_value', 'verification_file_name',
            'verification_file_content', 'meta_tag_content', 'is_verified',
            'verified_at', 'ssl_valid', 'is_safe', 'security_check_result',
            'created_at'
        ]
        read_only_fields = [
            'verification_token', 'dns_record_name', 'dns_record_value',
            'verification_file_name', 'verification_file_content', 'meta_tag_content',
            'is_verified', 'verified_at', 'ssl_valid', 'is_safe', 'security_check_result',
            'created_at'
        ]


class VerificationActivitySerializer(serializers.ModelSerializer):
    """Serializer for verification activity logs"""
    performer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VerificationActivity
        fields = [
            'id', 'action', 'description', 'performer', 'performer_name',
            'old_status', 'new_status', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_performer_name(self, obj):
        if obj.performer:
            return f"{obj.performer.first_name} {obj.performer.last_name}"
        return "System"


class InstitutionVerificationRequestSerializer(serializers.ModelSerializer):
    """Serializer for institution verification requests"""
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    email_verification = EmailVerificationSerializer(read_only=True)
    website_verification = WebsiteVerificationSerializer(read_only=True)
    activities = VerificationActivitySerializer(many=True, read_only=True)
    submitter_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = InstitutionVerificationRequest
        fields = [
            'id', 'institution_name', 'institution_type', 'description',
            'country', 'state', 'city', 'address', 'postal_code',
            'official_email', 'official_phone', 'official_website',
            'registration_number', 'tax_id', 'year_established',
            'accreditation_body', 'accreditation_number',
            'status', 'submission_date', 'review_date', 'activation_date',
            'submitter', 'submitter_name', 'reviewer', 'reviewer_name',
            'reviewer_notes', 'rejection_reason',
            'documents', 'email_verification', 'website_verification', 'activities',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'status', 'submission_date', 'review_date', 'activation_date',
            'submitter', 'reviewer', 'created_at', 'updated_at'
        ]
    
    def get_submitter_name(self, obj):
        if obj.submitter:
            return f"{obj.submitter.first_name} {obj.submitter.last_name}"
        return None
    
    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return f"{obj.reviewer.first_name} {obj.reviewer.last_name}"
        return None


class InstitutionVerificationRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating institution verification requests"""
    
    class Meta:
        model = InstitutionVerificationRequest
        fields = [
            'institution_name', 'institution_type', 'description',
            'country', 'state', 'city', 'address', 'postal_code',
            'official_email', 'official_phone', 'official_website',
            'registration_number', 'tax_id', 'year_established',
            'accreditation_body', 'accreditation_number'
        ]


class OrganizationVerificationRequestSerializer(serializers.ModelSerializer):
    """Serializer for organization verification requests"""
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    email_verification = EmailVerificationSerializer(read_only=True)
    website_verification = WebsiteVerificationSerializer(read_only=True)
    activities = VerificationActivitySerializer(many=True, read_only=True)
    submitter_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganizationVerificationRequest
        fields = [
            'id', 'organization_name', 'organization_type', 'description',
            'country', 'state', 'city', 'address', 'postal_code',
            'official_email', 'official_phone', 'official_website',
            'registration_number', 'tax_id', 'year_established',
            'industry', 'employee_count', 'annual_revenue',
            'status', 'submission_date', 'review_date', 'activation_date',
            'submitter', 'submitter_name', 'reviewer', 'reviewer_name',
            'reviewer_notes', 'rejection_reason',
            'documents', 'email_verification', 'website_verification', 'activities',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'status', 'submission_date', 'review_date', 'activation_date',
            'submitter', 'reviewer', 'created_at', 'updated_at'
        ]
    
    def get_submitter_name(self, obj):
        if obj.submitter:
            return f"{obj.submitter.first_name} {obj.submitter.last_name}"
        return None
    
    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return f"{obj.reviewer.first_name} {obj.reviewer.last_name}"
        return None


class OrganizationVerificationRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating organization verification requests"""
    
    class Meta:
        model = OrganizationVerificationRequest
        fields = [
            'organization_name', 'organization_type', 'description',
            'country', 'state', 'city', 'address', 'postal_code',
            'official_email', 'official_phone', 'official_website',
            'registration_number', 'tax_id', 'year_established',
            'industry', 'employee_count', 'annual_revenue'
        ]


class EmailVerificationCodeSerializer(serializers.Serializer):
    """Serializer for email verification code submission"""
    verification_code = serializers.CharField(max_length=6)


class WebsiteVerificationCheckSerializer(serializers.Serializer):
    """Serializer for triggering website verification check"""
    verification_method = serializers.ChoiceField(choices=['dns', 'file', 'meta_tag'])
