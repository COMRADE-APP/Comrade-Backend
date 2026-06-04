"""
Credit Scoring Service
Computes a 100-900 credit score based on 5 weighted factors.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Weights for each scoring factor (must sum to 1.0)
SCORE_WEIGHTS = {
    'savings': 0.25,
    'repayment': 0.30,
    'group': 0.15,
    'transaction': 0.15,
    'tenure': 0.15,
}

MIN_SCORE = 100
MAX_SCORE = 900
SCORE_RANGE = MAX_SCORE - MIN_SCORE


def compute_credit_score(user_profile):
    """
    Calculate a comprehensive credit score for a user.

    Factors:
    1. Savings Score (25%): Consistency and volume of savings
    2. Repayment Score (30%): Loan repayment history
    3. Group Score (15%): Active group membership, contribution regularity
    4. Transaction Score (15%): Platform transaction volume and frequency
    5. Tenure Score (15%): How long the user has been on the platform

    Args:
        user_profile: Authentication.Profile instance

    Returns:
        dict: {
            'total_score': int (100-900),
            'savings_score': int,
            'repayment_score': int,
            'group_score': int,
            'transaction_score': int,
            'tenure_score': int,
            'factors': dict of raw data used
        }
    """
    from Payment.models import PaymentProfile

    try:
        payment_profile = PaymentProfile.objects.get(user=user_profile)
    except PaymentProfile.DoesNotExist:
        return _minimum_score()

    factors = {}

    savings_score = _calculate_savings_score(payment_profile, user_profile, factors)
    repayment_score = _calculate_repayment_score(payment_profile, user_profile, factors)
    group_score = _calculate_group_score(payment_profile, factors)
    transaction_score = _calculate_transaction_score(payment_profile, factors)
    tenure_score = _calculate_tenure_score(user_profile, factors)

    total_score = int(
        savings_score * SCORE_WEIGHTS['savings'] +
        repayment_score * SCORE_WEIGHTS['repayment'] +
        group_score * SCORE_WEIGHTS['group'] +
        transaction_score * SCORE_WEIGHTS['transaction'] +
        tenure_score * SCORE_WEIGHTS['tenure']
    )

    total_score = max(MIN_SCORE, min(MAX_SCORE, total_score))

    return {
        'total_score': total_score,
        'savings_score': savings_score,
        'repayment_score': repayment_score,
        'group_score': group_score,
        'transaction_score': transaction_score,
        'tenure_score': tenure_score,
        'factors': factors,
    }


def _minimum_score():
    return {
        'total_score': MIN_SCORE,
        'savings_score': MIN_SCORE,
        'repayment_score': MIN_SCORE,
        'group_score': MIN_SCORE,
        'transaction_score': MIN_SCORE,
        'tenure_score': MIN_SCORE,
        'factors': {},
    }


def _normalize_score(raw_value, max_raw_value):
    """Convert a raw value (0 to max_raw) into the 100-900 score range."""
    if max_raw_value <= 0:
        return MIN_SCORE
    ratio = min(raw_value / max_raw_value, 1.0)
    return int(MIN_SCORE + (ratio * SCORE_RANGE))


def _calculate_savings_score(payment_profile, user_profile, factors):
    """
    Based on:
    - Current wallet balance
    - Total deposits in last 12 months
    - Months with at least one deposit
    """
    from Payment.models import TransactionToken

    wallet_balance = float(payment_profile.comrade_balance or 0)

    twelve_months_ago = timezone.now() - timedelta(days=365)
    deposits = TransactionToken.objects.filter(
        payment_profile=payment_profile,
        transaction_type__in=['deposit', 'savings_deposit', 'piggy_bank_contribution', 'contribution'],
        status='completed',
        created_at__gte=twelve_months_ago
    )
    total_deposits = float(deposits.aggregate(total=Sum('amount'))['total'] or 0)
    deposit_months = deposits.dates('created_at', 'month').count()

    factors['wallet_balance'] = wallet_balance
    factors['total_deposits_12m'] = total_deposits
    factors['active_deposit_months'] = deposit_months

    balance_component = _normalize_score(wallet_balance, 50000) * 0.3
    volume_component = _normalize_score(total_deposits, 200000) * 0.4
    consistency_component = _normalize_score(deposit_months, 12) * 0.3

    return int(balance_component + volume_component + consistency_component)


def _calculate_repayment_score(payment_profile, user_profile, factors):
    """
    Based on:
    - On-time repayment rate
    - Completed loan count
    - Current overdue amount
    """
    from Payment.models import LoanApplication, LoanRepayment
    loans = LoanApplication.objects.filter(
        user=user_profile,
        status__in=['disbursed', 'completed', 'defaulted']
    )
    total_loans = loans.count()

    if total_loans == 0:
        factors['total_loans'] = 0
        return 500

    completed_loans = loans.filter(status='completed').count()
    defaulted_loans = loans.filter(status='defaulted').count()

    repayments = LoanRepayment.objects.filter(
        loan__in=loans
    )
    total_repayments = repayments.count()
    on_time_repayments = repayments.filter(
        status='paid',
        paid_date__lte=F('due_date')
    ).count()

    on_time_rate = (on_time_repayments / total_repayments * 100) if total_repayments > 0 else 0
    completion_rate = (completed_loans / total_loans * 100) if total_loans > 0 else 0

    factors['total_loans'] = total_loans
    factors['completed_loans'] = completed_loans
    factors['defaulted_loans'] = defaulted_loans
    factors['on_time_rate'] = round(on_time_rate, 1)
    factors['completion_rate'] = round(completion_rate, 1)

    ontime_component = _normalize_score(on_time_rate, 100) * 0.5
    completion_component = _normalize_score(completion_rate, 100) * 0.3
    default_penalty = 0 if defaulted_loans == 0 else (defaulted_loans * 100)
    no_default_component = _normalize_score(max(0, 100 - default_penalty), 100) * 0.2

    return int(ontime_component + completion_component + no_default_component)


def _calculate_group_score(payment_profile, factors):
    """
    Based on:
    - Number of active group memberships
    - Contribution regularity in groups
    - Admin roles in groups
    """
    from Payment.models import PaymentGroupMember
    memberships = PaymentGroupMember.objects.filter(
        payment_profile=payment_profile,
        is_active=True
    )
    active_groups = memberships.count()
    leadership_roles = memberships.filter(is_admin=True).count()

    six_months_ago = timezone.now() - timedelta(days=180)
    from Payment.models import Contribution
    contributions = Contribution.objects.filter(
        member__payment_profile=payment_profile,
        contributed_at__gte=six_months_ago
    ).count()

    factors['active_groups'] = active_groups
    factors['leadership_roles'] = leadership_roles
    factors['contributions_6m'] = contributions

    groups_component = _normalize_score(active_groups, 5) * 0.4
    contributions_component = _normalize_score(contributions, 30) * 0.4
    leadership_component = _normalize_score(leadership_roles, 2) * 0.2

    return int(groups_component + contributions_component + leadership_component)


def _calculate_transaction_score(payment_profile, factors):
    """
    Based on:
    - Transaction count in last 12 months
    - Transaction value in last 12 months
    - Diversity of transaction types
    """
    from Payment.models import TransactionToken

    twelve_months_ago = timezone.now() - timedelta(days=365)
    transactions = TransactionToken.objects.filter(
        Q(payment_profile=payment_profile) | Q(recipient_profile=payment_profile),
        status='completed',
        created_at__gte=twelve_months_ago
    )
    txn_count = transactions.count()
    txn_value = float(transactions.aggregate(total=Sum('amount'))['total'] or 0)
    txn_types = transactions.values('transaction_type').distinct().count()

    factors['transactions_12m'] = txn_count
    factors['transaction_value_12m'] = txn_value
    factors['transaction_types'] = txn_types

    volume_component = _normalize_score(txn_count, 200) * 0.4
    value_component = _normalize_score(txn_value, 500000) * 0.4
    diversity_component = _normalize_score(txn_types, 6) * 0.2

    return int(volume_component + value_component + diversity_component)


def _calculate_tenure_score(user_profile, factors):
    """
    Based on how long the user has been on the platform.
    Max score at 2 years (730 days).
    """
    user = user_profile.user
    join_date = user.date_joined
    days_on_platform = (timezone.now() - join_date).days

    factors['days_on_platform'] = days_on_platform

    return _normalize_score(days_on_platform, 730)
