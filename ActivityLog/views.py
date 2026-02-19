from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.http import HttpResponse
import csv
import json

from ActivityLog.models import (
    UserActivity, ActionLog, ActivitySession,
    PermissionConsent, DevicePermissionLog,
    ConnectionSecurityLog, SearchActivityLog
)
from ActivityLog.serializers import (
    UserActivitySerializer, ActionLogSerializer, ActivitySessionSerializer,
    PermissionConsentSerializer, DevicePermissionLogSerializer,
    ConnectionSecurityLogSerializer, SearchActivityLogSerializer,
    ActivityExportSerializer
)
from ActivityLog.verification_utils import log_user_activity, check_connection_security, get_ip_geolocation


class UserActivityViewSet(ReadOnlyModelViewSet):
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = UserActivity.objects.filter(user=user)
        
        # Filter by activity type
        activity_type = self.request.query_params.get('type')
        if activity_type:
            queryset = queryset.filter(activity_type=activity_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get activity statistics for the current user"""
        user = request.user
        activities = UserActivity.objects.filter(user=user)
        
        total = activities.count()
        by_type = {}
        for activity_type, label in UserActivity.ACTIVITY_TYPES:
            count = activities.filter(activity_type=activity_type).count()
            if count > 0:
                by_type[activity_type] = {'label': label, 'count': count}
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timezone.timedelta(days=7)
        recent_count = activities.filter(timestamp__gte=week_ago).count()
        
        return Response({
            'total_activities': total,
            'by_type': by_type,
            'recent_week_count': recent_count,
        })
    
    @action(detail=False, methods=['post'])
    def log(self, request):
        """Log a new user activity from the frontend"""
        activity_type = request.data.get('activity_type', 'other')
        description = request.data.get('description', '')
        metadata = request.data.get('metadata', {})
        
        activity = log_user_activity(
            user=request.user,
            activity_type=activity_type,
            description=description,
            request=request,
            metadata=metadata
        )
        
        if activity:
            return Response(
                UserActivitySerializer(activity).data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'message': 'Activity not logged (consent not granted)'},
            status=status.HTTP_200_OK
        )


class ActionLogViewSet(ReadOnlyModelViewSet):
    serializer_class = ActionLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ActionLog.objects.filter(user=self.request.user)


class ActivitySessionViewSet(ReadOnlyModelViewSet):
    serializer_class = ActivitySessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ActivitySession.objects.filter(user=self.request.user)


class PermissionConsentViewSet(ModelViewSet):
    """Manage user consent for data collection"""
    serializer_class = PermissionConsentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PermissionConsent.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def update_consent(self, request):
        """
        Grant or revoke a specific permission consent.
        Expects: { "permission_type": "location", "is_granted": true/false }
        """
        permission_type = request.data.get('permission_type')
        is_granted = request.data.get('is_granted', False)
        
        if not permission_type:
            return Response(
                {'error': 'permission_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate permission type
        valid_types = [t[0] for t in PermissionConsent.PERMISSION_TYPES]
        if permission_type not in valid_types:
            return Response(
                {'error': f'Invalid permission_type. Valid types: {valid_types}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        consent, created = PermissionConsent.objects.get_or_create(
            user=request.user,
            permission_type=permission_type,
            defaults={'is_granted': is_granted}
        )
        
        if not created:
            consent.is_granted = is_granted
            if is_granted:
                consent.granted_at = timezone.now()
                consent.revoked_at = None
            else:
                consent.revoked_at = timezone.now()
            consent.save()
        elif is_granted:
            consent.granted_at = timezone.now()
            consent.save()
        
        # Log the permission change
        log_user_activity(
            user=request.user,
            activity_type='permission_change',
            description=f'{"Granted" if is_granted else "Revoked"} {permission_type} permission',
            request=request
        )
        
        return Response(PermissionConsentSerializer(consent).data)
    
    @action(detail=False, methods=['get'])
    def all_permissions(self, request):
        """Get all permission types with their current consent status"""
        user = request.user
        result = []
        
        for perm_type, perm_label in PermissionConsent.PERMISSION_TYPES:
            try:
                consent = PermissionConsent.objects.get(
                    user=user, permission_type=perm_type
                )
                result.append({
                    'permission_type': perm_type,
                    'label': perm_label,
                    'is_granted': consent.is_granted,
                    'granted_at': consent.granted_at,
                    'revoked_at': consent.revoked_at,
                })
            except PermissionConsent.DoesNotExist:
                result.append({
                    'permission_type': perm_type,
                    'label': perm_label,
                    'is_granted': False,
                    'granted_at': None,
                    'revoked_at': None,
                })
        
        return Response(result)


class ConnectionSecurityLogViewSet(ReadOnlyModelViewSet):
    """View connection security logs"""
    serializer_class = ConnectionSecurityLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ConnectionSecurityLog.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Check the current connection's security"""
        security_info = check_connection_security(request)
        geo_info = get_ip_geolocation(security_info['ip_address'])
        
        return Response({
            **security_info,
            'country': geo_info.get('country', 'Unknown'),
            'city': geo_info.get('city', 'Unknown'),
            'isp': geo_info.get('isp', 'Unknown'),
        })


class SearchActivityLogViewSet(ReadOnlyModelViewSet):
    """View search activity logs"""
    serializer_class = SearchActivityLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SearchActivityLog.objects.filter(user=self.request.user)


class ActivityExportView(APIView):
    """Export user activity data as CSV or JSON"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        export_format = request.query_params.get('format', 'json')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        user = request.user
        activities = UserActivity.objects.filter(user=user)
        
        if start_date:
            activities = activities.filter(timestamp__gte=start_date)
        if end_date:
            activities = activities.filter(timestamp__lte=end_date)
        
        # Log the download activity
        log_user_activity(
            user=user,
            activity_type='download',
            description=f'Exported activity log as {export_format.upper()}',
            request=request
        )
        
        if export_format == 'csv':
            return self._export_csv(activities)
        else:
            return self._export_json(activities)
    
    def _export_csv(self, activities):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="activity_log.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Activity Type', 'Description', 'Method', 'Endpoint', 'Status Code', 'IP Address', 'User Agent'])
        
        for activity in activities:
            writer.writerow([
                activity.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                activity.get_activity_type_display(),
                activity.description,
                activity.request_method or '',
                activity.endpoint or '',
                activity.status_code or '',
                activity.ip_address or '',
                activity.user_agent or '',
            ])
        
        return response
    
    def _export_json(self, activities):
        data = []
        for activity in activities:
            data.append({
                'timestamp': activity.timestamp.isoformat(),
                'activity_type': activity.activity_type,
                'activity_type_display': activity.get_activity_type_display(),
                'description': activity.description,
                'request_method': activity.request_method or '',
                'endpoint': activity.endpoint or '',
                'status_code': activity.status_code,
                'ip_address': activity.ip_address,
                'user_agent': activity.user_agent,
                'metadata': activity.metadata,
            })
        
        response = HttpResponse(
            json.dumps(data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="activity_log.json"'
        return response
