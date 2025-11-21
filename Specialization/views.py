from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from Specialization.models import Specialization, Stack, SavedSpecialization, SavedStack, SpecializationAdmin, SpecializationMembership, SpecializationModerator, SpecializationRoom, StackAdmin, StackMembership, StackModerator, CompletedSpecialization, CompletedStack
from Specialization.serializers import SpecializationSerializer, StackSerializer, SavedSpecializationSerializer, SavedStackSerializer, SpecializationAdminSerializer, SpecializationMembershipSerializer, SpecializationModeratorSerializer, SpecializationRoomSerializer, StackAdminSerializer, StackMembershipSerializer, StackModeratorSerializer, CompletedSpecializationSerializer, CompletedStackSerializer


# Create your views here.
class SpecializationViewSet(ModelViewSet):
    queryset = Specialization.objects.all()
    serializer_class = SpecializationSerializer

class StackViewSet(ModelViewSet):
    queryset = Stack.objects.all()
    serializer_class = StackSerializer

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


