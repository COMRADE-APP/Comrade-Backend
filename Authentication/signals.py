"""
Authentication Signals
Auto-creates PaymentProfile when a Profile is created
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


@receiver(post_save, sender='Authentication.Profile')
def create_payment_profile(sender, instance, created, **kwargs):
    """
    Automatically create a PaymentProfile when a new Profile is created.
    Initializes with free tier and zero balance.
    """
    if created:
        from Payment.models import PaymentProfile
        
        # Generate unique profile token
        profile_token = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        
        # Check if PaymentProfile already exists (shouldn't happen, but safe guard)
        if not PaymentProfile.objects.filter(user=instance).exists():
            PaymentProfile.objects.create(
                user=instance,
                tier='free',
                comrade_balance=0.00,
                profile_token=profile_token,
                payment_option='comrade_balance',
            )
