from Institution.models import Institution, InstBranch, Faculty, VCOffice, InstDepartment, AdminDep, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport, Library, Hostel, Cafeteria,   OtherInstitutionUnit
from rest_framework.serializers import ModelSerializer

class InstitutionSerializer(ModelSerializer):
    class Meta:
        model = Institution
        fields = '__all__'
        read_only_fields = ['created_at']

class InstBranchSerializer(ModelSerializer):
    class Meta:
        model = InstBranch
        fields = '__all__'
        read_only_fields = ['created_at']

class FacultySerializer(ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'
        read_only_fields = ['created_at']

class VCOfficeSerializer(ModelSerializer):
    class Meta:
        model = VCOffice
        fields = '__all__'
        read_only_fields = ['created_at']

class InstDepartmentSerializer(ModelSerializer):
    class Meta:
        model = InstDepartment
        fields = '__all__'
        read_only_fields = ['created_at']

class AdminDepSerializer(ModelSerializer):
    class Meta:
        model = AdminDep
        fields = '__all__'
        read_only_fields = ['created_at']

class ProgrammeSerializer(ModelSerializer):
    class Meta:
        model = Programme
        fields = '__all__'
        read_only_fields = ['created_at']

class HRSerializer(ModelSerializer):
    class Meta:
        model = HR
        fields = '__all__'
        read_only_fields = ['created_at']

class AdmissionsSerializer(ModelSerializer):
    class Meta:
        model = Admissions
        fields = '__all__'
        read_only_fields = ['created_at']

class HealthServicesSerializer(ModelSerializer):
    class Meta:
        model = HealthServices
        fields = '__all__'
        read_only_fields = ['created_at']

class SecuritySerializer(ModelSerializer):
    class Meta:
        model = Security
        fields = '__all__'
        read_only_fields = ['created_at']

class StudentAffairsSerializer(ModelSerializer):
    class Meta:
        model = StudentAffairs
        fields = '__all__'
        read_only_fields = ['created_at']

class SupportServicesSerializer(ModelSerializer):
    class Meta:
        model = SupportServices
        fields = '__all__'
        read_only_fields = ['created_at']

class FinanceSerializer(ModelSerializer):
    class Meta:
        model = Finance
        fields = '__all__'
        read_only_fields = ['created_at']

class MarketingSerializer(ModelSerializer):
    class Meta:
        model = Marketing
        fields = '__all__'
        read_only_fields = ['created_at']

class LegalSerializer(ModelSerializer):
    class Meta:
        model = Legal
        fields = '__all__'
        read_only_fields = ['created_at']

class ICTSerializer(ModelSerializer):
    class Meta:
        model = ICT
        fields = '__all__'
        read_only_fields = ['created_at']

class CareerOfficeSerializer(ModelSerializer):
    class Meta:
        model = CareerOffice
        fields = '__all__'
        read_only_fields = ['created_at']

class CounsellingSerializer(ModelSerializer):
    class Meta:
        model = Counselling
        fields = '__all__'
        read_only_fields = ['created_at']

class RegistrarOfficeSerializer(ModelSerializer):
    class Meta:
        model = RegistrarOffice
        fields = '__all__'
        read_only_fields = ['created_at']

class TransportSerializer(ModelSerializer):
    class Meta:
        model = Transport
        fields = '__all__'
        read_only_fields = ['created_at']

class LibrarySerializer(ModelSerializer):
    class Meta:
        model = Library
        fields = '__all__'
        read_only_fields = ['created_at']

class HostelSerializer(ModelSerializer):
    class Meta:
        model = Hostel
        fields = '__all__'
        read_only_fields = ['created_at']

class CafeteriaSerializer(ModelSerializer):
    class Meta:
        model = Cafeteria
        fields = '__all__'
        read_only_fields = ['created_at']

class OtherInstitutionUnitSerializer(ModelSerializer):
    class Meta:
        model = OtherInstitutionUnit
        fields = '__all__'
        read_only_fields = ['created_at']
        

