from rest_framework import serializers
from Resources.models import Resource




class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Resource