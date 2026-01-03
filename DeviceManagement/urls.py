from django.urls import path
from rest_framework.routers import DefaultRouter
from DeviceManagement.views import UserDeviceViewSet

router = DefaultRouter()
router.register(r'devices', UserDeviceViewSet, basename='device')

urlpatterns = router.urls
