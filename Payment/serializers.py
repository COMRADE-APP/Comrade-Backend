from rest_framework.serializers import ModelSerializer
from Payment.models import PaymentProfile, PaymentItem, PaymentLog, PaymentSlot, PaymentGroups

class PaymentProfileSerializer(ModelSerializer):
    class Meta:
        model = PaymentProfile
        fields = '__all__'

class PaymentItemSerializer(ModelSerializer):
    class Meta:
        model = PaymentItem
        fields = '__all__'

class PaymentLogSerializer(ModelSerializer):
    class Meta:
        model = PaymentLog
        fields = '__all__'

class PaymentSlotSerializer(ModelSerializer):
    class Meta:
        model = PaymentSlot
        fields = '__all__'

class PaymentGroupsSerializer(ModelSerializer):
    class Meta:
        model = PaymentGroups
        fields = '__all__'



