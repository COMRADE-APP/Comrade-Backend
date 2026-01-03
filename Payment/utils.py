from datetime import datetime
from django.utils import timezone
from Payment.models import PaymentProfile

# Tier Constants
TIER_LIMITS = {
    'free': {
        'max_group_members': 3,
        'monthly_purchases': 6,
        'max_groups': 3,
        'offline_notifications': 5,
    },
    'standard': {
        'max_group_members': 7,
        'monthly_purchases': 25,
        'max_groups': 10,
        'max_group_purchase_people': 25, # Special limit mentioned
    },
    'premium': {
        'max_group_members': 12,
        'monthly_purchases': 45,
        'max_groups': 20,
    },
    'gold': {
        'max_group_members': float('inf'),
        'monthly_purchases': float('inf'),
        'max_groups': float('inf'),
    }
}

def get_tier_limits(tier):
    return TIER_LIMITS.get(tier, TIER_LIMITS['free'])

def check_purchase_limit(payment_profile):
    """
    Check if user can make a purchase based on their tier.
    Resets counter if new month.
    """
    now = timezone.now()
    if payment_profile.last_purchase_month != now.month:
        payment_profile.monthly_purchases = 0
        payment_profile.last_purchase_month = now.month
        payment_profile.save()
        
    limits = get_tier_limits(payment_profile.tier)
    
    if payment_profile.monthly_purchases >= limits['monthly_purchases']:
        return False, f"Monthly purchase limit of {limits['monthly_purchases']} reached for {payment_profile.tier} tier."
    
    return True, None

def increment_purchase_count(payment_profile):
    payment_profile.monthly_purchases += 1
    payment_profile.save()

def check_group_creation_limit(payment_profile):
    """Check if user can create more groups"""
    limits = get_tier_limits(payment_profile.tier)
    current_count = payment_profile.created_groups.count()
    
    if current_count >= limits['max_groups']:
        return False, f"Maximum group limit of {limits['max_groups']} reached for {payment_profile.tier} tier."
        
    return True, None

def get_max_group_members(tier):
    return get_tier_limits(tier)['max_group_members']
