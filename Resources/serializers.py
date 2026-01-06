from rest_framework import serializers
from Resources.models import Resource, ResourceVisibility, VisibilityLog, Link, MainVisibilityLog, Visibility




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

class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Link

class VisibilitySerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Visibility


class MainVisibilityLogSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = MainVisibilityLog

