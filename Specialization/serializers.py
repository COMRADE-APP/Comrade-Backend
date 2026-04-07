from rest_framework import serializers
from Specialization.models import (
    Specialization, Stack, SavedSpecialization, SavedStack,
    SpecializationAdmin, SpecializationMembership, SpecializationModerator,
    SpecializationRoom, StackAdmin, StackMembership, StackModerator,
    CompletedSpecialization, CompletedStack, PositionTracker,
    Certificate, IssuedCertificate,
    Lesson, Quiz, QuizQuestion, QuizAttempt, Enrollment, LearnerProgress
)


# ============================================================================
# LESSON & CONTENT SERIALIZERS
# ============================================================================

class LessonSerializer(serializers.ModelSerializer):
    has_quiz = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'stack', 'title', 'description', 'content_type',
            'content_text', 'video_url', 'audio_url', 'image_url',
            'file_upload', 'code_snippet', 'code_language', 'external_url',
            'order', 'duration_minutes', 'is_preview', 'is_locked', 'created_on',
            'has_quiz'
        ]
        read_only_fields = ['id', 'created_on']

    def get_has_quiz(self, obj):
        return obj.quizzes.exists()


class LessonListSerializer(serializers.ModelSerializer):
    """Lightweight lesson serializer for listing within stacks."""
    completed = serializers.SerializerMethodField()
    has_quiz = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'content_type', 'order', 'duration_minutes',
            'is_preview', 'is_locked', 'completed', 'has_quiz',
            'content_text', 'video_url', 'audio_url', 'image_url',
            'file_upload', 'code_snippet', 'code_language', 'external_url'
        ]

    def get_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LearnerProgress.objects.filter(
                user=request.user, lesson=obj, completed=True
            ).exists()
        return False

    def get_has_quiz(self, obj):
        return obj.quizzes.exists()


# ============================================================================
# QUIZ & ASSESSMENT SERIALIZERS
# ============================================================================

class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = [
            'id', 'question_text', 'question_type', 'choices',
            'explanation', 'points', 'order', 'code_template', 'code_language'
        ]
        # Don't expose correct_answer in list — only after submission
        extra_kwargs = {'correct_answer': {'write_only': True}}


class QuizQuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizQuestion
        fields = '__all__'


class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'stack', 'lesson', 'specialization', 'title', 'description',
            'placement', 'passing_score', 'time_limit_minutes', 'max_attempts',
            'order', 'created_on', 'questions', 'question_count'
        ]
        read_only_fields = ['id', 'created_on']

    def get_question_count(self, obj):
        return obj.questions.count()


class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'quiz', 'user', 'answers', 'score', 'passed',
            'started_at', 'completed_at', 'attempt_number'
        ]
        read_only_fields = ['id', 'user', 'score', 'passed', 'started_at', 'attempt_number']


# ============================================================================
# ENROLLMENT & PROGRESS SERIALIZERS
# ============================================================================

class EnrollmentSerializer(serializers.ModelSerializer):
    specialization_name = serializers.CharField(source='specialization.name', read_only=True)
    specialization_image = serializers.URLField(source='specialization.image_url', read_only=True)
    specialization_type = serializers.CharField(source='specialization.learning_type', read_only=True)
    total_lessons = serializers.SerializerMethodField()
    completed_lessons = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'user', 'specialization', 'enrolled_at', 'status',
            'payment_status', 'progress_percent', 'last_accessed', 'completed_at',
            'specialization_name', 'specialization_image', 'specialization_type',
            'total_lessons', 'completed_lessons'
        ]
        read_only_fields = ['id', 'user', 'enrolled_at', 'last_accessed', 'progress_percent', 'completed_at']

    def get_total_lessons(self, obj):
        return Lesson.objects.filter(stack__specialization_stacks=obj.specialization).count()

    def get_completed_lessons(self, obj):
        return LearnerProgress.objects.filter(
            user=obj.user,
            lesson__stack__specialization_stacks=obj.specialization,
            completed=True
        ).count()


class LearnerProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model = LearnerProgress
        fields = [
            'id', 'user', 'lesson', 'completed', 'completed_at',
            'time_spent_minutes', 'notes', 'lesson_title'
        ]
        read_only_fields = ['id', 'user', 'completed_at']


# ============================================================================
# STACK & SPECIALIZATION (ENHANCED)
# ============================================================================

class StackDetailSerializer(serializers.ModelSerializer):
    """Stack with nested lessons and quizzes."""
    lessons = LessonListSerializer(many=True, read_only=True)
    quizzes = QuizSerializer(many=True, read_only=True)
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Stack
        fields = [
            'id', 'name', 'description', 'image_url', 'created_on',
            'lessons', 'quizzes', 'lesson_count'
        ]

    def get_lesson_count(self, obj):
        return obj.lessons.count()


class SpecializationSerializer(serializers.ModelSerializer):
    stacks_detail = StackDetailSerializer(source='stacks', many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    stack_count = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = Specialization
        fields = [
            'id', 'name', 'description', 'image_url', 'learning_type',
            'is_paid', 'price', 'created_by', 'created_on',
            'stacks', 'stacks_detail', 'members', 'admins', 'moderator',
            'member_count', 'stack_count', 'total_lessons', 'total_duration',
            'is_enrolled', 'user_progress'
        ]
        read_only_fields = ['id', 'created_on']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_stack_count(self, obj):
        return obj.stacks.count()

    def get_total_lessons(self, obj):
        return Lesson.objects.filter(stack__specialization_stacks=obj).count()

    def get_total_duration(self, obj):
        total = Lesson.objects.filter(stack__specialization_stacks=obj).aggregate(
            total=serializers.models.Sum('duration_minutes')
        )['total'] or 0
        return total

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(user=request.user, specialization=obj).exists()
        return False

    def get_user_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            enrollment = Enrollment.objects.filter(user=request.user, specialization=obj).first()
            if enrollment:
                return float(enrollment.progress_percent)
        return 0


class SpecializationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for catalog listing."""
    member_count = serializers.SerializerMethodField()
    stack_count = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Specialization
        fields = [
            'id', 'name', 'description', 'image_url', 'learning_type',
            'is_paid', 'price', 'created_on',
            'member_count', 'stack_count', 'total_lessons', 'is_enrolled'
        ]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_stack_count(self, obj):
        return obj.stacks.count()

    def get_total_lessons(self, obj):
        return Lesson.objects.filter(stack__specialization_stacks=obj).count()

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(user=request.user, specialization=obj).exists()
        return False


# ============================================================================
# CERTIFICATE SERIALIZERS (UPDATED)
# ============================================================================

class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = '__all__'


class IssuedCertificateSerializer(serializers.ModelSerializer):
    specialization_names = serializers.SerializerMethodField()

    class Meta:
        model = IssuedCertificate
        fields = '__all__'

    def get_specialization_names(self, obj):
        return [s.name for s in obj.specialization.all()]


# ============================================================================
# LEGACY SERIALIZERS (kept for compatibility)
# ============================================================================

class StackSerializer(serializers.ModelSerializer):
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Stack
        fields = '__all__'

    def get_lesson_count(self, obj):
        return obj.lessons.count() if hasattr(obj, 'lessons') else 0


class SavedSpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSpecialization
        fields = '__all__'

class SavedStackSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedStack
        fields = '__all__'

class SpecializationAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecializationAdmin
        fields = '__all__'

class StackAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackAdmin
        fields = '__all__'

class SpecializationMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecializationMembership
        fields = '__all__'

class StackMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackMembership
        fields = '__all__'

class SpecializationModeratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecializationModerator
        fields = '__all__'

class StackModeratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = StackModerator
        fields = '__all__'

class CompletedSpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompletedSpecialization
        fields = '__all__'

class CompletedStackSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompletedStack
        fields = '__all__'

class SpecializationRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecializationRoom
        fields = '__all__'

class PositionTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionTracker
        fields = '__all__'
