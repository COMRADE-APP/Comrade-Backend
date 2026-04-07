from rest_framework import serializers
from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, SavedPaymentMethod, GroupCheckoutRequest,
    GroupJoinRequest, GroupVote, GroupPhase, GroupPost, GroupPostReply,
    BillProvider, BillPayment,
    LoanProduct, CreditScore, LoanApplication, LoanRepayment,
    EscrowTransaction, EscrowDispute,
    InsuranceProduct, InsurancePolicy, InsuranceClaim,
    Donation, DonationContribution, GroupInvestment, InvestmentQuote,
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
    recipient_email = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    group_cover_photo = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    
    class Meta:
        model = TransactionToken
        fields = '__all__'
        read_only_fields = ['transaction_code', 'created_at']

    def get_recipient_email(self, obj):
        try:
            return obj.recipient_profile.user.user.email if obj.recipient_profile else None
        except Exception:
            return None

    def get_sender_email(self, obj):
        try:
            return obj.payment_profile.user.user.email if obj.payment_profile else None
        except Exception:
            return None

    def get_group_name(self, obj):
        if obj.payment_group:
            return obj.payment_group.name
        return None

    def get_group_cover_photo(self, obj):
        if obj.payment_group and obj.payment_group.cover_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.payment_group.cover_photo.url)
            return obj.payment_group.cover_photo.url
        return None

    def get_group_id(self, obj):
        if obj.payment_group:
            return str(obj.payment_group.id)
        return None

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
    can_withdraw = serializers.SerializerMethodField()
    withdrawal_message = serializers.SerializerMethodField()
    is_matured = serializers.BooleanField(read_only=True)
    savings_type_display = serializers.CharField(source='get_savings_type_display', read_only=True)
    contribution_mode_display = serializers.CharField(source='get_contribution_mode_display', read_only=True)
    
    class Meta:
        model = GroupTarget
        fields = '__all__'
        read_only_fields = ['achieved', 'achieved_at', 'current_amount', 'accrued_interest', 'last_interest_date']
    
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
    
    def get_can_withdraw(self, obj):
        allowed, _ = obj.can_withdraw()
        return allowed
    
    def get_withdrawal_message(self, obj):
        _, message = obj.can_withdraw()
        return message

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

# ── Group Phase / Post serializers ─────────────────────────────
class GroupPhaseSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = GroupPhase
        fields = '__all__'
        read_only_fields = ['id', 'current_amount', 'created_at']

    def get_progress_percentage(self, obj):
        if obj.target_amount and obj.target_amount > 0:
            return round((float(obj.current_amount) / float(obj.target_amount)) * 100, 2)
        return 0.0


class GroupPostReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()

    class Meta:
        model = GroupPostReply
        fields = '__all__'
        read_only_fields = ['id', 'author', 'created_at']

    def get_author_name(self, obj):
        try:
            return f"{obj.author.user.user.first_name} {obj.author.user.user.last_name}"
        except Exception:
            return 'Unknown'

    def get_author_avatar(self, obj):
        try:
            if obj.author.user.profile_picture:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.author.user.profile_picture.url)
                return obj.author.user.profile_picture.url
        except Exception:
            pass
        return None


class GroupPostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    replies = GroupPostReplySerializer(many=True, read_only=True)
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = GroupPost
        fields = '__all__'
        read_only_fields = ['id', 'author', 'reactions', 'created_at', 'updated_at']

    def get_author_name(self, obj):
        try:
            return f"{obj.author.user.user.first_name} {obj.author.user.user.last_name}"
        except Exception:
            return 'Unknown'

    def get_author_avatar(self, obj):
        try:
            if obj.author.user.profile_picture:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.author.user.profile_picture.url)
                return obj.author.user.profile_picture.url
        except Exception:
            pass
        return None

    def get_reply_count(self, obj):
        return obj.replies.count()


