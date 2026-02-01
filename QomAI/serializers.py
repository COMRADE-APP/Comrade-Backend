"""
QomAI Serializers
"""
from rest_framework import serializers
from .models import Conversation, Message, UserPreference, ContentAnalysis


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'created_at', 'tokens_used', 'model_used']
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'is_active', 'messages', 'message_count']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationListSerializer(serializers.ModelSerializer):
    """Lighter serializer for listing conversations"""
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'message_count', 'last_message']

    def get_message_count(self, obj):
        return obj.messages.count()

    def get_last_message(self, obj):
        last = obj.messages.last()
        return last.content[:100] if last else None


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['preferred_model', 'context_length', 'temperature', 'updated_at']
        read_only_fields = ['updated_at']


class ContentAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentAnalysis
        fields = ['id', 'analysis_type', 'input_content', 'result', 'confidence_score', 'created_at']
        read_only_fields = ['id', 'result', 'confidence_score', 'created_at']


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat requests"""
    message = serializers.CharField(max_length=10000)
    history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat responses"""
    message = serializers.CharField()
    conversation_id = serializers.UUIDField()
    tokens_used = serializers.IntegerField(required=False)
    model = serializers.CharField(required=False)
