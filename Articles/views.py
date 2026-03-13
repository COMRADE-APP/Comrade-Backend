from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Article, ArticleAttachment, Comment, ArticleLike, ArticleBookmark
from .serializers import ArticleSerializer, CommentSerializer
from django.db.models import Q

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user

class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'tags']
    ordering_fields = ['created_at', 'views_count', 'published_at']
    ordering = ['-created_at']
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        queryset = Article.objects.all()

        # Filtering by status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        else:
            # Default: show published, or my drafts
            if user.is_authenticated:
                queryset = queryset.filter(Q(status='published') | Q(author=user))
            else:
                queryset = queryset.filter(status='published')
        
        # Filter by 'mine'
        if self.request.query_params.get('mine') == 'true' and user.is_authenticated:
            queryset = queryset.filter(author=user)
            
        # Filter by category
        category = self.request.query_params.get('category')
        if category and category != 'all':
            queryset = queryset.filter(category=category)

        return queryset

    def perform_create(self, serializer):
        article = serializer.save(author=self.request.user)
        self._handle_attachments(article)

    def perform_update(self, serializer):
        article = serializer.save()
        self._handle_attachments(article)

    def _handle_attachments(self, article):
        attachments = self.request.FILES.getlist('attachments')
        for file in attachments:
            ArticleAttachment.objects.create(article=article, file=file)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def upload_attachment(self, request, id=None):
        article = self.get_object()
        if article.author != request.user:
            return Response({'detail': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
            
        attachment = ArticleAttachment.objects.create(article=article, file=file)
        # return full URL
        url = request.build_absolute_uri(attachment.file.url)
        return Response({'id': attachment.id, 'url': url, 'name': file.name, 'type': file.content_type}, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Increment view count
        instance.views_count += 1
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def record_read(self, request, id=None):
        instance = self.get_object()
        
        # Track per-user read if authenticated
        if request.user.is_authenticated:
            from .models import ArticleRead
            read, created = ArticleRead.objects.get_or_create(article=instance, user=request.user)
            if created:
                instance.read_count += 1
                instance.save(update_fields=['read_count'])
        else:
            # For anonymous users, just increment
            instance.read_count += 1
            instance.save(update_fields=['read_count'])
            
        return Response({'status': 'read recorded', 'read_count': instance.read_count})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, id=None):
        article = self.get_object()
        like, created = ArticleLike.objects.get_or_create(article=article, user=request.user)
        if not created:
            like.delete()
            return Response({'status': 'unliked'})
        return Response({'status': 'liked'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bookmark(self, request, id=None):
        article = self.get_object()
        bookmark, created = ArticleBookmark.objects.get_or_create(article=article, user=request.user)
        if not created:
            bookmark.delete()
            return Response({'status': 'unbookmarked'})
        return Response({'status': 'bookmarked'})
    
    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def comments(self, request, id=None):
        article = self.get_object()
        if request.method == 'GET':
            comments = Comment.objects.filter(article=article, parent=None)
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(article=article, user=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Comment.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
