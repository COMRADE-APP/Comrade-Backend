from rest_framework.serializers import ModelSerializer
from Specialization.models import Specialization, Stack, SavedSpecialization, SavedStack, SpecializationAdmin, SpecializationMembership, SpecializationModerator, SpecializationRoom, StackAdmin, StackMembership, StackModerator, CompletedSpecialization, CompletedStack, PositionTracker, Certificate, IssuedCertificate


class SpecializationSerializer(ModelSerializer):
    class Meta:
        model = Specialization
        fields = '__all__'

class StackSerializer(ModelSerializer):
    class Meta:
        model = Stack
        fields = '__all__'

class SavedSpecializationSerializer(ModelSerializer):
    class Meta:
        model = SavedSpecialization
        fields = '__all__'

class SavedStackSerializer(ModelSerializer):
    class Meta:
        model = SavedStack
        fields = '__all__'

class SpecializationAdminSerializer(ModelSerializer):
    class Meta:
        model = SpecializationAdmin
        fields = '__all__'

class StackAdminSerializer(ModelSerializer):
    class Meta:
        model = StackAdmin
        fields = '__all__'

class SpecializationMembershipSerializer(ModelSerializer):
    class Meta:
        model = SpecializationMembership
        fields = '__all__'

class StackMembershipSerializer(ModelSerializer):
    class Meta:
        model = StackMembership
        fields = '__all__'

class SpecializationModeratorSerializer(ModelSerializer):
    class Meta:
        model = SpecializationModerator
        fields = '__all__'

class StackModeratorSerializer(ModelSerializer):
    class Meta:
        model = StackModerator
        fields = '__all__'

class CompletedSpecializationSerializer(ModelSerializer):
    class Meta:
        model = CompletedSpecialization
        fields = '__all__'

class CompletedStackSerializer(ModelSerializer):
    class Meta:
        model = CompletedStack
        fields = '__all__'

class SpecializationRoomSerializer(ModelSerializer):
    class Meta:
        model = SpecializationRoom
        fields = '__all__'

class PositionTrackerSerializer(ModelSerializer):
    class Meta:
        model = PositionTracker
        fields = '__all__'

class CertificateSerializer(ModelSerializer):
    class Meta:
        model = Certificate
        fields = '__all__'

class IssuedCertificateSerializer(ModelSerializer):
    class Meta:
        model = IssuedCertificate
        fields = '__all__'

