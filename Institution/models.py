from django.db import models
from Organisation.models import ORG_TYPES

# Create your models here.
class Institution(models.Model):
    name = models.CharField(max_length=1000)
    inst_type = models.CharField(max_length=500, choices=ORG_TYPES, default='learning_inst')
    origin = models.CharField(max_length=500)
    abbreviation = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=200)
    town = models.CharField(max_length=100)
    city = models.CharField(max_length=500)
    academic_disc = models.CharField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class InstBranch(models.Model):
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=200)
    branch_code = models.CharField(max_length=200, unique=True, primary_key=True)
    origin = models.CharField(max_length=500)
    abbreviation = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    postal_code = models.CharField(max_length=200)
    town = models.CharField(max_length=100)
    city = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now=True)

# University
# ├── Office of the Vice Chancellor
# ├── Faculties / Colleges / Schools
# │   └── Departments
# │       └── Programs / Courses
# ├── Administrative Departments
# │   ├── Registrar
# │   ├── HR
# │   ├── Finance
# │   └── ICT
# ├── Student Affairs
# │   ├── Admissions
# │   ├── Career Office
# │   └── Counseling
# └── Support Services
#     ├── Security
#     ├── Transport
#     └── Health Services
class VCOffice(models.Model):
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING, null=True)
    office_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Faculty(models.Model):
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING, null=True)
    faculty_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class InstDepartment(models.Model):
    faculty = models.OneToOneField(Faculty, on_delete=models.DO_NOTHING)
    dep_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Programme(models.Model):
    faculty = models.OneToOneField(InstDepartment, on_delete=models.DO_NOTHING)
    programme_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

# ├── Administrative Departments
# │   ├── Registrar
# │   ├── HR
# │   ├── Finance
# │   └── ICT
# │   └── Legal

class AdminDep(models.Model):
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING, null=True)
    admin_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class RegistrarOffice(models.Model):
    admin_dep = models.OneToOneField(AdminDep, on_delete=models.DO_NOTHING)
    registrar_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class HR(models.Model):
    admin_dep = models.OneToOneField(AdminDep, on_delete=models.DO_NOTHING)
    hr_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class ICT(models.Model):
    admin_dep = models.OneToOneField(AdminDep, on_delete=models.DO_NOTHING)
    ict_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Finance(models.Model):
    admin_dep = models.OneToOneField(AdminDep, on_delete=models.DO_NOTHING)
    finance_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Marketing(models.Model):
    admin_dep = models.OneToOneField(AdminDep, on_delete=models.DO_NOTHING)
    marketing_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Legal(models.Model):
    admin_dep = models.OneToOneField(AdminDep, on_delete=models.DO_NOTHING)
    legal_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

# ├── Student Affairs
# │   ├── Admissions
# │   ├── Career Office
# │   └── Counseling

class StudentAffairs(models.Model):
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING, null=True)
    stud_affairs_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Admissions(models.Model):
    stud_affairs = models.OneToOneField(StudentAffairs, on_delete=models.DO_NOTHING)
    admissions_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class CareerOffice(models.Model):
    stud_affairs = models.OneToOneField(StudentAffairs, on_delete=models.DO_NOTHING)
    career_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Counselling(models.Model):
    stud_affairs = models.OneToOneField(StudentAffairs, on_delete=models.DO_NOTHING)
    counselling_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

# └── Support Services
#     ├── Security
#     ├── Transport
#     └── Health Services

class SupportServices(models.Model):
    institution = models.OneToOneField(Institution, on_delete=models.DO_NOTHING)
    inst_branch = models.OneToOneField(InstBranch, on_delete=models.DO_NOTHING, null=True)
    support_services_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Security(models.Model):
    stud_affairs = models.OneToOneField(SupportServices, on_delete=models.DO_NOTHING)
    security_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Transport(models.Model):
    stud_affairs = models.OneToOneField(SupportServices, on_delete=models.DO_NOTHING)
    transport_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Library(models.Model):
    stud_affairs = models.OneToOneField(SupportServices, on_delete=models.DO_NOTHING)
    library_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Cafeteria(models.Model):
    stud_affairs = models.OneToOneField(SupportServices, on_delete=models.DO_NOTHING)
    cafeteria_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class Hostel(models.Model):
    stud_affairs = models.OneToOneField(SupportServices, on_delete=models.DO_NOTHING)
    hostel_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)

class HealthServices(models.Model):
    stud_affairs = models.OneToOneField(SupportServices, on_delete=models.DO_NOTHING)
    health_services_code = models.CharField(max_length=500, unique=True, primary_key=True)
    name = models.CharField(max_length=500)
    description = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now=True)
