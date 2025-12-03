from django.contrib import admin
from Resources.models import Resource, ResourceVisibility, VisibilityLog
# Register your models here.
admin.site.register(Resource)
admin.site.register(ResourceVisibility)
admin.site.register(VisibilityLog)