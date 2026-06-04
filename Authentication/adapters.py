from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

# Map Google locale → ISO country code
GOOGLE_LOCALE_TO_COUNTRY = {
    'af': 'ZA', 'am': 'ET', 'ar': 'SA', 'az': 'AZ', 'be': 'BY',
    'bg': 'BG', 'bn': 'BD', 'bs': 'BA', 'ca': 'ES', 'ce': 'RU',
    'co': 'FR', 'cs': 'CZ', 'cy': 'GB', 'da': 'DK', 'de': 'DE',
    'el': 'GR', 'en': 'US', 'eo': 'US', 'es': 'ES', 'et': 'EE',
    'eu': 'ES', 'fa': 'IR', 'fi': 'FI', 'fr': 'FR', 'fy': 'NL',
    'ga': 'IE', 'gd': 'GB', 'gl': 'ES', 'gu': 'IN', 'ha': 'NG',
    'he': 'IL', 'hi': 'IN', 'hr': 'HR', 'ht': 'HT', 'hu': 'HU',
    'hy': 'AM', 'id': 'ID', 'ig': 'NG', 'is': 'IS', 'it': 'IT',
    'iw': 'IL', 'ja': 'JP', 'jv': 'ID', 'ka': 'GE', 'kk': 'KZ',
    'km': 'KH', 'kn': 'IN', 'ko': 'KR', 'ku': 'IQ', 'ky': 'KG',
    'la': 'VA', 'lb': 'LU', 'lo': 'LA', 'lt': 'LT', 'lv': 'LV',
    'mg': 'MG', 'mi': 'NZ', 'mk': 'MK', 'ml': 'IN', 'mn': 'MN',
    'mr': 'IN', 'ms': 'MY', 'mt': 'MT', 'my': 'MM', 'nb': 'NO',
    'ne': 'NP', 'nl': 'NL', 'nn': 'NO', 'no': 'NO', 'ny': 'MW',
    'or': 'IN', 'pa': 'IN', 'pl': 'PL', 'ps': 'AF', 'pt': 'PT',
    'ro': 'RO', 'ru': 'RU', 'rw': 'RW', 'sd': 'PK', 'si': 'LK',
    'sk': 'SK', 'sl': 'SI', 'sm': 'WS', 'sn': 'ZW', 'so': 'SO',
    'sq': 'AL', 'sr': 'RS', 'st': 'ZA', 'su': 'ID', 'sv': 'SE',
    'sw': 'KE', 'ta': 'IN', 'te': 'IN', 'tg': 'TJ', 'th': 'TH',
    'tk': 'TM', 'tl': 'PH', 'tr': 'TR', 'tt': 'RU', 'ug': 'CN',
    'uk': 'UA', 'ur': 'PK', 'uz': 'UZ', 'vi': 'VN', 'xh': 'ZA',
    'yi': 'US', 'yo': 'NG', 'zh': 'CN', 'zu': 'ZA',
}
from allauth.socialaccount.models import EmailAddress
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class MyAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for email-only authentication
    No username field - email is the primary identifier
    """
    
    def get_login_redirect_url(self, request):
        """Redirect to backend JWT callback which generates tokens and redirects to frontend"""
        # Redirect to our JWT callback endpoint which will generate tokens
        # and redirect to frontend with tokens in URL
        provider = getattr(request, 'socialaccount_provider', 'google')
        return f"/auth/{provider}/callback/"
    
    def get_signup_redirect_url(self, request):
        """Redirect to backend JWT callback which generates tokens and redirects to frontend"""
        provider = getattr(request, 'socialaccount_provider', 'google')
        return f"/auth/{provider}/callback/"
    
    def save_user(self, request, user, form, commit=True):
        """
        Save user with email as primary identifier
        Username is set to None
        """
        user = super().save_user(request, user, form, commit=False)
        user.username = None  # Force username to None
        user.is_active = True
        
        if commit:
            user.save()
            # Auto-verify email for email/password registration
            email, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email.lower()
            )
            if created or not email.verified:
                email.verified = True
                email.primary = True
                email.save()
        
        return user


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for OAuth providers
    Ensures email-only authentication and proper redirects
    """
    
    def get_login_redirect_url(self, request):
        """Redirect to backend JWT callback which generates tokens and redirects to frontend"""
        # Try to get the provider from the request or sociallogin
        provider = 'google'  # Default fallback
        if hasattr(request, 'session') and 'socialaccount_sociallogin' in request.session:
            try:
                sociallogin = request.session.get('socialaccount_sociallogin')
                if sociallogin:
                    provider = sociallogin.get('account', {}).get('provider', 'google')
            except:
                pass
        return f"/auth/{provider}/callback/"
    
    def get_signup_redirect_url(self, request):
        """Redirect to backend JWT callback which generates tokens and redirects to frontend"""
        return self.get_login_redirect_url(request)
    
    def populate_user(self, request, sociallogin, data):
        """Populate user from social data without username"""
        user = super().populate_user(request, sociallogin, data)
        user.username = None  # No username needed

        # Map locale to country_of_origin (Google, Apple, etc.)
        extra = sociallogin.account.extra_data or {}
        raw_locale = extra.get('locale', '') or data.get('locale', '')
        if raw_locale:
            lang_part = raw_locale.split('-')[0].split('_')[0].lower()
            mapped = GOOGLE_LOCALE_TO_COUNTRY.get(lang_part)
            if mapped:
                user.country_of_origin = mapped

        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save social login user
        Ensures email is verified and username is None
        """
        user = super().save_user(request, sociallogin, form)
        user.username = None
        user.is_active = True
        user.save()
        
        # Auto-verify email for social logins
        if user.email:
            email, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email.lower()
            )
            email.verified = True
            email.primary = True
            email.save()
        
        logger.info(f"Social user saved: {user.email}")
        return user
    
    def pre_social_login(self, request, sociallogin):
        """
        Connect social account to existing user with same email
        """
        if sociallogin.is_existing:
            return
        
        try:
            email = sociallogin.account.extra_data.get('email')
            if not email:
                return
            
            # Try to find existing user with same email
            from Authentication.models import CustomUser
            existing_user = CustomUser.objects.filter(email=email).first()
            
            if existing_user:
                # Connect social account to existing user
                sociallogin.connect(request, existing_user)
                logger.info(f"Connected social account to existing user: {email}")
                
        except Exception as e:
            logger.error(f"Error in pre_social_login: {str(e)}")