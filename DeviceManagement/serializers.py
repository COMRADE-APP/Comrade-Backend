from rest_framework import serializers
from DeviceManagement.models import UserDevice, DeviceVerification


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = '__all__'
        read_only_fields = ['user', 'device_fingerprint', 'first_seen', 'last_seen']


class DeviceVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceVerification
        fields = '__all__'
