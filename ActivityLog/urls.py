from django.urls import path
from rest_framework.routers import DefaultRouter
from ActivityLog.views import UserActivityViewSet, ActionLogViewSet

router = DefaultRouter()
router.register(r'activities', UserActivityViewSet, basename='activity')
router.register(r'actions', ActionLogViewSet, basename='action')

urlpatterns = router.urls
