"""
Data pipeline for extracting RL training features from the Comrade database.

Extracts state-action-reward tuples from:
- TransactionToken: purchase amounts, frequency
- UserActivity: engagement signals
- PaymentProfile: tier, balance, monthly purchases
- PaymentGroups/Members: group dynamics
- Product/UserSubscription: product interest

Can run standalone (with Django setup) or be imported.
"""

import os
import sys
import numpy as np
from datetime import timedelta

# Django setup for standalone usage
def setup_django():
    """Initialize Django settings if not already configured."""
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
        import django
        django.setup()


def extract_user_features(user_profile):
    """
    Extract ML features from a single user's PaymentProfile.
    Returns a dict of features suitable for the pricing model state.
    """
    from django.utils import timezone
    from Payment.models import (
        TransactionToken, PaymentGroupMember, UserPricingFeature,
        StudentVerification
    )
    from ActivityLog.models import UserActivity

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Transaction features
    recent_transactions = TransactionToken.objects.filter(
        payment_profile=user_profile,
        created_at__gte=thirty_days_ago,
    )
    tx_count = recent_transactions.count()
    tx_amounts = [float(t.amount) for t in recent_transactions]
    avg_tx_value = np.mean(tx_amounts) if tx_amounts else 0.0
    total_spend = sum(tx_amounts)

    # Group features
    group_memberships = PaymentGroupMember.objects.filter(
        payment_profile=user_profile,
        payment_group__is_active=True,
    )
    group_count = group_memberships.count()
    avg_group_size = 0.0
    if group_count > 0:
        sizes = [m.payment_group.members.count() for m in group_memberships[:10]]
        avg_group_size = np.mean(sizes)

    # Engagement features (from ActivityLog)
    try:
        user_obj = user_profile.user.user  # Profile → User
        logins = UserActivity.objects.filter(
            user=user_obj,
            activity_type='login',
            timestamp__gte=seven_days_ago,
        ).count()
        page_views = UserActivity.objects.filter(
            user=user_obj,
            activity_type='page_view',
            timestamp__gte=seven_days_ago,
        ).count()
    except Exception:
        logins = 0
        page_views = 0

    # Student status
    is_student = False
    student_discount = 0.0
    try:
        sv = StudentVerification.objects.get(user=user_profile.user)
        is_student = sv.is_active
        student_discount = float(sv.discount_rate) / 100 if is_student else 0.0
    except StudentVerification.DoesNotExist:
        pass

    # Days since registration
    try:
        days_since_reg = (now - user_profile.user.user.date_joined).days
    except Exception:
        days_since_reg = 0

    features = {
        # Financial
        'purchase_frequency': tx_count,
        'avg_transaction_value': avg_tx_value,
        'total_spend': total_spend,
        'cumulative_savings': 0.0,  # Needs PricingEvent history
        # Engagement
        'login_frequency': logins,
        'pages_per_session': page_views / max(logins, 1),
        # Platform
        'tier': user_profile.tier,
        'is_student': is_student,
        'student_discount': student_discount,
        'group_memberships_count': group_count,
        'avg_group_size': avg_group_size,
        'days_since_registration': days_since_reg,
        'comrade_balance': float(user_profile.comrade_balance),
    }

    return features


def update_user_pricing_features(user_profile):
    """
    Update or create the UserPricingFeature record for a user.
    Should be called periodically (e.g., daily cron job).
    """
    from Payment.models import UserPricingFeature

    features = extract_user_features(user_profile)

    tier_map = {'free': 'free', 'standard': 'standard', 'premium': 'premium', 'gold': 'gold'}

    obj, created = UserPricingFeature.objects.update_or_create(
        user=user_profile,
        defaults={
            'purchase_frequency': features['purchase_frequency'],
            'avg_transaction_value': features['avg_transaction_value'],
            'total_spend': features['total_spend'],
            'cumulative_savings': features['cumulative_savings'],
            'login_frequency': features['login_frequency'],
            'pages_per_session': features['pages_per_session'],
            'tier': tier_map.get(features['tier'], 'free'),
            'is_student': features['is_student'],
            'group_memberships_count': features['group_memberships_count'],
            'days_since_registration': features['days_since_registration'],
        },
    )
    return obj


def build_state_vector(features):
    """
    Convert user features dict into the 8-dimensional state vector
    expected by the RL agent.
    
    State: [group_size, price, demand, supply, notifications, sentiment, tier_idx, is_student]
    """
    tier_to_idx = {'free': 0, 'standard': 1, 'premium': 2, 'gold': 3}
    
    # Map features to state dimensions
    state = np.array([
        features.get('avg_group_size', 1.0),                    # G: group size
        100.0,                                                   # P: current price (default retail)
        features.get('purchase_frequency', 5.0),                 # D: demand proxy
        1.0,                                                     # S: supply (default)
        5.0,                                                     # N: notifications (default)
        0.5,                                                     # M: sentiment (neutral)
        float(tier_to_idx.get(features.get('tier', 'free'), 0)), # tier index
        float(features.get('is_student', False)),                 # student flag
    ], dtype=np.float32)
    
    return state


def generate_synthetic_training_data(n_samples=10000):
    """
    Generate synthetic state-action-reward tuples for bootstrapping
    model training when real data is scarce.
    Uses the Kenya market calibration from Qomrade.docx.
    """
    from ML.training.pricing_env import ComradePricingEnv
    
    env = ComradePricingEnv()
    data = []
    
    for _ in range(n_samples // 90):  # Each episode is ~90 steps
        state, _ = env.reset()
        done = False
        while not done:
            # Random exploration actions
            action = env.action_space.sample()
            next_state, reward, terminated, truncated, info = env.step(action)
            
            data.append({
                'state': state.tolist(),
                'action': action.tolist(),
                'reward': reward,
                'next_state': next_state.tolist(),
                'done': terminated or truncated,
                'info': {k: float(v) if isinstance(v, (int, float, np.floating)) else v 
                         for k, v in info.items()},
            })
            
            state = next_state
            done = terminated or truncated
    
    return data


def extract_pricing_events_for_training():
    """
    Extract historical PricingEvent records as training data.
    Returns list of (state, action, reward, next_state, done) tuples.
    """
    from Payment.models import PricingEvent

    events = PricingEvent.objects.all().order_by('user', 'created_at')
    
    tier_to_idx = {'free': 0, 'standard': 1, 'premium': 2, 'gold': 3}
    
    data = []
    prev_event = None
    
    for event in events:
        state = np.array([
            event.group_size,
            float(event.base_price),
            event.demand_score,
            event.supply_score,
            event.notification_count,
            event.sentiment_score,
            float(tier_to_idx.get(event.tier, 0)),
            float(event.is_student),
        ], dtype=np.float32)
        
        action = np.array([
            event.price_action,
            event.notify_action,
            event.promo_action,
        ], dtype=np.float32)
        
        # Compute reward
        savings_pct = float(event.user_savings) / float(event.base_price) if float(event.base_price) > 0 else 0
        revenue_margin = (float(event.revenue) - 60 * event.group_size) / max(60 * event.group_size, 1)
        reward = 0.5 * savings_pct + 0.5 * max(0, revenue_margin)
        if event.accepted:
            reward += 0.2
        
        if prev_event is not None and prev_event.user_id == event.user_id:
            data.append((
                prev_state, prev_action, prev_reward,
                state, False,
            ))
        
        prev_event = event
        prev_state = state
        prev_action = action
        prev_reward = reward
    
    return data


if __name__ == '__main__':
    print("Generating synthetic training data...")
    data = generate_synthetic_training_data(n_samples=5000)
    print(f"Generated {len(data)} samples")
    print(f"Sample state: {data[0]['state']}")
    print(f"Sample action: {data[0]['action']}")
    print(f"Sample reward: {data[0]['reward']:.4f}")
