from django.db import models
from Authentication.models import Profile
from datetime import datetime
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey

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
    ('comrade_balance', 'Qomrade Balance'),
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
    ('internal', 'Internal Payment Option (Qomrade Balance)'),
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
    created_at = models.DateTimeField(default=timezone.now)
    recipient_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='recipient_profile', null=True, blank=True)
    payment_group = models.ForeignKey('PaymentGroups', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_profile']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['transaction_type']),
        ]

class PaymentAuthorization(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    authorization_code = models.CharField(max_length=10000, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

class PaymentVerification(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    verification_code = models.CharField(max_length=10000, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

class TransactionTracker(models.Model):
    transaction_token = models.ForeignKey(TransactionToken, on_delete=models.CASCADE)
    authorization_token = models.ForeignKey(PaymentAuthorization, on_delete=models.CASCADE, null=True, blank=True)
    verification_token = models.ForeignKey(PaymentVerification, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=200, choices=TRANSACTION_STATUS, default='pending')
    updated_at = models.DateTimeField(default=timezone.now)

class TransactionHistory(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    transaction_token = models.ForeignKey(TransactionToken, on_delete=models.CASCADE)
    authorization_token = models.ForeignKey(PaymentAuthorization, on_delete=models.CASCADE)
    verification_token = models.ForeignKey(PaymentVerification, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=200, choices=PAY_TYPE, default='individual')
    status = models.CharField(max_length=200, choices=TRANSACTION_STATUS, default='pending')
    created_at = models.DateTimeField(default=timezone.now)

class PaymentItem(models.Model):
    name = models.CharField(max_length=2000)
    cost = models.DecimalField(decimal_places=2, max_digits=12)
    quantity = models.FloatField()
    total_cost = models.DecimalField(decimal_places=2, max_digits=12)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def save(self, *args, **kwargs):
        self.total_cost = self.cost * self.quantity
        super().save(*args, **kwargs)

class PaymentLog(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='purchase_profile')
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    purchase_item = models.ManyToManyField(PaymentItem, blank=True)
    payment_type = models.CharField(max_length=2000, choices=PAY_TYPE, default='individual')
    payment_date = models.DateTimeField(default=timezone.now)
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
    cover_photo = models.ImageField(upload_to='group_covers/', blank=True, null=True)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='created_groups', blank=True, null=True)
    max_capacity = models.IntegerField(default=3) # Default to Free tier limit
    tier = models.CharField(max_length=200, choices=TIER_OPT, default='free')
    item_grouping = models.ManyToManyField(PaymentItem, blank=True)
    
    # Room linkage – auto-create a Room alongside this group
    linked_room = models.ForeignKey(
        'Rooms.Room', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='linked_payment_group'
    )
    auto_create_room = models.BooleanField(default=True)
    
    # Group settings
    target_amount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    current_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    expiry_date = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)  # Alternative deadline field
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)  # Visibility setting
    auto_purchase = models.BooleanField(default=False)
    requires_approval = models.BooleanField(default=True)
    allow_anonymous = models.BooleanField(default=False)  # Allow anonymous membership
    
    # Application & Entry Fee Requirements
    entry_fee_required = models.BooleanField(default=False)
    entry_fee_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    custom_application_questions = models.JSONField(default=list, blank=True, help_text='List of questions for applicants')
    
    # Contribution settings
    contribution_type = models.CharField(max_length=20, choices=CONTRIBUTION_TYPE_CHOICES, default='flexible')
    contribution_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    
    # Group Type
    GROUP_TYPE_CHOICES = (
        ('standard', 'Standard Group'),
        ('piggy_bank', 'Piggy Bank Group'),
        ('kitty', 'Entity Kitty'),
    )
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, default='standard')
    
    # Generic relation to any entity (Business, CapitalVenture, Shop, Org, etc.)
    entity_content_type = models.ForeignKey(
        'contenttypes.ContentType', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='kitty_groups'
    )
    entity_object_id = models.CharField(max_length=255, blank=True, null=True)
    entity = GenericForeignKey('entity_content_type', 'entity_object_id')
    
    # Group lifecycle / maturation
    is_matured = models.BooleanField(default=False)  # True when deadline has passed
    termination_requested_by = models.ManyToManyField(
        PaymentProfile, blank=True, related_name='termination_requests'
    )  # Members who agreed to terminate
    is_terminated = models.BooleanField(default=False)
    
    # --- New: Pitch & Proposition ---
    investment_pitch = models.TextField(blank=True, default='', help_text='Investment or donation pitch description')
    loan_proposition = models.TextField(blank=True, default='', help_text='Loan offering/proposition details')
    parent_group = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sub_groups', help_text='Parent group (expansion of)'
    )
    joining_minimum = models.DecimalField(
        decimal_places=2, max_digits=12, default=0.00,
        help_text='Minimum wallet balance required to join'
    )
    accent_color = models.CharField(
        max_length=7, default='#6366f1', blank=True,
        help_text='Hex accent colour for UI theming, e.g. #6366f1'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
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


class GroupPhase(models.Model):
    """Tracks named phases (e.g. Seed Round, Growth) with targets and proportions."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='phases')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    proportion = models.DecimalField(decimal_places=2, max_digits=5, default=0.00, help_text='% of total target')
    current_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [models.Index(fields=['group', 'order'])]

    def __str__(self):
        return f"{self.group.name} — {self.name}"


class GroupPost(models.Model):
    """Discord-style post in a group's public discourse feed."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='group_posts')
    content = models.TextField()
    image = models.ImageField(upload_to='group_posts/', blank=True, null=True)
    is_pinned = models.BooleanField(default=False)
    reactions = models.JSONField(default=dict, blank=True, help_text='{"👍": [user_id,...], ...}')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
        ]

    def __str__(self):
        return f"Post by {self.author} in {self.group.name}"


