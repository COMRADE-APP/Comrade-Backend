"""
URL configuration for comrade project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import rest_framework
# from rest_framework.documentation import include_docs_urls # new
# from rest_framework.schemas import get_schema_view

# schema_view = get_schema_view(title='comrade API')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication (includes social auth callbacks, TOTP, login, register, etc.)
    path('auth/', include('Authentication.urls')),
    
    # Allauth social login initiation (Google, Facebook, etc.)
    path('accounts/', include('allauth.urls')),
    
    # User Management
    path('users/', include('UserManagement.urls')),
    path('api/articles/', include('Articles.urls')),
    
    # API endpoints
    path('api/rooms/', include('Rooms.urls')),
    path('api/announcements/', include('Announcements.urls')),
    path('api/tasks/', include('Task.urls')),  # Task management
    path('api/resources/', include('Resources.urls')),
    path('api/events/', include('Events.urls')),
    path('api/specializations/', include('Specialization.urls')),
    path('api/payments/', include('Payment.urls')),
    path('api/institutions/', include('Institution.urls')),
    path('api/organizations/', include('Organisation.urls')),
    path('api/devices/', include('DeviceManagement.urls')),
    path('api/activity/', include('ActivityLog.urls')),
    path('api/opinions/', include('Opinions.urls')),  # Opinions & Social
    path('api/notifications/', include('Notifications.urls')),  # Notifications
    path('api/messages/', include('Messages.urls')),  # Direct Messaging
    path('api/', include(rest_framework.urls)),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
