"""
Notification Serializers
"""
from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    actor_name = serializers.SerializerMethodField()
    actor_avatar = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'content_type', 'content_id', 'action_url',
            'is_read', 'read_at', 'created_at',
            'actor_name', 'actor_avatar', 'time_ago', 'extra_data'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_actor_name(self, obj):
        if obj.actor:
            return f"{obj.actor.first_name} {obj.actor.last_name}".strip() or obj.actor.email
        return None
    
    def get_actor_avatar(self, obj):
        if obj.actor:
            try:
                profile = obj.actor.user_profile
                if profile.avatar:
                    request = self.context.get('request')
                    if request:
                        return request.build_absolute_uri(profile.avatar.url)
                    return profile.avatar.url
            except Exception:
                pass
        return None
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "just now"
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f"{mins}m ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff < timedelta(days=7):
            days = int(diff.total_seconds() / 86400)
            return f"{days}d ago"
        else:
            return obj.created_at.strftime("%b %d")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    class Meta:
        model = NotificationPreference
        exclude = ['user', 'created_at', 'updated_at']
