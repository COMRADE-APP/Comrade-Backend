"""
Penalty Engine Service
Centralized penalty calculation for withdrawals, loans, and contributions.
All monetary calculations use Decimal to prevent floating-point errors.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal('0.01')


def calculate_withdrawal_penalty(withdrawal_request):
    """
    Calculate penalty for a group withdrawal based on group settings.

    Rules:
    - Immature exit: 2% of member's total contributions (default)
    - Emergency withdrawal: may have reduced penalty based on group policy
    - Excess contribution: no penalty (withdrawing surplus only)
    - Maturity: no penalty (group has matured)

    Returns:
        Decimal: The penalty amount to deduct from the withdrawal
    """
    group = withdrawal_request.payment_group
    withdrawal_type = withdrawal_request.withdrawal_type

    # No penalty for these types
    if withdrawal_type in ('excess_contribution', 'maturity'):
        return Decimal('0.00')

    # Get the member's total contribution to the group
    member = withdrawal_request.requester
    member_contributions = member.contribution_balance or Decimal('0.00')

    if withdrawal_type == 'exit':
        # Full exit — apply immature exit penalty rate from group settings
        penalty_rate = getattr(group, 'immature_exit_penalty_rate', Decimal('2.00'))
        penalty = (member_contributions * penalty_rate / Decimal('100')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        logger.info(
            f"Exit penalty for member {member.id}: "
            f"{penalty_rate}% of {member_contributions} = {penalty}"
        )
        return penalty

    if withdrawal_type == 'emergency':
        # Emergency — half the normal penalty rate
        penalty_rate = getattr(group, 'immature_exit_penalty_rate', Decimal('2.00')) / Decimal('2')
        penalty = (withdrawal_request.amount * penalty_rate / Decimal('100')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        return penalty

    if withdrawal_type == 'partial':
        # Partial withdrawal — only if amount exceeds excess contribution
        # Calculate the member's expected average contribution
        member_count = group.members.filter(is_active=True).count()
        if member_count == 0:
            return Decimal('0.00')

        expected_avg = (group.wallet_balance / Decimal(str(member_count))).quantize(TWO_PLACES)
        excess = member_contributions - expected_avg

        if withdrawal_request.amount <= excess:
            # Withdrawing within excess — no penalty
            return Decimal('0.00')
        else:
            # Withdrawing more than excess — penalty on the amount above excess
            penalized_amount = withdrawal_request.amount - max(excess, Decimal('0.00'))
            penalty_rate = getattr(group, 'immature_exit_penalty_rate', Decimal('2.00'))
            penalty = (penalized_amount * penalty_rate / Decimal('100')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            return penalty

    return Decimal('0.00')


def calculate_loan_penalty(loan_repayment):
    """
    Calculate late penalty for an overdue loan repayment.

    Uses the late_penalty_rate from the LoanProduct.
    Penalty is applied per day overdue, calculated as:
        (amount_due * late_penalty_rate / 100) * days_overdue

    Returns:
        Decimal: The penalty amount to add to the repayment
    """
    if loan_repayment.status == 'paid':
        return Decimal('0.00')

    loan = loan_repayment.loan_application
    product = loan.product

    late_penalty_rate = getattr(product, 'late_penalty_rate', Decimal('0.00'))
    if late_penalty_rate <= 0:
        return Decimal('0.00')

    due_date = loan_repayment.due_date
    if not due_date:
        return Decimal('0.00')

    now = timezone.now().date() if hasattr(due_date, 'year') else timezone.now()
    if hasattr(due_date, 'date'):
        due_date = due_date.date()
    if hasattr(now, 'date'):
        now = now.date()

    if now <= due_date:
        return Decimal('0.00')

    days_overdue = (now - due_date).days
    amount_due = loan_repayment.amount_due - loan_repayment.amount_paid

    if amount_due <= 0:
        return Decimal('0.00')

    # Daily penalty rate = annual rate / 365
    daily_rate = late_penalty_rate / Decimal('365')
    penalty = (amount_due * daily_rate / Decimal('100') * Decimal(str(days_overdue))).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )

    logger.info(
        f"Loan penalty for repayment {loan_repayment.id}: "
        f"{days_overdue} days overdue, rate={late_penalty_rate}%, penalty={penalty}"
    )
    return penalty


def calculate_contribution_penalty(round_contribution, member):
    """
    Calculate penalty for a late or missed round contribution.

    Currently returns a fixed percentage of the contribution amount
    for each day late. The group can configure this behavior.

    Returns:
        Decimal: The penalty amount
    """
    if round_contribution.status != 'active':
        return Decimal('0.00')

    if not round_contribution.next_contribution_date:
        return Decimal('0.00')

    now = timezone.now()
    if now <= round_contribution.next_contribution_date:
        return Decimal('0.00')

    # Check if member has already contributed to current cycle
    from Payment.models import RoundMemberContribution
    has_contributed = RoundMemberContribution.objects.filter(
        round=round_contribution,
        member=member,
        cycle_number=round_contribution.current_cycle
    ).exists()

    if has_contributed:
        return Decimal('0.00')

    # Calculate days late
    days_late = (now - round_contribution.next_contribution_date).days
    contribution_amount = round_contribution.contribution_amount

    # Default: 1% per day late, capped at 10%
    daily_penalty_rate = Decimal('1.00')
    max_penalty_pct = Decimal('10.00')

    penalty_pct = min(daily_penalty_rate * Decimal(str(days_late)), max_penalty_pct)
    penalty = (contribution_amount * penalty_pct / Decimal('100')).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    return penalty
