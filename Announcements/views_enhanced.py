"""
Announcements Enhanced Views
Permissions, service conversions, and subscription management
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from Announcements.models import Announcements
from Announcements.enhanced_models import (
    AnnouncementPermission, ServiceAnnouncementConversion,
    AnnouncementSubscription, OfflineAnnouncementNotification
)
from Announcements.serializers import AnnouncementsSerializer


class AnnouncementViewSet(ModelViewSet):
    """Main announcement ViewSet with enhanced features"""
    queryset = Announcements.objects.all()
    serializer_class = AnnouncementsSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['user', 'status', 'visibility']
    search_fields = ['heading', 'content']
    ordering_fields = ['-time_stamp']

    def perform_create(self, serializer):
        """Auto-set user to the authenticated user"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def grant_permission(self, request, pk=None):
        """Grant announcement permissions to a user"""
        announcement = self.get_object()
        user_id = request.data.get('user_id')
        role = request.data.get('role', 'moderator')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if requester has permission to grant
        if announcement.user != request.user:
            return Response(
                {'error': 'Only announcement creator can grant permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create or update permission
        permission, created = AnnouncementPermission.objects.update_or_create(
            announcement=announcement,
            user_id=user_id,
            defaults={
                'role': role,
                'can_create': role in ['admin', 'creator'],
                'can_edit': role in ['admin', 'moderator'],
                'can_delete': role == 'admin',
                'can_moderate': role in ['admin', 'moderator'],
                'granted_by': request.user
            }
        )
        
        return Response({
            'message': f'Permission {"granted" if created else "updated"} successfully',
            'permission': {
                'user_id': str(user_id),
                'role': role,
                'created': created
            }
        })
    
    @action(detail=True, methods=['post'])
    def subscribe(self, request, pk=None):
        """Subscribe to announcement notifications"""
        announcement = self.get_object()
        
        notification_period = request.data.get('notification_period', 'immediate')
        notify_email = request.data.get('notify_email', True)
        notify_push = request.data.get('notify_push', True)
        
        subscription, created = AnnouncementSubscription.objects.update_or_create(
            user=request.user,
            announcement=announcement,
            defaults={
                'notification_period': notification_period,
                'notify_email': notify_email,
                'notify_push': notify_push,
                'notification_enabled': True
            }
        )
        
        return Response({
            'message': f'{"Subscribed" if created else "Subscription updated"} successfully',
            'subscription': {
                'notification_period': notification_period,
                'notify_email': notify_email,
                'notify_push': notify_push
            }
        })
    
    @action(detail=True, methods=['post'])
    def unsubscribe(self, request, pk=None):
        """Unsubscribe from announcement notifications"""
        announcement = self.get_object()
        
        try:
            subscription = AnnouncementSubscription.objects.get(
                user=request.user,
                announcement=announcement
            )
            subscription.notification_enabled = False
            subscription.save()
            
            return Response({
                'message': 'Unsubscribed successfully'
            })
        except AnnouncementSubscription.DoesNotExist:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ServiceConversionView(APIView):
    """Convert other services (events, tasks, etc.) to announcements"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Convert a service object to announcement
        Expected data:
        - source_type: 'event', 'task', 'resource', etc.
        - source_id: UUID of source object
        - announcement_data: announcement fields (heading, content, etc.)
        - retain_source: whether to keep original (default True)
        """
        source_type = request.data.get('source_type')
        source_id = request.data.get('source_id')
        announcement_data = request.data.get('announcement_data', {})
        retain_source = request.data.get('retain_source', True)
        
        if not source_type or not source_id:
            return Response(
                {'error': 'source_type and source_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the appropriate content type
        try:
            # Map source types to app.model format
            model_mapping = {
                'event': 'Events.Event',
                'task': 'Announcements.Task',
                'resource': 'Resources.Resource',
                'post': 'Announcements.Text',
            }
            
            app_label, model_name = model_mapping.get(source_type, f'Unknown.{source_type}').split('.')
            content_type = ContentType.objects.get(app_label=app_label.lower(), model=model_name.lower())
            
            # Get source object for metadata
            source_object = content_type.get_object_for_this_type(id=source_id)
            source_title = getattr(source_object, 'title', getattr(source_object, 'heading', str(source_object)))
            
            # Store original content
            original_content = {
                'title': source_title,
                'type': source_type,
                'id': str(source_id)
            }
            
        except ContentType.DoesNotExist:
            return Response(
                {'error': f'Unknown source type: {source_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Source object not found: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create announcement
        announcement_data['user'] = request.user.id if isinstance(request.user.id, int) else request.user
        announcement_data.setdefault('status', 'sent')
        announcement_data.setdefault('visibility', 'public')
        
        serializer = AnnouncementsSerializer(data=announcement_data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        announcement = serializer.save()
        
        # Create conversion record
        conversion = ServiceAnnouncementConversion.objects.create(
            content_type=content_type,
            object_id=source_id,
            source_type=source_type,
            source_title=source_title,
            announcement=announcement,
            converted_by=request.user,
            retain_source=retain_source,
            original_content=original_content
        )
        
        # Optionally archive/delete source
        if not retain_source:
            try:
                source_object.is_active = False
                source_object.save()
            except AttributeError:
                pass  # Source doesn't support soft delete
        
        return Response({
            'message': 'Service converted to announcement successfully',
            'announcement': serializer.data,
            'conversion': {
                'id': str(conversion.id),
                'source_type': source_type,
                'source_title': source_title,
                'retain_source': retain_source
            }
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get conversion history for current user"""
        conversions = ServiceAnnouncementConversion.objects.filter(
            converted_by=request.user
        ).select_related('announcement').order_by('-converted_at')[:20]
        
        history = [{
            'id': str(c.id),
            'source_type': c.source_type,
            'source_title': c.source_title,
            'announcement_id': str(c.announcement.id),
            'announcement_heading': c.announcement.heading,
            'converted_at': c.converted_at.isoformat(),
            'retain_source': c.retain_source
        } for c in conversions]
        
        return Response({
            'conversions': history,
            'count': len(history)
        })


class OfflineNotificationViewSet(ModelViewSet):
    """Manage offline notification queue"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return OfflineAnnouncementNotification.objects.filter(
            user=self.request.user,
            queued=True
        ).order_by('scheduled_for')
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending notifications for current user"""
        notifications = self.get_queryset()[:50]
        
        data = [{
            'id': str(n.id),
            'announcement_id': str(n.announcement.id),
            'announcement_heading': n.announcement.heading,
            'notification_type': n.notification_type,
            'scheduled_for': n.scheduled_for.isoformat(),
            'retry_count': n.retry_count
        } for n in notifications]
        
        return Response({
            'notifications': data,
            'count': len(data)
        })
    
    @action(detail=True, methods=['post'])
    def mark_sent(self, request, pk=None):
        """Mark notification as sent"""
        notification = self.get_object()
        
        notification.sent = True
        notification.queued = False
        notification.sent_at = timezone.now()
        notification.save()
        
        return Response({
            'message': 'Notification marked as sent'
        })
