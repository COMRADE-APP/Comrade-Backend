"""
Django service layer for the RL Pricing Engine.

Integrates the ML pricing model with Django views and models:
- calculate_dynamic_price(): Get RL-optimized price for a user/product
- log_pricing_event(): Record pricing decisions for training
- update_user_features(): Update per-user ML features
"""

import numpy as np
from decimal import Decimal
from django.utils import timezone

from Payment.models import (
    PaymentProfile, Product, PricingEvent, UserPricingFeature,
    StudentVerification, TIER_OPT,
)


def _get_pricing_engine():
    """Lazy-load the pricing engine to avoid import overhead at module level."""
    from ML.inference.pricing_engine import get_pricing_engine
    return get_pricing_engine()


def calculate_dynamic_price(user_profile, product, override_student=None):
    """
    Calculate a dynamic price for a user+product combination.
    
    Args:
        user_profile: PaymentProfile instance
        product: Product instance
        override_student: Force student pricing (True/False), or None for auto-detect
    
    Returns:
        dict with pricing details
    """
    engine = _get_pricing_engine()
    base_price = float(product.price)
    
    # Build state vector from user features
    state = _build_user_state(user_profile, base_price, override_student)
    
    # Get RL pricing decision
    decision = engine.get_price(state, base_price=base_price)
    
    return {
        'base_price': base_price,
        'offered_price': decision.offered_price,
        'discount_pct': decision.discount_pct,
        'tier': decision.tier,
        'is_student': decision.is_student,
        'model_version': decision.model_version,
        'is_fallback': decision.is_fallback,
        'actions': {
            'price_action': decision.price_action,
            'notify_action': decision.notify_action,
            'promo_action': decision.promo_action,
        },
    }


def get_tier_recommendation(user_profile):
    """Get tier upgrade recommendation for a user."""
    engine = _get_pricing_engine()
    
    # Get cumulative savings from PricingEvent history
    from django.db.models import Sum
    savings = PricingEvent.objects.filter(
        user=user_profile, accepted=True
    ).aggregate(total=Sum('user_savings'))['total'] or 0
    
    rec = engine.get_tier_recommendation(
        cumulative_savings=float(savings),
        current_tier=user_profile.tier,
    )
    
    return {
        'current_tier': rec.current_tier,
        'recommended_tier': rec.recommended_tier,
        'cumulative_savings': rec.cumulative_savings,
        'savings_threshold': rec.savings_threshold,
        'progress_pct': rec.progress_pct,
        'estimated_monthly_savings': rec.estimated_monthly_savings,
        'should_upgrade': rec.recommended_tier != rec.current_tier,
    }


def log_pricing_event(user_profile, product, offered_price, accepted,
                       price_action=0, notify_action=0, promo_action=0,
                       model_version='v1', is_exploration=False):
    """
    Log a pricing decision to PricingEvent for training data collection.
    
    Call this whenever a price is shown to a user and when they accept/reject.
    """
    base_price = float(product.price)
    
    # Detect student status
    is_student = False
    try:
        sv = StudentVerification.objects.get(user=user_profile.user)
        is_student = sv.is_active
    except StudentVerification.DoesNotExist:
        pass
    
    # Get contextual features
    from Payment.models import PaymentGroupMember
    group_count = PaymentGroupMember.objects.filter(
        payment_profile=user_profile,
        payment_group__is_active=True,
    ).count()
    
    event = PricingEvent.objects.create(
        user=user_profile,
        product=product,
        base_price=Decimal(str(base_price)),
        offered_price=Decimal(str(offered_price)),
        discount_pct=Decimal(str((base_price - offered_price) / base_price * 100)) if base_price > 0 else 0,
        tier=user_profile.tier,
        is_student=is_student,
        group_size=max(1, group_count),
        demand_score=0.0,  # Could compute from recent activity
        sentiment_score=0.5,
        notification_count=0,
        supply_score=0.0,
        price_action=price_action,
        notify_action=notify_action,
        promo_action=promo_action,
        accepted=accepted,
        revenue=Decimal(str(offered_price)) if accepted else Decimal('0'),
        user_savings=Decimal(str(max(0, base_price - offered_price))) if accepted else Decimal('0'),
        model_version=model_version,
        is_exploration=is_exploration,
    )
    
    return event


def update_user_features(user_profile):
    """
    Update the UserPricingFeature record for a user.
    Should be called after transactions, periodically, or on login.
    """
    from ML.training.data_pipeline import update_user_pricing_features
    return update_user_pricing_features(user_profile)


def _build_user_state(user_profile, base_price, override_student=None):
    """Build the 8-dimensional state vector from user data."""
    from Payment.models import PaymentGroupMember
    
    tier_to_idx = {'free': 0, 'standard': 1, 'premium': 2, 'gold': 3}
    
    # Group size
    memberships = PaymentGroupMember.objects.filter(
        payment_profile=user_profile,
        payment_group__is_active=True,
    )
    if memberships.exists():
        sizes = [m.payment_group.members.count() for m in memberships[:5]]
        avg_group = np.mean(sizes)
    else:
        avg_group = 1.0
    
    # Student status
    if override_student is not None:
        is_student = override_student
    else:
        try:
            sv = StudentVerification.objects.get(user=user_profile.user)
            is_student = sv.is_active
        except StudentVerification.DoesNotExist:
            is_student = False
    
    # Demand proxy: recent purchase count
    from Payment.models import TransactionToken
    from datetime import timedelta
    recent_tx = TransactionToken.objects.filter(
        payment_profile=user_profile,
        created_at__gte=timezone.now() - timedelta(days=30),
    ).count()
    
    state = np.array([
        float(avg_group),                                  # G
        float(base_price),                                 # P
        float(min(recent_tx, 50)),                         # D (demand proxy)
        1.0,                                               # S (supply, default)
        float(TIER_CONFIG_MAP.get(user_profile.tier, 5)),  # N (notifications)
        0.5,                                               # M (sentiment, neutral)
        float(tier_to_idx.get(user_profile.tier, 0)),      # tier_idx
        float(is_student),                                 # is_student
    ], dtype=np.float32)
    
    return state


# Tier notification limits
TIER_CONFIG_MAP = {
    'free': 5,
    'standard': 25,
    'premium': 100,
    'gold': 500,
}
