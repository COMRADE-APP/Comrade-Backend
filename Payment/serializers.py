from rest_framework import serializers
from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription
)
from Payment.models import TRANSACTION_CATEGORY, PAY_OPT
from Authentication.models import Profile, CustomUser

class PaymentProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentProfile
        fields = '__all__'
        read_only_fields = ['comrade_balance', 'profile_token']
    
    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"

class PaymentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentItem
        fields = '__all__'
        read_only_fields = ['total_cost']

class PaymentLogSerializer(serializers.ModelSerializer):
    items = PaymentItemSerializer(source='purchase_item', many=True, read_only=True)
    
    class Meta:
        model = PaymentLog
        fields = '__all__'

class TransactionTokenSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source='recipient_profile.user.user.email', read_only=True)
    sender_email = serializers.EmailField(source='payment_profile.user.user.email', read_only=True)
    
    class Meta:
        model = TransactionToken
        fields = '__all__'
        read_only_fields = ['transaction_code', 'created_at']

class TransactionTrackerSerializer(serializers.ModelSerializer):
    transaction_details = TransactionTokenSerializer(source='transaction_token', read_only=True)
    
    class Meta:
        model = TransactionTracker
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
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
    transaction_details = TransactionTokenSerializer(source='transaction_token', read_only=True)
    
    class Meta:
        model = TransactionHistory
        fields = '__all__'

# Payment Group Serializers
class PaymentGroupMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='payment_profile.user.user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentGroupMember
        fields = '__all__'
        read_only_fields = ['total_contributed', 'joined_at']
    
    def get_user_name(self, obj):
        return f"{obj.payment_profile.user.user.first_name} {obj.payment_profile.user.user.last_name}"

class ContributionSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Contribution
        fields = '__all__'
        read_only_fields = ['contributed_at']
    
    def get_member_name(self, obj):
        return f"{obj.member.payment_profile.user.user.first_name} {obj.member.payment_profile.user.user.last_name}"

class StandingOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandingOrder
        fields = '__all__'

class GroupTargetSerializer(serializers.ModelSerializer):
    item_details = PaymentItemSerializer(source='target_item', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupTarget
        fields = '__all__'
        read_only_fields = ['achieved', 'achieved_at']
    
    def get_progress_percentage(self, obj):
        if obj.payment_group.current_amount and obj.target_amount:
            return round((obj.payment_group.current_amount / obj.target_amount) * 100, 2)
        return 0.0

class GroupInvitationSerializer(serializers.ModelSerializer):
    invited_user_email = serializers.EmailField(source='invited_profile.user.user.email', read_only=True)
    invited_by_name = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='payment_group.name', read_only=True)
    
    class Meta:
        model = GroupInvitation
        fields = '__all__'
        read_only_fields = ['invitation_link', 'created_at']
    
    def get_invited_by_name(self, obj):
        return f"{obj.invited_by.user.user.first_name} {obj.invited_by.user.user.last_name}"

class PaymentGroupsSerializer(serializers.ModelSerializer):
    members = PaymentGroupMemberSerializer(many=True, read_only=True)
    contributions_summary = serializers.SerializerMethodField()
    targets = GroupTargetSerializer(many=True, read_only=True)
    creator_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentGroups
        fields = '__all__'
        read_only_fields = ['current_amount', 'created_at', 'updated_at']
    
    def get_creator_name(self, obj):
        return f"{obj.creator.user.user.first_name} {obj.creator.user.user.last_name}"
    
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
        fields = ['name', 'description', 'max_capacity', 'target_amount', 'expiry_date', 'auto_purchase', 'requires_approval']

class CreateTransactionSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    transaction_type = serializers.ChoiceField(choices=[choice[0] for choice in TRANSACTION_CATEGORY])
    payment_option = serializers.ChoiceField(choices=[choice[0] for choice in PAY_OPT])
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


# Partner Serializers
from Payment.models import Partner, PartnerApplication

class PartnerSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    partner_type_display = serializers.CharField(source='get_partner_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Partner
        fields = '__all__'
        read_only_fields = ['id', 'verified_at', 'total_earnings', 'pending_payout', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"


class PartnerApplicationSerializer(serializers.ModelSerializer):
    applicant_email = serializers.EmailField(source='applicant.user.email', read_only=True)
    applicant_name = serializers.SerializerMethodField()
    partner_type_display = serializers.CharField(source='get_partner_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PartnerApplication
        fields = '__all__'
        read_only_fields = ['id', 'status', 'reviewed_by', 'review_notes', 'reviewed_at', 'partner', 'created_at', 'updated_at']
    
    def get_applicant_name(self, obj):
        return f"{obj.applicant.user.first_name} {obj.applicant.user.last_name}"
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['applicant'] = profile
        return super().create(validated_data)


class PartnerApplicationCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating partner applications"""
    class Meta:
        model = PartnerApplication
        fields = ['partner_type', 'business_name', 'business_registration', 'contact_email', 
                  'contact_phone', 'website', 'address', 'city', 'country', 'description', 
                  'products_services', 'business_license', 'supporting_document']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['applicant'] = profile
        return super().create(validated_data)
