from django.shortcuts import render
from Organisation.models import Organisation, OrgBranch, Division, Department, Section, Team, Project, Centre, Committee, Board, Unit, Institute, Program, OtherOrgUnit, OrganisationMember
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny, IsAuthenticated
from Organisation.serializers import OrganisationSerializer, OrgBranchSerializer, DivisionSerializer, DepartmentSerializer, SectionSerializer, TeamSerializer, ProjectSerializer, CentreSerializer, CommitteeSerializer, BoardSerializer, UnitSerializer, InstituteSerializer, ProgramSerializer, OtherOrgUnitSerializer, OrganisationMemberSerializer


# Create your views here.
class OrganisationViewSet(ModelViewSet):
    queryset = Organisation.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = OrganisationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset
    
    def perform_create(self, serializer):
        print(self.request.data)
        """Set created_by to the authenticated user"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        organisation = self.get_object()
        if organisation.followers.filter(id=request.user.id).exists():
             return Response({'detail': 'Already following'}, status=status.HTTP_400_BAD_REQUEST)
        organisation.followers.add(request.user)
        return Response({'status': 'followed', 'followers_count': organisation.followers.count()})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        organisation = self.get_object()
        if not organisation.followers.filter(id=request.user.id).exists():
             return Response({'detail': 'Not following'}, status=status.HTTP_400_BAD_REQUEST)
        organisation.followers.remove(request.user)
        return Response({'status': 'unfollowed', 'followers_count': organisation.followers.count()})
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of the organisation"""
        organisation = self.get_object()
        members = OrganisationMember.objects.filter(organisation=organisation, is_active=True)
        serializer = OrganisationMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """Get all branches of the organisation"""
        organisation = self.get_object()
        branches = OrgBranch.objects.filter(organisation=organisation)
        serializer = OrgBranchSerializer(branches, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        """Get full hierarchy of the organisation"""
        organisation = self.get_object()
        hierarchy = {
            'branches': OrgBranchSerializer(OrgBranch.objects.filter(organisation=organisation), many=True).data,
            'divisions': DivisionSerializer(Division.objects.filter(organisation=organisation), many=True).data,
            'committees': CommitteeSerializer(Committee.objects.filter(organisation=organisation), many=True).data,
            'boards': BoardSerializer(Board.objects.filter(organisation=organisation), many=True).data,
            'projects': ProjectSerializer(Project.objects.filter(organisation=organisation), many=True).data,
            'programs': ProgramSerializer(Program.objects.filter(organisation=organisation), many=True).data,
            'centres': CentreSerializer(Centre.objects.filter(organisation=organisation), many=True).data,
            'institutes': InstituteSerializer(Institute.objects.filter(organisation=organisation), many=True).data,
        }
        return Response(hierarchy)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_portal_password(self, request, pk=None):
        """Set or update portal password for entity account switching"""
        organisation = self.get_object()
        user = request.user
        
        # Only creator or admin can set portal password
        is_authorized = (organisation.created_by == user or
            OrganisationMember.objects.filter(
                organisation=organisation, user=user, role='admin', is_active=True
            ).exists())
        
        if not is_authorized:
            return Response({'error': 'Only the creator or admin can set the portal password'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        password = request.data.get('password')
        password_type = request.data.get('password_type', 'pin')
        
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if password_type == 'pin' and (not password.isdigit() or len(password) < 4):
            return Response({'error': 'PIN must be at least 4 digits'}, status=status.HTTP_400_BAD_REQUEST)
        
        if password_type == 'password' and len(password) < 6:
            return Response({'error': 'Password must be at least 6 characters'}, status=status.HTTP_400_BAD_REQUEST)
        
        organisation.portal_password_type = password_type
        organisation.set_portal_password(password)
        return Response({'message': 'Portal password set successfully'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_portal_password(self, request, pk=None):
        """Verify portal password for account switching"""
        organisation = self.get_object()
        user = request.user
        
        # Must be a member or creator
        is_member = (organisation.created_by == user or
            OrganisationMember.objects.filter(
                organisation=organisation, user=user, is_active=True
            ).exists())
        
        if not is_member:
            return Response({'error': 'You are not a member of this organisation'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        if not organisation.has_portal_password():
            return Response({'verified': True, 'message': 'No portal password set'})
        
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if organisation.check_portal_password(password):
            return Response({'verified': True, 'message': 'Password verified'})
        else:
            return Response({'verified': False, 'error': 'Incorrect password'}, 
                          status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_organizations(self, request):
        """Get organizations where current user is a member (for account switching)"""
        user = request.user
        # Get orgs where user is a member
        memberships = OrganisationMember.objects.filter(user=user, is_active=True).select_related('organisation')
        # Also include orgs created by the user
        created_orgs = Organisation.objects.filter(created_by=user)
        
        accounts = []
        seen_ids = set()
        
        # Add memberships
        for membership in memberships:
            org = membership.organisation
            if org.id not in seen_ids:
                accounts.append({
                    'id': str(org.id),
                    'name': org.name,
                    'type': 'organisation',
                    'avatar': org.profile_picture.url if org.profile_picture else None,
                    'role': membership.role,
                    'has_portal_password': org.has_portal_password(),
                })
                seen_ids.add(org.id)
        
        # Add created orgs
        for org in created_orgs:
            if org.id not in seen_ids:
                accounts.append({
                    'id': str(org.id),
                    'name': org.name,
                    'type': 'organisation',
                    'avatar': org.profile_picture.url if org.profile_picture else None,
                    'role': 'creator',
                    'has_portal_password': org.has_portal_password(),
                })
                seen_ids.add(org.id)
        
        return Response(accounts)

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
    

# ============================================================================
# MEMBER MANAGEMENT VIEWSET
# ============================================================================

class OrganisationMemberViewSet(ModelViewSet):
    """ViewSet for managing organisation members with title editing"""
    queryset = OrganisationMember.objects.all()
    serializer_class = OrganisationMemberSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by organisation if provided
        org_id = self.request.query_params.get('organisation')
        if org_id:
            queryset = queryset.filter(organisation_id=org_id)
        return queryset.filter(is_active=True)
    
    def perform_create(self, serializer):
        """Add member to organisation"""
        serializer.save()
    
    @action(detail=True, methods=['patch'])
    def update_title(self, request, pk=None):
        """Update member's title"""
        member = self.get_object()
        title = request.data.get('title', '')
        member.title = title
        member.save()
        serializer = self.get_serializer(member)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_role(self, request, pk=None):
        """Update member's role (requires admin permission)"""
        member = self.get_object()
        role = request.data.get('role')
        if role not in ['admin', 'moderator', 'member']:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
        member.role = role
        member.save()
        serializer = self.get_serializer(member)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate member (soft delete)"""
        member = self.get_object()
        member.is_active = False
        member.save()
        return Response({'status': 'Member deactivated'})
