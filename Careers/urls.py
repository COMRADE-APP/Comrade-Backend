"""
Careers URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'gigs', views.GigViewSet, basename='gig')
router.register(r'gig-applications', views.GigApplicationViewSet, basename='gig-application')
router.register(r'careers', views.CareerOpportunityViewSet, basename='career')
router.register(r'career-applications', views.CareerApplicationViewSet, basename='career-application')
router.register(r'preferences', views.UserCareerPreferenceViewSet, basename='career-preference')

urlpatterns = [
    path('', include(router.urls)),
]
