"""
Role-Specific Portal Views
Provides dashboard and management views for different user roles.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class StaffPortalDashboardView(APIView):
    """Staff portal dashboard with overview stats."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Staff portal dashboard",
            "role": "staff"
        })


class StaffUserAssistView(APIView):
    """Staff view to assist users."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "User assistance portal",
            "users": []
        })


class AuthorPortalDashboardView(APIView):
    """Author portal dashboard."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Author portal dashboard",
            "role": "author"
        })


class ModeratorPortalDashboardView(APIView):
    """Moderator portal dashboard."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Moderator portal dashboard",
            "role": "moderator"
        })


class ModeratorContentReviewView(APIView):
    """Moderator content review queue."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Content review queue",
            "items": []
        })


class LecturerPortalDashboardView(APIView):
    """Lecturer portal dashboard."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Lecturer portal dashboard",
            "role": "lecturer"
        })


class InstitutionPortalDashboardView(APIView):
    """Institution portal dashboard."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Institution portal dashboard",
            "role": "institution"
        })


class OrganisationPortalDashboardView(APIView):
    """Organisation portal dashboard."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Organisation portal dashboard",
            "role": "organisation"
        })


class PartnerPortalDashboardView(APIView):
    """Partner portal dashboard."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            "message": "Partner portal dashboard",
            "role": "partner"
        })
