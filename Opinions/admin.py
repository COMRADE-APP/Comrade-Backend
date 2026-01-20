from django.contrib import admin
from .models import Opinion, OpinionLike, OpinionComment, OpinionRepost, Follow, Bookmark


@admin.register(Opinion)
class OpinionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'content_preview', 'visibility', 'likes_count', 'comments_count', 'created_at']
    list_filter = ['visibility', 'is_pinned', 'created_at']
    search_fields = ['content', 'user__email', 'user__first_name']
    readonly_fields = ['likes_count', 'comments_count', 'reposts_count', 'created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(OpinionLike)
class OpinionLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'opinion', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email']


@admin.register(OpinionComment)
class OpinionCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'opinion', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'user__email']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(OpinionRepost)
class OpinionRepostAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'opinion', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email']


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['id', 'follower', 'following', 'created_at']
    list_filter = ['created_at']
    search_fields = ['follower__email', 'following__email']


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'opinion', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email']
