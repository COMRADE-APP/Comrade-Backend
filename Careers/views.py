"""
Careers Views with Recommendation Algorithm
"""
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from .models import Gig, GigApplication, CareerOpportunity, CareerApplication, UserCareerPreference
from .serializers import (
    GigSerializer, GigCreateSerializer, GigApplicationSerializer,
    CareerOpportunitySerializer, CareerOpportunityCreateSerializer,
    CareerApplicationSerializer, UserCareerPreferenceSerializer
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, 'creator'):
            return obj.creator == request.user
        if hasattr(obj, 'posted_by'):
            return obj.posted_by == request.user
        return False


class GigViewSet(viewsets.ModelViewSet):
    queryset = Gig.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'industry']
    ordering_fields = ['created_at', 'pay_amount', 'deadline']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return GigCreateSerializer
        return GigSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        # Filter by industry
        industry = self.request.query_params.get('industry')
        if industry:
            qs = qs.filter(industry=industry)
        
        # Filter by remote
        is_remote = self.request.query_params.get('is_remote')
        if is_remote:
            qs = qs.filter(is_remote=is_remote.lower() == 'true')
        
        return qs

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_gigs(self, request):
        """Get gigs created by current user"""
        gigs = self.queryset.filter(creator=request.user)
        serializer = GigSerializer(gigs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def recommended(self, request):
        """Get recommended gigs based on user preferences"""
        recommendations = get_recommended_gigs(request.user)
        serializer = GigSerializer(recommendations, many=True)
        return Response(serializer.data)


class GigApplicationViewSet(viewsets.ModelViewSet):
    queryset = GigApplication.objects.all()
    serializer_class = GigApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        gig_id = self.request.query_params.get('gig_id')
        if gig_id:
            qs = qs.filter(gig_id=gig_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)


class CareerOpportunityViewSet(viewsets.ModelViewSet):
    queryset = CareerOpportunity.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'company_name', 'description', 'industry']
    ordering_fields = ['created_at', 'salary_min', 'application_deadline']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CareerOpportunityCreateSerializer
        return CareerOpportunitySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        
        # Filter by job type
        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)
        
        # Filter by experience level
        experience = self.request.query_params.get('experience_level')
        if experience:
            qs = qs.filter(experience_level=experience)
        
        # Filter by industry
        industry = self.request.query_params.get('industry')
        if industry:
            qs = qs.filter(industry=industry)
        
        # Filter by remote
        is_remote = self.request.query_params.get('is_remote')
        if is_remote:
            qs = qs.filter(is_remote=is_remote.lower() == 'true')
            
        # Filter by Organization
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            qs = qs.filter(organization_id=org_id)
            
        # Filter by Institution
        inst_id = self.request.query_params.get('institution_id')
        if inst_id:
            qs = qs.filter(institution_id=inst_id)
        
        return qs

    def perform_create(self, serializer):
        serializer.save(posted_by=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_postings(self, request):
        """Get career opportunities posted by current user"""
        careers = CareerOpportunity.objects.filter(posted_by=request.user)
        serializer = CareerOpportunitySerializer(careers, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def recommended(self, request):
        """Get recommended careers based on user preferences"""
        recommendations = get_recommended_careers(request.user)
        serializer = CareerOpportunitySerializer(recommendations, many=True)
        return Response(serializer.data)


class CareerApplicationViewSet(viewsets.ModelViewSet):
    queryset = CareerApplication.objects.all()
    serializer_class = CareerApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        career_id = self.request.query_params.get('career_id')
        if career_id:
            qs = qs.filter(career_id=career_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)


class UserCareerPreferenceViewSet(viewsets.ViewSet):
    """Manage user career preferences"""
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """Get current user's preferences"""
        try:
            pref = UserCareerPreference.objects.get(user=request.user)
            serializer = UserCareerPreferenceSerializer(pref)
            return Response(serializer.data)
        except UserCareerPreference.DoesNotExist:
            return Response({'detail': 'No preferences set'}, status=404)

    def create(self, request):
        """Create or update user preferences"""
        pref, created = UserCareerPreference.objects.get_or_create(user=request.user)
        serializer = UserCareerPreferenceSerializer(pref, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# RECOMMENDATION ALGORITHM
# ==============================================================================

def get_recommended_gigs(user, limit=20):
    """
    Recommendation algorithm for gigs
    Combines industry match + recent activity
    """
    try:
        prefs = UserCareerPreference.objects.get(user=user)
    except UserCareerPreference.DoesNotExist:
        # No preferences, return popular open gigs
        return Gig.objects.filter(status='open').order_by('-created_at')[:limit]
    
    # Base queryset: open gigs not created by user
    qs = Gig.objects.filter(status='open').exclude(creator=user)
    
    # Score by industry match (higher weight)
    industry_match = Q()
    if prefs.industries:
        for ind in prefs.industries:
            industry_match |= Q(industry=ind)
    
    # Score by pay range
    pay_match = Q()
    if prefs.preferred_pay_min:
        pay_match &= Q(pay_amount__gte=prefs.preferred_pay_min)
    if prefs.preferred_pay_max:
        pay_match &= Q(pay_amount__lte=prefs.preferred_pay_max)
    
    # Score by remote preference
    if prefs.is_remote_only:
        qs = qs.filter(is_remote=True)
    
    # Combine: industry matches first, then by recency
    industry_gigs = qs.filter(industry_match).order_by('-created_at')
    other_gigs = qs.exclude(industry_match).order_by('-created_at')
    
    # Combine results
    combined = list(industry_gigs[:limit]) + list(other_gigs[:max(0, limit - industry_gigs.count())])
    return combined[:limit]


def get_recommended_careers(user, limit=20):
    """
    Recommendation algorithm for career opportunities
    Combines industry match + job type + experience + recent activity
    """
    try:
        prefs = UserCareerPreference.objects.get(user=user)
    except UserCareerPreference.DoesNotExist:
        # No preferences, return recent active careers
        return CareerOpportunity.objects.filter(is_active=True).order_by('-created_at')[:limit]
    
    # Base queryset: active careers not posted by user
    qs = CareerOpportunity.objects.filter(is_active=True).exclude(posted_by=user)
    
    # Score by industry match
    if prefs.industries:
        industry_q = Q()
        for ind in prefs.industries:
            industry_q |= Q(industry=ind)
        qs = qs.filter(industry_q)
    
    # Score by job type preference
    if prefs.preferred_job_types:
        job_type_q = Q()
        for jt in prefs.preferred_job_types:
            job_type_q |= Q(job_type=jt)
        qs = qs.filter(job_type_q)
    
    # Score by salary range
    if prefs.preferred_pay_min:
        qs = qs.filter(Q(salary_max__gte=prefs.preferred_pay_min) | Q(salary_max__isnull=True))
    
    # Score by remote preference
    if prefs.is_remote_only:
        qs = qs.filter(is_remote=True)
    
    return qs.order_by('-created_at')[:limit]
