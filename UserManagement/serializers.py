from rest_framework import serializers
from Authentication.models import Student, CustomUser

class UserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'user_type', 'other_names', 'password', 'confirm_password',]

class StudentSerializer(serializers.ModelSerializer):
    # user = UserSerializer()

    class Meta: 
        model  = Student
        fields =  ['user', 'admission_number', 'year_of_admission', 'faculty', 'course', 'institution', 'phone_number']
    
    def update(self, instance, validated_data):
       
        for field, data_item in validated_data.items():
           setattr(instance, field, data_item)
        instance.save()
        return instance