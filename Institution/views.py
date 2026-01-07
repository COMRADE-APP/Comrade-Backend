"""
Institution App Views
Includes ViewSets for verification system and hierarchical institutional structures
"""
from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework import status

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

from Institution.serializers import (
    # Verification System Serializers
    InstitutionSerializer,
    InstitutionVerificationDocumentSerializer,
    InstitutionMemberSerializer,
    InstitutionVerificationLogSerializer,
    WebsiteVerificationRequestSerializer,
    OrganizationSerializer,
    # Hierarchical Structure Serializers
    InstBranchSerializer,
    VCOfficeSerializer,
    FacultySerializer,
    InstDepartmentSerializer,
    ProgrammeSerializer,
    AdminDepSerializer,
    RegistrarOfficeSerializer,
    HRSerializer,
    ICTSerializer,
    FinanceSerializer,
    MarketingSerializer,
    LegalSerializer,
    StudentAffairsSerializer,
    AdmissionsSerializer,
    CareerOfficeSerializer,
    CounsellingSerializer,
    SupportServicesSerializer,
    SecuritySerializer,
    TransportSerializer,
    LibrarySerializer,
    CafeteriaSerializer,
    HostelSerializer,
    HealthServicesSerializer,
    OtherInstitutionUnitSerializer,
)


# ============================================================================
# VERIFICATION SYSTEM VIEWSETS
# ============================================================================

class InstitutionViewSet(ModelViewSet):
    """
    ViewSet for Institution with verification workflow support
    """
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def send_email_verification(self, request, pk=None):
        """Send email verification to institution email"""
        institution = self.get_object()
        # TODO: Implement email verification logic
        return Response({
            'message': 'Verification email sent',
            'email': institution.email
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_email(self, request, pk=None):
        """Verify institution email with token"""
        institution = self.get_object()
        token = request.data.get('token')
        
        if institution.email_verification_token == token:
            institution.email_verified = True
            institution.save()
            return Response({'message': 'Email verified successfully'})
        return Response(
            {'error': 'Invalid verification token'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit_for_review(self, request, pk=None):
        """Submit institution for verification review"""
        institution = self.get_object()
        
        if not institution.email_verified:
            return Response(
                {'error': 'Email must be verified before submission'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not institution.documents_submitted:
            return Response(
                {'error': 'Documents must be submitted before review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        institution.status = 'submitted'
        institution.save()
        return Response({'message': 'Institution submitted for review'})
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def members(self, request, pk=None):
        """Get all members of the institution"""
        institution = self.get_object()
        members = institution.members.all()
        serializer = InstitutionMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def invite_member(self, request, pk=None):
        """Invite a user to join the institution"""
        institution = self.get_object()
        # TODO: Implement member invitation logic
        return Response({'message': 'Invitation sent'})
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def verification_logs(self, request, pk=None):
        """Get verification log history"""
        institution = self.get_object()
        logs = institution.verification_logs.all()
        serializer = InstitutionVerificationLogSerializer(logs, many=True)
        return Response(serializer.data)


class InstitutionMemberViewSet(ModelViewSet):
    queryset = InstitutionMember.objects.all()
    serializer_class = InstitutionMemberSerializer
    permission_classes = [IsAuthenticated]


class InstitutionVerificationDocumentViewSet(ModelViewSet):
    queryset = InstitutionVerificationDocument.objects.all()
    serializer_class = InstitutionVerificationDocumentSerializer
    permission_classes = [IsAuthenticated]


class OrganizationViewSet(ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


# ============================================================================
# HIERARCHICAL STRUCTURE VIEWSETS
# ============================================================================

class InstBranchViewSet(ModelViewSet):
    queryset = InstBranch.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = InstBranchSerializer


class VCOfficeViewSet(ModelViewSet):
    queryset = VCOffice.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = VCOfficeSerializer


class FacultyViewSet(ModelViewSet):
    queryset = Faculty.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = FacultySerializer


class InstDepartmentViewSet(ModelViewSet):
    queryset = InstDepartment.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = InstDepartmentSerializer


class ProgrammeViewSet(ModelViewSet):
    queryset = Programme.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ProgrammeSerializer


# Administrative Departments

class AdminDepViewSet(ModelViewSet):
    queryset = AdminDep.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AdminDepSerializer


class RegistrarOfficeViewSet(ModelViewSet):
    queryset = RegistrarOffice.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = RegistrarOfficeSerializer


class HRViewSet(ModelViewSet):
    queryset = HR.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = HRSerializer


class ICTViewSet(ModelViewSet):
    queryset = ICT.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = ICTSerializer


class FinanceViewSet(ModelViewSet):
    queryset = Finance.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = FinanceSerializer


class MarketingViewSet(ModelViewSet):
    queryset = Marketing.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = MarketingSerializer


class LegalViewSet(ModelViewSet):
    queryset = Legal.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = LegalSerializer


# Student Affairs

class StudentAffairsViewSet(ModelViewSet):
    queryset = StudentAffairs.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = StudentAffairsSerializer


class AdmissionsViewSet(ModelViewSet):
    queryset = Admissions.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = AdmissionsSerializer


class CareerOfficeViewSet(ModelViewSet):
    queryset = CareerOffice.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CareerOfficeSerializer


class CounsellingViewSet(ModelViewSet):
    queryset = Counselling.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CounsellingSerializer


# Support Services

class SupportServicesViewSet(ModelViewSet):
    queryset = SupportServices.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = SupportServicesSerializer


class SecurityViewSet(ModelViewSet):
    queryset = Security.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = SecuritySerializer


class TransportViewSet(ModelViewSet):
    queryset = Transport.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = TransportSerializer


class LibraryViewSet(ModelViewSet):
    queryset = Library.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = LibrarySerializer


class CafeteriaViewSet(ModelViewSet):
    queryset = Cafeteria.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CafeteriaSerializer


class HostelViewSet(ModelViewSet):
    queryset = Hostel.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = HostelSerializer


class HealthServicesViewSet(ModelViewSet):
    queryset = HealthServices.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = HealthServicesSerializer


class OtherInstitutionUnitViewSet(ModelViewSet):
    queryset = OtherInstitutionUnit.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = OtherInstitutionUnitSerializer
