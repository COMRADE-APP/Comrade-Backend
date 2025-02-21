from django.urls import path
from .views import *

user_list = UserViewSet.as_view({"get": "list", "post": "create"})
user_detail = UserViewSet.as_view({"get": "retrieve", "put":"update", "post":"update", "delete": "destroy"})

student_list = StudentViewSet.as_view({"get": "list", "post": "create"})
student_detail = StudentViewSet.as_view({"get": "retrieve", "put": "update","post": "update", "delete": "destroy"})



urlpatterns = [
    path('', user_list, name='user-list'),
    path("<int:pk>/", user_detail, name='user-detail'),
    path('students/', student_list, name='student-list'),
    path('students/<int:pk>/', student_detail, name='student_detail'),
]