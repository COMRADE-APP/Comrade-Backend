from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from Specialization.models import (
    Specialization, Stack, SavedSpecialization, SavedStack,
    SpecializationAdmin, SpecializationMembership, SpecializationModerator,
    SpecializationRoom, StackAdmin, StackMembership, StackModerator,
    CompletedSpecialization, CompletedStack, PositionTracker,
    Certificate, IssuedCertificate,
    Lesson, Quiz, QuizQuestion, QuizAttempt, Enrollment, LearnerProgress
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
    EnrollmentSerializer, LearnerProgressSerializer
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
        if self.action in ['list', 'retrieve', 'analytics', 'enroll', 'my_enrollments', 'progress']:
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

        stacks = specialization.stacks.all()
        progress_data = []
        total_lessons = 0
        completed_lessons = 0

        for stack in stacks:
            lessons = stack.lessons.all()
            stack_lessons = []
            for lesson in lessons:
                total_lessons += 1
                lp = LearnerProgress.objects.filter(user=request.user, lesson=lesson).first()
                is_completed = lp.completed if lp else False
                if is_completed:
                    completed_lessons += 1
                stack_lessons.append({
                    'id': lesson.id,
                    'title': lesson.title,
                    'content_type': lesson.content_type,
                    'duration_minutes': lesson.duration_minutes,
                    'order': lesson.order,
                    'is_preview': lesson.is_preview,
                    'is_locked': lesson.is_locked,
                    'completed': is_completed,
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


# ============================================================================
# STACK VIEWSET (ENHANCED)
# ============================================================================

class StackViewSet(ModelViewSet):
    queryset = Stack.objects.all()
    serializer_class = StackSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
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
