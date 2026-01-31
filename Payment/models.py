from django.db import models
from Authentication.models import Profile
from datetime import datetime

# Create your models here.
PAY_OPT = (
    ('paypal', 'PayPal'),
    ('mpesa', 'M-Pesa'),
    ('mastercard', 'MasterCard (Debit or Credit Card)'),
    ('amex', 'American Express'),
    ('discover', 'Discover Card'),
    ('western_union', 'Western Union'),
    ('stripe', 'Stripe'),
    ('cashapp', 'Cash App'),
    ('apple_pay', 'Apple Pay'),
    ('google_pay', 'Google Pay'),
    ('square', 'Square'),
    ('bank_transfer', 'Bank Transfer'),
    ('skrill', 'Skrill'),
    ('neteller', 'Neteller'),
    ('alipay', 'Alipay'),
    ('wechat_pay', 'WeChat Pay'),
    ('jcb', 'JCB'),
    ('diners_club', "Diner's Club"),
    ('unionpay', 'UnionPay'),
    ('maestro', 'Maestro'),
    ('visa', 'Visa'),
    ('venmo', 'Venmo'),
    ('gcash', 'G-Cash'),
    ('comrade_balance', 'Comrade Balance'),
)
PAY_TYPE = (
    ('individual', 'Individual Purchase'),
    ('group', 'Group Purchase')
)

TIER_OPT = (
    ('free', 'Free Membership'),
    ('standard', 'Standard Membership'),
    ('premium', 'Premium Membersip'),
    ('gold', 'Gold Membership'),
)

TRANSACTION_CATEGORY = (
    ('purchase', 'Purchase'),
    ('refund', 'Refund'),
    ('withdrawal', 'Withdrawal'),
    ('deposit', 'Deposit'),
    ('transfer', 'Transfer'),
    ('bid', 'Bid'),
    ('donation', 'Donation'),
    ('subscription', 'Subscription'),
    ('fee', 'Fee'),
    ('contribution', 'Contribution'),
    ('other', 'Other'),
)

TRANSACTION_STATUS = (
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
    ('cancelled', 'Cancelled'),
    ('in_review', 'In Review'),
    ('verified', 'Verified'),
    ('declined', 'Declined'),
    ('authorized', 'Authorized'),
    ('settled', 'Settled'),
    ('reversed', 'Reversed'),
    ('expired', 'Expired'),
)

PAY_OPT_TYPE = (
    ('external', 'External Payment Option'),
    ('internal', 'Internal Payment Option (Comrade Balance)'),
)

class PaymentProfile(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    payment_option = models.CharField(max_length=2000, choices=PAY_OPT, default='paypal')
    payment_number = models.CharField(max_length=10000, default='')
    transaction_token = models.CharField(max_length=10000, default='')
    comrade_balance = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    profile_token = models.CharField(max_length=10000, default='', unique=True)
    
    # Tier Management
    tier = models.CharField(max_length=20, choices=TIER_OPT, default='free')
    
    # Purchase Tracking for Limits
    monthly_purchases = models.IntegerField(default=0)
    last_purchase_month = models.IntegerField(default=1) # Month index (1-12)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['profile_token']),
            models.Index(fields=['tier']),
        ]

class TransactionToken(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    import uuid
    transaction_code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_type = models.CharField(max_length=200, choices=TRANSACTION_CATEGORY, default='purchase')
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    pay_from = models.CharField(max_length=200, choices=PAY_OPT_TYPE, default='external')
    payment_option = models.CharField(max_length=2000, choices=PAY_OPT, default='paypal')
    created_at = models.DateTimeField(default=datetime.now)
    recipient_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='recipient_profile', null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_profile']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['transaction_type']),
        ]

