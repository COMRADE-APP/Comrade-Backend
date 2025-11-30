from django.db import models
from Authentication.models import Profile
from datetime import datetime

# Create your models here.
PAY_OPT = (
    ('paypal', 'PayPal'),
    ('mpesa', 'M-Pesa'),
    ('mastercard', 'MasterCard (Debit or Credit Card)'),
    ('visa', 'Visa'),
    ('venmo', 'Venmo'),
    ('gcash', 'G-Cash'),
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

# Payment Profile
class PaymentProfile(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    payment_option = models.CharField(max_length=2000, choices=PAY_OPT, default='paypal')
    payment_number = models.CharField(max_length=10000, default='')
    payment_token = models.CharField(max_length=10000, default='')

# Payment Item
class PaymentItem(models.Model):
    name = models.CharField(max_length=2000)
    cost = models.DecimalField(decimal_places=2, max_digits=100)
    quantity = models.FloatField()
    total_cost = models.DecimalField(decimal_places=4, max_digits=100)
    created_at = models.DateTimeField(default=datetime.now)


# Payment Log
class PaymentLog(models.Model):
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='purchase_profile')
    amount = models.DecimalField(decimal_places=2, max_digits=100)
    purchase_item = models.ManyToManyField(PaymentItem, blank=True)
    payment_type = models.CharField(max_length=2000, choices=PAY_TYPE, default='individual')
    payment_date = models.DateTimeField(default=datetime.now)
    recipient = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE, related_name='sale_profile')



# Payment Group
class PaymentGroups(models.Model):
    name = models.CharField(max_length=5000)
    payment_profiles = models.ManyToManyField(PaymentProfile, blank=True)
    max_capacity = models.IntegerField(default=3)
    tier = models.CharField(max_length=200, choices=TIER_OPT, default='standard')
    item_grouping = models.ManyToManyField(PaymentItem, blank=True)
    created_at = models.DateTimeField(default=datetime.now)

# Payment Slot
class PaymentSlot(models.Model):
    payment_group = models.OneToOneField(PaymentGroups, on_delete=models.CASCADE)
    payment_profile = models.ForeignKey(PaymentProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(decimal_places=4, max_digits=100)
    created_at = models.DateTimeField(default=datetime.now)


