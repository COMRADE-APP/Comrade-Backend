"""
Verification utility functions for email, website, and document verification
"""
import requests
import dns.resolver
import hashlib
import re
from urllib.parse import urlparse
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import magic  # python-magic for file type detection


class EmailVerifier:
    """Handle email verification"""
    
    @staticmethod
    def send_verification_email(email_verification):
        """Send verification email with code"""
        subject = 'Verify Your Email - Qomrade Platform'
        
        context = {
            'verification_code': email_verification.verification_code,
            'verification_link': f"{settings.FRONTEND_URL}/verify-email/{email_verification.verification_token}",
            'expires_in': '24 hours'
        }
        
        message = f"""
        Welcome to Qomrade!
        
        Your verification code is: {email_verification.verification_code}
        
        Or click this link to verify: {context['verification_link']}
        
        This code expires in 24 hours.
        
        If you didn't request this, please ignore this email.
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email_verification.email],
            fail_silently=False,
        )
    
    @staticmethod
    def is_disposable_email(email):
        """Check if email is from disposable email provider"""
        disposable_domains = [
            'tempmail.com', '10minutemail.com', 'guerrillamail.com',
            'throwaway.email', 'temp-mail.org', 'mailinator.com'
        ]
        domain = email.split('@')[1].lower()
        return domain in disposable_domains


class WebsiteVerifier:
    """Handle website verification and security checks"""
    
    @staticmethod
    def check_dns_verification(domain, token):
        """Check if DNS TXT record exists with verification token"""
        try:
            answers = dns.resolver.resolve(domain, 'TXT')
            for rdata in answers:
                txt_string = str(rdata).strip('"')
                if token in txt_string:
                    return True
            return False
        except Exception as e:
            print(f"DNS verification error: {e}")
            return False
    
    @staticmethod
    def check_file_verification(url, token):
        """Check if verification file exists on website"""
        try:
            verification_url = f"{url.rstrip('/')}/comrade-verify.txt"
            response = requests.get(verification_url, timeout=10)
            
            if response.status_code == 200:
                return token in response.text
            return False
        except Exception as e:
            print(f"File verification error: {e}")
            return False
    
    @staticmethod
    def check_meta_verification(url, token):
        """Check if meta tag exists in HTML"""
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                meta_pattern = f'<meta\\s+name="comrade-verify"\\s+content="{token}"'
                return bool(re.search(meta_pattern, response.text, re.IGNORECASE))
            return False
        except Exception as e:
            print(f"Meta verification error: {e}")
            return False
    
    @staticmethod
    def check_ssl(url):
        """Check if website has valid SSL certificate"""
        try:
            parsed = urlparse(url)
            if parsed.scheme == 'https':
                response = requests.get(url, timeout=10)
                return response.status_code < 400
            return False
        except:
            return False
    
    @staticmethod
    def check_safe_browsing(url):
        """
        Check website safety using Google Safe Browsing API
        Requires GOOGLE_SAFE_BROWSING_API_KEY in settings
        """
        api_key = getattr(settings, 'GOOGLE_SAFE_BROWSING_API_KEY', None)
        
        if not api_key:
            print("Google Safe Browsing API key not configured")
            return {'is_safe': True, 'threats': []}  # Skip if not configured
        
        endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
        
        payload = {
            "client": {
                "clientId": "comrade-platform",
                "clientVersion": "1.0.0"
            },
            "threatInfo": {
                "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url}]
            }
        }
        
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                matches = data.get('matches', [])
                
                return {
                    'is_safe': len(matches) == 0,
                    'threats': matches
                }
            else:
                return {'is_safe': True, 'threats': [], 'error': 'API request failed'}
        
        except Exception as e:
            print(f"Safe Browsing check error: {e}")
            return {'is_safe': True, 'threats': [], 'error': str(e)}


class DocumentVerifier:
    """Handle document verification"""
    
    ALLOWED_MIME_TYPES = [
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/jpg',
    ]
    
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_file(file):
        """Validate file type and size"""
        errors = []
        
        # Check file size
        if file.size > DocumentVerifier.MAX_FILE_SIZE:
            errors.append(f"File size exceeds maximum allowed size of 10MB")
        
        # Check MIME type
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)  # Reset file pointer
        
        if mime not in DocumentVerifier.ALLOWED_MIME_TYPES:
            errors.append(f"File type {mime} not allowed. Only PDF and images (JPG, PNG) are accepted.")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def calculate_hash(file):
        """Calculate SHA-256 hash of file"""
        hasher = hashlib.sha256()
        for chunk in file.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()
    
    @staticmethod
    def scan_virus(file):
        """
        Placeholder for virus scanning
        In production, integrate with ClamAV or similar
        """
        # TODO: Integrate with antivirus service
        return True  # Assume safe for now


class VerificationWorkflow:
    """Manage verification workflow progression"""
    
    @staticmethod
    def can_submit(verification_request):
        """Check if request can be submitted"""
        checks = []
        
        # Check email verification
        if hasattr(verification_request, 'emailverification_set'):
            email_verified = verification_request.emailverification_set.filter(verified=True).exists()
            checks.append(('email', email_verified))
        
        # Check website verification (optional)
        if verification_request.official_website:
            if hasattr(verification_request, 'websiteverification_set'):
                website_verified = verification_request.websiteverification_set.filter(domain_verified=True).exists()
                checks.append(('website', website_verified))
        
        # Check documents
        if hasattr(verification_request, 'verificationdocument_set'):
            has_documents = verification_request.verificationdocument_set.count() >= 2  # Minimum 2 documents
            checks.append(('documents', has_documents))
        
        return all(check[1] for check in checks), checks
    
    @staticmethod
    def auto_activate(verification_request):
        """Automatically activate institution/organization after approval"""
        from Institution.models import Institution
        from Organisation.models import Organisation
        from Verification.models import InstitutionVerificationRequest, OrganizationVerificationRequest
        
        if isinstance(verification_request, InstitutionVerificationRequest):
            institution = Institution.objects.create(
                name=verification_request.institution_name,
                institution_type=verification_request.institution_type,
                country=verification_request.country,
                state=verification_request.state,
                city=verification_request.city,
                address=verification_request.address,
                official_email=verification_request.official_email,
                official_website=verification_request.official_website,
                phone_number=verification_request.phone_number,
                created_by=verification_request.submitted_by,
            )
            
            # Assign creator as admin
            # TODO: Create admin role and assign
            
            verification_request.institution = institution
            verification_request.status = 'activated'
            verification_request.save()
            
            return institution
        
        elif isinstance(verification_request, OrganizationVerificationRequest):
            organization = Organisation.objects.create(
                name=verification_request.organization_name,
                organization_type=verification_request.organization_type,
                country=verification_request.country,
                state=verification_request.state,
                city=verification_request.city,
                address=verification_request.address,
                official_email=verification_request.official_email,
                official_website=verification_request.official_website,
                phone_number=verification_request.phone_number,
                created_by=verification_request.submitted_by,
            )
            
            verification_request.organization = organization
            verification_request.status = 'activated'
            verification_request.save()
            
            return organization
        
        return None
