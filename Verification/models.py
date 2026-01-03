"""
Institution and Organization Verification Models
Handles secure verification workflow from submission to activation
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


# Status choices
VERIFICATION_STATUS = (
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('under_review', 'Under Review'),
    ('additional_info', 'Additional Information Requested'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('activated', 'Activated'),
)

INSTITUTION_TYPES = (
    ('university', 'University'),
    ('college', 'College'),
    ('school', 'School'),
    ('research', 'Research Institution'),
    ('training', 'Training Center'),
    ('other', 'Other'),
)

ORGANIZATION_TYPES = (
    ('ngo', 'Non-Governmental Organization'),
    ('corporate', 'Corporate/Business'),
    ('government', 'Government Agency'),
    ('nonprofit', 'Non-Profit'),
    ('association', 'Professional Association'),
    ('other', 'Other'),
)


class InstitutionVerificationRequest(models.Model):
    """Verification request for creating an institution"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    institution_name = models.CharField(max_length=300)
    institution_type = models.CharField(max_length=50, choices=INSTITUTION_TYPES)
    
    # Location
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    address = models.TextField(max_length=500)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Contact Information
    official_email = models.EmailField()
    official_website = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20)
    
    # Registration Details
    registration_number = models.CharField(max_length=100)
    year_established = models.IntegerField(null=True, blank=True)
    
    # Additional Information
    description = models.TextField(max_length=2000, blank=True)
    number_of_staff = models.IntegerField(null=True, blank=True)
    number_of_students = models.IntegerField(null=True, blank=True)
    
    # Documents (stored as references to VerificationDocument)
    documents_uploaded = models.BooleanField(default=False)
    
    # Submission & Review
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='institution_verification_requests')
    status = models.CharField(max_length=50, choices=VERIFICATION_STATUS, default='draft')
    
    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_institutions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    additional_info_request = models.TextField(blank=True)
    
    # Activation
    institution = models.OneToOneField(Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='verification_request')
    activated_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['submitted_by']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.institution_name} - {self.status}"


class OrganizationVerificationRequest(models.Model):
    """Verification request for creating an organization"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    organization_name = models.CharField(max_length=300)
    organization_type = models.CharField(max_length=50, choices=ORGANIZATION_TYPES)
    
    # Location
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    address = models.TextField(max_length=500)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Contact Information
    official_email = models.EmailField()
    official_website = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20)
    
    # Registration Details
    registration_number = models.CharField(max_length=100)
    tax_id = models.CharField(max_length=100, blank=True)
    year_established = models.IntegerField(null=True, blank=True)
    
    # Additional Information
    description = models.TextField(max_length=2000, blank=True)
    number_of_employees = models.IntegerField(null=True, blank=True)
    annual_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Documents
    documents_uploaded = models.BooleanField(default=False)
    
    # Submission & Review
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='organization_verification_requests')
    status = models.CharField(max_length=50, choices=VERIFICATION_STATUS, default='draft')
    
    reviewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_organizations')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    additional_info_request = models.TextField(blank=True)
    
    # Activation
    organization = models.OneToOneField(Organisation, on_delete=models.SET_NULL, null=True, blank=True, related_name='verification_request')
    activated_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['submitted_by']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.organization_name} - {self.status}"


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
