import random
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, F
from .models import QNote, QNoteLike, QNoteComment, QNoteCommentLike, QNoteRepost, QNoteSave
from .serializers import (
    QNoteSerializer, QNoteCreateSerializer, QNoteCommentSerializer
)


class QNoteViewSet(viewsets.ModelViewSet):
    queryset = QNote.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return QNoteCreateSerializer
        return QNoteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.save(author=self.request.user)
        output = QNoteSerializer(note, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        if instance.author == self.request.user:
            instance.is_active = False
            instance.save()

    @action(detail=False, methods=['get'])
    def random(self, request):
        user = request.user
        notes = list(QNote.objects.filter(is_active=True).exclude(author=user))
        random.shuffle(notes)
        page_size = int(request.query_params.get('page_size', 10))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        page_notes = notes[start:end]
        serializer = QNoteSerializer(page_notes, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'has_next': end < len(notes),
            'page': page,
            'total': len(notes),
        })

    @action(detail=False, methods=['get'])
    def trending(self, request):
        notes = QNote.objects.filter(is_active=True).exclude(author=request.user) \
            .annotate(total=Count('likes') + Count('reposts') + Count('comments')) \
            .order_by('-total')[:20]
        serializer = QNoteSerializer(notes, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        note = self.get_object()
        like, created = QNoteLike.objects.get_or_create(note=note, user=request.user)
        if created:
            QNote.objects.filter(pk=note.pk).update(like_count=F('like_count') + 1)
            note.refresh_from_db()
            return Response({'liked': True, 'like_count': note.like_count})
        else:
            like.delete()
            QNote.objects.filter(pk=note.pk).update(like_count=F('like_count') - 1)
            note.refresh_from_db()
            return Response({'liked': False, 'like_count': note.like_count})

    @action(detail=True, methods=['post'])
    def repost(self, request, pk=None):
        note = self.get_object()
        repost, created = QNoteRepost.objects.get_or_create(note=note, user=request.user)
        if created:
            QNote.objects.filter(pk=note.pk).update(repost_count=F('repost_count') + 1)
            note.refresh_from_db()
            return Response({'reposted': True, 'repost_count': note.repost_count})
        else:
            repost.delete()
            QNote.objects.filter(pk=note.pk).update(repost_count=F('repost_count') - 1)
            note.refresh_from_db()
            return Response({'reposted': False, 'repost_count': note.repost_count})

    @action(detail=True, methods=['post'])
    def save(self, request, pk=None):
        note = self.get_object()
        saved, created = QNoteSave.objects.get_or_create(note=note, user=request.user)
        if created:
            QNote.objects.filter(pk=note.pk).update(save_count=F('save_count') + 1)
            note.refresh_from_db()
            return Response({'saved': True, 'save_count': note.save_count})
        else:
            saved.delete()
            QNote.objects.filter(pk=note.pk).update(save_count=F('save_count') - 1)
            note.refresh_from_db()
            return Response({'saved': False, 'save_count': note.save_count})

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        note = self.get_object()
        if request.method == 'GET':
            comments = QNoteComment.objects.filter(note=note, parent=None).order_by('created_at')
            serializer = QNoteCommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        else:
            content = request.data.get('content', '').strip()
            if not content:
                return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
            parent_id = request.data.get('parent')
            parent = None
            if parent_id:
                parent = QNoteComment.objects.filter(id=parent_id, note=note).first()
            comment = QNoteComment.objects.create(
                note=note,
                author=request.user,
                content=content,
                parent=parent,
            )
            QNote.objects.filter(pk=note.pk).update(comment_count=F('comment_count') + 1)
            note.refresh_from_db()
            serializer = QNoteCommentSerializer(comment, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        note = self.get_object()
        return Response({
            'id': str(note.id),
            'content': note.content,
            'color': note.color,
            'share_url': request.build_absolute_uri(f'/qnotes/{note.id}'),
        })

    @action(detail=True, methods=['post'], url_path='comments/(?P<comment_id>[^/.]+)/like')
    def comment_like(self, request, pk=None, comment_id=None):
        note = self.get_object()
        comment = QNoteComment.objects.filter(id=comment_id, note=note).first()
        if not comment:
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        like, created = QNoteCommentLike.objects.get_or_create(comment=comment, user=request.user)
        if created:
            QNoteComment.objects.filter(pk=comment.pk).update(like_count=F('like_count') + 1)
            comment.refresh_from_db()
            return Response({'liked': True, 'like_count': comment.like_count})
        else:
            like.delete()
            QNoteComment.objects.filter(pk=comment.pk).update(like_count=F('like_count') - 1)
            comment.refresh_from_db()
            return Response({'liked': False, 'like_count': comment.like_count})
