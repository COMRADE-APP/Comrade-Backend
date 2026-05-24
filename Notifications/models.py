"""
Notification Models
Handles notifications for user interactions (likes, comments, follows, etc.)
"""
from django.db import models
from django.utils import timezone
from Authentication.models import CustomUser


NOTIFICATION_TYPES = (
    ('like', 'Like'),
    ('comment', 'Comment'),
    ('follow', 'Follow'),
    ('repost', 'Repost'),
    ('mention', 'Mention'),
    ('reply', 'Reply'),
    ('research_update', 'Research Update'),
    ('article_published', 'Article Published'),
    ('product_update', 'Product Update'),
    ('system', 'System'),
    ('announcement', 'Announcement'),
    ('recommendation', 'Recommendation'),
    ('trending', 'Trending'),
    ('suggested', 'Suggested'),
    ('profile_view', 'Profile View'),
    ('new_post', 'New Post'),
    ('group_round', 'Group Round'),
    ('group_contribution', 'Group Contribution'),
    ('group_claim', 'Group Claim'),
    ('group_message', 'Group Message'),
    # Provider Notifications
    ('provider_application_submitted', 'Application Submitted'),
    ('provider_application_approved', 'Application Approved'),
    ('provider_application_rejected', 'Application Rejected'),
    ('provider_application_requires_changes', 'Application Requires Changes'),
    ('provider_query_response', 'Query Response'),
    ('provider_transaction_complete', 'Transaction Complete'),
    ('provider_transaction_refund', 'Transaction Refund'),
    ('provider_payout_received', 'Payout Received'),
    ('provider_document_approved', 'Document Approved'),
    ('provider_document_rejected', 'Document Rejected'),
)


