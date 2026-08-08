"""
Compliance Models — CDD/EDD, safeguarding, and AML/STR for the fintech platform.

Qomrade acts as a facilitator, not an operator. These models support the
compliance obligations that come with enabling collaborative purchase,
savings, and investment: know-your-customer (CDD/EDD), safeguarding of
client funds, and anti-money-laundering / suspicious-transaction reporting.

References: POCAMLA AML/CTF (CDD/EDD, 7-year record retention, STR),
CBK e-money safeguarding rules (100% backed, ring-fenced, redeemable),
and the VASP Act (Nov 2025) licensing regime.
"""
from django.db import models
from django.conf import settings
import uuid


RISK_LEVELS = (
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('prohibited', 'Prohibited'),
)

STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('in_progress', 'In Progress'),
    ('cleared', 'Cleared'),
    ('flagged', 'Flagged'),
    ('rejected', 'Rejected'),
    ('closed', 'Closed'),
)

CUSTOMER_TYPES = (
    ('individual', 'Individual'),
    ('organisation', 'Organisation'),
    ('institution', 'Institution'),
    ('provider', 'Provider'),
)


class CustomerRiskProfile(models.Model):
    """Risk classification of a customer (individual or entity)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='risk_profiles',
        null=True,
        blank=True,
    )
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES)
    organisation = models.CharField(max_length=255, blank=True)
    institution = models.CharField(max_length=255, blank=True)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default='low')
    score = models.IntegerField(default=0)
    reason = models.TextField(blank=True)
    source_of_funds = models.TextField(blank=True)
    occupation = models.CharField(max_length=200, blank=True)
    country_of_residence = models.CharField(max_length=100, blank=True)
    politically_exposed = models.BooleanField(default=False)
    pep_details = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='risk_reviews',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.customer_type} risk: {self.risk_level}"


class CDDRecord(models.Model):
    """Customer Due Diligence record and verification workflow."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cdd_records',
    )
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES)
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    passport_number = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    identification_verified = models.BooleanField(default=False)
    address_verified = models.BooleanField(default=False)
    beneficial_owner_identified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cdd_verifications',
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"CDD: {self.full_name} ({self.status})"


class EDDRecord(models.Model):
    """Enhanced Due Diligence — required for high-risk customers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cdd_record = models.ForeignKey(
        CDDRecord,
        on_delete=models.CASCADE,
        related_name='edd_records',
    )
    risk_profile = models.ForeignKey(
        CustomerRiskProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edd_records',
    )
    reason_for_edd = models.CharField(max_length=255)
    source_of_funds_documented = models.BooleanField(default=False)
    source_of_wealth_documented = models.BooleanField(default=False)
    senior_approval_obtained = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='edd_approvals',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"EDD for {self.cdd_record}"


class SafeguardingAccount(models.Model):
    """Client-fund safeguarding / ring-fencing record."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='safeguarding_accounts',
    )
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100, blank=True)
    provider = models.CharField(max_length=255)
    funds_pooled = models.BooleanField(default=False)
    ring_fenced = models.BooleanField(default=True)
    fully_backed = models.BooleanField(default=True)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Safeguarding: {self.account_name}"


class SuspiciousTransactionReport(models.Model):
    """AML suspicious-transaction report (STR)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='str_reports_filed',
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='str_reports',
        null=True,
        blank=True,
    )
    transaction_reference = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='KES')
    suspicious_reason = models.TextField()
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    filed_with_regulator = models.BooleanField(default=False)
    filed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"STR: {self.transaction_reference or self.id}"


class ComplianceRecord(models.Model):
    """Retention ledger — regulatory 7-year record-keeping."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='compliance_records',
        null=True,
        blank=True,
    )
    record_type = models.CharField(max_length=50)
    reference = models.CharField(max_length=255, blank=True)
    content = models.JSONField(default=dict, blank=True)
    retention_until = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Compliance record: {self.record_type} ({self.reference})"
