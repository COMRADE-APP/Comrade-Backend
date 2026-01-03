from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction as db_transaction
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, GroupMembers,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription
)
from Payment.serializers import (
    PaymentProfileSerializer, PaymentItemSerializer, PaymentLogSerializer,
    PaymentGroupsSerializer, TransactionTokenSerializer,
    PaymentAuthorizationSerializer, PaymentVerificationSerializer,
    TransactionHistorySerializer, TransactionTrackerSerializer,
    GroupMembersSerializer, ContributionSerializer,
    StandingOrderSerializer, GroupInvitationSerializer, GroupTargetSerializer,
    PaymentGroupsCreateSerializer, CreateTransactionSerializer,
    ProductSerializer, UserSubscriptionSerializer
)
from Authentication.models import CustomUser


class PaymentProfileViewSet(ModelViewSet):
    queryset = PaymentProfile.objects.all()
    serializer_class = PaymentProfileSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current user's payment profile"""
        profile, created = PaymentProfile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get current user's balance"""
        profile, _ = PaymentProfile.objects.get_or_create(user=request.user)
        return Response({'balance': str(profile.comrade_balance)})


class TransactionViewSet(ModelViewSet):
    queryset = TransactionToken.objects.all()
    serializer_class = TransactionTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get transactions for current user"""
        return TransactionToken.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        ).select_related('sender', 'receiver').order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def create_transaction(self, request):
        """Create a new transaction"""
        serializer = CreateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        sender = request.user
        sender_profile, _ = PaymentProfile.objects.get_or_create(user=sender)
        
        # Get recipient
        receiver_id = serializer.validated_data['receiver_id']
        try:
            receiver = CustomUser.objects.get(id=receiver_id)
            receiver_profile, _ = PaymentProfile.objects.get_or_create(user=receiver)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Recipient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        amount = serializer.validated_data['amount']
        payment_method = serializer.validated_data['payment_method']
        
        # Check balance for internal transfers
        if payment_method == 'INTERNAL':
            if sender_profile.comrade_balance < amount:
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create transaction
        transaction = TransactionToken.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            payment_method=payment_method,
            transaction_type=serializer.validated_data['transaction_type'],
            description=serializer.validated_data.get('description', ''),
            metadata=serializer.validated_data.get('metadata', {}),
            status='pending'
        )
        
        # Process if using internal balance
        if payment_method == 'INTERNAL':
            sender_profile.comrade_balance -= amount
            sender_profile.total_sent += amount
            receiver_profile.comrade_balance += amount
            receiver_profile.total_received += amount
            
            sender_profile.save()
            receiver_profile.save()
            
            transaction.status = 'completed'
            transaction.save()
        
        return Response(TransactionTokenSerializer(transaction).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get transaction history"""
        transactions = self.get_queryset()
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(transactions, many=True)
        return Response(serializer.data)


class PaymentGroupsViewSet(ModelViewSet):
    queryset = PaymentGroups.objects.all()
    serializer_class = PaymentGroupsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get groups where user is admin or member"""
        return PaymentGroups.objects.filter(
            Q(admin=self.request.user) | Q(members__user=self.request.user)
        ).distinct().prefetch_related('members', 'contributions', 'targets')
    
    def create(self, request):
        """Create a payment group"""
        serializer = PaymentGroupsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        group = PaymentGroups.objects.create(
            admin=request.user,
            **serializer.validated_data
        )
        
        # Add creator as admin member
        GroupMembers.objects.create(
            group=group,
            user=request.user,
            role='ADMIN'
        )
        
        return Response(PaymentGroupsSerializer(group).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a payment group"""
        group = self.get_object()
        
        if GroupMembers.objects.filter(group=group, user=request.user).exists():
            return Response({'error': 'Already a member'}, status=status.HTTP_400_BAD_REQUEST)
        
        member = GroupMembers.objects.create(
            group=group,
            user=request.user
        )
        
        return Response(GroupMembersSerializer(member).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def contribute(self, request, pk=None):
        """Make a contribution to the group"""
        group = self.get_object()
        
        # Check membership
        try:
            member = GroupMembers.objects.get(group=group, user=request.user)
        except GroupMembers.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
        
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        amount = float(amount)
        payment_profile, _ = PaymentProfile.objects.get_or_create(user=request.user)
        
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
            group=group,
            member=request.user,
            amount=amount
        )
        
        return Response(ContributionSerializer(contribution).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def invite(self, request, pk=None):
        """Invite someone to the group"""
        group = self.get_object()
        
        # Check if user is admin
        try:
            member = GroupMembers.objects.get(group=group, user=request.user)
            if member.role != 'ADMIN' and group.admin != request.user:
                return Response({'error': 'Only admins can invite'}, status=status.HTTP_403_FORBIDDEN)
        except GroupMembers.DoesNotExist:
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        
        invitee_email = request.data.get('invitee_email')
        if not invitee_email:
            return Response({'error': 'Invitee email required'}, status=status.HTTP_400_BAD_REQUEST)
        
        expires_at = timezone.now() + timedelta(days=7)
        
        invitation = GroupInvitation.objects.create(
            group=group,
            inviter=request.user,
            invitee_email=invitee_email,
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
        serializer = GroupMembersSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def contributions_list(self, request, pk=None):
        """Get group contributions"""
        group = self.get_object()
        contributions = group.contributions.all().order_by('-contribution_date')
        serializer = ContributionSerializer(contributions, many=True)
        return Response(serializer.data)


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.filter(is_available=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Get recommended products for user"""
        # Basic recommendation - most popular
        products = Product.objects.filter(is_available=True).order_by('-created_at')[:10]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class UserSubscriptionViewSet(ModelViewSet):
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get current user's subscriptions"""
        return UserSubscription.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_subscription(self, request):
        """Get user's active subscription"""
        subscription, created = UserSubscription.objects.get_or_create(
            user=request.user,
            defaults={'subscription_type': 'BASIC', 'status': 'ACTIVE'}
        )
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel subscription"""
        subscription = self.get_object()
        if subscription.user != request.user:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        subscription.status = 'CANCELLED'
        subscription.auto_renew = False
        subscription.save()
        
        return Response(self.get_serializer(subscription).data)


class PaymentItemViewSet(ModelViewSet):
    queryset = PaymentItem.objects.all()
    serializer_class = PaymentItemSerializer
    permission_classes = [IsAuthenticated]


class GroupTargetViewSet(ModelViewSet):
    queryset = GroupTarget.objects.all()
    serializer_class = GroupTargetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get targets for user's groups"""
        user_groups = PaymentGroups.objects.filter(
            Q(admin=self.request.user) | Q(members__user=self.request.user)
        )
        return GroupTarget.objects.filter(group__in=user_groups).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def contribute(self, request, pk=None):
        """Contribute to a target"""
        target = self.get_object()
        
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        amount = float(amount)
        payment_profile, _ = PaymentProfile.objects.get_or_create(user=request.user)
        
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Deduct from user
        payment_profile.comrade_balance -= amount
        payment_profile.save()
        
        # Add to target
        target.current_amount += amount
        if target.current_amount >= target.target_amount:
            target.is_achieved = True
        target.save()
        
        # Also update group amount
        target.group.current_amount += amount
        target.group.save()
        
        return Response(self.get_serializer(target).data)
