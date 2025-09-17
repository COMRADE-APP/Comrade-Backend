from Announcements.models import Announcements, Text, Reply
from rest_framework import serializers


class AnnouncementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcements
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']
        
class TextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Text
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']     

class ReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = Reply
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status'] 
# class TaskSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Task
#         fields = '__all__'  
#         read_only_fields = ['time_stamp', 'status']

