from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Count
from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta
from itertools import chain

from .models import (
    Opinion, OpinionLike, OpinionComment, OpinionRepost, 
    Follow, Bookmark, OpinionMedia, ContentBlock, ContentReport, HiddenContent,
    Story, StoryView as StoryViewModel
)
from .serializers import (
    OpinionSerializer, OpinionCreateSerializer, OpinionCommentSerializer,
    FollowSerializer, UserFollowSerializer, BookmarkSerializer,
    StorySerializer, StoryCreateSerializer
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


def create_interaction_notification(actor, recipient, notification_type, opinion=None, message=''):
    """Helper to create notifications for interactions"""
    from Notifications.models import create_notification
    
    if actor.id == recipient.id:
        return None
    
    content_id = opinion.id if opinion else ''
    action_url = f'/opinions/{opinion.id}' if opinion else ''
    
    return create_notification(
        recipient=recipient,
        notification_type=notification_type,
        message=message,
        actor=actor,
        content_type='opinion',
        content_id=content_id,
        action_url=action_url
    )


class OpinionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for opinions - main feed functionality
    Anyone can view public opinions, anyone can create.
    """
    serializer_class = OpinionSerializer
    pagination_class = OpinionPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Opinion.objects.filter(is_deleted=False)
        
        # Exclude blocked users and hidden content
        if user.is_authenticated:
            blocked_ids = ContentBlock.objects.filter(user=user).values_list('blocked_user_id', flat=True)
            hidden_opinion_ids = HiddenContent.objects.filter(user=user).values_list('opinion_id', flat=True)
            queryset = queryset.exclude(user_id__in=blocked_ids).exclude(id__in=hidden_opinion_ids)
        
        # Filter by visibility
        if user.is_authenticated:
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
        
        return queryset.select_related('user', 'reposted_by', 'original_opinion__user').prefetch_related('media_files').order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OpinionCreateSerializer
        return OpinionSerializer
    
    def perform_create(self, serializer):
        # Check character limit based on user tier
        content = self.request.data.get('content', '')
        user = self.request.user
        
        # Get user tier (default to free)
        tier = 'free'
        try:
            from Payment.models import PaymentProfile
            profile = PaymentProfile.objects.get(user__user=user)
            tier = profile.tier
        except Exception:
            pass
        
        max_chars = 5000 if tier in ['premium', 'gold'] else 500
        if len(content) > max_chars:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'content': f'Maximum {max_chars} characters allowed for your tier.'})
        
        # Handle entity authorship - get organisation or institution from request
        organisation = None
        institution = None
        establishment = None
        poster_role = None
        
        org_id = self.request.data.get('organisation')
        inst_id = self.request.data.get('institution')
        estab_id = self.request.data.get('establishment')
        
        if org_id:
            try:
                from Organisation.models import Organisation, OrganisationMember
                membership = OrganisationMember.objects.filter(
                    organisation_id=org_id, 
                    user=user, 
                    is_active=True
                ).first()
                org = Organisation.objects.get(id=org_id)
                if membership:
                    organisation = org
                    poster_role = membership.role
                elif org.created_by == user:
                    organisation = org
                    poster_role = 'owner'
            except Exception as e:
                print(f"Error setting organisation: {e}")
        
        if inst_id:
            try:
                from Institution.models import Institution, InstitutionMember
                membership = InstitutionMember.objects.filter(
                    institution_id=inst_id, 
                    user=user, 
                    is_active=True
                ).first()
                inst = Institution.objects.get(id=inst_id)
                if membership:
                    institution = inst
                    # Map institution roles to poster_role
                    role_map = {'creator': 'owner', 'admin': 'admin', 'moderator': 'moderator', 'member': 'member', 'subscriber': 'member'}
                    poster_role = role_map.get(membership.role, 'member')
                elif inst.created_by == user:
                    institution = inst
                    poster_role = 'owner'
            except Exception as e:
                print(f"Error setting institution: {e}")
        
        if estab_id:
            try:
                from Payment.models import Establishment
                estab = Establishment.objects.get(id=estab_id)
                if estab.owner.user == user:
                    establishment = estab
                    poster_role = 'owner'
                # Check if user is linked via the org that owns it
                elif estab.organisation and organisation and estab.organisation == organisation:
                    establishment = estab
            except Exception as e:
                print(f"Error setting establishment: {e}")
        
        # Allow manual poster_role override (if provided explicitly)
        explicit_role = self.request.data.get('poster_role')
        if explicit_role and explicit_role in ['owner', 'admin', 'moderator', 'member']:
            poster_role = explicit_role
        
        # Handle room-scoped opinions
        room = None
        room_id = self.request.data.get('room')
        if room_id:
            try:
                from Rooms.models import Room
                room = Room.objects.get(id=room_id)
            except Exception as e:
                print(f"Error setting room: {e}")
        
        # Handle anonymous posting
        is_anonymous = self.request.data.get('is_anonymous', False)
        if isinstance(is_anonymous, str):
            is_anonymous = is_anonymous.lower() in ('true', '1', 'yes')
        
        opinion = serializer.save(
            user=user, 
            organisation=organisation, 
            institution=institution,
            establishment=establishment,
            poster_role=poster_role,
            room=room,
            is_anonymous=bool(is_anonymous)
        )
        
        # Handle media files
        media_files = self.request.FILES.getlist('media')
        for i, file in enumerate(media_files[:4]):  # Max 4 files
            media_type = 'image'
            if file.content_type.startswith('video'):
                media_type = 'video'
            elif 'gif' in file.content_type:
                media_type = 'gif'
            elif not file.content_type.startswith('image'):
                media_type = 'file'
            
            OpinionMedia.objects.create(
                opinion=opinion,
                file=file,
                media_type=media_type,
                file_name=file.name,
                file_size=file.size,
                mime_type=file.content_type,
                order=i
            )
            
        # Handle mentioned users notifications
        mentioned_user_ids = self.request.data.getlist('mentioned_users')
        if mentioned_user_ids:
            # Deduplicate
            mentioned_user_ids = list(set(mentioned_user_ids))
            for user_id in mentioned_user_ids:
                try:
                    user_to_notify = CustomUser.objects.get(id=user_id)
                    create_interaction_notification(
                        user, 
                        user_to_notify, 
                        'mention', 
                        opinion,
                        f'{user.first_name} mentioned you in a post'
                    )
                except Exception as e:
                    print(f"Error notifying mentioned user {user_id}: {e}")
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def feed(self, request):
        """Get personalized feed - opinions from followed users"""
        following_ids = request.user.following.values_list('following_id', flat=True)
        blocked_ids = ContentBlock.objects.filter(user=request.user).values_list('blocked_user_id', flat=True)
        hidden_ids = HiddenContent.objects.filter(user=request.user).values_list('opinion_id', flat=True)
        
        queryset = Opinion.objects.filter(
            Q(user_id__in=following_ids) | Q(user=request.user),
            is_deleted=False,
            visibility__in=['public', 'followers']
        ).exclude(
            user_id__in=blocked_ids
        ).exclude(
            id__in=hidden_ids
        ).select_related('user', 'reposted_by').prefetch_related('media_files').order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        serializer = OpinionSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending opinions (most engagement in last 24h)"""
        yesterday = timezone.now() - timedelta(days=1)
        queryset = Opinion.objects.filter(
            is_deleted=False,
            visibility='public',
            created_at__gte=yesterday
        ).order_by('-likes_count', '-comments_count', '-reposts_count')[:50]
        
        serializer = OpinionSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='room/(?P<room_id>[^/.]+)')
    def room_opinions(self, request, room_id=None):
        """Get opinions for a specific room"""
        queryset = Opinion.objects.filter(
            is_deleted=False,
            room_id=room_id
        ).select_related('user', 'reposted_by').prefetch_related('media_files').order_by('-created_at')
        
        # Exclude blocked users if authenticated
        if request.user.is_authenticated:
            blocked_ids = ContentBlock.objects.filter(user=request.user).values_list('blocked_user_id', flat=True)
            hidden_ids = HiddenContent.objects.filter(user=request.user).values_list('opinion_id', flat=True)
            queryset = queryset.exclude(user_id__in=blocked_ids).exclude(id__in=hidden_ids)
        
        page = self.paginate_queryset(queryset)
        serializer = OpinionSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        """Like or unlike an opinion"""
        opinion = self.get_object()
        like, created = OpinionLike.objects.get_or_create(user=request.user, opinion=opinion)
        
        if not created:
            like.delete()
            opinion.likes_count = max(0, opinion.likes_count - 1)
            opinion.save(update_fields=['likes_count'])
            return Response({'liked': False, 'likes_count': opinion.likes_count})
        
        opinion.likes_count += 1
        opinion.save(update_fields=['likes_count'])
        
        # Create notification
        create_interaction_notification(
            request.user, opinion.user, 'like', opinion,
            f'{request.user.first_name} liked your post'
        )
        
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
            repost.delete()
            opinion.reposts_count = max(0, opinion.reposts_count - 1)
            opinion.save(update_fields=['reposts_count'])
            return Response({'reposted': False, 'reposts_count': opinion.reposts_count})
        
        opinion.reposts_count += 1
        opinion.save(update_fields=['reposts_count'])
        
        # Create repost opinion entry
        Opinion.objects.create(
            user=opinion.user,
            content=opinion.content,
            is_repost=True,
            original_opinion=opinion,
            reposted_by=request.user,
            visibility=opinion.visibility
        )
        
        create_interaction_notification(
            request.user, opinion.user, 'repost', opinion,
            f'{request.user.first_name} reposted your post'
        )
        
        return Response({'reposted': True, 'reposts_count': opinion.reposts_count})
    
    @action(detail=True, methods=['get'])
    def reposters(self, request, pk=None):
        """Get users who reposted an opinion (filtered by following)"""
        opinion = self.get_object()
        
        repost_users = OpinionRepost.objects.filter(opinion=opinion).values_list('user_id', flat=True)
        
        if request.user.is_authenticated:
            following_ids = list(request.user.following.values_list('following_id', flat=True))
            # Include self if I report it
            following_ids.append(request.user.id)
            
            # Filter: only show reposters that I follow (or myself)
            # Find intersection of reposters and following
            valid_ids = list(set(repost_users) & set(following_ids))
            users = CustomUser.objects.filter(id__in=valid_ids)
        else:
            return Response([])

        serializer = UserFollowSerializer(users, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def share(self, request, pk=None):
        """Track share count"""
        opinion = self.get_object()
        opinion.shares_count += 1
        opinion.save(update_fields=['shares_count'])
        return Response({'shares_count': opinion.shares_count})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bookmark(self, request, pk=None):
        """Bookmark or unbookmark an opinion"""
        opinion = self.get_object()
        bookmark, created = Bookmark.objects.get_or_create(user=request.user, opinion=opinion)
        
        if not created:
            bookmark.delete()
            return Response({'bookmarked': False})
        
        return Response({'bookmarked': True})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def hide(self, request, pk=None):
        """Hide opinion from recommendations"""
        opinion = self.get_object()
        reason = request.data.get('reason', 'not_interested')
        
        hidden, created = HiddenContent.objects.get_or_create(
            user=request.user,
            opinion=opinion,
            defaults={'reason': reason}
        )
        
        return Response({'hidden': True, 'message': 'You won\'t see this content anymore'})
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def report(self, request, pk=None):
        """Report content"""
        opinion = self.get_object()
        reason = request.data.get('reason', 'other')
        description = request.data.get('description', '')
        
        ContentReport.objects.create(
            reporter=request.user,
            opinion=opinion,
            reported_user=opinion.user,
            reason=reason,
            description=description
        )
        
        return Response({'reported': True, 'message': 'Thank you for your report. We will review it.'})
    
    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, pk=None):
        """Get or add comments on an opinion"""
        opinion = self.get_object()
        
        if request.method == 'GET':
            comments = OpinionComment.objects.filter(
                opinion=opinion,
                parent_comment__isnull=True
            ).select_related('user').prefetch_related('replies__user').order_by('-created_at')
            serializer = OpinionCommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        print(request.data)
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
        
        # Notify opinion owner
        create_interaction_notification(
            request.user, opinion.user, 'comment', opinion,
            f'{request.user.first_name} commented on your post'
        )
        
        # If replying, also notify parent comment owner
        if parent_comment and parent_comment.user != opinion.user:
            create_interaction_notification(
                request.user, parent_comment.user, 'reply', opinion,
                f'{request.user.first_name} replied to your comment'
            )
        
        serializer = OpinionCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BlockViewSet(viewsets.ViewSet):
    """ViewSet for blocking users"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Block or unblock a user"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'detail': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if target_user == request.user:
            return Response({'detail': 'Cannot block yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        block, created = ContentBlock.objects.get_or_create(
            user=request.user,
            blocked_user=target_user,
            defaults={'reason': request.data.get('reason', '')}
        )
        
        if not created:
            block.delete()
            return Response({'blocked': False})
        
        # Also unfollow if following
        Follow.objects.filter(follower=request.user, following=target_user).delete()
        Follow.objects.filter(follower=target_user, following=request.user).delete()
        
        return Response({'blocked': True, 'message': f'You have blocked {target_user.first_name}'})
    
    @action(detail=False, methods=['get'])
    def list_blocked(self, request):
        """Get list of blocked users"""
        blocked = ContentBlock.objects.filter(user=request.user).select_related('blocked_user')
        data = [
            {
                'id': b.blocked_user.id,
                'name': f'{b.blocked_user.first_name} {b.blocked_user.last_name}',
                'email': b.blocked_user.email,
                'blocked_at': b.created_at
            }
            for b in blocked
        ]
        return Response(data)


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
        
        # Check if blocked
        if ContentBlock.objects.filter(
            Q(user=request.user, blocked_user=target_user) |
            Q(user=target_user, blocked_user=request.user)
        ).exists():
            return Response({'detail': 'Cannot follow this user'}, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # Create notification
        create_interaction_notification(
            request.user, target_user, 'follow', None,
            f'{request.user.first_name} started following you'
        )
        
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
        following_ids = list(request.user.following.values_list('following_id', flat=True))
        following_ids.append(request.user.id)
        blocked_ids = list(ContentBlock.objects.filter(
            Q(user=request.user) | Q(blocked_user=request.user)
        ).values_list('blocked_user_id', 'user_id'))
        blocked_ids = [item for sublist in blocked_ids for item in sublist]
        
        suggestions = CustomUser.objects.exclude(
            id__in=following_ids + blocked_ids
        ).annotate(
            follower_count=Count('followers')
        ).order_by('-follower_count')[:20]
        
        serializer = UserFollowSerializer(suggestions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def circles(self, request):
        """Get circles - mutual followers (users who follow you and you follow them)"""
        # Get users I'm following
        following_ids = set(request.user.following.values_list('following_id', flat=True))
        # Get users following me
        followers_ids = set(request.user.followers.values_list('follower_id', flat=True))
        # Intersection = mutual followers (circles)
        circle_ids = following_ids & followers_ids
        
        circles = CustomUser.objects.filter(id__in=circle_ids)
        
        results = []
        for u in circles:
            avatar_url = None
            try:
                if hasattr(u, 'user_profile') and u.user_profile.avatar:
                    avatar_url = request.build_absolute_uri(u.user_profile.avatar.url)
            except:
                pass
            
            results.append({
                'id': u.id,
                'user': {
                    'id': u.id,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'full_name': f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email,
                    'avatar_url': avatar_url,
                },
                'first_name': u.first_name,
                'last_name': u.last_name,
                'full_name': f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email,
            })
        
        return Response(results)


class BookmarkViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing bookmarked opinions"""
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user).select_related('opinion', 'opinion__user')


