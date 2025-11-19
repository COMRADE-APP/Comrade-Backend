from  rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from Authentication.serializers import RegisterSerializer, LoginSerializer, CustomUserSerializer, LecturerSerializer, OrgStaffSerializer, StudentAdminSerializer, OrgAdminSerializer, InstAdminSerializer, InstStaffSerializer, ProfileSerializer
from django.contrib.auth import authenticate
from Authentication.models import Student, CustomUser, Lecturer, OrgStaff, StudentAdmin, OrgAdmin, InstAdmin, InstStaff, Profile
from rest_framework.decorators import action

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data = request.data)

        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data,status=status.HTTP_200_OK)

# class StudentViewSet(ModelViewSet):
#     queryset = Student.objects.all()
#     serializer_class = StudentSerializer
#     permission_classes = [IsAuthenticated]
class CustomUserViewSet(ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
class LecturerViewSet(ModelViewSet):
    queryset = Lecturer.objects.all()
    serializer_class = LecturerSerializer
    permission_classes = [IsAuthenticated]
class OrgStaffViewSet(ModelViewSet):
    queryset = OrgStaff.objects.all()
    serializer_class = OrgStaffSerializer
    permission_classes = [IsAuthenticated]
class StudentAdminViewSet(ModelViewSet):
    queryset = StudentAdmin.objects.all()
    serializer_class = StudentAdminSerializer
    permission_classes = [IsAuthenticated]

class OrgAdminViewSet(ModelViewSet):
    queryset = OrgAdmin.objects.all()
    serializer_class = OrgAdminSerializer
    permission_classes = [IsAuthenticated]
class InstAdminViewSet(ModelViewSet):
    queryset = InstAdmin.objects.all()
    serializer_class = InstAdminSerializer
    permission_classes = [IsAuthenticated]
class InstStaffViewSet(ModelViewSet):
    queryset = InstStaff.objects.all()
    serializer_class = InstStaffSerializer
    permission_classes = [IsAuthenticated]
class ProfileViewSet(ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
