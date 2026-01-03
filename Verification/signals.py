"""
Signals for verification workflow automation
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from Verification.models import (
    InstitutionVerificationRequest,
    OrganizationVerificationRequest,
    VerificationActivity
)
from datetime import datetime


@receiver(post_save, sender=InstitutionVerificationRequest)
def log_institution_verification_activity(sender, instance, created, **kwargs):
    """Log activity when institution verification is created or updated"""
    if created:
        VerificationActivity.objects.create(
            verification_request=instance,
            action='created',
            performed_by=instance.submitted_by,
            details={'institution_name': instance.institution_name}
        )


@receiver(post_save, sender=OrganizationVerificationRequest)
def log_organization_verification_activity(sender, instance, created, **kwargs):
    """Log activity when organization verification is created or updated"""
    if created:
        VerificationActivity.objects.create(
            verification_request=instance,
            action='created',
            performed_by=instance.submitted_by,
            details={'organization_name': instance.organization_name}
        )