class PaymentAuthorization(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    authorization_code = models.CharField(max_length=10000, unique=True)
    created_at = models.DateTimeField(default=datetime.now)

class PaymentVerification(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    verification_code = models.CharField(max_length=10000, unique=True)
    created_at = models.DateTimeField(default=datetime.now)

class TransactionTracker(models.Model):
    transaction_token = models.ForeignKey(TransactionToken, on_delete=models.CASCADE)
    authorization_token = models.ForeignKey(PaymentAuthorization, on_delete=models.CASCADE, null=True, blank=True)
    verification_token = models.ForeignKey(PaymentVerification, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=200, choices=TRANSACTION_STATUS, default='pending')
    updated_at = models.DateTimeField(default=datetime.now)

class TransactionHistory(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    transaction_token = models.ForeignKey(TransactionToken, on_delete=models.CASCADE)
    authorization_token = models.ForeignKey(PaymentAuthorization, on_delete=models.CASCADE)
    verification_token = models.ForeignKey(PaymentVerification, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=200, choices=PAY_TYPE, default='individual')
    status = models.CharField(max_length=200, choices=TRANSACTION_STATUS, default='pending')
    created_at = models.DateTimeField(default=datetime.now)

class PaymentItem(models.Model):
    name = models.CharField(max_length=2000)
    cost = models.DecimalField(decimal_places=2, max_digits=12)
    quantity = models.FloatField()
    total_cost = models.DecimalField(decimal_places=2, max_digits=12)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        self.total_cost = self.cost * self.quantity
        super().save(*args, **kwargs)

class PaymentLog(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='purchase_profile')
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    purchase_item = models.ManyToManyField(PaymentItem, blank=True)
    payment_type = models.CharField(max_length=2000, choices=PAY_TYPE, default='individual')
    payment_date = models.DateTimeField(default=datetime.now)
    recipient = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='sale_profile')
    notes = models.TextField(blank=True)

# Payment Group - Group savings/purchases
class PaymentGroups(models.Model):
    import uuid
    
    CONTRIBUTION_TYPE_CHOICES = (
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
        ('flexible', 'Flexible'),
    )
    
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('one_time', 'One Time'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=5000)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='created_groups', blank=True, null=True)
    max_capacity = models.IntegerField(default=3) # Default to Free tier limit
    tier = models.CharField(max_length=200, choices=TIER_OPT, default='free')
    item_grouping = models.ManyToManyField(PaymentItem, blank=True)
    
    # Group settings
    target_amount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    current_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    expiry_date = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)  # Alternative deadline field
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)  # Visibility setting
    auto_purchase = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=True)
    
    # Contribution settings
    contribution_type = models.CharField(max_length=20, choices=CONTRIBUTION_TYPE_CHOICES, default='flexible')
    contribution_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['creator']),
            models.Index(fields=['is_active']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name_plural = 'Payment Groups'
    
    def __str__(self):
        return self.name

# Payment Group Members
class PaymentGroupMember(models.Model):
    payment_group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='members')
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    contribution_percentage = models.DecimalField(decimal_places=2, max_digits=5, default=0.00)
    total_contributed = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    joined_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['payment_group', 'payment_profile']
        indexes = [
            models.Index(fields=['payment_group']),
            models.Index(fields=['payment_profile']),
        ]

# Contribution tracking
class Contribution(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey(PaymentGroupMember, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    transaction = models.ForeignKey(TransactionToken, on_delete=models.SET_NULL, null=True, blank=True)
    contributed_at = models.DateTimeField(default=datetime.now)
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_group']),
            models.Index(fields=['-contributed_at']),
        ]

# Standing Orders for recurring contributions
class StandingOrder(models.Model):
    member = models.ForeignKey(PaymentGroupMember, on_delete=models.CASCADE, related_name='standing_orders')
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    frequency = models.CharField(max_length=50, choices=(
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
    ))
    next_contribution_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['next_contribution_date', 'is_active']),
        ]

# Group Invitations
class GroupInvitation(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='invitations')
    invited_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='sent_invitations')
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ), default='pending')
    invitation_link = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(default=datetime.now)
    expires_at = models.DateTimeField()
    
    class Meta:
        unique_together = ['payment_group', 'invited_profile']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]

# Shop Products / Services
class Product(models.Model):
    PRODUCT_TYPES = (
        ('physical', 'Physical Product'),
        ('digital', 'Digital Product'),
        ('service', 'Service'),
        ('subscription', 'Subscription'), # Resource, Specialization, etc.
        ('recommendation', 'Recommendation'),
    )
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(decimal_places=2, max_digits=12)
    product_type = models.CharField(max_length=50, choices=PRODUCT_TYPES, default='physical')
    image_url = models.URLField(blank=True, null=True)
    
    # Logic flags
    is_sharable = models.BooleanField(default=True) # Can be bought by a group
    requires_subscription = models.BooleanField(default=False)
    duration_days = models.IntegerField(default=30) # For subscriptions
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# User Subscription to Products/Services
class UserSubscription(models.Model):
    user = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='subscriptions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['end_date']),
        ]