class UnifiedFeedView(APIView):
    """
    Unified feed combining opinions, research, articles, announcements, products
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get(self, request):
        feed_type = request.query_params.get('type', 'all')  # all, opinions, research, announcements, products
        limit = int(request.query_params.get('limit', 20))
        
        feed_items = []
        
        # Get opinions
        if feed_type in ['all', 'opinions']:
            opinions = self._get_opinions(request, limit if feed_type == 'opinions' else limit // 3)
            feed_items.extend(opinions)
        
        # Get research
        if feed_type in ['all', 'research']:
            research = self._get_research(request, limit if feed_type == 'research' else limit // 4)
            feed_items.extend(research)
        
        # Get announcements
        if feed_type in ['all', 'announcements']:
            announcements = self._get_announcements(request, limit if feed_type == 'announcements' else limit // 4)
            feed_items.extend(announcements)
        
        # Get products
        if feed_type in ['all', 'products']:
            products = self._get_products(request, limit if feed_type == 'products' else limit // 4)
            feed_items.extend(products)
        
        # Sort by date
        feed_items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return Response({
            'results': feed_items[:limit],
            'count': len(feed_items)
        })
    
    def _get_opinions(self, request, limit):
        from .serializers import OpinionSerializer
        
        queryset = Opinion.objects.filter(
            is_deleted=False,
            visibility='public'
        ).select_related('user', 'reposted_by').prefetch_related('media_files').order_by('-created_at')[:limit]
        
        serializer = OpinionSerializer(queryset, many=True, context={'request': request})
        items = serializer.data
        
        for item in items:
            item['content_type'] = 'opinion'
            item['category_label'] = 'Opinion'
            item['category_color'] = 'blue'
        
        return items
    
    def _get_research(self, request, limit):
        try:
            from Research.models import ResearchProject
            
            research = ResearchProject.objects.filter(
                is_published=True
            ).select_related('principal_investigator').order_by('-published_at')[:limit]
            
            items = []
            for r in research:
                items.append({
                    'id': str(r.id),
                    'content_type': 'research',
                    'category_label': 'Research',
                    'category_color': 'purple',
                    'title': r.title,
                    'content': r.abstract[:300] + '...' if len(r.abstract) > 300 else r.abstract,
                    'creator': {
                        'id': r.principal_investigator.id,
                        'name': f'{r.principal_investigator.first_name} {r.principal_investigator.last_name}',
                    },
                    'created_at': r.published_at.isoformat() if r.published_at else r.created_at.isoformat(),
                    'views_count': r.views,
                    'action_url': f'/research/{r.id}'
                })
            return items
        except Exception:
            return []
    
    def _get_announcements(self, request, limit):
        try:
            from Announcements.models import Announcement
            
            announcements = Announcement.objects.filter(
                is_active=True
            ).order_by('-created_at')[:limit]
            
            items = []
            for a in announcements:
                items.append({
                    'id': a.id,
                    'content_type': 'announcement',
                    'category_label': 'Announcement',
                    'category_color': 'yellow',
                    'title': a.title,
                    'content': a.content[:300] + '...' if len(a.content) > 300 else a.content,
                    'created_at': a.created_at.isoformat(),
                    'action_url': f'/announcements/{a.id}'
                })
            return items
        except Exception:
            return []
    
    def _get_products(self, request, limit):
        try:
            from Payment.models import Product
            
            products = Product.objects.filter(
                is_active=True
            ).order_by('-created_at')[:limit]
            
            items = []
            for p in products:
                items.append({
                    'id': str(p.id),
                    'content_type': 'product',
                    'category_label': 'Product',
                    'category_color': 'green',
                    'title': p.name,
                    'content': p.description[:200] + '...' if len(p.description) > 200 else p.description,
                    'price': str(p.price),
                    'created_at': p.created_at.isoformat(),
                    'action_url': f'/shop/{p.id}'
                })
            return items
        except Exception:
            return []


class NewContentCheckView(APIView):
    """Check for new content since last check (for refresh notification)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        since = request.query_params.get('since')
        if not since:
            return Response({'has_new': False})
        
        try:
            from datetime import datetime
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            
            new_count = Opinion.objects.filter(
                created_at__gt=since_dt,
                is_deleted=False,
                visibility='public'
            ).count()
            
            return Response({
                'has_new': new_count > 0,
                'new_count': new_count
            })
        except ValueError:
            return Response({'has_new': False})


class StoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Instagram/WhatsApp-style stories.
    Stories are grouped by user on the frontend.
    """
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Return only active, non-expired stories"""
        return Story.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('user').order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return StoryCreateSerializer
        return StorySerializer

    def list(self, request):
        """Get stories from followed users, grouped by user"""
        user = request.user
        if not user.is_authenticated:
            return Response([])

        # Get stories from followed users + own stories
        following_ids = list(user.following.values_list('following_id', flat=True))
        following_ids.append(user.id)

        stories = self.get_queryset().filter(user_id__in=following_ids)

        # Group stories by user
        from collections import OrderedDict
        grouped = OrderedDict()
        for story in stories:
            uid = story.user_id
            if uid not in grouped:
                user_data = {
                    'id': story.user.id,
                    'email': story.user.email,
                    'first_name': story.user.first_name,
                    'last_name': story.user.last_name,
                    'full_name': f"{story.user.first_name or ''} {story.user.last_name or ''}".strip() or story.user.email,
                    'avatar_url': None,
                }
                try:
                    if hasattr(story.user, 'user_profile') and story.user.user_profile.avatar:
                        user_data['avatar_url'] = request.build_absolute_uri(story.user.user_profile.avatar.url)
                except:
                    pass
                grouped[uid] = {
                    'user': user_data,
                    'stories': [],
                    'has_unviewed': False,
                }
            serialized = StorySerializer(story, context={'request': request}).data
            grouped[uid]['stories'].append(serialized)
            if not serialized.get('has_viewed'):
                grouped[uid]['has_unviewed'] = True

        # Put current user's stories first, then users with unviewed stories
        result = []
        if user.id in grouped:
            result.append(grouped.pop(user.id))
        unviewed = [v for v in grouped.values() if v['has_unviewed']]
        viewed = [v for v in grouped.values() if not v['has_unviewed']]
        result.extend(unviewed)
        result.extend(viewed)

        return Response(result)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def view(self, request, pk=None):
        """Mark a story as viewed"""
        story = self.get_object()
        if story.user == request.user:
            return Response({'viewed': True})

        _, created = StoryViewModel.objects.get_or_create(
            story=story,
            viewer=request.user
        )
        if created:
            story.views_count += 1
            story.save(update_fields=['views_count'])

        return Response({'viewed': True, 'views_count': story.views_count})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_stories(self, request):
        """Get current user's active stories"""
        stories = self.get_queryset().filter(user=request.user)
        serializer = StorySerializer(stories, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def viewers(self, request, pk=None):
        """Get list of viewers for a story (only story owner)"""
        story = self.get_object()
        if story.user != request.user:
            return Response({'detail': 'Only the story owner can see viewers'}, status=status.HTTP_403_FORBIDDEN)

        views = StoryViewModel.objects.filter(story=story).select_related('viewer')
        data = [
            {
                'id': v.viewer.id,
                'name': f"{v.viewer.first_name or ''} {v.viewer.last_name or ''}".strip() or v.viewer.email,
                'viewed_at': v.viewed_at,
            }
            for v in views
        ]
        return Response(data)

