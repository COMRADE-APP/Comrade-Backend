"""
AllAuth Social Account Adapter
Customizes OAuth behavior for Google and Facebook authentication
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.shortcuts import redirect
import logging

logger = logging.getLogger(__name__)


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for social authentication
    Handles OAuth redirects and user profile creation
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed (and before the pre_social_login signal is emitted).
        
        We use this to link social accounts to existing users if email matches.
        """
        # If the user is already logged in, connect the social account
        if sociallogin.is_existing:
            return
        
        # Try to connect social account to existing user with same email
        try:
            email = sociallogin.account.extra_data.get('email', '').lower()
            if email:
                from Authentication.models import CustomUser
                try:
                    user = CustomUser.objects.get(email=email)
                    sociallogin.connect(request, user)
                    logger.info(f"Connected social account to existing user: {email}")
                except CustomUser.DoesNotExist:
                    pass
        except Exception as e:
            logger.error(f"Error in pre_social_login: {e}")
    
    def save_user(self, request, sociallogin, form=None):
        """
        Saves a newly signed up social login user.
        Creates associated Profile when user is created via OAuth.
        """
        user = super().save_user(request, sociallogin, form)
        
        try:
            # Create Profile if it doesn't exist
            from Authentication.models import Profile
            if not hasattr(user, 'profile'):
                Profile.objects.create(user=user)
                logger.info(f"Created profile for OAuth user: {user.email}")
        except Exception as e:
            logger.error(f"Error creating profile for OAuth user: {e}")
        
        return user
    
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the URL to redirect to after successfully connecting a social account.
        """
        return f"{settings.FRONTEND_URL}/dashboard"
    
    def get_login_redirect_url(self, request):
        """
        Returns the URL to redirect to after a successful social login.
        Redirect to frontend with tokens in URL params.
        """
        return f"{settings.FRONTEND_URL}/auth/callback"


class MyAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter for account registration
    """
    
    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Custom email confirmation URL that redirects to frontend
        """
        url = f"{settings.FRONTEND_URL}/auth/verify-email/{emailconfirmation.key}/"
        return url
