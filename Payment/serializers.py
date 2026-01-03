from rest_framework import serializers
from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, GroupMembers,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription
)
from Authentication.models import CustomUser

class PaymentProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentProfile
        fields = '__all__'
        read_only_fields = ['comrade_balance', 'total_sent', 'total_received', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class TransactionTokenSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    receiver_email = serializers.EmailField(source='receiver.email', read_only=True)
    token_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = TransactionToken
        fields = '__all__'
        read_only_fields = ['token', 'created_at', 'updated_at', 'token_display']


class CreateTransactionSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    payment_method = serializers.ChoiceField(choices=['INTERNAL', 'EXTERNAL'])
    transaction_type = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'


class UserSubscriptionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class GroupMembersSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMembers
        fields = '__all__'
        read_only_fields = ['total_contributed', 'joined_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class ContributionSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    transaction_details = TransactionTokenSerializer(source='transaction', read_only=True)
    
    class Meta:
        model = Contribution
        fields = '__all__'
        read_only_fields = ['contribution_date']
    
    def get_member_name(self, obj):
        return f"{obj.member.first_name} {obj.member.last_name}"


class StandingOrderSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True, allow_null=True)
    
    class Meta:
        model = StandingOrder
        fields = '__all__'


class GroupTargetSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = GroupTarget
        fields = '__all__'
        read_only_fields = ['current_amount', 'is_achieved', 'created_at', 'updated_at']


class GroupInvitationSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    inviter_name = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupInvitation
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_inviter_name(self, obj):
        return f"{obj.inviter.first_name} {obj.inviter.last_name}"


class PaymentGroupsSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    members = GroupMembersSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    contributions_summary = serializers.SerializerMethodField()
    targets = GroupTargetSerializer(many=True, read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentGroups
        fields = '__all__'
        read_only_fields = ['current_amount', 'created_at', 'updated_at']
    
    def get_admin_name(self, obj):
        return f"{obj.admin.first_name} {obj.admin.last_name}"
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_progress_percentage(self, obj):
        if obj.target_amount and obj.target_amount > 0:
            return round((obj.current_amount / obj.target_amount) * 100, 2)
        return 0.0
    
    def get_contributions_summary(self, obj):
        return {
            'total_contributions': obj.contributions.count(),
            'total_amount': obj.current_amount,
            'target_amount': obj.target_amount or 0,
        }


class PaymentGroupsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentGroups
        fields = ['name', 'description', 'group_type', 'target_amount', 'currency', 'deadline']


class PaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLog
        fields = '__all__'


class PaymentAuthorizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAuthorization
        fields = '__all__'


class PaymentVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentVerification
        fields = '__all__'


class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionHistory
        fields = '__all__'


class TransactionTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionTracker
        fields = '__all__'
