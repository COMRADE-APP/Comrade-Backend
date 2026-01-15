# Task/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskViewSet, 
    QuestionViewSet, 
    TaskResponseViewSet,
    MyTasksViewSet,
)

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'responses', TaskResponseViewSet, basename='task-response')
router.register(r'my_tasks', MyTasksViewSet, basename='my-tasks')

urlpatterns = [
    path('', include(router.urls)),
]
