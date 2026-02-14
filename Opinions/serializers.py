from rest_framework import serializers
from .models import Opinion, OpinionLike, OpinionComment, OpinionRepost, Follow, Bookmark, OpinionMedia, Story, StoryView
from Authentication.models import CustomUser


class UserMiniSerializer(serializers.ModelSerializer):
    """Minimal user info for opinions"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar_url', 'user_type', 'is_following']
    
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
    
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False


class OpinionMediaSerializer(serializers.ModelSerializer):
    """Serializer for opinion media attachments"""
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = OpinionMedia
        fields = ['id', 'url', 'media_type', 'caption', 'file_name', 'order']
    
    def get_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class OpinionSerializer(serializers.ModelSerializer):
    """Full opinion serializer with engagement data"""
    user = UserMiniSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    is_reposted = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    quoted_opinion = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    media_files = OpinionMediaSerializer(many=True, read_only=True)
    reposted_by_user = serializers.SerializerMethodField()
    original_content = serializers.SerializerMethodField()
    entity_author = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Opinion
        fields = [
            'id', 'user', 'content', 'visibility', 'media_url', 'media_type',
            'likes_count', 'comments_count', 'reposts_count', 'shares_count', 'views_count',
            'is_liked', 'is_reposted', 'is_bookmarked',
            'quoted_opinion', 'is_pinned', 'is_repost', 'reposted_by_user', 'original_content',
            'media_files', 'created_at', 'time_ago', 'entity_author', 'is_anonymous', 'room', 'user_type'
        ]
        read_only_fields = ['id', 'user', 'likes_count', 'comments_count', 'reposts_count', 'created_at']
    
    def get_user_type(self, obj):
        """Get the user type label for display (e.g., Student, Staff, Admin)"""
        if obj.is_anonymous:
            return None
        if obj.user:
            return obj.user.user_type
        return None
    
    def to_representation(self, instance):
        """Override to mask user info for anonymous opinions"""
        data = super().to_representation(instance)
        
        # Mask user info if anonymous
        if instance.is_anonymous:
            data['user'] = {
                'id': None,
                'email': None,
                'first_name': 'Anonymous',
                'last_name': '',
                'full_name': 'Anonymous',
                'avatar_url': None,
                'user_type': None,
                'is_following': False,
            }
            data['user_type'] = None
        
        return data
    
    def get_entity_author(self, obj):
        """Return entity author info if opinion was posted by an org or institution"""
        if obj.organisation:
            return {
                'id': obj.organisation.id,
                'name': obj.organisation.name,
                'type': 'organisation',
                'avatar': obj.organisation.logo.url if obj.organisation.logo else None,
            }
        if obj.institution:
            return {
                'id': obj.institution.id,
                'name': obj.institution.name,
                'type': 'institution',
                'avatar': obj.institution.logo.url if obj.institution.logo else None,
            }
        return None
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return OpinionLike.objects.filter(user=request.user, opinion=obj).exists()
        return False
    
    def get_is_reposted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return OpinionRepost.objects.filter(user=request.user, opinion=obj).exists()
        return False
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, opinion=obj).exists()
        return False
    
    def get_reposted_by_user(self, obj):
        if obj.is_repost and obj.reposted_by:
            return {
                'id': obj.reposted_by.id,
                'name': f'{obj.reposted_by.first_name} {obj.reposted_by.last_name}'.strip(),
            }
        return None
    
    def get_original_content(self, obj):
        if obj.is_repost and obj.original_opinion:
            return {
                'id': obj.original_opinion.id,
                'user': UserMiniSerializer(obj.original_opinion.user, context=self.context).data
            }
        return None
    
    def get_quoted_opinion(self, obj):
        if obj.quoted_opinion:
            return {
                'id': obj.quoted_opinion.id,
                'content': obj.quoted_opinion.content[:100],
                'user': {
                    'first_name': obj.quoted_opinion.user.first_name,
                    'last_name': obj.quoted_opinion.user.last_name,
                }
            }
        return None
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'just now'
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f'{mins}m'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days}d'
        else:
            return obj.created_at.strftime('%b %d')


class OpinionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating opinions"""
    class Meta:
        model = Opinion
        fields = ['content', 'visibility', 'media_url', 'media_type', 'quoted_opinion', 'is_anonymous', 'room']
    
    def validate_content(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Opinion content cannot be empty")
        return value


class OpinionCommentSerializer(serializers.ModelSerializer):
    """Comment serializer with user info"""
    user = UserMiniSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = OpinionComment
        fields = [
            'id', 'user', 'opinion', 'parent_comment', 'content',
            'likes_count', 'is_liked', 'replies', 'created_at', 'time_ago'
        ]
        read_only_fields = ['id', 'user', 'likes_count', 'created_at']
    
    def get_replies(self, obj):
        # Only get top-level replies to avoid deep recursion
        if obj.parent_comment is None:
            replies = obj.replies.all()[:5]
            return OpinionCommentSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_is_liked(self, obj):
        request = self.context.get('request')
        # Comment likes not implemented yet - placeholder
        return False
    
    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'just now'
        elif diff < timedelta(hours=1):
            mins = int(diff.total_seconds() / 60)
            return f'{mins}m'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h'
        else:
            return obj.created_at.strftime('%b %d')


class FollowSerializer(serializers.ModelSerializer):
    """Follow relationship serializer"""
    follower = UserMiniSerializer(read_only=True)
    following = UserMiniSerializer(read_only=True)
    
    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']
        read_only_fields = ['id', 'follower', 'created_at']


class UserFollowSerializer(serializers.ModelSerializer):
    """User serializer for followers/following lists"""
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'avatar_url', 'user_type', 'is_following',
            'followers_count', 'following_count', 'bio'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.email
    
    def get_avatar_url(self, obj):
        try:
            profile = getattr(obj, 'user_profile', None) or getattr(obj, 'profile', None)
            if profile and profile.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.avatar.url)
                return profile.avatar.url
        except:
            pass
        return None
    
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user != obj:
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False
    
    def get_followers_count(self, obj):
        return obj.followers.count()
    
    def get_following_count(self, obj):
        return obj.following.count()
    
    def get_bio(self, obj):
        try:
            profile = getattr(obj, 'user_profile', None) or getattr(obj, 'profile', None)
            if profile:
                return profile.bio
        except:
            pass
        return ""