class GroupPostReply(models.Model):
    """Threaded reply on a GroupPost."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(GroupPost, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='group_replies')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.author} on {self.post_id}"


class GroupCheckoutRequest(models.Model):
    """Tracks a proposed group checkout that requires member approval."""
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='checkout_requests')
    initiator = models.ForeignKey(PaymentProfile, on_delete=models.SET_NULL, null=True, related_name='initiated_checkouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    items_payload = models.JSONField(default=list, help_text="Cart items and checkout payload")
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved & Processed'),
        ('rejected', 'Rejected'),
        ('failed', 'Processing Failed')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    approvals = models.ManyToManyField(PaymentProfile, related_name='approved_checkouts', blank=True)
    rejections = models.ManyToManyField(PaymentProfile, related_name='rejected_checkouts', blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Checkout Request for {self.group.name} - KES {self.amount}"

    def get_approval_percentage(self):
        total_members = self.group.members.count()
        if total_members == 0:
            return 0
        return (self.approvals.count() / total_members) * 100

# Payment Group Members
class PaymentGroupMember(models.Model):
    payment_group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='members')
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)  # Anonymous membership
    anonymous_alias = models.CharField(max_length=100, blank=True)  # e.g. "Member-A3F2"
    contribution_percentage = models.DecimalField(decimal_places=2, max_digits=5, default=0.00)
    total_contributed = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['payment_group', 'payment_profile']
        indexes = [
            models.Index(fields=['payment_group']),
            models.Index(fields=['payment_profile']),
        ]
    
    def save(self, *args, **kwargs):
        if self.is_anonymous and not self.anonymous_alias:
            import secrets
            self.anonymous_alias = f"Member-{secrets.token_hex(2).upper()}"
        super().save(*args, **kwargs)

# Contribution tracking
class Contribution(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey(PaymentGroupMember, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    transaction = models.ForeignKey(TransactionToken, on_delete=models.SET_NULL, null=True, blank=True)
    contributed_at = models.DateTimeField(default=timezone.now)
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
    created_at = models.DateTimeField(default=timezone.now)
    
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
    created_at = models.DateTimeField(default=timezone.now)
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
    
    # Inventory Tracking
    stock_quantity = models.IntegerField(default=0)
    sku = models.CharField(max_length=100, blank=True)
    
    # Logic flags
    is_sharable = models.BooleanField(default=True) # Sharable = 1 product for all group members; Non-sharable = 1 per member
    allow_group_purchase = models.BooleanField(default=True) # If False, product is strictly individual purchase only
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
    
    SAVINGS_TYPE_CHOICES = (
        ('normal', 'Normal Piggy Bank'),
        ('locked', 'Locked Savings'),
        ('fixed_deposit', 'Fixed Deposit'),
    )
    
    CONTRIBUTION_MODE_CHOICES = (
        ('equal', 'Equal Contributions'),
        ('proportional', 'Proportional Contributions'),
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
    
    # Savings type — determines withdrawal rules and interest
    savings_type = models.CharField(max_length=20, choices=SAVINGS_TYPE_CHOICES, default='normal')
    
    # Fixed deposit configuration
    interest_rate = models.DecimalField(
        decimal_places=2, max_digits=6, default=0.00,
        help_text='Annual interest rate % (for fixed_deposit type)'
    )
    penalty_rate = models.DecimalField(
        decimal_places=2, max_digits=6, default=2.00,
        help_text='Early withdrawal penalty % (for fixed_deposit type)'
    )
    accrued_interest = models.DecimalField(
        decimal_places=2, max_digits=12, default=0.00,
        help_text='Total interest earned so far'
    )
    last_interest_date = models.DateTimeField(null=True, blank=True)
    
    # Contribution mode for group piggy banks
    contribution_mode = models.CharField(
        max_length=20, choices=CONTRIBUTION_MODE_CHOICES, default='equal',
        help_text='How group members contribute (equal or proportional)'
    )
    
    # Piggy Bank Logic
    locking_status = models.CharField(max_length=20, choices=LOCK_OPTIONS, default='unlocked')
    maturity_date = models.DateTimeField(null=True, blank=True)
    is_sharable = models.BooleanField(default=True) # If false, funds are segregated per user
    
    is_bid = models.BooleanField(default=False) # Is this a bid?
    bid_status = models.CharField(max_length=20, default='pending') # pending, accumulated, confirmed
    
    achieved = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    MAX_INDIVIDUAL_PIGGY_BANKS = 3
    MAX_GROUP_PIGGY_MEMBERSHIPS = 3
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_group', 'achieved']),
            models.Index(fields=['owner', 'achieved']),
            models.Index(fields=['savings_type']),
        ]
    
    def is_individual(self):
        return self.payment_group is None and self.owner is not None
    
    @property
    def is_matured(self):
        """Check if the piggy bank has reached its maturity date."""
        if self.maturity_date and timezone.now() >= self.maturity_date:
            return True
        return False
    
    def can_withdraw(self):
        """Check withdrawal eligibility based on savings_type."""
        if self.savings_type == 'locked':
            # Locked: no withdrawals until maturity
            return self.is_matured, 'Locked savings cannot be withdrawn until maturity date.'
        elif self.savings_type == 'fixed_deposit':
            # Fixed deposit: can withdraw anytime but penalty applies before maturity
            return True, None
        else:
            # Normal: anytime
            return True, None
    
    def calculate_withdrawal_penalty(self, amount):
        """Calculate penalty for early withdrawal on fixed_deposit type."""
        if self.savings_type == 'fixed_deposit' and not self.is_matured:
            penalty = amount * (self.penalty_rate / 100)
            return penalty
        return 0

# Individual Savings within a Group Target (for non-sharable)
class IndividualShare(models.Model):
    target = models.ForeignKey(GroupTarget, on_delete=models.CASCADE, related_name='shares')
    member = models.ForeignKey(PaymentGroupMember, on_delete=models.CASCADE)
    target_amount = models.DecimalField(decimal_places=2, max_digits=12)
    current_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    quantity = models.IntegerField(default=1) # Target quantity of item
    achieved = models.BooleanField(default=False)


# ============================================================================
# DONATIONS & CHARITY
# ============================================================================

DONATION_STATUS = (
    ('draft', 'Draft'),
    ('collecting', 'Collecting Contributions'),
    ('submitted', 'Submitted to Recipient'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
)

DONATION_MODE = (
    ('lump_sum', 'Lump Sum (Group dictates once)'),
    ('individual_share', 'Individual Share (Portion-based)'),
    ('independent_quote', 'Independent Quoting (Each member quotes)'),
)

DONATION_FREQUENCY = (
    ('one_time', 'One Time'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
)

class Donation(models.Model):
    """Tracks individual or group donations to charities/businesses/orgs."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    DONOR_TYPE_CHOICES = (
        ('individual', 'Individual'),
        ('group', 'Group'),
    )
    donor_type = models.CharField(max_length=20, choices=DONOR_TYPE_CHOICES, default='individual')
    
    # Individual donor (set for individual donations)
    donor_profile = models.ForeignKey(
        PaymentProfile, on_delete=models.CASCADE, null=True, blank=True,
        related_name='donations'
    )
    # Group donor (set for group donations)
    payment_group = models.ForeignKey(
        PaymentGroups, on_delete=models.CASCADE, null=True, blank=True,
        related_name='donations'
    )
    
    # Group donation mode
    donation_mode = models.CharField(
        max_length=20, choices=DONATION_MODE, default='lump_sum',
        help_text='How group members contribute to this donation'
    )
    
    # Generic Campaign details
    name = models.CharField(max_length=255, default='Untitled Campaign')
    category = models.CharField(max_length=100, default='General charity', help_text='e.g., Health, Education, Relief')

    
    # Recipient — generic FK to charity, business, org, etc.
    recipient_content_type = models.ForeignKey(
        'contenttypes.ContentType', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='received_donations'
    )
    recipient_object_id = models.CharField(max_length=255, blank=True, null=True)
    recipient = GenericForeignKey('recipient_content_type', 'recipient_object_id')
    recipient_name = models.CharField(max_length=500, blank=True, help_text='Display name of recipient')
    
    # Amount tracking
    total_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    amount_collected = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    
    # Scheduling
    is_recurring = models.BooleanField(default=False)
    frequency = models.CharField(max_length=20, choices=DONATION_FREQUENCY, default='one_time')
    next_due_date = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True, help_text='Deadline for group contributions')
    
    # Status & metadata
    VISIBILITY_CHOICES = (
        ('internal', 'Internal (Group Only)'),
        ('external', 'External (Public)'),
    )
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='external')
    status = models.CharField(max_length=20, choices=DONATION_STATUS, default='draft')
    description = models.TextField(blank=True)
    
    # Linked vote (for lump_sum group donations)
    approval_vote = models.ForeignKey(
        'GroupVote', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='donation_approval'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['donor_profile', 'status']),
            models.Index(fields=['payment_group', 'status']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        origin = self.payment_group.name if self.payment_group else 'Individual'
        return f"Donation to {self.recipient_name} ({origin}) - {self.total_amount}"


class DonationContribution(models.Model):
    """Tracks each member's contribution to a group donation."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey(
        PaymentGroupMember, on_delete=models.CASCADE, null=True, blank=True,
        related_name='donation_contributions'
    )
    donor_profile = models.ForeignKey(
        PaymentProfile, on_delete=models.CASCADE,
        related_name='donation_contribution_records'
    )
    
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    
    CONTRIBUTION_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('submitted', 'Submitted to Recipient'),
    )
    status = models.CharField(max_length=20, choices=CONTRIBUTION_STATUS, default='pending')
    
    transaction = models.ForeignKey(
        TransactionToken, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='donation_contributions'
    )
    
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['donation', 'status']),
            models.Index(fields=['donor_profile']),
        ]
    
    def __str__(self):
        return f"Contribution of {self.amount} to {self.donation.recipient_name}"


# ============================================================================
# GROUP INVESTMENTS
# ============================================================================

INVESTMENT_STATUS = (
    ('quoting', 'Members Are Quoting'),
    ('collecting', 'Collecting Payments'),
    ('invested', 'Invested'),
    ('matured', 'Matured / Returns Available'),
    ('closed', 'Closed'),
    ('cancelled', 'Cancelled'),
)

QUOTING_MODE = (
    ('lump_sum', 'Lump Sum (One member proposes, group approves)'),
    ('proportional', 'Proportional Quoting (Each quotes, profits split by ratio)'),
    ('independent', 'Independent (Each invests alone, no coordination)'),
)

class GroupInvestment(models.Model):
    """Tracks group investment activities with multiple quoting modes."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    payment_group = models.ForeignKey(
        PaymentGroups, on_delete=models.CASCADE, related_name='group_investments'
    )
    
    # Investment target — link to opportunity or venture
    investment_opportunity = models.ForeignKey(
        'Funding.InvestmentOpportunity', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='group_investments'
    )
    capital_venture = models.ForeignKey(
        'Funding.CapitalVenture', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='group_investments'
    )
    
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    
    # Quoting mode
    quoting_mode = models.CharField(max_length=20, choices=QUOTING_MODE, default='proportional')
    
    # Amounts
    total_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    amount_collected = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    
    # Returns tracking
    total_returns = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    net_profit_loss = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    
    # Status
    status = models.CharField(max_length=20, choices=INVESTMENT_STATUS, default='quoting')
    
    # Linked approval vote (for lump_sum mode)
    approval_vote = models.ForeignKey(
        'GroupVote', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='investment_approval'
    )
    
    # Initiator
    initiated_by = models.ForeignKey(
        PaymentProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='initiated_investments'
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_group', 'status']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Investment: {self.name} ({self.payment_group.name})"


class InvestmentQuote(models.Model):
    """Tracks individual member quotes and ownership within a group investment."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    group_investment = models.ForeignKey(
        GroupInvestment, on_delete=models.CASCADE, related_name='quotes'
    )
    member = models.ForeignKey(
        PaymentGroupMember, on_delete=models.CASCADE, related_name='investment_quotes'
    )
    
    quoted_amount = models.DecimalField(decimal_places=2, max_digits=12)
    ownership_percentage = models.DecimalField(
        decimal_places=4, max_digits=8, default=0.00,
        help_text='Auto-calculated based on proportional contribution'
    )
    
    # Returns allocated to this member
    allocated_returns = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    
    QUOTE_STATUS = (
        ('pending', 'Quote Submitted'),
        ('confirmed', 'Payment Confirmed'),
        ('paid', 'Paid / Invested'),
    )
    status = models.CharField(max_length=20, choices=QUOTE_STATUS, default='pending')
    
    transaction = models.ForeignKey(
        TransactionToken, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='investment_quotes'
    )
    
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['group_investment', 'member']
        indexes = [
            models.Index(fields=['group_investment', 'status']),
        ]
    
    def __str__(self):
        return f"{self.member} quoted {self.quoted_amount} ({self.ownership_percentage}%)"


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
    
    created_at = models.DateTimeField(default=timezone.now)
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
    
    created_at = models.DateTimeField(default=timezone.now)
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
    
    created_at = models.DateTimeField(default=timezone.now)
    
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
    
    created_at = models.DateTimeField(default=timezone.now)
    
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
    
    created_at = models.DateTimeField(default=timezone.now)
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
    
    created_at = models.DateTimeField(default=timezone.now)
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
    created_at = models.DateTimeField(default=timezone.now)
    
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
    created_at = models.DateTimeField(default=timezone.now)
    
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
    created_at = models.DateTimeField(default=timezone.now)
    
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
    
    created_at = models.DateTimeField(default=timezone.now)
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
    
    SERVICE_TYPES = (
        ('appointment', 'Appointment (e.g. In-person/Remote session)'),
        ('call_service', 'Call Service (e.g. Phone consultation)'),
        ('online_sale', 'Online Sale (e.g. Digital download)'),
    )
    
    service_mode = models.CharField(max_length=20, choices=SERVICE_MODE, default='in_person')
    service_type = models.CharField(max_length=30, choices=SERVICE_TYPES, default='appointment')
    setup_data = models.JSONField(default=dict, blank=True, help_text='Stores specific fields: delay_minutes, break_minutes, max_bookings, tags, call_number')
    
    category = models.CharField(max_length=200, blank=True, help_text='e.g. Hair, Plumbing, Tutoring')
    image = models.ImageField(upload_to='services/', null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
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
    created_at = models.DateTimeField(default=timezone.now)
    
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
    
    # Offline sales tracking
    SALES_CHANNEL_CHOICES = (
        ('online', 'Online'),
        ('in_store', 'In-Store/Offline'),
        ('pop_up', 'Pop-up Market'),
    )
    sales_channel = models.CharField(max_length=20, choices=SALES_CHANNEL_CHOICES, default='online')
    is_offline = models.BooleanField(default=False)
    
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
    
    created_at = models.DateTimeField(default=timezone.now)
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
    item_type = models.CharField(max_length=50, default='product')
    metadata = models.JSONField(default=dict, blank=True)
    
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
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['user', 'establishment']
        indexes = [
            models.Index(fields=['establishment', '-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} rated {self.establishment.name} {self.rating}/5"


# ============================================================================
# SAVED PAYMENT METHODS
# ============================================================================

PAYMENT_METHOD_TYPE = (
    ('card', 'Credit/Debit Card'),
    ('mpesa', 'M-Pesa'),
    ('paypal', 'PayPal'),
    ('bank_transfer', 'Bank Transfer'),
    ('equity', 'Equity Bank'),
)

CARD_BRAND = (
    ('visa', 'Visa'),
    ('mastercard', 'Mastercard'),
    ('amex', 'American Express'),
    ('discover', 'Discover'),
    ('jcb', 'JCB'),
    ('diners_club', "Diner's Club"),
    ('unionpay', 'UnionPay'),
    ('maestro', 'Maestro'),
    ('unknown', 'Unknown'),
)

class SavedPaymentMethod(models.Model):
    """Stores tokenized payment method references — no raw card numbers."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='saved_methods')
    
    # Method type
    method_type = models.CharField(max_length=20, choices=PAYMENT_METHOD_TYPE, default='card')
    
    # Card-specific fields (only for method_type='card')
    last_four = models.CharField(max_length=4, blank=True)
    card_brand = models.CharField(max_length=20, choices=CARD_BRAND, default='unknown', blank=True)
    expiry_month = models.IntegerField(null=True, blank=True)
    expiry_year = models.IntegerField(null=True, blank=True)
    billing_zip = models.CharField(max_length=20, blank=True)
    
    # M-Pesa specific
    phone_number = models.CharField(max_length=20, blank=True)
    
    # PayPal specific
    paypal_email = models.EmailField(blank=True)
    
    # Bank-specific
    bank_account_last_four = models.CharField(max_length=4, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    
    # Provider token (encrypted reference from Stripe/PayPal/etc.)
    provider_token = models.CharField(max_length=500, blank=True)
    provider = models.CharField(max_length=50, blank=True)  # e.g., 'stripe', 'paypal'
    
    # Display
    nickname = models.CharField(max_length=100, blank=True)  # e.g., "My Visa ending 4242"
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['payment_profile', 'is_default']),
            models.Index(fields=['method_type']),
        ]
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        if self.method_type == 'card':
            return f"{self.get_card_brand_display()} ending {self.last_four}"
        elif self.method_type == 'mpesa':
            return f"M-Pesa {self.phone_number}"
        elif self.method_type == 'paypal':
            return f"PayPal {self.paypal_email}"
        return f"{self.get_method_type_display()} - {self.nickname or self.id}"
    
    def save(self, *args, **kwargs):
        # Auto-generate nickname if empty
        if not self.nickname:
            self.nickname = str(self)
        # Ensure only one default per user
        if self.is_default:
            SavedPaymentMethod.objects.filter(
                payment_profile=self.payment_profile, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


# ============================================================================
# ML PRICING: Models for RL-based dynamic pricing
# ============================================================================

STUDENT_VERIFICATION_STATUS = (
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('expired', 'Expired'),
)

class StudentVerification(models.Model):
    """Student verification for student pricing package.
    Students verified via ID documents, admission letter, transcripts, or school email."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='student_verification')
    
    # Verification documents
    student_id_document = models.FileField(upload_to='student_verification/ids/', null=True, blank=True)
    admission_letter = models.FileField(upload_to='student_verification/admission/', null=True, blank=True)
    transcript = models.FileField(upload_to='student_verification/transcripts/', null=True, blank=True)
    school_email = models.EmailField(blank=True, help_text='Must be a valid .edu or .ac.xx email')
    
    # School info
    institution_name = models.CharField(max_length=500)
    student_number = models.CharField(max_length=100, blank=True)
    expected_graduation = models.DateField(null=True, blank=True)
    
    # Verification status
    status = models.CharField(max_length=20, choices=STUDENT_VERIFICATION_STATUS, default='pending')
    verified_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_students')
    verification_notes = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Discount
    discount_rate = models.DecimalField(decimal_places=2, max_digits=5, default=40.00)  # 40% default
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} - {self.institution_name} ({self.status})"
    
    @property
    def is_active(self):
        if self.status != 'approved':
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


class PricingEvent(models.Model):
    """Logs every pricing decision for RL training data collection."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Who and what
    user = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='pricing_events')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Pricing decision
    base_price = models.DecimalField(decimal_places=2, max_digits=12)
    offered_price = models.DecimalField(decimal_places=2, max_digits=12)
    discount_pct = models.DecimalField(decimal_places=4, max_digits=8, default=0)
    
    # State at time of decision (for replay buffer)
    tier = models.CharField(max_length=20, choices=TIER_OPT)
    is_student = models.BooleanField(default=False)
    group_size = models.IntegerField(default=1)
    demand_score = models.FloatField(default=0.0)
    sentiment_score = models.FloatField(default=0.5)
    notification_count = models.IntegerField(default=0)
    supply_score = models.FloatField(default=0.0)
    
    # Action taken by model
    price_action = models.FloatField(default=0.0)       # Price adjustment [-0.3, 0.3]
    notify_action = models.FloatField(default=0.0)       # Notification intensity [0, 1]
    promo_action = models.FloatField(default=0.0)        # Promo discount [0, 0.5]
    
    # Outcome
    accepted = models.BooleanField(default=False)
    revenue = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    user_savings = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    
    # Metadata
    model_version = models.CharField(max_length=50, default='v1')
    is_exploration = models.BooleanField(default=False)  # Was noise added?
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['tier']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Pricing {self.offered_price} for {self.user} ({self.tier})"


