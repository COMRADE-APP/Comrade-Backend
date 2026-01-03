from django.db import models
from Authentication.models import CustomUser
from datetime import datetime
import uuid


class CredentialVerification(models.Model):
    """Universal credential verification for all user types"""
    
    VERIFICATION_STATUS = (
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('additional_info_required', 'Additional Info Required'),
    )
    
    USER_ROLES = (
        ('researcher', 'Researcher'),
        ('author', 'Author'),
        ('editor', 'Editor'),
        ('publisher', 'Publisher'),
        ('moderator', 'Moderator'),
        ('creator', 'Creator'),
        ('inst_staff', 'Institutional Staff'),
        ('org_staff', 'Organizational Staff'),
        ('lecturer', 'Lecturer'),
        ('student', 'Student'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='credential_verifications')
    role_applying_for = models.CharField(max_length=50, choices=USER_ROLES)
    
    # Identity Verification
    full_name = models.CharField(max_length=300)
    id_document = models.FileField(upload_to='credentials/identity/')
    id_type = models.CharField(max_length=50, choices=(
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('driver_license', 'Driver License'),
        ('other', 'Other Official ID'),
    ))
    id_number = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    
    # Qualification Documents
    qualification_documents = models.JSONField(default=list, blank=True)  # [{title, file_url, institution, year}]
    cv_resume = models.FileField(upload_to='credentials/cv/', null=True, blank=True)
    cover_letter = models.TextField(blank=True)
    
    # Experience
    years_of_experience = models.IntegerField(default=0)
    experience_documents = models.JSONField(default=list, blank=True)  # [{company, role, from, to, reference}]
    portfolio_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # Academic Credentials (for researchers, lecturers)
    highest_degree = models.CharField(max_length=100, blank=True)
    field_of_study = models.CharField(max_length=200, blank=True)
    alma_mater = models.CharField(max_length=300, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    academic_transcripts = models.FileField(upload_to='credentials/transcripts/', null=True, blank=True)
    
    # Publication Record (for researchers, authors)
    publications = models.JSONField(default=list, blank=True)  # [{title, journal, year, doi}]
    google_scholar_url = models.URLField(blank=True)
    orcid = models.CharField(max_length=100, blank=True, help_text="ORCID iD")
    h_index = models.IntegerField(null=True, blank=True)
    total_citations = models.IntegerField(default=0)
    
    # Professional Licenses
    professional_licenses = models.JSONField(default=list, blank=True)  # [{type, number, issuing_body, expiry}]
    certifications = models.JSONField(default=list, blank=True)
    
    # References
    references = models.JSONField(default=list, blank=True)  # [{name, title, email, phone, institution}]
    
    # Verification Status
    status = models.CharField(max_length=50, choices=VERIFICATION_STATUS, default='pending')
    submitted_at = models.DateTimeField(default=datetime.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_credentials')
    
    # Feedback
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    additional_info_request = models.TextField(blank=True)
    
    # Approval
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # For periodic re-verification
    
    # Supporting Documents
    supporting_documents = models.JSONField(default=list, blank=True)  # Additional docs
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['role_applying_for']),
            models.Index(fields=['reviewed_by']),
        ]
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_applying_for_display()} ({self.get_status_display()})"


