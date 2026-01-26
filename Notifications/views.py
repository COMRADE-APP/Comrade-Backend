"""
Notification Views
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'marked_read': updated})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'success': True})
    
    @action(detail=False, methods=['post'])
    def clear_all(self, request):
        """Delete all notifications"""
        deleted, _ = self.get_queryset().delete()
        return Response({'deleted': deleted})


class NotificationPreferenceView(APIView):
    """
    Get/update notification preferences
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        prefs, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs)
        return Response(serializer.data)
    
    def patch(self, request):
        prefs, created = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NewNotificationsView(APIView):
    """
    Check for new notifications since a given timestamp (for polling)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        since = request.query_params.get('since')
        queryset = Notification.objects.filter(recipient=request.user, is_read=False)
        
        if since:
            from datetime import datetime
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__gt=since_dt)
            except ValueError:
                pass
        
        count = queryset.count()
        latest = queryset.first()
        
        return Response({
            'new_count': count,
            'has_new': count > 0,
            'latest_at': latest.created_at.isoformat() if latest else None
        })
