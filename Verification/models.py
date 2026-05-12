"""
Verification Models for Groups, Businesses, Shops, Personal, Creators, Tutors, Courses
Handles secure verification workflow from submission to activation with liveness detection
"""
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from Authentication.models import CustomUser
from Institution.models import Institution
from Organisation.models import Organisation
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets


VERIFICATION_TYPES = (
    ('group', 'Group'),
    ('business', 'Business'),
    ('shop', 'Shop'),
    ('personal', 'Personal'),
    ('creator', 'Creator'),
    ('tutor', 'Tutor'),
    ('course', 'Course'),
    ('institution', 'Institution'),
    ('organization', 'Organization'),
)

VERIFICATION_STATUS = (
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('pending_liveness', 'Pending Liveness Verification'),
    ('liveness_failed', 'Liveness Verification Failed'),
    ('under_review', 'Under Review'),
    ('additional_info', 'Additional Information Requested'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('activated', 'Activated'),
)

ENTITY_TYPES = (
    ('group', 'Group'),
    ('business', 'Business'),
    ('shop', 'Shop'),
    ('personal', 'Personal'),
    ('creator', 'Creator'),
    ('tutor', 'Tutor'),
    ('course', 'Course'),
    ('institution', 'Institution'),
    ('organization', 'Organization'),
)

GROUP_TYPES = (
    ('community', 'Community'),
    ('team', 'Team'),
    ('club', 'Club'),
    ('company', 'Company'),
    ('nonprofit', 'Non-Profit'),
    ('educational', 'Educational'),
    ('other', 'Other'),
)

BUSINESS_TYPES = (
    ('sole_proprietorship', 'Sole Proprietorship'),
    ('partnership', 'Partnership'),
    ('llc', 'Limited Liability Company'),
    ('corporation', 'Corporation'),
    ('nonprofit', 'Non-Profit'),
    ('government', 'Government Entity'),
    ('other', 'Other'),
)

SHOP_TYPES = (
    ('retail', 'Retail Store'),
    ('online', 'Online Store'),
    ('marketplace', 'Marketplace Vendor'),
    ('food', 'Food Service'),
    ('service', 'Service Provider'),
    ('other', 'Other'),
)

CREATOR_TYPES = (
    ('artist', 'Artist'),
    ('musician', 'Musician'),
    ('writer', 'Writer'),
    ('photographer', 'Photographer'),
    ('video_creator', 'Video Creator'),
    ('influencer', 'Influencer'),
    ('educator', 'Educator'),
    ('other', 'Other'),
)

TUTOR_TYPES = (
    ('individual', 'Individual Tutor'),
    ('tutoring_center', 'Tutoring Center'),
    ('online_tutor', 'Online Tutor'),
    ('academic', 'Academic Institution'),
    ('corporate_trainer', 'Corporate Trainer'),
    ('other', 'Other'),
)

COURSE_TYPES = (
    ('academic', 'Academic Course'),
    ('professional', 'Professional Course'),
    ('skill', 'Skill Development'),
    ('language', 'Language Course'),
    ('hobby', 'Hobby Course'),
    ('certification', 'Certification Course'),
    ('other', 'Other'),
)

IDENTIFICATION_TYPES = (
    ('passport', 'Passport'),
    ('national_id', 'National ID'),
    ('drivers_license', 'Driver\'s License'),
    ('voters_id', 'Voter\'s ID'),
    ('business_license', 'Business License'),
    ('tax_certificate', 'Tax Certificate'),
    ('other', 'Other'),
)

TAX_SYSTEM_TYPES = (
    ('vat', 'VAT'),
    ('gst', 'GST'),
    ('sales_tax', 'Sales Tax'),
    ('income_tax', 'Income Tax'),
    ('corporate_tax', 'Corporate Tax'),
    ('other', 'Other'),
)


class VerificationDocument(models.Model):
    """Secure document storage for verification requests"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Generic relation to verification request
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    verification_request = GenericForeignKey('content_type', 'object_id')
    
    # Document Details
    DOCUMENT_TYPES = (
        ('registration', 'Registration Certificate'),
        ('license', 'Operating License'),
        ('tax', 'Tax Document'),
        ('incorporation', 'Incorporation Certificate'),
        ('proof_address', 'Proof of Address'),
        ('accreditation', 'Accreditation Certificate'),
        ('other', 'Other Document'),
    )
    
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    document_name = models.CharField(max_length=200)
    file = models.FileField(upload_to='verification_documents/%Y/%m/')
    file_size = models.IntegerField()  # in bytes
    file_hash = models.CharField(max_length=64)  # SHA-256 hash
    mime_type = models.CharField(max_length=100)
    
    # Verification
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Security
    virus_scanned = models.BooleanField(default=False)
    is_safe = models.BooleanField(default=False)
    
    uploaded_at = models.DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_hash:
            # Generate SHA-256 hash
            hasher = hashlib.sha256()
            for chunk in self.file.chunks():
                hasher.update(chunk)
            self.file_hash = hasher.hexdigest()
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.document_type} - {self.document_name}"


class EmailVerification(models.Model):
    """Email verification for institutions/organizations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Generic relation
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    verification_request = GenericForeignKey('content_type', 'object_id')
    
    email = models.EmailField()
    verification_token = models.CharField(max_length=100, unique=True)
    verification_code = models.CharField(max_length=6)  # 6-digit code
    
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Expiry
    expires_at = models.DateTimeField()
    
    # Tracking
    verification_attempts = models.IntegerField(default=0)
    last_sent_at = models.DateTimeField(default=datetime.now)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        if not self.verification_token:
            self.verification_token = secrets.token_urlsafe(32)
        if not self.verification_code:
            self.verification_code = str(secrets.randbelow(1000000)).zfill(6)
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return datetime.now() > self.expires_at
    
    def __str__(self):
        return f"Email verification for {self.email}"


class WebsiteVerification(models.Model):
    """Website verification and security check"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Generic relation
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    verification_request = GenericForeignKey('content_type', 'object_id')
    
    website_url = models.URLField()
    
    # Verification Method
    VERIFICATION_METHODS = (
        ('dns', 'DNS TXT Record'),
        ('file', 'File Upload'),
        ('meta', 'HTML Meta Tag'),
    )
    verification_method = models.CharField(max_length=20, choices=VERIFICATION_METHODS)
    verification_token = models.CharField(max_length=100, unique=True)
    
    # Security Check (Google Safe Browsing)
    is_safe = models.BooleanField(default=False)
    security_check_result = models.JSONField(default=dict, blank=True)
    security_checked_at = models.DateTimeField(null=True, blank=True)
    
    # SSL Check
    has_ssl = models.BooleanField(default=False)
    ssl_valid = models.BooleanField(default=False)
    
    # Domain Verification
    domain_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Instructions for user
    verification_instructions = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        if not self.verification_token:
            self.verification_token = f"comrade-verify-{secrets.token_urlsafe(16)}"
        super().save(*args, **kwargs)
    
    def get_dns_instructions(self):
        return f"Add TXT record: comrade-verify={self.verification_token}"
    
    def get_file_instructions(self):
        return f"Upload file 'comrade-verify.txt' with content: {self.verification_token}"
    
    def get_meta_instructions(self):
        return f'Add meta tag: <meta name="comrade-verify" content="{self.verification_token}">'
    
    def __str__(self):
        return f"Website verification for {self.website_url}"


class VerificationActivity(models.Model):
    """Track all activities during verification process"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Generic relation
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    verification_request = GenericForeignKey('content_type', 'object_id')
    
    ACTION_TYPES = (
        ('created', 'Created'),
        ('submitted', 'Submitted'),
        ('status_changed', 'Status Changed'),
        ('document_uploaded', 'Document Uploaded'),
        ('document_verified', 'Document Verified'),
        ('email_verified', 'Email Verified'),
        ('website_verified', 'Website Verified'),
        ('liveness_initiated', 'Liveness Verification Initiated'),
        ('liveness_completed', 'Liveness Verification Completed'),
        ('liveness_failed', 'Liveness Verification Failed'),
        ('info_requested', 'Additional Info Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('activated', 'Activated'),
        ('comment_added', 'Comment Added'),
    )
    
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    details = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(default=datetime.now)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} at {self.timestamp}"


class LivenessVerification(models.Model):
    """Live video verification for liveness detection"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    verification_request = models.ForeignKey(
        'EntityVerificationRequest',
        on_delete=models.CASCADE,
        related_name='liveness_verifications'
    )
    
    session_id = models.CharField(max_length=100, unique=True)
    
    LIVENESS_STATUS = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    )
    status = models.CharField(max_length=20, choices=LIVENESS_STATUS, default='pending')
    
    video_file = models.FileField(upload_to='liveness_videos/%Y/%m/', null=True, blank=True)
    video_duration = models.FloatField(null=True, blank=True)
    
    liveness_score = models.FloatField(null=True, blank=True)
    liveness_verified = models.BooleanField(default=False)
    
    face_detected = models.BooleanField(default=False)
    multiple_faces = models.BooleanField(default=False)
    screen_recording_detected = models.BooleanField(default=False)
    mask_detected = models.BooleanField(default=False)
    
    verification_token = models.CharField(max_length=100)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        if not self.session_id:
            self.session_id = secrets.token_urlsafe(32)
        if not self.verification_token:
            self.verification_token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return datetime.now() > self.expires_at
    
    def __str__(self):
        return f"Liveness verification {self.session_id} - {self.status}"


class EntityVerificationRequest(models.Model):
    """Comprehensive verification for all entity types"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES)
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    
    status = models.CharField(max_length=50, choices=VERIFICATION_STATUS, default='draft')
    
    submitted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='verification_requests'
    )
    
    reviewer = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_verifications'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    rejection_reason = models.TextField(blank=True)
    additional_info_request = models.TextField(blank=True)
    
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_badge = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['entity_type', 'status', '-created_at']),
            models.Index(fields=['submitted_by']),
            models.Index(fields=['is_verified']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.entity_type} verification - {self.status}"


