"""
Institution Portal Views
Contains views for document upload functionality
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from Institution.models import Institution, InstitutionVerificationDocument
from Institution.serializers import InstitutionSerializer, InstitutionVerificationDocumentSerializer
from Institution.views import InstitutionViewSet


# Document upload view for compatibility with URLs
class DocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, institution_id):
        """Upload verification document for an institution"""
        try:
            institution = Institution.objects.get(id=institution_id)
        except Institution.DoesNotExist:
            return Response(
                {'error': 'Institution not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # TODO: Implement file upload, virus scanning, and document creation
        serializer = InstitutionVerificationDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(institution=institution, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
