"""
Celery tasks for the Payment module.
All periodic tasks that handle financial automation, penalties, reminders, and scoring.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.models import Q, F, Sum
from decimal import Decimal
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# ROUND CONTRIBUTION REMINDERS (existing task — preserved)
# ============================================================================

@shared_task
def send_round_contribution_reminders():
    """
    Check for active rounds that have upcoming contribution deadlines
    and send reminders to members who haven't contributed to the current cycle.
    """
    from Payment.models import RoundContribution, RoundMemberContribution
    from Notifications.models import create_notification

    logger.info("Running send_round_contribution_reminders task")
    now = timezone.now()

    active_rounds = RoundContribution.objects.filter(
        status='active',
        next_contribution_date__isnull=False
    )

    reminders_sent = 0
    for round_obj in active_rounds:
        time_until_due = round_obj.next_contribution_date - now

        if time_until_due <= timedelta(hours=48):
            group_members = round_obj.payment_group.members.filter(is_active=True)

            contributed_member_ids = RoundMemberContribution.objects.filter(
                round=round_obj,
                cycle_number=round_obj.current_cycle
            ).values_list('member_id', flat=True)

            pending_members = group_members.exclude(id__in=contributed_member_ids)

            for pm in pending_members:
                if not pm.payment_profile or not pm.payment_profile.user:
                    continue
                message = (
                    f"Reminder: Contribute {round_obj.currency} {round_obj.contribution_amount} "
                    f"to round '{round_obj.round_name or round_obj.round_number}' "
                    f"by {round_obj.next_contribution_date.strftime('%Y-%m-%d')}."
                )
                if time_until_due < timedelta(0):
                    message = (
                        f"URGENT: Your contribution of {round_obj.currency} {round_obj.contribution_amount} "
                        f"to round '{round_obj.round_name or round_obj.round_number}' is OVERDUE."
                    )

                try:
                    create_notification(
                        recipient=pm.payment_profile.user.user,
                        notification_type='group_contribution',
                        message=message,
                        action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds",
                        extra_data={'group_id': str(round_obj.payment_group.id), 'round_id': str(round_obj.id)}
                    )
                    reminders_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send reminder to member {pm.id}: {e}")

    logger.info(f"Contribution reminders sent: {reminders_sent}")
    return f"Reminders sent: {reminders_sent}"


# ============================================================================
# STANDING ORDER PROCESSING
# ============================================================================

@shared_task
def process_standing_orders():
    """
    Process active bill standing orders that are due today.
    Creates BillPayment records and deducts from user wallets.
    Runs daily at 06:00.
    """
    from Payment.models import BillStandingOrder, BillPayment, TransactionToken, PaymentProfile

    logger.info("Running process_standing_orders task")
    now = timezone.now().date()
    processed = 0
    failed = 0

    active_orders = BillStandingOrder.objects.filter(
        status='active',
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    )

    for order in active_orders:
        # Determine if this order is due based on frequency
        if not _is_order_due(order, now):
            continue

        try:
            with db_transaction.atomic():
                user_profile = order.user
                payment_profile = user_profile.payment_profile.first()
                if not payment_profile:
                    logger.warning(f"No payment profile for user {user_profile.id}")
                    failed += 1
                    continue

                # Check sufficient balance
                if payment_profile.wallet_balance < order.amount:
                    logger.warning(
                        f"Insufficient balance for standing order {order.id}: "
                        f"balance={payment_profile.wallet_balance}, required={order.amount}"
                    )
                    # Notify user of insufficient funds
                    _notify_insufficient_funds(user_profile, order)
                    failed += 1
                    continue

                # Deduct from wallet
                payment_profile.wallet_balance -= order.amount
                payment_profile.save()

                # Create transaction record
                txn = TransactionToken.objects.create(
                    sender_profile=payment_profile,
                    amount=order.amount,
                    transaction_type='bill_payment',
                    status='completed',
                    description=f"Standing order: {order.provider.name}",
                )

                # Create bill payment record
                BillPayment.objects.create(
                    user=user_profile,
                    provider=order.provider.category if hasattr(order.provider, 'category') else 'other',
                    account_number=order.provider.account_number,
                    amount=order.amount,
                    status='completed',
                    transaction=txn,
                )

                processed += 1
                logger.info(f"Processed standing order {order.id} for {order.amount}")

        except Exception as e:
            logger.error(f"Failed to process standing order {order.id}: {e}")
            failed += 1

    logger.info(f"Standing orders processed: {processed}, failed: {failed}")
    return f"Processed: {processed}, Failed: {failed}"


def _is_order_due(order, today):
    """Check if a standing order is due based on its frequency."""
    start = order.start_date
    if not start:
        return False

    days_since_start = (today - start).days
    if days_since_start < 0:
        return False

    if order.frequency == 'weekly':
        return days_since_start % 7 == 0
    elif order.frequency == 'monthly':
        return today.day == start.day or (
            today.day == 1 and start.day > 28  # Handle months with fewer days
        )
    elif order.frequency == 'quarterly':
        return days_since_start % 90 == 0
    return False


def _notify_insufficient_funds(user_profile, order):
    """Notify a user that their standing order failed due to insufficient funds."""
    from Notifications.models import create_notification
    try:
        create_notification(
            recipient=user_profile.user,
            notification_type='payment_failed',
            message=(
                f"Your standing order to {order.provider.name} for "
                f"KES {order.amount} failed: insufficient wallet balance."
            ),
            action_url="/payments/bills",
        )
    except Exception as e:
        logger.error(f"Failed to send insufficient funds notification: {e}")


# ============================================================================
# LOAN OVERDUE CHECK & PENALTY APPLICATION
# ============================================================================

@shared_task
def check_loan_overdue():
    """
    Find loan repayments that are overdue and update loan status.
    Runs daily at 07:00.
    """
    from Payment.models import LoanApplication, LoanRepayment
    from Notifications.models import create_notification

    logger.info("Running check_loan_overdue task")
    now = timezone.now()
    updated = 0

    # Find repayments that are past due and not yet paid
    overdue_repayments = LoanRepayment.objects.filter(
        status='pending',
        due_date__lt=now
    ).select_related('loan_application', 'loan_application__applicant')

    for repayment in overdue_repayments:
        repayment.status = 'overdue'
        repayment.save()

        loan = repayment.loan_application
        if loan.status != 'overdue':
            loan.status = 'overdue'
            loan.save()

        # Notify borrower
        try:
            applicant = loan.applicant
            if applicant and applicant.user:
                create_notification(
                    recipient=applicant.user.user,
                    notification_type='loan_overdue',
                    message=(
                        f"Your loan repayment of KES {repayment.amount_due} "
                        f"was due on {repayment.due_date.strftime('%Y-%m-%d')} and is now overdue."
                    ),
                    action_url="/payments/loans",
                )
                
                # Trigger SMS Alert
                try:
                    from Notifications.services.sms_service import send_sms
                    phone_number = getattr(applicant.user.user, 'phone_number', None)
                    if not phone_number and hasattr(applicant.user.user, 'profile'):
                        phone_number = getattr(applicant.user.user.profile, 'phone_number', None)
                    
                    if phone_number:
                        sms_msg = f"Qomrade: Your loan repayment of KES {repayment.amount_due} is OVERDUE. Please pay to avoid penalties."
                        send_sms(str(phone_number), sms_msg)
                except Exception as sms_e:
                    logger.error(f"Failed to send SMS for overdue loan: {sms_e}")
                    
        except Exception as e:
            logger.error(f"Failed to notify about overdue loan: {e}")

        updated += 1

    logger.info(f"Overdue repayments found: {updated}")
    return f"Overdue repayments: {updated}"


@shared_task
def apply_late_penalties():
    """
    Apply late penalties to overdue loan repayments.
    Runs daily at 09:00.
    """
    from Payment.models import LoanRepayment
    from Payment.services.penalty_engine import calculate_loan_penalty

    logger.info("Running apply_late_penalties task")
    applied = 0

    overdue_repayments = LoanRepayment.objects.filter(
        status='overdue'
    ).select_related('loan_application__product')

    for repayment in overdue_repayments:
        try:
            penalty = calculate_loan_penalty(repayment)
            if penalty > 0:
                repayment.penalty = penalty
                repayment.save()
                applied += 1
                logger.info(f"Applied penalty {penalty} to repayment {repayment.id}")
        except Exception as e:
            logger.error(f"Failed to apply penalty to repayment {repayment.id}: {e}")

    logger.info(f"Penalties applied: {applied}")
    return f"Penalties applied: {applied}"


# ============================================================================
# INSURANCE EXPIRY CHECK
# ============================================================================

@shared_task
def check_insurance_expiry():
    """
    Check for expiring and lapsed insurance policies.
    Runs daily at 07:30.
    """
    from Payment.models import InsurancePolicy
    from Notifications.models import create_notification

    logger.info("Running check_insurance_expiry task")
    now = timezone.now()
    today = now.date()

    expired = 0
    lapsed = 0
    warned = 0

    # 1. Expire policies past end_date
    expired_policies = InsurancePolicy.objects.filter(
        status='active',
        end_date__lt=today
    )
    for policy in expired_policies:
        policy.status = 'expired'
        policy.save()
        expired += 1

    # 2. Lapse policies with missed premiums > 30 days
    overdue_threshold = today - timedelta(days=30)
    lapsable_policies = InsurancePolicy.objects.filter(
        status='active',
        next_payment_date__lt=overdue_threshold
    )
    for policy in lapsable_policies:
        policy.status = 'lapsed'
        policy.save()
        lapsed += 1

        # Notify user
        try:
            if policy.user and policy.user.user:
                create_notification(
                    recipient=policy.user.user,
                    notification_type='insurance_lapsed',
                    message=(
                        f"Your insurance policy {policy.policy_number} has lapsed "
                        f"due to missed premium payments."
                    ),
                    action_url="/payments/insurance",
                )
        except Exception:
            pass

    # 3. Warn users about upcoming premium due dates (7 days notice)
    warning_date = today + timedelta(days=7)
    upcoming_policies = InsurancePolicy.objects.filter(
        status='active',
        next_payment_date__lte=warning_date,
        next_payment_date__gte=today
    )
    for policy in upcoming_policies:
        try:
            if policy.user and policy.user.user:
                create_notification(
                    recipient=policy.user.user,
                    notification_type='insurance_premium_due',
                    message=(
                        f"Your insurance premium of KES {policy.product.premium_amount} "
                        f"for policy {policy.policy_number} is due on "
                        f"{policy.next_payment_date.strftime('%Y-%m-%d')}."
                    ),
                    action_url="/payments/insurance",
                )
                warned += 1
        except Exception:
            pass

    logger.info(f"Insurance check: expired={expired}, lapsed={lapsed}, warned={warned}")
    return f"Expired: {expired}, Lapsed: {lapsed}, Warned: {warned}"


# ============================================================================
# DISPUTE TIMEOUT CHECK
# ============================================================================

@shared_task
def check_dispute_timeouts():
    """
    Auto-resolve escrow disputes where seller hasn't responded within 72 hours.
    Runs daily at 10:00.
    """
    from Payment.models import EscrowTransaction, EscrowDispute, TransactionToken
    from Notifications.models import create_notification

    logger.info("Running check_dispute_timeouts task")
    resolved = 0
    timeout_threshold = timezone.now() - timedelta(hours=72)

    # Find disputed escrows where dispute was filed > 72h ago
    # and seller has not responded (no evidence from seller, no counter-claim)
    timed_out_escrows = EscrowTransaction.objects.filter(
        status='disputed',
        updated_at__lte=timeout_threshold
    ).select_related('buyer', 'seller')

    for escrow in timed_out_escrows:
        try:
            with db_transaction.atomic():
                # Auto-resolve in buyer's favor
                escrow.status = 'refunded'
                escrow.save()

                # Refund buyer
                buyer_profile = escrow.buyer
                if buyer_profile:
                    buyer_profile.wallet_balance += escrow.amount
                    buyer_profile.save()

                    # Create refund transaction
                    TransactionToken.objects.create(
                        receiver_profile=buyer_profile,
                        amount=escrow.amount,
                        transaction_type='refund',
                        status='completed',
                        description=f"Auto-refund: Escrow dispute timeout (72h seller no-response)",
                    )

                # Notify both parties
                for profile, msg in [
                    (escrow.buyer, "Your escrow dispute was auto-resolved in your favor (seller did not respond within 72 hours)."),
                    (escrow.seller, "An escrow dispute was auto-resolved against you because you did not respond within 72 hours."),
                ]:
                    if profile and profile.user:
                        try:
                            create_notification(
                                recipient=profile.user.user,
                                notification_type='escrow_resolved',
                                message=msg,
                                action_url=f"/payments/escrow",
                            )
                            
                            # Trigger SMS Alert
                            try:
                                from Notifications.services.sms_service import send_sms
                                phone_number = getattr(profile.user.user, 'phone_number', None)
                                if not phone_number and hasattr(profile.user.user, 'profile'):
                                    phone_number = getattr(profile.user.user.profile, 'phone_number', None)
                                
                                if phone_number:
                                    sms_msg = f"Qomrade: Escrow {escrow.id} auto-resolved. Log in for details."
                                    send_sms(str(phone_number), sms_msg)
                            except Exception as sms_e:
                                logger.error(f"Failed to send SMS for escrow timeout: {sms_e}")
                                
                        except Exception:
                            pass

                resolved += 1
                logger.info(f"Auto-resolved escrow {escrow.id} in buyer's favor (timeout)")

        except Exception as e:
            logger.error(f"Failed to auto-resolve escrow {escrow.id}: {e}")

    logger.info(f"Dispute timeouts resolved: {resolved}")
    return f"Timeouts resolved: {resolved}"


# ============================================================================
# CREDIT SCORE RECOMPUTATION
# ============================================================================

@shared_task
def recompute_credit_scores():
    """
    Recompute credit scores for all users with payment profiles.
    Runs weekly (Sunday 02:00).
    """
    from Payment.models import PaymentProfile, CreditScore
    from Payment.services.credit_scoring import compute_credit_score

    logger.info("Running recompute_credit_scores task")
    updated = 0
    errors = 0

    profiles = PaymentProfile.objects.filter(
        user__isnull=False
    ).select_related('user', 'user__user')

    for profile in profiles:
        try:
            score_data = compute_credit_score(profile.user)

            # Update or create CreditScore record
            credit_score, created = CreditScore.objects.update_or_create(
                user=profile,
                defaults={
                    'score': score_data['total_score'],
                    'savings_score': score_data['savings_score'],
                    'repayment_score': score_data['repayment_score'],
                    'group_score': score_data['group_score'],
                    'transaction_score': score_data['transaction_score'],
                    'tenure_score': score_data['tenure_score'],
                    'last_updated': timezone.now(),
                }
            )
            updated += 1

        except Exception as e:
            logger.error(f"Failed to compute credit score for profile {profile.id}: {e}")
            errors += 1

    logger.info(f"Credit scores updated: {updated}, errors: {errors}")
    return f"Updated: {updated}, Errors: {errors}"


# ============================================================================
# GROUP INVITATION EXPIRATION
# ============================================================================

@shared_task
def expire_group_invitations():
    """
    Auto-expire pending group invitations that have passed their expiry date.
    Runs daily at 00:30.
    """
    from Payment.models import GroupInvitation
    from Notifications.models import create_notification

    logger.info("Running expire_group_invitations task")
    now = timezone.now()
    
    expired_invites = GroupInvitation.objects.filter(
        status='pending',
        expires_at__lt=now
    ).select_related('payment_group', 'invited_user')

    count = 0
    for invite in expired_invites:
        invite.status = 'expired'
        invite.save()
        count += 1
        
        # Notify the inviter
        try:
            if invite.invited_by and invite.invited_by.user:
                create_notification(
                    recipient=invite.invited_by.user,
                    notification_type='invitation_expired',
                    message=f"Your invitation to {invite.invited_user or invite.invited_email} for group '{invite.payment_group.name}' has expired.",
                    action_url=f"/payments/groups/{invite.payment_group.id}",
                )
        except Exception as e:
            logger.error(f"Failed to notify about expired invitation {invite.id}: {e}")

    logger.info(f"Expired invitations: {count}")
    return f"Expired: {count}"


# ============================================================================
# PIGGY BANK INTEREST ACCRUAL
# ============================================================================

@shared_task
def accrue_piggy_bank_interest():
    """
    Accrue daily interest on fixed_deposit type piggy banks.
    Runs daily at 01:00.
    """
    from Payment.models import GroupTarget

    logger.info("Running accrue_piggy_bank_interest task")
    accrued = 0

    fixed_deposits = GroupTarget.objects.filter(
        savings_type='fixed_deposit',
        status='active',
        interest_rate__gt=0,
        current_amount__gt=0
    )

    for piggy in fixed_deposits:
        try:
            # Daily interest = (annual_rate / 365) * current_balance
            daily_rate = piggy.interest_rate / Decimal('365')
            daily_interest = (daily_rate / Decimal('100')) * piggy.current_amount
            
            piggy.accrued_interest = (piggy.accrued_interest or Decimal('0.00')) + daily_interest
            piggy.save()
            accrued += 1
        except Exception as e:
            logger.error(f"Failed to accrue interest for piggy {piggy.id}: {e}")

    logger.info(f"Piggy banks interest accrued: {accrued}")
    return f"Accrued: {accrued}"


# ============================================================================
# GROUP AUTOMATION PROCESSING (STANDING ORDERS)
# ============================================================================

@shared_task
def process_group_automations():
    """
    Process active group automations (StandingOrders) that are due.
    Handles contributions, withdrawals, savings, purchases, etc.
    Runs periodically (e.g. daily at 06:15).
    """
    from Payment.models import StandingOrder
    from django.db import transaction as db_transaction
    
    logger.info("Running process_group_automations task")
    now = timezone.now()
    processed = 0
    failed = 0
    
    active_orders = StandingOrder.objects.filter(
        is_active=True,
        next_contribution_date__lte=now
    ).select_related('member__payment_profile', 'member__payment_group')
    
    for order in active_orders:
        try:
            with db_transaction.atomic():
                amount = order.amount
                group = order.member.payment_group
                payment_profile = order.member.payment_profile
                
                if order.automation_type == 'withdraw':
                    _process_automation_withdraw(order, group, amount, payment_profile)
                elif order.automation_type == 'contribute':
                    _process_automation_contribute(order, group, amount, payment_profile)
                elif order.automation_type == 'save':
                    _process_automation_save(order, group, amount, payment_profile)
                elif order.automation_type == 'purchase':
                    _process_automation_purchase(order, group, amount, payment_profile)
                elif order.automation_type == 'loan_repayment':
                    _process_automation_loan_repayment(order, group, amount, payment_profile)
                else:
                    logger.warning(f"Unhandled automation type {order.automation_type} for order {order.id}")
                    
                _update_next_run_date(order)
                processed += 1
                
        except Exception as e:
            logger.error(f"Failed to process group automation {order.id}: {e}")
            failed += 1
            try:
                import random
                from datetime import timedelta
                random_delay = random.randint(15, 120)
                order.next_contribution_date = timezone.now() + timedelta(minutes=random_delay)
                order.save()
                logger.info(f"Rescheduled failed automation {order.id} to retry in {random_delay} minutes")
            except Exception as reschedule_err:
                logger.error(f"Failed to reschedule automation {order.id}: {reschedule_err}")

    logger.info(f"Group automations processed: {processed}, failed: {failed}")
    return f"Processed: {processed}, Failed: {failed}"


def _update_next_run_date(order):
    from datetime import timedelta
    from dateutil.relativedelta import relativedelta
    now = timezone.now()
    
    if order.frequency == 'daily':
        order.next_contribution_date = order.next_contribution_date + timedelta(days=1)
    elif order.frequency == 'weekly':
        order.next_contribution_date = order.next_contribution_date + timedelta(weeks=1)
    elif order.frequency == 'fortnight':
        order.next_contribution_date = order.next_contribution_date + timedelta(days=14)
    elif order.frequency == 'monthly':
        order.next_contribution_date = order.next_contribution_date + relativedelta(months=1)
    
    # Catch up if it's still in the past
    while order.next_contribution_date <= now:
        if order.frequency == 'daily':
            order.next_contribution_date += timedelta(days=1)
        elif order.frequency == 'weekly':
            order.next_contribution_date += timedelta(weeks=1)
        elif order.frequency == 'fortnight':
            order.next_contribution_date += timedelta(days=14)
        elif order.frequency == 'monthly':
            order.next_contribution_date += relativedelta(months=1)
            
    order.save()


def _process_automation_withdraw(order, group, amount, payment_profile):
    from Payment.models import PaymentGroupMember, TransactionToken
    import uuid
    
    if group.current_amount < amount:
        raise ValueError(f"Insufficient group funds {group.current_amount} for withdrawal of {amount}")
        
    mode = order.withdrawal_mode
    if mode == 'all':
        active_members = group.members.filter(is_active=True)
        count = active_members.count()
        if count == 0:
            raise ValueError("No active members to withdraw to")
            
        split_amount = amount / Decimal(str(count))
        group.current_amount -= amount
        group.save()
        
        for m in active_members:
            m.payment_profile.comrade_balance += split_amount
            m.payment_profile.save()
            TransactionToken.objects.create(
                payment_profile=m.payment_profile,
                transaction_code=uuid.uuid4(),
                amount=split_amount,
                transaction_type='transfer',
                description=f"Group automation: Equal withdrawal split from {group.name}",
                payment_group=group
            )
            
    elif mode == 'sequential':
        seq = order.withdrawal_sequence
        if not seq:
            raise ValueError("Withdrawal sequence is empty")
            
        index = order.withdrawal_current_index % len(seq)
        target_member_id = seq[index]
        
        try:
            target_member = PaymentGroupMember.objects.get(id=target_member_id)
        except PaymentGroupMember.DoesNotExist:
            raise ValueError(f"Member {target_member_id} in sequence not found")
            
        group.current_amount -= amount
        group.save()
        
        target_member.payment_profile.comrade_balance += amount
        target_member.payment_profile.save()
        
        TransactionToken.objects.create(
            payment_profile=target_member.payment_profile,
            transaction_code=uuid.uuid4(),
            amount=amount,
            transaction_type='transfer',
            description=f"Group automation: Sequential withdrawal from {group.name}",
            payment_group=group
        )
        
        order.withdrawal_current_index = (index + 1) % len(seq)
        order.save()
        
    elif mode == 'selected':
        recipients = order.withdrawal_recipients
        if not recipients:
            raise ValueError("No withdrawal recipients selected")
            
        members = PaymentGroupMember.objects.filter(id__in=recipients)
        count = members.count()
        if count == 0:
            raise ValueError("Selected members not found")
            
        split_amount = amount / Decimal(str(count))
        group.current_amount -= amount
        group.save()
        
        for m in members:
            m.payment_profile.comrade_balance += split_amount
            m.payment_profile.save()
            TransactionToken.objects.create(
                payment_profile=m.payment_profile,
                transaction_code=uuid.uuid4(),
                amount=split_amount,
                transaction_type='transfer',
                description=f"Group automation: Selected withdrawal from {group.name}",
                payment_group=group
            )

def _process_automation_contribute(order, group, amount, payment_profile):
    from Payment.models import Contribution, TransactionToken, PaymentGroups
    import uuid
    
    if payment_profile.wallet_balance < amount:
        if payment_profile.comrade_balance < amount:
            raise ValueError("Insufficient funds for contribution automation")
        else:
            payment_profile.comrade_balance -= amount
    else:
        payment_profile.wallet_balance -= amount
        
    payment_profile.save()
    
    if order.target_type == 'kitty' and order.target_id:
        try:
            kitty = PaymentGroups.objects.get(id=order.target_id)
            kitty.current_amount += amount
            kitty.save()
            desc = f"Group automation: Contribution to {kitty.name}"
        except PaymentGroups.DoesNotExist:
            raise ValueError("Target kitty not found")
    else:
        group.current_amount += amount
        group.save()
        desc = f"Group automation: Contribution to {group.name}"
        
    order.member.total_contributed += amount
    order.member.save()
    
    txn = TransactionToken.objects.create(
        payment_profile=payment_profile,
        transaction_code=uuid.uuid4(),
        amount=amount,
        transaction_type='transfer',
        description=desc,
        payment_group=group
    )
    
    Contribution.objects.create(
        payment_group=group,
        member=order.member,
        amount=amount,
        transaction=txn
    )

def _process_automation_save(order, group, amount, payment_profile):
    from Payment.models import GroupTarget, TransactionToken, Contribution
    import uuid
    
    if payment_profile.wallet_balance < amount:
        raise ValueError("Insufficient funds for save automation")
        
    try:
        target = GroupTarget.objects.get(id=order.target_id)
    except GroupTarget.DoesNotExist:
        raise ValueError("Target piggy bank not found")
        
    payment_profile.wallet_balance -= amount
    payment_profile.save()
    
    target.current_amount += amount
    target.save()
    
    txn = TransactionToken.objects.create(
        payment_profile=payment_profile,
        transaction_code=uuid.uuid4(),
        amount=amount,
        transaction_type='transfer',
        description=f"Group automation: Savings to {target.name}",
        payment_group=group
    )
    
    Contribution.objects.create(
        payment_group=group,
        target=target,
        member=order.member,
        amount=amount,
        transaction=txn
    )

def _process_automation_purchase(order, group, amount, payment_profile):
    from Payment.models import TransactionToken
    import uuid
    
    if payment_profile.wallet_balance < amount:
        raise ValueError("Insufficient funds for purchase automation")
        
    payment_profile.wallet_balance -= amount
    payment_profile.save()
    
    TransactionToken.objects.create(
        payment_profile=payment_profile,
        transaction_code=uuid.uuid4(),
        amount=amount,
        transaction_type='payment',
        description=f"Group automation: Auto-purchase {order.target_name}",
        payment_group=group
    )

def _process_automation_loan_repayment(order, group, amount, payment_profile):
    from Payment.models import TransactionToken
    import uuid
    
    if payment_profile.wallet_balance < amount:
        raise ValueError("Insufficient funds for loan repayment automation")
        
    payment_profile.wallet_balance -= amount
    payment_profile.save()
    
    TransactionToken.objects.create(
        payment_profile=payment_profile,
        transaction_code=uuid.uuid4(),
        amount=amount,
        transaction_type='loan_repayment',
        description=f"Group automation: Loan Repayment for {order.target_name}",
        payment_group=group
    )
