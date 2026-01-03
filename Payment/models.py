from django.db import models
from Authentication.models import CustomUser
from datetime import datetime
import uuid

# Payment Options
PAY_OPT = (
    ('paypal', 'PayPal'),
    ('mpesa', 'M-Pesa'),
    ('mastercard', 'MasterCard'),
    ('visa', 'Visa'),
    ('stripe', 'Stripe'),
    ('bank_transfer', 'Bank Transfer'),
    ('comrade_balance', 'Comrade Balance'),
)

TRANSACTION_CATEGORY = (
    ('purchase', 'Purchase'),
    ('transfer', 'Transfer'),
    ('deposit', 'Deposit'),
    ('withdrawal', 'Withdrawal'),
    ('refund', 'Refund'),
    ('contribution', 'Contribution'),
    ('subscription', 'Subscription'),
)

TRANSACTION_STATUS = (
    ('pending', 'Pending'),
    ('authorized', 'Authorized'),
    ('verified', 'Verified'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
)

PAYMENT_METHOD = (
    ('INTERNAL', 'Internal (Comrade Balance)'),
    ('EXTERNAL', 'External Payment Gateway'),
)

GROUP_TYPE = (
    ('SAVINGS', 'Savings Group'),
    ('PURCHASE', 'Purchase Group'),
)

MEMBER_ROLE = (
    ('ADMIN', 'Administrator'),
    ('MEMBER', 'Member'),
)

FREQUENCY = (
    ('DAILY', 'Daily'),
    ('WEEKLY', 'Weekly'),
    ('MONTHLY', 'Monthly'),
    ('YEARLY', 'Yearly'),
)

INVITATION_STATUS = (
    ('PENDING', 'Pending'),
    ('ACCEPTED', 'Accepted'),
    ('DECLINED', 'Declined'),
    ('EXPIRED', 'Expired'),
)

SUBSCRIPTION_TYPE = (
    ('BASIC', 'Basic'),
    ('PREMIUM', 'Premium'),
    ('ENTERPRISE', 'Enterprise'),
)

SUBSCRIPTION_STATUS = (
    ('ACTIVE', 'Active'),
    ('CANCELLED', 'Cancelled'),
    ('EXPIRED', 'Expired'),
)


class PaymentProfile(models.Model):
    """User payment account with balance tracking"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='payment_profile')
    comrade_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_sent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_received = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_methods = models.JSONField(default=list, blank=True)
    default_payment_method = models.CharField(max_length=50, choices=PAY_OPT, default='comrade_balance')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['comrade_balance']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - Balance: ${self.comrade_balance}"


class TransactionToken(models.Model):
    """Core transaction model with tokenization"""
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_transactions')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_transactions', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, default='INTERNAL')
    external_payment_provider = models.CharField(max_length=100, blank=True)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_CATEGORY, default='transfer')
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='pending')
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    authorization_code = models.CharField(max_length=255, blank=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['sender']),
            models.Index(fields=['receiver']),
            models.Index(fields=['token']),
            models.Index(fields=['status']),
            models.Index(fields=['-created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"TXN-{self.token} - ${self.amount}"
    
    @property
    def token_display(self):
        return f"TXN-{self.token}"


class PaymentGroups(models.Model):
    """Group savings or collaborative purchasing"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='administered_groups')
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE, default='SAVINGS')
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    deadline = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['admin']),
            models.Index(fields=['group_type']),
            models.Index(fields=['is_active']),
        ]
        verbose_name_plural = 'Payment Groups'
    
    def __str__(self):
        return f"{self.name} ({self.group_type})"


class GroupMembers(models.Model):
    """Tracks members in payment groups"""
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='group_memberships')
    role = models.CharField(max_length=10, choices=MEMBER_ROLE, default='MEMBER')
    total_contributed = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['group', 'user']
        indexes = [
            models.Index(fields=['group']),
            models.Index(fields=['user']),
            models.Index(fields=['role']),
        ]
        verbose_name_plural = 'Group Members'
    
    def __str__(self):
        return f"{self.user.email} in {self.group.name}"


class Contribution(models.Model):
    """Individual contributions to payment groups"""
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='contributions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction = models.ForeignKey(TransactionToken, on_delete=models.SET_NULL, null=True, blank=True)
    contribution_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['group']),
            models.Index(fields=['member']),
            models.Index(fields=['-contribution_date']),
        ]
        ordering = ['-contribution_date']
    
    def __str__(self):
        return f"{self.member.email} contributed ${self.amount} to {self.group.name}"


class StandingOrder(models.Model):
    """Recurring payment automation"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='standing_orders')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_standing_orders', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, default='INTERNAL')
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    last_executed = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
            models.Index(fields=['next_execution']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.frequency} ${self.amount}"


class GroupInvitation(models.Model):
    """Invite system for payment groups"""
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_group_invitations')
    invitee_email = models.EmailField()
    status = models.CharField(max_length=20, choices=INVITATION_STATUS, default='PENDING')
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['group']),
            models.Index(fields=['invitee_email']),
            models.Index(fields=['status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Invitation to {self.invitee_email} for {self.group.name}"


class GroupTarget(models.Model):
    """Savings goals/milestones for groups (piggy bank feature)"""
    group = models.ForeignKey(PaymentGroups, on_delete=models.CASCADE, related_name='targets')
    name = models.CharField(max_length=255)
    description = models.TextField()
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    target_date = models.DateField(null=True, blank=True)
    is_achieved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['group']),
            models.Index(fields=['is_achieved']),
            models.Index(fields=['target_date']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.group.name}"
    
    @property
    def progress_percentage(self):
        if self.target_amount > 0:
            return round((self.current_amount / self.target_amount) * 100, 2)
        return 0.0


class PaymentItem(models.Model):
    """Items/purposes for transactions"""
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - ${self.price}"


class Product(models.Model):
    """Products available for purchase"""
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100)
    stock_quantity = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_available']),
        ]
    
    def __str__(self):
        return f"{self.name} - ${self.price}"


class UserSubscription(models.Model):
    """Subscription management for users"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='subscription')
    subscription_type = models.CharField(max_length=20, choices=SUBSCRIPTION_TYPE, default='BASIC')
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='ACTIVE')
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['subscription_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.subscription_type}"


# Legacy models (keeping for compatibility)
class PaymentLog(models.Model):
    """Legacy payment log model"""
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='logs')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=50)
    payment_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)


class PaymentAuthorization(models.Model):
    """Payment authorization records"""
    transaction = models.ForeignKey(TransactionToken, on_delete=models.CASCADE, related_name='authorizations')
    authorization_code = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PaymentVerification(models.Model):
    """Payment verification records"""
    transaction = models.ForeignKey(TransactionToken, on_delete=models.CASCADE, related_name='verifications')
    verification_code = models.CharField(max_length=255, unique=True)
    verified_at = models.DateTimeField(auto_now_add=True)


class TransactionHistory(models.Model):
    """Historical transaction records"""
    transaction = models.ForeignKey(TransactionToken, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)


class TransactionTracker(models.Model):
    """Track transaction status changes"""
    transaction = models.ForeignKey(TransactionToken, on_delete=models.CASCADE, related_name='tracker')
    status = models.CharField(max_length=20)
    updated_at = models.DateTimeField(auto_now=True)
