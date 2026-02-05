"""
File Scanning Service for Funding Documents
Integrates with VirusTotal (malware) and SightEngine (NSFW) APIs
"""
import os
import requests
import hashlib
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# API Configuration
VIRUSTOTAL_API_KEY = os.getenv('VIRUSTOTAL_API_KEY', '')
SIGHTENGINE_API_USER = os.getenv('SIGHTENGINE_API_USER', '')
SIGHTENGINE_API_SECRET = os.getenv('SIGHTENGINE_API_SECRET', '')

VIRUSTOTAL_UPLOAD_URL = "https://www.virustotal.com/api/v3/files"
VIRUSTOTAL_ANALYSIS_URL = "https://www.virustotal.com/api/v3/analyses/{}"
SIGHTENGINE_URL = "https://api.sightengine.com/1.0/check.json"

# File type categories
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}


def get_file_hash(file_path):
    """Generate SHA256 hash of file for VirusTotal lookup"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_file_extension(filename):
    """Extract file extension"""
    return os.path.splitext(filename)[1].lower()


def scan_for_malware(file_path):
    """
    Scan file using VirusTotal API
    Returns: dict with 'is_clean', 'threats', 'raw_response'
    """
    if not VIRUSTOTAL_API_KEY or VIRUSTOTAL_API_KEY == 'your-virustotal-api-key':
        logger.warning("VirusTotal API key not configured, skipping malware scan")
        return {'is_clean': True, 'skipped': True, 'reason': 'API key not configured'}
    
    headers = {"x-apikey": VIRUSTOTAL_API_KEY}
    
    try:
        # First, try to check if file was already scanned (by hash)
        file_hash = get_file_hash(file_path)
        check_url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
        
        response = requests.get(check_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # File already analyzed
            data = response.json()
            stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
            malicious = stats.get('malicious', 0)
            suspicious = stats.get('suspicious', 0)
            
            return {
                'is_clean': malicious == 0 and suspicious == 0,
                'threats': malicious + suspicious,
                'stats': stats,
                'scan_id': file_hash
            }
        
        # File not found, upload for scanning
        with open(file_path, 'rb') as f:
            files = {"file": (os.path.basename(file_path), f)}
            upload_response = requests.post(VIRUSTOTAL_UPLOAD_URL, headers=headers, files=files, timeout=60)
        
        if upload_response.status_code == 200:
            analysis_id = upload_response.json().get('data', {}).get('id')
            return {
                'is_clean': None,  # Pending
                'scan_id': analysis_id,
                'status': 'submitted',
                'message': 'File submitted for analysis'
            }
        else:
            logger.error(f"VirusTotal upload failed: {upload_response.text}")
            return {'is_clean': None, 'error': upload_response.text}
            
    except Exception as e:
        logger.error(f"VirusTotal scan error: {str(e)}")
        return {'is_clean': None, 'error': str(e)}


def scan_for_nsfw(file_path):
    """
    Scan image file using SightEngine API for NSFW content
    Returns: dict with 'is_safe', 'nudity_score', 'raw_response'
    """
    if not SIGHTENGINE_API_USER or SIGHTENGINE_API_USER == 'your-sightengine-api-user':
        logger.warning("SightEngine API not configured, skipping NSFW scan")
        return {'is_safe': True, 'skipped': True, 'reason': 'API credentials not configured'}
    
    # Only scan image files
    ext = get_file_extension(file_path)
    if ext not in IMAGE_EXTENSIONS:
        return {'is_safe': True, 'skipped': True, 'reason': 'Not an image file'}
    
    try:
        with open(file_path, 'rb') as f:
            files = {'media': f}
            params = {
                'api_user': SIGHTENGINE_API_USER,
                'api_secret': SIGHTENGINE_API_SECRET,
                'models': 'nudity-2.0,weapon,recreational_drug,gore'
            }
            
            response = requests.post(SIGHTENGINE_URL, files=files, data=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check nudity scores
            nudity = data.get('nudity', {})
            sexual_display = nudity.get('sexual_display', 0)
            erotica = nudity.get('erotica', 0)
            very_suggestive = nudity.get('very_suggestive', 0)
            
            # Check for weapons/drugs/gore
            weapon_score = data.get('weapon', 0)
            drugs_score = data.get('recreational_drug', 0)
            gore_score = data.get('gore', {}).get('prob', 0)
            
            # Thresholds
            is_nsfw = sexual_display > 0.5 or erotica > 0.5 or very_suggestive > 0.7
            is_violent = weapon_score > 0.7 or drugs_score > 0.7 or gore_score > 0.7
            
            return {
                'is_safe': not (is_nsfw or is_violent),
                'nudity_score': max(sexual_display, erotica, very_suggestive),
                'violence_score': max(weapon_score, drugs_score, gore_score),
                'details': {
                    'nudity': nudity,
                    'weapon': weapon_score,
                    'drugs': drugs_score,
                    'gore': gore_score
                }
            }
        else:
            logger.error(f"SightEngine scan failed: {response.text}")
            return {'is_safe': None, 'error': response.text}
            
    except Exception as e:
        logger.error(f"SightEngine scan error: {str(e)}")
        return {'is_safe': None, 'error': str(e)}


def process_document_scan(document_id):
    """
    Main function to scan a FundingDocument
    Should be called asynchronously (e.g., via Celery) after upload
    """
    from Funding.models import FundingDocument
    
    try:
        document = FundingDocument.objects.get(id=document_id)
        file_path = document.file.path
        
        # Update status to scanning
        document.scan_status = 'scanning'
        document.save(update_fields=['scan_status'])
        
        scan_results = {
            'malware': None,
            'nsfw': None
        }
        
        # Run malware scan
        malware_result = scan_for_malware(file_path)
        scan_results['malware'] = malware_result
        
        if malware_result.get('is_clean') == False:
            document.scan_status = 'malware'
            document.scan_result = scan_results
            document.scanned_at = timezone.now()
            document.is_viewable = False
            document.save()
            logger.warning(f"Malware detected in document {document_id}")
            return {'status': 'rejected', 'reason': 'malware'}
        
        # Run NSFW scan for images
        nsfw_result = scan_for_nsfw(file_path)
        scan_results['nsfw'] = nsfw_result
        
        if nsfw_result.get('is_safe') == False:
            document.scan_status = 'nsfw_rejected'
            document.scan_result = scan_results
            document.scanned_at = timezone.now()
            document.is_viewable = False
            document.save()
            logger.warning(f"NSFW content detected in document {document_id}")
            return {'status': 'rejected', 'reason': 'nsfw'}
        
        # All scans passed
        document.scan_status = 'clean'
        document.scan_result = scan_results
        document.scanned_at = timezone.now()
        document.is_viewable = True
        document.save()
        
        logger.info(f"Document {document_id} passed all scans")
        return {'status': 'clean'}
        
    except FundingDocument.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return {'status': 'error', 'reason': 'document_not_found'}
    except Exception as e:
        logger.error(f"Scan processing error for {document_id}: {str(e)}")
        try:
            document.scan_status = 'error'
            document.scan_result = {'error': str(e)}
            document.scanned_at = timezone.now()
            document.save()
        except:
            pass
        return {'status': 'error', 'reason': str(e)}
