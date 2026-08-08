"""URL configuration for the Compliance app."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from Compliance.views import CDDRecordViewSet, ComplianceStatusView

router = DefaultRouter()
router.register(r'cdd', CDDRecordViewSet, basename='cdd')

urlpatterns = [
    path('', include(router.urls)),
    path('status/', ComplianceStatusView.as_view(), name='compliance-status'),
]