class UserPricingFeature(models.Model):
    """Per-user ML features updated periodically for the pricing model."""
    user = models.OneToOneField(PaymentProfile, on_delete=models.CASCADE, related_name='pricing_features')
    
    # Financial features
    cumulative_savings = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    purchase_frequency = models.FloatField(default=0.0)   # Purchases per month
    avg_transaction_value = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    total_spend = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    
    # Engagement features
    login_frequency = models.FloatField(default=0.0)      # Logins per week
    session_duration_avg = models.FloatField(default=0.0)  # Minutes
    pages_per_session = models.FloatField(default=0.0)
    
    # Platform features
    tier = models.CharField(max_length=20, choices=TIER_OPT, default='free')
    is_student = models.BooleanField(default=False)
    group_memberships_count = models.IntegerField(default=0)
    days_since_registration = models.IntegerField(default=0)
    
    # Pricing model state
    current_discount_rate = models.FloatField(default=0.0)
    price_sensitivity = models.FloatField(default=0.5)    # Estimated from behavior
    churn_risk = models.FloatField(default=0.0)           # Probability of leaving
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['tier']),
            models.Index(fields=['is_student']),
        ]
    
    def __str__(self):
        return f"Features for {self.user} (tier={self.tier}, student={self.is_student})"


# ============================================================================
# GROUP DISCOURSE: Public join requests & portfolio display
# ============================================================================

