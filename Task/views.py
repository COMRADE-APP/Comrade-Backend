# Task/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from datetime import datetime

from Announcements.models import (
    Task, 
    Question, 
    SubQuestion, 
    Choice, 
    FileResponse, 
    CompletedTask, 
    QuestionResponse, 
    TaskResponse,
    TaskSettings,
    TaskAnalytics
)
from .serializers import (
    TaskSerializer,
    TaskCreateSerializer,
    QuestionSerializer,
    QuestionResponseSerializer,
    TaskResponseSerializer,
    TaskSubmissionSerializer,
    CompletedTaskSerializer,
    FileResponseSerializer,
    TaskSettingsSerializer,
    TaskAnalyticsSerializer,
)


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission: staff can create/edit, others can only read.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and (
            request.user.is_staff or 
            request.user.is_admin or 
            request.user.is_lecturer or
            request.user.is_moderator
        )


class TaskViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Tasks.
    Provides list, create, retrieve, update, delete operations.
    All authenticated users can create tasks.
    """
    queryset = Task.objects.all().order_by('-time_stamp')
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TaskCreateSerializer
        return TaskSerializer
    
    def get_queryset(self):
        """Filter tasks based on visibility and user permissions"""
        user = self.request.user
        queryset = Task.objects.all()
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by state if provided  
        state_filter = self.request.query_params.get('state', None)
        if state_filter:
            queryset = queryset.filter(state=state_filter)
        
        # Filter by category
        category_filter = self.request.query_params.get('category', None)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        
        # Filter by visibility based on user type
        if not (user.is_staff or user.is_admin):
            queryset = queryset.filter(
                Q(visibility='public') | 
                Q(user=user) |
                Q(visibility='private', user=user)
            )
        
        return queryset.order_by('-time_stamp')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get all questions for a task"""
        task = self.get_object()
        questions = Question.objects.filter(task=task).order_by('position')
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit responses to a task"""
        task = self.get_object()
        user = request.user
        import json
        from django.utils import timezone
        now = timezone.now()
        
        # Check if task is an activity
        if task.is_activity:
            return Response(
                {'error': 'This task is an activity. Use mark_completed instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check start date
        if task.start_date and now < task.start_date:
            return Response(
                {'error': 'This task is not yet available for submissions'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if task is still active
        if task.state != 'active':
            return Response(
                {'error': 'This task is no longer accepting submissions'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check due date and late submissions
        if task.due_date and now > task.due_date:
            try:
                if not task.settings.accept_late_submissions:
                    return Response(
                        {'error': 'This task is past its due date and does not accept late submissions'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except TaskSettings.DoesNotExist:
                return Response(
                    {'error': 'This task is past its due date'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Check task settings for attempt limits
        try:
            settings = task.settings
            existing_submissions = TaskResponse.objects.filter(task=task, user=user).count()
            
            if settings.one_take and existing_submissions > 0:
                return Response(
                    {'error': 'This is a one-take task. You have already submitted.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if existing_submissions >= settings.max_attempts:
                return Response(
                    {'error': f'Maximum attempts ({settings.max_attempts}) reached.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except TaskSettings.DoesNotExist:
            # No settings, check simple duplicate
            if TaskResponse.objects.filter(task=task, user=user).exists():
                return Response(
                    {'error': 'You have already submitted this task'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        responses_data = request.data.get('responses', [])
        if isinstance(responses_data, str):
            try:
                responses_data = json.loads(responses_data)
            except json.JSONDecodeError:
                return Response({'error': 'Invalid responses format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create TaskResponse
        task_response = TaskResponse.objects.create(
            user=user,
            task=task,
            status='pending',
            total_score=0.0
        )
        
        current_total_score = 0.0
        
        # Create individual question responses
        for resp in responses_data:
            question_id = resp.get('question_id')
            question = get_object_or_404(Question, id=question_id)
            
            qr_data = {
                'user': user,
                'task': task,
                'question': question,
                'answer_text': resp.get('answer_text', ''),
                'status': 'pending'
            }
            
            # Handle choice answer
            choice_id = resp.get('answer_choice')
            if choice_id:
                try:
                    qr_data['answer_choice'] = Choice.objects.get(id=choice_id)
                except Choice.DoesNotExist:
                    pass
            
            # Extract expected file based on question ID
            file_key = f'file_{question_id}'
            
            # Auto-grade if it's a choice question and has a correct choice
            score = 0.0
            if 'answer_choice' in qr_data and qr_data['answer_choice'] and qr_data['answer_choice'].is_correct:
                score = 1.0 # Default point for correct choice
            
            qr_data['score'] = score
            current_total_score += score
            
            qr = QuestionResponse.objects.create(**qr_data)
            
            if question.question_type == 'file' and file_key in request.FILES:
                qr.answer_file = request.FILES[file_key]
                qr.save()
            elif question.question_type == 'multiple_file':
                # Save first file to answer_file, optionally could expand schema, but saving one and parsing others if needed
                files = request.FILES.getlist(file_key)
                if files:
                    qr.answer_file = files[0]
                    qr.save()
            
            task_response.question_responses.add(qr)
        
        # Save auto-graded total score
        task_response.total_score = current_total_score
        task_response.save()
        
        # Mark task as completed for user
        CompletedTask.objects.update_or_create(
            user=user,
            task=task,
            defaults={'is_completed': True, 'status': 'pending'}
        )
        
        # Track analytics
        TaskAnalytics.objects.create(task=task, user=user, action='submit')
        
        serializer = TaskResponseSerializer(task_response)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        """Get all responses for a task (staff only)"""
        task = self.get_object()
        
        # Only allow staff to see all responses
        if not (request.user.is_staff or request.user.is_admin or request.user == task.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        responses = TaskResponse.objects.filter(task=task)
        serializer = TaskResponseSerializer(responses, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def grade_response(self, request, pk=None):
        """Submit grades for a specific TaskResponse"""
        task_response = self.get_object()
        task = task_response.task
        
        # Only task creator or staff can grade
        if not (request.user.is_staff or request.user.is_admin or request.user == task.user):
            return Response(
                {'error': 'Permission denied. Only the task creator can grade submissions.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        grades_data = request.data.get('grades', [])
        if not isinstance(grades_data, list):
            return Response({'error': 'Invalid grades format. Expected a list.'}, status=status.HTTP_400_BAD_REQUEST)
            
        total_score = 0.0
        
        # Update individual question scores
        for grade_obj in grades_data:
            qr_id = grade_obj.get('question_response_id')
            score = grade_obj.get('score', 0.0)
            
            try:
                qr = task_response.question_responses.get(id=qr_id)
                qr.score = float(score)
                qr.save()
            except (QuestionResponse.DoesNotExist, ValueError):
                continue
                
        # Recalculate total score
        for qr in task_response.question_responses.all():
            total_score += qr.score
            
        task_response.total_score = total_score
        task_response.status = 'graded' # Or leave as 'pending' depending on requirement
        task_response.save()
        
        serializer = TaskResponseSerializer(task_response)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def my_response(self, request, pk=None):
        """Get current user's response for a task"""
        task = self.get_object()
        response = TaskResponse.objects.filter(task=task, user=request.user).first()
        
        if not response:
            return Response(
                {'error': 'No submission found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TaskResponseSerializer(response)
        return Response(serializer.data)
        
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark an activity (non-submission task) as completed"""
        task = self.get_object()
        user = request.user
        
        if not task.is_activity:
            return Response(
                {'error': 'Only activities can be marked as completed directly. For tasks with questions, use the submit endpoint.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        CompletedTask.objects.update_or_create(
            user=user,
            task=task,
            defaults={'is_completed': True, 'status': 'completed'}
        )
        TaskAnalytics.objects.create(task=task, user=user, action='mark_completed')
        
        return Response({'message': 'Activity marked as completed successfully'}, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'])
    def my_created_submissions(self, request):
        """Get all submissions for tasks created by the current user"""
        user = request.user
        
        tasks_created_by_user = Task.objects.filter(user=user)
        responses = TaskResponse.objects.filter(task__in=tasks_created_by_user).order_by('-time_stamp')
        
        serializer = TaskResponseSerializer(responses, many=True)
        return Response(serializer.data)
    
    # SETTINGS
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    @action(detail=True, methods=['get', 'put', 'patch'], url_path='settings')
    def task_settings(self, request, pk=None):
        """Get or update task settings"""
        task = self.get_object()
        
        if request.method == 'GET':
            try:
                settings = task.settings
            except TaskSettings.DoesNotExist:
                settings = TaskSettings.objects.create(task=task)
            serializer = TaskSettingsSerializer(settings)
            return Response(serializer.data)
        
        # PUT/PATCH — only creator or staff
        if task.user != request.user and not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            settings = task.settings
        except TaskSettings.DoesNotExist:
            settings = TaskSettings.objects.create(task=task)
        
        serializer = TaskSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    # ANALYTICS
    
    @action(detail=True, methods=['post'])
    def record_access(self, request, pk=None):
        """Record user accessing the task"""
        task = self.get_object()
        user = request.user if request.user.is_authenticated else None
        TaskAnalytics.objects.create(task=task, user=user, action='access')
        return Response({'status': 'recorded'})
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for task (creator only)"""
        task = self.get_object()
        
        if task.user != request.user and not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.db.models.functions import TruncDate
        
        action_counts = dict(
            TaskAnalytics.objects.filter(task=task)
            .values_list('action').annotate(count=Count('id'))
            .values_list('action', 'count')
        )
        
        daily_access = list(
            TaskAnalytics.objects.filter(task=task)
            .annotate(date=TruncDate('created_at'))
            .values('date').annotate(count=Count('id'))
            .order_by('date').values('date', 'count')[:30]
        )
        
        unique_visitors = TaskAnalytics.objects.filter(
            task=task, action='access', user__isnull=False
        ).values('user').distinct().count()
        
        return Response({
            'action_counts': action_counts,
            'daily_access': daily_access,
            'unique_visitors': unique_visitors,
            'total_submissions': TaskResponse.objects.filter(task=task).count(),
            'question_count': Question.objects.filter(task=task).count(),
        })
    
    # SAVE DRAFT
    
    @action(detail=True, methods=['post'])
    def save_draft(self, request, pk=None):
        """Save draft responses (auto-save feature)"""
        task = self.get_object()
        # Store draft in analytics metadata for now
        TaskAnalytics.objects.create(
            task=task, user=request.user, action='save_draft',
            metadata={'responses': request.data.get('responses', [])}
        )
        return Response({'status': 'draft_saved'})


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Questions within tasks"""
    queryset = Question.objects.all().order_by('position')
    serializer_class = QuestionSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]
    
    def get_queryset(self):
        task_id = self.request.query_params.get('task', None)
        if task_id:
            return Question.objects.filter(task_id=task_id).order_by('position')
        return Question.objects.all().order_by('position')


class TaskResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing task responses"""
    queryset = TaskResponse.objects.all()
    serializer_class = TaskResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Staff can see all, others only their own
        if user.is_staff or user.is_admin:
            return TaskResponse.objects.all()
        return TaskResponse.objects.filter(user=user)


class MyTasksViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing user's own tasks and completed tasks"""
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Task.objects.filter(user=user).order_by('-time_stamp')
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """Get all completed tasks for current user"""
        completed = CompletedTask.objects.filter(
            user=request.user, 
            is_completed=True
        )
        serializer = CompletedTaskSerializer(completed, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending/uncompleted tasks for current user"""
        completed_task_ids = CompletedTask.objects.filter(
            user=request.user,
            is_completed=True
        ).values_list('task_id', flat=True)
        
        pending = Task.objects.filter(
            state='active'
        ).exclude(id__in=completed_task_ids)
        
        serializer = TaskSerializer(pending, many=True)
        return Response(serializer.data)
