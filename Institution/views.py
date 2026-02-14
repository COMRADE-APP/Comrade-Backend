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
    
    def perform_create(self, serializer):
        """Set created_by to the authenticated user"""
        serializer.save(created_by=self.request.user, is_active=True)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def follow(self, request, pk=None):
        institution = self.get_object()
        if institution.followers.filter(id=request.user.id).exists():
             return Response({'detail': 'Already following'}, status=status.HTTP_400_BAD_REQUEST)
        institution.followers.add(request.user)
        return Response({'status': 'followed', 'followers_count': institution.followers.count()})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk=None):
        institution = self.get_object()
        if not institution.followers.filter(id=request.user.id).exists():
             return Response({'detail': 'Not following'}, status=status.HTTP_400_BAD_REQUEST)
        institution.followers.remove(request.user)
        return Response({'status': 'unfollowed', 'followers_count': institution.followers.count()})
    
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_institutions(self, request):
        """Get institutions where current user is a member (for account switching)"""
        user = request.user
        # Get institutions where user is a member
        memberships = InstitutionMember.objects.filter(user=user).select_related('institution')
        # Also include institutions created by the user
        created_institutions = Institution.objects.filter(created_by=user)
        
        accounts = []
        seen_ids = set()
        
        # Add memberships
        for membership in memberships:
            inst = membership.institution
            if inst.id not in seen_ids:
                accounts.append({
                    'id': str(inst.id),
                    'name': inst.name,
                    'type': 'institution',
                    'avatar': inst.logo_url,
                    'role': membership.role
                })
                seen_ids.add(inst.id)
        
        # Add created institutions
        for inst in created_institutions:
            if inst.id not in seen_ids:
                accounts.append({
                    'id': str(inst.id),
                    'name': inst.name,
                    'type': 'institution',
                    'avatar': inst.logo_url,
                    'role': 'creator'
                })
                seen_ids.add(inst.id)
        
        return Response(accounts)


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
    
    def get_queryset(self):
        """Filter to show only approved units to non-admins"""
        qs = super().get_queryset()
        institution_id = self.request.query_params.get('institution')
        if institution_id:
            qs = qs.filter(institution_id=institution_id)
        # Only show approved units to general users
        if not self.request.user.is_staff:
            qs = qs.filter(approval_status='approved')
        return qs
    
    def perform_create(self, serializer):
        """Auto-approve if user is institution creator/admin, else pending"""
        institution_id = self.request.data.get('institution')
        user = self.request.user
        is_admin = False
        
        if institution_id:
            try:
                institution = Institution.objects.get(pk=institution_id)
                is_admin = (institution.created_by == user or 
                           InstitutionMember.objects.filter(
                               institution=institution, 
                               user=user, 
                               role__in=['creator', 'admin']
                           ).exists())
            except Institution.DoesNotExist:
                pass
        
        serializer.save(
            created_by=user,
            approval_status='approved' if is_admin else 'pending'
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending_units(self, request):
        """Get pending units for institutions where user is admin"""
        institution_id = request.query_params.get('institution')
        if not institution_id:
            return Response({'error': 'institution query param required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is admin
        try:
            institution = Institution.objects.get(pk=institution_id)
            is_admin = (institution.created_by == request.user or 
                       InstitutionMember.objects.filter(
                           institution=institution, 
                           user=request.user, 
                           role__in=['creator', 'admin']
                       ).exists())
            if not is_admin:
                return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        except Institution.DoesNotExist:
            return Response({'error': 'Institution not found'}, status=status.HTTP_404_NOT_FOUND)
        
        pending = InstBranch.objects.filter(institution_id=institution_id, approval_status='pending')
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        """Approve a pending unit"""
        from datetime import datetime
        unit = self.get_object()
        
        # Check if user is admin of the institution
        institution = unit.institution
        is_admin = (institution.created_by == request.user or 
                   InstitutionMember.objects.filter(
                       institution=institution, 
                       user=request.user, 
                       role__in=['creator', 'admin']
                   ).exists())
        if not is_admin:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        unit.approval_status = 'approved'
        unit.approved_by = request.user
        unit.approved_at = datetime.now()
        unit.save()
        return Response({'status': 'approved', 'id': str(unit.id)})
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """Reject a pending unit"""
        unit = self.get_object()
        
        # Check if user is admin of the institution
        institution = unit.institution
        is_admin = (institution.created_by == request.user or 
                   InstitutionMember.objects.filter(
                       institution=institution, 
                       user=request.user, 
                       role__in=['creator', 'admin']
                   ).exists())
        if not is_admin:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        unit.approval_status = 'rejected'
        unit.rejection_reason = request.data.get('reason', '')
        unit.save()
        return Response({'status': 'rejected', 'id': str(unit.id)})




class BaseUnitViewSet(ModelViewSet):
    """
    Base ViewSet for all Institution Units.
    Handles:
    1. Flexible creation (linking to Institution/Branch).
    2. Standardized filtering by Institution unique ID.
    3. Permission/Visibility logic (Admins see pending, others see approved).
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        # 1. Filter by Institution
        institution_id = self.request.query_params.get('institution')
        if institution_id:
            # Handle models that link via 'institution' or 'department__institution' etc.
            # Using a generic approach might be tricky, but most have 'institution' field now.
            if hasattr(self.queryset.model, 'institution'):
                qs = qs.filter(institution_id=institution_id)
            elif hasattr(self.queryset.model, 'department'): # For Programme
                qs = qs.filter(department__institution_id=institution_id)
            elif hasattr(self.queryset.model, 'admin_dep'): # For HR, ICT, etc
                 qs = qs.filter(admin_dep__institution_id=institution_id)
            # Note: With my previous model update, MOST units now have direct 'institution' FK.
            # So standard filtering works for 90% of cases.
            
            # Fallback for old records or complex paths if fields are missing?
            # My previous update ADDED 'institution' field to almost all models.
            # So simple filtering should work for new records.
            # For mixed records, the ORM filter below handles the direct field.
            
            # Since I added 'institution' field to ALL unit models, we can rely on it.
            # However, we must ensure the query param is respected.
            pass

        # To be safe and utilize the direct field I added:
        if institution_id and hasattr(self.queryset.model, 'institution'):
             qs = qs.filter(institution_id=institution_id)

        # 2. Filter by Approval Status
        # If user is NOT staff (System Admin) and NOT Institution Admin, hide pending.
        user = self.request.user
        if not user.is_staff:
            is_inst_admin = False
            if institution_id:
                try:
                    # Check if user is creator or member-admin of this institution
                    # We can optimistically check without hitting DB if we trust logic elsewhere,
                    # but DB check is safer.
                    from Institution.models import Institution, InstitutionMember
                    is_inst_admin = Institution.objects.filter(
                        id=institution_id, 
                        created_by=user
                    ).exists() or InstitutionMember.objects.filter(
                        institution_id=institution_id,
                        user=user,
                        role__in=['creator', 'admin']
                    ).exists()
                except:
                    pass
            
            if not is_inst_admin:
                # General public or regular members only see approved units
                if hasattr(self.queryset.model, 'approval_status'):
                    qs = qs.filter(approval_status='approved')
        
        return qs

    def perform_create(self, serializer):
        institution_id = self.request.data.get('institution')
        branch_id = self.request.data.get('inst_branch')
        user = self.request.user
        is_admin = False
        
        # Check permissions
        if institution_id:
            try:
                institution = Institution.objects.get(pk=institution_id)
                is_admin = (institution.created_by == user or 
                           InstitutionMember.objects.filter(
                               institution=institution, 
                               user=user, 
                               role__in=['creator', 'admin']
                           ).exists())
            except Institution.DoesNotExist:
                pass
        
        save_kwargs = {
            'created_by': user,
            'approval_status': 'approved' if is_admin else 'pending'
        }
        
        if institution_id:
            save_kwargs['institution_id'] = institution_id
        if branch_id:
            save_kwargs['inst_branch_id'] = branch_id
            
        serializer.save(**save_kwargs)


class InstBranchViewSet(BaseUnitViewSet):
    queryset = InstBranch.objects.all()
    serializer_class = InstBranchSerializer
    
    # Specific actions like pending_units, approve, reject need to be preserved/refactored
    # For now, I'll keep the custom actions from the original ViewSet
    # But I should copy them here since I'm overwriting the class.
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending_units(self, request):
        return self._pending_units_logic(request)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        return self._approve_logic(request)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        return self._reject_logic(request)

    # Helper methods to avoid code duplication if I wanted to share this logic
    # But for now, keeping it simple by defining generic actions on BaseUnitViewSet?
    # Yes, moving approve/reject to BaseUnitViewSet is smart.

class BaseUnitViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        institution_id = self.request.query_params.get('institution')
        if institution_id and hasattr(self.queryset.model, 'institution'):
             qs = qs.filter(institution_id=institution_id)

        user = self.request.user
        # System admin sees everything
        if user.is_staff:
            return qs

        # Check if Institution Admin
        is_inst_admin = False
        if institution_id:
            try:
                is_inst_admin = Institution.objects.filter(id=institution_id, created_by=user).exists()
                if not is_inst_admin:
                    is_inst_admin = InstitutionMember.objects.filter(
                        institution_id=institution_id, user=user, role__in=['creator', 'admin']
                    ).exists()
            except:
                pass
        
        if not is_inst_admin:
             if hasattr(self.queryset.model, 'approval_status'):
                qs = qs.filter(approval_status='approved')
        
        return qs

    def perform_create(self, serializer):
        institution_id = self.request.data.get('institution')
        branch_id = self.request.data.get('inst_branch')
        user = self.request.user
        is_admin = False
        
        if institution_id:
            try:
                institution = Institution.objects.get(pk=institution_id)
                is_admin = (institution.created_by == user or 
                           InstitutionMember.objects.filter(
                               institution=institution, user=user, role__in=['creator', 'admin']
                           ).exists())
            except Institution.DoesNotExist:
                pass
        
        save_kwargs = {
            'created_by': user,
            'approval_status': 'approved' if is_admin else 'pending'
        }
        if institution_id: save_kwargs['institution_id'] = institution_id
        if branch_id: save_kwargs['inst_branch_id'] = branch_id
        
        serializer.save(**save_kwargs)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending_units(self, request):
        institution_id = request.query_params.get('institution')
        if not institution_id:
            return Response({'error': 'institution query param required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Auth check
        is_admin = Institution.objects.filter(id=institution_id, created_by=request.user).exists()
        if not is_admin:
            is_admin = InstitutionMember.objects.filter(
                institution_id=institution_id, user=request.user, role__in=['creator', 'admin']
            ).exists()
        
        if not is_admin:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
            
        qs = self.queryset.filter(institution_id=institution_id, approval_status='pending')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        unit = self.get_object()
        institution = getattr(unit, 'institution', None)
        if not institution: return Response({'error': 'Unit not linked to institution'}, status=400)

        is_admin = (institution.created_by == request.user or 
                   InstitutionMember.objects.filter(institution=institution, user=request.user, role__in=['creator', 'admin']).exists())
        
        if not is_admin: return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        unit.approval_status = 'approved'
        unit.approved_by = request.user
        unit.approved_at = datetime.now()
        unit.save()
        return Response({'status': 'approved', 'id': str(unit.id)})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        unit = self.get_object()
        institution = getattr(unit, 'institution', None)
        if not institution: return Response({'error': 'Unit not linked to institution'}, status=400)

        is_admin = (institution.created_by == request.user or 
                   InstitutionMember.objects.filter(institution=institution, user=request.user, role__in=['creator', 'admin']).exists())
        
        if not is_admin: return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        unit.approval_status = 'rejected'
        unit.rejection_reason = request.data.get('reason', '')
        unit.save()
        return Response({'status': 'rejected', 'id': str(unit.id)})


# Implementations

class VCOfficeViewSet(BaseUnitViewSet):
    queryset = VCOffice.objects.all()
    serializer_class = VCOfficeSerializer

class FacultyViewSet(BaseUnitViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer

class InstDepartmentViewSet(BaseUnitViewSet):
    queryset = InstDepartment.objects.all()
    serializer_class = InstDepartmentSerializer

class ProgrammeViewSet(BaseUnitViewSet):
    queryset = Programme.objects.all()
    serializer_class = ProgrammeSerializer

class InstBranchViewSet(BaseUnitViewSet):
    queryset = InstBranch.objects.all()
    serializer_class = InstBranchSerializer

class AdminDepViewSet(BaseUnitViewSet):
    queryset = AdminDep.objects.all()
    serializer_class = AdminDepSerializer

class RegistrarOfficeViewSet(BaseUnitViewSet):
    queryset = RegistrarOffice.objects.all()
    serializer_class = RegistrarOfficeSerializer

class HRViewSet(BaseUnitViewSet):
    queryset = HR.objects.all()
    serializer_class = HRSerializer

class ICTViewSet(BaseUnitViewSet):
    queryset = ICT.objects.all()
    serializer_class = ICTSerializer

class FinanceViewSet(BaseUnitViewSet):
    queryset = Finance.objects.all()
    serializer_class = FinanceSerializer

class MarketingViewSet(BaseUnitViewSet):
    queryset = Marketing.objects.all()
    serializer_class = MarketingSerializer

class LegalViewSet(BaseUnitViewSet):
    queryset = Legal.objects.all()
    serializer_class = LegalSerializer

class StudentAffairsViewSet(BaseUnitViewSet):
    queryset = StudentAffairs.objects.all()
    serializer_class = StudentAffairsSerializer

class AdmissionsViewSet(BaseUnitViewSet):
    queryset = Admissions.objects.all()
    serializer_class = AdmissionsSerializer

class CareerOfficeViewSet(BaseUnitViewSet):
    queryset = CareerOffice.objects.all()
    serializer_class = CareerOfficeSerializer

class CounsellingViewSet(BaseUnitViewSet):
    queryset = Counselling.objects.all()
    serializer_class = CounsellingSerializer

class SupportServicesViewSet(BaseUnitViewSet):
    queryset = SupportServices.objects.all()
    serializer_class = SupportServicesSerializer

class SecurityViewSet(BaseUnitViewSet):
    queryset = Security.objects.all()
    serializer_class = SecuritySerializer

class TransportViewSet(BaseUnitViewSet):
    queryset = Transport.objects.all()
    serializer_class = TransportSerializer

class LibraryViewSet(BaseUnitViewSet):
    queryset = Library.objects.all()
    serializer_class = LibrarySerializer

class CafeteriaViewSet(BaseUnitViewSet):
    queryset = Cafeteria.objects.all()
    serializer_class = CafeteriaSerializer

class HostelViewSet(BaseUnitViewSet):
    queryset = Hostel.objects.all()
    serializer_class = HostelSerializer

class HealthServicesViewSet(BaseUnitViewSet):
    queryset = HealthServices.objects.all()
    serializer_class = HealthServicesSerializer

class OtherInstitutionUnitViewSet(BaseUnitViewSet):
    queryset = OtherInstitutionUnit.objects.all()
    serializer_class = OtherInstitutionUnitSerializer

