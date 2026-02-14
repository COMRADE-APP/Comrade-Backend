from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit, OrganisationMember
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer


class OrganisationSerializer(ModelSerializer):
    current_user_role = serializers.SerializerMethodField()

    class Meta:
        model = Organisation
        fields = '__all__'
        read_only_fields = ['created_on']

    def get_current_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if obj.created_by == request.user:
                return 'creator'
            try:
                member = OrganisationMember.objects.get(organisation=obj, user=request.user)
                return member.role
            except OrganisationMember.DoesNotExist:
                return None
        return None

    is_following = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(id=request.user.id).exists()
        return False

    def get_followers_count(self, obj):
        return obj.followers.count()

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


# ============================================================================
# MEMBER MANAGEMENT SERIALIZER
# ============================================================================

class OrganisationMemberSerializer(ModelSerializer):
    """Serializer for OrganisationMember with user details"""
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = OrganisationMember
        fields = [
            'id', 'organisation', 'user', 'user_email', 'user_name', 'user_avatar',
            'role', 'title', 'joined_at', 'is_active'
        ]
        read_only_fields = ['joined_at']
    
    def get_user_name(self, obj):
        if obj.user.first_name:
            return f"{obj.user.first_name} {obj.user.last_name or ''}".strip()
        return obj.user.email
    
    def get_user_avatar(self, obj):
        if hasattr(obj.user, 'profile') and obj.user.profile and obj.user.profile.avatar:
            return obj.user.profile.avatar.url
        return None


