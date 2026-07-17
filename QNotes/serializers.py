from rest_framework import serializers
from .models import QNote, QNoteComment, default_note_color


class QNoteCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = QNoteComment
        fields = ['id', 'content', 'author_name', 'parent', 'created_at',
                  'like_count', 'is_liked', 'replies']
        read_only_fields = ['author_name', 'created_at', 'like_count', 'is_liked', 'replies']

    def get_author_name(self, obj):
        return 'Anonymous'

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_replies(self, obj):
        replies = QNoteComment.objects.filter(parent=obj).order_by('created_at')
        return QNoteCommentSerializer(replies, many=True, context=self.context).data


class QNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    is_reposted = serializers.SerializerMethodField()
    comment_list = serializers.SerializerMethodField()

    class Meta:
        model = QNote
        fields = [
            'id', 'author_name', 'content', 'color', 'created_at',
            'like_count', 'repost_count', 'comment_count', 'save_count',
            'is_liked', 'is_saved', 'is_reposted', 'comment_list',
        ]
        read_only_fields = [
            'author_name', 'created_at',
            'like_count', 'repost_count', 'comment_count', 'save_count',
            'is_liked', 'is_saved', 'is_reposted', 'comment_list',
        ]

    def get_author_name(self, obj):
        return 'Anonymous'

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.saves.filter(user=request.user).exists()
        return False

    def get_is_reposted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.reposts.filter(user=request.user).exists()
        return False

    def get_comment_list(self, obj):
        comments = QNoteComment.objects.filter(note=obj, parent=None).order_by('created_at')
        return QNoteCommentSerializer(comments, many=True, context=self.context).data


class QNoteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QNote
        fields = ['content', 'color']

    def create(self, validated_data):
        request = self.context.get('request')
        note = QNote.objects.create(
            author=request.user if request and request.user.is_authenticated else None,
            content=validated_data['content'],
            color=validated_data.get('color', default_note_color()),
        )
        return note
