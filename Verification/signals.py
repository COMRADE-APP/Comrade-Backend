"""
Signals for verification workflow automation
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from Verification.models import (
    EntityVerificationRequest,
    VerificationActivity
)


@receiver(post_save, sender=EntityVerificationRequest)
def log_entity_verification_activity(sender, instance, created, **kwargs):
    """Log activity when entity verification is created or updated"""
    if created:
        VerificationActivity.objects.create(
            verification_request=instance,
            action='created',
            performed_by=instance.submitted_by,
            details={'entity_type': instance.entity_type}
        )