from rest_framework import serializers
from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, SavedPaymentMethod
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
    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentGroupMember
        fields = '__all__'
        read_only_fields = ['total_contributed', 'joined_at', 'anonymous_alias']
    
    def get_user_email(self, obj):
        if obj.is_anonymous:
            return None
        return obj.payment_profile.user.user.email
    
    def get_user_name(self, obj):
        if obj.is_anonymous:
            return obj.anonymous_alias or 'Anonymous Member'
        return f"{obj.payment_profile.user.user.first_name} {obj.payment_profile.user.user.last_name}"

class ContributionSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Contribution
        fields = '__all__'
        read_only_fields = ['contributed_at']
    
    def get_member_name(self, obj):
        if obj.member.is_anonymous:
            return obj.member.anonymous_alias or 'Anonymous Member'
        return f"{obj.member.payment_profile.user.user.first_name} {obj.member.payment_profile.user.user.last_name}"

class StandingOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandingOrder
        fields = '__all__'

class GroupTargetSerializer(serializers.ModelSerializer):
    item_details = PaymentItemSerializer(source='target_item', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    owner_email = serializers.EmailField(source='owner.user.user.email', read_only=True)
    owner_name = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='payment_group.name', read_only=True)
    type = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupTarget
        fields = '__all__'
        read_only_fields = ['achieved', 'achieved_at', 'current_amount']
    
    def get_progress_percentage(self, obj):
        if obj.target_amount and obj.target_amount > 0:
            return round((float(obj.current_amount) / float(obj.target_amount)) * 100, 2)
        return 0.0
    
    def get_owner_name(self, obj):
        if obj.owner:
            return f"{obj.owner.user.user.first_name} {obj.owner.user.user.last_name}"
        return None
    
    def get_type(self, obj):
        """Return 'individual' or 'group' based on piggy bank type"""
        return 'individual' if obj.owner else 'group'

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
            return round((float(obj.current_amount) / float(obj.target_amount)) * 100, 2)
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
        fields = ['name', 'description', 'max_capacity', 'target_amount', 'expiry_date', 
                  'deadline', 'auto_purchase', 'requires_approval', 'is_public',
                  'contribution_type', 'contribution_amount', 'frequency', 'group_type',
                  'allow_anonymous']

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


# Agent, Supplier, Shop Serializers
from Payment.models import AgentApplication, SupplierApplication, ShopRegistration

class AgentApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.user.get_full_name', read_only=True)
    agent_type_display = serializers.CharField(source='get_agent_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AgentApplication
        fields = '__all__'
        read_only_fields = ['status', 'reviewed_by', 'review_notes', 'result_at', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['applicant'] = profile
        return super().create(validated_data)


class SupplierApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='applicant.user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SupplierApplication
        fields = '__all__'
        read_only_fields = ['status', 'reviewed_by', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['applicant'] = profile
        return super().create(validated_data)


class ShopRegistrationSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.user.get_full_name', read_only=True)

    class Meta:
        model = ShopRegistration
        fields = '__all__'
        read_only_fields = ['owner', 'created_at', 'updated_at', 'is_active']
        
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['owner'] = profile
        return super().create(validated_data)


# ============================================================================
# MARKETPLACE SERIALIZERS
# ============================================================================

from Payment.models import (
    Establishment, EstablishmentBranch, MenuItem, HotelRoom,
    Booking, ServiceOffering, ServiceTimeSlot, Order, OrderItem, Review
)


class EstablishmentBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstablishmentBranch
        fields = '__all__'
        read_only_fields = ['created_at']


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = '__all__'
        read_only_fields = ['created_at']


class HotelRoomSerializer(serializers.ModelSerializer):
    room_type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    
    class Meta:
        model = HotelRoom
        fields = '__all__'
        read_only_fields = ['created_at']


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ['user', 'created_at']
    
    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['user'] = profile
        return super().create(validated_data)


class EstablishmentSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    establishment_type_display = serializers.CharField(source='get_establishment_type_display', read_only=True)
    branches = EstablishmentBranchSerializer(many=True, read_only=True)
    branch_count = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Establishment
        fields = '__all__'
        read_only_fields = ['owner', 'slug', 'rating', 'review_count', 'is_verified', 'created_at', 'updated_at']
    
    def get_owner_name(self, obj):
        return f"{obj.owner.user.first_name} {obj.owner.user.last_name}"
    
    def get_branch_count(self, obj):
        return obj.branches.filter(is_active=True).count()
    
    def get_recent_reviews(self, obj):
        reviews = obj.reviews.all()[:3]
        return ReviewSerializer(reviews, many=True).data
    
    def create(self, validated_data):
        from django.utils.text import slugify
        import uuid
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['owner'] = profile
        # Auto-generate slug
        name = validated_data.get('name', '')
        slug = slugify(name)
        if Establishment.objects.filter(slug=slug).exists():
            slug = f"{slug}-{str(uuid.uuid4())[:8]}"
        validated_data['slug'] = slug
        return super().create(validated_data)


class EstablishmentListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""
    establishment_type_display = serializers.CharField(source='get_establishment_type_display', read_only=True)
    branch_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Establishment
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'banner',
            'establishment_type', 'establishment_type_display', 'categories',
            'city', 'country', 'rating', 'review_count', 'branch_count',
            'delivery_available', 'pickup_available', 'dine_in_available',
            'is_active', 'is_verified'
        ]
    
    def get_branch_count(self, obj):
        return obj.branches.filter(is_active=True).count()


class BookingSerializer(serializers.ModelSerializer):
    establishment_name = serializers.CharField(source='establishment.name', read_only=True)
    room_name = serializers.CharField(source='hotel_room.name', read_only=True)
    booking_type_display = serializers.CharField(source='get_booking_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['user', 'status', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['user'] = profile
        return super().create(validated_data)


class ServiceOfferingSerializer(serializers.ModelSerializer):
    provider_name = serializers.SerializerMethodField()
    service_mode_display = serializers.CharField(source='get_service_mode_display', read_only=True)
    establishment_name = serializers.CharField(source='establishment.name', read_only=True)
    available_slots_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceOffering
        fields = '__all__'
        read_only_fields = ['provider', 'created_at']
    
    def get_provider_name(self, obj):
        return f"{obj.provider.user.first_name} {obj.provider.user.last_name}"
    
    def get_available_slots_count(self, obj):
        from datetime import date
        return obj.time_slots.filter(is_booked=False, date__gte=date.today()).count()
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['provider'] = profile
        return super().create(validated_data)


class ServiceTimeSlotSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    class Meta:
        model = ServiceTimeSlot
        fields = '__all__'
        read_only_fields = ['is_booked', 'booked_by', 'created_at']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    buyer_name = serializers.SerializerMethodField()
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    delivery_mode_display = serializers.CharField(source='get_delivery_mode_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    establishment_name = serializers.CharField(source='establishment.name', read_only=True)
    
    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['id', 'buyer', 'status', 'total_amount', 'created_at', 'updated_at']
    
    def get_buyer_name(self, obj):
        return f"{obj.buyer.user.first_name} {obj.buyer.user.last_name}"


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating orders with items."""
    establishment_id = serializers.IntegerField(required=False)
    order_type = serializers.ChoiceField(choices=['product', 'food', 'hotel_booking', 'service_appointment'])
    delivery_mode = serializers.ChoiceField(choices=['pickup', 'delivery', 'appointment'])
    payment_type = serializers.ChoiceField(choices=['individual', 'group'], default='individual')
    payment_group_id = serializers.UUIDField(required=False)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    # For service appointments
    service_time_slot_id = serializers.IntegerField(required=False)
    
    # For bookings
    booking_id = serializers.IntegerField(required=False)
    
    # Items
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text='List of {product_id or menu_item_id, quantity}'
    )


# ============================================================================
# SAVED PAYMENT METHOD SERIALIZERS
# ============================================================================

class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedPaymentMethod
        fields = '__all__'
        read_only_fields = ['id', 'payment_profile', 'card_brand', 'provider_token', 
                           'provider', 'is_verified', 'created_at', 'updated_at']
    
    def get_display_name(self, obj):
        return str(obj)


class SavedPaymentMethodCreateSerializer(serializers.Serializer):
    """Serializer for creating a saved payment method with validation."""
    method_type = serializers.ChoiceField(choices=['card', 'mpesa', 'paypal', 'bank_transfer', 'equity'])
    
    # Card fields
    card_number = serializers.CharField(required=False, max_length=19, help_text='Full card number (will be tokenized)')
    expiry_month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    expiry_year = serializers.IntegerField(required=False, min_value=2024)
    cvc = serializers.CharField(required=False, max_length=4)
    billing_zip = serializers.CharField(required=False, max_length=20)
    
    # M-Pesa fields
    phone_number = serializers.CharField(required=False, max_length=20)
    
    # PayPal fields
    paypal_email = serializers.EmailField(required=False)
    
    # Bank fields
    bank_name = serializers.CharField(required=False, max_length=100)
    account_number = serializers.CharField(required=False, max_length=20)
    
    # Common
    nickname = serializers.CharField(required=False, max_length=100, allow_blank=True)
    is_default = serializers.BooleanField(required=False, default=False)
    save_details = serializers.BooleanField(required=False, default=True)
    
    def validate_card_number(self, value):
        """Validate card number using Luhn algorithm."""
        if not value:
            return value
        digits = value.replace(' ', '').replace('-', '')
        if not digits.isdigit():
            raise serializers.ValidationError("Card number must contain only digits.")
        if len(digits) < 13 or len(digits) > 19:
            raise serializers.ValidationError("Card number must be between 13 and 19 digits.")
        # Luhn check
        total = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        if total % 10 != 0:
            raise serializers.ValidationError("Invalid card number.")
        return digits
    
    def validate_phone_number(self, value):
        """Validate phone number for M-Pesa."""
        if not value:
            return value
        digits = value.replace(' ', '').replace('+', '').replace('-', '')
        if not digits.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(digits) < 9 or len(digits) > 15:
            raise serializers.ValidationError("Invalid phone number length.")
        return value
    
    def validate(self, data):
        method_type = data.get('method_type')
        if method_type == 'card':
            required = ['card_number', 'expiry_month', 'expiry_year', 'cvc']
            missing = [f for f in required if not data.get(f)]
            if missing:
                raise serializers.ValidationError({f: 'This field is required for card payments.' for f in missing})
        elif method_type == 'mpesa':
            if not data.get('phone_number'):
                raise serializers.ValidationError({'phone_number': 'Phone number is required for M-Pesa.'})
        elif method_type == 'paypal':
            if not data.get('paypal_email'):
                raise serializers.ValidationError({'paypal_email': 'PayPal email is required.'})
        elif method_type in ('bank_transfer', 'equity'):
            if not data.get('account_number'):
                raise serializers.ValidationError({'account_number': 'Account number is required for bank transfers.'})
        return data

