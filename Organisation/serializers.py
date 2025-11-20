from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit
from rest_framework.serializers import ModelSerializer


class OrganisationSerializer(ModelSerializer):
    class Meta:
        model = Organisation
        fields = '__all__'
        read_only_fields = ['created_on']

class OrgBranchSerializer(ModelSerializer):
    class Meta:
        model = OrgBranch
        fields = '__all__'
        read_only_fields = ['created_on']

class DivisionSerializer(ModelSerializer):
    class Meta:
        model = Division
        fields = '__all__'
        read_only_fields = ['created_on']

class SectionSerializer(ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'
        read_only_fields = ['created_on']

class DepartmentSerializer(ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ['created_on']

class UnitSerializer(ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'
        read_only_fields = ['created_on']

class CommitteeSerializer(ModelSerializer):
    class Meta:
        model = Committee
        fields = '__all__'
        read_only_fields = ['created_on']

class BoardSerializer(ModelSerializer):
    class Meta:
        model = Board
        fields = '__all__'
        read_only_fields = ['created_on']

class TeamSerializer(ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ['created_on']

class InstituteSerializer(ModelSerializer):
    class Meta:
        model = Institute
        fields = '__all__'
        read_only_fields = ['created_on']

class ProgramSerializer(ModelSerializer):
    class Meta:
        model = Program
        fields = '__all__'
        read_only_fields = ['created_on']

class CentreSerializer(ModelSerializer):
    class Meta:
        model = Centre
        fields = '__all__'
        read_only_fields = ['created_on']

class ProjectSerializer(ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['created_on']

class OtherOrgUnitSerializer(ModelSerializer):
    class Meta:
        model = OtherOrgUnit
        fields = '__all__'
        read_only_fields = ['created_on']

