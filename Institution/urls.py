from rest_framework.routers import DefaultRouter
from Institution.views import InstitutionViewSet, InstBranchViewSet, FacultyViewSet, VCOfficeViewSet, InstDepartmentViewSet, AdminDepViewSet, ProgrammeViewSet, HRViewSet, AdmissionsViewSet, HealthServicesViewSet, SecurityViewSet, StudentAffairsViewSet, SupportServicesViewSet, FinanceViewSet, MarketingViewSet, LegalViewSet, ICTViewSet, CareerOfficeViewSet, CounsellingViewSet, RegistrarOfficeViewSet, TransportViewSet, LibraryViewSet, HostelViewSet, CafeteriaViewSet, OtherInstitutionUnitViewSet


router = DefaultRouter()


router.register(r'institution', InstitutionViewSet, basename='institution')
router.register(r'inst_branch', InstBranchViewSet, basename='inst_branch')
router.register(r'faculty', FacultyViewSet, basename='faculty')
router.register(r'vc_office', VCOfficeViewSet, basename='vc_office')
router.register(r'inst_department', InstDepartmentViewSet, basename='inst_department')
router.register(r'admin_dep', AdminDepViewSet, basename='admin_dep')
router.register(r'programme', ProgrammeViewSet, basename='programme')
router.register(r'hr', HRViewSet, basename='hr')
router.register(r'admissions', AdmissionsViewSet, basename='admissions')
router.register(r'health_services', HealthServicesViewSet, basename='health_services')
router.register(r'security', SecurityViewSet, basename='security')
router.register(r'student_affairs', StudentAffairsViewSet, basename='student_affairs')
router.register(r'support_services', SupportServicesViewSet, basename='support_services')
router.register(r'finance', FinanceViewSet, basename='finance')
router.register(r'marketing', MarketingViewSet, basename='marketing')
router.register(r'legal', LegalViewSet, basename='legal')
router.register(r'ict', ICTViewSet, basename='ict')
router.register(r'career_office', CareerOfficeViewSet, basename='career_office')
router.register(r'counselling', CounsellingViewSet, basename='counselling')
router.register(r'registrar_office', RegistrarOfficeViewSet, basename='registrar_office')
router.register(r'transport', TransportViewSet, basename='transport')
router.register(r'library', LibraryViewSet, basename='library')
router.register(r'hostel', HostelViewSet, basename='hostel')
router.register(r'cafeteria', CafeteriaViewSet, basename='cafeteria')
router.register(r'other_institution_unit', OtherInstitutionUnitViewSet, basename='other_institution_unit')


urlpatterns = [

]
urlpatterns += router.urls
