from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ActivityLog.views import (
    UserActivityViewSet, ActionLogViewSet, ActivitySessionViewSet,
    PermissionConsentViewSet, ConnectionSecurityLogViewSet,
    SearchActivityLogViewSet, ActivityExportView
)

router = DefaultRouter()
router.register(r'activities', UserActivityViewSet, basename='user-activity')
router.register(r'actions', ActionLogViewSet, basename='action-log')
router.register(r'sessions', ActivitySessionViewSet, basename='activity-session')
router.register(r'consents', PermissionConsentViewSet, basename='permission-consent')
router.register(r'connections', ConnectionSecurityLogViewSet, basename='connection-security')
router.register(r'searches', SearchActivityLogViewSet, basename='search-activity')

urlpatterns = [
    path('', include(router.urls)),
    path('export/', ActivityExportView.as_view(), name='activity-export'),
]
