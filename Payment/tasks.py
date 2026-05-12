from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from Payment.models import RoundContribution, RoundMemberContribution
from Notifications.models import create_notification
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_round_contribution_reminders():
    """
    Check for active rounds that have upcoming contribution deadlines
    and send reminders to members who haven't contributed to the current cycle.
    """
    logger.info("Running send_round_contribution_reminders task")
    now = timezone.now()
    
    # We want to remind people if the deadline is within the next 48 hours,
    # or if the deadline has passed and they haven't contributed.
    # To avoid spamming, we only send one reminder per cycle, or one every 24h.
    
    active_rounds = RoundContribution.objects.filter(
        status='active',
        next_contribution_date__isnull=False
    )
    
    for round_obj in active_rounds:
        time_until_due = round_obj.next_contribution_date - now
        
        # Determine if we should send a reminder:
        # If due in less than 48 hours, or already overdue
        if time_until_due <= timedelta(hours=48):
            # Let's not spam them. Check last reminder sent.
            # Ideally, we track last_reminder_sent per member per cycle.
            # But simpler: track on the round itself, or just check every 24h.
            if round_obj.last_reminder_sent and (now - round_obj.last_reminder_sent) < timedelta(hours=24):
                continue
                
            group_members = round_obj.payment_group.members.filter(is_active=True)
            
            # Find members who HAVE contributed to the current cycle
            contributed_member_ids = RoundMemberContribution.objects.filter(
                round=round_obj,
                cycle_number=round_obj.current_cycle
            ).values_list('member_id', flat=True)
            
            # Find those who HAVEN'T
            pending_members = group_members.exclude(id__in=contributed_member_ids)
            
            for pm in pending_members:
                message = f"Reminder: Contribute {round_obj.currency} {round_obj.contribution_amount} to round '{round_obj.round_name or round_obj.round_number}' by {round_obj.next_contribution_date.strftime('%Y-%m-%d')}."
                if time_until_due < timedelta(0):
                    message = f"URGENT: Your contribution of {round_obj.currency} {round_obj.contribution_amount} to round '{round_obj.round_name or round_obj.round_number}' is OVERDUE."
                    
                create_notification(
                    recipient=pm.payment_profile.user.user,
                    notification_type='group_contribution',
                    message=message,
                    action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds",
                    extra_data={'group_id': str(round_obj.payment_group.id), 'round_id': str(round_obj.id)}
                )
                
            round_obj.last_reminder_sent = now
            round_obj.save()
            
    return "Reminders processed"
