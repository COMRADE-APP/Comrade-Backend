from decimal import Decimal
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
    GroupCertificate,
    RoundContribution, RoundMemberContribution, BenefitDistributionRule,
    WithdrawalRequest, GroupSettingsChangeRequest, RoundPosition,
    PiggyBankConversionRequest,
    ProviderRegistration, ProviderDocument, ProviderStaff, ServiceProduct,
    ProviderTransaction, ProviderQuery, ProviderApplication, ProviderNotification
)
from Payment.models import TRANSACTION_CATEGORY, PAY_OPT
from Authentication.models import Profile, CustomUser
from Payment.utils import get_or_create_payment_profile

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
    recipient_name = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()
    initiator_name = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    group_cover_photo = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    
    class Meta:
        model = TransactionToken
        fields = '__all__'
        read_only_fields = ['transaction_code', 'created_at']

    def get_recipient_email(self, obj):
        try:
            return obj.recipient_profile.user.user.email if obj.recipient_profile else None
        except Exception:
            return None

    def get_recipient_name(self, obj):
        try:
            if obj.recipient_profile:
                user = obj.recipient_profile.user.user
                return f"{user.first_name} {user.last_name}".strip() or user.username
            return None
        except Exception:
            return None

    def get_sender_email(self, obj):
        try:
            return obj.payment_profile.user.user.email if obj.payment_profile else None
        except Exception:
            return None

    def get_initiator_name(self, obj):
        try:
            if obj.payment_profile:
                user = obj.payment_profile.user.user
                return f"{user.first_name} {user.last_name}".strip() or user.username
            return None
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

    def get_direction(self, obj):
        request = self.context.get('request')
        if not request:
            return 'unknown'
        try:
            current_user = request.user
            payment_profile = obj.payment_profile
            recipient_profile = obj.recipient_profile
            
            if payment_profile and payment_profile.user.user == current_user:
                return 'sent'
            elif recipient_profile and recipient_profile.user.user == current_user:
                return 'received'
            return 'unknown'
        except Exception:
            return 'unknown'

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


