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
    payment_number = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
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
    
    # Group Type
    GROUP_TYPE_CHOICES = (
        ('standard', 'Standard Group'),
        ('piggy_bank', 'Piggy Bank Group'),
    )
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, default='standard')
    
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
    invited_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, null=True, blank=True)
    invited_email = models.EmailField(null=True, blank=True)
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


class AgentApplication(models.Model):
    """Application to become a specific type of Agent (e.g., Delivery)"""
    AGENT_TYPES = (
        ('delivery', 'Delivery Agent'),
        ('sales', 'Sales Agent'),
        ('support', 'Support Agent'),
    )
    
    applicant = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='agent_applications')
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPES, default='delivery')
    vehicle_type = models.CharField(max_length=50, blank=True)  # For delivery
    license_plate = models.CharField(max_length=20, blank=True) # For delivery
    
    # Coverage
    operating_zone = models.CharField(max_length=100)
    availability = models.JSONField(default=dict) # e.g. {"mon": "9-5", "tue": "9-5"}
    
    # Documents
    id_card = models.FileField(upload_to='agent_applications/ids/')
    driving_license = models.FileField(upload_to='agent_applications/licenses/', null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PARTNER_STATUS, default='pending')
    reviewed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_agent_apps')
    review_notes = models.TextField(blank=True)
    result_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"{self.applicant.user.username} - {self.get_agent_type_display()}"


class SupplierApplication(models.Model):
    """Application to become a Product/Service Supplier"""
    applicant = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='supplier_applications')
    business_name = models.CharField(max_length=200)
    business_registration_number = models.CharField(max_length=100, blank=True)
    
    categories = models.JSONField(default=list) # e.g. ["Electronics", "Fashion"]
    min_order_quantity = models.IntegerField(default=1)
    wholesale_pricing_available = models.BooleanField(default=False)
    
    # Documents
    catalog_sample = models.FileField(upload_to='supplier_applications/catalogs/', null=True, blank=True)
    business_permit = models.FileField(upload_to='supplier_applications/permits/')
    
    status = models.CharField(max_length=20, choices=PARTNER_STATUS, default='pending')
    reviewed_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_supplier_apps')
    
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"{self.business_name} - Supplier Application"


class ShopRegistration(models.Model):
    """Model for a User-created Shop (Storefront)"""
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='shops')
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    logo = models.ImageField(upload_to='shops/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='shops/banners/', null=True, blank=True)
    
    # Configuration
    currency = models.CharField(max_length=3, default='KES')
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


# ============================================================================
# MARKETPLACE: Establishments, Menus, Hotels, Services, Orders, Reviews
# ============================================================================

ESTABLISHMENT_TYPES = (
    ('restaurant', 'Restaurant'),
    ('hotel', 'Hotel'),
    ('coffee_shop', 'Coffee Shop'),
    ('supermarket', 'Supermarket'),
    ('store', 'Store'),
    ('service_provider', 'Service Provider'),
    ('food_shop', 'Food Shop'),
)

class Establishment(models.Model):
    """A restaurant, hotel, coffee shop, supermarket, store, or service provider."""
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='establishments')
    organisation = models.ForeignKey(
        'Organisation.Organisation', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='establishments'
    )
    
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='establishments/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='establishments/banners/', null=True, blank=True)
    
    establishment_type = models.CharField(max_length=50, choices=ESTABLISHMENT_TYPES)
    categories = models.JSONField(default=list, blank=True, help_text='e.g. ["Italian", "Fine Dining"]')
    
    # Location
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Operations
    opening_hours = models.JSONField(default=dict, blank=True, help_text='e.g. {"mon": "08:00-22:00"}')
    
    # Ratings (denormalized for performance)
    rating = models.DecimalField(decimal_places=2, max_digits=3, default=0.00)
    review_count = models.IntegerField(default=0)
    
    # Delivery/service modes
    delivery_available = models.BooleanField(default=False)
    pickup_available = models.BooleanField(default=True)
    dine_in_available = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['establishment_type']),
            models.Index(fields=['is_active', 'establishment_type']),
            models.Index(fields=['-rating']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_establishment_type_display()})"


class EstablishmentBranch(models.Model):
    """Branch/location of an establishment."""
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=300)
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    opening_hours = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    def __str__(self):
        return f"{self.establishment.name} - {self.name}"


class MenuItem(models.Model):
    """Food/product item offered by an establishment (restaurant, café, food shop)."""
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=12)
    category = models.CharField(max_length=200, blank=True, help_text='e.g. Appetizers, Main Course, Beverages')
    image = models.ImageField(upload_to='menu_items/', null=True, blank=True)
    is_available = models.BooleanField(default=True)
    preparation_time = models.IntegerField(default=15, help_text='Estimated preparation time in minutes')
    dietary_tags = models.JSONField(default=list, blank=True, help_text='e.g. ["vegan", "gluten-free"]')
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['establishment', 'is_available']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.establishment.name}"


