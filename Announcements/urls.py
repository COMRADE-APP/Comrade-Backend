"""
Announcements URL Configuration with Enhanced Features
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Announcements.views import AnnouncementsViewSet
from Announcements.views_enhanced import (
    AnnouncementViewSet as EnhancedAnnouncementViewSet,
    ServiceConversionView,
    OfflineNotificationViewSet
)

router = DefaultRouter()
# Use enhanced viewset for main announcements
router.register(r'', EnhancedAnnouncementViewSet, basename='announcement')
router.register(r'notifications', OfflineNotificationViewSet, basename='offline-notification')

urlpatterns = [
    path('', include(router.urls)),
    # Service conversion endpoint
    path('convert/', ServiceConversionView.as_view(), name='convert-to-announcement'),
    path('convert/history/', ServiceConversionView.as_view(), name='conversion-history'),
]