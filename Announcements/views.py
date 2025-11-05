from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from Announcements.models import Announcements, Text, Reply, AnnouncementsRequest, Task, Reposts, Choice, Pin, CompletedTask, FileResponse, Question, QuestionResponse, SubQuestion
from Announcements.serializers import AnnouncementsSerializer, TextSerializer, ReplySerializer, AnnouncementsRequestSerializer, ChoiceSerializer, RepostsSerializer, PinSerializer, TaskSerializer, CompletedTaskSerializer, FileResponseSerializer, QuestionSerializer, QuestionResponseSerializer, SubQuestionSerializer
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

# Create your views here.
class AnnouncementsViewSet(ModelViewSet):
    queryset = Announcements.objects.all()
    serializer_class = AnnouncementsSerializer
    filterset_fields = ['user', 'status', 'time_stamp', 'visibility']
    search_fields = ['heading', 'content']
    ordering_fields = ['time_stamp', 'status']

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

    @action(methods=['post', 'get'], detail=False)
    def expiry_sensor(self, request):
        task_serializer = TaskSerializer(data=request.data)

        if not task_serializer.is_valid():
            return Response({'error': task_serializer.error_messages}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        expiry_date = task_serializer.validated_data['due_date']
        task_id = task_serializer.validated_data['id']

        if not expiry_date:
            return Response({'error': 'The due date of the Task was not indicated'}, status=status.HTTP_404_NOT_FOUND)
        
        def _schedule_checker(task_id, target_time):
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

        checker_thread = threading.Thread(target=_schedule_checker, args=(task_id, expiry_date), daemon=True)
        checker_thread.start()

        return Response({'message': 'The task deadline has been reached'}, status=status.HTTP_202_ACCEPTED)
    

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

