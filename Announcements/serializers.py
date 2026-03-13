from Announcements.models import Announcements, Text, Reply, AnnouncementsRequest, Task, Reposts, Choice, Pin, CompletedTask, FileResponse, Question, QuestionResponse, SubQuestion, TaskResponse, Reaction, Comment, TaskGradingConfig
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
    question_detail = QuestionSerializer(source='question', read_only=True)
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
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    task_detail = TaskSerializer(source='task', read_only=True)
    question_responses_detail = QuestionResponseSerializer(source='question_responses', many=True, read_only=True)

    class Meta:
        model = TaskResponse
        fields = '__all__'  
        read_only_fields = ['time_stamp']

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return 'Anonymous'

    def get_user_email(self, obj):
        return obj.user.email if obj.user else ''

    def get_user_avatar(self, obj):
        try:
            from Authentication.models import Profile
            profile = Profile.objects.filter(user=obj.user).first()
            if profile and profile.profile_picture:
                return profile.profile_picture.url
        except Exception:
            pass
        return None


class TaskGradingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskGradingConfig
        fields = '__all__'
        read_only_fields = ['created_at']

class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reaction
        fields = '__all__'  
        read_only_fields = ['time_stamp']

class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_disliked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = '__all__'  
        read_only_fields = ['time_stamp']
    
    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return 'Anonymous'

    def get_user_avatar(self, obj):
        try:
            from Authentication.models import Profile
            profile = Profile.objects.filter(user=obj.user).first()
            if profile and profile.profile_picture:
                return profile.profile_picture.url
        except Exception:
            pass
        return None

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_dislikes_count(self, obj):
        return obj.dislikes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_is_disliked(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.dislikes.filter(id=request.user.id).exists()
        return False

    def get_replies(self, obj):
        if obj.parent is None:
            replies = obj.replies.all().order_by('time_stamp')
            return CommentSerializer(replies, many=True, context=self.context).data
        return []