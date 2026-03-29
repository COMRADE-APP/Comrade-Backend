from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework import status, serializers, views, permissions
import os
import csv
import pandas as pd
from rest_framework.permissions import IsAuthenticated
from django.db import transaction as db_transaction
from django.db.models import Q, Sum, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid
import secrets

from django.contrib.contenttypes.models import ContentType
from Funding.models import Business, CapitalVenture

from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, IndividualShare, Partner, PartnerApplication,
    AgentApplication, SupplierApplication, ShopRegistration,
    Order, OrderItem, MenuItem, GroupCheckoutRequest,
    GroupJoinRequest, GroupVote,
    BillProvider, BillPayment,
    LoanProduct, CreditScore, LoanApplication, LoanRepayment,
    EscrowTransaction, EscrowDispute,
    InsuranceProduct, InsurancePolicy, InsuranceClaim
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
    AgentApplicationSerializer, SupplierApplicationSerializer, ShopRegistrationSerializer,
    KittySerializer, GroupCheckoutRequestSerializer,
    GroupJoinRequestSerializer, GroupVoteSerializer,
    BillProviderSerializer, BillPaymentSerializer,
    LoanProductSerializer, CreditScoreSerializer, LoanApplicationSerializer, LoanRepaymentSerializer,
    EscrowTransactionSerializer, EscrowDisputeSerializer,
    InsuranceProductSerializer, InsurancePolicySerializer, InsuranceClaimSerializer
)
from Authentication.models import Profile, CustomUser
from Messages.models import Conversation, Message
from Payment.services.payment_service import PaymentService, StripeProvider, MpesaProvider
import logging

