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
import rest_framework
# from rest_framework.documentation import include_docs_urls # new
# from rest_framework.schemas import get_schema_view

# schema_view = get_schema_view(title='comrade API')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('Authentication.urls')),
    path('users/', include('UserManagement.urls')),
    path('rooms/', include('Rooms.urls')),
    path('announcements/', include('Announcements.urls')),
    path('resources/', include('Resources.urls')),
    path('events/', include('Events.urls')),
    path('specializations/', include('Specialization.urls')),
    path('payments/', include('Payment.urls')),
    path('api/', include(rest_framework.urls)),
    # path('docs/', include_docs_urls(title='Blog API')), # new
    # path('schema/', schema_view),
]
