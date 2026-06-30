from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Max
from Specialization.models import (
    Specialization, Stack, SavedSpecialization, SavedStack,
    SpecializationAdmin, SpecializationMembership, SpecializationModerator,
    SpecializationRoom, StackAdmin, StackMembership, StackModerator,
    CompletedSpecialization, CompletedStack, PositionTracker,
    Certificate, IssuedCertificate,
    Lesson, Quiz, QuizQuestion, QuizAttempt, Enrollment, LearnerProgress,
    Activity, ActivitySubmission, Lab
)
from Specialization.serializers import (
    SpecializationSerializer, SpecializationListSerializer, StackSerializer,
    StackDetailSerializer, SavedSpecializationSerializer, SavedStackSerializer,
    SpecializationAdminSerializer, SpecializationMembershipSerializer,
    SpecializationModeratorSerializer, SpecializationRoomSerializer,
    StackAdminSerializer, StackMembershipSerializer, StackModeratorSerializer,
    CompletedSpecializationSerializer, CompletedStackSerializer,
    PositionTrackerSerializer, CertificateSerializer, IssuedCertificateSerializer,
    LessonSerializer, LessonListSerializer, QuizSerializer, QuizQuestionSerializer,
    QuizQuestionCreateSerializer, QuizAttemptSerializer,
    EnrollmentSerializer, LearnerProgressSerializer,
    ActivitySerializer, ActivitySubmissionSerializer, LabSerializer
)
from Authentication.models import Profile
from Specialization.permissions import IsAdmin, IsCreator, IsModerator
from decimal import Decimal
import json, uuid, random
from datetime import datetime


# ============================================================================
# SPECIALIZATION VIEWSET (ENHANCED)
# ============================================================================

