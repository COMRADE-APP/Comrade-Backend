from rest_framework import serializers
from .models import Room
from django.contrib.auth.models import User

class RoomSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    members = serializers.SlugRelatedField(many=True, slug_field = 'username', queryset=User.objects.all(), required=False) # display the members in the room using username instead of the id.

    class Meta:
        model = Room
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_on', 'invitation_code']

    def create(self, validated_data):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError({"error": "Request context is required."})

        validated_data['created_by'] = request.user  # Assign current user
        room= Room.objects.create(**validated_data)
        return room

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.institution = validated_data.get('institution', instance.institution)
        instance.save()
        return instance  
    def delete(self, instance):
        instance.delete()
        return instance
