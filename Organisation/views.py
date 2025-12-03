from django.shortcuts import render
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from Organisation.serializers import OrganisationSerializer, OrgBranchSerializer, DivisionSerializer, DepartmentSerializer, SectionSerializer, TeamSerializer, ProjectSerializer, CentreSerializer, CommitteeSerializer, BoardSerializer, UnitSerializer, InstituteSerializer, ProgramSerializer, OtherOrgUnitSerializer


# Create your views here.
class OrganisationViewSet(ModelViewSet):
    queryset = Organisation.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = OrganisationSerializer
    

class OrgBranchViewSet(ModelViewSet):
    queryset = OrgBranch.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = OrgBranchSerializer
    

class DivisionViewSet(ModelViewSet):
    queryset = Division.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = DivisionSerializer
    

class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = DepartmentSerializer
    

class SectionViewSet(ModelViewSet):
    queryset = Section.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = SectionSerializer
    

class UnitViewSet(ModelViewSet):
    queryset = Unit.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = UnitSerializer
    

class TeamViewSet(ModelViewSet):
    queryset = Team.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = TeamSerializer
    

class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ProjectSerializer
    

class ProgramViewSet(ModelViewSet):
    queryset = Program.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ProgramSerializer
    

class BoardViewSet(ModelViewSet):
    queryset = Board.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = BoardSerializer
    

class CommitteeViewSet(ModelViewSet):
    queryset = Committee.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CommitteeSerializer
    

class InstituteViewSet(ModelViewSet):
    queryset = Institute.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = InstituteSerializer
    

class CentreViewSet(ModelViewSet):
    queryset = Centre.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CentreSerializer
    

class OtherOrgUnitViewSet(ModelViewSet):
    queryset = OtherOrgUnit.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = OtherOrgUnitSerializer
    

    