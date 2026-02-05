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

    def validate_message(self, value):
        """
        Enforce word count limit:
        - Free users (default): 250 words
        - Staff/Premium: Higher limits (e.g. 1000+)
        """
        # Count words (simple split)
        word_count = len(value.split())
        
        # Get request from context
        request = self.context.get('request')
        user = request.user if request else None
        
        # Determine limit
        # TODO: Check for 'premium' group or subscription status
        if user and (user.is_staff or user.groups.filter(name='Premium').exists()):
            limit = 2000
        else:
            limit = 250
            
        if word_count > limit:
            raise serializers.ValidationError(
                f"Message too long ({word_count} words). Free tier limit is {limit} words."
            )
        return value

    def validate_history(self, value):
        """
        Ensure history is a list of dicts.
        Handle case where it might be a nested list due to parsing issues.
        """
        if isinstance(value, list):
            # If item 0 is a list, maybe the whole thing is wrapped?
            if len(value) > 0 and isinstance(value[0], list):
                # Flatten or unwrap?
                # If it's [[{...}, {...}]], return value[0]
                return value[0]
        return value


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat responses"""
    message = serializers.CharField()
    conversation_id = serializers.UUIDField()
    tokens_used = serializers.IntegerField(required=False)
    model = serializers.CharField(required=False)
