# Task/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from datetime import datetime
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
    TaskAnalytics,
    TaskGradingConfig
)
from Task.serializers import (
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
    TaskGradingConfigSerializer
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
            
        # Filter by research project
        research_project_filter = self.request.query_params.get('research_project', None)
        if research_project_filter:
            queryset = queryset.filter(research_project=research_project_filter)
        
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
            if 'answer_choice' in qr_data and qr_data['answer_choice'] and getattr(qr_data['answer_choice'], 'is_correct', False):
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
        
    @action(detail=True, methods=['post'], url_path='grade_response')
    def grade_response(self, request, pk=None):
        """Grade a specific response"""
        task = self.get_object()
        response_id = request.data.get('response_id')
        scores = request.data.get('scores', {})
        feedback = request.data.get('feedback', '')

        try:
            task_response = TaskResponse.objects.get(pk=response_id, task=task)
        except TaskResponse.DoesNotExist:
            return Response({'error': 'Response not found'}, status=status.HTTP_404_NOT_FOUND)

        total = 0
        for qr_id, score_val in scores.items():
            try:
                qr = QuestionResponse.objects.get(pk=int(qr_id))
                qr.score = float(score_val)
                qr.save()
                total += float(score_val)
            except (QuestionResponse.DoesNotExist, ValueError):
                continue

        task_response.total_score = total
        task_response.review_status = 'graded'
        task_response.feedback = feedback
        task_response.graded_at = datetime.now()
        task_response.graded_by = request.user
        task_response.save()

        serializer = TaskResponseSerializer(task_response)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='(?P<response_id>[^/.]+)/update_status')
    def update_response_status(self, request, response_id=None):
        """Update review status of a response"""
        new_status = request.data.get('review_status')
        feedback = request.data.get('feedback', '')

        valid_statuses = ['pending', 'received', 'under_review', 'complete', 'confirmed', 'graded']
        if new_status not in valid_statuses:
            return Response({'error': f'Invalid status. Must be one of: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            task_response = TaskResponse.objects.get(pk=response_id)
        except TaskResponse.DoesNotExist:
            return Response({'error': 'Response not found'}, status=status.HTTP_404_NOT_FOUND)

        task_response.review_status = new_status
        if feedback:
            task_response.feedback = feedback
        if new_status == 'graded':
            task_response.graded_at = datetime.now()
            task_response.graded_by = request.user
        task_response.save()

        serializer = TaskResponseSerializer(task_response)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def auto_grade(self, request, pk=None):
        """Auto-grade all responses for a task based on correct choices"""
        task = self.get_object()
        responses = TaskResponse.objects.filter(task=task)
        graded_count = 0

        for task_response in responses:
            if task_response.review_status != 'graded':
                self._auto_grade_response(task_response, task)
                graded_count += 1

        return Response({
            'message': f'Auto-graded {graded_count} responses',
            'graded_count': graded_count
        })

    def _auto_grade_response(self, task_response, task):
        """Internal helper for auto-grading a single response"""
        total = 0.0
        for qr in task_response.question_responses.all():
            if hasattr(qr, 'answer_choice') and qr.answer_choice and getattr(qr.answer_choice, 'is_correct', False):
                qr.score = float(getattr(qr.question, 'points', 1.0))
            elif hasattr(qr.question, 'question_type') and qr.question.question_type in ('radio', 'check') and hasattr(qr, 'answer_choice') and qr.answer_choice:
                qr.score = 0.0
            
            # If no actual score could be derived, ensure score holds its current value or 0
            score_val = qr.score if hasattr(qr, 'score') and qr.score is not None else 0.0
            qr.score = float(score_val)
            qr.save()
            total += float(score_val)

        task_response.total_score = total
        task_response.review_status = 'graded'
        task_response.graded_at = datetime.now()
        task_response.feedback = 'Auto-graded'
        task_response.save()

    @action(detail=True, methods=['get', 'post', 'patch'], url_path='grading_config')
    def grading_config(self, request, pk=None):
        """Get or set grading config for a task"""
        task = self.get_object()

        if request.method == 'GET':
            try:
                config = TaskGradingConfig.objects.get(task=task)
                serializer = TaskGradingConfigSerializer(config)
                return Response(serializer.data)
            except TaskGradingConfig.DoesNotExist:
                return Response({'detail': 'No grading config'}, status=status.HTTP_404_NOT_FOUND)

        # POST or PATCH
        config, created = TaskGradingConfig.objects.get_or_create(task=task)
        serializer = TaskGradingConfigSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # If scheduled grading, start background thread
            if config.auto_grade and config.scheduled_grade_at and not config.grade_immediately:
                import threading
                import time
                def _scheduled_grade(task_id, target_time):
                    while True:
                        if datetime.now() >= target_time:
                            try:
                                t = Task.objects.get(pk=task_id)
                                resps = TaskResponse.objects.filter(task=t)
                                for r in resps:
                                    if r.review_status != 'graded':
                                        self._auto_grade_response(r, t)
                            except Exception:
                                pass
                            break
                        time.sleep(30)

                t = threading.Thread(target=_scheduled_grade, args=(task.id, config.scheduled_grade_at), daemon=True)
                t.start()

            return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='ai_grade')
    def ai_grade(self, request, pk=None):
        """
        AI-powered grading for text/paragraph answers.
        Uses Gemini to compare student answers against expected answers and assign scores.
        """
        import os, json
        task = self.get_object()
        response_id = request.data.get('response_id')

        try:
            task_response = TaskResponse.objects.get(pk=response_id, task=task)
        except TaskResponse.DoesNotExist:
            return Response({'error': 'Response not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            import google.generativeai as genai
            api_key = os.environ.get('GEMINI_API_KEY', '')
            if not api_key:
                return Response({'error': 'GEMINI_API_KEY not configured on the server'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')

            total_score = 0
            grading_results = []

            for qr in task_response.question_responses.all():
                question = qr.question
                points = getattr(question, 'points', 1.0)
                # For choice-based questions, use standard auto-grade
                if hasattr(question, 'question_type') and question.question_type in ('radio', 'check'):
                    if hasattr(qr, 'answer_choice') and qr.answer_choice and getattr(qr.answer_choice, 'is_correct', False):
                        qr.score = float(points)
                    else:
                        qr.score = 0.0
                    qr.save()
                    total_score += float(qr.score)
                    grading_results.append({
                        'question': question.heading,
                        'score': qr.score,
                        'max': points,
                        'method': 'auto'
                    })
                    continue

                # For text-based questions, use AI grading
                expected = getattr(question, 'correct_answer_text', '')
                student_answer = qr.answer_text or ''

                if not student_answer.strip():
                    qr.score = 0.0
                    qr.save()
                    grading_results.append({
                        'question': question.heading,
                        'score': 0,
                        'max': points,
                        'feedback': 'No answer provided',
                        'method': 'ai'
                    })
                    continue

                prompt = f"""Grade the following student answer on a scale of 0 to {points}.
Return ONLY a JSON object with "score" (number) and "feedback" (brief explanation string).

Question: {question.heading}
{f'Expected answer: {expected}' if expected else 'No specific expected answer provided - grade based on quality and relevance.'}
Student answer: {student_answer}

JSON response:"""

                try:
                    ai_response = model.generate_content(prompt)
                    ai_text = ai_response.text.strip()
                    if ai_text.startswith('```'):
                        ai_text = ai_text.split('\n', 1)[1] if '\n' in ai_text else ai_text[3:]
                    if ai_text.endswith('```'):
                        ai_text = ai_text[:-3]
                    if ai_text.startswith('json'):
                        ai_text = ai_text[4:]

                    result = json.loads(ai_text.strip())
                    score = min(float(result.get('score', 0)), points)
                    feedback = result.get('feedback', '')
                except Exception:
                    score = 0.0
                    feedback = 'AI grading failed for this question'

                qr.score = score
                qr.save()
                total_score += score
                grading_results.append({
                    'question': question.heading,
                    'score': score,
                    'max': points,
                    'feedback': feedback,
                    'method': 'ai'
                })

            task_response.total_score = total_score
            task_response.review_status = 'graded'
            task_response.graded_at = datetime.now()
            task_response.graded_by = request.user
            task_response.feedback = 'AI-graded'
            task_response.save()

            serializer = TaskResponseSerializer(task_response)
            return Response({
                'response': serializer.data,
                'grading_details': grading_results,
                'total_score': total_score
            })

        except Exception as e:
            return Response({'error': f'AI grading failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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

    # ====== AI-POWERED ENDPOINTS ======

    @action(detail=False, methods=['post'], url_path='generate_from_document')
    def generate_from_document(self, request):
        """
        AI-powered: Upload a document (PDF, DOCX, image) and auto-generate a task with questions.
        Returns structured JSON that the frontend can use to pre-populate the CreateTask form.
        """
        import os, json
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        extracted_text = ""
        try:
            fname = file_obj.name.lower()
            if fname.endswith('.pdf'):
                import PyPDF2
                reader = PyPDF2.PdfReader(file_obj)
                for page in reader.pages:
                    extracted_text += (page.extract_text() or '') + '\n'
            elif fname.endswith('.docx'):
                from docx import Document as DocxDocument
                doc = DocxDocument(file_obj)
                for para in doc.paragraphs:
                    extracted_text += para.text + '\n'
            elif fname.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                try:
                    from PIL import Image
                    import pytesseract
                    img = Image.open(file_obj)
                    extracted_text = pytesseract.image_to_string(img)
                except Exception:
                    extracted_text = ""
            else:
                extracted_text = file_obj.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return Response({'error': f'Failed to parse file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if not extracted_text.strip():
            return Response({'error': 'Could not extract text from the uploaded file'}, status=status.HTTP_400_BAD_REQUEST)

        # Use Gemini to generate a task
        try:
            import google.generativeai as genai
            api_key = os.environ.get('GEMINI_API_KEY', '')
            if not api_key:
                return Response({'error': 'GEMINI_API_KEY not configured on the server'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')

            prompt = f"""Analyze the following document text and create a structured educational task from it.
Return a JSON object (no markdown, just raw JSON) with this exact structure:
{{
  "heading": "Task title based on the content",
  "description": "A brief description/instructions for the task",
  "category": "exam" or "test" or "survey" or "questionnaire" or "other",
  "difficulty": "beginner" or "intermediate" or "advanced",
  "questions": [
    {{
      "heading": "Question text",
      "description": "Additional question context if needed",
      "question_type": "radio" or "check" or "short_text" or "text",
      "points": 1.0,
      "correct_answer_text": "The correct answer for text questions",
      "choices": [
        {{"content": "Choice A text", "is_correct": false}},
        {{"content": "Choice B text", "is_correct": true}}
      ]
    }}
  ]
}}

Generate 5-10 good questions covering the key topics. Use "radio" for single-choice, "check" for multiple-choice, and "short_text" or "text" for open-ended. Always mark the correct choice(s) with is_correct=true. For text questions provide correct_answer_text.

DOCUMENT TEXT:
{extracted_text[:8000]}"""

            response = model.generate_content(prompt)
            response_text = response.text.strip()
            # Clean markdown code fences if present
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            if response_text.startswith('json'):
                response_text = response_text[4:]

            task_data = json.loads(response_text.strip())
            return Response(task_data, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({'error': 'AI returned invalid JSON. Please try again.', 'raw': response_text[:500]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'AI generation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='generate_questions')
    def generate_questions(self, request):
        """
        AI-powered: Generate questions from notes/text with specified difficulty and count.
        """
        import os, json
        notes_text = request.data.get('text', '')
        difficulty = request.data.get('difficulty', 'mixed')  # beginner, intermediate, advanced, mixed
        count = min(int(request.data.get('count', 5)), 20)
        question_types = request.data.get('question_types', 'mixed')  # mixed, radio, text, check

        if not notes_text.strip():
            return Response({'error': 'No text provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import google.generativeai as genai
            api_key = os.environ.get('GEMINI_API_KEY', '')
            if not api_key:
                return Response({'error': 'GEMINI_API_KEY not configured on the server'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')

            diff_instruction = f'difficulty level: {difficulty}' if difficulty != 'mixed' else 'a mix of beginner, intermediate, and advanced difficulty levels'
            type_instruction = {
                'radio': 'Use only single-choice (radio) questions.',
                'check': 'Use only multiple-choice (check) questions.',
                'text': 'Use only open-ended text questions.',
                'mixed': 'Use a mix of single-choice (radio), multiple-choice (check), and open-ended text questions.'
            }.get(question_types, 'Use a mix of question types.')

            prompt = f"""Based on the following study notes/content, generate exactly {count} educational questions.
{diff_instruction}. {type_instruction}

Return a JSON array (no markdown, just raw JSON) with this exact structure:
[
  {{
    "heading": "Question text",
    "description": "",
    "question_type": "radio" or "check" or "short_text" or "text",
    "points": 1.0,
    "correct_answer_text": "The correct answer for text-based questions",
    "choices": [
      {{"content": "Choice text", "is_correct": false}},
      {{"content": "Correct choice", "is_correct": true}}
    ]
  }}
]

Rules:
- For radio/check questions, provide 4 choices with correct one(s) marked is_correct=true
- For text/short_text questions, provide the answer in correct_answer_text and leave choices empty
- Questions should test understanding, not just recall
- Make questions progressively cover different topics from the material

CONTENT:
{notes_text[:8000]}"""

            response = model.generate_content(prompt)
            response_text = response.text.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            if response_text.startswith('json'):
                response_text = response_text[4:]

            questions = json.loads(response_text.strip())
            return Response({'questions': questions}, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            return Response({'error': 'AI returned invalid JSON. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({'error': f'AI generation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
