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
    TaskResponse,
    TaskSettings,
    TaskAnalytics,
    TaskGradingConfig
)
from Authentication.serializers import CustomUserSerializer


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'content', 'is_correct', 'selected', 'time_stamp']
        read_only_fields = ['time_stamp']


class TaskGradingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskGradingConfig
        fields = '__all__'
        read_only_fields = ['id', 'task', 'time_stamp']


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
    settings = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['id', 'user', 'heading', 'description', 'visibility', 
                  'status', 'state', 'category', 'difficulty', 'is_activity', 'start_date', 'due_date',
                  'time_stamp', 'questions', 'question_count', 'response_count',
                  'settings', 'institution', 'organisation', 'research_project']
        read_only_fields = ['time_stamp', 'user']
    
    def get_question_count(self, obj):
        return Question.objects.filter(task=obj).count()
    
    def get_response_count(self, obj):
        return TaskResponse.objects.filter(task=obj).count()
    
    def get_settings(self, obj):
        try:
            return TaskSettingsSerializer(obj.settings).data
        except TaskSettings.DoesNotExist:
            return None


class TaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tasks with questions and settings"""
    questions = serializers.ListField(child=serializers.DictField(), required=False, write_only=True)
    settings = serializers.DictField(required=False, write_only=True)
    
    class Meta:
        model = Task
        fields = ['heading', 'description', 'visibility', 'category', 'difficulty',
                  'is_activity', 'start_date', 'due_date', 'questions', 'settings', 'institution', 'organisation', 'research_project']
    
    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        settings_data = validated_data.pop('settings', {})
        task = Task.objects.create(**validated_data)
        
        for idx, q_data in enumerate(questions_data):
            choices_data = q_data.pop('choices', [])
            q_data.pop('subquestions', None)  # Remove read-only field if sent
            q_data['position'] = q_data.get('position', idx + 1)
            question = Question.objects.create(task=task, **q_data)
            
            for choice_data in choices_data:
                choice_data.pop('id', None)
                choice_data.pop('time_stamp', None)
                Choice.objects.create(question=question, **choice_data)
        
        # Create settings
        if settings_data:
            TaskSettings.objects.create(task=task, **settings_data)
        else:
            TaskSettings.objects.create(task=task)  # Create with defaults
        
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
    task = TaskSerializer(read_only=True)
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


class TaskSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSettings
        fields = [
            'id', 'task', 'timer_enabled', 'timer_duration',
            'no_tab_leaving', 'auto_submit_on_tab_change', 'max_tab_switches',
            'auto_save', 'one_take', 'max_attempts', 'accept_late_submissions',
            'record_video', 'shuffle_questions', 'show_results_immediately',
            'questions_per_page', 'passing_score', 'time_stamp'
        ]
        read_only_fields = ['id', 'task', 'time_stamp']


class TaskAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAnalytics
        fields = ['id', 'task', 'user', 'action', 'metadata', 'created_at']
        read_only_fields = ['id', 'created_at']

