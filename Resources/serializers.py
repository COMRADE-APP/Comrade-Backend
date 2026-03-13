from rest_framework import serializers
from Resources.models import (
    Resource, ResourceVisibility, VisibilityLog, Link, MainVisibilityLog, Visibility,
    ResourceAccessRequest, ResourceAnalytics, ResourceComment, ResourceReview
)



class ResourceSerializer(serializers.ModelSerializer):
    # Read-only nested fields for display
    linked_opinion_details = serializers.SerializerMethodField()
    linked_article_details = serializers.SerializerMethodField()
    linked_research_details = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    # Accept frontend field names and map to model fields
    name = serializers.CharField(write_only=True, required=False, source='title')
    description = serializers.CharField(write_only=True, required=False, source='desc')
    resource_type = serializers.CharField(write_only=True, required=False, source='file_type')
    external_link = serializers.URLField(write_only=True, required=False, source='res_link')

    class Meta:
        fields = '__all__'
        model = Resource
        read_only_fields = ['created_by', 'created_on']
        extra_kwargs = {
            'title': {'required': False},
            'desc': {'required': False},
            'file_type': {'required': False},
            'res_link': {'required': False},
        }

    def get_file_size(self, obj):
        if obj.res_file:
            try:
                return obj.res_file.size
            except:
                pass
        return None

    def get_file(self, obj):
        """Return absolute URL for the resource file"""
        if obj.res_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.res_file.url)
            return obj.res_file.url
        return obj.res_link or None

    def get_cover_image_url(self, obj):
        if obj.cover_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        return obj.image_url or None

    def get_created_by_name(self, obj):
        if obj.created_by:
            user = obj.created_by.user
            return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        return None

    def get_linked_opinion_details(self, obj):
        from Opinions.serializers import OpinionSerializer
        if obj.linked_opinion:
            return OpinionSerializer(obj.linked_opinion).data
        return None

    def get_linked_article_details(self, obj):
        from Articles.serializers import ArticleSerializer
        if obj.linked_article:
            return ArticleSerializer(obj.linked_article).data
        return None

    def get_linked_research_details(self, obj):
        from Research.serializers import ResearchProjectSerializer
        if obj.linked_research:
            return ResearchProjectSerializer(obj.linked_research).data
        return None

class ResourceVisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ResourceVisibility


class VisibilityLogSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = VisibilityLog

class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Link

class VisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Visibility


class MainVisibilityLogSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = MainVisibilityLog


class ResourceAccessRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()

    class Meta:
        model = ResourceAccessRequest
        fields = ['id', 'resource', 'requester', 'requester_name', 'status', 'message',
                  'reviewed_by', 'review_note', 'requested_at', 'reviewed_at', 'expires_at']
        read_only_fields = ['id', 'requester', 'requested_at', 'reviewed_at', 'reviewed_by']

    def get_requester_name(self, obj):
        try:
            user = obj.requester.user
            return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        except:
            return str(obj.requester)


class ResourceAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceAnalytics
        fields = ['id', 'resource', 'user', 'action', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']


class ResourceCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_disliked = serializers.SerializerMethodField()

    class Meta:
        model = ResourceComment
        fields = [
            'id', 'resource', 'user', 'user_name', 'user_avatar', 'content',
            'parent', 'likes_count', 'dislikes_count', 'is_liked', 'is_disliked',
            'is_edited', 'replies', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        try:
            user = obj.user.user
            return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        except:
            return str(obj.user)

    def get_user_avatar(self, obj):
        try:
            if obj.user.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user.avatar.url)
                return obj.user.avatar.url
        except:
            pass
        return None

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_dislikes_count(self, obj):
        return obj.dislikes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from Authentication.models import Profile
            profile = Profile.objects.filter(user=request.user).first()
            return obj.likes.filter(id=profile.id).exists() if profile else False
        return False

    def get_is_disliked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from Authentication.models import Profile
            profile = Profile.objects.filter(user=request.user).first()
            return obj.dislikes.filter(id=profile.id).exists() if profile else False
        return False

    def get_replies(self, obj):
        if obj.parent is None:  # Only get replies for top-level comments
            replies = obj.replies.all()
            return ResourceCommentSerializer(replies, many=True, context=self.context).data
        return []


class ResourceReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = ResourceReview
        fields = ['id', 'resource', 'user', 'user_name', 'user_avatar', 'rating', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        try:
            user = obj.user.user
            return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
        except:
            return str(obj.user)

    def get_user_avatar(self, obj):
        try:
            if obj.user.avatar:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user.avatar.url)
                return obj.user.avatar.url
        except:
            pass
        return None
