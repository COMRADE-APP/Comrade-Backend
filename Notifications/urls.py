"""
Notification URLs
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationPreferenceView, NewNotificationsView

router = DefaultRouter()
router.register('', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('new/', NewNotificationsView.as_view(), name='new-notifications'),
    path('', include(router.urls)),
]
