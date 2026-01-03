from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from ActivityLog.models import UserActivity, ActionLog
from ActivityLog.serializers import UserActivitySerializer, ActionLogSerializer


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserActivity.objects.filter(user=self.request.user)


class ActionLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActionLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ActionLog.objects.filter(user=self.request.user)
