from rest_framework import viewsets
from django.contrib.auth.models import User
from Authentication.models import Student
from .serializers import *

class UserViewSet(viewsets.ModelViewSet):
    queryset =User.objects.all()
    serializer_class = UserSerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer