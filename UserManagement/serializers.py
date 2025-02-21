from rest_framework import serializers
from django.contrib.auth.models import User
from Authentication.models import Student

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta: 
        model  = Student
        fields = '__all__'