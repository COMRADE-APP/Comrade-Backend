from Announcements.models import Announcements, Text, Reply, AnnouncementsRequest, Task, Reposts, Choice, Pin, CompletedTask, FileResponse, Question, QuestionResponse, SubQuestion, TaskResponse, Reaction, Comment
from rest_framework import serializers


class AnnouncementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcements
        fields = '__all__'  
        read_only_fields = ['user', 'time_stamp', 'status']
        
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
class AnnouncementsRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementsRequest
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']
    # def validate(self, data):
        
    #     return data

class RepostsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reposts
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']

class PinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pin
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']

class CompletedTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompletedTask
        fields = '__all__'  
        read_only_fields = ['completed_on']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'  
        read_only_fields = ['timestamp']

class SubQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubQuestion
        fields = '__all__'  
        read_only_fields = ['timestamp']
    
class QuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionResponse
        fields = '__all__'  
        read_only_fields = ['timestamp']

class FileResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileResponse
        fields = '__all__'  
        read_only_fields = ['timestamp']

class TaskResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskResponse
        fields = '__all__'  
        read_only_fields = ['timestamp']

class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = '__all__'  
        read_only_fields = ['time_stamp']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'  
        read_only_fields = ['time_stamp']