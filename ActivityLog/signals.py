from django.db.models.signals import post_save
from django.dispatch import receiver
from Payment.models import TransactionHistory, EscrowTransaction
from ActivityLog.models import ActionLog, UserActivity
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=TransactionHistory)
def log_financial_transaction(sender, instance, created, **kwargs):
    """
    Creates an immutable audit log for every financial transaction.
    """
    if created:
        try:
            # Determine user from payment profile
            user = None
            if instance.payment_profile and instance.payment_profile.user:
                user = instance.payment_profile.user.user

            action_type = f"transaction_{instance.transaction_type}"
            
            details = {
                'transaction_id': str(instance.id),
                'transaction_code': str(getattr(instance, 'transaction_code', '')),
                'amount': str(instance.amount),
                'status': getattr(instance, 'status', 'completed'),
                'description': instance.description,
            }

            ActionLog.objects.create(
                user=user,
                action=action_type,
                details=details
            )
            
            # Also add to general user activity for timeline viewing
            if user:
                UserActivity.objects.create(
                    user=user,
                    activity_type='payment',
                    description=f"Transaction: {instance.transaction_type} of {instance.amount}",
                    metadata=details
                )
        except Exception as e:
            logger.error(f"Failed to create audit log for transaction {instance.id}: {str(e)}")


@receiver(post_save, sender=EscrowTransaction)
def log_escrow_transaction(sender, instance, created, **kwargs):
    """
    Creates an audit log for marketplace/escrow state changes.
    """
    try:
        user = instance.buyer.user if instance.buyer else None
        
        # If not created, log the state change
        action = "escrow_created" if created else f"escrow_status_{instance.status}"
        
        details = {
            'escrow_id': str(instance.id),
            'amount': str(instance.amount),
            'status': instance.status,
            'title': getattr(instance, 'title', ''),
        }

        ActionLog.objects.create(
            user=user,
            action=action,
            details=details
        )
    except Exception as e:
        logger.error(f"Failed to create audit log for escrow {instance.id}: {str(e)}")
