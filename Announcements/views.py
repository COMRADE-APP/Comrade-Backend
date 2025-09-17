from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from Announcements.models import Announcements, Text, Reply 
from Announcements.serializers import AnnouncementsSerializer, TextSerializer, ReplySerializer
from rest_framework.decorators import action


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
    @action(detail=False, methods=['get', 'post'])
    def announcement_request(self, request):
        req_announcements = Announcements

class TextViewSet(ModelViewSet):
    queryset = Text.objects.all()
    serializer_class = TextSerializer
    filterset_fields = ['user', 'status', 'time_stamp']
    search_fields = ['content']
    ordering_fields = ['time_stamp', 'status']  
class ReplyViewSet(ModelViewSet):
    queryset = Reply.objects.all()
    serializer_class = ReplySerializer
    filterset_fields = ['user', 'status', 'time_stamp', 'reference_text']
    search_fields = ['content']
    ordering_fields = ['time_stamp', 'status']
