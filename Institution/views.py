from django.shortcuts import render
from Institution.models import Institution, InstBranch, Faculty, VCOffice, InstDepartment, AdminDep, Programme, HR, Admissions, HealthServices, Security, StudentAffairs, SupportServices, Finance, Marketing, Legal, ICT, CareerOffice, Counselling, RegistrarOffice, Transport, Library, Hostel, Cafeteria
from Institution.serializers import InstitutionSerializer, InstBranchSerializer, FacultySerializer, VCOfficeSerializer, InstDepartmentSerializer, AdminDepSerializer, ProgrammeSerializer, HRSerializer, AdmissionsSerializer, HealthServicesSerializer, SecuritySerializer, StudentAffairsSerializer, SupportServicesSerializer, FinanceSerializer, MarketingSerializer, LegalSerializer, ICTSerializer, CareerOfficeSerializer, CounsellingSerializer, RegistrarOfficeSerializer, TransportSerializer, LibrarySerializer, HostelSerializer, CafeteriaSerializer
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly


# Create your views here.
class InstitutionViewSet(ModelViewSet):
    queryset = Institution.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = InstitutionSerializer

class InstBranchViewSet(ModelViewSet):
    queryset = InstBranch.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = InstBranchSerializer

class FacultyViewSet(ModelViewSet):
    queryset = Faculty.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = FacultySerializer

class VCOfficeViewSet(ModelViewSet):
    queryset = VCOffice.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = VCOfficeSerializer

class InstDepartmentViewSet(ModelViewSet):
    queryset = InstDepartment.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = InstDepartmentSerializer

class AdmissionsViewSet(ModelViewSet):
    queryset = Admissions.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AdmissionsSerializer

class AdminDepViewSet(ModelViewSet):
    queryset = AdminDep.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AdminDepSerializer

class ProgrammeViewSet(ModelViewSet):
    queryset = Programme.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ProgrammeSerializer

class HRViewSet(ModelViewSet):
    queryset = HR.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = HRSerializer

class HealthServicesViewSet(ModelViewSet):
    queryset = HealthServices.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = HealthServicesSerializer

class SecurityViewSet(ModelViewSet):
    queryset = Security.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = SecuritySerializer

class StudentAffairsViewSet(ModelViewSet):
    queryset = StudentAffairs.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = StudentAffairsSerializer

class SupportServicesViewSet(ModelViewSet):
    queryset = SupportServices.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = SupportServicesSerializer

class FinanceViewSet(ModelViewSet):
    queryset = Finance.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = FinanceSerializer

class MarketingViewSet(ModelViewSet):
    queryset = Marketing.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = MarketingSerializer

class CareerOfficeViewSet(ModelViewSet):
    queryset = CareerOffice.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CareerOfficeSerializer

class LegalViewSet(ModelViewSet):
    queryset = Legal.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = LegalSerializer

class ICTViewSet(ModelViewSet):
    queryset = ICT.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ICTSerializer

class CounsellingViewSet(ModelViewSet):
    queryset = Counselling.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CounsellingSerializer

class TransportViewSet(ModelViewSet):
    queryset = Transport.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = TransportSerializer

class RegistrarOfficeViewSet(ModelViewSet):
    queryset = RegistrarOffice.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = RegistrarOfficeSerializer

class LibraryViewSet(ModelViewSet):
    queryset = Library.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = LibrarySerializer

class HostelViewSet(ModelViewSet):
    queryset = Hostel.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = HostelSerializer

class CafeteriaViewSet(ModelViewSet):
    queryset = Cafeteria.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CafeteriaSerializer
