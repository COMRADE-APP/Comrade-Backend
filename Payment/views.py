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
    Product, UserSubscription, IndividualShare, Partner, PartnerApplication,
    AgentApplication, SupplierApplication, ShopRegistration
)
from Payment.serializers import (
    PaymentProfileSerializer, PaymentItemSerializer, PaymentLogSerializer,
    PaymentGroupsSerializer, TransactionTokenSerializer,
    PaymentAuthorizationSerializer, PaymentVerificationSerializer,
    TransactionHistorySerializer, TransactionTrackerSerializer,
    PaymentGroupMemberSerializer, ContributionSerializer,
    StandingOrderSerializer, GroupInvitationSerializer, GroupTargetSerializer,
    PaymentGroupsCreateSerializer, CreateTransactionSerializer,
    ProductSerializer, UserSubscriptionSerializer, PartnerSerializer, PartnerApplicationSerializer, PartnerApplicationCreateSerializer,
    AgentApplicationSerializer, SupplierApplicationSerializer, ShopRegistrationSerializer
)
from Authentication.models import Profile, CustomUser


class PaymentProfileViewSet(ModelViewSet):
    queryset = PaymentProfile.objects.all()
    serializer_class = PaymentProfileSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get current user's payment profile"""
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        serializer = self.get_serializer(payment_profile)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def balance(self, request):
        """Get current user's balance"""
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
             return Response({'balance': 0.00})
             
        return Response({'balance': payment_profile.comrade_balance})


from Payment.utils import check_purchase_limit, increment_purchase_count, check_group_creation_limit, get_max_group_members, get_or_create_payment_profile

