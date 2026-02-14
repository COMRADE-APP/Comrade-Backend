"""
Enhanced Institution Models with Verification System
Includes document verification, member management, and admin framework
"""
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
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
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, related_name='created_institutions')
    
    # Verification documents metadata
    documents_submitted = models.BooleanField(default=False)
    documents_verified = models.BooleanField(default=False)
    
    # Review
    reviewed_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='inst_reviews')
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
    
    # Logo/Media
    logo_url = models.URLField(blank=True, null=True) # Keep for backward compatibility or external logos
    profile_picture = models.ImageField(upload_to='institution_profiles/', null=True, blank=True)
    cover_picture = models.ImageField(upload_to='institution_covers/', null=True, blank=True)

    # Followers
    followers = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='followed_institutions')
    
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
    verified_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Security
    virus_scanned = models.BooleanField(default=False)
    virus_scan_result = models.CharField(max_length=50, default='pending')  # clean, infected, error
    
    # OCR extracted text (for searchability)
    extracted_text = models.TextField(blank=True)
    
    uploaded_at = models.DateTimeField(default=datetime.now)
    uploaded_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, related_name='uploaded_docs')
    
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
    user = models.ForeignKey('Authentication.CustomUser', on_delete=models.CASCADE)
    
    role = models.CharField(max_length=20, choices=MEMBER_ROLE, default='member')
    title = models.CharField(max_length=200, blank=True, help_text="Custom editable title (e.g. 'Dean of Faculty')")
    
    # Custom permissions (JSON)
    permissions = models.JSONField(default=dict, blank=True)
    # Example: {'create_announcement': True, 'manage_members': False, 'edit_institution': False}
    
    # Invitation
    invited_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, related_name='sent_institution_invitations')
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
    
    performed_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True)
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
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, related_name='created_organizations')
    
    created_at = models.DateTimeField(default=datetime.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
    
    def __str__(self):
        return self.name



# ============================================================================
# HIERARCHICAL INSTITUTION STRUCTURE MODELS
# These models enable building out the internal structure of verified institutions
# Only accessible after an Institution has been verified
# ============================================================================

# University/Institution Structure:
# ├── Institution Branches (Campuses)
# ├── Office of the Vice Chancellor
# ├── Faculties / Colleges / Schools
# │   └── Departments
# │       └── Programs / Courses
# ├── Administrative Departments
# │   ├── Registrar
# │   ├── HR
# │   ├── Finance
# │   ├── ICT
# │   ├── Marketing
# │   └── Legal
# ├── Student Affairs
# │   ├── Admissions
# │   ├── Career Office
# │   └── Counseling
# └── Support Services
#     ├── Security
#     ├── Transport
#     ├── Library
#     ├── Cafeteria
#     ├── Hostel
#     └── Health Services


class InstBranch(models.Model):
    """Institution branches/campuses - allows multi-campus institutions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='branches')
    
    name = models.CharField(max_length=200)
    branch_code = models.CharField(max_length=200, unique=True)
    origin = models.CharField(max_length=500, blank=True)
    abbreviation = models.CharField(max_length=200, blank=True)
    
    # Address
    address = models.TextField()
    postal_code = models.CharField(max_length=200, blank=True)
    town = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=500)
    country = models.CharField(max_length=100)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_inst_branches')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_inst_branches')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Institution Branch'
        verbose_name_plural = 'Institution Branches'
        indexes = [
            models.Index(fields=['institution', 'is_active']),
            models.Index(fields=['branch_code']),
            models.Index(fields=['approval_status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.institution.name}"


class VCOffice(models.Model):
    """Vice Chancellor's Office / Executive Office"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='vc_offices')
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='vc_offices')
    
    name = models.CharField(max_length=500)
    office_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='vc_office_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_vc_offices')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_vc_offices')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Vice Chancellor Office'
        verbose_name_plural = 'Vice Chancellor Offices'
        indexes = [
            models.Index(fields=['institution', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.institution.name}"


class Faculty(models.Model):
    """Academic Faculties/Schools/Colleges"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='faculties')
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='faculties')
    
    name = models.CharField(max_length=500)
    faculty_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='faculty_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_faculties')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_faculties')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculties'
        indexes = [
            models.Index(fields=['institution', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.institution.name}"


class InstDepartment(models.Model):
    """Academic Departments within Faculties"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='departments', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='departments', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='departments')
    
    name = models.CharField(max_length=500)
    dep_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='inst_department_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_inst_departments')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_inst_departments')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Institution Department'
        verbose_name_plural = 'Institution Departments'
        indexes = [
            models.Index(fields=['faculty', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.faculty.name}"


class Programme(models.Model):
    """Academic Programs/Courses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(InstDepartment, on_delete=models.CASCADE, related_name='programmes', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='programmes', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='programmes')
    
    name = models.CharField(max_length=500)
    programme_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='programme_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_programmes')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_programmes')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Programme'
        verbose_name_plural = 'Programmes'
        indexes = [
            models.Index(fields=['department', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.department.name}"


# ============================================================================
# ADMINISTRATIVE DEPARTMENTS
# ============================================================================

class AdminDep(models.Model):
    """Administrative Department Parent"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='admin_departments')
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='admin_departments')
    
    name = models.CharField(max_length=500)
    admin_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='admin_dep_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Approval workflow fields
    approval_status = models.CharField(max_length=20, choices=(
        ('approved', 'Approved'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    ), default='approved')
    created_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_admin_deps')
    approved_by = models.ForeignKey('Authentication.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_admin_deps')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Administrative Department'
        verbose_name_plural = 'Administrative Departments'
        indexes = [
            models.Index(fields=['institution', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.institution.name}"


class RegistrarOffice(models.Model):
    """Registrar's Office"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_dep = models.ForeignKey(AdminDep, on_delete=models.CASCADE, related_name='registrar_offices', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='registrar_offices', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='registrar_offices')
    
    name = models.CharField(max_length=500)
    registrar_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='registrar_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Registrar Office'
        verbose_name_plural = 'Registrar Offices'
    
    def __str__(self):
        return f"{self.name} - {self.admin_dep.name}"


class HR(models.Model):
    """Human Resources Department"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_dep = models.ForeignKey(AdminDep, on_delete=models.CASCADE, related_name='hr_departments', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='hr_departments', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='hr_departments')
    
    name = models.CharField(max_length=500)
    hr_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='hr_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'HR Department'
        verbose_name_plural = 'HR Departments'
    
    def __str__(self):
        return f"{self.name} - {self.admin_dep.name}"


class ICT(models.Model):
    """ICT/IT Department"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_dep = models.ForeignKey(AdminDep, on_delete=models.CASCADE, related_name='ict_departments', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='ict_departments', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='ict_departments')
    
    name = models.CharField(max_length=500)
    ict_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='ict_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'ICT Department'
        verbose_name_plural = 'ICT Departments'
    
    def __str__(self):
        return f"{self.name} - {self.admin_dep.name}"


class Finance(models.Model):
    """Finance Department"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_dep = models.ForeignKey(AdminDep, on_delete=models.CASCADE, related_name='finance_departments', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='finance_departments', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='finance_departments')
    
    name = models.CharField(max_length=500)
    finance_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='finance_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Finance Department'
        verbose_name_plural = 'Finance Departments'
    
    def __str__(self):
        return f"{self.name} - {self.admin_dep.name}"


class Marketing(models.Model):
    """Marketing Department"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_dep = models.ForeignKey(AdminDep, on_delete=models.CASCADE, related_name='marketing_departments', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='marketing_departments', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='marketing_departments')
    
    name = models.CharField(max_length=500)
    marketing_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='marketing_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Marketing Department'
        verbose_name_plural = 'Marketing Departments'
    
    def __str__(self):
        return f"{self.name} - {self.admin_dep.name}"


class Legal(models.Model):
    """Legal Department"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_dep = models.ForeignKey(AdminDep, on_delete=models.CASCADE, related_name='legal_departments', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='legal_departments', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='legal_departments')
    
    name = models.CharField(max_length=500)
    legal_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='legal_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Legal Department'
        verbose_name_plural = 'Legal Departments'
    
    def __str__(self):
        return f"{self.name} - {self.admin_dep.name}"


# ============================================================================
# STUDENT AFFAIRS
# ============================================================================

class StudentAffairs(models.Model):
    """Student Affairs Department Parent"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='student_affairs')
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='student_affairs')
    
    name = models.CharField(max_length=500)
    stud_affairs_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='student_affairs_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Student Affairs'
        verbose_name_plural = 'Student Affairs'
        indexes = [
            models.Index(fields=['institution', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.institution.name}"


class Admissions(models.Model):
    """Admissions Office"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stud_affairs = models.ForeignKey(StudentAffairs, on_delete=models.CASCADE, related_name='admissions_offices', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='admissions_offices', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='admissions_offices')
    
    name = models.CharField(max_length=500)
    admissions_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='admissions_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Admissions Office'
        verbose_name_plural = 'Admissions Offices'
    
    def __str__(self):
        return f"{self.name} - {self.stud_affairs.name}"


class CareerOffice(models.Model):
    """Career Services Office"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stud_affairs = models.ForeignKey(StudentAffairs, on_delete=models.CASCADE, related_name='career_offices', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='career_offices', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='career_offices')
    
    name = models.CharField(max_length=500)
    career_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='career_office_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Career Office'
        verbose_name_plural = 'Career Offices'
    
    def __str__(self):
        return f"{self.name} - {self.stud_affairs.name}"


class Counselling(models.Model):
    """Counselling Services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stud_affairs = models.ForeignKey(StudentAffairs, on_delete=models.CASCADE, related_name='counselling_services', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='counselling_services', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='counselling_services')
    
    name = models.CharField(max_length=500)
    counselling_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='counselling_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Counselling Service'
        verbose_name_plural = 'Counselling Services'
    
    def __str__(self):
        return f"{self.name} - {self.stud_affairs.name}"


# ============================================================================
# SUPPORT SERVICES
# ============================================================================

class SupportServices(models.Model):
    """Support Services Department Parent"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='support_services')
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='support_services')
    
    name = models.CharField(max_length=500)
    support_services_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='support_services_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Support Services'
        verbose_name_plural = 'Support Services'
        indexes = [
            models.Index(fields=['institution', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.institution.name}"


class Security(models.Model):
    """Security Services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_services = models.ForeignKey(SupportServices, on_delete=models.CASCADE, related_name='security_units', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='security_units', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='security_units')
    
    name = models.CharField(max_length=500)
    security_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='security_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Security Service'
        verbose_name_plural = 'Security Services'
    
    def __str__(self):
        return f"{self.name} - {self.support_services.name}"


class Transport(models.Model):
    """Transport Services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_services = models.ForeignKey(SupportServices, on_delete=models.CASCADE, related_name='transport_units', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='transport_units', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='transport_units')
    
    name = models.CharField(max_length=500)
    transport_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='transport_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Transport Service'
        verbose_name_plural = 'Transport Services'
    
    def __str__(self):
        return f"{self.name} - {self.support_services.name}"


class Library(models.Model):
    """Library Services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_services = models.ForeignKey(SupportServices, on_delete=models.CASCADE, related_name='libraries', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='libraries', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='libraries')
    
    name = models.CharField(max_length=500)
    library_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='library_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Library'
        verbose_name_plural = 'Libraries'
    
    def __str__(self):
        return f"{self.name} - {self.support_services.name}"


class Cafeteria(models.Model):
    """Cafeteria Services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_services = models.ForeignKey(SupportServices, on_delete=models.CASCADE, related_name='cafeterias', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='cafeterias', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='cafeterias')
    
    name = models.CharField(max_length=500)
    cafeteria_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='cafeteria_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cafeteria'
        verbose_name_plural = 'Cafeterias'
    
    def __str__(self):
        return f"{self.name} - {self.support_services.name}"


class Hostel(models.Model):
    """Hostel/Accommodation Services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_services = models.ForeignKey(SupportServices, on_delete=models.CASCADE, related_name='hostels', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='hostels', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='hostels')
    
    name = models.CharField(max_length=500)
    hostel_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='hostel_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Hostel'
        verbose_name_plural = 'Hostels'
    
    def __str__(self):
        return f"{self.name} - {self.support_services.name}"


class HealthServices(models.Model):
    """Health/Medical Services"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_services = models.ForeignKey(SupportServices, on_delete=models.CASCADE, related_name='health_services', null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='health_services', null=True, blank=True)
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='health_services')
    
    name = models.CharField(max_length=500)
    health_services_code = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='health_services_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Health Service'
        verbose_name_plural = 'Health Services'
    
    def __str__(self):
        return f"{self.name} - {self.support_services.name}"


# ============================================================================
# FLEXIBLE UNIT STRUCTURE
# ============================================================================

class OtherInstitutionUnit(models.Model):
    """Generic unit for custom/flexible institutional structures"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='other_units')
    inst_branch = models.ForeignKey(InstBranch, on_delete=models.CASCADE, null=True, blank=True, related_name='other_units')
    
    parent_units = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='child_units')
    
    name = models.CharField(max_length=500)
    unit_code = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    
    staff = models.ManyToManyField('Authentication.CustomUser', blank=True, related_name='other_unit_memberships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Other Institution Unit'
        verbose_name_plural = 'Other Institution Units'
        indexes = [
            models.Index(fields=['institution', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.institution.name}"