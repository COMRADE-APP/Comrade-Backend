from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
import uuid
import secrets

from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, IndividualShare
)
from Payment.serializers import (
    PaymentProfileSerializer, PaymentItemSerializer, PaymentLogSerializer,
    PaymentGroupsSerializer, TransactionTokenSerializer,
    PaymentAuthorizationSerializer, PaymentVerificationSerializer,
    TransactionHistorySerializer, TransactionTrackerSerializer,
    PaymentGroupMemberSerializer, ContributionSerializer,
    StandingOrderSerializer, GroupInvitationSerializer, GroupTargetSerializer,
    PaymentGroupsCreateSerializer, CreateTransactionSerializer,
    ProductSerializer, UserSubscriptionSerializer
)
from Authentication.models import Profile, CustomUser


class PaymentProfileViewSet(ModelViewSet):
    queryset = PaymentProfile.objects.all()
    serializer_class = PaymentProfileSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current user's payment profile"""
        try:
            profile = Profile.objects.get(user=request.user)
            payment_profile = PaymentProfile.objects.get(user=profile)
            serializer = self.get_serializer(payment_profile)
            return Response(serializer.data)
        except (Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get current user's balance"""
        try:
            profile = Profile.objects.get(user=request.user)
            payment_profile = PaymentProfile.objects.get(user=profile)
            return Response({'balance': payment_profile.comrade_balance})
        except (Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            return Response({'balance': 0.00})


from Payment.utils import check_purchase_limit, increment_purchase_count, check_group_creation_limit, get_max_group_members

class TransactionViewSet(ModelViewSet):
    queryset = TransactionToken.objects.all()
    serializer_class = TransactionTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get transactions for current user"""
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            payment_profile = PaymentProfile.objects.get(user=profile)
            return TransactionToken.objects.filter(
                Q(payment_profile=payment_profile) | Q(recipient_profile=payment_profile)
            ).select_related('payment_profile', 'recipient_profile').order_by('-created_at')
        except (Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            return TransactionToken.objects.none()
    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def create_transaction(self, request):
        """Create a new transaction"""
        serializer = CreateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        profile = Profile.objects.get(user=user)
        sender_payment_profile = PaymentProfile.objects.get(user=profile)
        
        # Check Tier Limits for Purchase
        transaction_type = serializer.validated_data['transaction_type']
        if transaction_type == 'purchase':
            can_purchase, error_msg = check_purchase_limit(sender_payment_profile)
            if not can_purchase:
                return Response({'error': error_msg}, status=status.HTTP_403_FORBIDDEN)
        
        # Get recipient
        recipient_email = serializer.validated_data['recipient_email']
        try:
            recipient_user = CustomUser.objects.get(email=recipient_email)
            recipient_profile = Profile.objects.get(user=recipient_user)
            recipient_payment_profile = PaymentProfile.objects.get(user=recipient_profile)
        except (CustomUser.DoesNotExist, Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        amount = serializer.validated_data['amount']
        payment_option = serializer.validated_data['payment_option']
        
        # Check balance for internal transfers/payments
        if payment_option == 'comrade_balance':
            if sender_payment_profile.comrade_balance < amount:
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Deduct balance
            sender_payment_profile.comrade_balance -= amount
            sender_payment_profile.save()
            
            # Add to recipient
            recipient_payment_profile.comrade_balance += amount
            recipient_payment_profile.save()
        
        # Create Transaction Record
        transaction = TransactionToken.objects.create(
            payment_profile=sender_payment_profile,
            recipient_profile=recipient_payment_profile,
            transaction_type=transaction_type,
            amount=amount,
            payment_option=payment_option,
            pay_from='internal' if payment_option == 'comrade_balance' else 'external'
        )
        
        # Create History
        TransactionHistory.objects.create(
            payment_profile=sender_payment_profile,
            transaction_token=transaction,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=sender_payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=sender_payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=amount, # Helper field
            status='completed'
        )
        
        # Increment purchase count if applicable
        if transaction_type == 'purchase':
            increment_purchase_count(sender_payment_profile)
            
        return Response(TransactionTokenSerializer(transaction).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get transaction history"""
        transactions = self.get_queryset()
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)



    

class PaymentGroupsViewSet(ModelViewSet):
    queryset = PaymentGroups.objects.all()
    serializer_class = PaymentGroupsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            payment_profile = PaymentProfile.objects.get(user=profile)
            return PaymentGroups.objects.filter(members__payment_profile=payment_profile).distinct()
        except:
            return PaymentGroups.objects.none()
            
    def perform_create(self, serializer):
        user = self.request.user
        profile = Profile.objects.get(user=user)
        payment_profile = PaymentProfile.objects.get(user=profile)
        
        # Check Limits
        can_create, error_msg = check_group_creation_limit(payment_profile)
        if not can_create:
            raise serializers.ValidationError(error_msg)
            
        # Set max capacity based on tier
        max_limit = get_max_group_members(payment_profile.tier)
        requested_capacity = serializer.validated_data.get('max_capacity', 10)
        final_capacity = min(requested_capacity, max_limit)
        if payment_profile.tier == 'gold':
            final_capacity = requested_capacity # Unlimited
            
        group = serializer.save(
            creator=payment_profile,
            tier=payment_profile.tier,
            max_capacity=final_capacity
        )
        
        # Add creator as admin member
        PaymentGroupMember.objects.create(
            payment_group=group,
            payment_profile=payment_profile,
            is_admin=True
        )

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a payment group"""
        group = self.get_object()
        user = request.user
        profile = Profile.objects.get(user=user)
        payment_profile = PaymentProfile.objects.get(user=profile)
        
        # Check capacity
        if group.members.count() >= group.max_capacity:
            return Response({'error': 'Group is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already a member
        if PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).exists():
            return Response({'error': 'Already a member'}, status=status.HTTP_400_BAD_REQUEST)
        
        member = PaymentGroupMember.objects.create(
            payment_group=group,
            payment_profile=payment_profile
        )
        
        return Response(PaymentGroupMemberSerializer(member).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def contribute(self, request, pk=None):
        """Make a contribution to the group"""
        group = self.get_object()
        user = request.user
        profile = Profile.objects.get(user=user)
        payment_profile = PaymentProfile.objects.get(user=profile)
        
        # Get member
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
        
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        amount = float(amount)
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Deduct from user
        payment_profile.comrade_balance -= amount
        payment_profile.save()
        
        # Add to group
        group.current_amount += amount
        group.save()
        
        # Update member contribution
        member.total_contributed += amount
        member.save()
        
        # Record contribution
        contribution = Contribution.objects.create(
            payment_group=group,
            member=member,
            amount=amount,
            notes=request.data.get('notes', '')
        )
        
        # Check if target reached
        if group.target_amount and group.current_amount >= group.target_amount:
            if group.auto_purchase:
                # Trigger auto purchase logic here
                pass
        
        return Response(ContributionSerializer(contribution).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """Invite someone to the group"""
        group = self.get_object()
        user = request.user
        profile = Profile.objects.get(user=user)
        payment_profile = PaymentProfile.objects.get(user=profile)
        
        # Check if user is admin
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            if not member.is_admin and group.creator != payment_profile:
                return Response({'error': 'Only admins can invite'}, status=status.HTTP_403_FORBIDDEN)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        
        invited_email = request.data.get('email')
        try:
            invited_user = CustomUser.objects.get(email=invited_email)
            invited_profile = Profile.objects.get(user=invited_user)
            invited_payment_profile = PaymentProfile.objects.get(user=invited_profile)
        except (CustomUser.DoesNotExist, Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create invitation
        invitation_link = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        
        invitation = GroupInvitation.objects.create(
            payment_group=group,
            invited_profile=invited_payment_profile,
            invited_by=payment_profile,
            invitation_link=invitation_link,
            expires_at=expires_at
        )
        
        return Response(GroupInvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def my_groups(self, request):
        """Get user's groups"""
        groups = self.get_queryset()
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get group members"""
        group = self.get_object()
        members = group.members.all()
        serializer = PaymentGroupMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def contributions_list(self, request, pk=None):
        """Get group contributions"""
        group = self.get_object()
        contributions = group.contributions.all().order_by('-contributed_at')
        serializer = ContributionSerializer(contributions, many=True)
        return Response(serializer.data)


class PaymentItemViewSet(ModelViewSet):
    queryset = PaymentItem.objects.all()
    serializer_class = PaymentItemSerializer
    permission_classes = [IsAuthenticated]

# Shop / Product Views
class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated] 
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Get recommended products"""
        # Simple Logic: Random 5 or specific tagged 'recommendation'
        products = Product.objects.filter(product_type='recommendation')[:10]
        if not products.exists():
            products = Product.objects.all()[:10]
        return Response(ProductSerializer(products, many=True).data)

# Piggy Bank / Group Target Views
class GroupTargetViewSet(ModelViewSet):
    queryset = GroupTarget.objects.all()
    serializer_class = GroupTargetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            payment_profile = PaymentProfile.objects.get(user=profile)
            return GroupTarget.objects.filter(payment_group__members__payment_profile=payment_profile)
        except:
            return GroupTarget.objects.none()

    @action(detail=True, methods=['post'])
    def contribute(self, request, pk=None):
        """Contribute to a piggy bank / target"""
        target = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check locking
        if target.locking_status == 'locked_time' and target.maturity_date and target.maturity_date > timezone.now():
            return Response({'error': f'Piggy bank is locked until {target.maturity_date}'}, status=status.HTTP_403_FORBIDDEN)
            
        if target.locking_status == 'locked_goal' and target.current_amount < target.target_amount:
             # Just a warning? Or prevent withdrawal? Normally deposit is fine, withdrawal is locked.
             pass
             
        # Add logic to process payment (deduct balance etc) -> Simplified for now
        target.current_amount += float(amount)
        if target.current_amount >= target.target_amount:
            target.achieved = True
            target.achieved_at = timezone.now()
            # Notify user logic here
            
        target.save()
        
        return Response({'status': 'Contribution successful', 'current_amount': target.current_amount})

class UserSubscriptionViewSet(ModelViewSet):
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            payment_profile = PaymentProfile.objects.get(user=profile)
            return UserSubscription.objects.filter(user=payment_profile)
        except:
            return UserSubscription.objects.none()
