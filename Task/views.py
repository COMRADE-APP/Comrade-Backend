# Task/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import datetime

from Announcements.models import (
    Task, 
    Question, 
    SubQuestion, 
    Choice, 
    FileResponse, 
    CompletedTask, 
    QuestionResponse, 
    TaskResponse
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
        
        # Check if task is still active
        if task.state != 'active':
            return Response(
                {'error': 'This task is no longer accepting submissions'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already submitted
        if TaskResponse.objects.filter(task=task, user=user).exists():
            return Response(
                {'error': 'You have already submitted this task'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        responses_data = request.data.get('responses', [])
        
        # Create TaskResponse
        task_response = TaskResponse.objects.create(
            user=user,
            task=task,
            status='pending'
        )
        
        # Create individual question responses
        for resp in responses_data:
            question_id = resp.get('question_id')
            question = get_object_or_404(Question, id=question_id)
            
            QuestionResponse.objects.create(
                user=user,
                task=task,
                question=question,
                answer_text=resp.get('answer_text', ''),
                status='pending'
            )
        
        # Mark task as completed for user
        CompletedTask.objects.create(
            user=user,
            task=task,
            is_completed=True,
            status='pending'
        )
        
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