class BookmarkSerializer(serializers.ModelSerializer):
    """Bookmark serializer"""
    opinion = OpinionSerializer(read_only=True)
    
    class Meta:
        model = Bookmark
        fields = ['id', 'opinion', 'created_at']
        read_only_fields = ['id', 'created_at']


class StorySerializer(serializers.ModelSerializer):
    """Serializer for viewing stories"""
    user = UserMiniSerializer(read_only=True)
    media_url = serializers.SerializerMethodField()
    has_viewed = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Story
        fields = [
            'id', 'user', 'media_url', 'media_type', 'caption',
            'background_color', 'views_count', 'has_viewed',
            'is_active', 'created_at', 'expires_at', 'time_ago'
        ]
        read_only_fields = ['id', 'user', 'views_count', 'created_at', 'expires_at']

    def get_media_url(self, obj):
        if obj.media:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.media.url)
            return obj.media.url
        return None

    def get_has_viewed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return StoryView.objects.filter(story=obj, viewer=request.user).exists()
        return False

    def get_time_ago(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        diff = now - obj.created_at
        if diff < timedelta(minutes=1):
            return 'just now'
        elif diff < timedelta(hours=1):
            return f'{int(diff.total_seconds() / 60)}m'
        elif diff < timedelta(days=1):
            return f'{int(diff.total_seconds() / 3600)}h'
        return obj.created_at.strftime('%b %d')


class StoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating stories"""
    class Meta:
        model = Story
        fields = ['media', 'media_type', 'caption', 'background_color']

