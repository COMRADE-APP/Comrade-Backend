from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from DeviceManagement.models import UserDevice
from DeviceManagement.serializers import UserDeviceSerializer
from Authentication.device_utils import revoke_device
from Authentication.activity_logger import log_device_activity


class UserDeviceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserDeviceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserDevice.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke/deactivate a device"""
        device = self.get_object()
        
        if device.user != request.user:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        success = revoke_device(request.user, device.id)
        
        if success:
            log_device_activity(request.user, request, 'revoke', device.id)
            return Response({"message": "Device revoked successfully."})
        
        return Response({"detail": "Failed to revoke device."}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def trust(self, request, pk=None):
        """Mark a device as trusted"""
        device = self.get_object()
        
        if device.user != request.user:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        device.trust_level = 'trusted'
        device.save()
        
        log_device_activity(request.user, request, 'trust', device.id)
        
        return Response({"message": "Device marked as trusted."})