class GroupJoinRequest(models.Model):
    """Public request to join a payment group / piggy bank — includes portfolio details."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='join_requests')
    requester = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='group_join_requests')
    
    # Portfolio & motivation
    message = models.TextField(help_text='Why do you want to join? Include portfolio details.')
    portfolio_details = models.JSONField(default=dict, blank=True, help_text='Structured portfolio info')
    
    # Custom Application & Fees
    application_answers = models.JSONField(default=dict, blank=True, help_text='Answers to custom group questions')
    has_paid_entry_fee = models.BooleanField(default=False)
    
    STATUS_CHOICES = (
        ('pending_payment', 'Pending Payment'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        PaymentProfile, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_join_requests'
    )
    review_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['group', 'requester']
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['requester', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Join request to {self.group.name} by {self.requester}"


# ============================================================================
# GROUP VOTING: Approvals for investments, savings, withdrawals, etc.
# ============================================================================

class GroupVote(models.Model):
    """A vote/poll within a payment group room for actions requiring approval."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='votes')
    created_by = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='created_votes')
    
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    
    VOTE_TYPE_CHOICES = (
        ('investment', 'Investment Decision'),
        ('savings', 'Savings Decision'),
        ('withdrawal', 'Withdrawal Request'),
        ('purchase', 'Purchase Approval'),
        ('expansion', 'Expansion / Scaling'),
        ('remuneration', 'Remuneration / Payout'),
        ('other', 'Other'),
    )
    vote_type = models.CharField(max_length=20, choices=VOTE_TYPE_CHOICES, default='other')
    
    # Amount associated with the vote (optional)
    amount = models.DecimalField(decimal_places=2, max_digits=12, null=True, blank=True)
    
    # Voting results
    votes_for = models.ManyToManyField(PaymentProfile, blank=True, related_name='voted_for')
    votes_against = models.ManyToManyField(PaymentProfile, blank=True, related_name='voted_against')
    votes_abstain = models.ManyToManyField(PaymentProfile, blank=True, related_name='voted_abstain')
    
    STATUS_CHOICES = (
        ('open', 'Open for Voting'),
        ('passed', 'Passed'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Vote: {self.title} ({self.group.name})"
    
    @property
    def total_votes(self):
        return self.votes_for.count() + self.votes_against.count() + self.votes_abstain.count()
    
    @property
    def approval_percentage(self):
        total = self.votes_for.count() + self.votes_against.count()
        if total == 0:
            return 0
        return round((self.votes_for.count() / total) * 100, 1)


# ==================== BILL PAYMENTS ====================

BILL_CATEGORY = (
    ('electricity', 'Electricity'),
    ('water', 'Water'),
    ('tv', 'TV & Streaming'),
    ('airtime', 'Airtime & Data'),
    ('internet', 'Internet'),
    ('school_fees', 'School Fees'),
    ('rent', 'Rent'),
    ('government', 'Government Services'),
    ('other', 'Other'),
)

BILL_STATUS = (
    ('pending', 'Pending'),
    ('processing', 'Processing'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('reversed', 'Reversed'),
)

class BillProvider(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=BILL_CATEGORY)
    logo = models.ImageField(upload_to='bill_providers/', blank=True, null=True)
    account_label = models.CharField(max_length=100, default='Account Number')
    account_format = models.CharField(max_length=200, blank=True, help_text='Regex pattern for account validation')
    min_amount = models.DecimalField(decimal_places=2, max_digits=10, default=10.00)
    max_amount = models.DecimalField(decimal_places=2, max_digits=10, default=100000.00)
    commission_rate = models.DecimalField(decimal_places=4, max_digits=6, default=0.0150)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class BillPayment(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='bill_payments')
    provider = models.ForeignKey(BillProvider, on_delete=models.CASCADE, related_name='payments')
    account_number = models.CharField(max_length=200)
    account_name = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    commission = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    total_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    status = models.CharField(max_length=20, choices=BILL_STATUS, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=50, choices=PAY_OPT, default='comrade_balance')
    transaction = models.ForeignKey(TransactionToken, on_delete=models.SET_NULL, null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            import uuid
            self.reference = f"BILL-{uuid.uuid4().hex[:12].upper()}"
        self.commission = self.amount * self.provider.commission_rate
        self.total_amount = self.amount + self.commission
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.provider.name} - {self.account_number} - KES {self.amount}"


# ==================== MICRO-LOANS & CREDIT SCORING ====================

LOAN_STATUS = (
    ('draft', 'Draft'),
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('disbursed', 'Disbursed'),
    ('repaying', 'Repaying'),
    ('completed', 'Completed'),
    ('defaulted', 'Defaulted'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
)

REPAYMENT_STATUS = (
    ('upcoming', 'Upcoming'),
    ('due', 'Due'),
    ('paid', 'Paid'),
    ('overdue', 'Overdue'),
    ('waived', 'Waived'),
)

RISK_LEVEL = (
    ('very_low', 'Very Low'),
    ('low', 'Low'),
    ('moderate', 'Moderate'),
    ('high', 'High'),
    ('very_high', 'Very High'),
)

class LoanProduct(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    interest_rate = models.DecimalField(decimal_places=2, max_digits=6, help_text='Monthly interest rate %')
    min_amount = models.DecimalField(decimal_places=2, max_digits=12)
    max_amount = models.DecimalField(decimal_places=2, max_digits=12)
    min_tenure_months = models.IntegerField(default=1)
    max_tenure_months = models.IntegerField(default=24)
    requires_guarantor = models.BooleanField(default=False)
    guarantors_required = models.IntegerField(default=0)
    min_credit_score = models.IntegerField(default=0, help_text='Minimum credit score required')
    processing_fee = models.DecimalField(decimal_places=2, max_digits=6, default=0, help_text='Processing fee %')
    late_penalty_rate = models.DecimalField(decimal_places=2, max_digits=6, default=1.5, help_text='Late payment penalty % per month')
    is_group_loan = models.BooleanField(default=False)
    eligible_tiers = models.JSONField(default=list, blank=True, help_text='List of eligible membership tiers')
    icon = models.CharField(max_length=50, default='💰')
    color = models.CharField(max_length=50, default='from-blue-500 to-cyan-600')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['interest_rate']

    def __str__(self):
        return f"{self.name} ({self.interest_rate}% monthly)"


class CreditScore(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='credit_score')
    score = models.IntegerField(default=300, help_text='Score from 100-900')
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL, default='moderate')
    factors = models.JSONField(default=dict, blank=True, help_text='Breakdown of score factors')
    savings_score = models.IntegerField(default=0)
    repayment_score = models.IntegerField(default=0)
    group_score = models.IntegerField(default=0)
    transaction_score = models.IntegerField(default=0)
    tenure_score = models.IntegerField(default=0)
    computed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['score']),
        ]

    def __str__(self):
        return f"{self.user.user.email} - Score: {self.score}"


class LoanApplication(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='loan_applications')
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.CASCADE, related_name='applications')
    group = models.ForeignKey('PaymentGroups', on_delete=models.SET_NULL, null=True, blank=True, related_name='group_loans')
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    tenure_months = models.IntegerField()
    purpose = models.TextField(blank=True)
    monthly_payment = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    total_repayment = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    processing_fee_amount = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    credit_score_at_application = models.IntegerField(default=0)
    guarantors = models.ManyToManyField(Profile, blank=True, related_name='guaranteed_loans')
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='pending')
    rejection_reason = models.TextField(blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def save(self, *args, **kwargs):
        rate = self.loan_product.interest_rate / 100
        self.monthly_payment = (self.amount * (1 + rate * self.tenure_months)) / self.tenure_months
        self.total_repayment = self.monthly_payment * self.tenure_months
        self.processing_fee_amount = self.amount * (self.loan_product.processing_fee / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Loan {self.id} - {self.user.user.email} - KES {self.amount}"


class LoanRepayment(models.Model):
    loan = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='repayments')
    installment_number = models.IntegerField()
    amount_due = models.DecimalField(decimal_places=2, max_digits=12)
    amount_paid = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    penalty = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    due_date = models.DateField()
    paid_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=REPAYMENT_STATUS, default='upcoming')
    transaction = models.ForeignKey(TransactionToken, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['loan', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"Installment {self.installment_number} - Loan {self.loan.id}"


# ==================== ESCROW SERVICES ====================

ESCROW_STATUS = (
    ('initiated', 'Initiated'),
    ('funded', 'Funded'),
    ('in_progress', 'In Progress'),
    ('delivered', 'Delivered'),
    ('released', 'Released'),
    ('disputed', 'Disputed'),
    ('refunded', 'Refunded'),
    ('cancelled', 'Cancelled'),
)

ESCROW_TYPE = (
    ('marketplace', 'Marketplace Purchase'),
    ('gig', 'Gig / Freelance'),
    ('p2p', 'Peer-to-Peer'),
    ('group_investment', 'Group Investment'),
    ('custom', 'Custom'),
)

DISPUTE_STATUS = (
    ('open', 'Open'),
    ('under_review', 'Under Review'),
    ('resolved_buyer', 'Resolved — Buyer Wins'),
    ('resolved_seller', 'Resolved — Seller Wins'),
    ('settled', 'Settled — Split'),
    ('closed', 'Closed'),
)

class EscrowTransaction(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='escrow_as_buyer')
    seller = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='escrow_as_seller')
    escrow_type = models.CharField(max_length=30, choices=ESCROW_TYPE, default='marketplace')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=12)
    escrow_fee = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    total_amount = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    fee_rate = models.DecimalField(decimal_places=4, max_digits=6, default=0.0200)
    status = models.CharField(max_length=20, choices=ESCROW_STATUS, default='initiated')
    milestones = models.JSONField(default=list, blank=True, help_text='List of milestone objects')
    delivery_proof = models.TextField(blank=True)
    release_conditions = models.TextField(blank=True)
    funded_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def save(self, *args, **kwargs):
        self.escrow_fee = self.amount * self.fee_rate
        self.total_amount = self.amount + self.escrow_fee
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Escrow: {self.title} - KES {self.amount}"


