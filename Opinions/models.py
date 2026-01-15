from django.db import models
from django.utils import timezone
from Authentication.models import CustomUser


VISIBILITY_CHOICES = (
    ('public', 'Public'),
    ('followers', 'Followers Only'),
    ('only_me', 'Only Me'),
)


class Opinion(models.Model):
    """
    Opinion model - similar to tweets on X/Twitter.
    Users can post short opinions with visibility settings.
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='opinions'
    )
    content = models.CharField(max_length=500)
    visibility = models.CharField(
        max_length=20, 
        choices=VISIBILITY_CHOICES, 
        default='public'
    )
    media_url = models.URLField(blank=True, null=True)
    media_type = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        choices=[('image', 'Image'), ('video', 'Video'), ('gif', 'GIF')]
    )
    
    # Engagement counts (denormalized for performance)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    reposts_count = models.PositiveIntegerField(default=0)
    
    # For quote reposts
    quoted_opinion = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='quotes'
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
        ]
    
    def __str__(self):
        return f"{self.user.email}: {self.content[:50]}..."


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
    content = models.CharField(max_length=500)
    
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
