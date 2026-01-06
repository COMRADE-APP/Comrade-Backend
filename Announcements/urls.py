"""
Announcements URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Announcements.views_enhanced import AnnouncementViewSet, ServiceConversionView

router = DefaultRouter()
router.register(r'', AnnouncementViewSet, basename='announcement')
router.register(r'convert', ServiceConversionView, basename='convert-to-announcement')

urlpatterns = [
    path('', include(router.urls)),
]