class UserQualification(models.Model):
    """Track approved qualifications for users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verified_qualifications')
    verification = models.ForeignKey(CredentialVerification, on_delete=models.CASCADE, related_name='approved_qualifications')
    
    qualification_type = models.CharField(max_length=100, choices=(
        ('degree', 'Academic Degree'),
        ('certificate', 'Professional Certificate'),
        ('license', 'Professional License'),
        ('award', 'Award/Recognition'),
        ('training', 'Professional Training'),
    ))
    
    title = models.CharField(max_length=300)
    institution = models.CharField(max_length=300)
    field = models.CharField(max_length=200)
    level = models.CharField(max_length=100, choices=(
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', 'Bachelor Degree'),
        ('master', 'Master Degree'),
        ('doctoral', 'Doctoral Degree'),
        ('postdoctoral', 'Postdoctoral'),
        ('professional', 'Professional Certification'),
    ), blank=True)
    
    year_obtained = models.IntegerField()
    expiry_date = models.DateField(null=True, blank=True)
    
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_other_qualifications')
    
    document = models.FileField(upload_to='qualifications/')
    credential_url = models.URLField(blank=True, help_text="Link to verify online")
    
    class Meta:
        ordering = ['-year_obtained']
        indexes = [
            models.Index(fields=['user', 'verified']),
            models.Index(fields=['qualification_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.title} ({self.year_obtained})"


class BackgroundCheck(models.Model):
    """Background verification for sensitive roles"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='background_checks')
    credential_verification = models.ForeignKey(CredentialVerification, on_delete=models.CASCADE, related_name='background_checks')
    
    check_type = models.CharField(max_length=50, choices=(
        ('criminal', 'Criminal Record'),
        ('employment', 'Employment Verification'),
        ('education', 'Education Verification'),
        ('reference', 'Reference Check'),
        ('identity', 'Identity Verification'),
        ('credit', 'Credit Check'),
    ))
    
    status = models.CharField(max_length=50, choices=(
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ), default='pending')
    
    result = models.CharField(max_length=50, choices=(
        ('clear', 'Clear'),
        ('flagged', 'Flagged'),
        ('requires_review', 'Requires Manual Review'),
    ), blank=True)
    
    notes = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    
    requested_at = models.DateTimeField(default=datetime.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    conducted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='conducted_background_checks')
    
    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['check_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_check_type_display()} ({self.get_status_display()})"


class MembershipRequest(models.Model):
    """Universal membership request model for institutions/organizations/rooms"""
    
    ENTITY_TYPES = (
        ('institution', 'Institution'),
        ('organization', 'Organization'),
        ('room', 'Room'),
        ('specialization', 'Specialization'),
    )
    
    REQUEST_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='membership_requests')
    
    # Polymorphic entity reference
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPES)
    entity_id = models.UUIDField()
    entity_name = models.CharField(max_length=300)  # Cached for display
    
    # Request details
    role_requested = models.CharField(max_length=50)
    message = models.TextField(blank=True)
    credentials_submitted = models.JSONField(default=dict, blank=True)
    
    # Approval token (if provided by admin)
    approval_token = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(max_length=50, choices=REQUEST_STATUS, default='pending')
    requested_at = models.DateTimeField(default=datetime.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_membership_requests')
    
    # Response
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['entity_type', 'entity_id', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['approval_token']),
        ]
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.user.email} -> {self.entity_name} ({self.get_status_display()})"


class InvitationLink(models.Model):
    """Reusable invitation links for entities"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_invitations')
    
    # Entity
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    entity_name = models.CharField(max_length=300)  # Cached
    
    # Link details
    token = models.CharField(max_length=255, unique=True, db_index=True)
    role_granted = models.CharField(max_length=50)
    max_uses = models.IntegerField(null=True, blank=True)  # None = unlimited
    uses_count = models.IntegerField(default=0)
    
    # Validity
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Permissions for role
    permissions = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['is_active', 'expires_at']),
        ]
    
    def __str__(self):
        return f"Invite to {self.entity_name} ({self.role_granted})"
    
    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        if self.max_uses and self.uses_count >= self.max_uses:
            return False
        return True


class PresetUserAccount(models.Model):
    """Admin-created user accounts with preset credentials"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='preset_accounts_created')
    
    # User details
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    role = models.CharField(max_length=50)
    preset_password = models.CharField(max_length=255)  # Temp password (hashed)
    
    # Entity assignment
    entity_type = models.CharField(max_length=50)
    entity_id = models.UUIDField()
    entity_name = models.CharField(max_length=300)
    
    # Additional user data
    phone_number = models.CharField(max_length=15, blank=True)
    user_type = models.CharField(max_length=50, blank=True)
    
    # Status
    activated = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    invitation_sent = models.BooleanField(default=False)
    invitation_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Linked user once activated
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='preset_account')
    
    created_at = models.DateTimeField(default=datetime.now)
    expires_at = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['activated', 'expires_at']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]
    
    def __str__(self):
        status = "Activated" if self.activated else "Pending"
        return f"{self.email} - {self.role} ({status})"