class TransactionHistoryDetailSerializer(serializers.ModelSerializer):
    transaction_code = serializers.UUIDField(source='transaction_token.transaction_code', read_only=True)
    transaction_type = serializers.CharField(source='transaction_token.transaction_type', read_only=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(source='transaction_token.created_at', read_only=True)
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()
    recipient_email = serializers.SerializerMethodField()
    payment_option = serializers.CharField(source='transaction_token.payment_option', read_only=True)
    description = serializers.CharField(source='transaction_token.description', read_only=True)
    authorization_code = serializers.SerializerMethodField()
    verification_code = serializers.SerializerMethodField()
    can_be_reversed = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    group_cover_photo = serializers.SerializerMethodField()

    class Meta:
        model = TransactionHistory
        fields = [
            'id', 'transaction_code', 'transaction_type', 'transaction_category',
            'amount', 'status', 'payment_type', 'created_at',
            'sender_name', 'sender_email', 'recipient_name', 'recipient_email',
            'payment_option', 'description', 'authorization_code', 'verification_code',
            'can_be_reversed', 'direction', 'group_id', 'group_name', 'group_cover_photo'
        ]

    def get_sender_name(self, obj):
        try:
            profile = obj.payment_profile
            if profile and profile.user:
                user = profile.user.user
                return f"{user.first_name} {user.last_name}".strip() or user.email
            return None
        except Exception:
            return None

    def get_sender_email(self, obj):
        try:
            return obj.payment_profile.user.user.email if obj.payment_profile else None
        except Exception:
            return None

    def get_recipient_name(self, obj):
        try:
            recipient = obj.transaction_token.recipient_profile
            if recipient and recipient.user:
                user = recipient.user.user
                return f"{user.first_name} {user.last_name}".strip() or user.email
            return None
        except Exception:
            return None

    def get_recipient_email(self, obj):
        try:
            recipient = obj.transaction_token.recipient_profile
            return recipient.user.user.email if recipient else None
        except Exception:
            return None

    def get_direction(self, obj):
        request = self.context.get('request')
        if not request:
            return 'unknown'
        try:
            current_user = request.user
            sender_profile = obj.payment_profile
            recipient = obj.transaction_token.recipient_profile
            
            if sender_profile and sender_profile.user.user == current_user:
                return 'sent'
            elif recipient and recipient.user.user == current_user:
                return 'received'
            return 'unknown'
        except Exception:
            return 'unknown'

    def get_group_id(self, obj):
        try:
            if obj.transaction_token and obj.transaction_token.payment_group:
                return str(obj.transaction_token.payment_group.id)
            return None
        except Exception:
            return None

    def get_group_name(self, obj):
        try:
            if obj.transaction_token and obj.transaction_token.payment_group:
                return obj.transaction_token.payment_group.name
            return None
        except Exception:
            return None

    def get_group_cover_photo(self, obj):
        try:
            if obj.transaction_token and obj.transaction_token.payment_group:
                group = obj.transaction_token.payment_group
                if group.cover_photo:
                    request = self.context.get('request')
                    if request:
                        return request.build_absolute_uri(group.cover_photo.url)
                    return group.cover_photo.url
            return None
        except Exception:
            return None

    def get_authorization_code(self, obj):
        if obj.authorization_token:
            return obj.authorization_token.authorization_code
        return None

    def get_verification_code(self, obj):
        if obj.verification_token:
            return obj.verification_token.verification_code
        return None

    def get_can_be_reversed(self, obj):
        try:
            if obj.transaction_token:
                return obj.transaction_token.status in ['completed', 'verified', 'settled'] and not obj.transaction_token.reversed_at
            return False
        except Exception:
            return False

# Payment Group Serializers
class PaymentGroupMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentGroupMember
        fields = '__all__'
        read_only_fields = ['total_contributed', 'joined_at', 'anonymous_alias']
    
    def get_user_email(self, obj):
        if obj.is_anonymous or not obj.payment_profile or not obj.payment_profile.user or not obj.payment_profile.user.user:
            return None
        return obj.payment_profile.user.user.email
    
    def get_user_name(self, obj):
        if obj.is_anonymous:
            return obj.anonymous_alias or 'Anonymous Member'
        if obj.payment_profile and obj.payment_profile.user and obj.payment_profile.user.user:
            return f"{obj.payment_profile.user.user.first_name} {obj.payment_profile.user.user.last_name}"
        return "Unknown Member"

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
    upvote_count = serializers.SerializerMethodField()
    has_upvoted = serializers.SerializerMethodField()
    child_replies = serializers.SerializerMethodField()
    reaction_summary = serializers.SerializerMethodField()

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

    def get_upvote_count(self, obj):
        return getattr(obj, 'upvotes', []).count() if hasattr(obj, 'upvotes') else 0

    def get_has_upvoted(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        try:
            return hasattr(obj, 'upvotes') and obj.upvotes.filter(user__user__email=request.user.email).exists()
        except Exception:
            return False

    def get_reaction_summary(self, obj):
        request = self.context.get('request')
        user_id = str(request.user.id) if request and request.user.is_authenticated else None
        
        summary = []
        reactions = getattr(obj, 'reactions', {}) or {}
        for icon, users in reactions.items():
            if users:
                summary.append({
                    'emoji': icon,
                    'count': len(users),
                    'has_reacted': user_id in users if user_id else False
                })
        return summary

    def get_child_replies(self, obj):
        if obj.child_replies.exists():
            return GroupPostReplySerializer(obj.child_replies.all(), many=True, context=self.context).data
        return []


class GroupPostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    def get_replies(self, obj):
        top_level_replies = obj.replies.filter(parent_reply__isnull=True)
        return GroupPostReplySerializer(top_level_replies, many=True, context=self.context).data
    reply_count = serializers.SerializerMethodField()
    upvote_count = serializers.SerializerMethodField()
    has_upvoted = serializers.SerializerMethodField()
    reaction_summary = serializers.SerializerMethodField()

    class Meta:
        model = GroupPost
        fields = '__all__'
        read_only_fields = ['id', 'author', 'reactions', 'upvotes', 'created_at', 'updated_at']

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

    def get_upvote_count(self, obj):
        return getattr(obj, 'upvotes', []).count() if hasattr(obj, 'upvotes') else 0

    def get_has_upvoted(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        try:
            return hasattr(obj, 'upvotes') and obj.upvotes.filter(user__user__email=request.user.email).exists()
        except Exception:
            return False

    def get_reaction_summary(self, obj):
        request = self.context.get('request')
        user_id = str(request.user.id) if request and request.user.is_authenticated else None
        
        summary = []
        reactions = obj.reactions or {}
        for icon, users in reactions.items():
            if users:
                summary.append({
                    'emoji': icon,
                    'count': len(users),
                    'has_reacted': user_id in users if user_id else False
                })
        return summary


class GroupCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupCertificate
        fields = '__all__'

class PaymentGroupsSerializer(serializers.ModelSerializer):
    certificate = GroupCertificateSerializer(read_only=True)
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
        if obj.creator and obj.creator.user and obj.creator.user.user:
            return f"{obj.creator.user.user.first_name} {obj.creator.user.user.last_name}"
        return "Unknown"

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
                  'investment_pitch', 'loan_proposition', 'parent_group', 'is_kitty',
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
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
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
    
    # Card fields (PCI compliant - expects tokenized provider_token from frontend)
    provider_token = serializers.CharField(required=False, help_text='Stripe PaymentMethod ID (e.g., pm_12345)')
    
    # Optional fields for manual entry (deprecated - use provider_token instead)
    card_number = serializers.CharField(required=False, max_length=19, allow_blank=True)
    expiry_month = serializers.IntegerField(required=False, min_value=1, max_value=12, allow_null=True)
    expiry_year = serializers.IntegerField(required=False, min_value=2024, allow_null=True)
    cvc = serializers.CharField(required=False, max_length=4, allow_blank=True)
    billing_zip = serializers.CharField(required=False, max_length=20, allow_blank=True)
    
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
        """Card number validation is deprecated. Use provider_token instead."""
        return value
    
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
            pp = get_or_create_payment_profile(request.user)
            if not pp:
                return None
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
    
    def validate(self, data):
        # If loan_product is passed as an ID string, convert to object
        if 'loan_product' in data and isinstance(data['loan_product'], str):
            try:
                from Payment.models import LoanProduct
                data['loan_product'] = LoanProduct.objects.get(id=data['loan_product'])
            except:
                pass
        # If group is passed as ID string, convert to object
        if 'group' in data and isinstance(data['group'], str):
            try:
                from Payment.models import PaymentGroups
                data['group'] = PaymentGroups.objects.get(id=data['group'])
            except:
                pass
        return data


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
    end_date = serializers.DateTimeField(source='deadline', required=False, allow_null=True)
    cover_image_url = serializers.SerializerMethodField()
    organization_details = serializers.JSONField(required=False, allow_null=True)
    
    class Meta:
        model = Donation
        fields = '__all__'
        read_only_fields = ['id', 'amount_collected', 'created_at', 'updated_at', 'cover_image_url']
    
    def get_cover_image_url(self, obj):
        try:
            if hasattr(obj, 'cover_image') and obj.cover_image:
                return obj.cover_image.url
            if hasattr(obj, 'banner_image') and obj.banner_image:
                return obj.banner_image.url
        except Exception:
            pass
        return None
    
    def to_internal_value(self, data):
        # Map end_date to deadline
        if 'end_date' in data:
            data['deadline'] = data.pop('end_date')
        return super().to_internal_value(data)

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

# ============================================================================
# PROVIDER MANAGEMENT SERIALIZERS
# ============================================================================

class ProviderDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProviderDocument
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'file_size', 'mime_type', 'status', 'verified_by', 'verified_at', 'created_at']

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ProviderStaffSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)

    class Meta:
        model = ProviderStaff
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'created_by', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"

    def get_user_avatar(self, obj):
        try:
            if obj.user.profile_picture:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.user.profile_picture.url)
                return obj.user.profile_picture.url
        except Exception:
            pass
        return None


class ServiceProductSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    linked_kitty_name = serializers.CharField(source='linked_kitty.name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProduct
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProviderTransactionSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)
    service_product_name = serializers.CharField(source='service_product.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    processed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProviderTransaction
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'reference_number', 'commission_amount', 'provider_amount', 'platform_amount', 'processed_at', 'created_at']

    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"

    def get_processed_by_name(self, obj):
        if obj.processed_by:
            return f"{obj.processed_by.user.user.first_name} {obj.processed_by.user.user.last_name}"
        return None


class ProviderQuerySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()
    query_type_display = serializers.CharField(source='get_query_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)

    class Meta:
        model = ProviderQuery
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'resolved_by', 'resolved_at', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            return f"{obj.assigned_to.user.user.first_name} {obj.assigned_to.user.user.last_name}"
        return None

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return f"{obj.resolved_by.user.user.first_name} {obj.resolved_by.user.user.last_name}"
        return None


class ProviderApplicationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    service_product_name = serializers.CharField(source='service_product.name', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    application_type_display = serializers.CharField(source='get_application_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    provider_name = serializers.CharField(source='provider.business_name', read_only=True)
    linked_policy_number = serializers.CharField(source='linked_policy.policy_number', read_only=True)
    linked_loan_id = serializers.UUIDField(source='linked_loan.id', read_only=True)

    class Meta:
        model = ProviderApplication
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'reviewed_by', 'reviewed_at', 'submitted_at', 'created_at', 'updated_at']

    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return f"{obj.reviewed_by.user.user.first_name} {obj.reviewed_by.user.user.last_name}"
        return None


class ProviderNotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    is_read_display = serializers.SerializerMethodField()

    class Meta:
        model = ProviderNotification
        fields = '__all__'
        read_only_fields = ['id', 'provider', 'user', 'created_at']

    def get_is_read_display(self, obj):
        return 'Read' if obj.is_read else 'Unread'


class ProviderRegistrationSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.user.email', read_only=True)
    provider_type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    documents = ProviderDocumentSerializer(many=True, read_only=True)
    staff_count = serializers.SerializerMethodField()
    service_products_count = serializers.SerializerMethodField()
    logo_url = serializers.SerializerMethodField()
    linked_kitty_name = serializers.CharField(source='linked_payment_group.name', read_only=True)

    class Meta:
        model = ProviderRegistration
        fields = '__all__'
        read_only_fields = [
            'id', 'user', 'status', 'rejection_reason', 'reviewed_by', 'review_notes',
            'reviewed_at', 'linked_payment_group', 'created_at', 'updated_at'
        ]

    def get_user_name(self, obj):
        return f"{obj.user.user.first_name} {obj.user.user.last_name}"

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return f"{obj.reviewed_by.user.user.first_name} {obj.reviewed_by.user.user.last_name}"
        return None

    def get_staff_count(self, obj):
        return obj.staff_members.filter(status='active').count()

    def get_service_products_count(self, obj):
        return obj.service_products.filter(status='active').count()

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None


class ProviderRegistrationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderRegistration
        fields = [
            'provider_type', 'business_name', 'business_email', 'business_phone',
            'business_address', 'business_registration_number', 'tax_id', 'category',
            'description', 'website', 'commission_rate', 'min_transaction_amount',
            'max_transaction_amount', 'supported_payment_methods', 'auto_create_kitty',
            'kitty_name', 'kitty_target_amount'
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            profile = Profile.objects.get(user=request.user)
            validated_data['user'] = profile
        return super().create(validated_data)


class ProviderRegistrationListSerializer(serializers.ModelSerializer):
    provider_type_display = serializers.CharField(source='get_provider_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    logo_url = serializers.SerializerMethodField()
    staff_count = serializers.SerializerMethodField()
    service_products_count = serializers.SerializerMethodField()

    class Meta:
        model = ProviderRegistration
        fields = [
            'id', 'business_name', 'provider_type', 'provider_type_display', 'category',
            'category_display', 'status', 'status_display', 'logo_url', 'staff_count',
            'service_products_count', 'created_at'
        ]

    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

    def get_staff_count(self, obj):
        return obj.staff_members.filter(status='active').count()

    def get_service_products_count(self, obj):
        return obj.service_products.filter(status='active').count()

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
    approval_vote = serializers.SerializerMethodField()
    is_group_member = serializers.SerializerMethodField()
    # Frontend alias fields
    investment_name = serializers.SerializerMethodField()
    amount_invested = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = GroupInvestment
        fields = '__all__'
        read_only_fields = ['id', 'amount_collected', 'total_returns', 'net_profit_loss', 'created_at', 'updated_at']

    def validate(self, data):
        if not data.get('name') and data.get('investment_name'):
            data['name'] = data['investment_name']
        return data
    
    def get_investment_name(self, obj):
        return obj.name
    
    def get_amount_invested(self, obj):
        return float(obj.total_amount) if obj.total_amount else 0
    
    def get_current_value(self, obj):
        return float(obj.total_amount) if obj.total_amount else 0
    
    def get_type(self, obj):
        return 'Commercial Venture'

    def get_group_name(self, obj):
        return obj.payment_group.name if obj.payment_group else None

    def get_initiator_name(self, obj):
        if obj.initiated_by:
            return f"{obj.initiated_by.user.user.first_name} {obj.initiated_by.user.user.last_name}"
        return None

    def get_approval_vote(self, obj):
        if obj.approval_vote:
            return GroupVoteSerializer(obj.approval_vote, context=self.context).data
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

    def get_is_group_member(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from Payment.models import PaymentProfile, PaymentGroupMember
        try:
            payment_profile = PaymentProfile.objects.get(user__user=request.user)
            if obj.payment_group:
                return PaymentGroupMember.objects.filter(payment_group=obj.payment_group, payment_profile=payment_profile).exists()
        except:
            return False
        return False

# ============================================================================
# ADVANCED GROUP FEATURES SERIALIZERS
# ============================================================================

class RoundMemberContributionSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.payment_profile.user.user.get_full_name', read_only=True)
    on_behalf_of_name = serializers.CharField(source='on_behalf_of.payment_profile.user.user.get_full_name', read_only=True)
    
    class Meta:
        model = RoundMemberContribution
        fields = '__all__'


class RoundPositionSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.payment_profile.user.user.get_full_name', read_only=True)
    
    class Meta:
        model = RoundPosition
        fields = '__all__'


class RoundApprovalMemberSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = PaymentGroupMember
        fields = ['id', 'member_name', 'profile_picture']

    def get_member_name(self, obj):
        try:
            user = obj.payment_profile.user.user
            full = user.get_full_name()
            return full if full.strip() else user.email
        except Exception:
            return str(obj.id)

    def get_profile_picture(self, obj):
        try:
            profile = obj.payment_profile.user
            if profile.profile_picture:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.profile_picture.url)
                return profile.profile_picture.url
        except Exception:
            pass
        return None


class RoundContributionSerializer(serializers.ModelSerializer):
    member_contributions = RoundMemberContributionSerializer(many=True, read_only=True)
    round_number = serializers.IntegerField(read_only=True)
    round_name = serializers.CharField(required=False, allow_blank=True)
    approvals = RoundApprovalMemberSerializer(many=True, read_only=True)
    rejections = RoundApprovalMemberSerializer(many=True, read_only=True)
    user_has_approved = serializers.SerializerMethodField()
    user_has_rejected = serializers.SerializerMethodField()
    user_position = serializers.SerializerMethodField()
    members_rotation = serializers.SerializerMethodField()
    cycle_contributions = serializers.SerializerMethodField()
    cycles_completed = serializers.IntegerField(source='total_cycles_completed', read_only=True)
    awarded_to_name = serializers.SerializerMethodField()
    is_recipient = serializers.SerializerMethodField()
    has_unclaimed_payout = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()
    pending_claim_amount = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = RoundContribution
        fields = '__all__'
        read_only_fields = ['approvals', 'rejections', 'approval_notes']

    def validate_round_name(self, value):
        """Ensure round name is unique per group."""
        if not value:  # Allow empty/blank names
            return value
        
        group = self.context.get('payment_group')
        if group and RoundContribution.objects.filter(payment_group=group, round_name=value).exists():
            if self.instance and self.instance.round_name == value:
                return value  # Allow updating same round with same name
            raise serializers.ValidationError(f"A round with name '{value}' already exists in this group.")
        return value

    def get_user_has_approved(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.approvals.filter(payment_profile__user__user=request.user).exists()

    def get_user_has_rejected(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.rejections.filter(payment_profile__user__user=request.user).exists()

    def get_user_position(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return None
        from Payment.models import RoundPosition
        pos = RoundPosition.objects.filter(round=obj, member__payment_profile__user__user=request.user).first()
        return pos.position_number if pos else None

    def get_members_rotation(self, obj):
        """Returns ordered list of members with past/current/future status."""
        from Payment.models import RoundPosition
        positions = RoundPosition.objects.filter(round=obj).order_by('position_number')
        rotation = []
        for pos in positions:
            # Check if this member has already been awarded in award_history
            has_received = any(str(pos.member.id) == str(history.get('member_id')) for history in obj.award_history)
            
            # They are current if they are the awarded_to or if it's their cycle and not received yet
            is_current = (obj.awarded_to_id == pos.member.id) or (obj.current_cycle == pos.position_number and not has_received and obj.status == 'active')
            
            status = 'past' if has_received else ('current' if is_current else 'pending')
            
            # If the round hasn't started, everyone is pending except maybe assigned positions
            if obj.status in ['pending_approval', 'pending']:
                status = 'pending'
                
            rotation.append({
                'member_id': pos.member.id,
                'name': pos.member.payment_profile.user.user.get_full_name() or pos.member.payment_profile.user.user.email,
                'position': pos.position_number,
                'status': status
            })
        return rotation

    def get_awarded_to_name(self, obj):
        request = self.context.get('request')
        if request and request.user and not request.user.is_anonymous:
            # Check current awarded recipient
            if obj.awarded_to and obj.awarded_to.payment_profile.user.user.id == request.user.id:
                return "Me"
            
            # Check if user has an unclaimed payout in history
            from Payment.models import PaymentGroupMember
            try:
                member = PaymentGroupMember.objects.get(
                    payment_group=obj.payment_group,
                    payment_profile__user__user=request.user
                )
                if any(str(h.get('member_id')) == str(member.id) and not h.get('claimed') for h in obj.award_history):
                    return "Me"
            except:
                pass

        if not obj.awarded_to:
            return "Not assigned"
        user = obj.awarded_to.payment_profile.user.user
        return user.get_full_name() or user.email

    def get_is_recipient(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return False

        from Payment.models import PaymentGroupMember
        try:
            member = PaymentGroupMember.objects.get(
                payment_group=obj.payment_group,
                payment_profile__user__user=request.user
            )
            # True if currently awarded OR has unclaimed payout in history
            if obj.awarded_to_id == member.id:
                return True
            if any(str(h.get('member_id')) == str(member.id) and not h.get('claimed') for h in obj.award_history):
                return True
        except PaymentGroupMember.DoesNotExist:
            pass

        return False

    def get_has_unclaimed_payout(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return False

        from Payment.models import PaymentGroupMember
        try:
            member = PaymentGroupMember.objects.get(
                payment_group=obj.payment_group,
                payment_profile__user__user=request.user
            )
            
            # Check if user is the awarded recipient with unclaimed funds (for current cycle)
            if obj.claim_status == 'unclaimed' and obj.awarded_to_id == member.id:
                return True
                
            # Also check award_history for any unclaimed cycle payouts for this member
            for h in obj.award_history:
                member_id = h.get('member_id')
                claimed = h.get('claimed', False)
                if member_id and str(member_id) == str(member.id) and not claimed:
                    return True
            
            return False
        except Exception as e:
            return False
    
    def get_can_claim(self, obj):
        """Check if the current user can claim their payout"""
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return False
        
        from Payment.models import PaymentGroupMember
        try:
            member = PaymentGroupMember.objects.get(
                payment_group=obj.payment_group,
                payment_profile__user__user=request.user
            )
            
            # Check if current user is the awarded recipient with unclaimed funds
            if obj.claim_status == 'unclaimed' and obj.awarded_to_id == member.id:
                return True
                
            # Also check award_history for unclaimed payouts for this user
            for h in obj.award_history:
                if str(h.get('member_id')) == str(member.id) and not h.get('claimed', False):
                    return True
            
            return False
        except:
            return False
    
    def get_pending_claim_amount(self, obj):
        """Get the amount pending for current user to claim"""
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return 0
        
        from Payment.models import PaymentGroupMember
        try:
            member = PaymentGroupMember.objects.get(
                payment_group=obj.payment_group,
                payment_profile__user__user=request.user
            )
            
            # Check current cycle
            if obj.claim_status == 'unclaimed' and obj.awarded_to_id == member.id:
                return float(obj.total_collected) if obj.total_collected else 0
                
            # Check award_history
            for h in obj.award_history:
                if str(h.get('member_id')) == str(member.id) and not h.get('claimed', False):
                    return h.get('amount', 0)
            
            return 0
        except:
            return 0

    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()

    def get_cycle_contributions(self, obj):
        """Returns contributions specifically for the current cycle."""
        contributions = obj.member_contributions.filter(cycle_number=obj.current_cycle)
        return RoundMemberContributionSerializer(contributions, many=True, context=self.context).data


class BenefitDistributionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenefitDistributionRule
        fields = '__all__'


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.CharField(source='requester.payment_profile.user.user.get_full_name', read_only=True)
    
    class Meta:
        model = WithdrawalRequest
        fields = '__all__'
        read_only_fields = ['status', 'approved_by', 'approval_date', 'rejection_reason', 'processed_at', 'transaction', 'immature_exit_deduction', 'payment_group', 'requester', 'destination_wallet']


class PiggyBankConversionRequestSerializer(serializers.ModelSerializer):
    proposed_by_name = serializers.CharField(source='proposed_by.payment_profile.user.user.username', read_only=True)
    proposed_by_display = serializers.CharField(source='proposed_by.payment_profile.user.user.get_full_name', read_only=True)
    piggy_bank_name = serializers.CharField(source='piggy_bank.name', read_only=True)
    group_name = serializers.CharField(source='piggy_bank.payment_group.name', read_only=True)
    
    approving_members_details = serializers.SerializerMethodField()
    rejecting_members_details = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    
    class Meta:
        model = PiggyBankConversionRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'approval_vote']
    
    def get_approving_members_details(self, obj):
        members = []
        for m in obj.approving_members.all():
            members.append({
                'id': str(m.id),
                'name': m.anonymous_alias if m.is_anonymous else m.payment_profile.user.user.get_full_name(),
                'is_anonymous': m.is_anonymous
            })
        return members
    
    def get_rejecting_members_details(self, obj):
        members = []
        for m in obj.rejecting_members.all():
            members.append({
                'id': str(m.id),
                'name': m.anonymous_alias if m.is_anonymous else m.payment_profile.user.user.get_full_name(),
                'is_anonymous': m.is_anonymous
            })
        return members
    
    def get_total_members(self, obj):
        if obj.piggy_bank and obj.piggy_bank.payment_group:
            return obj.piggy_bank.payment_group.members.count()
        return 0


class GroupSettingsChangeRequestSerializer(serializers.ModelSerializer):
    proposed_by_name = serializers.CharField(source='proposed_by.payment_profile.user.user.get_full_name', read_only=True)

    class Meta:
        model = GroupSettingsChangeRequest
        fields = '__all__'
        read_only_fields = ['status', 'approval_vote']


class CurrencyConversionSerializer(serializers.Serializer):
    from_currency = serializers.CharField(max_length=3)
    to_currency = serializers.CharField(max_length=3)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class CurrencyConversionResultSerializer(serializers.Serializer):
    original_amount = serializers.FloatField()
    original_currency = serializers.CharField()
    converted_amount = serializers.FloatField()
    target_currency = serializers.CharField()
    exchange_rate = serializers.FloatField()
    provider = serializers.CharField()
    timestamp = serializers.DateTimeField(default=None, required=False)


class ExchangeRateSerializer(serializers.Serializer):
    from_currency = serializers.CharField()
    to_currency = serializers.CharField()
    rate = serializers.DecimalField(max_digits=18, decimal_places=8)
    timestamp = serializers.DateTimeField(default=None, required=False)
