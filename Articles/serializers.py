from rest_framework import serializers
from .models import Article, ArticleAttachment, Comment, ArticleLike, ArticleBookmark
from Authentication.serializers import CustomUserSerializer as UserSerializer

class ArticleAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleAttachment
        fields = ['id', 'file', 'uploaded_at']

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ['id', 'article', 'user', 'content', 'created_at', 'updated_at', 'parent', 'replies']
        read_only_fields = ['user', 'article']

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []

class ArticleSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField() # Custom user logic if needed, or just nested
    attachments = ArticleAttachmentSerializer(many=True, read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt', 
            'author', 'category', 'tags', 'status', 'cover_image',
            'created_at', 'published_at', 'views_count',
            'attachments', 'is_liked', 'is_bookmarked',
            'likes_count', 'comments_count'
        ]
        read_only_fields = ['author', 'slug', 'views_count', 'created_at', 'published_at']

    def get_author(self, obj):
        # Simplified author info
        return {
            "id": obj.author.id,
            "name": f"{obj.author.first_name} {obj.author.last_name}" if obj.author.first_name else obj.author.email,
            "email": obj.author.email
            # Add avatar if available in your User model
        }

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ArticleLike.objects.filter(article=obj, user=request.user).exists()
        return False

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ArticleBookmark.objects.filter(article=obj, user=request.user).exists()
        return False

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['author'] = user
        return super().create(validated_data)
