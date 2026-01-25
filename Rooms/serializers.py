from rest_framework import serializers
from Rooms.models import Room, DefaultRoom, DirectMessage, DirectMessageRoom, ForwadingLog
from Authentication.models import CustomUser


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for chat listings"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class RoomSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Room
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_on', 'invitation_code', 'room_code']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None
    
    def get_member_count(self, obj):
        return obj.members.count()


class RoomListSerializer(serializers.ModelSerializer):
    """Simplified room serializer for listing"""
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    
    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'operation_state', 'member_count', 
                  'is_member', 'created_on', 'invitation_code']
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.members.filter(id=request.user.id).exists()
        return False


class RoomRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for room recommendations"""
    member_count = serializers.SerializerMethodField()
    match_reason = serializers.SerializerMethodField()
    
    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'operation_state', 'member_count', 
                  'match_reason', 'created_on']
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_match_reason(self, obj):
        # This will be set in the view based on why it's recommended
        return getattr(obj, 'match_reason', 'Popular in your institution')


class DefaultRoomSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DefaultRoom
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_on', 'invitation_code', 'room_code']
    
    def get_member_count(self, obj):
        return obj.members.count()


class DirectMessageSerializer(serializers.ModelSerializer):
    sender_info = UserMinimalSerializer(source='sender', read_only=True)
    receiver_info = UserMinimalSerializer(source='receiver', read_only=True)
    
    class Meta:
        model = DirectMessage
        fields = ['id', 'sender', 'sender_info', 'receiver', 'receiver_info', 
                  'content', 'file', 'dm_room', 'status', 'message_type', 
                  'message_origin', 'time_stamp', 'is_read', 'delivered_on', 'read_on']
        read_only_fields = ['id', 'sender', 'time_stamp', 'delivered_on', 'read_on']


class DirectMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating direct messages"""
    receiver = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), 
        required=False, 
        allow_null=True
    )
    
    class Meta:
        model = DirectMessage
        fields = ['receiver', 'content', 'file', 'dm_room', 'message_type']
    
    def create(self, validated_data):
        request = self.context['request']
        validated_data['sender'] = request.user
        validated_data['status'] = 'sent'
        
        # If receiver not provided, infer from dm_room participants
        if not validated_data.get('receiver') and validated_data.get('dm_room'):
            dm_room = validated_data['dm_room']
            other_participant = dm_room.participants.exclude(id=request.user.id).first()
            if other_participant:
                validated_data['receiver'] = other_participant
            else:
                raise serializers.ValidationError({'receiver': 'Could not determine receiver from DM room'})
        
        return super().create(validated_data)


