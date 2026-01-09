"""
Payment Tier Utilities
Handles tier-based limits for purchases, groups, and subscriptions
"""
from django.utils import timezone


# Tier Configuration - Complete definitions matching user specifications
TIER_LIMITS = {
    'free': {
        'max_group_members': 3,           # Maximum people per group
        'max_groups_created': 3,          # Can create up to 3 groups
        'monthly_purchases': 6,           # 6 purchases per month
        'max_group_purchase_members': 3,  # Group purchase limit
        'offline_notifications': 5,       # Limited to 5 offline notification subscriptions on onboarding
    },
    'standard': {
        'max_group_members': 7,
        'max_groups_created': 5,
        'monthly_purchases': 25,
        'max_group_purchase_members': 25,
        'offline_notifications': 25,
    },
    'premium': {
        'max_group_members': 12,
        'max_groups_created': 15,
        'monthly_purchases': 45,
        'max_group_purchase_members': 45,
        'offline_notifications': 100,
    },
    'gold': {
        'max_group_members': float('inf'),  # Unlimited
        'max_groups_created': float('inf'),
        'monthly_purchases': float('inf'),
        'max_group_purchase_members': float('inf'),
        'offline_notifications': float('inf'),
    }
}


def get_tier_limits(tier):
    """Get limits for a specific tier"""
    return TIER_LIMITS.get(tier, TIER_LIMITS['free'])


def get_max_group_members(tier):
    """Get maximum number of group members allowed for tier"""
    limits = get_tier_limits(tier)
    max_val = limits['max_group_members']
    return 99999 if max_val == float('inf') else int(max_val)


def get_max_groups_created(tier):
    """Get maximum number of groups a user can create"""
    limits = get_tier_limits(tier)
    max_val = limits['max_groups_created']
    return 99999 if max_val == float('inf') else int(max_val)


def get_monthly_purchase_limit(tier):
    """Get monthly purchase limit for tier"""
    limits = get_tier_limits(tier)
    max_val = limits['monthly_purchases']
    return 99999 if max_val == float('inf') else int(max_val)


def get_offline_notification_limit(tier):
    """Get offline notification subscription limit"""
    limits = get_tier_limits(tier)
    max_val = limits['offline_notifications']
    return 99999 if max_val == float('inf') else int(max_val)


def check_purchase_limit(payment_profile):
    """
    Check if user can make a purchase based on tier limits
    Returns: (can_purchase: bool, error_message: str or None)
    """
    tier = payment_profile.tier
    current_month = timezone.now().month
    
    # Reset monthly counter if new month
    if payment_profile.last_purchase_month != current_month:
        payment_profile.monthly_purchases = 0
        payment_profile.last_purchase_month = current_month
        payment_profile.save()
    
    limit = get_monthly_purchase_limit(tier)
    
    if payment_profile.monthly_purchases >= limit:
        return False, f"Monthly purchase limit ({limit}) reached for {tier} tier. Upgrade to make more purchases."
    
    return True, None


def increment_purchase_count(payment_profile):
    """Increment monthly purchase count"""
    current_month = timezone.now().month
    
    if payment_profile.last_purchase_month != current_month:
        payment_profile.monthly_purchases = 1
        payment_profile.last_purchase_month = current_month
    else:
        payment_profile.monthly_purchases += 1
    
    payment_profile.save()


def check_group_creation_limit(payment_profile):
    """
    Check if user can create more groups
    Returns: (can_create: bool, error_message: str or None)
    """
    tier = payment_profile.tier
    limit = get_max_groups_created(tier)
    
    groups_created = payment_profile.created_groups.count()
    
    if groups_created >= limit:
        return False, f"Group creation limit ({limit}) reached for {tier} tier. Upgrade to create more groups."
    
    return True, None


def check_group_member_limit(payment_group):
    """
    Check if group can add more members
    Returns: (can_add: bool, error_message: str or None)
    """
    tier = payment_group.tier
    limit = get_max_group_members(tier)
    current_members = payment_group.members.count()
    
    if current_members >= limit:
        return False, f"Member limit ({limit}) reached for this group's {tier} tier."
    
    return True, None


