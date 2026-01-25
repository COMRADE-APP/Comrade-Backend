from django.db import models
from django.utils import timezone
from Authentication.models import CustomUser


VISIBILITY_CHOICES = (
    ('public', 'Public'),
    ('followers', 'Followers Only'),
    ('only_me', 'Only Me'),
)

MEDIA_TYPE_CHOICES = (
    ('image', 'Image'),
    ('video', 'Video'),
    ('gif', 'GIF'),
    ('file', 'File'),
)

REPORT_REASON_CHOICES = (
    ('spam', 'Spam'),
    ('harassment', 'Harassment'),
    ('hate_speech', 'Hate Speech'),
    ('violence', 'Violence'),
    ('misinformation', 'Misinformation'),
    ('inappropriate', 'Inappropriate Content'),
    ('other', 'Other'),
)


class Opinion(models.Model):
    """
    Opinion model - similar to tweets on X/Twitter.
    Users can post opinions with visibility settings and media.
    Character limit: 500 for free users, 5000 for premium.
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='opinions'
    )
    content = models.TextField(max_length=5000)  # Increased for premium users
    visibility = models.CharField(
        max_length=20, 
        choices=VISIBILITY_CHOICES, 
        default='public'
    )
    
    # Legacy single media field (keep for backward compatibility)
    media_url = models.URLField(blank=True, null=True)
    media_type = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=MEDIA_TYPE_CHOICES
    )
    
    # Engagement counts (denormalized for performance)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    reposts_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    
    # For quote reposts
    quoted_opinion = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='quotes'
    )
    
    # Repost tracking
    is_repost = models.BooleanField(default=False)
    original_opinion = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reposts'
    )
    reposted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reposted_opinions'
    )
    
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_repost']),
        ]
    
    def __str__(self):
        return f"{self.user.email}: {self.content[:50]}..."


class OpinionMedia(models.Model):
    """
    Media attachments for opinions (images, videos, files)
    Allows multiple media per opinion
    """
    opinion = models.ForeignKey(
        Opinion,
        on_delete=models.CASCADE,
        related_name='media_files'
    )
    file = models.FileField(upload_to='opinions/media/%Y/%m/')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    caption = models.CharField(max_length=500, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    
    # File metadata
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    mime_type = models.CharField(max_length=100, blank=True)
    
    # For videos
    duration = models.PositiveIntegerField(null=True, blank=True)  # in seconds
    thumbnail = models.ImageField(upload_to='opinions/thumbnails/', blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Media for opinion {self.opinion.id} - {self.media_type}"


class OpinionLike(models.Model):
    """Track likes on opinions"""
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='opinion_likes'
    )
    opinion = models.ForeignKey(
        Opinion, 
        on_delete=models.CASCADE, 
        related_name='likes'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'opinion')
        
    def __str__(self):
        return f"{self.user.email} liked opinion {self.opinion.id}"


class OpinionComment(models.Model):
    """Comments/replies on opinions (threaded)"""
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='opinion_comments'
    )
    opinion = models.ForeignKey(
        Opinion, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    parent_comment = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    content = models.TextField(max_length=1000)
    
    likes_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"{self.user.email} commented on opinion {self.opinion.id}"


class OpinionRepost(models.Model):
    """Track reposts (retweets)"""
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='opinion_reposts'
    )
    opinion = models.ForeignKey(
        Opinion, 
        on_delete=models.CASCADE, 
        related_name='reposts'
    )
    comment = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'opinion')
        
    def __str__(self):
        return f"{self.user.email} reposted opinion {self.opinion.id}"


class Follow(models.Model):
    """User following relationship"""
    follower = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='following'
    )
    following = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='followers'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('follower', 'following')
        
    def __str__(self):
        return f"{self.follower.email} follows {self.following.email}"


class Bookmark(models.Model):
    """Bookmarked opinions"""
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='bookmarks'
    )
    opinion = models.ForeignKey(
        Opinion, 
        on_delete=models.CASCADE, 
        related_name='bookmarks'
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'opinion')
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.user.email} bookmarked opinion {self.opinion.id}"


class ContentBlock(models.Model):
    """Block content from specific users"""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='blocked_users'
    )
    blocked_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='opinion_blocked_by'
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'blocked_user')
    
    def __str__(self):
        return f"{self.user.email} blocked {self.blocked_user.email}"


class ContentReport(models.Model):
    """Report content for review"""
    reporter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    opinion = models.ForeignKey(
        Opinion,
        on_delete=models.CASCADE,
        related_name='reports',
        null=True,
        blank=True
    )
    reported_user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reports_received',
        null=True,
        blank=True
    )
    reason = models.CharField(max_length=50, choices=REPORT_REASON_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('reviewed', 'Reviewed'),
            ('action_taken', 'Action Taken'),
            ('dismissed', 'Dismissed'),
        ],
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews_made'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report by {self.reporter.email} - {self.reason}"


class HiddenContent(models.Model):
    """Track content hidden by users (don't recommend)"""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='hidden_content'
    )
    opinion = models.ForeignKey(
        Opinion,
        on_delete=models.CASCADE,
        related_name='hidden_by',
        null=True,
        blank=True
    )
    reason = models.CharField(max_length=100, blank=True)  # "not interested", etc.
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'opinion')
    
    def __str__(self):
        return f"{self.user.email} hid opinion {self.opinion.id}"

