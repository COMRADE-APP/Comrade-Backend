"""
Institution URLs Configuration
Routes for verification system and hierarchical structure endpoints
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Institution.views import (
    # Verification System ViewSets
    InstitutionViewSet,
    InstitutionMemberViewSet,
    InstitutionVerificationDocumentViewSet,
    OrganizationViewSet,
    #Hierarchical Structure ViewSets
    InstBranchViewSet,
    VCOfficeViewSet,
    FacultyViewSet,
    InstDepartmentViewSet,
    ProgrammeViewSet,
    AdminDepViewSet,
    RegistrarOfficeViewSet,
    HRViewSet,
    ICTViewSet,
    FinanceViewSet,
    MarketingViewSet,
    LegalViewSet,
    StudentAffairsViewSet,
    AdmissionsViewSet,
    CareerOfficeViewSet,
    CounsellingViewSet,
    SupportServicesViewSet,
    SecurityViewSet,
    TransportViewSet,
    LibraryViewSet,
    CafeteriaViewSet,
    HostelViewSet,
    HealthServicesViewSet,
    OtherInstitutionUnitViewSet,
)
from Institution.views_portal import DocumentUploadView

router = DefaultRouter()

# Verification System Routes
router.register(r'institutions', InstitutionViewSet, basename='institution')
router.register(r'members', InstitutionMemberViewSet, basename='institution-member')
router.register(r'documents', InstitutionVerificationDocumentViewSet, basename='verification-document')
router.register(r'organizations', OrganizationViewSet, basename='organization')

# Hierarchical Structure Routes
# Hierarchical Structure Routes
router.register(r'inst-branches', InstBranchViewSet, basename='inst-branch')
router.register(r'vc-offices', VCOfficeViewSet, basename='vc-office')
router.register(r'faculties', FacultyViewSet, basename='faculty')
router.register(r'inst-departments', InstDepartmentViewSet, basename='inst-department')
router.register(r'programmes', ProgrammeViewSet, basename='programme')

# Administrative
router.register(r'admin-departments', AdminDepViewSet, basename='admin-dep')
router.register(r'registrar-offices', RegistrarOfficeViewSet, basename='registrar-office')
router.register(r'hr', HRViewSet, basename='hr')
router.register(r'ict', ICTViewSet, basename='ict')
router.register(r'finance', FinanceViewSet, basename='finance')
router.register(r'marketing', MarketingViewSet, basename='marketing')
router.register(r'legal', LegalViewSet, basename='legal')

# Student Affairs
router.register(r'student-affairs', StudentAffairsViewSet, basename='student-affairs')
router.register(r'admissions', AdmissionsViewSet, basename='admissions')
router.register(r'career-offices', CareerOfficeViewSet, basename='career-office')
router.register(r'counselling', CounsellingViewSet, basename='counselling')

# Support Services
router.register(r'support-services', SupportServicesViewSet, basename='support-services')
router.register(r'security', SecurityViewSet, basename='security')
router.register(r'transport', TransportViewSet, basename='transport')
router.register(r'libraries', LibraryViewSet, basename='library')
router.register(r'cafeterias', CafeteriaViewSet, basename='cafeteria')
router.register(r'hostels', HostelViewSet, basename='hostel')
router.register(r'health-services', HealthServicesViewSet, basename='health-services')

# Other Units
router.register(r'other-units', OtherInstitutionUnitViewSet, basename='other-unit')

urlpatterns = [
    path('', include(router.urls)),
    # Legacy document upload endpoint (for compatibility with frontend)
    path('institutions/<uuid:institution_id>/documents/', DocumentUploadView.as_view(), name='upload-document'),
]
