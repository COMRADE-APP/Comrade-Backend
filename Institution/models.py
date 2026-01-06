"""
Enhanced Institution Models with Verification System
Includes document verification, member management, and admin framework
"""
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from Authentication.models import CustomUser
from datetime import datetime, timedelta
import uuid


# Institution types
INSTITUTION_TYPE = (
    ('university', 'University'),
    ('college', 'College'),
    ('school', 'School'),
    ('company', 'Company'),
    ('ngo', 'Non-Governmental Organization'),
    ('government', 'Government Agency'),
    ('research', 'Research Institution'),
    ('hospital', 'Hospital/Medical'),
    ('other', 'Other'),
)

# Verification status
VERIFICATION_STATUS = (
    ('pending', 'Pending Submission'),
    ('submitted', 'Submitted for Review'),
    ('under_review', 'Under Review'),
    ('verified', 'Verified'),
    ('rejected', 'Rejected'),
    ('suspended', 'Suspended'),
)

# Member roles
MEMBER_ROLE = (
    ('creator', 'Creator/Owner'),
    ('admin', 'Administrator'),
    ('moderator', 'Moderator'),
    ('member', 'Member'),
    ('subscriber', 'Subscriber'),
)

# Document types
DOCUMENT_TYPE = (
    ('registration_cert', 'Registration Certificate'),
    ('tax_id', 'Tax ID Document'),
    ('proof_address', 'Proof of Address'),
    ('director_id', 'Director ID'),
    ('other', 'Other Document'),
)


class Institution(models.Model):
    """Main Institution model with verification support"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=500)
    institution_type = models.CharField(max_length=50, choices=INSTITUTION_TYPE, default='university')
    description = models.TextField(blank=True)
    
    # Contact Information
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    website = models.URLField(blank=True, null=True)
    website_verified = models.BooleanField(default=False)
    website_verification_token = models.CharField(max_length=100, blank=True, null=True)
    website_verification_method = models.CharField(max_length=20, blank=True, null=True)  # dns or meta
    
    phone = models.CharField(max_length=20, blank=True)
    
    # Address
    country = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100)
    address = models.TextField()
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Registration Details
    registration_number = models.CharField(max_length=100, blank=True, unique=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True)
    
    # Verification
    status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_institutions')
    
    # Verification documents metadata
    documents_submitted = models.BooleanField(default=False)
    documents_verified = models.BooleanField(default=False)
    
    # Review
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_institutions')
    review_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Settings
    is_active = models.BooleanField(default=True)
    allow_public_signup = models.BooleanField(default=False)
    require_email_domain = models.BooleanField(default=False)
    
    # Logo
    logo_url = models.URLField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['email']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Institution'
        verbose_name_plural = 'Institutions'
    
    def __str__(self):
        return f"{self.name} ({self.get_institution_type_display()})"


class InstitutionVerificationDocument(models.Model):
    """Documents uploaded for institution verification"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='verification_documents')
    
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE)
    file_path = models.CharField(max_length=500)  # Encrypted file path
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()  # Size in bytes
    file_type = models.CharField(max_length=50)  # MIME type
    
    # Verification
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Security
    virus_scanned = models.BooleanField(default=False)
    virus_scan_result = models.CharField(max_length=50, default='pending')  # clean, infected, error
    
    # OCR extracted text (for searchability)
    extracted_text = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(default=datetime.now)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='uploaded_docs')
    
    class Meta:
        indexes = [
            models.Index(fields=['institution', 'document_type']),
            models.Index(fields=['verified']),
        ]
    
    def __str__(self):
        return f"{self.institution.name} - {self.get_document_type_display()}"


class InstitutionMember(models.Model):
    """Members of an institution with roles and permissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    
    role = models.CharField(max_length=20, choices=MEMBER_ROLE, default='member')
    
    # Custom permissions (JSON)
    permissions = models.JSONField(default=dict, blank=True)
    # Example: {'create_announcement': True, 'manage_members': False, 'edit_institution': False}
    
    # Invitation
    invited_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='sent_institution_invitations')
    invitation_accepted = models.BooleanField(default=False)
    invitation_token = models.CharField(max_length=100, blank=True, null=True)
    invitation_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    joined_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['institution', 'user']
        indexes = [
            models.Index(fields=['institution', 'role']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()} at {self.institution.name}"
    
    def has_permission(self, permission):
        """Check if member has specific permission"""
        # Creators and admins have all permissions
        if self.role in ['creator', 'admin']:
            return True
        
        # Check custom permissions
        return self.permissions.get(permission, False)


class InstitutionVerificationLog(models.Model):
    """Log of all verification actions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='verification_logs')
    
    action = models.CharField(max_length=50, choices=(
        ('created', 'Institution Created'),
        ('email_sent', 'Email Verification Sent'),
        ('email_verified', 'Email Verified'),
        ('website_verified', 'Website Verified'),
        ('document_uploaded', 'Document Uploaded'),
        ('document_verified', 'Document Verified'),
        ('submitted', 'Submitted for Review'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
        ('reactivated', 'Reactivated'),
    ))
    
    performed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    timestamp = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['institution', '-timestamp']),
            models.Index(fields=['action']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.institution.name} - {self.action} at {self.timestamp}"


class WebsiteVerificationRequest(models.Model):
    """Track website verification attempts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='website_verifications')
    
    method = models.CharField(max_length=20, choices=(
        ('dns', 'DNS TXT Record'),
        ('meta', 'Meta Tag'),
    ))
    
    verification_token = models.CharField(max_length=100)
    verification_code = models.CharField(max_length=100)  # What to add to DNS or meta
    
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Security checks
    ssl_valid = models.BooleanField(default=False)
    safe_browsing_passed = models.BooleanField(default=False)
    domain_age_days = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['institution', '-created_at']),
            models.Index(fields=['verified']),
        ]
    
    def __str__(self):
        return f"{self.institution.website} - {self.method}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.now() + timedelta(days=7)
        super().save(*args, **kwargs)


# Organization models (similar structure)
class Organization(models.Model):
    """Organization model - similar to Institution but for non-educational entities"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Copy same structure as Institution
    name = models.CharField(max_length=500)
    organization_type = models.CharField(max_length=50, choices=INSTITUTION_TYPE, default='company')
    description = models.TextField(blank=True)
    
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    website = models.URLField(blank=True, null=True)
    website_verified = models.BooleanField(default=False)
    
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.TextField()
    
    registration_number = models.CharField(max_length=100, blank=True, unique=True, null=True)
    status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_organizations')
    
    created_at = models.DateTimeField(default=datetime.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
    
    def __str__(self):
        return self.name
