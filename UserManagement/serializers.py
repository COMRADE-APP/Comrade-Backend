from rest_framework import serializers
from Authentication.models import Student, CustomUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta: 
        model  = Student
        fields =  ['id', 'user', 'admission_number', 'year_of_admission', 'faculty', 'course', 'institution', 'phone_number']
    
    def update(self, instance, validated_data):
       
        for field, data_item in validated_data.items():
           setattr(instance, field, data_item)
        instance.save()
        return instance