class EscrowDispute(models.Model):
    escrow = models.ForeignKey(EscrowTransaction, on_delete=models.CASCADE, related_name='disputes')
    raised_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='raised_disputes')
    reason = models.TextField()
    evidence = models.JSONField(default=list, blank=True, help_text='List of evidence URLs/descriptions')
    status = models.CharField(max_length=30, choices=DISPUTE_STATUS, default='open')
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_disputes')
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispute on {self.escrow.title}"


# ==================== MICRO-INSURANCE ====================

INSURANCE_CATEGORY = (
    ('health', 'Health'),
    ('asset', 'Asset Protection'),
    ('crop', 'Crop Insurance'),
    ('device', 'Device / Phone'),
    ('travel', 'Travel'),
    ('funeral', 'Funeral Cover'),
    ('education', 'Education Plan'),
    ('business', 'Business Insurance'),
)

POLICY_STATUS = (
    ('pending', 'Pending'),
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('claimed', 'Claimed'),
    ('cancelled', 'Cancelled'),
    ('lapsed', 'Lapsed'),
)

CLAIM_STATUS = (
    ('submitted', 'Submitted'),
    ('under_review', 'Under Review'),
    ('approved', 'Approved'),
    ('paid', 'Paid'),
    ('rejected', 'Rejected'),
    ('withdrawn', 'Withdrawn'),
)

