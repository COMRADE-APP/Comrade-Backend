from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CredentialVerificationViewSet, UserQualificationViewSet,
    BackgroundCheckViewSet, MembershipRequestViewSet,
    InvitationLinkViewSet, PresetUserAccountViewSet
)

router = DefaultRouter()
router.register(r'credentials', CredentialVerificationViewSet, basename='credential-verification')
router.register(r'qualifications', UserQualificationViewSet, basename='user-qualification')
router.register(r'background-checks', BackgroundCheckViewSet, basename='background-check')
router.register(r'membership-requests', MembershipRequestViewSet, basename='membership-request')
router.register(r'invitations', InvitationLinkViewSet, basename='invitation-link')
router.register(r'preset-accounts', PresetUserAccountViewSet, basename='preset-user-account')

urlpatterns = [
    path('', include(router.urls)),
]