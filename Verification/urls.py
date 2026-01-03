from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Verification import views

router = DefaultRouter()
router.register(r'institutions', views.InstitutionVerificationViewSet, basename='institution-verification')
router.register(r'organizations', views.OrganizationVerificationViewSet, basename='organization-verification')

urlpatterns = [
    path('', include(router.urls)),
]
