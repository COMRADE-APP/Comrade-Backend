"""
Platform-wide asynchronous tasks including global malware scanning.
"""
import os
import logging
from celery import shared_task
from django.apps import apps
from django.core.files.storage import default_storage
from Funding.services.file_scanner import scan_for_malware, scan_for_nsfw

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scan_model_file(self, app_label, model_name, object_id, file_field_name):
    """
    Generic Celery task that asynchronously scans any file field on any model.
    If malware or NSFW content is detected, the file is deleted and an alert is logged.
    """
    try:
        Model = apps.get_model(app_label, model_name)
        obj = Model.objects.get(pk=object_id)
        file_field = getattr(obj, file_field_name)
        
        if not file_field or not file_field.name:
            return "No file to scan"
            
        file_path = file_field.path
        
        if not os.path.exists(file_path):
            logger.warning(f"File {file_path} not found for scanning")
            return "File missing"
            
        # 1. Malware Scan
        malware_result = scan_for_malware(file_path)
        if malware_result.get('is_clean') == False:
            logger.error(f"[SECURITY] Malware detected in {app_label}.{model_name} ID {object_id}! Deleting file.")
            # Delete the malicious file
            default_storage.delete(file_field.name)
            # Nullify the field if possible
            setattr(obj, file_field_name, None)
            
            # If the model has specific status fields (like FundingDocument or VerificationDocument), update them
            if hasattr(obj, 'scan_status'):
                obj.scan_status = 'malware'
            if hasattr(obj, 'is_safe'):
                obj.is_safe = False
                
            obj.save()
            return f"Malware detected and file deleted"
            
        # 2. NSFW Scan (only runs if it's an image)
        nsfw_result = scan_for_nsfw(file_path)
        if nsfw_result.get('is_safe') == False:
            logger.error(f"[MODERATION] NSFW content detected in {app_label}.{model_name} ID {object_id}! Deleting file.")
            default_storage.delete(file_field.name)
            setattr(obj, file_field_name, None)
            
            if hasattr(obj, 'scan_status'):
                obj.scan_status = 'nsfw_rejected'
            if hasattr(obj, 'is_safe'):
                obj.is_safe = False
                
            obj.save()
            return f"NSFW content detected and file deleted"
            
        # 3. Clean
        if hasattr(obj, 'scan_status'):
            obj.scan_status = 'clean'
        if hasattr(obj, 'is_safe'):
            obj.is_safe = True
        obj.save()
        
        return "Scan passed safely"
        
    except Model.DoesNotExist:
        return "Object no longer exists"
    except Exception as e:
        logger.error(f"Error scanning file {app_label}.{model_name} ID {object_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(name='comrade.tasks.system_heartbeat')
def system_heartbeat():
    """
    Periodic task to confirm Celery workers and scheduler are alive.
    Writes a timestamp to Redis or log.
    """
    from django.core.cache import cache
    import datetime
    
    now = datetime.datetime.now().isoformat()
    cache.set('celery_heartbeat_timestamp', now, timeout=600)
    logger.info(f"Celery Heartbeat recorded at {now}")
    return now
