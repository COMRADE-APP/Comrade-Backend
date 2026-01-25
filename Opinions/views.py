from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.db import transaction

from .models import Opinion, OpinionLike, OpinionComment, OpinionRepost, Follow, Bookmark
from .serializers import (
    OpinionSerializer, OpinionCreateSerializer, OpinionCommentSerializer,
    FollowSerializer, UserFollowSerializer, BookmarkSerializer
)
from Authentication.models import CustomUser


class OpinionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners to edit their own objects"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class OpinionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for opinions - main feed functionality
    Anyone can view public opinions, anyone can create.
    """
    serializer_class = OpinionSerializer
    pagination_class = OpinionPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Opinion.objects.filter(is_deleted=False)
        
        # Filter by visibility
        if user.is_authenticated:
            # Show public, user's own, and from users they follow
            following_ids = user.following.values_list('following_id', flat=True)
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(user=user) |
                Q(visibility='followers', user_id__in=following_ids)
            )
        else:
            queryset = queryset.filter(visibility='public')
        
        # Filter by user if specified
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset.select_related('user').order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OpinionCreateSerializer
        return OpinionSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def feed(self, request):
        """Get personalized feed - opinions from followed users"""
        following_ids = request.user.following.values_list('following_id', flat=True)
        queryset = Opinion.objects.filter(
            Q(user_id__in=following_ids) | Q(user=request.user),
            is_deleted=False,
            visibility__in=['public', 'followers']
        ).select_related('user').order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        serializer = OpinionSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending opinions (most engagement in last 24h)"""
        from django.utils import timezone
        from datetime import timedelta
        
        yesterday = timezone.now() - timedelta(days=1)
        queryset = Opinion.objects.filter(
            is_deleted=False,
            visibility='public',
            created_at__gte=yesterday
        ).order_by('-likes_count', '-comments_count', '-reposts_count')[:50]
        
        serializer = OpinionSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """Like or unlike an opinion"""
        opinion = self.get_object()
        like, created = OpinionLike.objects.get_or_create(user=request.user, opinion=opinion)
        
        if not created:
            # Unlike
            like.delete()
            opinion.likes_count = max(0, opinion.likes_count - 1)
            opinion.save(update_fields=['likes_count'])
            return Response({'liked': False, 'likes_count': opinion.likes_count})
        
        # Like
        opinion.likes_count += 1
        opinion.save(update_fields=['likes_count'])
        return Response({'liked': True, 'likes_count': opinion.likes_count})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def repost(self, request, pk=None):
        """Repost an opinion"""
        opinion = self.get_object()
        repost, created = OpinionRepost.objects.get_or_create(
            user=request.user, 
            opinion=opinion,
            defaults={'comment': request.data.get('comment', '')}
        )
        
        if not created:
            # Un-repost
            repost.delete()
            opinion.reposts_count = max(0, opinion.reposts_count - 1)
            opinion.save(update_fields=['reposts_count'])
            return Response({'reposted': False, 'reposts_count': opinion.reposts_count})
        
        opinion.reposts_count += 1
        opinion.save(update_fields=['reposts_count'])
        return Response({'reposted': True, 'reposts_count': opinion.reposts_count})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bookmark(self, request, pk=None):
        """Bookmark or unbookmark an opinion"""
        opinion = self.get_object()
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, opinion=opinion)
        
        if not created:
            bookmark.delete()
            return Response({'bookmarked': False})
        
        return Response({'bookmarked': True})
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments on an opinion"""
        opinion = self.get_object()
        
        if request.method == 'GET':
            comments = OpinionComment.objects.filter(
                opinion=opinion,
                parent_comment__isnull=True
            ).select_related('user').order_by('-created_at')
            serializer = OpinionCommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        
        # POST - add comment
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        content = request.data.get('content', '').strip()
        parent_id = request.data.get('parent_comment')
        
        if not content:
            return Response({'detail': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        parent_comment = None
        if parent_id:
            try:
                parent_comment = OpinionComment.objects.get(id=parent_id, opinion=opinion)
            except OpinionComment.DoesNotExist:
                pass
        
        comment = OpinionComment.objects.create(
            user=request.user,
            opinion=opinion,
            parent_comment=parent_comment,
            content=content
        )
        
        opinion.comments_count += 1
        opinion.save(update_fields=['comments_count'])
        
        serializer = OpinionCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FollowViewSet(viewsets.ViewSet):
    """ViewSet for follow/unfollow functionality"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Follow or unfollow a user"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if target_user == request.user:
            return Response({'detail': 'Cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            following=target_user
        )
        
        if not created:
            follow.delete()
            return Response({
                'following': False,
                'followers_count': target_user.followers.count()
            })
        
        return Response({
            'following': True,
            'followers_count': target_user.followers.count()
        })
    
    @action(detail=False, methods=['get'])
    def followers(self, request):
        """Get list of followers"""
        user_id = request.query_params.get('user_id', request.user.id)
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        followers = CustomUser.objects.filter(following__following=user)
        serializer = UserFollowSerializer(followers, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def following(self, request):
        """Get list of users being followed"""
        user_id = request.query_params.get('user_id', request.user.id)
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        following = CustomUser.objects.filter(followers__follower=user)
        serializer = UserFollowSerializer(following, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """Get suggested users to follow"""
        # Exclude users already being followed and self
        following_ids = list(request.user.following.values_list('following_id', flat=True))
        following_ids.append(request.user.id)
        
        # Get users with most followers that current user is not following
        suggestions = CustomUser.objects.exclude(
            id__in=following_ids
        ).annotate(
            follower_count=models.Count('followers')
        ).order_by('-follower_count')[:20]
        
        serializer = UserFollowSerializer(suggestions, many=True, context={'request': request})
        return Response(serializer.data)


class BookmarkViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing bookmarked opinions"""
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user).select_related('opinion', 'opinion__user')