class EntityBasicInfo(models.Model):
    """Basic information for all entity types"""
    verification_request = models.OneToOneField(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='basic_info'
    )
    
    name = models.CharField(max_length=300)
    description = models.TextField(max_length=2000, blank=True)
    
    group_type = models.CharField(max_length=50, choices=GROUP_TYPES, blank=True)
    business_type = models.CharField(max_length=50, choices=BUSINESS_TYPES, blank=True)
    shop_type = models.CharField(max_length=50, choices=SHOP_TYPES, blank=True)
    creator_type = models.CharField(max_length=50, choices=CREATOR_TYPES, blank=True)
    tutor_type = models.CharField(max_length=50, choices=TUTOR_TYPES, blank=True)
    course_type = models.CharField(max_length=50, choices=COURSE_TYPES, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"Basic Info: {self.name}"


class EntityLocation(models.Model):
    """Location information for all entity types"""
    verification_request = models.OneToOneField(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='location'
    )
    
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    address = models.TextField(max_length=500)
    postal_code = models.CharField(max_length=20, blank=True)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    is_virtual = models.BooleanField(default=False)
    virtual_link = models.URLField(blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"{self.city}, {self.country}"


class EntityContact(models.Model):
    """Contact information for all entity types"""
    verification_request = models.OneToOneField(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='contact'
    )
    
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    website = models.URLField(blank=True)
    
    social_media = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"Contact: {self.email}"


class EntityRegistration(models.Model):
    """Registration and legal information"""
    verification_request = models.OneToOneField(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='registration'
    )
    
    registration_number = models.CharField(max_length=100)
    registration_document = models.FileField(upload_to='verification/registration/%Y/%m/', null=True, blank=True)
    
    year_established = models.IntegerField(null=True, blank=True)
    
    legal_name = models.CharField(max_length=300, blank=True)
    doing_business_as = models.CharField(max_length=300, blank=True)
    
    jurisdiction = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"Registration: {self.registration_number}"


class EntityTaxInfo(models.Model):
    """Tax information for businesses and organizations"""
    verification_request = models.OneToOneField(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='tax_info'
    )
    
    has_tax_id = models.BooleanField(default=False)
    tax_id = models.CharField(max_length=100, blank=True)
    tax_id_document = models.FileField(upload_to='verification/tax/%Y/%m/', null=True, blank=True)
    
    tax_system = models.CharField(max_length=50, choices=TAX_SYSTEM_TYPES, blank=True)
    tax_jurisdiction = models.CharField(max_length=100, blank=True)
    
    vat_number = models.CharField(max_length=50, blank=True)
    vat_registered = models.BooleanField(default=False)
    
    GST_number = models.CharField(max_length=50, blank=True)
    GST_registered = models.BooleanField(default=False)
    
    tax_filing_status = models.CharField(max_length=50, blank=True)
    last_tax_filing_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"Tax Info: {self.tax_id}"


class EntityIdentification(models.Model):
    """Identification documents for responsible persons"""
    verification_request = models.ForeignKey(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='identifications'
    )
    
    identification_type = models.CharField(max_length=50, choices=IDENTIFICATION_TYPES)
    
    document_number = models.CharField(max_length=100)
    document_file = models.FileField(upload_to='verification/id/%Y/%m/')
    
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    issuing_country = models.CharField(max_length=100)
    issuing_authority = models.CharField(max_length=200, blank=True)
    
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_identifications'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    verification_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"{self.identification_type}: {self.document_number}"


class VerificationVideo(models.Model):
    """Video recordings for verification"""
    verification_request = models.ForeignKey(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    
    VIDEO_TYPES = (
        ('liveness', 'Liveness Verification'),
        ('presentation', 'Entity Presentation'),
        ('interview', 'Interview'),
        ('other', 'Other'),
    )
    
    video_type = models.CharField(max_length=20, choices=VIDEO_TYPES)
    title = models.CharField(max_length=200)
    
    video_file = models.FileField(upload_to='verification_videos/%Y/%m/')
    thumbnail = models.ImageField(upload_to='verification_thumbnails/%Y/%m/', null=True, blank=True)
    
    duration = models.FloatField(null=True, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    
    is_processed = models.BooleanField(default=False)
    processing_status = models.CharField(max_length=50, blank=True)
    
    uploaded_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"{self.video_type}: {self.title}"


class VerificationChecklist(models.Model):
    """Checklist for verification requirements"""
    verification_request = models.ForeignKey(
        EntityVerificationRequest,
        on_delete=models.CASCADE,
        related_name='checklist'
    )
    
    CHECKLIST_ITEMS = (
        ('registration_doc', 'Registration Document'),
        ('tax_doc', 'Tax Document'),
        ('address_proof', 'Proof of Address'),
        ('id_document', 'ID Document'),
        ('liveness_video', 'Liveness Video'),
        ('presentation_video', 'Presentation Video'),
        ('business_plan', 'Business Plan'),
        ('portfolio', 'Portfolio'),
        ('certifications', 'Certifications'),
        ('qualifications', 'Qualifications'),
    )
    
    item = models.CharField(max_length=50, choices=CHECKLIST_ITEMS)
    is_required = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    document = models.ForeignKey(
        'VerificationDocument',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklist_items'
    )
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ('verification_request', 'item')
    
    def __str__(self):
        return f"{self.item}: {'Completed' if self.is_completed else 'Pending'}"
