from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['admission_number', 'year_of_admission', 'institution', 'faculty', 'course', 'phone_number']
    list_filter = ['admission_number', 'year_of_admission']
    
