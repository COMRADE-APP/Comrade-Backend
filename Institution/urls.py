"""
Institution URLs Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Institution.views_portal import InstitutionViewSet, DocumentUploadView

router = DefaultRouter()
router.register(r'', InstitutionViewSet, basename='institution')

urlpatterns = [
    path('', include(router.urls)),
    path('<uuid:institution_id>/documents/', DocumentUploadView.as_view(), name='upload-document'),
]
