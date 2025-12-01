from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from Specialization.models import Specialization, Stack, SavedSpecialization, SavedStack, SpecializationAdmin, SpecializationMembership, SpecializationModerator, SpecializationRoom, StackAdmin, StackMembership, StackModerator, CompletedSpecialization, CompletedStack, PositionTracker
from Specialization.serializers import SpecializationSerializer, StackSerializer, SavedSpecializationSerializer, SavedStackSerializer, SpecializationAdminSerializer, SpecializationMembershipSerializer, SpecializationModeratorSerializer, SpecializationRoomSerializer, StackAdminSerializer, StackMembershipSerializer, StackModeratorSerializer, CompletedSpecializationSerializer, CompletedStackSerializer, PositionTrackerSerializer
from Authentication.models import Profile
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from Specialization.permissions import IsAdmin, IsCreator, IsModerator
from django.shortcuts import get_object_or_404


# Create your views here.
class SpecializationViewSet(ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer
    permission_classes = [IsAuthenticated, IsModerator]

    @action(detail=True, methods=['post'], permission_classes=[IsCreator])
    def duplicate(self, request, id=None):
        serializer = SpecializationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': 'An error was encountered while trying to duplicate the specialization.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            id = serializer.validated_data.pop('id')
            user = request.user
            profile = Profile.objects.get(user=user)
            serializer.validated_data['created_by'] = profile
            serializer.save()
            data = {
                'data': serializer.data,
                'message': 'Specialization duplicated successfully'
            }
            return Response(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': 'The duplication of the specialization encountered an error.'}, status=status.HTTP_404_NOT_FOUND)

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
        serializer = StackSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'error': 'Duplication failed. Check if the stack is saved or in draft already.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = {
            'data': serializer.data,
            'message': 'Stack duplicated successfully.'
        }

        return Response(data, status=status.HTTP_201_CREATED)





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

