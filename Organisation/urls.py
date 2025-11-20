from rest_framework.routers import DefaultRouter
from Organisation.views import OrganisationViewSet, OrgBranchViewSet, DivisionViewSet, DepartmentViewSet, SectionViewSet, TeamViewSet, ProjectViewSet, CentreViewSet, CommitteeViewSet, BoardViewSet, UnitViewSet, InstituteViewSet, ProgramViewSet, OtherOrgUnitViewSet

router = DefaultRouter()
router.register(r'organisation', OrganisationViewSet, basename='organisation')
router.register(r'org_branch', OrgBranchViewSet, basename='org_branch')
router.register(r'division', DivisionViewSet, basename='division')
router.register(r'department', DepartmentViewSet, basename='department')
router.register(r'section', SectionViewSet, basename='section')
router.register(r'team', TeamViewSet, basename='team')
router.register(r'project', ProjectViewSet, basename='project')
router.register(r'centre', CentreViewSet, basename='centre')
router.register(r'committee', CommitteeViewSet, basename='committee')
router.register(r'board', BoardViewSet, basename='board')
router.register(r'unit', UnitViewSet, basename='unit')
router.register(r'institute', InstituteViewSet, basename='institute')
router.register(r'program', ProgramViewSet, basename='program')
router.register(r'other_org_unit', OtherOrgUnitViewSet, basename='other_org_unit')

urlpatterns = [

]

urlpatterns += router.urls