class PaymentGroupsSerializer(serializers.ModelSerializer):
    members = PaymentGroupMemberSerializer(many=True, read_only=True)
    contributions_summary = serializers.SerializerMethodField()
    targets = GroupTargetSerializer(many=True, read_only=True)
    phases = GroupPhaseSerializer(many=True, read_only=True)
    creator_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    parent_group_name = serializers.SerializerMethodField()
    
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

    def get_parent_group_name(self, obj):
        return obj.parent_group.name if obj.parent_group else None

class GroupCheckoutRequestSerializer(serializers.ModelSerializer):
    initiator_name = serializers.SerializerMethodField()
    initiator_username = serializers.SerializerMethodField()
    initiator_profile_picture = serializers.SerializerMethodField()
    approvals_count = serializers.SerializerMethodField()
    rejections_count = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    group_cover_photo = serializers.SerializerMethodField()
    recipient_info = serializers.SerializerMethodField()

    class Meta:
        model = GroupCheckoutRequest
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_initiator_name(self, obj):
        if obj.initiator and obj.initiator.user:
            return f"{obj.initiator.user.user.first_name} {obj.initiator.user.user.last_name}"
        return "Unknown"

    def get_initiator_username(self, obj):
        try:
            return obj.initiator.user.user.username if obj.initiator else None
        except Exception:
            return None

    def get_initiator_profile_picture(self, obj):
        try:
            if obj.initiator and obj.initiator.user and obj.initiator.user.profile_picture:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.initiator.user.profile_picture.url)
                return obj.initiator.user.profile_picture.url
        except Exception:
            pass
        return None

    def get_approvals_count(self, obj):
        return obj.approvals.count()

    def get_rejections_count(self, obj):
        return obj.rejections.count()

    def get_total_members(self, obj):
        return obj.group.members.count()

    def get_group_name(self, obj):
        return obj.group.name if obj.group else None

    def get_group_cover_photo(self, obj):
        if obj.group and obj.group.cover_photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.group.cover_photo.url)
            return obj.group.cover_photo.url
        return None

    def get_recipient_info(self, obj):
        """Extract recipient/business info from items_payload."""
        if not obj.items_payload:
            return None
        # Try to find the first item with business/recipient info
        for item in obj.items_payload:
            name = item.get('name') or item.get('business_name')
            if name:
                return {
                    'name': name,
                    'id': item.get('id'),
                    'type': item.get('type', 'product'),
                    'profile_picture': item.get('profile_picture') or item.get('image'),
                }
        return None

class PaymentGroupsCreateSerializer(serializers.ModelSerializer):
    phases_data = serializers.ListField(child=serializers.DictField(), write_only=True, required=False, default=[])

    class Meta:
        model = PaymentGroups
        fields = ['name', 'description', 'max_capacity', 'target_amount', 'expiry_date', 
                  'deadline', 'auto_purchase', 'requires_approval', 'is_public',
                  'contribution_type', 'contribution_amount', 'frequency', 'group_type',
                  'allow_anonymous', 'auto_create_room',
                  'investment_pitch', 'loan_proposition', 'parent_group',
                  'joining_minimum', 'accent_color', 'entry_fee_required',
                  'entry_fee_amount', 'phases_data']


