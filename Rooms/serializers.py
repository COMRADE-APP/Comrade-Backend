from rest_framework import serializers
from Rooms.models import Room, DefaultRoom, DirectMessage, DirectMessageRoom, ForwadingLog
from Authentication.models import CustomUser


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_on', 'invitation_code']

    
class DefaultRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultRoom
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'created_on', 'invitation_code']

class DirectMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectMessage
        fields = '__all__'
        read_only_fields = ['id', 'sender', 'time_stamp', 'is_read']

class DirectMessageRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectMessageRoom
        fields = '__all__'
        read_only_fields = ['id', 'created_on']


class ForwadingLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ForwadingLog
        fields = '__all__'
        read_only_fields = ['id', 'user', 'forwarded_on']