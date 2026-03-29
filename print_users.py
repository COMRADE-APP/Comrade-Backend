from Authentication.models import CustomUser

users = CustomUser.objects.all()
print([u.username for u in users])
