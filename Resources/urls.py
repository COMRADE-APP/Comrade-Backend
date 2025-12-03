from django.urls import path, include
from rest_framework.routers import DefaultRouter
import rest_framework.urls
from Resources.views import ResourceViewSet, ResourceVisibilityViewSet
import rest_framework

router = DefaultRouter()

router.register(r'resource', ResourceViewSet, basename='resource')
router.register(r'resource_visibility', ResourceVisibilityViewSet, basename='resource_visibility')

urlpatterns = [
    path('', include(router.urls)),
]