class DirectMessageRoomSerializer(serializers.ModelSerializer):
    participants_info = UserMinimalSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectMessageRoom
        fields = ['id', 'participants', 'participants_info', 'created_on', 
                  'last_message', 'unread_count', 'other_participant']
        read_only_fields = ['id', 'created_on']
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-time_stamp').first()
        if last_msg:
            return {
                'content': last_msg.content[:50] + '...' if len(last_msg.content) > 50 else last_msg.content,
                'time_stamp': last_msg.time_stamp,
                'sender_id': last_msg.sender_id,
                'is_read': last_msg.is_read
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(
                receiver=request.user,
                is_read=False
            ).count()
        return 0
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            other = obj.participants.exclude(id=request.user.id).first()
            if other:
                return UserMinimalSerializer(other).data
        return None


class DirectMessageRoomListSerializer(serializers.ModelSerializer):
    """Simplified serializer for DM room listings (conversations)"""
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DirectMessageRoom
        fields = ['id', 'other_participant', 'last_message', 'unread_count', 'created_on']
    
    def get_other_participant(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            other = obj.participants.exclude(id=request.user.id).first()
            if other:
                return {
                    'id': other.id,
                    'name': f"{other.first_name} {other.last_name}",
                    'email': other.email
                }
        return None
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-time_stamp').first()
        if last_msg:
            return {
                'content': last_msg.content[:50] + '...' if len(last_msg.content) > 50 else last_msg.content,
                'time_stamp': last_msg.time_stamp
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(receiver=request.user, is_read=False).count()
        return 0


class ForwadingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForwadingLog
        fields = '__all__'
        read_only_fields = ['id', 'user', 'forwarded_on']

# Import new models
from Rooms.models import RoomSettings, RoomChat, RoomChatFile


class RoomChatFileSerializer(serializers.ModelSerializer):
    """Serializer for chat file attachments"""
    class Meta:
        model = RoomChatFile
        fields = ['id', 'file', 'file_name', 'file_type', 'file_size', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class RoomChatSerializer(serializers.ModelSerializer):
    """Serializer for room chat messages with WhatsApp-like features"""
    sender_info = UserMinimalSerializer(source='sender', read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    files = RoomChatFileSerializer(many=True, read_only=True)
    is_own = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()
    delivered_count = serializers.SerializerMethodField()
    forwarded_from_room_name = serializers.SerializerMethodField()
    reply_to_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = RoomChat
        fields = [
            'id', 'room', 'sender', 'sender_info', 'sender_avatar', 'content',
            'message_type', 'status', 'files', 'event', 'task', 'resource', 'announcement',
            'is_forwarded', 'forwarded_from_room', 'forwarded_from_room_name',
            'forwarded_from_user', 'reply_to', 'reply_to_preview',
            'is_own', 'read_count', 'delivered_count', 'created_at', 'updated_at',
            'is_deleted'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']
    
    def get_sender_avatar(self, obj):
        """Get sender's avatar URL"""
        if hasattr(obj.sender, 'user_profile') and obj.sender.user_profile and obj.sender.user_profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.sender.user_profile.avatar.url)
            return obj.sender.user_profile.avatar.url
        return None
    
    def get_is_own(self, obj):
        """Check if message is from current user (for alignment/styling)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False
    
    def get_read_count(self, obj):
        """Count of users who have read this message"""
        return obj.read_by.count()
    
    def get_delivered_count(self, obj):
        """Count of users who received this message"""
        return obj.delivered_to.count()
    
    def get_forwarded_from_room_name(self, obj):
        """Get the name of room message was forwarded from (for display)"""
        if obj.is_forwarded and obj.forwarded_from_room:
            return obj.forwarded_from_room.name
        return None
    
    def get_reply_to_preview(self, obj):
        """Get preview of the message being replied to"""
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content[:100] if obj.reply_to.content else '',
                'sender_name': f"{obj.reply_to.sender.first_name} {obj.reply_to.sender.last_name}"
            }
        return None


class RoomChatCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating room chat messages"""
    class Meta:
        model = RoomChat
        fields = ['content', 'message_type', 'event', 'task', 'resource', 'announcement', 
                  'reply_to', 'is_forwarded', 'forwarded_from_room', 'original_chat']
    
    def validate(self, data):
        # Ensure at least content or a reference is provided
        if not data.get('content') and not any([
            data.get('event'), data.get('task'), 
            data.get('resource'), data.get('announcement')
        ]):
            # Will be valid if files are attached (handled in view)
            pass
        return data


class RoomSettingsSerializer(serializers.ModelSerializer):
    """Serializer for room settings (WhatsApp-like)"""
    class Meta:
        model = RoomSettings
        fields = [
            'chat_enabled', 'chat_permission', 
            'who_can_add_members', 'who_can_edit_info', 'who_can_send_media',
            'allow_opinion_tagging', 'allow_message_forwarding', 'show_forward_source',
            'is_discoverable', 'require_approval_to_join',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class RoomDetailSerializer(RoomSerializer):
    """Extended room serializer with settings and content counts"""
    settings = RoomSettingsSerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()
    is_moderator = serializers.SerializerMethodField()
    can_chat = serializers.SerializerMethodField()
    resources_count = serializers.SerializerMethodField()
    events_count = serializers.SerializerMethodField()
    tasks_count = serializers.SerializerMethodField()
    announcements_count = serializers.SerializerMethodField()
    chats_count = serializers.SerializerMethodField()
    
    class Meta(RoomSerializer.Meta):
        fields = '__all__'
    
    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None
    
    def get_cover_url(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return None
    
    def get_is_admin(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.admins.filter(id=request.user.id).exists()
        return False
    
    def get_is_moderator(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.moderators.filter(id=request.user.id).exists()
        return False
    
    def get_can_chat(self, obj):
        """Check if current user can send messages based on room settings"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        settings = getattr(obj, 'settings', None)
        if not settings or not settings.chat_enabled:
            return False
        
        permission = settings.chat_permission
        if permission == 'all_members':
            return obj.members.filter(id=request.user.id).exists()
        elif permission == 'admins_moderators':
            return (obj.admins.filter(id=request.user.id).exists() or 
                    obj.moderators.filter(id=request.user.id).exists())
        elif permission == 'admins_only':
            return obj.admins.filter(id=request.user.id).exists()
        return False
    
    def get_resources_count(self, obj):
        return obj.resources.count()
    
    def get_events_count(self, obj):
        return obj.events.count()
    
    def get_tasks_count(self, obj):
        return obj.tasks.count()
    
    def get_announcements_count(self, obj):
        return obj.announcements.count()
    
    def get_chats_count(self, obj):
        return obj.chats.filter(is_deleted=False).count()


class MemberDetailSerializer(serializers.ModelSerializer):
    """Detailed member info for room member list with follow status"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name',
                  'avatar_url', 'role', 'is_following', 'user_type']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    
    def get_avatar_url(self, obj):
        if hasattr(obj, 'user_profile') and obj.user_profile and obj.user_profile.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.user_profile.avatar.url)
            return obj.user_profile.avatar.url
        return None
    
    def get_role(self, obj):
        # Role is set by the view based on room context
        return getattr(obj, '_room_role', 'member')
    
    def get_is_following(self, obj):
        # is_following is set by the view
        return getattr(obj, '_is_following', False)
