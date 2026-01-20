# Task/serializers.py
from rest_framework import serializers
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
from Authentication.serializers import CustomUserSerializer


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'content', 'is_correct', 'selected', 'time_stamp']
        read_only_fields = ['time_stamp']


class SubQuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True, source='choice_set')
    
    class Meta:
        model = SubQuestion
        fields = ['id', 'heading', 'position', 'description', 'question_type', 'choices', 'time_stamp']
        read_only_fields = ['time_stamp']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True, source='choice_set')
    subquestions = SubQuestionSerializer(many=True, read_only=True, source='subquestion_set')
    
    class Meta:
        model = Question
        fields = ['id', 'heading', 'position', 'description', 'question_type', 
                  'has_subquestion', 'choices', 'subquestions', 'time_stamp']
        read_only_fields = ['time_stamp']


class TaskSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True, source='question_set')
    question_count = serializers.SerializerMethodField()
    response_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['id', 'user', 'heading', 'description', 'visibility', 
                  'status', 'state', 'due_date', 'time_stamp', 'questions',
                  'question_count', 'response_count']
        read_only_fields = ['time_stamp', 'user']
    
    def get_question_count(self, obj):
        return Question.objects.filter(task=obj).count()
    
    def get_response_count(self, obj):
        return TaskResponse.objects.filter(task=obj).count()


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks with questions"""
    questions = QuestionSerializer(many=True, required=False)
    
    class Meta:
        model = Task
        fields = ['heading', 'description', 'visibility', 'due_date', 'questions']
    
    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        task = Task.objects.create(**validated_data)
        
        for q_data in questions_data:
            choices_data = q_data.pop('choices', [])
            question = Question.objects.create(task=task, **q_data)
            
            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)
        
        return task


class QuestionResponseSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = QuestionResponse
        fields = ['id', 'user', 'task', 'question', 'sub_question', 
                  'answer_text', 'answer_choice', 'answer_file', 'score', 
                  'time_stamp', 'status']
        read_only_fields = ['time_stamp', 'user', 'score']


class TaskResponseSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    question_responses = QuestionResponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = TaskResponse
        fields = ['id', 'user', 'task', 'question_responses', 
                  'total_score', 'time_stamp', 'status']
        read_only_fields = ['time_stamp', 'user', 'total_score']


class TaskSubmissionSerializer(serializers.Serializer):
    """Serializer for submitting task responses"""
    task_id = serializers.IntegerField()
    responses = serializers.ListField(
        child=serializers.DictField()
    )
    
    def validate_task_id(self, value):
        if not Task.objects.filter(id=value).exists():
            raise serializers.ValidationError("Task not found")
        return value


class CompletedTaskSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    task = TaskSerializer(read_only=True)
    
    class Meta:
        model = CompletedTask
        fields = ['id', 'user', 'task', 'is_completed', 'completed_on', 'status']
        read_only_fields = ['completed_on', 'user']


class FileResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileResponse
        fields = ['id', 'question', 'sub_question', 'position', 'description', 'content', 'time_stamp']
        read_only_fields = ['time_stamp']