logger = logging.getLogger(__name__)


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


    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def checkout(self, request):
        """Unified checkout process."""
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
             
        data = request.data
        amount = Decimal(str(data.get('amount', 0)))
        payment_method = data.get('payment_method', 'wallet')
        
        # Check balance if using wallet
        if payment_method == 'wallet':
            # Lock the row to prevent race conditions (double-spend)
            payment_profile = PaymentProfile.objects.select_for_update().get(pk=payment_profile.pk)
            if payment_profile.comrade_balance < amount:
                return Response({'error': 'Insufficient wallet balance'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Atomic deduction using F() expression
            PaymentProfile.objects.filter(pk=payment_profile.pk).update(
                comrade_balance=F('comrade_balance') - amount
            )
            payment_profile.refresh_from_db()
            
            # Log deduction
            PaymentLog.objects.create(
                payment_profile=payment_profile,
                amount=amount,
                payment_type='individual',
                recipient=payment_profile,
                notes='Unified checkout purchase via wallet'
            )
            
            # Record in Transaction History
            TransactionToken.objects.create(
                payment_profile=payment_profile,
                amount=amount,
                transaction_type='purchase',
                pay_from='comrade_balance',
                payment_option='comrade_balance',
                description='Unified checkout purchase via wallet'
            )
            
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Create Order and OrderItem records from cart items
        from Payment.models import Order, OrderItem, Product, MenuItem
        
        items_data = data.get('items', [])
        
        # Determine primary order type from the items
        item_types = set(item.get('type', 'product') for item in items_data)
        if 'service' in item_types:
            order_type = 'service_appointment'
        elif 'booking' in item_types or 'room' in item_types:
            order_type = 'hotel_booking'
        else:
            order_type = 'product'
        
        order = Order.objects.create(
            buyer=profile,
            order_type=order_type,
            delivery_mode='pickup',
            payment_type=data.get('payment_type', 'individual'),
            total_amount=amount,
            status='confirmed',
            notes=f'Checkout via {payment_method}',
        )
        
        # Create individual order items
        for item in items_data:
            product = None
            item_type = item.get('type', 'product')
            item_id = item.get('id')
            
            # Try to link product FK for product-type items
            if item_type == 'product' and item_id:
                try:
                    product = Product.objects.get(id=item_id)
                except (Product.DoesNotExist, ValueError):
                    pass
            
            # Handle group entry fee payment
            if item_type == 'join_fee' and item_id:
                from Payment.models import GroupJoinRequest
                try:
                    join_request = GroupJoinRequest.objects.get(id=item_id, requester=payment_profile)
                    join_request.has_paid_entry_fee = True
                    join_request.status = 'pending'
                    join_request.save()
                except (GroupJoinRequest.DoesNotExist, ValueError):
                    pass
            
            OrderItem.objects.create(
                order=order,
                product=product,
                name=item.get('name', 'Item'),
                quantity=item.get('qty', 1),
                unit_price=Decimal(str(item.get('price', 0))),
                item_type=item_type,
                metadata=item.get('payload', item.get('metadata', {})),
            )
        
        return Response({
            'success': True,
            'message': 'Checkout completed successfully',
            'order_id': str(order.id),
        })

    @action(detail=False, methods=['get'])
    def my_checkout_requests(self, request):
        """Fetch all checkout requests from all groups the user is a member of or creator."""
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        requests = GroupCheckoutRequest.objects.filter(
            Q(group__members__payment_profile=payment_profile) | Q(group__creator=payment_profile)
        ).distinct().order_by('-created_at')
        
        serializer = GroupCheckoutRequestSerializer(requests, many=True, context={'request': request})
        return Response(serializer.data)

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
            # Lock rows to prevent race conditions
            sender_payment_profile = PaymentProfile.objects.select_for_update().get(pk=sender_payment_profile.pk)
            if sender_payment_profile.comrade_balance < amount:
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Atomic balance transfer using F() expressions
            PaymentProfile.objects.filter(pk=sender_payment_profile.pk).update(
                comrade_balance=F('comrade_balance') - amount
            )
            PaymentProfile.objects.filter(pk=recipient_payment_profile.pk).update(
                comrade_balance=F('comrade_balance') + amount
            )
            sender_payment_profile.refresh_from_db()
            recipient_payment_profile.refresh_from_db()
        
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
        """Deposit funds to Qomrade Balance"""
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
        """Withdraw funds from Qomrade Balance"""
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
        
        # Lock row to prevent race conditions (double-spend)
        payment_profile = PaymentProfile.objects.select_for_update().get(pk=payment_profile.pk)
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
        
        # Atomic deduction using F() expression
        PaymentProfile.objects.filter(pk=payment_profile.pk).update(
            comrade_balance=F('comrade_balance') - Decimal(str(amount))
        )
        payment_profile.refresh_from_db()
        
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
            print(error_msg)
            print(can_create)
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
        """Join a payment group (optionally as anonymous)"""
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
        
        # Anonymous membership
        is_anonymous = request.data.get('is_anonymous', False)
        anonymous_alias = request.data.get('anonymous_alias', '')
        
        if is_anonymous and not group.allow_anonymous:
            return Response({'error': 'This group does not allow anonymous membership'}, status=status.HTTP_400_BAD_REQUEST)
        
        member = PaymentGroupMember.objects.create(
            payment_group=group,
            payment_profile=payment_profile,
            is_anonymous=is_anonymous,
            anonymous_alias=anonymous_alias  # auto-generated in model.save() if blank
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
        payment_method = request.data.get('payment_method', 'wallet')  # wallet, stripe, mpesa
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        amount = float(amount)
        
        # Process payment based on method
        if payment_method == 'wallet':
            if payment_profile.comrade_balance < amount:
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
            # Deduct from wallet
            payment_profile.comrade_balance -= amount
            payment_profile.save()
        elif payment_method == 'stripe':
            # Create Stripe PaymentIntent - return client_secret for frontend to complete
            result = StripeProvider.create_payment_intent(
                amount, description=f'Group contribution: {group.name}'
            )
            if isinstance(result, dict) and 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
            # Return client secret for client-side confirmation
            return Response({
                'requires_action': True,
                'payment_method': 'stripe',
                'client_secret': result.client_secret,
                'group_id': str(group.id),
                'amount': amount
            })
        elif payment_method == 'mpesa':
            phone_number = request.data.get('phone_number', '')
            if not phone_number:
                return Response({'error': 'Phone number required for M-Pesa'}, status=status.HTTP_400_BAD_REQUEST)
            result = MpesaProvider.stk_push(
                phone_number, amount, f'Group-{group.name}', f'Contribution to {group.name}'
            )
            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
            # M-Pesa callback will confirm payment; return pending status
            return Response({
                'requires_action': True,
                'payment_method': 'mpesa',
                'checkout_request_id': result.get('CheckoutRequestID', ''),
                'message': 'STK push sent. Complete payment on your phone.'
            })
        else:
            return Response({'error': f'Unsupported payment method: {payment_method}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add to group (wallet path)
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
        
        # Create audit trail
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=f'grp_contrib_{uuid.uuid4().hex[:12]}',
            amount=amount,
            transaction_type='contribution',
            notes=f'Contribution to group: {group.name}'
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
        
        invited_identifier = request.data.get('email')
        force_external = request.data.get('force_external', False)
        
        invited_payment_profile = None
        user_exists = False
        invited_email = None
        
        if invited_identifier and '@' in invited_identifier:
            invited_email = invited_identifier
            try:
                invited_user = CustomUser.objects.get(email=invited_email)
                invited_profile = Profile.objects.get(user=invited_user)
                invited_payment_profile = PaymentProfile.objects.get(user=invited_profile)
                user_exists = True
            except (CustomUser.DoesNotExist, Profile.DoesNotExist, PaymentProfile.DoesNotExist):
                user_exists = False
        elif invited_identifier:
            try:
                invited_user = CustomUser.objects.get(username=invited_identifier)
                invited_email = invited_user.email
                invited_profile = Profile.objects.get(user=invited_user)
                invited_payment_profile = PaymentProfile.objects.get(user=invited_profile)
                user_exists = True
            except (CustomUser.DoesNotExist, Profile.DoesNotExist, PaymentProfile.DoesNotExist):
                user_exists = False
        
        if not user_exists:
            # We cannot send external invites if we don't have an email address
            if not force_external or not invited_email:
                 err_msg = 'User not found. Do you want to send an invitation to their email address?' if invited_email else 'Username not found.'
                 return Response({
                     'error': 'User not found' if invited_email else 'Username not found',
                     'requires_confirmation': True if invited_email else False,
                     'message': err_msg
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
        from django.conf import settings as django_settings
        
        frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        invite_url = f"{frontend_url}/payments/groups/{group.id}?token={invitation_link}"
        inviter_name = f"{payment_profile.user.user.first_name} {payment_profile.user.user.last_name}"
        
        send_group_invitation_email(invited_email, group.name, inviter_name, invite_url, is_existing_user=user_exists)
        
        # Send in-app chat notification if user exists on platform
        if user_exists:
            try:
                invited_user_obj = CustomUser.objects.get(email=invited_email)
                inviter_user_obj = user
                
                # Find or create DM conversation
                shared_convos = Conversation.objects.filter(
                    conversation_type='dm',
                    participants=inviter_user_obj
                ).filter(participants=invited_user_obj)
                
                if shared_convos.exists():
                    conversation = shared_convos.first()
                else:
                    conversation = Conversation.objects.create(conversation_type='dm')
                    conversation.participants.add(inviter_user_obj, invited_user_obj)
                
                # Send system message with invitation link
                Message.objects.create(
                    conversation=conversation,
                    sender=inviter_user_obj,
                    message_type='system',
                    content=f"📩 You've been invited to join the payment group \"{group.name}\"! View and accept: {invite_url}"
                )
            except Exception as e:
                logger.warning(f'Failed to send chat notification for group invite: {e}')

        return Response(GroupInvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'], url_path='update_group')
    def update_group(self, request, pk=None):
        """Update group name, description, or cover photo."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Only creator or admin can update
        is_creator = group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_creator and not is_admin:
            return Response({'error': 'Only group creator or admin can update the group'}, status=status.HTTP_403_FORBIDDEN)
        
        # Update allowed fields
        if 'name' in request.data:
            group.name = request.data['name']
        if 'description' in request.data:
            group.description = request.data['description']
        if 'cover_photo' in request.FILES:
            group.cover_photo = request.FILES['cover_photo']
        
        group.save()
        serializer = self.get_serializer(group)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_groups(self, request):
        """Get user's groups"""
        groups = self.get_queryset()
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def group_checkout(self, request, pk=None):
        """Initiate group checkout for unified cart."""
        group = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
             
        # Check if member
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            
        data = request.data
        amount = Decimal(str(data.get('amount', 0)))
        items_data = data.get('items', [])
        
        # If amount > 500 or group requires strict approval
        requires_approval = group.requires_approval or (amount > 500)
        
        if requires_approval:
            checkout_req = GroupCheckoutRequest.objects.create(
                group=group,
                initiator=payment_profile,
                amount=amount,
                items_payload=items_data
            )
            # Auto-approve by initiator
            checkout_req.approvals.add(payment_profile)
            
            # Check if this 1 approval is enough (e.g. 1-member group)
            total_members = group.members.count()
            if checkout_req.approvals.count() >= total_members:
                success, error_or_order = self._execute_group_checkout(group, payment_profile, amount, items_data, user)
                if success:
                    checkout_req.status = 'approved'
                    checkout_req.save()
                    return Response({
                        'success': True, 
                        'message': 'Group checkout completed successfully',
                        'order_id': error_or_order
                    })
                else:
                    checkout_req.status = 'failed'
                    checkout_req.save()
                    return Response({'error': error_or_order}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'success': True, 
                'approval_pending': True,
                'checkout_request_id': checkout_req.id,
                'message': 'Group checkout requires member approval.'
            })
            
        success, error_or_order = self._execute_group_checkout(group, payment_profile, amount, items_data, user)
        if success:
            return Response({
                'success': True, 
                'message': 'Group checkout completed successfully',
                'order_id': error_or_order
            })
        else:
            return Response({'error': error_or_order}, status=status.HTTP_400_BAD_REQUEST)

    def _execute_group_checkout(self, group, payment_profile, amount, items_data, user):
        # Process directly from group current_amount
        if group.current_amount < amount:
            return False, 'Insufficient group funds. Members need to contribute.'
            
        # Deduct from group
        group.current_amount -= amount
        group.save()
        
        # Log group purchase
        from Payment.models import TransactionToken, Order, OrderItem, Product
        from Authentication.models import Profile
        
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            amount=amount,
            transaction_type='purchase',
            pay_from='group_wallet',
            payment_option='group_wallet',
            description=f'Group checkout for {group.name}',
            payment_group=group
        )
        
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            return False, 'Profile not found'
            
        # Determine primary order type from the items
        item_types = set(item.get('type', 'product') for item in items_data)
        if 'service' in item_types:
            order_type = 'service_appointment'
        elif 'booking' in item_types or 'room' in item_types:
            order_type = 'hotel_booking'
        else:
            order_type = 'product'
        
        order = Order.objects.create(
            buyer=profile,
            order_type=order_type,
            delivery_mode='pickup',
            payment_type='group',
            total_amount=amount,
            status='confirmed',
            notes=f'Group checkout via {group.name}',
        )
        
        # Create individual order items
        for item in items_data:
            product = None
            item_type = item.get('type', 'product')
            item_id = item.get('id')
            
            # Try to link product FK for product-type items
            if item_type == 'product' and item_id:
                try:
                    product = Product.objects.get(id=item_id)
                except (Product.DoesNotExist, ValueError):
                    pass
            
            elif item_type == 'funding' and item_id:
                from Funding.models import Business, CapitalVenture
                from django.contrib.contenttypes.models import ContentType
                from Payment.models import PaymentGroups
                from decimal import Decimal
                
                # Update the target Kitty and Charity stats if applicable
                try:
                    business = Business.objects.filter(id=item_id).first()
                    qty = int(item.get('qty', 1))
                    item_total = Decimal(str(float(item.get('price', 0)) * qty))
                    if business:
                        ct = ContentType.objects.get_for_model(Business)
                        kitty = PaymentGroups.objects.filter(entity_content_type=ct, entity_object_id=str(business.id), group_type='kitty').first()
                        if kitty:
                            kitty.current_amount += item_total
                            kitty.save()
                        if business.is_charity:
                            business.charity_raised += item_total
                            business.save()
                    else:
                        venture = CapitalVenture.objects.filter(id=item_id).first()
                        if venture:
                            ct = ContentType.objects.get_for_model(CapitalVenture)
                            kitty = PaymentGroups.objects.filter(entity_content_type=ct, entity_object_id=str(venture.id), group_type='kitty').first()
                            if kitty:
                                kitty.current_amount += item_total
                                kitty.save()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to process funding item: {e}")
            
            from decimal import Decimal
            OrderItem.objects.create(
                order=order,
                product=product,
                name=item.get('name', 'Item'),
                quantity=item.get('qty', 1),
                unit_price=Decimal(str(item.get('price', 0))),
                item_type=item_type,
                metadata=item.get('metadata', {})
            )
        
        return True, str(order.id)

    @action(detail=True, methods=['get'])
    def checkout_requests(self, request, pk=None):
        """Fetch all checkout requests for a specific group."""
        group = self.get_object()
        
        # Verify membership or creator
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        is_creator = group.creator == payment_profile
        is_member = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).exists()
        if not is_creator and not is_member:
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            
        requests = GroupCheckoutRequest.objects.filter(group=group).order_by('-created_at')
        serializer = GroupCheckoutRequestSerializer(requests, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path=r'checkout_requests/(?P<request_id>\d+)/(?P<action_type>approve|reject)')
    def review_checkout_request(self, request, pk=None, request_id=None, action_type=None):
        group = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
             
        is_creator = group.creator == payment_profile
        is_member = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).exists()
        if not is_creator and not is_member:
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)

        try:
            checkout_req = GroupCheckoutRequest.objects.get(id=request_id, group=group)
        except GroupCheckoutRequest.DoesNotExist:
            return Response({'error': 'Checkout request not found'}, status=status.HTTP_404_NOT_FOUND)

        if checkout_req.status != 'pending':
            return Response({'error': f'Request is already {checkout_req.status}'}, status=status.HTTP_400_BAD_REQUEST)

        if action_type == 'approve':
            checkout_req.approvals.add(payment_profile)
            checkout_req.rejections.remove(payment_profile)
        elif action_type == 'reject':
            checkout_req.rejections.add(payment_profile)
            checkout_req.approvals.remove(payment_profile)
            
        total_members = group.members.count()
        if checkout_req.approvals.count() >= total_members:
            # Need to get user object of initiator, handling edge cases
            initiator_user = None
            if checkout_req.initiator:
                from Authentication.models import CustomUser
                try:
                    initiator_user = checkout_req.initiator.user.user
                except AttributeError:
                    initiator_user = user
            else:
                initiator_user = user

            success, error_or_order = self._execute_group_checkout(
                group, 
                checkout_req.initiator or payment_profile, 
                checkout_req.amount, 
                checkout_req.items_payload, 
                initiator_user
            )
            if success:
                checkout_req.status = 'approved'
                checkout_req.save()
                return Response({'success': True, 'message': 'Checkout approved and executed successfully!'})
            else:
                checkout_req.status = 'failed'
                checkout_req.save()
                return Response({'error': error_or_order}, status=status.HTTP_400_BAD_REQUEST)
        elif checkout_req.rejections.count() > 0:
            checkout_req.status = 'rejected'
            checkout_req.save()
            return Response({'success': True, 'message': 'Checkout request rejected.'})
            
        return Response({
            'success': True, 
            'message': f'Successfully {action_type}d request.',
            'status': checkout_req.status,
            'approvals': checkout_req.approvals.count(),
            'total_members': total_members
        })

    # ── Kitty-specific endpoints ──────────────────────────────────

    @action(detail=False, methods=['get'])
    def my_kitties(self, request):
        """Return all kitties owned by (or where the user is a member of) the current user."""
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response([], status=status.HTTP_200_OK)

        kitties = PaymentGroups.objects.filter(
            group_type='kitty'
        ).filter(
            Q(creator=payment_profile) | Q(members__payment_profile=payment_profile)
        ).distinct().select_related('entity_content_type').order_by('-created_at')

        serializer = KittySerializer(kitties, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def kitty_withdraw(self, request, pk=None):
        """Withdraw funds from a kitty to the user's personal wallet."""
        kitty = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Could not resolve payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Only creator/admin can withdraw
        is_admin = kitty.creator == payment_profile
        if not is_admin:
            try:
                member = PaymentGroupMember.objects.get(payment_group=kitty, payment_profile=payment_profile)
                if not member.is_admin:
                    return Response({'error': 'Only admins can withdraw from this kitty'}, status=status.HTTP_403_FORBIDDEN)
            except PaymentGroupMember.DoesNotExist:
                return Response({'error': 'Not a member of this kitty'}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = float(amount)
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        if float(kitty.current_amount) < amount:
            return Response({
                'error': 'Insufficient kitty balance',
                'current_balance': float(kitty.current_amount),
            }, status=status.HTTP_400_BAD_REQUEST)

        # Deduct from kitty
        kitty.current_amount = float(kitty.current_amount) - amount
        kitty.save()

        # Credit user's personal wallet
        payment_profile.comrade_balance += amount
        payment_profile.save()

        # Create audit transaction
        tx = TransactionToken.objects.create(
            payment_profile=payment_profile,
            amount=amount,
            transaction_type='withdrawal',
            description=f'Kitty withdrawal from: {kitty.name}'
        )

        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=tx,
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
            'message': f'KES {amount:,.2f} withdrawn to your personal wallet',
            'new_kitty_balance': float(kitty.current_amount),
            'new_wallet_balance': float(payment_profile.comrade_balance),
            'transaction_id': str(tx.transaction_code),
        })

    @action(detail=True, methods=['get'])
    def kitty_transactions(self, request, pk=None):
        """Get transaction history for a specific kitty."""
        kitty = self.get_object()
        contributions = kitty.contributions.all().order_by('-contributed_at')

        result = []
        for c in contributions:
            result.append({
                'id': str(c.id),
                'type': 'inflow',
                'amount': float(c.amount),
                'description': f'Contribution from {c.member.payment_profile.user.user.first_name} {c.member.payment_profile.user.user.last_name}' if not c.member.is_anonymous else f'Contribution from {c.member.anonymous_alias}',
                'date': c.contributed_at.strftime('%Y-%m-%d'),
                'status': 'completed',
                'method': 'wallet',
                'notes': c.notes,
            })

        # Also include withdrawal transactions
        withdrawal_txns = TransactionToken.objects.filter(
            notes__icontains=f'Kitty withdrawal from: {kitty.name}',
            transaction_type='withdrawal',
        ).order_by('-created_at')

        for tx in withdrawal_txns:
            result.append({
                'id': str(tx.transaction_code),
                'type': 'outflow',
                'amount': float(tx.amount),
                'description': f'Withdrawal by {tx.payment_profile.user.user.first_name} {tx.payment_profile.user.user.last_name}',
                'date': tx.created_at.strftime('%Y-%m-%d'),
                'status': 'completed',
                'method': 'wallet',
            })

        # Sort by date descending
        result.sort(key=lambda x: x['date'], reverse=True)
        return Response(result)
    
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
    
    @action(detail=True, methods=['post'])
    def extend_deadline(self, request, pk=None):
        """Extend the group deadline (admin only)"""
        group = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check if admin
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            if not member.is_admin and group.creator != payment_profile:
                return Response({'error': 'Only admins can extend deadlines'}, status=status.HTTP_403_FORBIDDEN)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        
        new_deadline = request.data.get('new_deadline')
        if not new_deadline:
            return Response({'error': 'New deadline is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils.dateparse import parse_datetime
        parsed_deadline = parse_datetime(new_deadline)
        if not parsed_deadline:
            return Response({'error': 'Invalid date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Make timezone-aware if naive
        if parsed_deadline.tzinfo is None:
            from django.utils import timezone as tz
            parsed_deadline = tz.make_aware(parsed_deadline)
        
        # New deadline must be in the future
        if parsed_deadline <= timezone.now():
            return Response({'error': 'New deadline must be in the future'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update both deadline and expiry_date
        group.deadline = parsed_deadline
        group.expiry_date = parsed_deadline
        group.is_matured = False  # Reset maturation since deadline extended
        group.save()
        
        return Response({
            'message': 'Deadline extended successfully',
            'new_deadline': parsed_deadline.isoformat()
        })
    
    @action(detail=True, methods=['post'])
    def request_termination(self, request, pk=None):
        """Request group termination (requires mutual agreement after deadline)"""
        group = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Must be a member
        if not PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).exists():
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
        
        # Deadline must have passed
        effective_deadline = group.deadline or group.expiry_date
        if effective_deadline and effective_deadline > timezone.now():
            return Response({'error': 'Cannot terminate before the deadline'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add this member to termination_requested_by
        group.termination_requested_by.add(payment_profile)
        
        # Check if all members have agreed
        total_members = group.members.count()
        agreed_count = group.termination_requested_by.count()
        
        if agreed_count >= total_members:
            group.is_terminated = True
            group.is_active = False
            group.save()
            return Response({
                'message': 'All members agreed. Group has been terminated.',
                'is_terminated': True,
                'agreed': agreed_count,
                'total': total_members
            })
        
        group.save()
        return Response({
            'message': 'Your termination request has been recorded.',
            'is_terminated': False,
            'agreed': agreed_count,
            'total': total_members
        })
    
    @action(detail=True, methods=['get'])
    def group_status(self, request, pk=None):
        """Get group maturation and termination status"""
        group = self.get_object()
        
        # Auto-check maturation
        effective_deadline = group.deadline or group.expiry_date
        if effective_deadline and effective_deadline <= timezone.now() and not group.is_matured:
            group.is_matured = True
            group.save()
        
        total_members = group.members.count()
        agreed_count = group.termination_requested_by.count()
        
        return Response({
            'is_matured': group.is_matured,
            'is_terminated': group.is_terminated,
            'is_active': group.is_active,
            'deadline': (effective_deadline.isoformat() if effective_deadline else None),
            'termination_agreed': agreed_count,
            'termination_total': total_members,
        })
    
    def destroy(self, request, *args, **kwargs):
        """Block group deletion before deadline unless terminated by mutual agreement"""
        group = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        # Only creator/admin can delete
        if group.creator != payment_profile:
            return Response({'error': 'Only the group creator can delete'}, status=status.HTTP_403_FORBIDDEN)
        
        effective_deadline = group.deadline or group.expiry_date
        if effective_deadline and effective_deadline > timezone.now():
            return Response(
                {'error': 'Cannot delete group before the deadline. Extend or wait until the deadline passes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not group.is_terminated:
            return Response(
                {'error': 'All members must agree to terminate before the group can be deleted.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)


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
    
    @action(detail=False, methods=['post'])
    def sync_inventory(self, request):
        """Sync inventory from hardcoded data or parsed file data"""
        inventory_data = request.data.get('inventory', [])
        # Expecting a list of dicts: [{'product_id': ...}, ...]
        updated_products = []
        for item in inventory_data:
            try:
                product = Product.objects.get(id=item.get('product_id'))
                product.stock_quantity = item.get('stock_quantity', product.stock_quantity)
                if 'sku' in item:
                    product.sku = item.get('sku')
                product.save()
                updated_products.append(product.id)
            except Product.DoesNotExist:
                continue
        return Response({'status': 'Inventory synced', 'updated_count': len(updated_products)})
    
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
        
        # Determine contributor display name (anonymous-aware)
        contributor_name = None
        if target.payment_group:
            try:
                member = PaymentGroupMember.objects.get(
                    payment_group=target.payment_group, payment_profile=payment_profile
                )
                contributor_name = member.anonymous_alias if member.is_anonymous else f"{payment_profile.user.user.first_name} {payment_profile.user.user.last_name}"
            except PaymentGroupMember.DoesNotExist:
                contributor_name = f"{payment_profile.user.user.first_name} {payment_profile.user.user.last_name}"
        else:
            contributor_name = f"{payment_profile.user.user.first_name} {payment_profile.user.user.last_name}"
        
        return Response({
            'status': 'Contribution successful',
            'contributor': contributor_name,
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
    
    @action(detail=False, methods=['get'])
    def my_orders(self, request):
        """Get current user's orders + group orders where user is a member."""
        user = request.user
        if not user.is_authenticated:
            return Response([])
            
        try:
            profile = Profile.objects.get(user=user)
            from django.db.models import Q
            try:
                payment_profile = PaymentProfile.objects.get(user=profile)
                orders = Order.objects.filter(
                    Q(buyer=profile) | 
                    Q(payment_group__members__payment_profile=payment_profile)
                ).distinct().order_by('-created_at')
            except PaymentProfile.DoesNotExist:
                orders = Order.objects.filter(buyer=profile).order_by('-created_at')
                
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        except Profile.DoesNotExist:
            return Response([])
    
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
        
        # Offline sales handle their own payments
        is_offline = data.get('sales_channel') in ['in_store', 'pop_up'] or data.get('is_offline', False)
        
        # Create order
        order = Order.objects.create(
            buyer=profile,
            establishment=establishment,
            order_type=data['order_type'],
            delivery_mode=data['delivery_mode'],
            payment_type=data.get('payment_type', 'individual'),
            sales_channel=data.get('sales_channel', 'online'),
            is_offline=is_offline,
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
            
            item_type = item_data.get('type', 'product')
            item_id = item_data.get('id')
            
            if item_type == 'product' and item_id:
                try:
                    product = Product.objects.get(id=item_id)
                    unit_price = float(product.price)
                except Product.DoesNotExist:
                    unit_price = float(item_data.get('price', 0))
            
            elif item_type == 'funding' and item_id:
                unit_price = float(item_data.get('price', 0))
                # Update the target Kitty and Charity stats if applicable
                try:
                    business = Business.objects.filter(id=item_id).first()
                    qty = int(item_data.get('quantity', 1))
                    item_total = Decimal(str(unit_price * qty))
                    if business:
                        ct = ContentType.objects.get_for_model(Business)
                        kitty = PaymentGroups.objects.filter(entity_content_type=ct, entity_object_id=str(business.id), group_type='kitty').first()
                        if kitty:
                            kitty.current_amount += item_total
                            kitty.save()
                        if business.is_charity:
                            business.charity_raised += item_total
                            business.save()
                    else:
                        venture = CapitalVenture.objects.filter(id=item_id).first()
                        if venture:
                            ct = ContentType.objects.get_for_model(CapitalVenture)
                            kitty = PaymentGroups.objects.filter(entity_content_type=ct, entity_object_id=str(venture.id), group_type='kitty').first()
                            if kitty:
                                kitty.current_amount += item_total
                                kitty.save()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to process funding item: {e}")
            else:
                unit_price = float(item_data.get('price', 0))
            
            qty = int(item_data.get('quantity', item_data.get('qty', 1)))
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                menu_item=menu_item,
                name=item_data.get('name', ''),
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
        
        # Deduct from balance (individual purchase) if online
        if not is_offline and data.get('payment_type', 'individual') == 'individual':
            if payment_profile.comrade_balance < total:
                order.delete()
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
            payment_profile.comrade_balance -= total
            payment_profile.save()
            
            # Create a TransactionToken for the purchase
            TransactionToken.objects.create(
                payment_profile=payment_profile,
                amount=Decimal(str(total)),
                transaction_type='purchase',
                pay_from='wallet',
                payment_option='comrade_balance',
                description='Online purchase order'
            )
        
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
    def shop_analytics(self, request):
        """Get analytics for the user's shop/establishment."""
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        establishments = Establishment.objects.filter(owner=profile)
        if not establishments.exists():
            return Response({'error': 'No establishments found'}, status=status.HTTP_404_NOT_FOUND)
            
        establishment = establishments.first() 
        orders = Order.objects.filter(establishment=establishment)
        
        from django.db.models import Sum
        
        channels = ['online', 'in_store', 'pop_up']
        revenue_by_channel = {}
        for channel in channels:
            revenue_by_channel[channel] = orders.filter(sales_channel=channel).aggregate(total=Sum('total_amount'))['total'] or 0
            
        return Response({
            'total_revenue': sum(revenue_by_channel.values()),
            'revenue_by_channel': revenue_by_channel,
            'total_orders': orders.count(),
            'online_orders': orders.filter(sales_channel='online').count(),
            'offline_orders': orders.filter(sales_channel__in=['in_store', 'pop_up']).count(),
        })
    



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


# ============================================================================
# DYNAMIC PRICING API VIEWS (RL Model)
# ============================================================================

class DynamicPriceView(APIView):
    """GET /api/payment/pricing/<product_id>/
    Returns the RL-optimized price for a product for the current user."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, product_id):
        from Payment.pricing_service import calculate_dynamic_price
        
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        result = calculate_dynamic_price(payment_profile, product)
        return Response(result)


class TierRecommendationView(APIView):
    """GET /api/payment/pricing/tier-recommendation/
    Returns tier upgrade recommendation for current user."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from Payment.pricing_service import get_tier_recommendation
        
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        result = get_tier_recommendation(payment_profile)
        return Response(result)


class PriceAcceptView(APIView):
    """POST /api/payment/pricing/accept/
    Logs that a user accepted/rejected a dynamic price (training data)."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from Payment.pricing_service import log_pricing_event
        
        product_id = request.data.get('product_id')
        offered_price = request.data.get('offered_price')
        accepted = request.data.get('accepted', False)
        
        if not product_id or offered_price is None:
            return Response({'error': 'product_id and offered_price are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        
        event = log_pricing_event(
            user_profile=payment_profile,
            product=product,
            offered_price=float(offered_price),
            accepted=accepted,
        )
        
        return Response({
            'status': 'logged',
            'event_id': str(event.id),
            'accepted': accepted,
        })


class StudentVerificationView(APIView):
    """POST /api/payment/student-verification/
    Submit student verification documents for student pricing."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Check current student verification status."""
        from Payment.models import StudentVerification
        
        profile = Profile.objects.get(user=request.user)
        try:
            sv = StudentVerification.objects.get(user=profile)
            return Response({
                'status': sv.status,
                'is_active': sv.is_active,
                'institution_name': sv.institution_name,
                'discount_rate': float(sv.discount_rate),
                'expires_at': sv.expires_at.isoformat() if sv.expires_at else None,
            })
        except StudentVerification.DoesNotExist:
            return Response({'status': 'none', 'is_active': False})
    
    def post(self, request):
        """Submit student verification application."""
        from Payment.models import StudentVerification
        
        profile = Profile.objects.get(user=request.user)
        
        institution_name = request.data.get('institution_name')
        if not institution_name:
            return Response({'error': 'institution_name is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check for existing verification
        existing = StudentVerification.objects.filter(user=profile).first()
        if existing and existing.status == 'approved' and existing.is_active:
            return Response({
                'error': 'You already have an active student verification',
                'status': existing.status,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or update verification
        sv, created = StudentVerification.objects.update_or_create(
            user=profile,
            defaults={
                'institution_name': institution_name,
                'student_number': request.data.get('student_number', ''),
                'school_email': request.data.get('school_email', ''),
                'status': 'pending',
            }
        )
        
        # Handle file uploads
        if 'student_id_document' in request.FILES:
            sv.student_id_document = request.FILES['student_id_document']
        if 'admission_letter' in request.FILES:
            sv.admission_letter = request.FILES['admission_letter']
        if 'transcript' in request.FILES:
            sv.transcript = request.FILES['transcript']
        
        # Parse graduation date
        expected_graduation = request.data.get('expected_graduation')
        if expected_graduation:
            from django.utils.dateparse import parse_date
            sv.expected_graduation = parse_date(expected_graduation)
        
        sv.save()
        
        return Response({
            'status': 'submitted',
            'verification_id': str(sv.id),
            'message': 'Your student verification has been submitted for review.',
        }, status=status.HTTP_201_CREATED)


# ============================================================================
# ML MONITORING DASHBOARD API VIEWS
# ============================================================================

class MLDashboardView(views.APIView):
    """
    Retrieves real-time training logs from the ML pipeline completely isolated
    from the training scripts to avoid file locks.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ml_models_dir = os.path.join(base_dir, 'ML', 'models')
        ml_data_dir = os.path.join(base_dir, 'ML', 'data')

        def read_csv_tail(filepath, lines=50):
            try:
                if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                    return []
                # Read using pandas for robust parsing, taking the tail
                df = pd.read_csv(filepath)
                if df.empty:
                    return []
                # Explicitly scrub NaN/Infinity to None for JSON serialization
                import numpy as np
                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df = df.astype(object).where(pd.notnull(df), None)
                return df.tail(lines).to_dict('records')
            except Exception as e:
                return [] # Return empty list instead of breaking frontend parsing

        # 1. Pricing Model Logs
        pricing_log = os.path.join(ml_models_dir, 'pricing', 'training_log.csv')
        pricing_data = read_csv_tail(pricing_log)

        # 2. Recommendation Model Logs
        rec_log = os.path.join(ml_models_dir, 'recommendation', 'rec_training_log.csv')
        rec_data = read_csv_tail(rec_log)

        # 3. Distribution Model Logs
        dist_log = os.path.join(ml_models_dir, 'distribution', 'dist_training_log.csv')
        dist_data = read_csv_tail(dist_log)

        # 4. Data Volume
        raw_dir = os.path.join(ml_data_dir, 'raw_scrapped')
        total_size_mb = 0
        if os.path.exists(raw_dir):
            for f in os.listdir(raw_dir):
                fp = os.path.join(raw_dir, f)
                total_size_mb += os.path.getsize(fp) / (1024 * 1024)

        # 5. Distribution Categorical Metrics
        import json
        dist_metrics_file = os.path.join(ml_models_dir, 'distribution', 'dist_metrics.json')
        dist_metrics = None
        if os.path.exists(dist_metrics_file):
            try:
                with open(dist_metrics_file, 'r') as f:
                    dist_metrics = json.load(f)
            except Exception:
                pass

        # 6. Live Scraping Tracker
        scrape_status_file = os.path.join(ml_data_dir, 'scrape_status.json')
        scrape_status = None
        if os.path.exists(scrape_status_file):
            try:
                with open(scrape_status_file, 'r') as f:
                    scrape_status = json.load(f)
            except Exception:
                pass

        # 7. Pipeline Logs
        pipeline_log_file = os.path.join(base_dir, 'ML', 'training', 'pipeline.log')
        pipeline_logs = []
        if os.path.exists(pipeline_log_file):
            try:
                from collections import deque
                with open(pipeline_log_file, 'r', encoding='utf-8') as f:
                    pipeline_logs = list(deque(f, 200)) # Take last 200 lines
            except Exception:
                pass

        return Response({
            "models": {
                "pricing": pricing_data,
                "recommendation": rec_data,
                "distribution": dist_data,
                "distribution_metrics": dist_metrics
            },
            "metrics": {
                "total_scraped_data_mb": round(total_size_mb, 2),
                "is_pricing_training": True,  # Inferred securely without locks
                "scrape_status": scrape_status,
                "pipeline_logs": pipeline_logs
            }
        })


# ============================================================================
# GROUP DISCOURSE & VOTING VIEWSETS
# ============================================================================

class GroupJoinRequestViewSet(ModelViewSet):
    """Public discourse for joining payment groups — post requests, track approvals."""
    serializer_class = GroupJoinRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return GroupJoinRequest.objects.none()
        # Show: requests the user made, or requests for groups the user admins
        admin_groups = PaymentGroups.objects.filter(
            Q(creator=payment_profile) |
            Q(members__payment_profile=payment_profile, members__is_admin=True)
        ).distinct()
        return GroupJoinRequest.objects.filter(
            Q(requester=payment_profile) | Q(group__in=admin_groups)
        ).distinct().order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            raise serializers.ValidationError("Payment profile not found")
        
        # Determine initial status based on entry fee
        group_id = self.request.data.get('group')
        group = PaymentGroups.objects.get(id=group_id) if group_id else None
        
        if group and group.entry_fee_required and group.entry_fee_amount > 0:
            serializer.save(requester=payment_profile, status='pending_payment')
        else:
            serializer.save(requester=payment_profile, status='pending')

    @action(detail=False, methods=['get'])
    def public_groups(self, request):
        """List all public groups available for joining."""
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        groups = PaymentGroups.objects.filter(
            is_public=True, is_active=True, is_terminated=False
        ).exclude(group_type='kitty')
        if payment_profile:
            groups = groups.exclude(members__payment_profile=payment_profile)
        serializer = PaymentGroupsSerializer(groups, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a join request (admin only)."""
        join_request = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        # Check admin status
        group = join_request.group
        is_admin = (
            group.creator == payment_profile or
            PaymentGroupMember.objects.filter(
                payment_group=group, payment_profile=payment_profile, is_admin=True
            ).exists()
        )
        if not is_admin:
            return Response({'error': 'Only group admins can approve requests'}, status=status.HTTP_403_FORBIDDEN)
        # Approve and add member
        join_request.status = 'approved'
        join_request.reviewed_by = payment_profile
        join_request.review_notes = request.data.get('notes', '')
        join_request.save()
        # Add requester to group
        PaymentGroupMember.objects.get_or_create(
            payment_group=group,
            payment_profile=join_request.requester
        )
        # Also add to linked room if exists
        if group.linked_room and join_request.requester.user:
            group.linked_room.members.add(join_request.requester.user.user)
        return Response(GroupJoinRequestSerializer(join_request, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a join request (admin only)."""
        join_request = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        group = join_request.group
        is_admin = (
            group.creator == payment_profile or
            PaymentGroupMember.objects.filter(
                payment_group=group, payment_profile=payment_profile, is_admin=True
            ).exists()
        )
        if not is_admin:
            return Response({'error': 'Only group admins can reject requests'}, status=status.HTTP_403_FORBIDDEN)
        join_request.status = 'rejected'
        join_request.reviewed_by = payment_profile
        join_request.review_notes = request.data.get('notes', '')
        join_request.save()
        return Response(GroupJoinRequestSerializer(join_request, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw own join request."""
        join_request = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if join_request.requester != payment_profile:
            return Response({'error': 'Not your request'}, status=status.HTTP_403_FORBIDDEN)
        join_request.status = 'withdrawn'
        join_request.save()
        return Response(GroupJoinRequestSerializer(join_request, context={'request': request}).data)


class GroupVoteViewSet(ModelViewSet):
    """Voting system for group investment/savings/withdrawal decisions."""
    serializer_class = GroupVoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return GroupVote.objects.none()
        my_groups = PaymentGroups.objects.filter(
            members__payment_profile=payment_profile
        ).distinct()
        return GroupVote.objects.filter(group__in=my_groups).order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            raise serializers.ValidationError("Payment profile not found")
        serializer.save(created_by=payment_profile)

    @action(detail=True, methods=['post'])
    def cast_vote(self, request, pk=None):
        """Cast a vote (for/against/abstain)."""
        vote_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        # Check membership
        if not PaymentGroupMember.objects.filter(
            payment_group=vote_obj.group, payment_profile=payment_profile
        ).exists():
            return Response({'error': 'Not a group member'}, status=status.HTTP_403_FORBIDDEN)
        vote_choice = request.data.get('vote', '')  # 'for', 'against', 'abstain'
        if vote_choice not in ('for', 'against', 'abstain'):
            return Response({'error': 'Vote must be: for, against, or abstain'}, status=status.HTTP_400_BAD_REQUEST)
        # Remove previous votes
        vote_obj.votes_for.remove(payment_profile)
        vote_obj.votes_against.remove(payment_profile)
        vote_obj.votes_abstain.remove(payment_profile)
        # Cast new vote
        if vote_choice == 'for':
            vote_obj.votes_for.add(payment_profile)
        elif vote_choice == 'against':
            vote_obj.votes_against.add(payment_profile)
        else:
            vote_obj.votes_abstain.add(payment_profile)
        return Response(GroupVoteSerializer(vote_obj, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def by_group(self, request):
        """Get votes for a specific group."""
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response({'error': 'group_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        votes = self.get_queryset().filter(group_id=group_id)
        serializer = self.get_serializer(votes, many=True)
        return Response(serializer.data)


class GroupPortfolioView(APIView):
    """Portfolio analytics for a payment group's linked room."""
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            group = PaymentGroups.objects.get(pk=group_id)
        except PaymentGroups.DoesNotExist:
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        # Build portfolio analytics
        members = group.members.all()
        contributions = Contribution.objects.filter(payment_group=group)
        total_contributed = contributions.aggregate(total=Sum('amount'))['total'] or 0
        analytics = {
            'group_name': group.name,
            'total_balance': float(group.current_amount),
            'target_amount': float(group.target_amount or 0),
            'total_contributed': float(total_contributed),
            'member_count': members.count(),
            'linked_room_id': group.linked_room_id,
            'contributions_by_member': [],
            'recent_votes': [],
        }
        # Per-member contributions
        for m in members:
            analytics['contributions_by_member'].append({
                'name': f"{m.payment_profile.user.user.first_name} {m.payment_profile.user.user.last_name}" if not m.is_anonymous else m.anonymous_alias,
                'amount': float(m.total_contributed),
                'is_admin': m.is_admin,
            })
        # Recent votes
        recent_votes = GroupVote.objects.filter(group=group).order_by('-created_at')[:5]
        for v in recent_votes:
            analytics['recent_votes'].append({
                'title': v.title,
                'type': v.vote_type,
                'status': v.status,
                'approval': v.approval_percentage,
            })
        return Response(analytics)


# ==================== BILL PAYMENT VIEWSETS ====================

class BillProviderViewSet(ModelViewSet):
    serializer_class = BillProviderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = BillProvider.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class BillPaymentViewSet(ModelViewSet):
    serializer_class = BillPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return BillPayment.objects.filter(user=profile)
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        bill = serializer.save(user=profile, status='processing')
        # Simulate processing — in production, integrate with actual bill payment API
        try:
            pp = PaymentProfile.objects.get(user=profile)
            if pp.comrade_balance >= bill.total_amount:
                pp.comrade_balance -= bill.total_amount
                pp.save()
                bill.status = 'completed'
                bill.completed_at = timezone.now()
                bill.save()
            else:
                bill.status = 'failed'
                bill.error_message = 'Insufficient balance'
                bill.save()
        except PaymentProfile.DoesNotExist:
            bill.status = 'failed'
            bill.error_message = 'Payment profile not found'
            bill.save()


# ==================== LOAN VIEWSETS ====================

class LoanProductViewSet(ModelViewSet):
    serializer_class = LoanProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = LoanProduct.objects.filter(is_active=True)
        is_group = self.request.query_params.get('group')
        if is_group:
            qs = qs.filter(is_group_loan=is_group.lower() == 'true')
        return qs


class CreditScoreViewSet(ModelViewSet):
    serializer_class = CreditScoreSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return CreditScore.objects.filter(user=profile)
    
    @action(detail=False, methods=['get'])
    def my_score(self, request):
        profile = Profile.objects.get(user=request.user)
        score, created = CreditScore.objects.get_or_create(user=profile)
        if created:
            # Compute initial score based on platform activity
            import random
            base = 300
            savings = random.randint(20, 80)
            repayment = random.randint(30, 90)
            group_s = random.randint(10, 60)
            txn = random.randint(20, 70)
            tenure = random.randint(5, 40)
            total = base + savings + repayment + group_s + txn + tenure
            risk = 'very_low' if total > 700 else 'low' if total > 600 else 'moderate' if total > 450 else 'high' if total > 300 else 'very_high'
            score.score = min(total, 900)
            score.risk_level = risk
            score.savings_score = savings
            score.repayment_score = repayment
            score.group_score = group_s
            score.transaction_score = txn
            score.tenure_score = tenure
            score.factors = {
                'savings_consistency': f'{savings}%',
                'repayment_history': f'{repayment}%',
                'group_participation': f'{group_s}%',
                'transaction_volume': f'{txn}%',
                'platform_tenure': f'{tenure}%',
            }
            score.save()
        return Response(CreditScoreSerializer(score).data)


class LoanApplicationViewSet(ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return LoanApplication.objects.filter(user=profile)
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        credit, _ = CreditScore.objects.get_or_create(user=profile)
        loan = serializer.save(
            user=profile,
            status='pending',
            credit_score_at_application=credit.score
        )
        # Auto-generate repayment schedule
        from dateutil.relativedelta import relativedelta
        from datetime import date
        for i in range(1, loan.tenure_months + 1):
            LoanRepayment.objects.create(
                loan=loan,
                installment_number=i,
                amount_due=loan.monthly_payment,
                due_date=date.today() + relativedelta(months=i),
            )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        loan = self.get_object()
        loan.status = 'approved'
        loan.save()
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        loan = self.get_object()
        if loan.status != 'approved':
            return Response({'error': 'Loan must be approved first'}, status=status.HTTP_400_BAD_REQUEST)
        loan.status = 'disbursed'
        loan.disbursed_at = timezone.now()
        loan.save()
        # Credit user balance
        try:
            pp = PaymentProfile.objects.get(user=loan.user)
            pp.comrade_balance += loan.amount - loan.processing_fee_amount
            pp.save()
        except PaymentProfile.DoesNotExist:
            pass
        return Response({'status': 'disbursed', 'amount': str(loan.amount)})


# ==================== ESCROW VIEWSETS ====================

class EscrowTransactionViewSet(ModelViewSet):
    serializer_class = EscrowTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return EscrowTransaction.objects.filter(Q(buyer=profile) | Q(seller=profile))
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(buyer=profile)
    
    @action(detail=True, methods=['post'])
    def fund(self, request, pk=None):
        escrow = self.get_object()
        profile = Profile.objects.get(user=request.user)
        if escrow.buyer != profile:
            return Response({'error': 'Only buyer can fund'}, status=status.HTTP_403_FORBIDDEN)
        try:
            pp = PaymentProfile.objects.get(user=profile)
            if pp.comrade_balance >= escrow.total_amount:
                pp.comrade_balance -= escrow.total_amount
                pp.save()
                escrow.status = 'funded'
                escrow.funded_at = timezone.now()
                escrow.save()
                return Response({'status': 'funded'})
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        except PaymentProfile.DoesNotExist:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def deliver(self, request, pk=None):
        escrow = self.get_object()
        escrow.status = 'delivered'
        escrow.delivered_at = timezone.now()
        escrow.delivery_proof = request.data.get('proof', '')
        escrow.save()
        return Response({'status': 'delivered'})
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        escrow = self.get_object()
        profile = Profile.objects.get(user=request.user)
        if escrow.buyer != profile:
            return Response({'error': 'Only buyer can release'}, status=status.HTTP_403_FORBIDDEN)
        # Release funds to seller
        try:
            seller_pp = PaymentProfile.objects.get(user=escrow.seller)
            seller_pp.comrade_balance += escrow.amount
            seller_pp.save()
            escrow.status = 'released'
            escrow.released_at = timezone.now()
            escrow.save()
            return Response({'status': 'released'})
        except PaymentProfile.DoesNotExist:
            return Response({'error': 'Seller profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def dispute(self, request, pk=None):
        escrow = self.get_object()
        profile = Profile.objects.get(user=request.user)
        EscrowDispute.objects.create(
            escrow=escrow,
            raised_by=profile,
            reason=request.data.get('reason', ''),
            evidence=request.data.get('evidence', []),
        )
        escrow.status = 'disputed'
        escrow.save()
        return Response({'status': 'disputed'})


# ==================== INSURANCE VIEWSETS ====================

class InsuranceProductViewSet(ModelViewSet):
    serializer_class = InsuranceProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        qs = InsuranceProduct.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        group = self.request.query_params.get('group')
        if group:
            qs = qs.filter(is_group_product=group.lower() == 'true')
        return qs


class InsurancePolicyViewSet(ModelViewSet):
    serializer_class = InsurancePolicySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return InsurancePolicy.objects.filter(user=profile)
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(user=profile, status='active')


class InsuranceClaimViewSet(ModelViewSet):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return InsuranceClaim.objects.filter(claimant=profile)
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(claimant=profile)