PREMIUM_FREQUENCY = (
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
    ('semi_annual', 'Semi-Annual'),
    ('annual', 'Annual'),
    ('one_time', 'One-Time'),
)

class InsuranceProduct(models.Model):
    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=200, help_text='Insurance company name')
    category = models.CharField(max_length=30, choices=INSURANCE_CATEGORY)
    description = models.TextField()
    premium_amount = models.DecimalField(decimal_places=2, max_digits=10, help_text='Premium per period')
    premium_frequency = models.CharField(max_length=20, choices=PREMIUM_FREQUENCY, default='monthly')
    coverage_amount = models.DecimalField(decimal_places=2, max_digits=12, help_text='Maximum coverage')
    deductible = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    waiting_period_days = models.IntegerField(default=0)
    terms = models.TextField(blank=True, help_text='Terms and conditions')
    benefits = models.JSONField(default=list, blank=True, help_text='List of coverage benefits')
    exclusions = models.JSONField(default=list, blank=True, help_text='List of exclusions')
    is_group_product = models.BooleanField(default=False)
    min_group_size = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, default='🛡️')
    color = models.CharField(max_length=50, default='from-teal-500 to-emerald-600')
    is_active = models.BooleanField(default=True)
    rating = models.DecimalField(decimal_places=1, max_digits=3, default=4.0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['category', 'premium_amount']

    def __str__(self):
        return f"{self.name} by {self.provider} ({self.get_category_display()})"


class InsurancePolicy(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='insurance_policies')
    product = models.ForeignKey(InsuranceProduct, on_delete=models.CASCADE, related_name='policies')
    group = models.ForeignKey('PaymentGroups', on_delete=models.SET_NULL, null=True, blank=True, related_name='insurance_policies')
    policy_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=POLICY_STATUS, default='pending')
    premium_paid = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    total_premiums_due = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    beneficiaries = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.policy_number:
            import uuid
            self.policy_number = f"POL-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Policy {self.policy_number} - {self.product.name}"


