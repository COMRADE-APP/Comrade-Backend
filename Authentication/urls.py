"""
Authentication URL Configuration with TOTP
"""
from django.urls import path, include
from Authentication.views_totp import (
    TOTPSetupView, TOTPVerifySetupView,
    TOTPVerifyLoginView, TOTPDisableView, TOTPBackupCodesView
)

urlpatterns = [
    # Django allauth URLs
    path('', include('allauth.urls')),
    
    # TOTP/2FA endpoints
    path('totp/setup/', TOTPSetupView.as_view(), name='totp-setup'),
    path('totp/verify-setup/', TOTPVerifySetupView.as_view(), name='totp-verify-setup'),
    path('totp/verify-login/', TOTPVerifyLoginView.as_view(), name='totp-verify-login'),
    path('totp/disable/', TOTPDisableView.as_view(), name='totp-disable'),
    path('totp/backup-codes/', TOTPBackupCodesView.as_view(), name='totp-backup-codes'),
]
