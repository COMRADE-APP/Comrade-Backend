from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import re
from rest_framework import serializers
from Authentication.models import Student, CustomUser, Lecturer, OrgStaff, StudentAdmin, OrgAdmin, InstAdmin, InstStaff, Profile

class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    confirm_password = serializers.CharField(write_only = True)
    admission_number = serializers.CharField()
    year_of_admission = serializers.CharField()
    faculty  = serializers.CharField()
    course = serializers.CharField()
    institution = serializers.CharField()
    phone_number = serializers.CharField()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password', 'email','confirm_password', 'admission_number', 'year_of_admission', 'faculty', 'course','institution', 'phone_number']

        extra_kwargs = {'password': {'write_only': True}} # ensure the password is sent in request but won't be returned in api responses.
    
    def validate(self, data):
        if Student.objects.filter(admission_number = data['admission_number']).exists():
            raise serializers.ValidationError({"admission_number": "Admission number already exists."})
        

        # validate the password.
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password too short. Use 8 characters or more."})
        if (
            not re.search(r'[A-Z]', password) or
            not re.search(r'[a-z]', password) or
            not re.search(r'[0-9]', password) or
            not re.search(r'[!@#$%^&*(),.?":{}|<>]', password)
        ):
            raise serializers.ValidationError({
                "password": "Password must contain at least one uppercase, lowercase, numeric, and special character."
            })

        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        

        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        try:
            user = User.objects.create_user(
            username = validated_data['username'],
            first_name = validated_data['first_name'],
            last_name = validated_data['last_name'],
            email = validated_data['email'],
            password = validated_data['password']
            )
        except Exception as e:
            raise serializers.ValidationError({"error": str(e)})
        
        try:
            Student.objects.create(
            user = user,
            admission_number = validated_data['admission_number'],
            year_of_admission = validated_data['year_of_admission'],
            faculty = validated_data['faculty'],
            course = validated_data['course'],
            institution = validated_data['institution'],
            phone_number = validated_data['phone_number']
            )
        except Exception as e:
            user.delete()
            raise serializers.ValidationError({"Error": "Student not created."})

        return user

class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only = True)

    def validate(self, data):
        username_or_email = data['username_or_email']
        password = data['password']

        # check if what was provided was username or password.
        user = User.objects.filter(username=username_or_email).first()

        # get username to the user if email is provide.
        user = User.objects.filter(email = username_or_email).first()
        
        if user:
            # email was provided. get username
            username = user.username
        else:
            username = username_or_email 
        
        user = authenticate(username=username, password = password)

        if not user:
            raise serializers.ValidationError({"Error": "Invalid credentials."})

        return{"username": user.username, "message": "Login successful."}
    
class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'  
        read_only_fields = ['admission_number']
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'  
        read_only_fields = ['email']
class LecturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecturer
        fields = '__all__'  
        read_only_fields = ['user']
class OrgStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgStaff
        fields = '__all__'  
        read_only_fields = ['user']
class StudentAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAdmin
        fields = '__all__'  
        read_only_fields = ['user']
class OrgAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAdmin
        fields = '__all__'  
        read_only_fields = ['user']
class InstAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstAdmin
        fields = '__all__'  
        read_only_fields = ['user']
class InstStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstStaff
        fields = '__all__'  
        read_only_fields = ['user']

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = '__all__'  
        read_only_fields = ['user']
