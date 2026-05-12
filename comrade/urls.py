"""
URL configuration for comrade project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import rest_framework
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

API_V1 = 'api/v1/'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('Authentication.urls')),
    path('accounts/', include('allauth.urls')),
    path('users/', include('UserManagement.urls')),

    # API v1 endpoints
    path(f'{API_V1}articles/', include('Articles.urls')),
    path(f'{API_V1}rooms/', include('Rooms.urls')),
    path(f'{API_V1}announcements/', include('Announcements.urls')),
    path(f'{API_V1}tasks/', include('Task.urls')),
    path(f'{API_V1}resources/', include('Resources.urls')),
    path(f'{API_V1}events/', include('Events.urls')),
    path(f'{API_V1}specializations/', include('Specialization.urls')),
    path(f'{API_V1}payments/', include('Payment.urls')),
    path(f'{API_V1}institutions/', include('Institution.urls')),
    path(f'{API_V1}organizations/', include('Organisation.urls')),
    path(f'{API_V1}devices/', include('DeviceManagement.urls')),
    path(f'{API_V1}activity/', include('ActivityLog.urls')),
    path(f'{API_V1}opinions/', include('Opinions.urls')),
    path(f'{API_V1}notifications/', include('Notifications.urls')),
    path(f'{API_V1}messages/', include('Messages.urls')),
    path(f'{API_V1}qomai/', include('QomAI.urls')),
    path(f'{API_V1}funding/', include('Funding.urls')),
    path(f'{API_V1}careers/', include('Careers.urls')),
    path(f'{API_V1}research/', include('Research.urls')),
    path(f'{API_V1}verification/', include('Verification.urls')),
    path(f'{API_V1}auth/', include(rest_framework.urls)),

    # API documentation (Swagger / ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Legacy API routes (backward compatibility — remove after frontend migration)
    path('api/articles/', include('Articles.urls')),
    path('api/rooms/', include('Rooms.urls')),
    path('api/announcements/', include('Announcements.urls')),
    path('api/tasks/', include('Task.urls')),
    path('api/resources/', include('Resources.urls')),
    path('api/events/', include('Events.urls')),
    path('api/specializations/', include('Specialization.urls')),
    path('api/payments/', include('Payment.urls')),
    path('api/institutions/', include('Institution.urls')),
    path('api/organizations/', include('Organisation.urls')),
    path('api/devices/', include('DeviceManagement.urls')),
    path('api/activity/', include('ActivityLog.urls')),
    path('api/opinions/', include('Opinions.urls')),
    path('api/notifications/', include('Notifications.urls')),
    path('api/messages/', include('Messages.urls')),
    path('api/qomai/', include('QomAI.urls')),
    path('api/funding/', include('Funding.urls')),
    path('api/careers/', include('Careers.urls')),
    path('api/research/', include('Research.urls')),
    path('api/verification/', include('Verification.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
