from django.contrib import admin
from .models import QNote, QNoteLike, QNoteComment, QNoteCommentLike, QNoteRepost, QNoteSave


@admin.register(QNote)
class QNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'content_preview', 'author', 'like_count', 'repost_count',
                    'comment_count', 'save_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['content']
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
    content_preview.short_description = 'Content'


@admin.register(QNoteLike)
class QNoteLikeAdmin(admin.ModelAdmin):
    list_display = ['note', 'user', 'created_at']
    list_filter = ['created_at']


@admin.register(QNoteComment)
class QNoteCommentAdmin(admin.ModelAdmin):
    list_display = ['note', 'author', 'content_preview', 'created_at']
    list_filter = ['created_at']

    def content_preview(self, obj):
        return obj.content[:60] + '...' if len(obj.content) > 60 else obj.content
    content_preview.short_description = 'Content'


@admin.register(QNoteRepost)
class QNoteRepostAdmin(admin.ModelAdmin):
    list_display = ['note', 'user', 'created_at']


@admin.register(QNoteSave)
class QNoteSaveAdmin(admin.ModelAdmin):
    list_display = ['note', 'user', 'created_at']


@admin.register(QNoteCommentLike)
class QNoteCommentLikeAdmin(admin.ModelAdmin):
    list_display = ['comment', 'user', 'created_at']
    list_filter = ['created_at']