class InsuranceClaim(models.Model):
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='insurance_claims')
    amount_claimed = models.DecimalField(decimal_places=2, max_digits=12)
    amount_approved = models.DecimalField(decimal_places=2, max_digits=12, default=0)
    reason = models.TextField()
    evidence = models.JSONField(default=list, blank=True, help_text='List of supporting documents/photos')
    status = models.CharField(max_length=20, choices=CLAIM_STATUS, default='submitted')
    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Claim on {self.policy.policy_number} - KES {self.amount_claimed}"


# ============================================================================
# SERVICE PROVIDERS & BILLING AUTOMATION
# ============================================================================

DESTINATION_TYPE = (
    ('external_mpesa', 'M-Pesa (External)'),
    ('external_bank', 'Bank Transfer (External)'),
    ('internal_wallet', 'Qomrade Wallet (Internal)'),
)

STANDING_ORDER_FREQ = (
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('quarterly', 'Quarterly'),
)

STANDING_ORDER_STATUS = (
    ('active', 'Active'),
    ('paused', 'Paused'),
    ('cancelled', 'Cancelled'),
    ('completed', 'Completed'),
)

class UserServiceProvider(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='saved_providers')
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=BILL_CATEGORY, default='other')
    account_number = models.CharField(max_length=255)
    destination_account = models.CharField(max_length=255, blank=True, null=True, help_text='Paybill, Till Number, Bank Account, etc.')
    destination_type = models.CharField(max_length=50, choices=DESTINATION_TYPE, default='external_mpesa')
    details = models.TextField(blank=True, help_text='Optional notes or description')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'category']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.account_number})"


class BillStandingOrder(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='bill_standing_orders')
    provider = models.ForeignKey(UserServiceProvider, on_delete=models.CASCADE, related_name='standing_orders')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=STANDING_ORDER_FREQ, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STANDING_ORDER_STATUS, default='active')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['start_date']),
        ]
        
    def __str__(self):
        return f"Standing Order: {self.provider.name} - KES {self.amount}/{self.frequency}"

