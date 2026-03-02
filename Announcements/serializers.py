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

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False, source='choice_set')
    class Meta:
        model = Question
        fields = '__all__'  
        read_only_fields = ['time_stamp']

class TaskSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False, source='question_set')
    class Meta:
        model = Task
        fields = '__all__'  
        read_only_fields = ['time_stamp', 'status']

    def create(self, validated_data):
        questions_data = validated_data.pop('question_set', [])
        task = Task.objects.create(**validated_data)
        for q_data in questions_data:
            choices_data = q_data.pop('choice_set', [])
            question = Question.objects.create(task=task, **q_data)
            for c_data in choices_data:
                Choice.objects.create(question=question, **c_data)
        return task

class RepostsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reposts
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
    user_name = serializers.SerializerMethodField()
    class Meta:
        model = Comment
        fields = '__all__'  
        read_only_fields = ['time_stamp']
    
    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return 'Anonymous'