def can_subscribe_offline_notifications(payment_profile, current_subscriptions=None):
    """
    Check if user can add more offline notification subscriptions
    """
    tier = payment_profile.tier
    limit = get_offline_notification_limit(tier)
    
    if current_subscriptions is None:
        try:
            from Announcements.enhanced_models import AnnouncementSubscription
            current_subscriptions = AnnouncementSubscription.objects.filter(
                user=payment_profile.user.user,
                offline_notification_enabled=True
            ).count()
        except:
            current_subscriptions = 0
    
    if current_subscriptions >= limit:
        return False, f"Offline notification limit ({limit}) reached for {tier} tier."
    
    return True, None


def get_tier_pricing():
    """Return pricing information for each tier"""
    return {
        'free': {
            'price': 0,
            'price_annual': 0,
            'currency': 'USD',
            'features': [
                'Up to 3 members per group',
                '6 purchases per month',
                '5 offline notification subscriptions',
                'Basic support'
            ]
        },
        'standard': {
            'price': 9.99,
            'price_annual': 99.99,  # 2 months free
            'currency': 'USD',
            'features': [
                'Up to 7 members per group',
                '25 purchases per month',
                '25 offline notification subscriptions',
                'Priority support',
                'Group purchases up to 25 people'
            ]
        },
        'premium': {
            'price': 19.99,
            'price_annual': 199.99,  # 2 months free
            'currency': 'USD',
            'features': [
                'Up to 12 members per group',
                '45 purchases per month',
                '100 offline notification subscriptions',
                'Premium support',
                'Group purchases up to 45 people',
                'Advanced analytics'
            ]
        },
        'gold': {
            'price': 49.99,
            'price_annual': 499.99,  # 2 months free
            'currency': 'USD',
            'features': [
                'Unlimited group members',
                'Unlimited purchases',
                'Unlimited offline notifications',
                'Dedicated support',
                'Custom features',
                'API access',
                'White-label options'
            ]
        }
    }


def upgrade_tier(payment_profile, new_tier, transaction_id=None):
    """
    Upgrade user's tier
    """
    old_tier = payment_profile.tier
    payment_profile.tier = new_tier
    payment_profile.save()
    
    # Update all groups created by this user
    from Payment.models import PaymentGroups
    PaymentGroups.objects.filter(creator=payment_profile).update(tier=new_tier)
    
    # Log the upgrade
    try:
        from ActivityLog.models import ActionLog
        if hasattr(payment_profile.user, 'user'):
            ActionLog.objects.create(
                user=payment_profile.user.user,
                action='tier_upgrade',
                details={'old_tier': old_tier, 'new_tier': new_tier, 'transaction_id': transaction_id}
            )
    except:
        pass  # ActivityLog may not be available
    
    return True


def can_access_premium_content(user, content_type):
    """
    Check if user can access premium content based on their tier
    """
    try:
        from Authentication.models import Profile
        from Payment.models import PaymentProfile
        
        profile = Profile.objects.get(user=user)
        payment_profile = PaymentProfile.objects.get(user=profile)
        
        premium_content = ['research', 'specialization', 'premium_rooms', 'premium_events']
        
        if content_type in premium_content:
            if payment_profile.tier in ['premium', 'gold']:
                return True
            return False
        
        return True  # Non-premium content is accessible to all
    except:
        return False


def check_piggy_bank_lock(target, action='withdraw'):
    """
    Check if piggy bank (GroupTarget) allows the requested action based on locking status
    """
    if target.locking_status == 'unlocked':
        return True, None
        
    if target.locking_status == 'locked_time':
        if target.maturity_date and target.maturity_date > timezone.now():
            if action == 'withdraw':
                return False, f'Savings locked until {target.maturity_date.strftime("%Y-%m-%d")}'
        return True, None
        
    if target.locking_status == 'locked_goal':
        if target.current_amount < target.target_amount:
            if action == 'withdraw':
                return False, f'Savings locked until target amount of {target.target_amount} is reached'
        return True, None
    
    return True, None


def process_bid_notification(target):
    """
    Process notification when bid target amount is reached
    """
    if target.is_bid and target.current_amount >= target.target_amount:
        target.bid_status = 'accumulated'
        target.save()
        
        # TODO: Send notification to user for bid confirmation
        # This would integrate with the notification system
        
        return True
    return False


def calculate_individual_share(target, member, quantity=1):
    """
    Calculate individual share for non-sharable products in a group target
    """
    from Payment.models import IndividualShare
    
    share, created = IndividualShare.objects.get_or_create(
        target=target,
        member=member,
        defaults={
            'target_amount': target.target_amount / target.payment_group.members.count(),
            'quantity': quantity
        }
    )
    
    return share
