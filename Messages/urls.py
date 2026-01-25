from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessagingSettingsView

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    path('settings/', MessagingSettingsView.as_view(), name='messaging-settings'),
    path('', include(router.urls)),
]
