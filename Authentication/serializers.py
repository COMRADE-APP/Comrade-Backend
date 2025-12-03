from django.contrib.auth import authenticate
import re
from rest_framework import serializers
from Authentication.models import (
    Student, CustomUser, Lecturer, OrgStaff, StudentAdmin, 
    OrgAdmin, InstAdmin, InstStaff, Profile, Author, Editor, 
    Moderator, ComradeAdmin
)


class BaseUserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'other_names', 'email', 'password', 'confirm_password', 'phone_number', 'user_type']
    
    def validate(self, data):
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password too short. Use 8 characters or more."})
        if (not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or 
            not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)):
            raise serializers.ValidationError({"password": "Password must contain at least one uppercase, lowercase, numeric, and special character."})
        if not data.get('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'The password should be confirmed'})
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        if len(data['phone_number']) < 10:
            raise serializers.ValidationError({'phone_number': 'Phone number must be at least 10 digits.'})
        
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        password = validated_data.pop('password', None)
        # Use the model manager so any custom create_user logic runs
        if password is not None:
            user = CustomUser.objects.create_user(password=password, is_active=False, **validated_data)
        else:
            user = CustomUser.objects.create_user(is_active=False, **validated_data)
        return user
    


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'other_names', 'phone_number', 'user_type', 'is_active']
        read_only_fields = ['id', 'is_active'] 


class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username_or_email = data['username_or_email']
        password = data['password']

        user = CustomUser.objects.filter(email=username_or_email).first()
        
        if not user:
            raise serializers.ValidationError({"error": "User not found."})
        
        authenticated = authenticate(username=user.email, password=password)

        if not authenticated:
            raise serializers.ValidationError({"error": "Invalid credentials."})

        self.user = authenticated
        return {
            'user_id': authenticated.id,
            'email': authenticated.email,
        }


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'
        # read_only_fields = ['user'] 

    def validate(self, data):
        if data.get('expecte_year_of_graduation') and data.get('year_of_admission'):
            if data['expecte_year_of_graduation'] < data['year_of_admission']:
                raise serializers.ValidationError({'expecte_year_of_graduation': 'Expected graduation year cannot be less than admission year'})
        return data


class LecturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecturer
        fields = '__all__'
        # read_only_fields = ['user'] 


class OrgStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgStaff
        fields = '__all__'
        # read_only_fields = ['user'] 


class StudentAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAdmin
        fields = '__all__'
        # read_only_fields = ['student']  # FIX: StudentAdmin links to Student, not user


class OrgAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAdmin
        fields = '__all__'
        # read_only_fields = ['staff']  # FIX: OrgAdmin links to OrgStaff, not user


class InstAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstAdmin
        fields = '__all__'
        # read_only_fields = ['staff']  # FIX: InstAdmin links to InstStaff, not user


class InstStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstStaff
        fields = '__all__'
        # read_only_fields = ['user'] 


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'
        # read_only_fields = ['user'] 


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'
        # read_only_fields = ['user']


class EditorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Editor
        fields = '__all__'
        # read_only_fields = ['user']


class ModeratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moderator
        fields = '__all__'
        # read_only_fields = ['user']


class ComradeAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComradeAdmin
        fields = '__all__'
        # read_only_fields = ['user']