from rest_framework import serializers
from ActivityLog.models import UserActivity, ActionLog


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']


class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = '__all__'
        read_only_fields = ['user', 'timestamp']
