"""
Global signals for the Qomrade platform.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from comrade.tasks import scan_model_file
import logging

logger = logging.getLogger(__name__)

# Track which models have been checked so we don't scan them infinitely if resaved
_ALREADY_SCANNED_CACHE = set()


def global_file_scan_receiver(sender, instance, created, **kwargs):
    """
    Listens to every model save. If the model has a FileField or ImageField,
    it queues a Celery task to scan the file for Malware and NSFW content.
    """
    # Skip models from third-party apps or Django internals if desired
    if sender._meta.app_label in ['auth', 'admin', 'contenttypes', 'sessions', 'axes', 'socialaccount']:
        return

    # To avoid resync loops or unnecessary scans, we can check if it's newly created
    # or if the file field specifically changed (harder to track generically).
    # For now, we only trigger on creation to be safe and cost-effective.
    if not created:
        return

    for field in sender._meta.get_fields():
        if isinstance(field, (models.FileField, models.ImageField)):
            file_attr = getattr(instance, field.name)
            
            # If a file was actually uploaded
            if file_attr and file_attr.name:
                # Dispatch the async Celery task
                logger.info(f"Queueing malware/NSFW scan for {sender._meta.app_label}.{sender._meta.model_name} (ID: {instance.pk})")
                scan_model_file.delay(
                    app_label=sender._meta.app_label,
                    model_name=sender._meta.model_name,
                    object_id=instance.pk,
                    file_field_name=field.name
                )
