from django.db import models
from django.conf import settings
import uuid

class Business(models.Model):
    INDUSTRY_CHOICES = [
        ('tech', 'Technology'),
        ('agri', 'Agriculture'),
        ('fin', 'Finance'),
        ('retail', 'Retail'),
        ('health', 'Healthcare'),
        ('educ', 'Education'),
        ('energy', 'Energy'),
        ('other', 'Other'),
    ]

    STAGE_CHOICES = [
        ('idea', 'Idea Phase'),
        ('mvp', 'MVP (Prototype)'),
        ('pre_seed', 'Pre-Seed'),
        ('seed', 'Seed'),
        ('series_a', 'Series A'),
        ('growth', 'Growth'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    founder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='businesses')
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    description = models.TextField()
    logo = models.ImageField(upload_to='business_logos/', null=True, blank=True)
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default='idea')
    website = models.URLField(null=True, blank=True)
    
    # Financial metrics (optional simplified)
    valuation = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Charity fields (Phase 3)
    is_charity = models.BooleanField(default=False, help_text="Is this a charity/non-profit?")
    charity_goal = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Fundraising goal")
    charity_raised = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Amount raised so far")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    @property
    def charity_progress(self):
        if self.is_charity and self.charity_goal and self.charity_goal > 0:
            return min((self.charity_raised / self.charity_goal) * 100, 100)
        return 0

class FundingDocument(models.Model):
    DOC_TYPES = [
        ('license', 'Business License'),
        ('pitch_deck', 'Pitch Deck'),
        ('financials', 'Financial Statements'),
        ('legal', 'Legal Contract'),
        ('patent', 'Patent/IP'),
        ('kpi', 'KPI Report'),
        ('other', 'Other Supporting Doc'),
    ]

    SCAN_STATUS_CHOICES = [
        ('pending', 'Pending Scan'),
        ('scanning', 'Scanning'),
        ('clean', 'Clean'),
        ('malware', 'Malware Detected'),
        ('nsfw_rejected', 'NSFW Content Rejected'),
        ('error', 'Scan Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='funding_docs/')
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Security scanning fields
    scan_status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default='pending')
    scan_result = models.JSONField(null=True, blank=True, help_text="Detailed scan results from APIs")
    scanned_at = models.DateTimeField(null=True, blank=True)
    is_viewable = models.BooleanField(default=False, help_text="Only True if scan passed")

    def __str__(self):
        return f"{self.business.name} - {self.title}"
    
    @property
    def is_safe(self):
        return self.scan_status == 'clean'

class FundingRequest(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open for Funding'),
        ('closing', 'Closing Soon'),
        ('funded', 'Fully Funded'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='funding_requests')
    amount_needed = models.DecimalField(max_digits=15, decimal_places=2)
    equity_offered = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage equity offered")
    use_of_funds = models.TextField(help_text="How will the funds be used?")
    min_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.business.name} seeking {self.amount_needed}"

class InvestmentOpportunity(models.Model):
    """
    General investment opportunities like Stocks, MMFs, Bonds, Lending.
    These might be managed by admins or partners.
    """
    TYPE_CHOICES = [
        ('stock', 'Stock Market'),
        ('mmf', 'Money Market Fund'),
        ('bond', 'Government/Corp Bond'),
        ('lending', 'P2P Lending'),
        ('crypto', 'Cryptocurrency'),
    ]

    RISK_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    provider = models.CharField(max_length=255, help_text="Institution offering this")
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    
    min_investment = models.DecimalField(max_digits=12, decimal_places=2)
    expected_return = models.CharField(max_length=100, help_text="e.g. '12% p.a.'")
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES)
    
    link = models.URLField(help_text="Link to external platform or internal action", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.provider})"

    class Meta:
        verbose_name_plural = "Investment Opportunities"


# ==============================================================================
# FUNDING RESPONSES & INTERACTIONS (Phase 2)
# ==============================================================================

class FundingResponse(models.Model):
    """Comments and offers on funding requests"""
    RESPONSE_TYPES = [
        ('comment', 'Comment'),
        ('offer', 'Investment Offer'),
        ('question', 'Question'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    funding_request = models.ForeignKey(FundingRequest, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='funding_responses')
    response_type = models.CharField(max_length=20, choices=RESPONSE_TYPES)
    content = models.TextField()
    
    # For investment offers
    offer_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    equity_requested = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.responder} - {self.response_type} on {self.funding_request}"

    class Meta:
        ordering = ['-created_at']


class FundingNegotiation(models.Model):
    """Private negotiation thread between founder and investor"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    funding_request = models.ForeignKey(FundingRequest, on_delete=models.CASCADE, related_name='negotiations')
    investor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='negotiations_as_investor')
    founder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='negotiations_as_founder')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Negotiation: {self.investor} <> {self.founder}"

    class Meta:
        unique_together = ['funding_request', 'investor']


class NegotiationMessage(models.Model):
    """Messages within a negotiation"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    negotiation = models.ForeignKey(FundingNegotiation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to='negotiation_attachments/', null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class FundingReaction(models.Model):
    """User reactions to funding requests"""
    REACTION_TYPES = [
        ('interested', '👀 Interested'),
        ('promising', '🚀 Promising'),
        ('caution', '⚠️ Caution'),
        ('like', '👍 Like'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    funding_request = models.ForeignKey(FundingRequest, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['funding_request', 'user']


# ==============================================================================
# CAPITAL VENTURES (Phase 4)
# ==============================================================================

class CapitalVenture(models.Model):
    """Investment funds managed by organizations/institutions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    
    # Link to organization or institution (import these if available)
    organization_id = models.UUIDField(null=True, blank=True)
    institution_id = models.UUIDField(null=True, blank=True)
    
    total_fund = models.DecimalField(max_digits=15, decimal_places=2)
    available_fund = models.DecimalField(max_digits=15, decimal_places=2)
    investment_criteria = models.TextField(help_text="What types of businesses this fund invests in")
    
    min_investment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_investment = models.DecimalField(max_digits=15, decimal_places=2)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class VentureBid(models.Model):
    """Bids from capital ventures on funding requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('negotiating', 'In Negotiation'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venture = models.ForeignKey(CapitalVenture, on_delete=models.CASCADE, related_name='bids')
    funding_request = models.ForeignKey(FundingRequest, on_delete=models.CASCADE, related_name='venture_bids')
    
    proposed_amount = models.DecimalField(max_digits=15, decimal_places=2)
    proposed_equity = models.DecimalField(max_digits=5, decimal_places=2)
    terms = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.venture.name} bid on {self.funding_request}"

