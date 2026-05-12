from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

CustomUser = get_user_model()


class CustomUserModelTest(TestCase):
    def test_create_user_with_email(self):
        user = CustomUser.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.user_type, 'normal_user')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        admin = CustomUser.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_email_normalization(self):
        email = 'TEST@Example.COM'
        user = CustomUser.objects.create_user(email=email, password='pass123')
        self.assertEqual(user.email, 'test@example.com')

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email=None, password='pass123')

    def test_user_str_representation(self):
        user = CustomUser.objects.create_user(
            email='user@example.com',
            password='pass123',
            first_name='John'
        )
        self.assertEqual(str(user), 'user@example.com')

    def test_user_types(self):
        valid_types = [
            'admin', 'staff', 'lecturer', 'student', 'normal_user',
            'moderator', 'student_admin', 'institutional_admin',
            'organisational_admin', 'author', 'editor', 'creator',
            'institutional_staff', 'organisational_staff'
        ]
        for user_type in valid_types:
            user = CustomUser.objects.create_user(
                email=f'{user_type}@example.com',
                password='pass123',
                user_type=user_type
            )
            self.assertEqual(user.user_type, user_type)


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='profile@example.com',
            password='pass123',
            first_name='Profile',
            last_name='Test'
        )

    def test_profile_auto_created_on_user(self):
        from Authentication.models import UserProfile
        profile = UserProfile.objects.filter(user=self.user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user, self.user)


class AuthenticationAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email='api@example.com',
            password='apipass123',
            first_name='API',
            last_name='Test'
        )

    def test_register_user(self):
        response = self.client.post('/auth/register/', {
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
        })
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        self.assertTrue(CustomUser.objects.filter(email='newuser@example.com').exists())

    def test_register_with_missing_fields(self):
        response = self.client.post('/auth/register/', {
            'email': 'incomplete@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        self.client.post('/auth/register/', {
            'email': 'dup@example.com',
            'password': 'pass123',
            'password2': 'pass123',
            'first_name': 'Dup',
        })
        response = self.client.post('/auth/register/', {
            'email': 'dup@example.com',
            'password': 'pass123',
            'password2': 'pass123',
            'first_name': 'Dup2',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_requires_email_and_password(self):
        response = self.client.post('/auth/login/', {
            'email': '',
            'password': '',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access_to_protected_endpoint(self):
        response = self.client.get('/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_heartbeat_requires_auth(self):
        response = self.client.post('/auth/heartbeat/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SerializerTest(APITestCase):
    def test_user_serializer_valid_data(self):
        from Authentication.serializers import BaseUserSerializer
        data = {
            'email': 'serializer@example.com',
            'password': 'serializerpass123',
            'password2': 'serializerpass123',
            'first_name': 'Serializer',
        }
        serializer = BaseUserSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_user_serializer_password_mismatch(self):
        from Authentication.serializers import BaseUserSerializer
        data = {
            'email': 'mismatch@example.com',
            'password': 'pass123',
            'password2': 'differentpass',
            'first_name': 'Mismatch',
        }
        serializer = BaseUserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_user_serializer_weak_password(self):
        from Authentication.serializers import BaseUserSerializer
        data = {
            'email': 'weak@example.com',
            'password': '123',
            'password2': '123',
            'first_name': 'Weak',
        }
        serializer = BaseUserSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_user_serializer_invalid_email(self):
        from Authentication.serializers import BaseUserSerializer
        data = {
            'email': 'not-an-email',
            'password': 'pass123',
            'password2': 'pass123',
            'first_name': 'Invalid',
        }
        serializer = BaseUserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