ROOM_TYPES = (
    ('standard', 'Standard Room'),
    ('deluxe', 'Deluxe Room'),
    ('suite', 'Suite'),
    ('event_room', 'Event Room'),
    ('conference_room', 'Conference Room'),
)

class HotelRoom(models.Model):
    """Hotel rooms and event/conference rooms."""
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='rooms')
    room_type = models.CharField(max_length=50, choices=ROOM_TYPES, default='standard')
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    price_per_night = models.DecimalField(decimal_places=2, max_digits=12)
    capacity = models.IntegerField(default=2)
    amenities = models.JSONField(default=list, blank=True, help_text='e.g. ["WiFi", "AC", "Mini Bar"]')
    images = models.JSONField(default=list, blank=True, help_text='List of image URLs')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['establishment', 'room_type', 'is_available']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()}) - {self.establishment.name}"


BOOKING_TYPES = (
    ('hotel_stay', 'Hotel Stay'),
    ('event_room', 'Event Room Booking'),
    ('restaurant_reservation', 'Restaurant Reservation'),
)

BOOKING_STATUS = (
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('cancelled', 'Cancelled'),
    ('completed', 'Completed'),
    ('no_show', 'No Show'),
)

class Booking(models.Model):
    """Reservations for hotels, event rooms, and restaurants."""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='bookings')
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='bookings')
    hotel_room = models.ForeignKey(HotelRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    
    booking_type = models.CharField(max_length=50, choices=BOOKING_TYPES)
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    guests = models.IntegerField(default=1)
    total_price = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    special_requests = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['establishment', 'check_in']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_booking_type_display()} at {self.establishment.name} by {self.user}"


SERVICE_MODE = (
    ('mobile', 'Mobile Service (Provider comes to you)'),
    ('in_person', 'In-Person (Visit the service point)'),
    ('both', 'Both Mobile and In-Person'),
)

class ServiceOffering(models.Model):
    """Services offered by businesses or individuals with appointment booking."""
    provider = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='service_offerings')
    establishment = models.ForeignKey(
        Establishment, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='service_offerings'
    )
    
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=12)
    duration_minutes = models.IntegerField(default=60)
    
    service_mode = models.CharField(max_length=20, choices=SERVICE_MODE, default='in_person')
    category = models.CharField(max_length=200, blank=True, help_text='e.g. Hair, Plumbing, Tutoring')
    image = models.ImageField(upload_to='services/', null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['provider', 'is_active']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} by {self.provider}"


class ServiceTimeSlot(models.Model):
    """Preset available time slots for service delivery."""
    service = models.ForeignKey(ServiceOffering, on_delete=models.CASCADE, related_name='time_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_booked = models.BooleanField(default=False)
    booked_by = models.ForeignKey(
        Profile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='booked_slots'
    )
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['service', 'date', 'is_booked']),
        ]
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"{self.service.name} - {self.date} {self.start_time}-{self.end_time}"


ORDER_TYPES = (
    ('product', 'Product Purchase'),
    ('food', 'Food Order'),
    ('hotel_booking', 'Hotel Booking'),
    ('service_appointment', 'Service Appointment'),
)

DELIVERY_MODE = (
    ('pickup', 'Pickup'),
    ('delivery', 'Delivery'),
    ('appointment', 'Appointment Attendance'),
)

ORDER_STATUS = (
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('preparing', 'Preparing'),
    ('ready', 'Ready for Pickup'),
    ('out_for_delivery', 'Out for Delivery'),
    ('delivered', 'Delivered'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
)

class Order(models.Model):
    """Unified order model for all purchase types."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    buyer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='orders')
    establishment = models.ForeignKey(
        Establishment, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    
    order_type = models.CharField(max_length=50, choices=ORDER_TYPES, default='product')
    delivery_mode = models.CharField(max_length=20, choices=DELIVERY_MODE, default='pickup')
    
    # Payment
    payment_type = models.CharField(max_length=20, choices=PAY_TYPE, default='individual')
    payment_group = models.ForeignKey(
        PaymentGroups, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    transaction = models.ForeignKey(
        TransactionToken, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    
    # Order details
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    total_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Service appointment reference
    service_time_slot = models.ForeignKey(
        ServiceTimeSlot, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    
    # Booking reference
    booking = models.ForeignKey(
        Booking, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['establishment', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.id} - {self.get_order_type_display()} ({self.get_status_display()})"


class OrderItem(models.Model):
    """Individual items within an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=300, blank=True, help_text='Snapshot of item name at order time')
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    subtotal = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    
    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        if not self.name:
            if self.product:
                self.name = self.product.name
            elif self.menu_item:
                self.name = self.menu_item.name
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.quantity}x {self.name} = {self.subtotal}"


class Review(models.Model):
    """Reviews for establishments."""
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='reviews')
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(default=5, help_text='Rating from 1 to 5')
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=datetime.now)
    
    class Meta:
        unique_together = ['user', 'establishment']
        indexes = [
            models.Index(fields=['establishment', '-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} rated {self.establishment.name} {self.rating}/5"