class SpecializationViewSet(ModelViewSet):
    queryset = Specialization.objects.all().order_by('-created_on')
    serializer_class = SpecializationSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'analytics', 'enroll', 'my_enrollments', 'progress', 'reorder_stacks']:
            return [IsAuthenticated()]
        return [IsModerator()]

    def get_serializer_class(self):
        if self.action == 'list':
            return SpecializationListSerializer
        return SpecializationSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        provider_id = self.request.query_params.get('provider')
        if provider_id:
            qs = qs.filter(provider_id=provider_id)
        return qs

    def perform_create(self, serializer):
        from Payment.models import PaymentGroups, PaymentProfile
        from django.contrib.contenttypes.models import ContentType
        
        instance = serializer.save()
        profile = Profile.objects.filter(user=self.request.user).first()
        if profile:
            instance.created_by.add(profile)
            instance.members.add(profile)
            
            try:
                payment_profile = PaymentProfile.objects.get(user=profile)
                ctype = ContentType.objects.get_for_model(Specialization)
                # Create a specific Kitty for this course
                PaymentGroups.objects.create(
                    name=f"Kitty: {instance.name}",
                    description=f"Revenue pool for {instance.name}",
                    creator=payment_profile,
                    group_type='kitty',
                    tier=payment_profile.tier,
                    entity_content_type=ctype,
                    entity_object_id=str(instance.id),
                    auto_create_room=False
                )
            except Exception as e:
                pass

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        """Enroll the current user in a specialization.
        If the course is paid and payment_method is provided, process payment directly.
        Otherwise return 402 for legacy shop-checkout flow."""
        specialization = self.get_object()
        payment_method = request.data.get('payment_method')
        
        if specialization.is_paid:
            if not payment_method:
                # Legacy flow — return 402 for frontend to show enrollment modal
                return Response({
                    'requires_checkout': True,
                    'item_payload': {
                        'id': str(specialization.id),
                        'name': specialization.name,
                        'price': float(specialization.price),
                        'type': 'course',
                        'qty': 1,
                        'image': specialization.image_url,
                        'is_sharable': False
                    }
                }, status=status.HTTP_402_PAYMENT_REQUIRED)
            
            # Direct enrollment with payment
            from Payment.models import PaymentProfile, PaymentGroups
            from django.contrib.contenttypes.models import ContentType
            
            payment_profile = None
            profile = Profile.objects.filter(user=request.user).first()
            if profile:
                payment_profile = PaymentProfile.objects.filter(user=profile).first()
                
            if not payment_profile or getattr(payment_profile, 'comrade_balance', 0) < specialization.price:
                return Response({'error': 'Insufficient wallet balance.'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Deduct from user wallet
            payment_profile.comrade_balance -= specialization.price
            payment_profile.save()
            
            # Credit Course Kitty
            ctype = ContentType.objects.get_for_model(Specialization)
            kitty = PaymentGroups.objects.filter(entity_content_type=ctype, entity_object_id=str(specialization.id)).first()
            if kitty:
                kitty.current_amount += specialization.price
                kitty.save()
                
            payment_status = 'paid'
        else:
            payment_status = 'free'

        enrollment, created = Enrollment.objects.get_or_create(
            user=request.user,
            specialization=specialization,
            defaults={
                'payment_status': payment_status,
                'status': 'active'
            }
        )
        if not created:
            return Response({'detail': 'Already enrolled', 'enrollment': EnrollmentSerializer(enrollment).data},
                          status=status.HTTP_200_OK)

        profile = Profile.objects.filter(user=request.user).first()
        if profile:
            specialization.members.add(profile)

        return Response({
            'detail': 'Successfully enrolled!',
            'enrollment': EnrollmentSerializer(enrollment).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def group_enroll(self, request, pk=None):
        """Enroll multiple group members in a specialization.
        Expects: { group_id, member_ids: [...], payment_method, amount }
        """
        specialization = self.get_object()
        member_ids = request.data.get('member_ids', [])
        total_amount = request.data.get('amount')
        payment_method = request.data.get('payment_method')
        
        if not member_ids:
            return Response({'error': 'No members specified.'}, status=status.HTTP_400_BAD_REQUEST)

        if specialization.is_paid:
            if not payment_method or not total_amount:
                return Response({'error': 'Payment method and amount required.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                total_amount = Decimal(str(total_amount))
            except (ValueError, TypeError):
                return Response({'error': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)
                
            from Payment.models import PaymentProfile, PaymentGroups
            from django.contrib.contenttypes.models import ContentType
            
            payment_profile = None
            profile = Profile.objects.filter(user=request.user).first()
            if profile:
                payment_profile = PaymentProfile.objects.filter(user=profile).first()
                
            if not payment_profile or getattr(payment_profile, 'comrade_balance', 0) < total_amount:
                return Response({'error': 'Insufficient wallet balance.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Deduct wallet
            payment_profile.comrade_balance -= total_amount
            payment_profile.save()
            
            # Credit Course Kitty
            ctype = ContentType.objects.get_for_model(Specialization)
            kitty = PaymentGroups.objects.filter(entity_content_type=ctype, entity_object_id=str(specialization.id)).first()
            if kitty:
                kitty.current_amount += total_amount
                kitty.save()

        # Enroll the requesting user first
        enrollment, _ = Enrollment.objects.get_or_create(
            user=request.user,
            specialization=specialization,
            defaults={
                'payment_status': 'paid' if specialization.is_paid else 'free',
                'status': 'active'
            }
        )
        profile = Profile.objects.filter(user=request.user).first()
        if profile:
            specialization.members.add(profile)

        # Enroll each member
        enrolled_count = 1  # counting the requester
        from Authentication.models import CustomUser
        for uid in member_ids:
            try:
                member_user = CustomUser.objects.get(id=uid)
                member_enrollment, created = Enrollment.objects.get_or_create(
                    user=member_user,
                    specialization=specialization,
                    defaults={
                        'payment_status': 'paid' if specialization.is_paid else 'free',
                        'status': 'active'
                    }
                )
                if created:
                    enrolled_count += 1
                member_profile = Profile.objects.filter(user=member_user).first()
                if member_profile:
                    specialization.members.add(member_profile)
            except Exception:
                continue

        return Response({
            'detail': f'Group enrolled! {enrolled_count} members now have access.',
            'enrolled_count': enrolled_count,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_enrollments(self, request):
        """Get all enrollments for the current user."""
        status_filter = request.query_params.get('status', None)
        enrollments = Enrollment.objects.filter(user=request.user)
        if status_filter:
            enrollments = enrollments.filter(status=status_filter)
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def progress(self, request, pk=None):
        """Get full progress tree for a specialization."""
        specialization = self.get_object()
        enrollment = Enrollment.objects.filter(user=request.user, specialization=specialization).first()
        is_enrolled = enrollment is not None

        stacks = specialization.stacks.all()
        progress_data = []
        total_lessons = 0
        completed_lessons = 0

        for stack in stacks:
            lessons = stack.lessons.all().order_by('order')
            stack_lessons = []
            sequential_blocked = False
            prev_lesson_completed = True

            for lesson in lessons:
                total_lessons += 1
                lp = LearnerProgress.objects.filter(user=request.user, lesson=lesson).first()
                is_completed = lp.completed if lp else False

                # Locked for unenrolled
                locked = lesson.is_locked
                if specialization.lock_for_unenrolled and not is_enrolled and not lesson.is_preview:
                    locked = True

                # Sequential locking
                if specialization.sequential_locking and not prev_lesson_completed and not lesson.is_preview:
                    locked = True
                    sequential_blocked = True

                # Skip disabled — hide future lessons
                if specialization.skip_disabled and sequential_blocked and not lesson.is_preview:
                    continue

                if is_completed:
                    completed_lessons += 1

                prev_lesson_completed = is_completed

                stack_lessons.append({
                    'id': lesson.id,
                    'title': lesson.title,
                    'content_type': lesson.content_type,
                    'duration_minutes': lesson.duration_minutes,
                    'order': lesson.order,
                    'is_preview': lesson.is_preview,
                    'is_locked': locked,
                    'completed': is_completed,
                    'sequential_blocked': sequential_blocked and not is_completed,
                })

            # Get quizzes for this stack
            quizzes = stack.quizzes.all()
            quiz_data = []
            for quiz in quizzes:
                best_attempt = QuizAttempt.objects.filter(
                    user=request.user, quiz=quiz
                ).order_by('-score').first()
                quiz_data.append({
                    'id': quiz.id,
                    'title': quiz.title,
                    'passing_score': quiz.passing_score,
                    'best_score': float(best_attempt.score) if best_attempt else None,
                    'passed': best_attempt.passed if best_attempt else False,
                    'attempts_used': QuizAttempt.objects.filter(user=request.user, quiz=quiz).count(),
                    'max_attempts': quiz.max_attempts,
                })

            progress_data.append({
                'stack_id': stack.id,
                'stack_name': stack.name,
                'lessons': stack_lessons,
                'quizzes': quiz_data,
                'total_lessons': len(stack_lessons),
                'completed_lessons': sum(1 for l in stack_lessons if l['completed']),
            })

        overall_progress = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

        # Update enrollment progress
        if enrollment:
            enrollment.progress_percent = Decimal(str(round(overall_progress, 2)))
            enrollment.save()

        return Response({
            'specialization_id': specialization.id,
            'specialization_name': specialization.name,
            'enrollment_status': enrollment.status if enrollment else 'not_enrolled',
            'overall_progress': round(overall_progress, 2),
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'stacks': progress_data,
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def analytics(self, request, pk=None):
        specialization = self.get_object()
        enrollments = Enrollment.objects.filter(specialization=specialization).count()
        completions = Enrollment.objects.filter(specialization=specialization, status='completed').count()
        total_lessons = Lesson.objects.filter(stack__specialization_stacks=specialization).count()

        return Response({
            'enrollments': enrollments,
            'completions': completions,
            'total_lessons': total_lessons,
            'total_stacks': specialization.stacks.count(),
        })

    @action(detail=True, methods=['post', 'get'], permission_classes=[IsCreator])
    def duplicate(self, request, pk=None):
        if not pk:
            return Response({'error': 'No instance passed.'}, status=status.HTTP_400_BAD_REQUEST)
        data = Specialization.objects.get(id=pk)
        data = data.__dict__
        data.pop('id', '_state')
        user = request.user
        profile = Profile.objects.get(user=user)
        now = datetime.now()
        data['created_by'] = [profile.id]
        data['created_on'] = now
        data['moderator'] = [profile.id]
        data['admins'] = [profile.id]
        serializer = SpecializationSerializer(data=data)
        if not serializer.is_valid():
            return Response({'error': f'Duplication failed. {serializer.errors}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            serializer.save()
            return Response({'data': serializer.data, 'message': 'Specialization duplicated.'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_from_files(self, request):
        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        file_names = [f.name for f in files]
        base_name = file_names[0].split('.')[0].replace('_', ' ').replace('-', ' ').title()
        profile = Profile.objects.get(user=request.user)
        new_spec = Specialization.objects.create(
            name=f"{base_name} Course",
            description=f"Auto-generated from {len(files)} files: {', '.join(file_names)}",
            learning_type='course',
            is_paid=False,
        )
        new_spec.created_by.add(profile)
        new_spec.admins.add(profile)
        for f in files:
            stack_name = f.name.split('.')[0].replace('_', ' ').title()
            stack = Stack.objects.create(name=stack_name, description=f"Module from {f.name}")
            stack.created_by.add(profile)
            new_spec.stacks.add(stack)
        serializer = self.get_serializer(new_spec)
        return Response({'message': f'Generated with {len(files)} stacks.', 'data': serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def reorder_stacks(self, request, pk=None):
        spec = self.get_object()
        stack_ids = request.data.get('ordered_stack_ids', [])
        spec.stack_order = stack_ids
        spec.save(update_fields=['stack_order'])
        return Response({'status': 'reordered', 'stack_order': stack_ids})


# ============================================================================
# STACK VIEWSET (ENHANCED)
# ============================================================================

class StackViewSet(ModelViewSet):
    queryset = Stack.objects.all()
    serializer_class = StackSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'add_lesson', 'remove_lesson', 'reorder_lessons']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsModerator()]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StackDetailSerializer
        return StackSerializer

    @action(detail=True, methods=['post'])
    def mark_as_complete(self, request, pk=None):
        stack = Stack.objects.get(pk=pk)
        profile = Profile.objects.get(user=request.user)
        data = {'stack': stack.id, 'completed_on': datetime.now(), 'completed_by': profile.id}
        serializer = CompletedStackSerializer(data=data)
        if not serializer.is_valid():
            return Response({'error': 'Failed to mark as complete.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({'data': serializer.data, 'message': 'Stack completed!'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def add_lesson(self, request, pk=None):
        stack = self.get_object()
        title = request.data.get('title', 'Untitled Lesson')
        content_type = request.data.get('content_type', 'text')
        description = request.data.get('description', '')
        content_text = request.data.get('content_text', '')
        video_url = request.data.get('video_url', '')
        duration_minutes = request.data.get('duration_minutes', 10)
        last_order = Lesson.objects.filter(stack=stack).aggregate(Max('order'))['order__max'] or 0
        lesson = Lesson.objects.create(
            stack=stack, title=title, content_type=content_type,
            description=description, content_text=content_text,
            video_url=video_url, duration_minutes=duration_minutes,
            order=last_order + 1,
        )
        from .serializers import LessonSerializer
        return Response(LessonSerializer(lesson).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def remove_lesson(self, request, pk=None):
        stack = self.get_object()
        lesson_id = request.data.get('lesson_id')
        if not lesson_id:
            return Response({'error': 'lesson_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        Lesson.objects.filter(pk=lesson_id, stack=stack).delete()
        return Response({'status': 'removed'})

    @action(detail=True, methods=['post'])
    def reorder_lessons(self, request, pk=None):
        stack = self.get_object()
        ordered_ids = request.data.get('ordered_ids', [])
        if not ordered_ids:
            return Response({'error': 'ordered_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        for idx, lesson_id in enumerate(ordered_ids):
            Lesson.objects.filter(pk=lesson_id, stack=stack).update(order=idx)
        return Response({'status': 'reordered'})


# ============================================================================
# LESSON VIEWSET
# ============================================================================

class LessonViewSet(ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'complete']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        stack_id = self.request.query_params.get('stack_id')
        if stack_id:
            qs = qs.filter(stack_id=stack_id)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete(self, request, pk=None):
        """Mark a lesson as completed and update enrollment progress."""
        lesson = self.get_object()

        # Check pass_mark_to_continue — if any stack-level quiz requires passing, enforce it
        stack = lesson.stack
        passing_quizzes = Quiz.objects.filter(stack=stack, pass_mark_to_continue=True)
        for quiz in passing_quizzes:
            passed = QuizAttempt.objects.filter(
                user=request.user, quiz=quiz, passed=True
            ).exists()
            if not passed:
                return Response({
                    'error': f'You must pass "{quiz.title}" before completing this lesson.',
                    'requires_pass': True,
                    'quiz_id': quiz.id,
                }, status=status.HTTP_400_BAD_REQUEST)

        progress, created = LearnerProgress.objects.get_or_create(
            user=request.user, lesson=lesson,
            defaults={'completed': True, 'completed_at': timezone.now()}
        )
        if not created and not progress.completed:
            progress.completed = True
            progress.completed_at = timezone.now()
            progress.save()

        # Update enrollment progress for the parent specialization
        specializations = Specialization.objects.filter(stacks=lesson.stack)
        for spec in specializations:
            enrollment = Enrollment.objects.filter(user=request.user, specialization=spec).first()
            if enrollment:
                total = Lesson.objects.filter(stack__specialization_stacks=spec).count()
                completed = LearnerProgress.objects.filter(
                    user=request.user,
                    lesson__stack__specialization_stacks=spec,
                    completed=True
                ).count()
                enrollment.progress_percent = Decimal(str(round(completed / total * 100, 2))) if total > 0 else 0
                enrollment.save()

                # AUTO-CERTIFICATE: If 100% complete, auto-issue certificate
                if completed == total and total > 0:
                    enrollment.status = 'completed'
                    enrollment.completed_at = timezone.now()
                    enrollment.save()
                    self._auto_issue_certificate(request.user, spec)

        return Response({
            'detail': 'Lesson completed!',
            'lesson_id': lesson.id,
            'completed': True
        })

    def _auto_issue_certificate(self, user, specialization):
        """Auto-generate certificate if template exists."""
        cert_template = Certificate.objects.filter(
            specialization=specialization, auto_generate=True
        ).first()

        profile = Profile.objects.filter(user=user).first()
        if not profile:
            return

        # Check if already issued
        existing = IssuedCertificate.objects.filter(
            issued_to=profile, specialization=specialization
        ).exists()
        if existing:
            return

        # Calculate average quiz score
        quizzes = Quiz.objects.filter(stack__specialization_stacks=specialization)
        attempts = QuizAttempt.objects.filter(user=user, quiz__in=quizzes, passed=True)
        avg_score = 0
        if attempts.exists():
            avg_score = sum(float(a.score) for a in attempts) / attempts.count()

        # Calculate hours
        total_mins = Lesson.objects.filter(stack__specialization_stacks=specialization).count() * 10
        hours = round(total_mins / 60, 1)

        # Determine grade
        if avg_score >= 90:
            grade = 'A'
        elif avg_score >= 80:
            grade = 'B+'
        elif avg_score >= 70:
            grade = 'B'
        else:
            grade = 'Pass'

        issued = IssuedCertificate.objects.create(
            issued_to=profile,
            certificate=cert_template,
            grade=grade,
            average_score=Decimal(str(round(avg_score, 2))),
            hours_completed=Decimal(str(hours)),
        )
        issued.specialization.add(specialization)

    @action(detail=True, methods=['post'])
    def add_block(self, request, pk=None):
        from .models import LessonContentBlock
        lesson = self.get_object()
        block_type = request.data.get('block_type', 'text')
        content = request.data.get('content', '')
        url = request.data.get('url', '')
        caption = request.data.get('caption', '')
        code_language = request.data.get('code_language', 'plaintext')
        background_color = request.data.get('background_color', '#ffffff')
        last_order = LessonContentBlock.objects.filter(lesson=lesson).aggregate(Max('order'))['order__max'] or 0
        block = LessonContentBlock.objects.create(
            lesson=lesson, block_type=block_type, content=content,
            url=url, caption=caption, code_language=code_language,
            background_color=background_color, order=last_order + 1,
        )
        from .serializers import LessonContentBlockSerializer
        return Response(LessonContentBlockSerializer(block).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def remove_block(self, request, pk=None):
        lesson = self.get_object()
        block_id = request.data.get('block_id')
        from .models import LessonContentBlock
        LessonContentBlock.objects.filter(pk=block_id, lesson=lesson).delete()
        return Response({'status': 'removed'})

    @action(detail=True, methods=['post'])
    def reorder_blocks(self, request, pk=None):
        lesson = self.get_object()
        ordered_ids = request.data.get('ordered_ids', [])
        if not ordered_ids:
            return Response({'error': 'ordered_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        from .models import LessonContentBlock
        for idx, block_id in enumerate(ordered_ids):
            LessonContentBlock.objects.filter(pk=block_id, lesson=lesson).update(order=idx)
        return Response({'status': 'reordered'})

    @action(detail=True, methods=['post'])
    def upload_block_file(self, request, pk=None):
        lesson = self.get_object()
        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        block_type = request.data.get('block_type', 'file')
        from .models import LessonContentBlock
        last_order = LessonContentBlock.objects.filter(lesson=lesson).aggregate(Max('order'))['order__max'] or 0
        block = LessonContentBlock.objects.create(
            lesson=lesson, block_type=block_type,
            caption=request.data.get('caption', uploaded.name),
            file=uploaded, order=last_order + 1,
        )
        from .serializers import LessonContentBlockSerializer
        return Response(LessonContentBlockSerializer(block).data, status=status.HTTP_201_CREATED)


# ============================================================================
# QUIZ VIEWSET
# ============================================================================

class QuizViewSet(ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'submit_attempt']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        stack_id = self.request.query_params.get('stack_id')
        lesson_id = self.request.query_params.get('lesson_id')
        specialization_id = self.request.query_params.get('specialization_id')
        if stack_id:
            qs = qs.filter(stack_id=stack_id)
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        if specialization_id:
            qs = qs.filter(specialization_id=specialization_id)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_attempt(self, request, pk=None):
        """Submit quiz answers and get graded results."""
        quiz = self.get_object()
        answers = request.data.get('answers', [])

        # Check max attempts
        attempt_count = QuizAttempt.objects.filter(user=request.user, quiz=quiz).count()
        if attempt_count >= quiz.max_attempts:
            return Response({'error': 'Maximum attempts reached.'}, status=status.HTTP_400_BAD_REQUEST)

        # Grade the quiz
        questions = quiz.questions.all()
        total_points = sum(q.points for q in questions)
        earned_points = 0
        graded_answers = []

        for answer in answers:
            question_id = answer.get('question_id')
            user_answer = answer.get('answer')
            try:
                question = questions.get(id=question_id)
            except QuizQuestion.DoesNotExist:
                continue

            is_correct = False
            if question.question_type in ['multiple_choice', 'true_false']:
                # Find the correct choice
                correct_choices = [c for c in question.choices if c.get('is_correct')]
                if correct_choices and user_answer == correct_choices[0].get('label'):
                    is_correct = True
            elif question.question_type == 'short_answer':
                if user_answer and user_answer.strip().lower() == question.correct_answer.strip().lower():
                    is_correct = True

            if is_correct:
                earned_points += question.points

            graded_answers.append({
                'question_id': question_id,
                'answer': user_answer,
                'is_correct': is_correct,
                'correct_answer': question.correct_answer if not is_correct else None,
                'explanation': question.explanation,
            })

        score = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = score >= quiz.passing_score

        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            user=request.user,
            answers=graded_answers,
            score=Decimal(str(round(score, 2))),
            passed=passed,
            completed_at=timezone.now(),
            attempt_number=attempt_count + 1,
        )

        return Response({
            'attempt_id': attempt.id,
            'score': round(score, 2),
            'passed': passed,
            'passing_score': quiz.passing_score,
            'earned_points': earned_points,
            'total_points': total_points,
            'answers': graded_answers,
            'attempt_number': attempt.attempt_number,
            'attempts_remaining': quiz.max_attempts - attempt.attempt_number,
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def my_attempts(self, request, pk=None):
        quiz = self.get_object()
        attempts = QuizAttempt.objects.filter(user=request.user, quiz=quiz)
        serializer = QuizAttemptSerializer(attempts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_from_content(self, request):
        """AI-powered quiz question generation from lesson content.
        Accepts (JSON or FormData):
          - lesson_ids: [...], content_text: "...", num_questions: 5, question_types: [...]
          - files: multipart upload (pdf, docx, txt, md)
          - reference_urls: [{label, url}, ...]
          - include_transcripts: bool (auto-extract YouTube/internet video transcripts)
        Uses configured AI provider (OpenAI, Gemini, or Hugging Face) or falls back to rules-based extraction.
        """
        import json

        def _parse_field(data, key, default=None):
            val = data.get(key, default)
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return val
            return val

        lesson_ids = _parse_field(request.data, 'lesson_ids', [])
        content_text = request.data.get('content_text', '')
        num_questions = int(_parse_field(request.data, 'num_questions', 5))
        question_types = _parse_field(request.data, 'question_types', ['multiple_choice', 'true_false'])
        reference_urls = _parse_field(request.data, 'reference_urls', [])
        include_transcripts = str(_parse_field(request.data, 'include_transcripts', False)).lower() in ('true', '1', 'yes')
        uploaded_files = request.FILES.getlist('files')

        # Gather content from lessons
        if lesson_ids:
            lessons = Lesson.objects.filter(id__in=lesson_ids)
            for lesson in lessons:
                if lesson.content_text:
                    content_text += '\n\n' + lesson.content_text
                for block in lesson.content_blocks.filter(block_type='text'):
                    if block.content:
                        content_text += '\n\n' + block.content
                if include_transcripts:
                    for block in lesson.content_blocks.filter(block_type='video'):
                        if block.url:
                            transcript = self._extract_video_transcript(block.url)
                            if transcript:
                                content_text += '\n\n[Video Transcript]\n' + transcript

        # Extract text from uploaded files
        if uploaded_files:
            for f in uploaded_files:
                extracted = self._extract_file_text(f)
                if extracted:
                    content_text += '\n\n[From file: ' + f.name + ']\n' + extracted

        # Fetch content from reference URLs
        if reference_urls:
            for ref in reference_urls:
                url = ref.get('url', '')
                label = ref.get('label', url)
                if not url:
                    continue
                fetched = self._fetch_url_content(url, include_transcripts)
                if fetched:
                    content_text += '\n\n[From: ' + label + ']\n' + fetched

        if not content_text.strip():
            return Response({'error': 'No content provided to generate from.'}, status=status.HTTP_400_BAD_REQUEST)

        generated_questions = []

        # Try AI generation via available providers
        ai_questions = self._try_ai_generation(content_text, num_questions, question_types)
        if ai_questions:
            generated_questions = ai_questions
        else:
            # Fallback: rules-based extraction
            generated_questions = self._rules_based_generation(content_text, num_questions)

        return Response({
            'questions': generated_questions,
            'source': 'ai' if ai_questions else 'rules',
            'content_length': len(content_text),
        })

    def _extract_file_text(self, file_obj):
        """Extract text content from uploaded file (PDF, DOCX, TXT, MD)."""
        import os
        ext = os.path.splitext(file_obj.name)[1].lower()
        try:
            if ext == '.pdf':
                try:
                    import fitz
                    text = ''
                    doc = fitz.open(stream=file_obj.read(), filetype='pdf')
                    for page in doc:
                        text += page.get_text()
                    doc.close()
                    return text
                except ImportError:
                    pass
            elif ext == '.docx':
                try:
                    from docx import Document
                    doc = Document(file_obj)
                    return '\n'.join(p.text for p in doc.paragraphs)
                except ImportError:
                    pass
            elif ext in ('.txt', '.md'):
                return file_obj.read().decode('utf-8', errors='replace')
        except Exception:
            pass
        return None

    def _fetch_url_content(self, url, include_transcripts=False):
        """Fetch content from a URL — extract visible text or transcript."""
        import requests
        from urllib.parse import urlparse
        import re

        # YouTube transcript
        if include_transcripts:
            transcript = self._extract_video_transcript(url)
            if transcript:
                return '[Video Transcript]\n' + transcript

        try:
            resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code == 200:
                html = resp.text
                # Strip HTML tags to get visible text
                text = re.sub(r'<[^>]+>', ' ', html)
                text = re.sub(r'\s+', ' ', text).strip()
                # Limit to reasonable size
                return text[:10000]
        except Exception:
            pass
        return None

    def _extract_video_transcript(self, url):
        """Extract transcript from YouTube videos (and other platforms where possible)."""
        import re
        # YouTube
        yt_match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([\w-]+)', url)
        if yt_match:
            video_id = yt_match.group(1)
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                return ' '.join(item['text'] for item in transcript_list)
            except Exception:
                pass
            # Fallback: try oEmbed for description
            try:
                import requests
                oembed = requests.get(
                    f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json',
                    timeout=10
                )
                if oembed.status_code == 200:
                    data = oembed.json()
                    return data.get('title', '') + '\n' + data.get('author_name', '') + '\n' + data.get('description', '')
            except Exception:
                pass
        return None

    def _try_ai_generation(self, content_text, num_questions, question_types):
        """Try AI providers in order: OpenAI -> Gemini -> Hugging Face."""
        import os, json

        # Try OpenAI
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            try:
                import requests
                prompt = f"""Generate {num_questions} educational quiz questions from the following content.
Question types to use: {', '.join(question_types)}.
For each question, provide: question_text, question_type, choices (for multiple_choice/true_false as list of {{label, text, is_correct}} objects), correct_answer (for short_answer), explanation, points (default 1).

Content:
{content_text[:8000]}

Return ONLY valid JSON array of question objects."""

                resp = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    json={'model': 'gpt-4o-mini', 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.7},
                    timeout=30
                )
                if resp.status_code == 200:
                    text = resp.json()['choices'][0]['message']['content']
                    # Extract JSON array from response
                    import re
                    json_match = re.search(r'\[.*\]', text, re.DOTALL)
                    if json_match:
                        questions = json.loads(json_match.group())
                        for q in questions:
                            q.setdefault('points', 1)
                            q.setdefault('explanation', '')
                        return questions
            except Exception:
                pass

        # Try Gemini
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            try:
                import requests
                prompt = f"""Generate {num_questions} educational quiz questions from the following content.
Question types to use: {', '.join(question_types)}.
Return JSON array of objects with: question_text, question_type, choices (array of {{label, text, is_correct}}), correct_answer, explanation, points.

Content:
{content_text[:8000]}"""

                resp = requests.post(
                    f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}',
                    headers={'Content-Type': 'application/json'},
                    json={'contents': [{'parts': [{'text': prompt}]}]},
                    timeout=30
                )
                if resp.status_code == 200:
                    text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                    import re
                    json_match = re.search(r'\[.*\]', text, re.DOTALL)
                    if json_match:
                        questions = json.loads(json_match.group())
                        for q in questions:
                            q.setdefault('points', 1)
                            q.setdefault('explanation', '')
                        return questions
            except Exception:
                pass

        # Try Hugging Face
        api_key = os.environ.get('HF_API_KEY')
        if api_key:
            try:
                import requests
                prompt = f"Generate {num_questions} quiz questions from this content. Return JSON array.\n\n{content_text[:4000]}"
                resp = requests.post(
                    'https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3',
                    headers={'Authorization': f'Bearer {api_key}'},
                    json={'inputs': prompt, 'parameters': {'max_new_tokens': 2000}},
                    timeout=30
                )
                if resp.status_code == 200:
                    text = resp.json()[0]['generated_text']
                    import re
                    json_match = re.search(r'\[.*\]', text, re.DOTALL)
                    if json_match:
                        questions = json.loads(json_match.group())
                        for q in questions:
                            q.setdefault('points', 1)
                            q.setdefault('explanation', '')
                        return questions
            except Exception:
                pass

        return None

    def _rules_based_generation(self, content_text, num_questions):
        """Fallback: extract sentences and create basic questions."""
        import re
        sentences = re.split(r'[.!?\n]+', content_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        import random
        random.shuffle(sentences)
        questions = []
        types_cycle = ['multiple_choice', 'true_false', 'short_answer']

        for i, sent in enumerate(sentences[:num_questions]):
            words = sent.split()
            q_type = types_cycle[i % len(types_cycle)]

            if q_type == 'true_false':
                questions.append({
                    'question_text': f'Based on the content: "{sent[:100]}" — Is this statement true?',
                    'question_type': 'true_false',
                    'choices': [
                        {'label': 'True', 'text': 'True', 'is_correct': True},
                        {'label': 'False', 'text': 'False', 'is_correct': False},
                    ],
                    'explanation': 'Review the content above.',
                    'points': 1,
                })
            elif q_type == 'short_answer' and len(words) > 3:
                # Blank out a keyword
                idx = max(1, len(words) // 2)
                keyword = words[idx].strip('",.')
                words[idx] = '______'
                questions.append({
                    'question_text': 'Fill in the blank: ' + ' '.join(words[:30]),
                    'question_type': 'short_answer',
                    'correct_answer': keyword,
                    'explanation': f'The correct term is: {keyword}',
                    'points': 1,
                })
            else:
                questions.append({
                    'question_text': f'What does this statement mean? "{sent[:150]}"',
                    'question_type': 'multiple_choice',
                    'choices': [
                        {'label': 'A', 'text': 'Refer to the lesson materials', 'is_correct': True},
                        {'label': 'B', 'text': 'This is incorrect', 'is_correct': False},
                        {'label': 'C', 'text': 'Not enough information', 'is_correct': False},
                        {'label': 'D', 'text': 'None of the above', 'is_correct': False},
                    ],
                    'explanation': 'Review the lesson content for the correct answer.',
                    'points': 1,
                })

        return questions[:num_questions]


class QuizQuestionViewSet(ModelViewSet):
    queryset = QuizQuestion.objects.all()
    serializer_class = QuizQuestionCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        quiz_id = self.request.query_params.get('quiz_id')
        if quiz_id:
            qs = qs.filter(quiz_id=quiz_id)
        return qs


# ============================================================================
# ENROLLMENT VIEWSET
# ============================================================================

class EnrollmentViewSet(ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def drop(self, request, pk=None):
        enrollment = self.get_object()
        enrollment.status = 'dropped'
        enrollment.save()
        return Response({'detail': 'Enrollment dropped.'})

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Simulate payment unlock for a paid specialization."""
        enrollment = self.get_object()
        enrollment.payment_status = 'paid'
        enrollment.save()
        return Response({'detail': 'Content unlocked!', 'payment_status': 'paid'})


# ============================================================================
# CERTIFICATE VIEWSET
# ============================================================================

class CertificateViewSet(ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]


class IssuedCertificateViewSet(ModelViewSet):
    queryset = IssuedCertificate.objects.all()
    serializer_class = IssuedCertificateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.filter(user=self.request.user).first()
        if profile:
            return IssuedCertificate.objects.filter(issued_to=profile)
        return IssuedCertificate.objects.none()

    @action(detail=False, methods=['get'])
    def verify(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response({'error': 'Verification code required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            cert = IssuedCertificate.objects.get(verification_code=code)
            return Response({
                'valid': True,
                'issued_to': str(cert.issued_to),
                'issued_on': cert.issued_on,
                'grade': cert.grade,
                'specialization': [s.name for s in cert.specialization.all()],
            })
        except IssuedCertificate.DoesNotExist:
            return Response({'valid': False, 'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# LEARNER PROGRESS VIEWSET
# ============================================================================

class LearnerProgressViewSet(ModelViewSet):
    queryset = LearnerProgress.objects.all()
    serializer_class = LearnerProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LearnerProgress.objects.filter(user=self.request.user)


# ============================================================================
# ACTIVITY VIEWSET
# ============================================================================

class ActivityViewSet(ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        stack_id = self.request.query_params.get('stack_id')
        if stack_id:
            qs = qs.filter(stack_id=stack_id)
        return qs


# ============================================================================
# LAB VIEWSET
# ============================================================================

class LabViewSet(ModelViewSet):
    queryset = Lab.objects.all()
    serializer_class = LabSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        stack_id = self.request.query_params.get('stack_id')
        if stack_id:
            qs = qs.filter(stack_id=stack_id)
        return qs


# ============================================================================
# LEGACY VIEWSETS (kept for compatibility)
# ============================================================================

class SavedSpecializationViewSet(ModelViewSet):
    queryset = SavedSpecialization.objects.all()
    serializer_class = SavedSpecializationSerializer

class SavedStackViewSet(ModelViewSet):
    queryset = SavedStack.objects.all()
    serializer_class = SavedStackSerializer

class CompletedSpecializationViewSet(ModelViewSet):
    queryset = CompletedSpecialization.objects.all()
    serializer_class = CompletedSpecializationSerializer

class CompletedStackViewSet(ModelViewSet):
    queryset = CompletedStack.objects.all()
    serializer_class = CompletedStackSerializer

class SpecializationAdminViewSet(ModelViewSet):
    queryset = SpecializationAdmin.objects.all()
    serializer_class = SpecializationAdminSerializer

class StackAdminViewSet(ModelViewSet):
    queryset = StackAdmin.objects.all()
    serializer_class = StackAdminSerializer

class SpecializationModeratorViewSet(ModelViewSet):
    queryset = SpecializationModerator.objects.all()
    serializer_class = SpecializationModeratorSerializer

class StackModeratorViewSet(ModelViewSet):
    queryset = StackModerator.objects.all()
    serializer_class = StackModeratorSerializer

class SpecializationMembershipViewSet(ModelViewSet):
    queryset = SpecializationMembership.objects.all()
    serializer_class = SpecializationMembershipSerializer

class StackMembershipViewSet(ModelViewSet):
    queryset = StackMembership.objects.all()
    serializer_class = StackMembershipSerializer

class SpecializationRoomViewSet(ModelViewSet):
    queryset = SpecializationRoom.objects.all()
    serializer_class = SpecializationRoomSerializer

class PositionTrackerViewSet(ModelViewSet):
    queryset = PositionTracker.objects.all()
    serializer_class = PositionTrackerSerializer
