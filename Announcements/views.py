from django.shortcuts import render
from django.db import models as db_models
from rest_framework.viewsets import ModelViewSet
from Announcements.models import Announcements, Text, Reply, AnnouncementsRequest, Task, Reposts, Choice, Pin, CompletedTask, FileResponse, Question, QuestionResponse, SubQuestion, TaskResponse, Comment, Reaction, TaskGradingConfig
from Announcements.serializers import AnnouncementsSerializer, TextSerializer, ReplySerializer, AnnouncementsRequestSerializer, ChoiceSerializer, RepostsSerializer, PinSerializer, TaskSerializer, CompletedTaskSerializer, FileResponseSerializer, QuestionSerializer, QuestionResponseSerializer, SubQuestionSerializer, TaskResponseSerializer, CommentSerializer, ReactionSerializer, TaskGradingConfigSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
import threading
import time
from datetime import datetime as _datetime
from Announcements.models import Announcements as _Announcements
from django.contrib.sessions.models import Session
from django.utils import timezone
from Rooms.models import Room

# Create your views here.
class AnnouncementsViewSet(ModelViewSet):
    queryset = Announcements.objects.all()
    serializer_class = AnnouncementsSerializer
    filterset_fields = ['user', 'status', 'time_stamp', 'visibility']
    search_fields = ['heading', 'content']
    ordering_fields = ['time_stamp', 'status']

    def perform_create(self, serializer):
        """Create announcement and optionally link to a room"""
        instance = serializer.save(user=self.request.user)
        
        # Check if room parameter was provided
        room_id = self.request.data.get('room')
        if room_id:
            try:
                room = Room.objects.get(pk=room_id)
                room.announcements.add(instance)
            except Room.DoesNotExist:
                pass  # Silently ignore invalid room ID

    @action(detail=False, methods=['get', 'post'])
    def recent_announcements(self, request):
        recent_announcements = Announcements.objects.filter(status='sent').order_by('-time_stamp')[:10]
        serializer = self.get_serializer(recent_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])
    def scheduled_announcements(self, request):
        scheduled_announcements = Announcements.objects.filter(status='scheduled').order_by('time_stamp')
        serializer = self.get_serializer(scheduled_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])
    def pending_announcements(self, request):
        pending_announcements = Announcements.objects.filter(status='pending').order_by('time_stamp')
        serializer = self.get_serializer(pending_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])      
    def not_sent_announcements(self, request):
        not_sent_announcements = Announcements.objects.filter(status='not_sent').order_by('time_stamp')
        serializer = self.get_serializer(not_sent_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def private_announcements(self, request):   
        private_announcements = Announcements.objects.filter(visibility='private').order_by('-time_stamp')
        serializer = self.get_serializer(private_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def only_me_announcements(self, request):   
        only_me_announcements = Announcements.objects.filter(visibility='only_me').order_by('-time_stamp')
        serializer = self.get_serializer(only_me_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def public_announcements(self, request):
        public_announcements = Announcements.objects.filter(visibility='public').order_by('-time_stamp')
        serializer = self.get_serializer(public_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def institutional_announcements(self, request): 
        institutional_announcements = Announcements.objects.filter(visibility='institutional').order_by('-time_stamp')
        serializer = self.get_serializer(institutional_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def organisational_announcements(self, request):    
        organisational_announcements = Announcements.objects.filter(visibility='organisational').order_by('-time_stamp')
        serializer = self.get_serializer(organisational_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def group_announcements(self, request):    
        group_announcements = Announcements.objects.filter(visibility='group').order_by('-time_stamp')
        serializer = self.get_serializer(group_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])
    def course_announcements(self, request):    
        course_announcements = Announcements.objects.filter(visibility='course').order_by('-time_stamp')
        serializer = self.get_serializer(course_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def faculty_announcements(self, request):    
        faculty_announcements = Announcements.objects.filter(visibility='faculty').order_by('-time_stamp')
        serializer = self.get_serializer(faculty_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])  
    def year_announcements(self, request):    
        year_announcements = Announcements.objects.filter(visibility='year').order_by('-time_stamp')
        serializer = self.get_serializer(year_announcements, many=True)
        return Response(serializer.data)
    @action(detail=False, methods=['get', 'post'])
    def semester_announcements(self, request):    
        semester_announcements = Announcements.objects.filter(visibility='semester').order_by('-time_stamp')
        serializer = self.get_serializer(semester_announcements, many=True)
        return Response(serializer.data)
    
    # # Requesting an announcement from the student to the admin
    @action(detail=False, methods=['get', 'post'])
    def verify_announcements(self, request):
        req_announcements = AnnouncementsRequestSerializer(data=request.data)
        status_req = 'approved'

        if not req_announcements.is_valid():
            return Response({'error': req_announcements.errors}, status=status.HTTP_404_NOT_FOUND)
        
        req_announcements.validated_data['verification_status'] = status_req
        req_announcements.save()

        user = req_announcements.validated_data['verified_by']
        heading = req_announcements.validated_data['heading']
        content = req_announcements.validated_data['content']
        visibility = req_announcements.validated_data['visibility']

        if user and heading and content and visibility:
            ann_new = Announcements.objects.create(user=user, heading=heading, content=content, visibility=visibility, status='sent')
            ann_new.save()
            return Response({'message': 'Announcement request approved and announcement created successfully.'}, status=status.HTTP_201_CREATED)
        return Response({'error': 'Failed to create announcement from request.'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get', 'post'])
    def reject_announcements(self, request):
        req_announcements = AnnouncementsRequestSerializer(data=request.data)
        status_req = 'rejected'

        if not req_announcements.is_valid():
            return Response({'error': req_announcements.errors}, status=status.HTTP_404_NOT_FOUND)
        
        req_announcements.validated_data['verification_status'] = status_req
        req_announcements.save()

        return Response({'message': 'Announcement request rejected successfully.'}, status=status.HTTP_200_OK)
    @action(detail=False, methods=['get', 'post'])
    def schedule_announcement(self, request):
        announcement_data = AnnouncementsSerializer(data=request.data)

        if not announcement_data.is_valid():
            return Response({'error': announcement_data.errors}, status=status.HTTP_404_NOT_FOUND)
        
        announcement_data.validated_data['send_status'] = 'scheduled'
        scheduled_time = announcement_data.validated_data.get('schedule_time')

        if not scheduled_time:
            return Response({'error': 'No schedule_time provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # save the scheduled announcement first
        announcement_instance = announcement_data.save()

        # run a background thread that checks every second whether the scheduled time has arrived

        def _schedule_checker(ann_id, target_time):
            try:
                while True:
                    now = _datetime.now()
                    if now >= target_time:
                        try:
                            ann = _Announcements.objects.get(pk=ann_id)
                            ann.send_status = 'sent'
                            ann.time_stamp = now
                            ann.status = 'sent'
                            ann.save()
                        except _Announcements.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = threading.Thread(target=_schedule_checker, args=(announcement_instance.id, scheduled_time), daemon=True)
        checker_thread.start()

        return Response({'message': 'Announcement scheduled successfully.', 'announcement': announcement_data.data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get', 'post'])
    def set_announcement_expiry(self, request):
        ann_id = request.data.get('announcement_id')
        expiry_time = request.data.get('expiry_time')

        if not ann_id or not expiry_time:
            return Response({'error': 'announcement_id and expiry_time are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            announcement = Announcements.objects.get(pk=ann_id)
        except Announcements.DoesNotExist:
            return Response({'error': 'Announcement not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        def _expiry_checker(ann_instance, target_time):
            try:
                while True:
                    now = _datetime.now()
                    if now >= target_time:
                        ann_instance.send_status = 'not_sent'
                        ann_instance.save()
                        break
                    time.sleep(1)
            except Exception:
                return

        expiry_thread = threading.Thread(target=_expiry_checker, args=(announcement, expiry_time), daemon=True)
        expiry_thread.start()

        return Response({'message': 'Announcement expiry set successfully.'}, status=status.HTTP_200_OK)
    
    @ action(detail=False, methods=['get', 'post'])
    def deactivate_announcement(self, request):
        ann_id = request.data.get('announcement_id')

        if not ann_id:
            return Response({'error': 'announcement_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            announcement = Announcements.objects.get(pk=ann_id)
        except Announcements.DoesNotExist:
            return Response({'error': 'Announcement not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        announcement.send_status = 'not_sent'
        announcement.save()

        return Response({'message': 'Announcement deactivated successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get', 'post'])
    def online_to_sms_sensor(self, request):
        ann_id = request.data.get('announcement_id')
        notice_minutes = request.data.get('notice_minutes')  # expected integer minutes

        if not ann_id or notice_minutes is None:
            return Response({'error': 'announcement_id and notice_minutes are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notice_minutes = int(notice_minutes)
            if notice_minutes < 0:
                raise ValueError()
        except Exception:
            return Response({'error': 'notice_minutes must be a non-negative integer.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            announcement = Announcements.objects.get(pk=ann_id)
        except Announcements.DoesNotExist:
            return Response({'error': 'Announcement not found.'}, status=status.HTTP_404_NOT_FOUND)

        # try common phone fields on the user object
        phone = getattr(announcement.user, 'phone', None) or getattr(announcement.user, 'phone_number', None)
        if not phone:
            return Response({'error': 'No phone number found for announcement user.'}, status=status.HTTP_400_BAD_REQUEST)

        # If the user currently has an active session on the platform, do not trigger the sensor.
        try:

            sessions = Session.objects.filter(expire_date__gte=timezone.now())
            for s in sessions:
                try:
                    data = s.get_decoded()
                except Exception:
                    continue
                if str(data.get('_auth_user_id')) == str(getattr(announcement.user, 'id', None)):
                    return Response({'message': 'User currently active on platform; SMS sensor not triggered.'}, status=status.HTTP_200_OK)
        except Exception:
            # if session-checking fails for any reason, fall back to scheduling SMS as before
            pass

        def send_sms(phone_number, message):
            # TODO: API REPLACEMENT - replace this placeholder with real SMS provider integration (Twilio, Nexmo, etc.)
            try:
                # Example placeholder: log/print the SMS
                print(f"[SMS] To: {phone_number} -- {message}")
            except Exception:
                # Do not raise from background sender
                return

        def _sms_checker(ann_id_local, delay_minutes):
            try:
                target_ts = time.time() + delay_minutes * 60
                # check every minute until target reached
                while True:
                    if time.time() >= target_ts:
                        try:
                            ann = Announcements.objects.get(pk=ann_id_local)
                            phone_local = getattr(ann.user, 'phone', None) or getattr(ann.user, 'phone_number', None)
                            if phone_local:
                                # Check if user has an active session
                                sessions = Session.objects.filter(expire_date__gte=timezone.now())
                                user_active = any(str(data.get('_auth_user_id')) == str(ann.user.id) for s in sessions for data in [s.get_decoded()])

                                if user_active:
                                    return  # Deactivate the sensor if user is active

                                heading = getattr(ann, 'heading', '') or ''
                                content = getattr(ann, 'content', '') or ''
                                message = f"{heading}\n{content}".strip()
                                send_sms(phone_local, message)
                                ann.send_status = 'sent'
                                ann.read_status = True
                                ann.time_stamp = _datetime.now()
                                ann.save()
                        except Announcements.DoesNotExist:
                            # nothing to do if announcement was removed
                            pass
                    break
                time.sleep(60)
            except Exception:
                return

        # start background checker thread (daemon so it won't block shutdown)
        checker_thread = threading.Thread(target=_sms_checker, args=(announcement.id, notice_minutes), daemon=True)
        checker_thread.start()

        return Response({'message': f'Announcement will be sent as SMS in {notice_minutes} minute(s).'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        announcement = self.get_object()
        user = request.user
        reaction_type = request.data.get('reaction_type', 'like')

        # Check if already reacted
        existing_reaction = Reaction.objects.filter(user=user, announcement=announcement, reaction_type=reaction_type).first()
        
        if existing_reaction:
            # Toggle reaction off
            existing_reaction.delete()
            return Response({'message': 'Reaction removed'}, status=status.HTTP_200_OK)
        else:
            # Add reaction
            Reaction.objects.create(user=user, announcement=announcement, reaction_type=reaction_type)
            return Response({'message': 'Reaction added'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        announcement = self.get_object()
        announcement.views += 1
        announcement.save(update_fields=['views'])
        return Response({'message': 'View recorded', 'views': announcement.views}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        announcement = self.get_object()
        if request.method == 'GET':
            comments = Comment.objects.filter(announcement=announcement).order_by('-time_stamp')
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif request.method == 'POST':
            content = request.data.get('content', '').strip()
            if not content:
                return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
            comment = Comment.objects.create(
                user=request.user,
                announcement=announcement,
                content=content,
            )
            serializer = CommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    # @action(detail=False, methods=['post', 'get'])
    # def repost_announcement(self, request):
    #     repost_serializer = RepostsSerializer(data=request.data)
        
    #     if repost_serializer.is_valid():
    #         repost_serializer.save()
    #         return Response({'message': 'Announcement reposted successfully✅'}, status=status.HTTP_201_CREATED)
    #     else:
    #         return Response({'error': repost_serializer.error_messages}, status=status.HTTP_403_FORBIDDEN)
        
        


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['content']
    ordering_fields = ['time_stamp', 'status']  

    def perform_create(self, serializer):
        """Create task and optionally link to a room"""
        instance = serializer.save(user=self.request.user)
        
        # Check if room parameter was provided
        room_id = self.request.data.get('room')
        if room_id:
            try:
                from Rooms.models import Room
                room = Room.objects.get(pk=room_id)
                room.tasks.add(instance)
            except Exception:
                pass  # Silently ignore invalid room ID

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        task = self.get_object()
        user = request.user
        reaction_type = request.data.get('reaction_type', 'like')

        existing_reaction = Reaction.objects.filter(user=user, task=task, reaction_type=reaction_type).first()
        
        if existing_reaction:
            existing_reaction.delete()
            return Response({'message': 'Reaction removed'}, status=status.HTTP_200_OK)
        else:
            Reaction.objects.create(user=user, task=task, reaction_type=reaction_type)
            return Response({'message': 'Reaction added'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        task = self.get_object()
        user = request.user
        
        if user.is_authenticated:
            existing_view = Reaction.objects.filter(user=user, task=task, reaction_type='view').exists()
            if not existing_view:
                Reaction.objects.create(user=user, task=task, reaction_type='view')
                # Assuming tasks don't have a view column natively yet, we can skip incrementing a direct field 
                # or we just rely on the Reaction table. Let's return success.
        
        return Response({'message': 'View recorded'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        # Placeholder for reporting tasks, could integrate with a Report model later
        return Response({'message': 'Task reported successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        # Placeholder for blocking this creator/task type
        return Response({'message': 'Task source blocked/marked not interested'}, status=status.HTTP_200_OK)

    @action(methods=['post', 'get'], detail=False)
    def set_expiry_duration(self, request):
        task_serializer = TaskSerializer(data=request.data)

        if not task_serializer.is_valid():
            return Response({'error': task_serializer.error_messages}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        expiry_date = task_serializer.validated_data['due_date']
        task_id = task_serializer.validated_data['id']

        if not expiry_date:
            return Response({'error': 'The due date of the Task was not indicated'}, status=status.HTTP_404_NOT_FOUND)
        
        def _expiry_sensor(task_id, target_time):
            try:
                while True:
                    now = _datetime.now()
                    if now >= target_time:
                        try:
                            task = Task.objects.get(pk=task_id)
                            task.state = 'expired'
                            task.time_stamp = now
                            task.status = 'sent'
                            task.save()
                        except Task.DoesNotExist:
                            pass
                    break
                time.sleep(1)
            except Exception:
                # fail silently for background checker
                return

        checker_thread = threading.Thread(target=_expiry_sensor, args=(task_id, expiry_date), daemon=True)
        checker_thread.start()

        return Response({'message': 'The task deadline has been reached'}, status=status.HTTP_202_ACCEPTED)

    # ====== RESPONSE MANAGEMENT ======

    @action(detail=True, methods=['get'])
    def responses(self, request, pk=None):
        """List all responses for a task"""
        task = self.get_object()
        responses = TaskResponse.objects.filter(task=task).order_by('-time_stamp')
        serializer = TaskResponseSerializer(responses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def my_response(self, request, pk=None):
        """Get current user's response for a task"""
        task = self.get_object()
        response = TaskResponse.objects.filter(task=task, user=request.user).first()
        if response:
            serializer = TaskResponseSerializer(response)
            return Response(serializer.data)
        return Response({'detail': 'No response found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def my_created_submissions(self, request):
        """List tasks created by the user that have received responses"""
        my_tasks = Task.objects.filter(user=request.user)
        tasks_with_responses = []
        for task in my_tasks:
            resp_count = TaskResponse.objects.filter(task=task).count()
            if resp_count > 0:
                graded_count = TaskResponse.objects.filter(task=task, review_status='graded').count()
                pending_count = resp_count - graded_count
                task_data = TaskSerializer(task).data
                task_data['response_count'] = resp_count
                task_data['graded_count'] = graded_count
                task_data['pending_count'] = pending_count
                tasks_with_responses.append(task_data)
        return Response(tasks_with_responses)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit answers for a task"""
        task = self.get_object()
        user = request.user
        responses_data = request.data.get('responses', [])

        # Check if already submitted
        existing = TaskResponse.objects.filter(task=task, user=user).first()
        if existing:
            return Response({'error': 'You have already submitted a response for this task'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the main TaskResponse
        task_response = TaskResponse.objects.create(
            user=user,
            task=task,
            review_status='received'
        )

        total_score = 0
        for resp in responses_data:
            question_id = resp.get('question_id')
            answer_text = resp.get('answer_text', '')
            answer_choice_id = resp.get('answer_choice_id')

            try:
                question = Question.objects.get(pk=question_id)
            except Question.DoesNotExist:
                continue

            qr = QuestionResponse.objects.create(
                user=user,
                task=task,
                question=question,
                answer_text=answer_text,
            )

            if answer_choice_id:
                try:
                    choice = Choice.objects.get(pk=answer_choice_id)
                    qr.answer_choice = choice
                    if choice.is_correct:
                        qr.score = 1.0
                        total_score += 1
                    qr.save()
                except Choice.DoesNotExist:
                    pass

            task_response.question_responses.add(qr)

        task_response.total_score = total_score
        task_response.save()

        # Check auto-grade config
        try:
            config = TaskGradingConfig.objects.get(task=task)
            if config.auto_grade and config.grade_immediately:
                self._auto_grade_response(task_response, task)
        except TaskGradingConfig.DoesNotExist:
            pass

        serializer = TaskResponseSerializer(task_response)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        task_response.graded_at = _datetime.now()
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
            task_response.graded_at = _datetime.now()
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
        total = 0
        for qr in task_response.question_responses.all():
            if qr.answer_choice and qr.answer_choice.is_correct:
                qr.score = 1.0
                total += 1
            elif qr.question.question_type in ('radio', 'check') and qr.answer_choice:
                qr.score = 0.0
            qr.save()

        task_response.total_score = total
        task_response.review_status = 'graded'
        task_response.graded_at = _datetime.now()
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
                def _scheduled_grade(task_id, target_time):
                    while True:
                        if _datetime.now() >= target_time:
                            try:
                                t = Task.objects.get(pk=task_id)
                                resps = TaskResponse.objects.filter(task=t)
                                for r in resps:
                                    if r.review_status != 'graded':
                                        total = 0
                                        for qr in r.question_responses.all():
                                            if qr.answer_choice and qr.answer_choice.is_correct:
                                                qr.score = 1.0
                                                total += 1
                                            qr.save()
                                        r.total_score = total
                                        r.review_status = 'graded'
                                        r.graded_at = _datetime.now()
                                        r.feedback = 'Auto-graded (scheduled)'
                                        r.save()
                            except Exception:
                                pass
                            break
                        time.sleep(30)

                t = threading.Thread(target=_scheduled_grade, args=(task.id, config.scheduled_grade_at), daemon=True)
                t.start()

            return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='save_draft')
    def save_draft(self, request, pk=None):
        """Save draft answers"""
        task = self.get_object()
        user = request.user
        responses_data = request.data.get('responses', [])

        # Get or create a draft response
        task_response, created = TaskResponse.objects.get_or_create(
            task=task, user=user,
            defaults={'review_status': 'pending'}
        )

        for resp in responses_data:
            question_id = resp.get('question_id')
            answer_text = resp.get('answer_text', '')
            answer_choice_id = resp.get('answer_choice_id')

            try:
                question = Question.objects.get(pk=question_id)
            except Question.DoesNotExist:
                continue

            qr, _ = QuestionResponse.objects.get_or_create(
                user=user, task=task, question=question,
                defaults={'answer_text': answer_text}
            )
            qr.answer_text = answer_text
            if answer_choice_id:
                try:
                    qr.answer_choice = Choice.objects.get(pk=answer_choice_id)
                except Choice.DoesNotExist:
                    pass
            qr.save()
            task_response.question_responses.add(qr)

        task_response.save()
        return Response({'message': 'Draft saved'})

    @action(detail=True, methods=['get'])
    def task_settings(self, request, pk=None):
        """Get task settings"""
        task = self.get_object()
        from Announcements.models import TaskSettings
        settings, created = TaskSettings.objects.get_or_create(task=task)
        from Announcements.serializers import TaskSerializer
        return Response({
            'timer_enabled': settings.timer_enabled,
            'timer_duration': str(settings.timer_duration) if settings.timer_duration else None,
            'no_tab_leaving': settings.no_tab_leaving,
            'auto_submit_on_tab_change': settings.auto_submit_on_tab_change,
            'max_tab_switches': settings.max_tab_switches,
            'auto_save': settings.auto_save,
            'one_take': settings.one_take,
            'max_attempts': settings.max_attempts,
            'accept_late_submissions': settings.accept_late_submissions,
            'record_video': settings.record_video,
            'shuffle_questions': settings.shuffle_questions,
            'show_results_immediately': settings.show_results_immediately,
            'questions_per_page': settings.questions_per_page,
            'passing_score': settings.passing_score,
        })

    @action(detail=True, methods=['post'])
    def record_access(self, request, pk=None):
        """Record analytics access"""
        task = self.get_object()
        from Announcements.models import TaskAnalytics
        TaskAnalytics.objects.create(
            task=task, user=request.user, action='access'
        )
        return Response({'message': 'Access recorded'})

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get task analytics"""
        task = self.get_object()
        from Announcements.models import TaskAnalytics
        data = TaskAnalytics.objects.filter(task=task).values('action').annotate(
            count=db_models.Count('id')
        )
        return Response(list(data))

    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """Get or add comments for a task"""
        task = self.get_object()
        if request.method == 'GET':
            comments = Comment.objects.filter(task=task).order_by('-time_stamp')
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        elif request.method == 'POST':
            content = request.data.get('content', '').strip()
            if not content:
                return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
            comment = Comment.objects.create(user=request.user, task=task, content=content)
            serializer = CommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Get all submissions for task"""
        task = self.get_object()
        submissions = TaskResponse.objects.filter(task=task).order_by('-time_stamp')
        serializer = TaskResponseSerializer(submissions, many=True)
        return Response(serializer.data)

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
                # For choice-based questions, use standard auto-grade
                if question.question_type in ('radio', 'check'):
                    if qr.answer_choice and qr.answer_choice.is_correct:
                        qr.score = question.points
                    else:
                        qr.score = 0.0
                    qr.save()
                    total_score += qr.score
                    grading_results.append({
                        'question': question.heading,
                        'score': qr.score,
                        'max': question.points,
                        'method': 'auto'
                    })
                    continue

                # For text-based questions, use AI grading
                expected = question.correct_answer_text or ''
                student_answer = qr.answer_text or ''

                if not student_answer.strip():
                    qr.score = 0.0
                    qr.save()
                    grading_results.append({
                        'question': question.heading,
                        'score': 0,
                        'max': question.points,
                        'feedback': 'No answer provided',
                        'method': 'ai'
                    })
                    continue

                prompt = f"""Grade the following student answer on a scale of 0 to {question.points}.
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
                    score = min(float(result.get('score', 0)), question.points)
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
                    'max': question.points,
                    'feedback': feedback,
                    'method': 'ai'
                })

            task_response.total_score = total_score
            task_response.review_status = 'graded'
            task_response.graded_at = _datetime.now()
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



class QuestionViewSet(ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['description']
    ordering_fields = ['time_stamp', 'status']

class ChoiceViewSet(ModelViewSet):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['content']
    ordering_fields = ['time_stamp', 'status']

class FileResponseViewSet(ModelViewSet):
    queryset = FileResponse.objects.all()
    serializer_class = FileResponseSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['task']
    ordering_fields = ['time_stamp', 'status']

class CompletedTaskViewSet(ModelViewSet):
    queryset = CompletedTask.objects.all()
    serializer_class = CompletedTaskSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['task']
    ordering_fields = ['time_stamp', 'status']

class QuestionResponseViewSet(ModelViewSet):
    queryset = QuestionResponse.objects.all()
    serializer_class = QuestionResponseSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['description']
    ordering_fields = ['time_stamp', 'status']

class SubQuestionViewSet(ModelViewSet):
    queryset = SubQuestion.objects.all()
    serializer_class = SubQuestionSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['description']
    ordering_fields = ['time_stamp', 'status']

"""Task methods are next"""

# TODO: create (CRUD)announcements
# Convert text to announcement or reply as well ✅ 
# Convert task into an announcement ✅
# Change visibity of announcements
# Schedule announcements that automatically posts when time is due
# Set expiring announcements
# Deactivate announcements
# Allow announcements creation permissions for other memebers


class TextViewSet(ModelViewSet):
    queryset = Text.objects.all()
    serializer_class = TextSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['content']
    ordering_fields = ['time_stamp', 'status']  

    # Convert text to announcement or reply as well 
    @action(detail=True, methods=['post'])
    def convert_to_announcement(self, request, pk=None):
        text_instance = self.get_object()
        announcement_data = {
            'user': text_instance.user.studentadmin,
            'heading': 'Announcement from Text ID {}'.format(text_instance.id),
            'content': text_instance.content,
            'visibility': 'private',
            'status': 'pending'
        }
        announcement_serializer = AnnouncementsSerializer(data=announcement_data)
        if announcement_serializer.is_valid():
            announcement_serializer.save()
            return Response({'message': 'Text converted to announcement successfully.', 'announcement': announcement_serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'error': announcement_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class ReplyViewSet(ModelViewSet):
    queryset = Reply.objects.all()
    serializer_class = ReplySerializer
    filterset_fields = ['user', 'status', 'time_stamp', 'reference_text']
    search_fields = ['content']
    ordering_fields = ['time_stamp', 'status']

class RepostsViewSet(ModelViewSet):
    queryset = Reposts.objects.all()
    serializer_class = RepostsSerializer
    filterset_fields = ['user', 'status', 'time_stamp', 'caption']
    search_fields = ['caption']
    ordering_fields = ['time_stamp', 'status']

class PinViewSet(ModelViewSet):
    queryset = Pin.objects.all()
    serializer_class = PinSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['task']
    ordering_fields = ['time_stamp', 'status']

class TaskResponseViewSet(ModelViewSet):
    queryset = TaskResponse.objects.all()
    serializer_class = TaskResponseSerializer
    filterset_fields = ['user', 'task', 'review_status']
    search_fields = ['task__heading', 'user__email']
    ordering_fields = ['time_stamp', 'review_status']

class CommentViewSet(ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    filterset_fields = ['user', 'time_stamp', 'announcement']
    search_fields = ['content']
    ordering_fields = ['time_stamp', 'highlight_order']

    @action(detail=True, methods=['post'])
    def highlight(self, request, pk=None):
        comment = self.get_object()
        # Verify the user requesting the highlight is the creator of the announcement
        # or has moderation permissions (for simplicity, assumed creator check here)
        if comment.announcement and request.user != comment.announcement.user:
            return Response({'error': 'Only the creator of the announcement can highlight comments.'}, status=status.HTTP_403_FORBIDDEN)
            
        highlight_order = request.data.get('highlight_order')
        
        if highlight_order is not None:
            try:
                order = int(highlight_order)
                if order < 1 or order > 6:
                    return Response({'error': 'Highlight order must be between 1 and 6.'}, status=status.HTTP_400_BAD_REQUEST)
                # Check for existing comment with this order on the same announcement
                if comment.announcement:
                    existing = Comment.objects.filter(announcement=comment.announcement, highlight_order=order).first()
                    if existing and existing.id != comment.id:
                        # Clear the other comment's order to swap
                        existing.highlight_order = None
                        existing.save()
            except ValueError:
                return Response({'error': 'Highlight order must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            order = None

        comment.highlight_order = order
        comment.save()

        return Response({'message': 'Comment highlight updated successfully.', 'highlight_order': comment.highlight_order}, status=status.HTTP_200_OK)

class ReactionViewSet(ModelViewSet):
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    filterset_fields = ['user', 'time_stamp']
    search_fields = ['text']
    ordering_fields = ['time_stamp']