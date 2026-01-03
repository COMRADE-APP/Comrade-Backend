from django.contrib import admin
from Resources.models import Resource, ResourceVisibility, VisibilityLog, Link, MainVisibilityLog, Visibility
# Register your models here.
admin.site.register(Resource)
admin.site.register(ResourceVisibility)
admin.site.register(VisibilityLog)
admin.site.register(Link)
admin.site.register(MainVisibilityLog)
admin.site.register(Visibility)