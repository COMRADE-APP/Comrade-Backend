"""
Verification URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EntityVerificationViewSet, LivenessVerificationViewSet,
    VerificationDocumentViewSet, VerificationVideoViewSet,
    IdentificationVerificationViewSet, VerificationChecklistViewSet,
    VerificationStatsView
)

router = DefaultRouter()
router.register(r'verifications', EntityVerificationViewSet, basename='verifications')
router.register(r'liveness', LivenessVerificationViewSet, basename='liveness')
router.register(r'documents', VerificationDocumentViewSet, basename='documents')
router.register(r'videos', VerificationVideoViewSet, basename='videos')
router.register(r'identifications', IdentificationVerificationViewSet, basename='identifications')
router.register(r'checklist', VerificationChecklistViewSet, basename='checklist')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', VerificationStatsView.as_view(), name='verification-stats'),
]