class TransactionViewSet(ModelViewSet):
    queryset = TransactionToken.objects.all()
    serializer_class = TransactionTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get transactions for current user"""
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return TransactionToken.objects.none()
            
        return TransactionToken.objects.filter(
            Q(payment_profile=payment_profile) | Q(recipient_profile=payment_profile)
        ).select_related('payment_profile', 'recipient_profile').order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def create_transaction(self, request):
        """Create a new transaction"""
        serializer = CreateTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        sender_payment_profile = get_or_create_payment_profile(user)
        if not sender_payment_profile:
            return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def deposit(self, request):
        """Deposit funds to Comrade Balance"""
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'bank_transfer')
        
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create transaction record
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_type='deposit',
            amount=amount,
            payment_option=payment_method,
            pay_from='external'
        )
        
        # Update balance
        payment_profile.comrade_balance += amount
        payment_profile.save()
        
        # Create history record
        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=transaction,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=amount,
            status='completed'
        )
        
        return Response({
            'status': 'success',
            'message': f'Successfully deposited ${amount:.2f}',
            'new_balance': float(payment_profile.comrade_balance),
            'transaction_id': str(transaction.transaction_code)
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def withdraw(self, request):
        """Withdraw funds from Comrade Balance"""
        amount = request.data.get('amount')
        account_number = request.data.get('account_number', '')
        payment_method = request.data.get('payment_method', 'bank_transfer')
        
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check balance
        if payment_profile.comrade_balance < amount:
            return Response({
                'error': 'Insufficient balance',
                'current_balance': float(payment_profile.comrade_balance),
                'requested_amount': amount
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create transaction record
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_type='withdrawal',
            amount=amount,
            payment_option=payment_method,
            pay_from='internal'
        )
        
        # Deduct balance
        payment_profile.comrade_balance -= amount
        payment_profile.save()
        
        # Create history record
        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=transaction,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=amount,
            status='completed'
        )
        
        return Response({
            'status': 'success',
            'message': f'Successfully withdrew ${amount:.2f}',
            'new_balance': float(payment_profile.comrade_balance),
            'transaction_id': str(transaction.transaction_code),
            'destination': account_number or 'Primary account'
        }, status=status.HTTP_201_CREATED)


    

class PaymentGroupsViewSet(ModelViewSet):
    queryset = PaymentGroups.objects.all()
    serializer_class = PaymentGroupsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return PaymentGroups.objects.none()
            
        return PaymentGroups.objects.filter(members__payment_profile=payment_profile).distinct()
            
    @db_transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new payment group"""
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             raise serializers.ValidationError("Could not create payment profile")
        
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
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check if user is admin
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            if not member.is_admin and group.creator != payment_profile:
                return Response({'error': 'Only admins can invite'}, status=status.HTTP_403_FORBIDDEN)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        
        invited_email = request.data.get('email')
        force_external = request.data.get('force_external', False)
        
        invited_payment_profile = None
        user_exists = False
        
        try:
            invited_user = CustomUser.objects.get(email=invited_email)
            invited_profile = Profile.objects.get(user=invited_user)
            invited_payment_profile = PaymentProfile.objects.get(user=invited_profile)
            user_exists = True
        except (CustomUser.DoesNotExist, Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            user_exists = False
        
        if not user_exists:
            if not force_external:
                 return Response({
                     'error': 'User not found',
                     'requires_confirmation': True,
                     'message': 'User does not exist. Do you want to send an invitation to their email address?'
                 }, status=status.HTTP_404_NOT_FOUND)
            
            # Create external invitation
            # Note: GroupInvitation now supports null invited_profile
        
        # Create invitation
        invitation_link = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(days=7)
        
        invitation = GroupInvitation.objects.create(
            payment_group=group,
            invited_profile=invited_payment_profile,
            invited_email=invited_email,
            invited_by=payment_profile,
            invitation_link=invitation_link,
            expires_at=expires_at
        )
        
        # Send Email
        from Payment.utils import send_group_invitation_email
        
        invite_url = f"http://localhost:3000/payments/groups/{group.id}/join?token={invitation_link}"
        inviter_name = f"{payment_profile.user.user.first_name} {payment_profile.user.user.last_name}"
        
        send_group_invitation_email(invited_email, group.name, inviter_name, invite_url, is_existing_user=user_exists)

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

class GroupInvitationViewSet(ModelViewSet):
    """ViewSet for handling group invitations"""
    queryset = GroupInvitation.objects.all()
    serializer_class = GroupInvitationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return GroupInvitation.objects.none()
            
        return GroupInvitation.objects.filter(
            invited_profile=payment_profile,
            status='pending',
            expires_at__gt=timezone.now()
        ).select_related('payment_group', 'invited_by')
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending invitations for current user"""
        invitations = self.get_queryset()
        serializer = self.get_serializer(invitations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def accept(self, request, pk=None):
        """Accept a group invitation"""
        invitation = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Verify invitation is for this user
        if invitation.invited_profile != payment_profile:
            return Response({'error': 'Invalid invitation'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if invitation is still valid
        if invitation.status != 'pending':
            return Response({'error': 'Invitation already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        if invitation.expires_at < timezone.now():
            invitation.status = 'expired'
            invitation.save()
            return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check group capacity
        group = invitation.payment_group
        if group.members.count() >= group.max_capacity:
            return Response({'error': 'Group is full'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add user to group
        PaymentGroupMember.objects.create(
            payment_group=group,
            payment_profile=payment_profile,
            is_admin=False
        )
        
        # Update invitation status
        invitation.status = 'accepted'
        invitation.save()
        
        return Response({
            'status': 'Invitation accepted',
            'group_id': str(group.id),
            'group_name': group.name
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a group invitation"""
        invitation = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Verify invitation is for this user
        if invitation.invited_profile != payment_profile:
            return Response({'error': 'Invalid invitation'}, status=status.HTTP_403_FORBIDDEN)
        
        # Update invitation status
        invitation.status = 'rejected'
        invitation.save()
        
        return Response({'status': 'Invitation rejected'})
    
    @action(detail=False, methods=['post'])
    def respond(self, request):
        """Respond to an invitation (accept or reject) by ID"""
        invitation_id = request.data.get('invitation_id')
        accept = request.data.get('accept', False)
        
        try:
            invitation = GroupInvitation.objects.get(id=invitation_id)
        except GroupInvitation.DoesNotExist:
            return Response({'error': 'Invitation not found'}, status=status.HTTP_404_NOT_FOUND)
        
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Verify invitation is for this user
        if invitation.invited_profile != payment_profile:
            return Response({'error': 'Invalid invitation'}, status=status.HTTP_403_FORBIDDEN)
        
        if accept:
            # Check if invitation is still valid
            if invitation.status != 'pending':
                return Response({'error': 'Invitation already processed'}, status=status.HTTP_400_BAD_REQUEST)
            
            if invitation.expires_at < timezone.now():
                invitation.status = 'expired'
                invitation.save()
                return Response({'error': 'Invitation has expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check group capacity
            group = invitation.payment_group
            if group.members.count() >= group.max_capacity:
                return Response({'error': 'Group is full'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Add user to group
            PaymentGroupMember.objects.create(
                payment_group=group,
                payment_profile=payment_profile,
                is_admin=False
            )
            
            invitation.status = 'accepted'
            invitation.save()
            
            return Response({
                'status': 'Invitation accepted',
                'group_id': str(group.id),
                'group_name': group.name
            })
        else:
            invitation.status = 'rejected'
            invitation.save()
            return Response({'status': 'Invitation rejected'})


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
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return GroupTarget.objects.none()
            
        # Get both individual piggy banks and group piggy banks
        return GroupTarget.objects.filter(
            Q(owner=payment_profile) |  # Individual piggy banks
            Q(payment_group__members__payment_profile=payment_profile)  # Group piggy banks
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             raise serializers.ValidationError("Could not create payment profile")
        
        # Check if individual or group piggy bank
        payment_group_id = self.request.data.get('payment_group')
        
        if payment_group_id:
            # Group piggy bank
            serializer.save()
        else:
            # Individual piggy bank
            serializer.save(owner=payment_profile)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def contribute(self, request, pk=None):
        """Contribute to a piggy bank / target"""
        target = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get payment profile
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check balance
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check locking for contributions (usually only withdrawals should be blocked)
        if target.locking_status in ['locked', 'locked_time', 'locked_goal']:
            # Allow contributions but notify about locked status
            pass
            
        # Deduct from user balance
        payment_profile.comrade_balance -= amount
        payment_profile.save()
        
        # Add to piggy bank
        target.current_amount += amount
        if target.current_amount >= target.target_amount:
            target.achieved = True
            target.achieved_at = timezone.now()
            
        target.save()
        
        return Response({
            'status': 'Contribution successful',
            'amount_contributed': amount,
            'current_amount': float(target.current_amount),
            'target_amount': float(target.target_amount),
            'achieved': target.achieved
        })
    
    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def withdraw(self, request, pk=None):
        """Withdraw from a piggy bank"""
        target = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check locking status
        if target.locking_status == 'locked':
            return Response({'error': 'This piggy bank is locked'}, status=status.HTTP_403_FORBIDDEN)
        
        if target.locking_status == 'locked_time':
            if target.maturity_date and target.maturity_date > timezone.now():
                return Response({
                    'error': f'Piggy bank is locked until {target.maturity_date.strftime("%Y-%m-%d")}'
                }, status=status.HTTP_403_FORBIDDEN)
        
        if target.locking_status == 'locked_goal':
            if target.current_amount < target.target_amount:
                return Response({'error': 'Piggy bank is locked until goal is reached'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check available amount
        if target.current_amount < amount:
            return Response({'error': 'Insufficient funds in piggy bank'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get payment profile
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Deduct from piggy bank
        target.current_amount -= amount
        target.save()
        
        # Add to user balance
        payment_profile.comrade_balance += amount
        payment_profile.save()
        
        return Response({
            'status': 'Withdrawal successful',
            'amount_withdrawn': amount,
            'remaining_amount': float(target.current_amount),
            'new_balance': float(payment_profile.comrade_balance)
        })
    
    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock a piggy bank"""
        target = self.get_object()
        lock_type = request.data.get('lock_type', 'locked')
        maturity_date = request.data.get('maturity_date')
        
        if lock_type == 'locked_time' and maturity_date:
            target.maturity_date = maturity_date
        
        target.locking_status = lock_type
        target.save()
        
        return Response({
            'status': 'Piggy bank locked successfully',
            'locking_status': target.locking_status,
            'maturity_date': target.maturity_date
        })
    
    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """Unlock a piggy bank"""
        target = self.get_object()
        
        # Check if it can be unlocked
        if target.locking_status == 'locked_time' and target.maturity_date:
            if target.maturity_date > timezone.now():
                return Response({
                    'error': f'Cannot unlock until {target.maturity_date.strftime("%Y-%m-%d")}'
                }, status=status.HTTP_403_FORBIDDEN)
        
        if target.locking_status == 'locked_goal':
            if target.current_amount < target.target_amount:
                return Response({'error': 'Cannot unlock until goal is reached'}, status=status.HTTP_403_FORBIDDEN)
        
        target.locking_status = 'unlocked'
        target.save()
        
        return Response({
            'status': 'Piggy bank unlocked successfully',
            'locking_status': target.locking_status
        })

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


# Partner Views
class PartnerViewSet(ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Show only approved partners by default"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Partner.objects.all()
        return Partner.objects.filter(status='approved', verified=True)
    
    @action(detail=False, methods=['get'])
    def my_partnership(self, request):
        """Get current user's partnership"""
        try:
            profile = Profile.objects.get(user=request.user)
            partner = Partner.objects.get(user=profile)
            serializer = self.get_serializer(partner)
            return Response(serializer.data)
        except Partner.DoesNotExist:
            return Response({'error': 'No partnership found'}, status=status.HTTP_404_NOT_FOUND)


class PartnerApplicationViewSet(ModelViewSet):
    queryset = PartnerApplication.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PartnerApplicationCreateSerializer
        return PartnerApplicationSerializer
    
    def get_queryset(self):
        """Users can only see their own applications, staff can see all"""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return PartnerApplication.objects.all()
        try:
            profile = Profile.objects.get(user=user)
            return PartnerApplication.objects.filter(applicant=profile)
        except:
            return PartnerApplication.objects.none()
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a partner application (admin only)"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        application = self.get_object()
        if application.status != 'pending':
            return Response({'error': 'Application already processed'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create Partner from application
        partner = Partner.objects.create(
            user=application.applicant,
            partner_type=application.partner_type,
            business_name=application.business_name,
            business_registration=application.business_registration,
            contact_email=application.contact_email,
            contact_phone=application.contact_phone,
            website=application.website,
            address=application.address,
            city=application.city,
            country=application.country,
            description=application.description,
            status='approved',
            verified=True,
            verified_at=timezone.now(),
        )
        
        application.status = 'approved'
        application.reviewed_by = Profile.objects.get(user=request.user)
        application.reviewed_at = timezone.now()
        application.partner = partner
        application.save()
        
        return Response({'message': 'Application approved', 'partner_id': partner.id})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a partner application (admin only)"""
        if not (request.user.is_staff or request.user.is_superuser):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        application = self.get_object()
        application.status = 'rejected'
        application.reviewed_by = Profile.objects.get(user=request.user)
        application.reviewed_at = timezone.now()
        application.review_notes = request.data.get('notes', '')
        application.save()
        
        return Response({'message': 'Application rejected'})
# Partner Registration Views
class PartnerViewSet(ModelViewSet):
    queryset = Partner.objects.all()
    serializer_class = PartnerSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def my_status(self, request):
        """Check if user is a partner"""
        try:
            profile = Profile.objects.get(user=request.user)
            partner = Partner.objects.get(user=profile)
            return Response(self.get_serializer(partner).data)
        except (Profile.DoesNotExist, Partner.DoesNotExist):
            return Response({'is_partner': False}, status=status.HTTP_404_NOT_FOUND)

class PartnerApplicationViewSet(ModelViewSet):
    queryset = PartnerApplication.objects.all()
    serializer_class = PartnerApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users see their own, admins see all
        user = self.request.user
        if user.is_staff:
            return PartnerApplication.objects.all().order_by('-created_at')
        try:
            profile = Profile.objects.get(user=user)
            return PartnerApplication.objects.filter(applicant=profile)
        except:
            return PartnerApplication.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PartnerApplicationCreateSerializer
        return PartnerApplicationSerializer

class AgentApplicationViewSet(ModelViewSet):
    """Manage Agent Applications"""
    queryset = AgentApplication.objects.all()
    serializer_class = AgentApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return AgentApplication.objects.all().order_by('-created_at')
        try:
            profile = Profile.objects.get(user=user)
            return AgentApplication.objects.filter(applicant=profile)
        except:
            return AgentApplication.objects.none()

class SupplierApplicationViewSet(ModelViewSet):
    """Manage Supplier Applications"""
    queryset = SupplierApplication.objects.all()
    serializer_class = SupplierApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return SupplierApplication.objects.all().order_by('-created_at')
        try:
            profile = Profile.objects.get(user=user)
            return SupplierApplication.objects.filter(applicant=profile)
        except:
            return SupplierApplication.objects.none()

class ShopRegistrationViewSet(ModelViewSet):
    """Manage Shop Registrations"""
    queryset = ShopRegistration.objects.all()
    serializer_class = ShopRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Admins see all, users see their own
        if user.is_staff:
             return ShopRegistration.objects.all()
        try:
            profile = Profile.objects.get(user=user)
            return ShopRegistration.objects.filter(owner=profile)
        except:
            return ShopRegistration.objects.none()


# ============================================================================
# MARKETPLACE VIEWSETS
# ============================================================================

from Payment.models import (
    Establishment, EstablishmentBranch, MenuItem, HotelRoom,
    Booking, ServiceOffering, ServiceTimeSlot, Order, OrderItem, Review
)
from Payment.serializers import (
    EstablishmentSerializer, EstablishmentListSerializer, EstablishmentBranchSerializer,
    MenuItemSerializer, HotelRoomSerializer, BookingSerializer,
    ServiceOfferingSerializer, ServiceTimeSlotSerializer,
    OrderSerializer, CreateOrderSerializer, OrderItemSerializer, ReviewSerializer
)


class EstablishmentViewSet(ModelViewSet):
    """CRUD for establishments (restaurants, hotels, supermarkets, etc.)"""
    queryset = Establishment.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EstablishmentListSerializer
        return EstablishmentSerializer
    
    def get_queryset(self):
        qs = Establishment.objects.filter(is_active=True)
        
        # Filter by type
        est_type = self.request.query_params.get('type')
        if est_type:
            qs = qs.filter(establishment_type=est_type)
        
        # Filter by city
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        return qs.order_by('-rating', '-review_count')
    
    @action(detail=False, methods=['get'])
    def my_establishments(self, request):
        """Get establishments owned by current user."""
        try:
            profile = Profile.objects.get(user=request.user)
            qs = Establishment.objects.filter(owner=profile)
            serializer = EstablishmentListSerializer(qs, many=True)
            return Response(serializer.data)
        except Profile.DoesNotExist:
            return Response([])
    
    @action(detail=True, methods=['get'])
    def menu(self, request, pk=None):
        """Get the menu/items for an establishment."""
        establishment = self.get_object()
        items = MenuItem.objects.filter(establishment=establishment, is_available=True)
        return Response(MenuItemSerializer(items, many=True).data)
    
    @action(detail=True, methods=['get'])
    def rooms(self, request, pk=None):
        """Get hotel rooms for an establishment."""
        establishment = self.get_object()
        rooms = HotelRoom.objects.filter(establishment=establishment, is_available=True)
        return Response(HotelRoomSerializer(rooms, many=True).data)
    
    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        """Get service offerings for an establishment."""
        establishment = self.get_object()
        services = ServiceOffering.objects.filter(establishment=establishment, is_active=True)
        return Response(ServiceOfferingSerializer(services, many=True).data)
    
    @action(detail=True, methods=['get'])
    def reviews_list(self, request, pk=None):
        """Get reviews for an establishment."""
        establishment = self.get_object()
        reviews = establishment.reviews.all()
        return Response(ReviewSerializer(reviews, many=True).data)


class MenuItemViewSet(ModelViewSet):
    """CRUD for menu items (owner-only for create/update/delete)."""
    queryset = MenuItem.objects.filter(is_available=True)
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = MenuItem.objects.all()
        establishment_id = self.request.query_params.get('establishment')
        if establishment_id:
            qs = qs.filter(establishment_id=establishment_id)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__icontains=category)
        return qs


class HotelRoomViewSet(ModelViewSet):
    """CRUD for hotel/event rooms."""
    queryset = HotelRoom.objects.all()
    serializer_class = HotelRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = HotelRoom.objects.all()
        establishment_id = self.request.query_params.get('establishment')
        if establishment_id:
            qs = qs.filter(establishment_id=establishment_id)
        room_type = self.request.query_params.get('room_type')
        if room_type:
            qs = qs.filter(room_type=room_type)
        return qs


class BookingViewSet(ModelViewSet):
    """Manage bookings (hotel stays, event rooms, restaurant reservations)."""
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            if user.is_staff:
                return Booking.objects.all().order_by('-created_at')
            return Booking.objects.filter(user=profile).order_by('-created_at')
        except:
            return Booking.objects.none()
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking (establishment owner or staff)."""
        booking = self.get_object()
        booking.status = 'confirmed'
        booking.save()
        return Response(BookingSerializer(booking).data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        booking = self.get_object()
        booking.status = 'cancelled'
        booking.save()
        return Response(BookingSerializer(booking).data)


class ServiceOfferingViewSet(ModelViewSet):
    """CRUD for service offerings."""
    queryset = ServiceOffering.objects.filter(is_active=True)
    serializer_class = ServiceOfferingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = ServiceOffering.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__icontains=category)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs
    
    @action(detail=True, methods=['get'])
    def available_slots(self, request, pk=None):
        """Get available time slots for a service."""
        from datetime import date
        service = self.get_object()
        slots = service.time_slots.filter(is_booked=False, date__gte=date.today())
        return Response(ServiceTimeSlotSerializer(slots, many=True).data)


class ServiceTimeSlotViewSet(ModelViewSet):
    """CRUD for service time slots."""
    queryset = ServiceTimeSlot.objects.all()
    serializer_class = ServiceTimeSlotSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = ServiceTimeSlot.objects.all()
        service_id = self.request.query_params.get('service')
        if service_id:
            qs = qs.filter(service_id=service_id)
        available = self.request.query_params.get('available')
        if available == 'true':
            from datetime import date
            qs = qs.filter(is_booked=False, date__gte=date.today())
        return qs
    
    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        """Book a time slot."""
        slot = self.get_object()
        if slot.is_booked:
            return Response({'error': 'Slot already booked'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        slot.is_booked = True
        slot.booked_by = profile
        slot.save()
        return Response(ServiceTimeSlotSerializer(slot).data)


class OrderViewSet(ModelViewSet):
    """Manage orders (purchases, food orders, bookings, appointments)."""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        try:
            profile = Profile.objects.get(user=user)
            if user.is_staff:
                return Order.objects.all()
            return Order.objects.filter(buyer=profile)
        except:
            return Order.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateOrderSerializer
        return OrderSerializer
    
    @db_transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a new order with items."""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            profile = Profile.objects.get(user=request.user)
            payment_profile = PaymentProfile.objects.get(user=profile)
        except (Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Determine establishment
        establishment = None
        if data.get('establishment_id'):
            try:
                establishment = Establishment.objects.get(id=data['establishment_id'])
            except Establishment.DoesNotExist:
                return Response({'error': 'Establishment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create order
        order = Order.objects.create(
            buyer=profile,
            establishment=establishment,
            order_type=data['order_type'],
            delivery_mode=data['delivery_mode'],
            payment_type=data.get('payment_type', 'individual'),
            delivery_address=data.get('delivery_address', ''),
            notes=data.get('notes', ''),
        )
        
        # Process items
        total = 0
        items_data = data.get('items', [])
        for item_data in items_data:
            product = None
            menu_item = None
            unit_price = 0
            
            if 'product_id' in item_data:
                try:
                    product = Product.objects.get(id=item_data['product_id'])
                    unit_price = float(product.price)
                except Product.DoesNotExist:
                    pass
            
            if 'menu_item_id' in item_data:
                try:
                    menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                    unit_price = float(menu_item.price)
                except MenuItem.DoesNotExist:
                    pass
            
            qty = int(item_data.get('quantity', 1))
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                menu_item=menu_item,
                quantity=qty,
                unit_price=unit_price
            )
            total += float(order_item.subtotal)
        
        # Handle service appointment
        if data.get('service_time_slot_id'):
            try:
                slot = ServiceTimeSlot.objects.get(id=data['service_time_slot_id'])
                if not slot.is_booked:
                    slot.is_booked = True
                    slot.booked_by = profile
                    slot.save()
                    order.service_time_slot = slot
                    total += float(slot.service.price)
            except ServiceTimeSlot.DoesNotExist:
                pass
        
        # Handle booking reference
        if data.get('booking_id'):
            try:
                booking = Booking.objects.get(id=data['booking_id'])
                order.booking = booking
                total += float(booking.total_price)
            except Booking.DoesNotExist:
                pass
        
        order.total_amount = total
        
        # Deduct from balance (individual purchase)
        if data.get('payment_type', 'individual') == 'individual':
            if payment_profile.comrade_balance < total:
                order.delete()
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
            payment_profile.comrade_balance -= total
            payment_profile.save()
        
        order.status = 'confirmed'
        order.save()
        
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order status (establishment owner or staff)."""
        order = self.get_object()
        new_status = request.data.get('status')
        valid = ['pending', 'confirmed', 'preparing', 'ready', 'out_for_delivery', 'delivered', 'completed', 'cancelled']
        if new_status not in valid:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = new_status
        order.save()
        return Response(OrderSerializer(order).data)
    
    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """Get current user's orders."""
        orders = self.get_queryset()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class ReviewViewSet(ModelViewSet):
    """CRUD for establishment reviews."""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = Review.objects.all()
        establishment_id = self.request.query_params.get('establishment')
        if establishment_id:
            qs = qs.filter(establishment_id=establishment_id)
        return qs
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        review = serializer.save(user=profile)
        
        # Update establishment rating
        establishment = review.establishment
        reviews = establishment.reviews.all()
        total_rating = sum(r.rating for r in reviews)
        count = reviews.count()
        establishment.rating = total_rating / count if count else 0
        establishment.review_count = count
        establishment.save()
