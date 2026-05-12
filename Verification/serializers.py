"""
Verification Serializers for all entity types
"""
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import (
    EntityVerificationRequest, EntityBasicInfo, EntityLocation,
    EntityContact, EntityRegistration, EntityTaxInfo,
    EntityIdentification, VerificationDocument, VerificationActivity,
    LivenessVerification, VerificationVideo, VerificationChecklist
)


class EntityBasicInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityBasicInfo
        fields = '__all__'


class EntityLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityLocation
        fields = '__all__'


class EntityContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityContact
        fields = '__all__'


class EntityRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityRegistration
        fields = '__all__'


class EntityTaxInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityTaxInfo
        fields = '__all__'


class EntityIdentificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityIdentification
        fields = '__all__'
        read_only_fields = ('is_verified', 'verified_by', 'verified_at', 'verification_notes')


class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = '__all__'
        read_only_fields = ('verified', 'verified_by', 'verified_at', 'virus_scanned', 'is_safe')


class LivenessVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LivenessVerification
        fields = '__all__'
        read_only_fields = ('session_id', 'liveness_score', 'liveness_verified', 
                          'face_detected', 'multiple_faces', 'screen_recording_detected',
                          'mask_detected', 'completed_at', 'error_message')


class VerificationVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationVideo
        fields = '__all__'


class VerificationChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationChecklist
        fields = '__all__'


class VerificationActivitySerializer(serializers.ModelSerializer):
    performed_by_username = serializers.CharField(source='performed_by.username', read_only=True)
    
    class Meta:
        model = VerificationActivity
        fields = '__all__'


class EntityVerificationRequestSerializer(serializers.ModelSerializer):
    basic_info = EntityBasicInfoSerializer()
    location = EntityLocationSerializer()
    contact = EntityContactSerializer()
    registration = EntityRegistrationSerializer()
    tax_info = EntityTaxInfoSerializer()
    identifications = EntityIdentificationSerializer(many=True)
    activities = VerificationActivitySerializer(many=True, read_only=True)
    checklist = VerificationChecklistSerializer(many=True, read_only=True)
    
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)
    
    class Meta:
        model = EntityVerificationRequest
        fields = '__all__'
        read_only_fields = ('status', 'reviewer', 'reviewed_at', 'is_verified', 
                          'verified_at', 'verification_badge', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        basic_info_data = validated_data.pop('basic_info', {})
        location_data = validated_data.pop('location', {})
        contact_data = validated_data.pop('contact', {})
        registration_data = validated_data.pop('registration', {})
        tax_info_data = validated_data.pop('tax_info', {})
        identifications_data = validated_data.pop('identifications', [])
        
        verification_request = EntityVerificationRequest.objects.create(**validated_data)
        
        if basic_info_data:
            EntityBasicInfo.objects.create(verification_request=verification_request, **basic_info_data)
        if location_data:
            EntityLocation.objects.create(verification_request=verification_request, **location_data)
        if contact_data:
            EntityContact.objects.create(verification_request=verification_request, **contact_data)
        if registration_data:
            EntityRegistration.objects.create(verification_request=verification_request, **registration_data)
        if tax_info_data:
            EntityTaxInfo.objects.create(verification_request=verification_request, **tax_info_data)
        
        for id_data in identifications_data:
            EntityIdentification.objects.create(verification_request=verification_request, **id_data)
        
        VerificationActivity.objects.create(
            verification_request=verification_request,
            action='created',
            performed_by=verification_request.submitted_by,
            details={'entity_type': verification_request.entity_type}
        )
        
        return verification_request


class EntityVerificationRequestCreateSerializer(serializers.Serializer):
    entity_type = serializers.ChoiceField(choices=[
        ('group', 'Group'), ('business', 'Business'), ('shop', 'Shop'),
        ('personal', 'Personal'), ('creator', 'Creator'), ('tutor', 'Tutor'),
        ('course', 'Course')
    ])
    
    name = serializers.CharField(max_length=300)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    
    entity_type_specific = serializers.DictField(required=False)
    
    country = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100)
    address = serializers.CharField(max_length=500)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_virtual = serializers.BooleanField(default=False)
    virtual_link = serializers.URLField(required=False, allow_blank=True)
    
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20)
    website = serializers.URLField(required=False, allow_blank=True)
    social_media = serializers.DictField(required=False)
    
    registration_number = serializers.CharField(max_length=100)
    year_established = serializers.IntegerField(required=False, allow_null=True)
    legal_name = serializers.CharField(max_length=300, required=False, allow_blank=True)
    jurisdiction = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    has_tax_id = serializers.BooleanField(default=False)
    tax_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    tax_system = serializers.CharField(max_length=50, required=False, allow_blank=True)
    tax_jurisdiction = serializers.CharField(max_length=100, required=False, allow_blank=True)
    vat_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    GST_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    identifications = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class EntityVerificationRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityVerificationRequest
        fields = ('status', 'rejection_reason', 'additional_info_request', 'is_verified')


class StaffVerificationReviewSerializer(serializers.ModelSerializer):
    basic_info = EntityBasicInfoSerializer(read_only=True)
    location = EntityLocationSerializer(read_only=True)
    contact = EntityContactSerializer(read_only=True)
    registration = EntityRegistrationSerializer(read_only=True)
    tax_info = EntityTaxInfoSerializer(read_only=True)
    identifications = EntityIdentificationSerializer(many=True, read_only=True)
    videos = VerificationVideoSerializer(many=True, read_only=True)
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    checklist = VerificationChecklistSerializer(many=True, read_only=True)
    activities = VerificationActivitySerializer(many=True, read_only=True)
    
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    reviewer_username = serializers.CharField(source='reviewer.username', read_only=True)
    
    class Meta:
        model = EntityVerificationRequest
        fields = '__all__'


class LivenessInitiationSerializer(serializers.Serializer):
    verification_request_id = serializers.UUIDField()


class LivenessCompletionSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    video_data = serializers.FileField(required=False)
    
    face_detected = serializers.BooleanField()
    multiple_faces = serializers.BooleanField()
    screen_recording_detected = serializers.BooleanField()
    mask_detected = serializers.BooleanField()
    liveness_score = serializers.FloatField()


class BulkVerificationActionSerializer(serializers.Serializer):
    verification_ids = serializers.ListField(child=serializers.UUIDField())
    action = serializers.ChoiceField(choices=['approve', 'reject', 'request_info'])
    notes = serializers.CharField(required=False, allow_blank=True)