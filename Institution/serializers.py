"""
Institution App Serializers
Includes serializers for verification system and hierarchical institutional structures
"""
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from Institution.models import (
    # Verification System Models
    Institution,
    InstitutionVerificationDocument,
    InstitutionMember,
    InstitutionVerificationLog,
    WebsiteVerificationRequest,
    Organization,
    # Hierarchical Structure Models
    InstBranch,
    VCOffice,
    Faculty,
    InstDepartment,
    Programme,
    AdminDep,
    RegistrarOffice,
    HR,
    ICT,
    Finance,
    Marketing,
    Legal,
    StudentAffairs,
    Admissions,
    CareerOffice,
    Counselling,
    SupportServices,
    Security,
    Transport,
    Library,
    Cafeteria,
    Hostel,
    HealthServices,
    OtherInstitutionUnit,
)


# ============================================================================
# VERIFICATION SYSTEM SERIALIZERS
# ============================================================================

class InstitutionSerializer(ModelSerializer):
    class Meta:
        model = Institution
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'verified_at', 'submitted_at']

    current_user_role = serializers.SerializerMethodField()

    def get_current_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if obj.created_by == request.user:
                return 'creator'
            try:
                member = InstitutionMember.objects.get(institution=obj, user=request.user)
                return member.role
            except InstitutionMember.DoesNotExist:
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


class InstitutionVerificationDocumentSerializer(ModelSerializer):
    class Meta:
        model = InstitutionVerificationDocument
        fields = '__all__'
        read_only_fields = ['uploaded_at', 'uploaded_by', 'verified_at', 'verified_by']


class InstitutionMemberSerializer(ModelSerializer):
    class Meta:
        model = InstitutionMember
        fields = '__all__'
        read_only_fields = ['joined_at', 'updated_at', 'invited_by']


class InstitutionVerificationLogSerializer(ModelSerializer):
    class Meta:
        model = InstitutionVerificationLog
        fields = '__all__'
        read_only_fields = ['timestamp', 'performed_by']


class WebsiteVerificationRequestSerializer(ModelSerializer):
    class Meta:
        model = WebsiteVerificationRequest
        fields = '__all__'
        read_only_fields = ['created_at', 'verified_at']


class OrganizationSerializer(ModelSerializer):
    class Meta:
        model = Organization
        fields = '__all__'
        read_only_fields = ['created_at', 'verified_at', 'created_by']


# ============================================================================
# HIERARCHICAL STRUCTURE SERIALIZERS
# ============================================================================

class InstBranchSerializer(ModelSerializer):
    class Meta:
        model = InstBranch
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class VCOfficeSerializer(ModelSerializer):
    class Meta:
        model = VCOffice
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class FacultySerializer(ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class InstDepartmentSerializer(ModelSerializer):
    class Meta:
        model = InstDepartment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ProgrammeSerializer(ModelSerializer):
    class Meta:
        model = Programme
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# Administrative Departments

class AdminDepSerializer(ModelSerializer):
    class Meta:
        model = AdminDep
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class RegistrarOfficeSerializer(ModelSerializer):
    class Meta:
        model = RegistrarOffice
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class HRSerializer(ModelSerializer):
    class Meta:
        model = HR
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ICTSerializer(ModelSerializer):
    class Meta:
        model = ICT
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class FinanceSerializer(ModelSerializer):
    class Meta:
        model = Finance
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class MarketingSerializer(ModelSerializer):
    class Meta:
        model = Marketing
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class LegalSerializer(ModelSerializer):
    class Meta:
        model = Legal
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# Student Affairs

class StudentAffairsSerializer(ModelSerializer):
    class Meta:
        model = StudentAffairs
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class AdmissionsSerializer(ModelSerializer):
    class Meta:
        model = Admissions
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CareerOfficeSerializer(ModelSerializer):
    class Meta:
        model = CareerOffice
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CounsellingSerializer(ModelSerializer):
    class Meta:
        model = Counselling
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# Support Services

class SupportServicesSerializer(ModelSerializer):
    class Meta:
        model = SupportServices
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class SecuritySerializer(ModelSerializer):
    class Meta:
        model = Security
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TransportSerializer(ModelSerializer):
    class Meta:
        model = Transport
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class LibrarySerializer(ModelSerializer):
    class Meta:
        model = Library
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class CafeteriaSerializer(ModelSerializer):
    class Meta:
        model = Cafeteria
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class HostelSerializer(ModelSerializer):
    class Meta:
        model = Hostel
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class HealthServicesSerializer(ModelSerializer):
    class Meta:
        model = HealthServices
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


# Other Units

class OtherInstitutionUnitSerializer(ModelSerializer):
    class Meta:
        model = OtherInstitutionUnit
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
