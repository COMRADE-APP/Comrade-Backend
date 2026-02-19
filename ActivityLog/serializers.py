from rest_framework import serializers
from ActivityLog.models import (
    UserActivity, ActionLog, ActivitySession,
    PermissionConsent, DevicePermissionLog,
    ConnectionSecurityLog, SearchActivityLog
)


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = '__all__'
        read_only_fields = ['timestamp']


class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = '__all__'
        read_only_fields = ['timestamp']


class ActivitySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivitySession
        fields = '__all__'


class PermissionConsentSerializer(serializers.ModelSerializer):
    permission_type_display = serializers.CharField(
        source='get_permission_type_display', read_only=True
    )
    
    class Meta:
        model = PermissionConsent
        fields = '__all__'
        read_only_fields = ['id', 'user', 'granted_at', 'revoked_at', 'updated_at']


class DevicePermissionLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(
        source='get_action_display', read_only=True
    )
    
    class Meta:
        model = DevicePermissionLog
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']


class ConnectionSecurityLogSerializer(serializers.ModelSerializer):
    security_level_display = serializers.CharField(
        source='get_security_level_display', read_only=True
    )
    
    class Meta:
        model = ConnectionSecurityLog
        fields = '__all__'
        read_only_fields = ['id', 'checked_at']


class SearchActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchActivityLog
        fields = '__all__'
        read_only_fields = ['id', 'searched_at']


class ActivityExportSerializer(serializers.Serializer):
    """Serializer for activity export request"""
    format = serializers.ChoiceField(choices=['csv', 'json'], default='json')
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    activity_types = serializers.ListField(
        child=serializers.CharField(), required=False
    )
