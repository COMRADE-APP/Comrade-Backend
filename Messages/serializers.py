from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Conversation, ConversationParticipant, Message, MessageRead, UserMessagingSettings
from Authentication.models import CustomUser


class UserMiniSerializer(serializers.ModelSerializer):
    """Minimal user info for messages"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'full_name', 'avatar_url', 'is_online']
    
    def get_full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.email
    
    def get_avatar_url(self, obj):
        try:
            if hasattr(obj, 'user_profile') and obj.user_profile.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user_profile.avatar.url)
                return obj.user_profile.avatar.url
        except:
            pass
        return None
    
    def get_is_online(self, obj):
        # Check if user was active in the last 5 minutes
        if hasattr(obj, 'last_activity'):
            return obj.last_activity > timezone.now() - timedelta(minutes=5)
        return False


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for individual messages"""
    sender = UserMiniSerializer(read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    reply_to_preview = serializers.SerializerMethodField()
    media_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content',
            'media_url', 'reply_to', 'reply_to_preview', 'reactions',
            'is_edited', 'is_deleted', 'is_mine', 'created_at', 'time_ago'
        ]
        read_only_fields = ['id', 'sender', 'created_at']
    
    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'now'
        elif diff < timedelta(hours=1):
            return f'{int(diff.total_seconds() / 60)}m'
        elif diff < timedelta(days=1):
            return f'{int(diff.total_seconds() / 3600)}h'
        elif diff < timedelta(days=7):
            return f'{diff.days}d'
        else:
            return obj.created_at.strftime('%b %d')
    
    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False
    
    def get_reply_to_preview(self, obj):
        if obj.reply_to and not obj.reply_to.is_deleted:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content[:50],
                'sender_name': obj.reply_to.sender.first_name if obj.reply_to.sender else 'Unknown'
            }
        return None
    
    def get_media_url(self, obj):
        if obj.media:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.media.url)
            return obj.media.url
        return None


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations"""
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_request = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'name', 'other_user',
            'last_message', 'unread_count', 'is_request',
            'is_muted', 'is_pinned', 'created_at', 'updated_at'
        ]
    
    def get_other_user(self, obj):
        request = self.context.get('request')
        if request and obj.conversation_type == 'dm':
            other = obj.get_other_participant(request.user)
            if other:
                return UserMiniSerializer(other, context=self.context).data
        return None
    
    def get_last_message(self, obj):
        msg = obj.get_last_message()
        if msg:
            return {
                'id': msg.id,
                'content': msg.content[:50] if msg.content else f'[{msg.message_type}]',
                'sender_id': msg.sender_id,
                'created_at': msg.created_at,
                'is_deleted': msg.is_deleted
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request:
            try:
                participant = obj.participant_details.get(user=request.user)
                return participant.get_unread_count()
            except ConversationParticipant.DoesNotExist:
                pass
        return 0
    
    def get_is_request(self, obj):
        request = self.context.get('request')
        if request:
            try:
                participant = obj.participant_details.get(user=request.user)
                return participant.is_request and not participant.request_accepted
            except ConversationParticipant.DoesNotExist:
                pass
        return False
    
    def get_is_muted(self, obj):
        request = self.context.get('request')
        if request:
            try:
                participant = obj.participant_details.get(user=request.user)
                return participant.is_muted
            except ConversationParticipant.DoesNotExist:
                pass
        return False
    
    def get_is_pinned(self, obj):
        request = self.context.get('request')
        if request:
            try:
                participant = obj.participant_details.get(user=request.user)
                return participant.is_pinned
            except ConversationParticipant.DoesNotExist:
                pass
        return False


class ConversationDetailSerializer(ConversationSerializer):
    """Detailed serializer with messages"""
    messages = serializers.SerializerMethodField()
    participants = UserMiniSerializer(many=True, read_only=True)
    
    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages', 'participants']
    
    def get_messages(self, obj):
        messages = obj.messages.filter(is_deleted=False).order_by('-created_at')[:50]
        return MessageSerializer(messages, many=True, context=self.context).data


class UserMessagingSettingsSerializer(serializers.ModelSerializer):
    """Serializer for messaging settings"""
    class Meta:
        model = UserMessagingSettings
        fields = [
            'allow_messages_from', 'show_read_receipts',
            'show_online_status', 'auto_accept_circles', 'notification_sound'
        ]


class StartConversationSerializer(serializers.Serializer):
    """Serializer for starting a new conversation"""
    user_id = serializers.IntegerField()
    message = serializers.CharField(required=False, allow_blank=True)
    
    def validate_user_id(self, value):
        try:
            CustomUser.objects.get(id=value)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a message"""
    content = serializers.CharField(required=False, allow_blank=True)
    message_type = serializers.ChoiceField(
        choices=['text', 'image', 'video', 'audio', 'file'],
        default='text'
    )
    reply_to = serializers.IntegerField(required=False, allow_null=True)
