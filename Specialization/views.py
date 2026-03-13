from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from Specialization.models import Specialization, Stack, SavedSpecialization, SavedStack, SpecializationAdmin, SpecializationMembership, SpecializationModerator, SpecializationRoom, StackAdmin, StackMembership, StackModerator, CompletedSpecialization, CompletedStack, PositionTracker, Certificate, IssuedCertificate
from Specialization.serializers import SpecializationSerializer, StackSerializer, SavedSpecializationSerializer, SavedStackSerializer, SpecializationAdminSerializer, SpecializationMembershipSerializer, SpecializationModeratorSerializer, SpecializationRoomSerializer, StackAdminSerializer, StackMembershipSerializer, StackModeratorSerializer, CompletedSpecializationSerializer, CompletedStackSerializer, PositionTrackerSerializer, CertificateSerializer, IssuedCertificateSerializer
from Authentication.models import Profile
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from Specialization.permissions import IsAdmin, IsCreator, IsModerator
from django.shortcuts import get_object_or_404
import json
import uuid
import random
from datetime import datetime


# Create your views here.
class SpecializationViewSet(ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    # permission_classes = [IsModerator, IsAdmin, IsCreator]
    permission_classes = [IsModerator]

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
        print(now)

        print(profile)
        data['created_by'] = [profile.id, ]
        data['created_on'] = now
        data['moderator'] = [profile.id, ]
        data['admins'] = [profile.id, ]
        print(data)
        serializer = SpecializationSerializer(data=data)

        if not serializer.is_valid():
            return Response({'error': f'An error was encountered while trying to duplicate the specialization.\n --- {serializer._errors}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            serializer.save()
            context = {
                'data': serializer.data,
                'message': 'Specialization duplicated successfully'
            }
            return Response(context, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'error': f'The duplication of the specialization encountered an error.{serializer._errors}'}, status=status.HTTP_404_NOT_FOUND)
        
        
    @action(detail=True, methods=['post', 'get'])
    def mark_as_complete(self, request, pk=None):
        specialization = Specialization.objects.get(pk=pk)

        user = request.user
        profile = Profile.objects.get(user=user)
        data = dict()
        data['specialization'] = specialization.id
        data['completed_on'] = datetime.now()
        data['completed_by'] = profile.id 

        serializer = CompletedSpecializationSerializer(data=data)
        if not serializer.is_valid():
            return Response({'error': 'An error occured trying to mark the specialization as completed. Check the data passed.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        context = {
            'data': serializer.data,
            'message': 'Specialization marked as completed successfully.'
        }
        return Response(context, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        specialization = self.get_object()
        
        # Real metrics
        enrollments = specialization.specializationmembership_set.count() if hasattr(specialization, 'specializationmembership_set') else specialization.members.count()
        completions = CompletedSpecialization.objects.filter(specialization=specialization).count()
        
        # Mock Engagement metrics for UI
        views = enrollments * random.randint(3, 10)
        shares = int(enrollments * random.uniform(0.1, 0.5))
        likes = int(enrollments * random.uniform(0.3, 0.8))
        average_rating = round(random.uniform(3.5, 5.0), 1) if enrollments > 0 else 0.0

        revenue = 0
        if specialization.is_paid and specialization.price:
            revenue = float(specialization.price) * enrollments

        return Response({
            'enrollments': enrollments,
            'completions': completions,
            'views': views,
            'shares': shares,
            'likes': likes,
            'average_rating': average_rating,
            'revenue': revenue
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def generate_from_files(self, request):
        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        # In a real scenario, an LLM/OCR would process these files. 
        # Here we mock the generation based on the file count/names.
        file_names = [f.name for f in files]
        base_name = file_names[0].split('.')[0].replace('_', ' ').replace('-', ' ').title()
        
        user = request.user
        profile = Profile.objects.get(user=user)

        # Create the Specialization
        new_specialization = Specialization.objects.create(
            name=f"{base_name} Course",
            description=f"Auto-generated learning path from {len(files)} uploaded files: {', '.join(file_names)}",
            learning_type='course',
            is_paid=False,
        )
        new_specialization.created_by.add(profile)
        new_specialization.admins.add(profile)
        
        # Create a matching Stack per file
        for f in files:
            stack_name = f.name.split('.')[0].replace('_', ' ').title()
            stack = Stack.objects.create(
                name=stack_name,
                description=f"Module covering topics from {f.name}"
            )
            stack.created_by.add(profile)
            new_specialization.stacks.add(stack)

        serializer = self.get_serializer(new_specialization)
        return Response({
            'message': f'Successfully generated {new_specialization.learning_type} with {len(files)} stacks.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    

class StackViewSet(ModelViewSet):
    queryset = Stack.objects.all()
    serializer_class = StackSerializer
    permission_classes = [IsAuthenticated, IsModerator]

    @action(detail=True, methods=['post'])
    def create_stack(self, request):
        serializer = StackSerializer(data=request.data)

        if not serializer.is_valid:
            return Response({'error': f'Invalid data input. \n{serializer.error_messages}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # profile = Profile.objects.get(user=request.user)
        profile = get_object_or_404(Profile, user=request.user)
        serializer.save(created_by=profile)

        data = {
            'stack_data': serializer.data,
            'message': 'Stack created successfully.'
        }
        return Response(data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsCreator])
    def duplicate_stack(self, request, id=None):
        if not id:
            return Response({'error': 'An instance of a stack must be passed'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = Stack.objects.get(pk=id)
            data = data.__dict__
            data.pop('id', '_state')

            user = request.user
            profile = Profile.objects.get(user=user)

            data['created_by'] = [profile.id, ]
            data['created_on'] = datetime.now()
            data['moderator'] = [profile.id, ]
            data['admins'] = [profile.id, ]

            serializer = StackSerializer(data=data)

            if not serializer.is_valid():
                return Response({'error': 'Duplication failed. Check if the stack is saved or in draft already.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            data = {
                'data': serializer.data,
                'message': 'Stack duplicated successfully.'
            }

            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def mark_as_complete(self, request, pk=None):
        stack = Stack.objects.get(pk=pk)

        user = request.user
        profile = Profile.objects.get(user=user)
        data = dict()
        data['stack'] = stack.id
        data['completed_on'] = datetime.now()
        data['completed_by'] = profile.id

        serializer = CompletedStackSerializer(data=data)
        if not serializer.is_valid():
            return Response({'error': 'An error occured trying to mark the stack as completed. Check the data passed.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        context = {
            'data': serializer.data,
            'message': 'Stack marked as completed successfully.'
        }
        return Response(context, status=status.HTTP_201_CREATED)





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

class CertificateViewSet(ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer

class IssuedCertificateViewSet(ModelViewSet):
    queryset = IssuedCertificate.objects.all()
    serializer_class = IssuedCertificateSerializer

