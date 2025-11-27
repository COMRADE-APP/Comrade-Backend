from  rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet
from Authentication.serializers import LoginSerializer, CustomUserSerializer, LecturerSerializer, OrgStaffSerializer, StudentAdminSerializer, OrgAdminSerializer, InstAdminSerializer, InstStaffSerializer, ProfileSerializer, BaseUserSerializer
from django.contrib.auth import authenticate
from Authentication.models import Student, CustomUser, Lecturer, OrgStaff, StudentAdmin, OrgAdmin, InstAdmin, InstStaff, Profile
from rest_framework.decorators import action
from UserManagement.serializers import UserSerializer, StudentSerializer
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


class RegisterView(APIView):
    
    def post(self, request):
        serializer = BaseUserSerializer(data = request.data)

        if serializer.is_valid():
            user = serializer.save()


            # generate verification link
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verify_url = f"{request.scheme}://{request.get_host()}/auth/verify-email/?uid={uid}&token={token}/verify"
            verify_path = reverse('verify')  # name='verify' in Authentication/urls.py
            verify_url = request.build_absolute_uri(f"{verify_path}?uid={uid}&token={token}")

            
            # Send email to the recipient
            send_mail('Verify your account', f'Click to verify: {verify_url}', settings.DEFAULT_FROM_EMAIL, [user.email])

            return Response({"message": "User registered successfully. Check email to verify."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VerifyView(APIView):
    def get(self, request):
        uid = request.GET.get('uid')
        token = request.GET.get('token')

        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=uid)
        except Exception:
            return Response({'detail': 'Invalid verification link.'}, status=status.HTTP_400_BAD_REQUEST)
        if default_token_generator.check_token(user, token):
            user.is_active = True

            # map user_type -> boolean flag name
            flag_map = {
                'student': 'is_student',
                'lecturer': 'is_lecturer',
                'organisational_staff': 'is_org_staff',
                'student_admin': 'is_student_admin',
                'organisational_admin': 'is_org_admin',
                'institutional_admin': 'is_inst_admin',
                'institutional_staff': 'is_inst_staff',
                'admin': 'is_admin',
                'moderator': 'is_moderator',
                'author': 'is_author',
                'editor': 'is_editor',
            }
            flag = flag_map.get(user.user_type)
            if flag:
                setattr(user, flag, True)

            user.save()
            return Response({'detail': 'Email verified. You may complete profile.'})
        return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = getattr(serializer, 'user', None)
        if user is None:
            return Response({"detail": "Authentication failed."}, status=status.HTTP_400_BAD_REQUEST)
        
        # generate verification link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        verify_url = f"{request.scheme}://{request.get_host()}/auth/verify-email/?uid={uid}&token={token}/verify"
        verify_path = reverse('verify')  # name='verify' in Authentication/urls.py
        verify_url = request.build_absolute_uri(f"{verify_path}?uid={uid}&token={token}")

        
        # Send email to the recipient
        send_mail('Verify your account', f'Click to verify: {verify_url}', settings.DEFAULT_FROM_EMAIL, [user.email])
        
        data = {
            "user_id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "user_type": user.user_type,
            "message": f"Login successful. Enter Verification code sent on your phone number: {user.phone_number : 6f}****"
        }
        return Response(data, status=status.HTTP_200_OK)
    



# class StudentViewSet(ModelViewSet):
#     queryset = Student.objects.all()
#     serializer_class = StudentSerializer
#     permission_classes = [IsAuthenticated]
class CustomUserViewSet(ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get', 'post'], permission_classes=[AllowAny], serializer_class=BaseUserSerializer)
    def register_student(self, request):
        if request.method == 'GET':
            users = CustomUser.objects.all()
            serializer = CustomUserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = BaseUserSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()    

             # generate verification link
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            verify_url = f"{request.scheme}://{request.get_host()}/auth/verify-email/?uid={uid}&token={token}/verify"
            verify_path = reverse('verify')  # name='verify' in Authentication/urls.py
            verify_url = request.build_absolute_uri(f"{verify_path}?uid={uid}&token={token}")

            
            # Send email to the recipient
            send_mail('Verify your account', f'Click to verify: {verify_url}', settings.DEFAULT_FROM_EMAIL, [user.email])
            print(send_mail('Verify your account', f'Click to verify: {verify_url}', settings.DEFAULT_FROM_EMAIL, [user.email]))

            user.save()
            return Response({"message": "User registered successfully. Check your email."}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



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