class Notification(models.Model):
    """
    Core notification model for all user notifications
    """
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='actions',
        null=True,
        blank=True
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        default='system'
    )
    title = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    
    # Generic relation to any content
    content_type = models.CharField(max_length=100, blank=True)  # e.g., 'opinion', 'research', 'article'
    content_id = models.CharField(max_length=100, blank=True)  # ID of the related content
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Action URL (where to navigate when clicked)
    action_url = models.CharField(max_length=500, blank=True)
    
    # Metadata
    extra_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} notification for {self.recipient.email}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class NotificationPreference(models.Model):
    """
    User preferences for notifications
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notifications - Social
    email_likes = models.BooleanField(default=True)
    email_comments = models.BooleanField(default=True)
    email_follows = models.BooleanField(default=True)
    email_mentions = models.BooleanField(default=True)
    email_reposts = models.BooleanField(default=True)
    email_announcements = models.BooleanField(default=True)
    
    # Push notifications (in-app) - Social
    push_likes = models.BooleanField(default=True)
    push_comments = models.BooleanField(default=True)
    push_follows = models.BooleanField(default=True)
    push_mentions = models.BooleanField(default=True)
    push_reposts = models.BooleanField(default=True)
    push_announcements = models.BooleanField(default=True)
    
    # Provider Email Notifications
    email_provider_application = models.BooleanField(default=True)
    email_provider_approved = models.BooleanField(default=True)
    email_provider_rejected = models.BooleanField(default=True)
    email_provider_query = models.BooleanField(default=True)
    email_provider_transaction = models.BooleanField(default=True)
    email_provider_payout = models.BooleanField(default=True)
    
    # Provider Push Notifications
    push_provider_application = models.BooleanField(default=True)
    push_provider_approved = models.BooleanField(default=True)
    push_provider_rejected = models.BooleanField(default=True)
    push_provider_query = models.BooleanField(default=True)
    push_provider_transaction = models.BooleanField(default=True)
    push_provider_payout = models.BooleanField(default=True)
    
    # Digest settings
    email_digest = models.BooleanField(default=False)  # Send daily digest instead of individual emails
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification preferences for {self.user.email}"


# Notification creation helper
def create_notification(
    recipient,
    notification_type,
    message,
    actor=None,
    content_type='',
    content_id='',
    title='',
    action_url='',
    extra_data=None
):
    """
    Helper function to create notifications
    """
    # Don't notify yourself
    if actor and actor.id == recipient.id:
        return None
    
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        content_type=content_type,
        content_id=str(content_id) if content_id else '',
        action_url=action_url,
        extra_data=extra_data or {}
    )
    
    # ── Auto-dispatch email for critical financial notifications ──
    CRITICAL_EMAIL_TYPES = {
        'payment', 'payment_failed', 'loan_overdue', 'loan_approved',
        'escrow_resolved', 'insurance_lapsed', 'insurance_premium_due',
        'provider_submitted', 'provider_approved', 'kyc_approved', 'kyc_rejected',
        # Provider notifications
        'provider_application_submitted', 'provider_application_approved',
        'provider_application_rejected', 'provider_application_requires_changes',
        'provider_query_response', 'provider_transaction_complete',
        'provider_transaction_refund', 'provider_payout_received',
    }
    if notification_type in CRITICAL_EMAIL_TYPES:
        try:
            from Notifications.services.email_service import EmailService
            user_email = recipient.email
            user_name = getattr(recipient, 'first_name', '') or recipient.email.split('@')[0]
            
            # Map notification type to email template
            template_map = {
                'kyc_approved': 'kyc_approved',
                'kyc_rejected': 'kyc_rejected',
                'payment': 'payout_processed',
                'payment_failed': 'standing_order_failed',
                'loan_overdue': 'loan_overdue',
                'loan_approved': 'loan_approved',
                'escrow_resolved': 'dispute_resolved',
                'insurance_lapsed': None,
                'insurance_premium_due': None,
                # Provider notifications
                'provider_application_submitted': 'provider_app_submitted',
                'provider_application_approved': 'provider_app_approved',
                'provider_application_rejected': 'provider_app_rejected',
                'provider_application_requires_changes': 'provider_app_changes',
                'provider_query_response': 'provider_query_response',
                'provider_transaction_complete': 'provider_transaction',
                'provider_transaction_refund': 'refund_issued',
                'provider_payout_received': 'payout_processed',
            }
            
            template_key = template_map.get(notification_type)
            if template_key:
                EmailService.send(
                    template_key=template_key,
                    recipient_email=user_email,
                    context={
                        'name': user_name,
                        'amount': extra_data.get('amount', '') if extra_data else '',
                        'reason': extra_data.get('reason', '') if extra_data else '',
                        'reference': extra_data.get('reference', '') if extra_data else '',
                        'method': extra_data.get('method', '') if extra_data else '',
                        'due_date': extra_data.get('due_date', '') if extra_data else '',
                        'title': title or '',
                        'resolution': extra_data.get('resolution', '') if extra_data else '',
                        'provider': extra_data.get('provider', '') if extra_data else '',
                    }
                )
            else:
                # Fallback: send the raw notification message as email
                EmailService.send_raw(
                    subject=title or f'Qomrade Alert: {notification_type}',
                    body=message,
                    recipient_email=user_email
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send email for notification {notification.id}: {e}")
    
    # ── Auto-dispatch SMS for priority provider notifications ──
    PRIORITY_SMS_TYPES = {
        'provider_application_approved',
        'provider_application_rejected',
        'provider_transaction_complete',
        'provider_payout_received',
    }
    if notification_type in PRIORITY_SMS_TYPES:
        try:
            from Notifications.services.sms_service import send_sms
            user = instance.recipient
            phone = getattr(user, 'phone_number', None)
            if phone:
                sms_map = {
                    'provider_application_approved': f"Qomrade: Your application to {extra_data.get('provider', 'provider') if extra_data else 'provider'} has been APPROVED!",
                    'provider_application_rejected': f"Qomrade: Your application to {extra_data.get('provider', 'provider') if extra_data else 'provider'} was not approved. Log in for details.",
                    'provider_transaction_complete': f"Qomrade: Transaction of {extra_data.get('amount', '') if extra_data else ''} completed with {extra_data.get('provider', 'provider') if extra_data else 'provider'}.",
                    'provider_payout_received': f"Qomrade: Payout of {extra_data.get('amount', '') if extra_data else ''} received!",
                }
                sms_message = sms_map.get(notification_type)
                if sms_message:
                    send_sms(phone, sms_message)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send SMS for notification {notification.id}: {e}")
    
    return notification


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Notification)
def send_push_notification(sender, instance, created, **kwargs):
    if created:
        from .services.push import PushNotificationService

        prefs = getattr(instance.recipient, 'notification_preferences', None)

        pref_field = None
        if instance.notification_type.startswith('provider_'):
            type_mapping = {
                'provider_application_submitted': 'push_provider_application',
                'provider_application_approved': 'push_provider_approved',
                'provider_application_rejected': 'push_provider_rejected',
                'provider_application_requires_changes': 'push_provider_application',
                'provider_query_response': 'push_provider_query',
                'provider_transaction_complete': 'push_provider_transaction',
                'provider_transaction_refund': 'push_provider_transaction',
                'provider_payout_received': 'push_provider_payout',
                'provider_document_approved': 'push_provider_application',
                'provider_document_rejected': 'push_provider_application',
            }
            pref_field = type_mapping.get(instance.notification_type)
        else:
            pref_field = f"push_{instance.notification_type}s"

        if prefs and pref_field:
            if hasattr(prefs, pref_field) and not getattr(prefs, pref_field):
                return

        title = instance.title or "New Notification"

        PushNotificationService.send_to_user(
            user=instance.recipient,
            title=title,
            body=instance.message,
            data={
                "notification_id": str(instance.id),
                "type": instance.notification_type,
                "action_url": instance.action_url
            }
        )

        # Push via WebSocket for real-time badge update
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'notify_{instance.recipient.id}',
                {
                    'type': 'send_notification',
                    'payload': {
                        'notification_id': str(instance.id),
                        'type': instance.notification_type,
                        'title': title,
                        'message': instance.message,
                        'action_url': instance.action_url,
                    }
                }
            )
        except Exception:
            pass
