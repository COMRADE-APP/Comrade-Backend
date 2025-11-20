from rest_framework import serializers
from Resources.models import Resource, ResourceVisibility, VisibilityLog




class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Resource

class ResourceVisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = ResourceVisibility


class VisibilityLogSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = VisibilityLog