# Group Target/Goals (Piggy Bank)
class GroupTarget(models.Model):
    LOCK_OPTIONS = (
        ('unlocked', 'Unlocked'),
        ('locked', 'Locked'),  # Simple locked status
        ('locked_time', 'Locked until Date'),
        ('locked_goal', 'Locked until Goal'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    # Owner for individual piggy banks (null if group piggy bank)
    owner = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='individual_piggy_banks')
    # Group piggy bank - null for individual
    payment_group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='targets', null=True, blank=True)
    target_item = models.ForeignKey(PaymentItem, on_delete=models.SET_NULL, null=True, blank=True)
    target_product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True) # Link to Shop Product
    
    name = models.CharField(max_length=255, default='Piggy Bank')
    target_amount = models.DecimalField(decimal_places=2, max_digits=12)
    current_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Piggy Bank Logic
    locking_status = models.CharField(max_length=20, choices=LOCK_OPTIONS, default='unlocked')
    maturity_date = models.DateTimeField(null=True, blank=True)
    is_sharable = models.BooleanField(default=True) # If false, funds are segregated per user
    
    is_bid = models.BooleanField(default=False) # Is this a bid?
    bid_status = models.CharField(max_length=20, default='pending') # pending, accumulated, confirmed
    
    achieved = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_group', 'achieved']),
            models.Index(fields=['owner', 'achieved']),
        ]
    
    def is_individual(self):
        return self.payment_group is None and self.owner is not None

# Individual Savings within a Group Target (for non-sharable)
class IndividualShare(models.Model):
    target = models.ForeignKey(GroupTarget, on_delete=models.CASCADE, related_name='shares')
    member = models.ForeignKey(PaymentGroupMember, on_delete=models.CASCADE)
    target_amount = models.DecimalField(decimal_places=2, max_digits=12)
    current_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    quantity = models.IntegerField(default=1) # Target quantity of item
    achieved = models.BooleanField(default=False)


PARTNER_TYPES = (
    ('distributor', 'Distributor'),
    ('supplier', 'Supplier'),
    ('publisher', 'Publisher'),
    ('author', 'Author'),
    ('retailer', 'Retailer'),
    ('wholesaler', 'Wholesaler'),
    ('manufacturer', 'Manufacturer'),
    ('affiliate', 'Affiliate'),
    ('sponsor', 'Sponsor'),
    ('advertiser', 'Advertiser'),
    ('content_creator', 'Content Creator'),
)

PARTNER_STATUS = (
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('suspended', 'Suspended'),
    ('inactive', 'Inactive'),
)


class Partner(models.Model):
    """Platform partners: distributors, suppliers, publishers, authors, etc."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='partnerships')
    
    # Partner info
    partner_type = models.CharField(max_length=50, choices=PARTNER_TYPES)
    business_name = models.CharField(max_length=500)
    business_registration = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    
    # Contact
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PARTNER_STATUS, default='pending')
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Commission/Revenue
    commission_rate = models.DecimalField(decimal_places=2, max_digits=5, default=10.00)  # percentage
    total_earnings = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    pending_payout = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    
    # Documents
    business_license = models.FileField(upload_to='partners/licenses/', null=True, blank=True)
    verification_document = models.FileField(upload_to='partners/verification/', null=True, blank=True)
    
    # Bio/Description
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='partners/logos/', null=True, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['partner_type', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.business_name} ({self.get_partner_type_display()})"


class PartnerApplication(models.Model):
    """Application to become a platform partner"""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='partner_applications')
    
    # Application details
    partner_type = models.CharField(max_length=50, choices=PARTNER_TYPES)
    business_name = models.CharField(max_length=500)
    business_registration = models.CharField(max_length=200, blank=True)
    
    # Contact
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Description
    description = models.TextField(help_text='Describe your business and why you want to partner with us')
    products_services = models.TextField(help_text='What products or services will you offer?')
    
    # Documents
    business_license = models.FileField(upload_to='partner_applications/licenses/', null=True, blank=True)
    supporting_document = models.FileField(upload_to='partner_applications/documents/', null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PARTNER_STATUS, default='pending')
    reviewed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Resulting Partner
    partner = models.OneToOneField(Partner, on_delete=models.SET_NULL, null=True, blank=True, related_name='application')
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['applicant']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.business_name} - {self.get_partner_type_display()} Application"