class KittySerializer(serializers.ModelSerializer):
    """Serializer tailored for the kitty management frontend."""
    balance = serializers.DecimalField(source='current_amount', max_digits=12, decimal_places=2)
    total_inflow = serializers.SerializerMethodField()
    total_outflow = serializers.SerializerMethodField()
    entity_type = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    investors_count = serializers.SerializerMethodField()
    is_charity = serializers.SerializerMethodField()
    monthly_data = serializers.SerializerMethodField()
    connected_accounts = serializers.SerializerMethodField()

    class Meta:
        model = PaymentGroups
        fields = [
            'id', 'name', 'description', 'balance', 'currency', 'status',
            'total_inflow', 'total_outflow', 'entity_type', 'type',
            'investors_count', 'is_charity', 'monthly_data',
            'connected_accounts', 'created_at', 'target_amount',
        ]

    # ── Computed helpers ──────────────────────────────────────────
    def _contributions_qs(self, obj):
        return obj.contributions.all()

    def get_total_inflow(self, obj):
        from django.db.models import Sum
        total = self._contributions_qs(obj).aggregate(total=Sum('amount'))['total']
        return float(total or 0)

    def get_total_outflow(self, obj):
        """Outflow = total_inflow − current_amount (what has been withdrawn)."""
        inflow = self.get_total_inflow(obj)
        return max(inflow - float(obj.current_amount), 0)

    def get_entity_type(self, obj):
        if obj.entity_content_type:
            return obj.entity_content_type.model.title()
        return 'General'

    def get_type(self, obj):
        if not obj.entity_content_type:
            return 'business'
        model_name = obj.entity_content_type.model.lower()
        mapping = {
            'business': 'enterprise',
            'capitalventure': 'venture',
            'shopregistration': 'shop',
            'organisation': 'business',
            'institution': 'business',
            'specialization': 'business',
        }
        return mapping.get(model_name, 'business')

    def get_status(self, obj):
        if obj.is_terminated:
            return 'terminated'
        return 'active' if obj.is_active else 'inactive'

    def get_currency(self, obj):
        return 'KES'

    def get_investors_count(self, obj):
        return obj.members.count()

    def get_is_charity(self, obj):
        if obj.entity_content_type:
            model = obj.entity_content_type.model.lower()
            if model == 'business':
                entity = obj.entity
                if entity and hasattr(entity, 'is_charity'):
                    return entity.is_charity
        return False

    def get_monthly_data(self, obj):
        """Aggregate contributions by month for the last 7 months."""
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth
        from datetime import datetime, timedelta
        from django.utils import timezone

        end = timezone.now()
        start = end - timedelta(days=210)  # ~7 months

        monthly = (
            obj.contributions
               .filter(contributed_at__gte=start)
               .annotate(month=TruncMonth('contributed_at'))
               .values('month')
               .annotate(inflow=Sum('amount'))
               .order_by('month')
        )

        result = []
        for entry in monthly:
            month_label = entry['month'].strftime('%b')
            inflow = float(entry['inflow'] or 0)
            # Outflow is approximated as a fraction of inflow for display
            outflow = round(inflow * 0.65, 2)
            result.append({'month': month_label, 'inflow': inflow, 'outflow': outflow})
        return result

    def get_connected_accounts(self, obj):
        # Placeholder — real connected accounts would come from a related model
        return []


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
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def _resolve_image(self, field_file):
        """Return the URL for an image field, handling external URLs stored as strings."""
        if not field_file:
            return None
        url = str(field_file)
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if hasattr(field_file, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(field_file.url)
            return field_file.url
        return url
    
    def get_image(self, obj):
        return self._resolve_image(obj.image)


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
    logo = serializers.SerializerMethodField()
    banner = serializers.SerializerMethodField()
    
    class Meta:
        model = Establishment
        fields = '__all__'
        read_only_fields = ['owner', 'slug', 'rating', 'review_count', 'is_verified', 'created_at', 'updated_at']
    
    def _resolve_image(self, field_file):
        """Return the URL for an image field, handling external URLs stored as strings."""
        if not field_file:
            return None
        url = str(field_file)
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if hasattr(field_file, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(field_file.url)
            return field_file.url
        return url
    
    def get_logo(self, obj):
        return self._resolve_image(obj.logo)
    
    def get_banner(self, obj):
        return self._resolve_image(obj.banner)
    
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
    logo = serializers.SerializerMethodField()
    banner = serializers.SerializerMethodField()
    
    class Meta:
        model = Establishment
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'banner',
            'establishment_type', 'establishment_type_display', 'categories',
            'city', 'country', 'rating', 'review_count', 'branch_count',
            'delivery_available', 'pickup_available', 'dine_in_available',
            'is_active', 'is_verified'
        ]
    
    def _resolve_image(self, field_file):
        """Return the URL for an image field, handling external URLs stored as strings."""
        if not field_file:
            return None
        url = str(field_file)
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if hasattr(field_file, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(field_file.url)
            return field_file.url
        return url
    
    def get_logo(self, obj):
        return self._resolve_image(obj.logo)
    
    def get_banner(self, obj):
        return self._resolve_image(obj.banner)
    
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
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceOffering
        fields = '__all__'
        read_only_fields = ['provider', 'created_at']
    
    def _resolve_image(self, field_file):
        """Return the URL for an image field, handling external URLs stored as strings."""
        if not field_file:
            return None
        url = str(field_file)
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if hasattr(field_file, 'url'):
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(field_file.url)
            return field_file.url
        return url
    
    def get_image(self, obj):
        return self._resolve_image(obj.image)
    
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
    group_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['id', 'buyer', 'status', 'total_amount', 'created_at', 'updated_at']
    
    def get_buyer_name(self, obj):
        return f"{obj.buyer.user.first_name} {obj.buyer.user.last_name}"
        
    def get_group_name(self, obj):
        if obj.payment_group:
            return obj.payment_group.name
        return None


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating orders with items."""
    establishment_id = serializers.IntegerField(required=False)
    order_type = serializers.ChoiceField(choices=['product', 'food', 'hotel_booking', 'service_appointment'])
    delivery_mode = serializers.ChoiceField(choices=['pickup', 'delivery', 'appointment'])
    payment_type = serializers.ChoiceField(choices=['individual', 'group'], default='individual')
    sales_channel = serializers.ChoiceField(choices=['online', 'in_store', 'pop_up'], default='online')
    is_offline = serializers.BooleanField(default=False)
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


# ============================================================================
# GROUP DISCOURSE & VOTING SERIALIZERS
# ============================================================================

class GroupJoinRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    requester_email = serializers.SerializerMethodField()
    requester_avatar = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    group_entry_fee_amount = serializers.DecimalField(source='group.entry_fee_amount', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = GroupJoinRequest
        fields = '__all__'
        read_only_fields = ['id', 'requester', 'status', 'reviewed_by', 'review_notes', 'has_paid_entry_fee', 'created_at', 'updated_at']
    
    def get_requester_name(self, obj):
        try:
            return f"{obj.requester.user.user.first_name} {obj.requester.user.user.last_name}"
        except Exception:
            return "Unknown"
    
    def get_requester_email(self, obj):
        try:
            return obj.requester.user.user.email
        except Exception:
            return None
    
    def get_requester_avatar(self, obj):
        try:
            if obj.requester.user.profile_picture:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.requester.user.profile_picture.url)
                return obj.requester.user.profile_picture.url
        except Exception:
            pass
        return None


class GroupVoteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='group.name', read_only=True)
    vote_type_display = serializers.CharField(source='get_vote_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_votes = serializers.IntegerField(read_only=True)
    approval_percentage = serializers.FloatField(read_only=True)
    votes_for_count = serializers.SerializerMethodField()
    votes_against_count = serializers.SerializerMethodField()
    votes_abstain_count = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupVote
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'status', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        try:
            return f"{obj.created_by.user.user.first_name} {obj.created_by.user.user.last_name}"
        except Exception:
            return "Unknown"
    
    def get_votes_for_count(self, obj):
        return obj.votes_for.count()
    
    def get_votes_against_count(self, obj):
        return obj.votes_against.count()
    
    def get_votes_abstain_count(self, obj):
        return obj.votes_abstain.count()
    
    def get_user_vote(self, obj):
        """Return the current user's vote on this item."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            from Authentication.models import Profile
            profile = Profile.objects.get(user=request.user)
            pp = PaymentProfile.objects.get(user=profile)
            if obj.votes_for.filter(pk=pp.pk).exists():
                return 'for'
            if obj.votes_against.filter(pk=pp.pk).exists():
                return 'against'
            if obj.votes_abstain.filter(pk=pp.pk).exists():
                return 'abstain'
        except Exception:
            pass
        return None


# ==================== BILL PAYMENT SERIALIZERS ====================

class BillProviderSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = BillProvider
        fields = '__all__'


class BillPaymentSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_category = serializers.CharField(source='provider.get_category_display', read_only=True)
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    
    class Meta:
        model = BillPayment
        fields = '__all__'
        read_only_fields = ['commission', 'total_amount', 'reference', 'status', 'completed_at', 'user', 'transaction', 'error_message']


from Payment.models import UserServiceProvider, BillStandingOrder
class UserServiceProviderSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    destination_type_display = serializers.CharField(source='get_destination_type_display', read_only=True)

    class Meta:
        model = UserServiceProvider
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class BillStandingOrderSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_account = serializers.CharField(source='provider.account_number', read_only=True)

    class Meta:
        model = BillStandingOrder
        fields = '__all__'
        read_only_fields = ['user', 'created_at', 'updated_at']


# ==================== LOAN SERIALIZERS ====================

class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = '__all__'


class CreditScoreSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    risk_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    class Meta:
        model = CreditScore
        fields = '__all__'
        read_only_fields = ['user', 'score', 'risk_level', 'factors', 'savings_score', 'repayment_score', 'group_score', 'transaction_score', 'tenure_score', 'computed_at']


class LoanRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRepayment
        fields = '__all__'
        read_only_fields = ['loan', 'installment_number', 'amount_due', 'due_date']


class LoanApplicationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='loan_product.name', read_only=True)
    product_interest = serializers.DecimalField(source='loan_product.interest_rate', max_digits=6, decimal_places=2, read_only=True)
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    repayments = LoanRepaymentSerializer(many=True, read_only=True)
    guarantor_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LoanApplication
        fields = '__all__'
        read_only_fields = ['id', 'user', 'monthly_payment', 'total_repayment', 'processing_fee_amount', 'credit_score_at_application', 'status', 'rejection_reason', 'disbursed_at', 'completed_at']
    
    def get_guarantor_count(self, obj):
        return obj.guarantors.count()


# ==================== ESCROW SERIALIZERS ====================

class EscrowDisputeSerializer(serializers.ModelSerializer):
    raised_by_email = serializers.EmailField(source='raised_by.user.email', read_only=True)
    
    class Meta:
        model = EscrowDispute
        fields = '__all__'
        read_only_fields = ['raised_by', 'resolved_by', 'resolved_at']


class EscrowTransactionSerializer(serializers.ModelSerializer):
    buyer_email = serializers.EmailField(source='buyer.user.email', read_only=True)
    seller_email = serializers.EmailField(source='seller.user.email', read_only=True)
    buyer_name = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    disputes = EscrowDisputeSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_escrow_type_display', read_only=True)
    
    class Meta:
        model = EscrowTransaction
        fields = '__all__'
        read_only_fields = ['id', 'escrow_fee', 'total_amount', 'funded_at', 'delivered_at', 'released_at']
    
    def get_buyer_name(self, obj):
        return f"{obj.buyer.user.first_name} {obj.buyer.user.last_name}".strip() or obj.buyer.user.email
    
    def get_seller_name(self, obj):
        return f"{obj.seller.user.first_name} {obj.seller.user.last_name}".strip() or obj.seller.user.email


# ==================== INSURANCE SERIALIZERS ====================

class InsuranceProductSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    frequency_display = serializers.CharField(source='get_premium_frequency_display', read_only=True)
    
    class Meta:
        model = InsuranceProduct
        fields = '__all__'


class InsuranceClaimSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = InsuranceClaim
        fields = '__all__'
        read_only_fields = ['id', 'claimant', 'amount_approved', 'reviewer_notes', 'reviewed_at', 'paid_at']


class InsurancePolicySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_provider = serializers.CharField(source='product.provider', read_only=True)
    product_category = serializers.CharField(source='product.get_category_display', read_only=True)
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    claims = InsuranceClaimSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = InsurancePolicy
        fields = '__all__'
        read_only_fields = ['id', 'user', 'policy_number', 'status', 'premium_paid', 'total_premiums_due']


# ==================== DONATIONS & CHARITY SERIALIZERS ====================

class DonationContributionSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    donor_email = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DonationContribution
        fields = '__all__'
        read_only_fields = ['id', 'confirmed_at', 'created_at']

    def get_member_name(self, obj):
        if obj.member:
            if obj.member.is_anonymous:
                return obj.member.anonymous_alias or 'Anonymous'
            return f"{obj.member.payment_profile.user.user.first_name} {obj.member.payment_profile.user.user.last_name}"
        if obj.donor_profile:
            return f"{obj.donor_profile.user.user.first_name} {obj.donor_profile.user.user.last_name}"
        return 'Unknown'

    def get_donor_email(self, obj):
        try:
            return obj.donor_profile.user.user.email
        except Exception:
            return None


class DonationSerializer(serializers.ModelSerializer):
    contributions = DonationContributionSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    donor_type_display = serializers.CharField(source='get_donor_type_display', read_only=True)
    mode_display = serializers.CharField(source='get_donation_mode_display', read_only=True)
    group_name = serializers.SerializerMethodField()
    donor_name = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    contributor_count = serializers.SerializerMethodField()
    confirmed_count = serializers.SerializerMethodField()
    goal_amount = serializers.DecimalField(source='total_amount', max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Donation
        fields = '__all__'
        read_only_fields = ['id', 'amount_collected', 'created_at', 'updated_at']

    def get_group_name(self, obj):
        return obj.payment_group.name if obj.payment_group else None

    def get_donor_name(self, obj):
        if obj.donor_profile:
            return f"{obj.donor_profile.user.user.first_name} {obj.donor_profile.user.user.last_name}"
        if obj.payment_group:
            return obj.payment_group.name
        return 'Unknown'

    def get_progress_percentage(self, obj):
        if obj.total_amount and obj.total_amount > 0:
            return round((float(obj.amount_collected) / float(obj.total_amount)) * 100, 2)
        return 0.0

    def get_contributor_count(self, obj):
        return obj.contributions.count()

    def get_confirmed_count(self, obj):
        return obj.contributions.filter(status='confirmed').count()


# ==================== GROUP INVESTMENT SERIALIZERS ====================

class InvestmentQuoteSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    member_email = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InvestmentQuote
        fields = '__all__'
        read_only_fields = ['id', 'ownership_percentage', 'allocated_returns', 'confirmed_at', 'created_at']

    def get_member_name(self, obj):
        if obj.member.is_anonymous:
            return obj.member.anonymous_alias or 'Anonymous'
        return f"{obj.member.payment_profile.user.user.first_name} {obj.member.payment_profile.user.user.last_name}"

    def get_member_email(self, obj):
        try:
            if obj.member.is_anonymous:
                return None
            return obj.member.payment_profile.user.user.email
        except Exception:
            return None


class GroupInvestmentSerializer(serializers.ModelSerializer):
    quotes = InvestmentQuoteSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    quoting_mode_display = serializers.CharField(source='get_quoting_mode_display', read_only=True)
    group_name = serializers.SerializerMethodField()
    initiator_name = serializers.SerializerMethodField()
    quote_count = serializers.SerializerMethodField()
    confirmed_count = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    opportunity_name = serializers.SerializerMethodField()
    opportunity_category = serializers.SerializerMethodField()

    class Meta:
        model = GroupInvestment
        fields = '__all__'
        read_only_fields = ['id', 'amount_collected', 'total_returns', 'net_profit_loss', 'created_at', 'updated_at']

    def get_group_name(self, obj):
        return obj.payment_group.name if obj.payment_group else None

    def get_initiator_name(self, obj):
        if obj.initiated_by:
            return f"{obj.initiated_by.user.user.first_name} {obj.initiated_by.user.user.last_name}"
        return None

    def get_quote_count(self, obj):
        return obj.quotes.count()

    def get_confirmed_count(self, obj):
        return obj.quotes.filter(status='confirmed').count()

    def get_progress_percentage(self, obj):
        if obj.total_amount and obj.total_amount > 0:
            return round((float(obj.amount_collected) / float(obj.total_amount)) * 100, 2)
        return 0.0

    def get_opportunity_name(self, obj):
        if obj.investment_opportunity:
            return obj.investment_opportunity.title
        if obj.capital_venture:
            return obj.capital_venture.name
        return None

    def get_opportunity_category(self, obj):
        if obj.investment_opportunity:
            return obj.investment_opportunity.get_type_display()
        if obj.capital_venture:
            return "Venture Capital"
        return "Internal Group Fund"
