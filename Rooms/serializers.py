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
    class Meta:
        model = DirectMessage
        fields = ['receiver', 'content', 'file', 'dm_room', 'message_type']
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        validated_data['status'] = 'sent'
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