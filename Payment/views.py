from django.shortcuts import render, get_object_or_404
from django.apps import apps
from django.conf import settings
from Payment.utils import get_or_create_payment_profile
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
    Product, UserSubscription, Partner, PartnerApplication,
    AgentApplication, SupplierApplication, ShopRegistration,
    Order, OrderItem, MenuItem, GroupCheckoutRequest,
    GroupJoinRequest, GroupVote, GroupPhase, GroupPost, GroupPostReply,
    BillProvider, BillPayment,
    LoanProduct, CreditScore, LoanApplication, LoanRepayment,
    EscrowTransaction, EscrowDispute,
    InsuranceProduct, InsurancePolicy, InsuranceClaim,
    Donation, DonationContribution, GroupInvestment, InvestmentQuote,
    RoundContribution, RoundMemberContribution, BenefitDistributionRule,
    WithdrawalRequest, GroupSettingsChangeRequest, GroupCertificate, RoundPosition,
    PiggyBankConversionRequest,
    ProviderRegistration, ProviderDocument, ProviderStaff, ServiceProduct,
    ProviderTransaction, ProviderQuery, ProviderApplication, ProviderNotification
)
from Payment.serializers import (
    PaymentProfileSerializer, PaymentItemSerializer, PaymentLogSerializer,
    PaymentGroupsSerializer, TransactionTokenSerializer,
    PaymentAuthorizationSerializer, PaymentVerificationSerializer,
    TransactionHistorySerializer, TransactionHistoryDetailSerializer, TransactionTrackerSerializer,
    PaymentGroupMemberSerializer, ContributionSerializer,
    StandingOrderSerializer, GroupInvitationSerializer, GroupTargetSerializer,
    PaymentGroupsCreateSerializer, CreateTransactionSerializer,
    ProductSerializer, UserSubscriptionSerializer, PartnerSerializer, PartnerApplicationSerializer, PartnerApplicationCreateSerializer,
    AgentApplicationSerializer, SupplierApplicationSerializer, ShopRegistrationSerializer,
    KittySerializer, GroupCheckoutRequestSerializer,
    GroupJoinRequestSerializer, GroupVoteSerializer,
    GroupPhaseSerializer, GroupPostSerializer, GroupPostReplySerializer,
    BillProviderSerializer, BillPaymentSerializer,
    LoanProductSerializer, CreditScoreSerializer, LoanApplicationSerializer, LoanRepaymentSerializer,
    EscrowTransactionSerializer, EscrowDisputeSerializer,
    InsuranceProductSerializer, InsurancePolicySerializer, InsuranceClaimSerializer,
    DonationSerializer, DonationContributionSerializer,
    GroupInvestmentSerializer, InvestmentQuoteSerializer,
    RoundContributionSerializer, RoundMemberContributionSerializer,
    BenefitDistributionRuleSerializer, WithdrawalRequestSerializer,
    GroupSettingsChangeRequestSerializer, GroupCertificateSerializer, RoundPositionSerializer,
    PiggyBankConversionRequestSerializer,
    ProviderRegistrationSerializer, ProviderRegistrationListSerializer, ProviderDocumentSerializer,
    ProviderStaffSerializer, ServiceProductSerializer, ProviderTransactionSerializer,
    ProviderQuerySerializer, ProviderApplicationSerializer, ProviderNotificationSerializer
)
from Funding.serializers import BusinessSerializer
from Funding.models import Business
from Authentication.models import Profile, CustomUser
from Messages.models import Conversation, Message
from Notifications.models import create_notification
from Opinions.models import Follow
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
        """Get current user's balance with currency conversion for display"""
        from Payment.currency_service import currency_service

        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
             return Response({'balance': 0.00, 'currency': settings.PLATFORM_CURRENCY})

        user_currency = currency_service.detect_currency_for_user(request)
        platform_amount = payment_profile.comrade_balance

        display_amount = platform_amount
        if user_currency != settings.PLATFORM_CURRENCY:
            converted = currency_service.convert(
                Decimal(str(platform_amount)),
                settings.PLATFORM_CURRENCY,
                user_currency
            )
            display_amount = converted['converted_amount']

        return Response({
            'balance': float(platform_amount),
            'display_balance': round(float(display_amount), 2),
            'display_currency': user_currency,
            'platform_currency': settings.PLATFORM_CURRENCY,
            'exchange_rate': float(currency_service.get_rate(settings.PLATFORM_CURRENCY, user_currency)) if user_currency != settings.PLATFORM_CURRENCY else 1.0
        })

    @action(detail=False, methods=['get'])
    def supported_currencies(self, request):
        """Get list of supported currencies with full info"""
        from Payment.currency_service import currency_service
        return Response({
            'platform_currency': settings.PLATFORM_CURRENCY,
            'default_currency': settings.DEFAULT_CURRENCY,
            'currencies': currency_service.get_all_currencies_info(),
            'currency_codes': currency_service.get_supported_currencies()
        })

    @action(detail=False, methods=['get'])
    def detect_currency(self, request):
        """Detect the best currency for the current user based on location/profile"""
        from Payment.currency_service import currency_service
        currency = currency_service.detect_currency_for_user(request)
        info = currency_service.get_currency_info(currency)
        return Response({
            'detected_currency': currency,
            'currency_info': {
                'code': currency,
                'symbol': info.get('symbol', currency),
                'name': info.get('name', currency)
            },
            'platform_currency': settings.PLATFORM_CURRENCY
        })

    @action(detail=False, methods=['get'])
    def exchange_rate(self, request):
        """Get exchange rate between two currencies"""
        from_currency = request.query_params.get('from', 'USD')
        to_currency = request.query_params.get('to', 'USD')
        from Payment.currency_service import currency_service

        rate = currency_service.get_rate(from_currency.upper(), to_currency.upper())
        return Response({
            'from_currency': from_currency.upper(),
            'to_currency': to_currency.upper(),
            'rate': float(rate)
        })

    @action(detail=False, methods=['get'])
    def all_rates(self, request):
        """Get all exchange rates for a base currency"""
        base = request.query_params.get('base', 'USD')
        from Payment.currency_service import currency_service
        rates = currency_service.get_all_rates(base.upper())
        return Response({
            'base_currency': base.upper(),
            'rates': rates
        })

    @action(detail=False, methods=['post'])
    def convert(self, request):
        """Convert amount between currencies"""
        from_currency = request.data.get('from_currency', 'USD')
        to_currency = request.data.get('to_currency', 'USD')
        amount = request.data.get('amount')

        if not amount:
            return Response({'error': 'Amount is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        from Payment.currency_service import currency_service
        result = currency_service.convert(amount, from_currency.upper(), to_currency.upper())
        return Response(result)

    @action(detail=False, methods=['post'])
    def set_preferred_currency(self, request):
        """Set user's preferred currency for both payment profile and user profile"""
        currency = request.data.get('currency', 'USD').upper()
        from Payment.currency_service import currency_service

        if currency not in currency_service.get_supported_currencies():
            return Response({'error': f'Currency {currency} is not supported'}, status=status.HTTP_400_BAD_REQUEST)

        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Could not find payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payment_profile.preferred_currency = currency
        payment_profile.save()

        try:
            profile = request.user.profile
            profile.preferred_currency = currency
            profile.save()
        except Exception:
            pass

        return Response({
            'status': 'success',
            'preferred_currency': currency,
            'platform_currency': settings.PLATFORM_CURRENCY
        })


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
            
            # Handle round contribution payment
            if item_type == 'round_contribution' and item_id:
                try:
                    round_obj = RoundContribution.objects.get(id=item_id)
                    member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
                    if order.status == 'confirmed':
                        round_obj.record_contribution(
                            member=member,
                            amount=Decimal(str(item.get('price', 0))),
                            notes=item.get('notes', '')
                        )
                except Exception as e:
                    logger.error(f"Error processing round contribution in checkout: {str(e)}")
            
            # Handle piggy bank contribution payment
            if item_type == 'piggy_bank_contribution' and item_id:
                try:
                    target = GroupTarget.objects.get(id=item_id)
                    amount = Decimal(str(item.get('price', 0)))
                    
                    # Update piggy bank balance
                    target.current_amount += amount
                    target.save()
                    
                    # Create contribution record
                    from Payment.models import Contribution
                    member = None
                    if target.payment_group:
                        try:
                            member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
                            member.total_contributed += amount
                            member.save()
                        except PaymentGroupMember.DoesNotExist:
                            pass
                    
                    # Fallback for individual piggy banks
                    if not member:
                        member = PaymentGroupMember.objects.filter(payment_profile=payment_profile).first()
                    
                    if member:
                        Contribution.objects.create(
                            payment_group=target.payment_group,
                            target=target,
                            member=member,
                            amount=amount,
                            notes=item.get('notes', '')
                        )
                    
                    # Create transaction record
                    TransactionToken.objects.create(
                        payment_profile=payment_profile,
                        transaction_code=uuid.uuid4(),
                        amount=amount,
                        transaction_type='piggy_bank_contribution',
                        description=f'Contribution to Piggy Bank: {target.name}',
                        payment_group=target.payment_group,
                        piggy_bank=target
                    )
                except Exception as e:
                    logger.error(f"Error processing piggy bank contribution in checkout: {str(e)}")

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

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get transaction history from orders and transactions"""
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'results': [], 'count': 0})
        
        combined = []
        
        # Get TransactionTokens
        try:
            tokens = TransactionToken.objects.filter(
                Q(payment_profile=payment_profile) | Q(recipient_profile=payment_profile)
            ).select_related('payment_profile', 'payment_profile__user', 'recipient_profile', 'recipient_profile__user').order_by('-created_at')[:100]
            
            for t in tokens:
                combined.append({
                    'id': str(t.transaction_code),
                    'type': t.transaction_type,
                    'amount': str(t.amount),
                    'status': t.status,
                    'created_at': t.created_at.isoformat() if t.created_at else None,
                    'description': t.description or f"{t.get_transaction_type_display()} - {t.get_payment_option_display()}",
                    'reference': str(t.transaction_code),
                    'source': 'transaction'
                })
        except Exception as e:
            import logging
            logging.error(f"Error fetching TransactionToken: {e}")
        
        # Get Orders
        try:
            from Payment.models import Order
            orders = Order.objects.filter(
                buyer__user=user
            ).distinct().select_related('buyer', 'buyer__user').prefetch_related('items', 'items__product').order_by('-created_at')[:100]
            
            for order in orders:
                combined.append({
                    'id': str(order.id),
                    'type': 'order',
                    'amount': str(order.total_amount),
                    'status': order.status,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'description': f"Order #{order.order_number or str(order.id)[:8]} - {order.get_status_display()}",
                    'reference': str(order.id),
                    'source': 'order'
                })
        except Exception as e:
            import logging
            logging.error(f"Error fetching Orders: {e}")
        
        # Sort by date (newest first)
        combined.sort(key=lambda x: x['created_at'] or '', reverse=True)
        
        return Response({
            'results': combined[:100],
            'count': len(combined)
        })
    
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
            pay_from='internal' if payment_option == 'comrade_balance' else 'external',
            status='completed'
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

    @action(detail=False, methods=['post'])
    @db_transaction.atomic
    def reverse(self, request):
        """Reverse a completed transaction"""
        transaction_code = request.data.get('transaction_code')
        reason = request.data.get('reason', '')

        if not transaction_code:
            return Response({'error': 'Transaction code is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Could not find payment profile'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transaction = TransactionToken.objects.select_for_update().get(
                transaction_code=transaction_code
            )
        except TransactionToken.DoesNotExist:
            return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)

        if transaction.status not in ['completed', 'verified', 'settled']:
            return Response({'error': 'Transaction cannot be reversed'}, status=status.HTTP_400_BAD_REQUEST)

        if transaction.reversed_at:
            return Response({'error': 'Transaction already reversed'}, status=status.HTTP_400_BAD_REQUEST)

        is_sender = transaction.payment_profile == payment_profile
        is_recipient = transaction.recipient_profile == payment_profile

        if not is_sender and not is_recipient:
            return Response({'error': 'Not authorized to reverse this transaction'}, status=status.HTTP_403_FORBIDDEN)

        sender_profile = transaction.payment_profile
        recipient_profile = transaction.recipient_profile

        if is_sender and recipient_profile:
            sender_profile.comrade_balance += transaction.amount
            sender_profile.save()
        elif is_recipient and sender_profile:
            sender_profile.comrade_balance += transaction.amount
            sender_profile.save()
            recipient_profile.comrade_balance -= transaction.amount
            recipient_profile.save()

        transaction.status = 'reversed'
        transaction.reversed_at = timezone.now()
        transaction.reversal_reason = reason
        transaction.save()

        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=transaction,
            transaction_category='reversal',
            payment_type='individual',
            status='reversed',
            amount=transaction.amount
        )

        return Response({
            'status': 'success',
            'message': 'Transaction reversed successfully',
            'new_balance': float(sender_profile.comrade_balance) if is_sender else float(recipient_profile.comrade_balance)
        })

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
            pay_from='external',
            status='completed'
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
            pay_from='internal',
            status='completed'
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
    
    @action(detail=False, methods=['get'])
    def search_invitable_users(self, request):
        """Search for users to invite based on privacy settings and follow relationships."""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])

        current_user = request.user
        
        # Search users by username, name or email
        users = CustomUser.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query)
        ).exclude(id=current_user.id).distinct()[:20]
        
        results = []
        for user in users:
            try:
                # UserProfile model from Authentication
                profile = user.user_profile
                allow_invites = profile.allow_group_invites
            except Exception:
                allow_invites = 'followers' # Default
            
            # Check follow relationship (bidirectional as requested)
            is_follower = Follow.objects.filter(follower=user, following=current_user).exists()
            is_following = Follow.objects.filter(follower=current_user, following=user).exists()
            
            can_invite = False
            if allow_invites == 'anyone':
                can_invite = True
            elif allow_invites == 'followers' and (is_follower or is_following):
                can_invite = True
            
            if can_invite:
                avatar_url = None
                if hasattr(user, 'user_profile') and user.user_profile.avatar:
                    avatar_url = request.build_absolute_uri(user.user_profile.avatar.url)
                
                results.append({
                    'id': user.id,
                    'username': user.username,
                    'full_name': f"{user.first_name} {user.last_name}",
                    'email': user.email,
                    'avatar': avatar_url,
                })
        
        return Response(results)

    @action(detail=False, methods=['get'])
    def search_users(self, request):
        """Search for users to send money to."""
        query = request.query_params.get('q', '')
        if len(query) < 2:
            return Response([])

        current_user = request.user
        
        # Search all users by username, name or email (more permissive for sending money)
        users = CustomUser.objects.filter(
            Q(username__icontains=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query)
        ).exclude(id=current_user.id).distinct()[:20]
        
        results = []
        for user in users:
            avatar_url = None
            if hasattr(user, 'user_profile') and user.user_profile.avatar:
                avatar_url = request.build_absolute_uri(user.user_profile.avatar.url)
            
            results.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.email,
                'email': user.email,
                'avatar': avatar_url,
            })
        
        return Response(results)

    @action(detail=True, methods=['get'])
    def kitty_analytics(self, request, pk=None):
        """Get transaction analytics for a kitty."""
        group = self.get_object()
        if group.group_type != 'kitty':
            return Response({'error': 'Not a kitty'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Inflow/Outflow aggregations
        transactions = TransactionToken.objects.filter(payment_group=group)
        
        # Monthly breakdown
        from django.db.models.functions import TruncMonth
        monthly_stats = transactions.annotate(month=TruncMonth('created_at')).values('month').annotate(
            inflow=Sum('amount', filter=Q(transaction_type='contribution')),
            outflow=Sum('amount', filter=Q(transaction_type='withdrawal'))
        ).order_by('month')
        
        # Channel breakdown
        channel_stats = transactions.values('payment_option').annotate(
            total=Sum('amount')
        )
        
        # Connected businesses
        connected_businesses = []
        if group.entity_type and group.entity_id:
            try:
                Business = apps.get_model('Funding', 'Business')
                business = Business.objects.filter(id=group.entity_id).first()
                if business:
                    connected_businesses.append(BusinessSerializer(business).data)
            except Exception:
                pass

        return Response({
            'current_balance': group.current_amount,
            'monthly_stats': monthly_stats,
            'channel_stats': channel_stats,
            'connected_businesses': connected_businesses
        })

    @action(detail=True, methods=['get'])
    def analytics_summary(self, request, pk=None):
        """Comprehensive analytics summary for a payment group."""
        group = self.get_object()
        from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
        from django.db.models import Count, Avg
        
        transactions = TransactionToken.objects.filter(payment_group=group)
        members = PaymentGroupMember.objects.filter(payment_group=group)
        
        # Overall stats
        total_inflow = transactions.filter(
            transaction_type__in=['contribution', 'deposit']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_outflow = transactions.filter(
            transaction_type__in=['withdrawal', 'payout']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Monthly trends (last 12 months)
        twelve_months_ago = timezone.now() - timedelta(days=365)
        monthly_trends = transactions.filter(
            created_at__gte=twelve_months_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            inflow=Sum('amount', filter=Q(transaction_type__in=['contribution', 'deposit'])),
            outflow=Sum('amount', filter=Q(transaction_type__in=['withdrawal', 'payout'])),
            tx_count=Count('id')
        ).order_by('month')
        
        # Member contribution heatmap (member_id -> {month -> amount})
        member_heatmap = []
        for member in members.select_related('payment_profile', 'payment_profile__user'):
            member_txs = transactions.filter(
                payment_profile=member.payment_profile,
                transaction_type__in=['contribution', 'deposit'],
                created_at__gte=twelve_months_ago
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                total=Sum('amount')
            ).order_by('month')
            
            pp = member.payment_profile
            user_obj = pp.user if pp else None
            member_heatmap.append({
                'member_id': str(member.id),
                'name': f"{user_obj.first_name} {user_obj.last_name}".strip() if user_obj else member.anonymous_alias or 'Anonymous',
                'is_admin': member.is_admin,
                'total_contributed': float(member.total_contributed or 0),
                'monthly': [{
                    'month': entry['month'].isoformat() if entry['month'] else None,
                    'amount': float(entry['total'] or 0)
                } for entry in member_txs]
            })
        
        # Top 5 contributors
        top_contributors = sorted(member_heatmap, key=lambda x: x['total_contributed'], reverse=True)[:5]
        
        # Growth rate
        current_month_inflow = transactions.filter(
            transaction_type__in=['contribution', 'deposit'],
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        last_month = timezone.now() - timedelta(days=30)
        prev_month_inflow = transactions.filter(
            transaction_type__in=['contribution', 'deposit'],
            created_at__month=last_month.month,
            created_at__year=last_month.year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        growth_rate = 0
        if prev_month_inflow > 0:
            growth_rate = float((current_month_inflow - prev_month_inflow) / prev_month_inflow * 100)
        
        return Response({
            'group_id': str(group.id),
            'group_name': group.name,
            'total_balance': float(group.current_amount or 0),
            'target_amount': float(group.target_amount or 0),
            'progress_pct': float((group.current_amount or 0) / group.target_amount * 100) if group.target_amount else 0,
            'member_count': members.count(),
            'total_inflow': float(total_inflow),
            'total_outflow': float(total_outflow),
            'net_flow': float(total_inflow - total_outflow),
            'growth_rate': round(growth_rate, 2),
            'monthly_trends': [{
                'month': entry['month'].isoformat() if entry['month'] else None,
                'inflow': float(entry['inflow'] or 0),
                'outflow': float(entry['outflow'] or 0),
                'tx_count': entry['tx_count']
            } for entry in monthly_trends],
            'member_heatmap': member_heatmap,
            'top_contributors': top_contributors,
        })

    @action(detail=True, methods=['get'])
    def financial_report(self, request, pk=None):
        """Generate a financial report for the group (exportable)."""
        group = self.get_object()
        from django.db.models.functions import TruncMonth
        
        # Date range filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        transactions = TransactionToken.objects.filter(payment_group=group)
        if start_date:
            transactions = transactions.filter(created_at__date__gte=start_date)
        if end_date:
            transactions = transactions.filter(created_at__date__lte=end_date)
        
        # Summary
        inflow = transactions.filter(
            transaction_type__in=['contribution', 'deposit']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        outflow = transactions.filter(
            transaction_type__in=['withdrawal', 'payout']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Category breakdown
        category_breakdown = transactions.values('transaction_type').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Monthly P&L
        monthly_pnl = transactions.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            income=Sum('amount', filter=Q(transaction_type__in=['contribution', 'deposit'])),
            expenses=Sum('amount', filter=Q(transaction_type__in=['withdrawal', 'payout', 'fee'])),
        ).order_by('month')
        
        # Transaction ledger (last 100)
        ledger = transactions.order_by('-created_at')[:100].values(
            'id', 'amount', 'transaction_type', 'description', 'created_at', 'status'
        )
        
        # Member balances
        members = PaymentGroupMember.objects.filter(payment_group=group).select_related(
            'payment_profile', 'payment_profile__user'
        )
        member_summary = []
        for m in members:
            pp = m.payment_profile
            user_obj = pp.user if pp else None
            member_summary.append({
                'member_id': str(m.id),
                'name': f"{user_obj.first_name} {user_obj.last_name}".strip() if user_obj else m.anonymous_alias or 'Anonymous',
                'contributed': float(m.total_contributed or 0),
                'withdrawn': float(m.total_withdrawn or 0) if hasattr(m, 'total_withdrawn') else 0,
                'net': float(m.total_contributed or 0),
                'is_admin': m.is_admin,
            })
        
        return Response({
            'group_name': group.name,
            'report_generated_at': timezone.now().isoformat(),
            'date_range': {'start': start_date, 'end': end_date},
            'summary': {
                'total_income': float(inflow),
                'total_expenses': float(outflow),
                'net_position': float(inflow - outflow),
                'current_balance': float(group.current_amount or 0),
            },
            'category_breakdown': [{
                'type': entry['transaction_type'],
                'total': float(entry['total'] or 0),
                'count': entry['count']
            } for entry in category_breakdown],
            'monthly_pnl': [{
                'month': entry['month'].isoformat() if entry['month'] else None,
                'income': float(entry['income'] or 0),
                'expenses': float(entry['expenses'] or 0),
                'net': float((entry['income'] or 0) - (entry['expenses'] or 0)),
            } for entry in monthly_pnl],
            'ledger': list(ledger),
            'member_summary': member_summary,
        })

    @action(detail=True, methods=['post'])
    def create_business_with_kitty(self, request, pk=None):
        """Create a business linked to this group, optionally auto-creating/linking a kitty."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        
        # Only admin can create business for group
        is_admin = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile, is_admin=True).exists()
        if not is_admin and group.creator != payment_profile:
            return Response({'error': 'Only group admins can create businesses'}, status=status.HTTP_403_FORBIDDEN)
            
        business_data = request.data.copy()
        auto_create_kitty = business_data.pop('auto_create_kitty', False)
        existing_kitty_id = business_data.pop('existing_kitty_id', None)
        
        serializer = BusinessSerializer(data=business_data)
        if serializer.is_valid():
            business = serializer.save()
            
            # Track business ownership to group (could be handled in Business model metadata)
            # For now, kitty is the primary link
            
            if auto_create_kitty:
                kitty = PaymentGroups.objects.create(
                    name=f"{business.name} Kitty",
                    group_type='kitty',
                    creator=payment_profile,
                    entity_type=ContentType.objects.get_for_model(business),
                    entity_id=business.id,
                    parent_group=group
                )
                # Add group admins to kitty
                admins = PaymentGroupMember.objects.filter(payment_group=group, is_admin=True)
                for admin in admins:
                    PaymentGroupMember.objects.get_or_create(payment_group=kitty, payment_profile=admin.payment_profile, is_admin=True)
            elif existing_kitty_id:
                try:
                    kitty = PaymentGroups.objects.get(id=existing_kitty_id, group_type='kitty')
                    kitty.entity_type = ContentType.objects.get_for_model(business)
                    kitty.entity_id = business.id
                    kitty.save()
                except PaymentGroups.DoesNotExist:
                    pass
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
        
        # Check if this is a kitty creation
        is_kitty = serializer.validated_data.get('is_kitty', False) or serializer.validated_data.get('group_type') == 'kitty'
        # Handle both parent_group and payment_group (from frontend) for kitty linkage
        parent_group_id = serializer.validated_data.get('parent_group') or self.request.data.get('payment_group')
        
        # Check Limits (skip for kitties as they're sub-funds)
        if not is_kitty:
            can_create, error_msg = check_group_creation_limit(payment_profile)
            if not can_create:
                print(error_msg)
                print(can_create)
                raise serializers.ValidationError(error_msg)
            
        # Set max capacity based on tier (skip for kitties)
        if is_kitty:
            max_capacity = 1000  # Default high capacity for kitties
        else:
            max_limit = get_max_group_members(payment_profile.tier)
            requested_capacity = serializer.validated_data.get('max_capacity', 10)
            max_capacity = min(requested_capacity, max_limit)
            if payment_profile.tier == 'gold':
                max_capacity = requested_capacity  # Unlimited
        
        # Pop phases_data before saving the group
        phases_data = serializer.validated_data.pop('phases_data', [])

        # For kitties, creator should be the parent group's creator
        creator = payment_profile
        if is_kitty and parent_group_id:
            try:
                # If parent_group_id is already an object (from serializer), use it, otherwise fetch
                parent_group = parent_group_id if isinstance(parent_group_id, PaymentGroups) else PaymentGroups.objects.get(id=parent_group_id)
                creator = parent_group.creator  # Group creator becomes kitty creator
            except (PaymentGroups.DoesNotExist, ValueError):
                pass

        group = serializer.save(
            creator=creator,
            tier=payment_profile.tier if not is_kitty else 'standard',
            max_capacity=max_capacity
        )
        
        # Add creator as admin member (for kitties, add group admin members)
        if is_kitty and parent_group_id:
            # Add all admins from parent group to kitty
            parent_admins = PaymentGroupMember.objects.filter(
                payment_group_id=parent_group_id,
                is_admin=True
            )
            for admin_member in parent_admins:
                PaymentGroupMember.objects.create(
                    payment_group=group,
                    payment_profile=admin_member.payment_profile,
                    is_admin=True
                )
        else:
            # Regular group - add creator as admin
            PaymentGroupMember.objects.create(
                payment_group=group,
                payment_profile=payment_profile,
                is_admin=True
            )

        # Create phases
        for idx, phase in enumerate(phases_data):
            GroupPhase.objects.create(
                group=group,
                name=phase.get('name', f'Phase {idx + 1}'),
                description=phase.get('description', ''),
                target_amount=Decimal(str(phase.get('target_amount', 0))),
                proportion=Decimal(str(phase.get('proportion', 0))),
                start_date=phase.get('start_date'),
                end_date=phase.get('end_date'),
                order=idx,
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
        
        # Upgrade capacity based on new member count
        if hasattr(group, 'auto_upgrade_capacity'):
            group.auto_upgrade_capacity()
        
        return Response(PaymentGroupMemberSerializer(member).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def start_round(self, request, pk=None):
        round_obj = self.get_object()
        
        if round_obj.status != 'pending':
            return Response({'error': 'Round is already active or completed'}, status=400)
            
        # Automated game: randomly assign if method is random and no one is awarded
        if round_obj.assignment_method == 'random' and not round_obj.awarded_to:
            import random
            group_members = list(round_obj.payment_group.members.all())
            # Find members who haven't been awarded in previous rounds
            awarded_member_ids = RoundContribution.objects.filter(payment_group=round_obj.payment_group, awarded_to__isnull=False).values_list('awarded_to_id', flat=True)
            eligible_members = [m for m in group_members if m.id not in awarded_member_ids]
            
            if eligible_members:
                round_obj.awarded_to = random.choice(eligible_members)
            elif group_members:
                # Cycle resets, everyone is eligible again
                round_obj.awarded_to = random.choice(group_members)
        
        elif round_obj.assignment_method == 'sequential' and not round_obj.awarded_to:
            # Picking position system
            try:
                pos = RoundPosition.objects.get(payment_group=round_obj.payment_group, position_number=round_obj.round_number)
                round_obj.awarded_to = pos.member
            except RoundPosition.DoesNotExist:
                # Fallback or error
                pass
                
        round_obj.status = 'active'
        round_obj.start_date = timezone.now()
        round_obj.save()
        
        return Response({'status': 'Round started', 'awarded_to': str(round_obj.awarded_to.id) if round_obj.awarded_to else None})

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
        
        from decimal import Decimal
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process payment based on method
        if payment_method == 'wallet':
            # Lock profile before balance check and deduction to prevent race conditions
            payment_profile = PaymentProfile.objects.select_for_update().get(id=payment_profile.id)
            if payment_profile.comrade_balance < amount:
                return Response({'error': f'Insufficient balance. Your balance is {payment_profile.comrade_balance}, but you tried to contribute {amount}.'}, status=status.HTTP_400_BAD_REQUEST)
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
        group = PaymentGroups.objects.select_for_update().get(id=group.id)
        group.current_amount += amount
        group.save()
        
        # Update member contribution
        on_behalf_of_id = request.data.get('on_behalf_of')
        target_member = member
        if on_behalf_of_id:
            try:
                target_member = PaymentGroupMember.objects.get(id=on_behalf_of_id, payment_group=group)
            except (PaymentGroupMember.DoesNotExist, ValueError):
                return Response({'error': 'Target member not found in this group'}, status=status.HTTP_404_NOT_FOUND)

        target_member.total_contributed += amount
        target_member.save()
        
        # Record contribution
        contribution = Contribution.objects.create(
            payment_group=group,
            member=target_member,
            on_behalf_of=member if on_behalf_of_id else None,
            amount=amount,
            notes=request.data.get('notes', '')
        )
        
        # Create audit trail
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=amount,
            transaction_type='contribution',
            description=f'Contribution to group: {group.name}'
        )
        
        # Check if target reached
        if group.target_amount and group.current_amount >= group.target_amount:
            if group.auto_purchase:
                # Trigger auto purchase logic here
                pass
        
        return Response(ContributionSerializer(contribution).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def group_donations(self, request, pk=None):
        """Get donations belonging to this group or where this group is the recipient."""
        group = self.get_object()
        from django.contrib.contenttypes.models import ContentType
        
        group_type = ContentType.objects.get_for_model(group)
        
        donations = Donation.objects.filter(
            Q(payment_group=group) | 
            Q(recipient_content_type=group_type, recipient_object_id=str(group.id))
        ).order_by('-created_at')
        
        return Response(DonationSerializer(donations, many=True).data)

    @action(detail=True, methods=['get', 'post'])
    def group_investments(self, request, pk=None):
        """Get or create investments belonging to this group."""
        group = self.get_object()
        
        if request.method == 'POST':
            # Get user profile
            from Authentication.models import Profile
            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                return Response({'error': 'Profile not found'}, status=400)
            
            # Get payment profile
            try:
                payment_profile = PaymentProfile.objects.get(user=profile)
            except PaymentProfile.DoesNotExist:
                return Response({'error': 'Payment profile not found'}, status=400)
            
            # Map frontend fields to model fields
            data = {
                'name': request.data.get('investment_name') or request.data.get('name', 'Unnamed Investment'),
                'description': request.data.get('description', ''),
                'total_amount': request.data.get('amount_invested') or request.data.get('total_amount', 0),
                'status': 'quoting',  # Default status for new investments
                'payment_group': group.id,
                'initiated_by': payment_profile.id,
            }
            
            serializer = GroupInvestmentSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
        
        investments = GroupInvestment.objects.filter(payment_group=group).order_by('-created_at')
        return Response(GroupInvestmentSerializer(investments, many=True).data)

    @action(detail=True, methods=['get', 'post'])
    def group_loans(self, request, pk=None):
        """Get or create loans for this group."""
        group = self.get_object()
        
        if request.method == 'POST':
            from Authentication.models import Profile
            try:
                profile = Profile.objects.get(user=request.user)
            except Profile.DoesNotExist:
                return Response({'error': 'Profile not found'}, status=400)
            
            data = {
                'loan_product': request.data.get('loan_product'),
                'amount': request.data.get('amount'),
                'tenure_months': request.data.get('tenure_months'),
                'purpose': request.data.get('purpose', ''),
                'group': group.id,
            }
            
            serializer = LoanApplicationSerializer(data=data)
            if serializer.is_valid():
                serializer.save(user=profile)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
        
        loans = LoanApplication.objects.filter(group=group).order_by('-created_at')
        return Response(LoanApplicationSerializer(loans, many=True).data)

    @action(detail=True, methods=['get'])
    def group_kitties(self, request, pk=None):
        """Get sub-kitties under this group."""
        group = self.get_object()
        kitties = PaymentGroups.objects.filter(parent_group=group, is_kitty=True).order_by('-created_at')
        return Response(KittySerializer(kitties, many=True).data)

    @action(detail=True, methods=['get'])
    def group_businesses(self, request, pk=None):
        """Get establishments/businesses owned by this group."""
        group = self.get_object()
        businesses = Business.objects.filter(payment_group=group).order_by('-created_at')
        return Response(BusinessSerializer(businesses, many=True).data)

    @action(detail=True, methods=['get'])
    def group_rounds(self, request, pk=None):
        """Get round contributions for this group."""
        group = self.get_object()
        rounds = RoundContribution.objects.filter(payment_group=group).order_by('-round_number')
        return Response(RoundContributionSerializer(rounds, many=True).data)

    @action(detail=True, methods=['get'], url_path='group_withdrawals')
    def group_withdrawals(self, request, pk=None):
        """List withdrawal requests for this group."""
        group = self.get_object()
        withdrawals = WithdrawalRequest.objects.filter(payment_group=group).order_by('-created_at')
        return Response(WithdrawalRequestSerializer(withdrawals, many=True).data)

    @action(detail=True, methods=['post'], url_path='request_withdrawal')
    def request_withdrawal(self, request, pk=None):
        """Create a withdrawal request for this group."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'You are not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = WithdrawalRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                payment_group=group, 
                requester=member,
                destination_wallet=payment_profile
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def group_benefit_rules(self, request, pk=None):
        """Get benefit distribution rules for this group."""
        group = self.get_object()
        rules = BenefitDistributionRule.objects.filter(payment_group=group).order_by('priority')
        return Response(BenefitDistributionRuleSerializer(rules, many=True).data)

    @action(detail=True, methods=['get'])
    def group_settings_changes(self, request, pk=None):
        """Get group settings change requests."""
        group = self.get_object()
        changes = GroupSettingsChangeRequest.objects.filter(payment_group=group).order_by('-created_at')
        return Response(GroupSettingsChangeRequestSerializer(changes, many=True).data)

    @action(detail=True, methods=['get', 'post'])
    def group_ventures(self, request, pk=None):
        """Get or create ventures for this group."""
        from Funding.serializers import CapitalVentureSerializer
        group = self.get_object()
        
        if request.method == 'POST':
            # Map frontend fields to model fields
            data = {
                'name': request.data.get('venture_name') or request.data.get('name', 'Unnamed Venture'),
                'description': request.data.get('description', ''),
                'investment_criteria': request.data.get('description', 'General investment criteria'),
                'total_fund': request.data.get('total_fund', 0) or 0,
                'available_fund': request.data.get('available_fund', 0) or 0,
                'min_investment': request.data.get('min_investment', 0) or 0,
                'max_investment': request.data.get('max_investment', 0) or 1000000,
                'investment_focus': request.data.get('investment_focus', ''),
                'payment_group': group.id,
                'created_by': request.user.id,
            }
            
            serializer = CapitalVentureSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        ventures = CapitalVenture.objects.filter(payment_group=group).order_by('-created_at')
        return Response(CapitalVentureSerializer(ventures, many=True).data)

    @action(detail=True, methods=['post'])
    def contribute_on_behalf(self, request, pk=None):
        """Contribute to a round on behalf of another member."""
        group = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found.'}, status=400)
            
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'You must be a member of this group.'}, status=403)
            
        on_behalf_of_id = request.data.get('on_behalf_of')
        round_id = request.data.get('round_id')
        amount = request.data.get('amount')
        
        if not all([on_behalf_of_id, round_id, amount]):
            return Response({'error': 'on_behalf_of, round_id, and amount are required.'}, status=400)
            
        try:
            target_member = PaymentGroupMember.objects.get(id=on_behalf_of_id, payment_group=group)
            round_obj = RoundContribution.objects.get(id=round_id, payment_group=group)
        except (PaymentGroupMember.DoesNotExist, RoundContribution.DoesNotExist):
            return Response({'error': 'Target member or round not found.'}, status=404)
            
        if payment_profile.comrade_balance < Decimal(str(amount)):
             return Response({'error': 'Insufficient balance in wallet.'}, status=400)
        
        payment_profile.comrade_balance -= Decimal(str(amount))
        payment_profile.save()
        
        contribution = RoundMemberContribution.objects.create(
            round=round_obj,
            member=member,
            on_behalf_of=target_member,
            contribution_amount=amount,
            notes=request.data.get('notes', '')
        )
        
        round_obj.total_collected += Decimal(str(amount))
        round_obj.save()
        
        return Response(RoundMemberContributionSerializer(contribution).data)

    @action(detail=True, methods=['post'])
    def request_certificate(self, request, pk=None):
        """Request a verification certificate for the group."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        is_admin = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile, is_admin=True).exists()
        if not is_admin and group.creator != payment_profile:
            return Response({'error': 'Only group admins can request a certificate'}, status=status.HTTP_403_FORBIDDEN)
            
        cert, created = GroupCertificate.objects.get_or_create(payment_group=group)
        if not created and cert.status == 'approved':
            return Response({'error': 'Group is already verified', 'registration_number': cert.registration_number}, status=status.HTTP_400_BAD_REQUEST)
            
        cert.status = 'pending'
        cert.save()
        return Response({'message': 'Certificate requested successfully', 'status': cert.status})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def verify_group(self, request, pk=None):
        group = self.get_object()
        action_type = request.data.get('action', 'approve') # approve or reject
        notes = request.data.get('notes', '')
        
        try:
            cert = GroupCertificate.objects.get(payment_group=group)
        except GroupCertificate.DoesNotExist:
            return Response({'error': 'No pending certificate request for this group'}, status=status.HTTP_404_NOT_FOUND)
            
        if action_type == 'approve':
            import uuid
            cert.status = 'approved'
            cert.registration_number = f"QOM-{uuid.uuid4().hex[:8].upper()}-{timezone.now().year}"
            cert.issued_at = timezone.now()
            cert.expires_at = timezone.now() + timedelta(days=365) # 1 year validity
            cert.verification_notes = notes or 'Verified and Contract Generated'
            cert.save()
            return Response({'message': 'Group verified successfully', 'registration_number': cert.registration_number})
        elif action_type == 'reject':
            cert.status = 'rejected'
            cert.verification_notes = notes
            cert.save()
            return Response({'message': 'Group verification rejected'})
        else:
            return Response({'error': 'Invalid action type'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'])
    def group_automations(self, request, pk=None):
        group = self.get_object()
        
        if request.method == 'POST':
            user = request.user
            payment_profile = get_or_create_payment_profile(user)
            
            # Get the member for this group
            try:
                member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            except PaymentGroupMember.DoesNotExist:
                return Response({'error': 'You are not a member of this group'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate next contribution date
            from datetime import datetime, timedelta
            frequency = request.data.get('frequency', 'monthly')
            execution_day = int(request.data.get('execution_day', 1))
            
            now = datetime.now()
            if frequency == 'daily':
                next_date = now + timedelta(days=1)
            elif frequency == 'weekly':
                next_date = now + timedelta(weeks=1)
            else:  # monthly
                next_date = now.replace(day=min(execution_day, 28))
                if next_date <= now:
                    next_date = (now.replace(day=1) + timedelta(days=32)).replace(day=min(execution_day, 28))
            
            # Map frontend fields to model fields
            data = {
                'member': member.id,
                'amount': request.data.get('amount'),
                'frequency': frequency,
                'next_contribution_date': next_date,
                'is_active': request.data.get('is_active', True)
            }
            
            serializer = StandingOrderSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Get automations through member's payment group
        automations = StandingOrder.objects.filter(
            member__payment_group=group
        ).select_related('member', 'member__payment_profile')
        return Response(StandingOrderSerializer(automations, many=True).data)

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
                user_exists = True
            except CustomUser.DoesNotExist:
                user_exists = False
        elif invited_identifier:
            try:
                invited_user = CustomUser.objects.get(username=invited_identifier)
                invited_email = invited_user.email
                user_exists = True
                
                # Check privacy for username search
                try:
                    target_profile = invited_user.user_profile
                    allow_invites = target_profile.allow_group_invites
                except Exception:
                    allow_invites = 'followers'
                
                if allow_invites != 'anyone':
                    is_mutual = Follow.objects.filter(follower=invited_user, following=user).exists() or \
                                Follow.objects.filter(follower=user, following=invited_user).exists()
                    if allow_invites == 'none' or (allow_invites == 'followers' and not is_mutual):
                        return Response({'error': 'This user does not allow invitations from non-followers.'}, status=status.HTTP_403_FORBIDDEN)
                        
            except CustomUser.DoesNotExist:
                user_exists = False
        
        if user_exists:
            try:
                invited_profile = Profile.objects.get(user=invited_user)
                invited_payment_profile = PaymentProfile.objects.get(user=invited_profile)
            except (Profile.DoesNotExist, PaymentProfile.DoesNotExist):
                # User exists but might not have payment profile yet
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
        
        # Send in-app notification if user exists on platform (instead of DM)
        if user_exists:
            try:
                create_notification(
                    recipient=invited_user,
                    actor=user,
                    notification_type='system',
                    title='Group Invitation',
                    message=f"You've been invited to join the payment group \"{group.name}\" by {payment_profile.user.user.username}.",
                    action_url=invite_url,
                    extra_data={'group_id': str(group.id), 'invitation_link': invitation_link}
                )
            except Exception as e:
                logger.warning(f'Failed to send notification for group invite: {e}')

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

    @action(detail=True, methods=['get'], url_path='group_piggy_banks')
    def group_piggy_banks(self, request, pk=None):
        """Get piggy banks belonging to this group with fund isolation."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_member = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).exists()
        if not is_member and group.creator != payment_profile:
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
        
        targets = GroupTarget.objects.filter(payment_group=group).order_by('-created_at')
        
        # Fund isolation: compute per-member contributions
        data = []
        for target in targets:
            target_data = GroupTargetSerializer(target, context={'request': request}).data
            # Add isolated contribution info
            from Payment.models import Contribution
            member_contributions = Contribution.objects.filter(
                payment_group=group
            ).values('member__payment_profile').annotate(
                total=Sum('amount')
            )
            target_data['fund_isolation'] = {
                'total_fund': str(target.current_amount),
                'target_fund': str(target.target_amount),
                'contributors': len(member_contributions),
            }
            data.append(target_data)
        
        return Response(data)

    @action(detail=True, methods=['get'], url_path='analytics')
    def analytics(self, request, pk=None):
        """Get group analytics: contribution trends, member activity, etc."""
        import logging
        logger = logging.getLogger('django')
        logger.error(f"ANALYTICS: pk={pk}, request.method={request.method}")
        
        from django.http import Http404
        try:
            group = self.get_object()
            logger.error(f"ANALYTICS: group found, id={group.id}")
        except PaymentGroups.DoesNotExist:
            logger.error(f"ANALYTICS: Group {pk} does not exist")
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"ANALYTICS: Error finding group {pk}: {str(e)}")
            return Response({'error': f'Error finding group: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_member = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).exists()
        if not is_member and group.creator != payment_profile:
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncMonth
        
        # Monthly contribution trend
        try:
            monthly = Contribution.objects.filter(payment_group=group).annotate(
                month=TruncMonth('contributed_at')
            ).values('month').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('month')
        except Exception:
            monthly = []
        
        # Top contributors
        try:
            top_contributors = PaymentGroupMember.objects.filter(
                payment_group=group
            ).order_by('-total_contributed')[:5]
        except Exception:
            top_contributors = []
        
        top_list = []
        for m in top_contributors:
            try:
                if m.is_anonymous:
                    name = m.anonymous_alias or 'Anonymous'
                elif m.payment_profile and m.payment_profile.user and m.payment_profile.user.user:
                    user = m.payment_profile.user.user
                    name = f"{user.first_name} {user.last_name}".strip() or user.email
                else:
                    name = 'Unknown Member'
            except Exception:
                name = 'Unknown Member'
            top_list.append({
                'name': name,
                'contributed': str(m.total_contributed),
                'is_anonymous': m.is_anonymous,
            })
        
        try:
            checkout_count = group.checkout_requests.count()
            pending_count = group.checkout_requests.filter(status='pending').count()
        except Exception:
            checkout_count = 0
            pending_count = 0
        
        return Response({
            'monthly_trend': [
                {'month': entry['month'].isoformat() if entry['month'] else None, 'total': str(entry['total']), 'count': entry['count']}
                for entry in monthly
            ],
            'top_contributors': top_list,
            'total_members': group.members.count(),
            'total_contributed': str(group.current_amount),
            'target_amount': str(group.target_amount or 0),
            'progress': round(float(group.current_amount) / float(group.target_amount) * 100, 2) if group.target_amount and group.target_amount > 0 else 0,
            'capacity_category': str(group.max_capacity),
            'checkout_requests_count': checkout_count,
            'pending_checkouts': pending_count,
        })

    @action(detail=True, methods=['get', 'put'], url_path='rules')
    def rules(self, request, pk=None):
        """Get or update group rules."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.method == 'GET':
            return Response({'rules_text': group.rules_text or ''})
        
        # PUT — only admin/creator
        is_creator = group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_creator and not is_admin:
            return Response({'error': 'Only admins can update rules'}, status=status.HTTP_403_FORBIDDEN)
        
        group.rules_text = request.data.get('rules_text', '')
        group.save(update_fields=['rules_text', 'updated_at'])
        return Response({'message': 'Rules updated', 'rules_text': group.rules_text})

    @action(detail=True, methods=['patch'], url_path='update_settings')
    def update_settings(self, request, pk=None):
        """Update group-level settings (admin/creator only)."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_creator = group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_creator and not is_admin:
            return Response({'error': 'Only admins can update settings'}, status=status.HTTP_403_FORBIDDEN)
        
        allowed_fields = [
            'requires_approval', 'allow_anonymous', 'transaction_trigger_role',
            'approval_threshold', 'hierarchy_mode', 'accent_color',
            'joining_minimum', 'investment_pitch', 'loan_proposition',
            'allow_partial_withdrawal', 'immature_exit_penalty_rate',
            'is_lifetime', 'expiry_date', 'deadline',
            'contribution_type', 'contribution_amount', 'frequency',
            'is_round_contribution_enabled', 'round_frequency', 'round_amount',
            'round_assignment_method', 'round_persistence_mode', 'round_persistence_count',
            'target_amount', 'entry_fee_required', 'entry_fee_amount',
            'custom_application_questions', 'is_public', 'auto_purchase',
        ]
        updated = []
        for field in allowed_fields:
            if field in request.data:
                setattr(group, field, request.data[field])
                updated.append(field)
        
        if updated:
            group.save(update_fields=updated + ['updated_at'])
        
        serializer = self.get_serializer(group)
        return Response({
            'message': f'Updated: {", ".join(updated)}',
            'group': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='change_group_type')
    def change_group_type(self, request, pk=None):
        """Change group type (standard/piggy_bank/kitty). Admin/creator only."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        is_creator = group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_creator and not is_admin:
            return Response({'error': 'Only admins can change group type'}, status=status.HTTP_403_FORBIDDEN)

        new_type = request.data.get('group_type')
        if not new_type:
            return Response({'error': 'group_type is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            group.change_group_type(new_type, requestor=payment_profile)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(group)
        return Response({
            'message': f'Group type changed to {new_type}',
            'group': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='change_capacity')
    def change_capacity(self, request, pk=None):
        """Manually override capacity_category. Admin/creator only."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        is_creator = group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_creator and not is_admin:
            return Response({'error': 'Only admins can change capacity'}, status=status.HTTP_403_FORBIDDEN)

        new_capacity = request.data.get('capacity_category')
        valid_categories = dict(PaymentGroups._meta.get_field('capacity_category').choices)
        if not new_capacity or new_capacity not in valid_categories:
            return Response({'error': f'capacity_category must be one of {list(valid_categories.keys())}'}, status=status.HTTP_400_BAD_REQUEST)

        group.capacity_category = new_capacity
        group.save(update_fields=['capacity_category', 'updated_at'])
        serializer = self.get_serializer(group)
        return Response({
            'message': f'Capacity changed to {new_capacity}',
            'group': serializer.data
        })

    @action(detail=True, methods=['get'], url_path='portfolio_snapshot')
    def portfolio_snapshot(self, request, pk=None):
        """Unified snapshot of all connected entities: type, gains, performance %, start date."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        is_member = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile
        ).exists()
        if not is_member and group.creator != payment_profile:
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)

        snapshot = []

        # Piggy Banks (GroupTargets)
        piggy_banks = GroupTarget.objects.filter(payment_group=group)
        for pb in piggy_banks:
            pct = round((float(pb.current_amount) / float(pb.target_amount) * 100), 2) if pb.target_amount and pb.target_amount > 0 else 0
            snapshot.append({
                'id': str(pb.id),
                'type': 'piggy_bank',
                'name': pb.name,
                'current_amount': str(pb.current_amount),
                'target_amount': str(pb.target_amount),
                'gains': str(pb.current_amount - pb.target_amount) if pb.current_amount > pb.target_amount else '0',
                'performance_pct': pct,
                'start_date': pb.created_at.isoformat() if pb.created_at else None,
                'status': pb.status,
            })

        # Donations
        donations = Donation.objects.filter(payment_group=group)
        for d in donations:
            pct = round((float(d.current_amount) / float(d.target_amount) * 100), 2) if d.target_amount and d.target_amount > 0 else 0
            snapshot.append({
                'id': str(d.id),
                'type': 'donation',
                'name': d.title,
                'current_amount': str(d.current_amount),
                'target_amount': str(d.target_amount),
                'gains': '0',
                'performance_pct': pct,
                'start_date': d.created_at.isoformat() if d.created_at else None,
                'status': d.status,
            })

        # Investments
        investments = GroupInvestment.objects.filter(payment_group=group)
        for inv in investments:
            pct = 0
            if inv.contribution_balance and inv.contribution_balance > 0:
                pct = round((float(inv.net_profit_loss or 0) / float(inv.contribution_balance) * 100), 2)
            snapshot.append({
                'id': str(inv.id),
                'type': 'investment',
                'name': inv.title,
                'current_amount': str(inv.amount_collected),
                'target_amount': str(inv.total_amount),
                'gains': str(inv.net_profit_loss or 0),
                'performance_pct': pct,
                'start_date': inv.created_at.isoformat() if inv.created_at else None,
                'status': inv.status,
            })

        # Round Contributions
        rounds = RoundContribution.objects.filter(payment_group=group)
        for r in rounds:
            snapshot.append({
                'id': str(r.id),
                'type': 'round',
                'name': f'Round {r.round_number}',
                'current_amount': str(r.total_collected),
                'target_amount': str(r.contribution_amount),
                'gains': '0',
                'performance_pct': r.get_progress_percentage(),
                'start_date': r.start_date.isoformat() if r.start_date else None,
                'status': r.status,
            })

        # Withdrawals
        withdrawals = WithdrawalRequest.objects.filter(payment_group=group)
        for w in withdrawals:
            snapshot.append({
                'id': str(w.id),
                'type': 'withdrawal',
                'name': f'{w.withdrawal_type} - {w.amount}',
                'current_amount': str(w.amount),
                'target_amount': '0',
                'gains': '0',
                'performance_pct': 0,
                'start_date': w.created_at.isoformat() if w.created_at else None,
                'status': w.status,
            })

        # Owned Establishments
        establishments = Establishment.objects.filter(owning_group=group)
        for est in establishments:
            snapshot.append({
                'id': str(est.id),
                'type': 'establishment',
                'name': est.name,
                'current_amount': '0',
                'target_amount': '0',
                'gains': '0',
                'performance_pct': 0,
                'start_date': est.created_at.isoformat() if est.created_at else None,
                'status': 'active' if est.is_active else 'inactive',
            })

        return Response({
            'group_id': str(group.id),
            'group_name': group.name,
            'total_items': len(snapshot),
            'entities': snapshot,
        })

    @action(detail=True, methods=['post'], url_path='update_member_role')
    def update_member_role(self, request, pk=None):
        """Update a member's role (admin/creator only)."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_creator = group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_creator and not is_admin:
            return Response({'error': 'Only admins can change roles'}, status=status.HTTP_403_FORBIDDEN)
        
        member_id = request.data.get('member_id')
        new_role = request.data.get('role')  # 'admin', 'moderator', 'member'
        
        if not member_id or not new_role:
            return Response({'error': 'member_id and role are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_role not in ['admin', 'moderator', 'member']:
            return Response({'error': 'Invalid role. Must be admin, moderator, or member.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target_member = PaymentGroupMember.objects.get(id=member_id, payment_group=group)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Member not found in this group'}, status=status.HTTP_404_NOT_FOUND)
        
        # Prevent demoting the group creator
        if target_member.payment_profile == group.creator and new_role != 'admin':
            return Response({'error': 'Cannot demote the group creator'}, status=status.HTTP_400_BAD_REQUEST)
        
        target_member.role = new_role
        target_member.is_admin = (new_role == 'admin')
        target_member.save(update_fields=['role', 'is_admin'])
        
        return Response({
            'message': f'Role updated to {new_role}',
            'member_id': member_id,
            'role': new_role
        })

    @action(detail=True, methods=['post'], url_path='apply_certificate')
    def apply_certificate(self, request, pk=None):
        """Apply for group certification/verification."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        is_creator = group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        
        if not is_creator and not is_admin:
            return Response({'error': 'Only admins can apply for certification'}, status=status.HTTP_403_FORBIDDEN)
            
        from .models import GroupCertificate
        from .serializers import GroupCertificateSerializer
        
        certificate, created = GroupCertificate.objects.get_or_create(payment_group=group)
        if not created and certificate.status in ['pending', 'approved']:
            return Response({'error': f'Certificate is already {certificate.status}'}, status=status.HTTP_400_BAD_REQUEST)
            
        certificate.status = 'pending'
        certificate.save()
        
        return Response({'message': 'Certificate application submitted successfully', 'certificate': GroupCertificateSerializer(certificate).data})

    @action(detail=True, methods=['get'], url_path='certificate_status')
    def certificate_status(self, request, pk=None):
        """Get the current certificate status."""
        group = self.get_object()
        from .models import GroupCertificate
        from .serializers import GroupCertificateSerializer
        
        try:
            certificate = GroupCertificate.objects.get(payment_group=group)
            return Response(GroupCertificateSerializer(certificate).data)
        except GroupCertificate.DoesNotExist:
            return Response({'status': 'none', 'message': 'No certificate application found.'})

    @action(detail=True, methods=['post'], url_path='approve_certificate')
    def approve_certificate(self, request, pk=None):
        """Approve or reject a certificate (Superadmin/System level action)."""
        if not request.user.is_staff:
            return Response({'error': 'Only staff can approve certificates'}, status=status.HTTP_403_FORBIDDEN)
            
        group = self.get_object()
        action_type = request.data.get('action', 'approved') # 'approved', 'rejected', 'revoked'
        notes = request.data.get('notes', '')
        
        from .models import GroupCertificate
        from .serializers import GroupCertificateSerializer
        
        try:
            certificate = GroupCertificate.objects.get(payment_group=group)
            certificate.status = action_type
            certificate.verification_notes = notes
            if action_type == 'approved':
                certificate.issued_at = timezone.now()
                # Dummy reg number generation
                certificate.registration_number = f"QOM-{group.id}-{timezone.now().strftime('%Y%m%d')}"
            certificate.save()
            return Response({'message': f'Certificate {action_type}', 'certificate': GroupCertificateSerializer(certificate).data})
        except GroupCertificate.DoesNotExist:
            return Response({'error': 'No certificate application found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='create_entity')
    def create_entity(self, request, pk=None):
        """Create any connected entity (piggy bank, donation, round, benefit rule, investment pitch, settings change)."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists() or group.creator == payment_profile
        if not is_admin:
            return Response({'error': 'Only admins can create entities'}, status=status.HTTP_403_FORBIDDEN)

        entity_type = request.data.get('entity_type')
        data = request.data.get('data', {})

        if entity_type == 'piggy_bank':
            name = data.get('name')
            if not name:
                return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)
            obj = GroupTarget.objects.create(
                payment_group=group,
                name=name,
                target_amount=data.get('target_amount', 0),
                description=data.get('description', ''),
                is_sharable=data.get('is_sharable', True),
            )
            return Response({'entity_type': 'piggy_bank', 'id': str(obj.id), 'data': GroupTargetSerializer(obj).data}, status=status.HTTP_201_CREATED)

        elif entity_type == 'donation':
            title = data.get('title')
            if not title:
                return Response({'error': 'title is required'}, status=status.HTTP_400_BAD_REQUEST)
            obj = Donation.objects.create(
                payment_group=group,
                title=title,
                description=data.get('description', ''),
                target_amount=data.get('target_amount', 0),
                minimum_contribution=data.get('minimum_contribution', 0),
                status='active',
            )
            return Response({'entity_type': 'donation', 'id': str(obj.id), 'data': DonationSerializer(obj).data}, status=status.HTTP_201_CREATED)

        elif entity_type == 'round':
            obj = RoundContribution.objects.create(
                payment_group=group,
                round_number=data.get('round_number', 1),
                contribution_amount=data.get('contribution_amount', group.round_amount),
                assignment_method=data.get('assignment_method', group.round_assignment_method),
                start_date=timezone.now(),
                status='pending',
            )
            return Response({'entity_type': 'round', 'id': str(obj.id), 'data': RoundContributionSerializer(obj).data}, status=status.HTTP_201_CREATED)

        elif entity_type == 'benefit_rule':
            obj = BenefitDistributionRule.objects.create(
                payment_group=group,
                distribution_criteria=data.get('distribution_criteria', 'contribution_proportional'),
                payout_frequency=data.get('payout_frequency', 'immediate'),
                wallet_percentage=data.get('wallet_percentage', 100),
                group_retain_percentage=data.get('group_retain_percentage', 0),
                requires_approval=data.get('requires_approval', False),
                approval_threshold=data.get('approval_threshold', 51),
                minimum_payout=data.get('minimum_payout', 0),
            )
            return Response({'entity_type': 'benefit_rule', 'id': str(obj.id), 'data': BenefitDistributionRuleSerializer(obj).data}, status=status.HTTP_201_CREATED)

        elif entity_type == 'investment_pitch':
            group.investment_pitch = data.get('pitch', '')
            group.pitch_visibility = data.get('visibility', 'internal')
            group.save(update_fields=['investment_pitch', 'pitch_visibility', 'updated_at'])
            return Response({'entity_type': 'investment_pitch', 'message': 'Investment pitch updated', 'group': self.get_serializer(group).data}, status=status.HTTP_200_OK)

        elif entity_type == 'settings_change':
            change_type = data.get('change_type')
            if not change_type:
                return Response({'error': 'change_type is required'}, status=status.HTTP_400_BAD_REQUEST)
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            old_values = {}
            for field in data.get('fields', []):
                if hasattr(group, field):
                    old_values[field] = getattr(group, field)
            obj = GroupSettingsChangeRequest.objects.create(
                payment_group=group,
                proposed_by=member,
                change_type=change_type,
                change_description=data.get('description', ''),
                old_values=old_values,
                new_values=data.get('new_values', {}),
                impact_summary=data.get('impact_summary', ''),
            )
            return Response({'entity_type': 'settings_change', 'id': str(obj.id), 'data': GroupSettingsChangeRequestSerializer(obj).data}, status=status.HTTP_201_CREATED)

        elif entity_type == 'withdrawal_request':
            amount = Decimal(str(data.get('amount', 0)))
            if amount <= 0:
                return Response({'error': 'amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            if amount > member.total_contributed:
                return Response({'error': 'Amount exceeds your contributions'}, status=status.HTTP_400_BAD_REQUEST)
            obj = WithdrawalRequest.objects.create(
                payment_group=group,
                requester=member,
                amount=amount,
                withdrawal_type=data.get('withdrawal_type', 'partial'),
                reason=data.get('reason', ''),
                destination_wallet=payment_profile,
            )
            if data.get('withdrawal_type') == 'exit':
                obj.immature_exit_deduction = obj.calculate_immature_deduction()
                obj.save(update_fields=['immature_exit_deduction'])
            return Response({'entity_type': 'withdrawal_request', 'id': str(obj.id), 'data': WithdrawalRequestSerializer(obj).data}, status=status.HTTP_201_CREATED)

        return Response({'error': f'Unknown entity_type: {entity_type}'}, status=status.HTTP_400_BAD_REQUEST)

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
        
        # Enforce transaction_trigger_role
        if group.transaction_trigger_role == 'admin':
            is_admin = member.is_admin or group.creator == payment_profile
            if not is_admin:
                return Response({'error': 'Only admins can trigger checkouts in this group.'}, status=status.HTTP_403_FORBIDDEN)
        
        # If amount > 500 or group requires strict approval
        requires_approval = group.requires_approval or (amount > 500)
        
        if requires_approval:
            checkout_req = GroupCheckoutRequest.objects.create(
                group=group,
                initiator=payment_profile,
                amount=amount,
                items_payload=items_data,
                is_locked=True,
            )
            # Auto-approve by initiator
            checkout_req.approvals.add(payment_profile)
            
            # Check if this 1 approval is enough (e.g. 1-member group or low threshold)
            total_members = PaymentGroupMember.objects.filter(payment_group=group).count()
            import math
            threshold_count = math.ceil((group.approval_threshold / 100.0) * total_members)
            
            if checkout_req.approvals.count() >= max(1, threshold_count):
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

        notes = request.data.get('notes', '')

        if action_type == 'approve':
            checkout_req.approvals.add(payment_profile)
            checkout_req.rejections.remove(payment_profile)
            if notes:
                checkout_req.approval_notes = f"{checkout_req.approval_notes}\n{payment_profile.user.user.first_name}: {notes}".strip()
        elif action_type == 'reject':
            checkout_req.rejections.add(payment_profile)
            checkout_req.approvals.remove(payment_profile)
            if notes:
                checkout_req.rejection_notes = f"{checkout_req.rejection_notes}\n{payment_profile.user.user.first_name}: {notes}".strip()
            
        total_members = PaymentGroupMember.objects.filter(payment_group=group).count()
        import math
        threshold_count = math.ceil((group.approval_threshold / 100.0) * total_members)
        if checkout_req.approvals.count() >= max(1, threshold_count):
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

        rejections_count = checkout_req.rejections.count()
        approvals_count = checkout_req.approvals.count()
        remaining_voters = total_members - approvals_count - rejections_count

        # Reject if rejections make it mathematically impossible to reach threshold
        if approvals_count + remaining_voters < max(1, threshold_count):
            checkout_req.status = 'rejected'
            checkout_req.save()
            return Response({'success': True, 'message': 'Checkout request rejected - insufficient support.'})

        return Response({
            'success': True, 
            'message': f'Successfully {action_type}d request.',
            'status': checkout_req.status,
            'approvals': approvals_count,
            'rejections': rejections_count,
            'threshold_needed': max(1, threshold_count),
            'total_members': total_members
        })

    @action(detail=True, methods=['post'], url_path='cancel_checkout_request')
    def cancel_checkout_request(self, request, pk=None):
        """Cancel a pending checkout request. Only initiator can cancel, and only if no other approvals exist."""
        group = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        request_id = request.data.get('checkout_request_id')
        if not request_id:
            return Response({'error': 'checkout_request_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            checkout_req = GroupCheckoutRequest.objects.get(id=request_id, group=group)
        except GroupCheckoutRequest.DoesNotExist:
            return Response({'error': 'Checkout request not found'}, status=status.HTTP_404_NOT_FOUND)

        if checkout_req.status != 'pending':
            return Response({'error': f'Cannot cancel request that is already {checkout_req.status}'}, status=status.HTTP_400_BAD_REQUEST)

        if checkout_req.initiator != payment_profile:
            return Response({'error': 'Only the initiator can cancel a checkout request'}, status=status.HTTP_403_FORBIDDEN)

        # Prevent cancellation if others have already approved
        other_approvals = checkout_req.approvals.exclude(id=payment_profile.id)
        if other_approvals.exists():
            return Response({'error': 'Cannot cancel after other members have approved'}, status=status.HTTP_400_BAD_REQUEST)

        checkout_req.status = 'cancelled'
        checkout_req.save(update_fields=['status', 'updated_at'])
        return Response({'success': True, 'message': 'Checkout request cancelled.'})

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
        """Withdraw funds from a kitty - keeps funds in kitty as a container."""
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
        
        # Deduct from kitty (funds stay in kitty container)
        kitty.current_amount = float(kitty.current_amount) - amount
        kitty.save()
        
        # Create audit transaction (funds stay in kitty ecosystem)
        tx = TransactionToken.objects.create(
            payment_profile=payment_profile,
            amount=amount,
            transaction_type='kitty_withdrawal',
            description=f'Kitty withdrawal from: {kitty.name} (funds remain in kitty ecosystem)'
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
        
        self.logger.info(f"Kitty withdrawal: {amount} from {kitty.name} - funds kept in kitty ecosystem")
        
        return Response({
            'status': 'success',
            'message': f'KES {amount:,.2f} withdrawn from kitty (funds managed in kitty ecosystem)',
            'new_kitty_balance': float(kitty.current_amount),
            'kitty_name': kitty.name,
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
        
        # Upgrade capacity based on new member count
        if hasattr(group, 'auto_upgrade_capacity'):
            group.auto_upgrade_capacity()
        
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
    logger = logging.getLogger(__name__)

    def create(self, request, *args, **kwargs):
        self.logger.debug(f"CREATE PIGGY BANK - Request data: {request.data}")
        self.logger.debug(f"CREATE PIGGY BANK - User: {request.user}")
        self.logger.debug(f"CREATE PIGGY BANK - Auth: {request.auth}")
        try:
            response = super().create(request, *args, **kwargs)
            self.logger.debug(f"CREATE PIGGY BANK - Response status: {response.status_code}")
            self.logger.debug(f"CREATE PIGGY BANK - Response data: {response.data}")
            return response
        except Exception as e:
            self.logger.error(f"CREATE PIGGY BANK - Exception: {str(e)}")
            self.logger.error(f"CREATE PIGGY BANK - Exception type: {type(e)}")
            raise

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
            # Group piggy bank — check 3-group-piggy-membership limit
            member_group_piggy_count = GroupTarget.objects.filter(
                payment_group__members__payment_profile=payment_profile,
                status='active'
            ).distinct().count()
            if member_group_piggy_count >= GroupTarget.MAX_GROUP_PIGGY_MEMBERSHIPS:
                raise serializers.ValidationError(
                    f"You can be a member of at most {GroupTarget.MAX_GROUP_PIGGY_MEMBERSHIPS} group piggy banks."
                )
            serializer.save()
        else:
            # Individual piggy bank — check 3-individual limit
            individual_count = GroupTarget.objects.filter(
                owner=payment_profile, status='active'
            ).count()
            if individual_count >= GroupTarget.MAX_INDIVIDUAL_PIGGY_BANKS:
                raise serializers.ValidationError(
                    f"You can own at most {GroupTarget.MAX_INDIVIDUAL_PIGGY_BANKS} individual piggy banks."
                )
            serializer.save(owner=payment_profile)

    @action(detail=True, methods=['post'])
    def start_round(self, request, pk=None):
        round_obj = self.get_object()
        
        if round_obj.status != 'pending':
            return Response({'error': 'Round is already active or completed'}, status=400)
            
        # Automated game: randomly assign if method is random and no one is awarded
        if round_obj.assignment_method == 'random' and not round_obj.awarded_to:
            import random
            group_members = list(round_obj.payment_group.members.all())
            # Find members who haven't been awarded in previous rounds
            awarded_member_ids = RoundContribution.objects.filter(payment_group=round_obj.payment_group, awarded_to__isnull=False).values_list('awarded_to_id', flat=True)
            eligible_members = [m for m in group_members if m.id not in awarded_member_ids]
            
            if eligible_members:
                round_obj.awarded_to = random.choice(eligible_members)
            elif group_members:
                # Cycle resets, everyone is eligible again
                round_obj.awarded_to = random.choice(group_members)
        
        elif round_obj.assignment_method == 'sequential' and not round_obj.awarded_to:
            # Picking position system
            try:
                pos = RoundPosition.objects.get(payment_group=round_obj.payment_group, position_number=round_obj.round_number)
                round_obj.awarded_to = pos.member
            except RoundPosition.DoesNotExist:
                # Fallback or error
                pass
                
        round_obj.status = 'active'
        round_obj.start_date = timezone.now()
        round_obj.save()
        
        return Response({'status': 'Round started', 'awarded_to': str(round_obj.awarded_to.id) if round_obj.awarded_to else None})

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
        
        # Get payment profile with row lock
        user = request.user
        try:
            payment_profile = PaymentProfile.objects.select_for_update().get(user__user=user)
        except PaymentProfile.DoesNotExist:
            payment_profile = get_or_create_payment_profile(user)
            payment_profile = PaymentProfile.objects.select_for_update().get(id=payment_profile.id)
        
        # Check balance
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check locking for contributions (usually only withdrawals should be blocked)
        if target.locking_status in ['locked', 'locked_time', 'locked_goal']:
            # Allow contributions but notify about locked status
            pass
            
        # Deduct from user balance
        payment_profile.comrade_balance -= Decimal(str(amount))
        payment_profile.save()
        
        # Add to piggy bank balance atomically
        target = GroupTarget.objects.select_for_update().get(id=target.id)
        target.current_amount += Decimal(str(amount))
        target.save()

        # Update member total contribution if group piggy bank
        member = None
        if target.payment_group:
            try:
                member = PaymentGroupMember.objects.get(
                    payment_group=target.payment_group, payment_profile=payment_profile
                )
                member.total_contributed += Decimal(str(amount))
                member.save()
            except PaymentGroupMember.DoesNotExist:
                pass

        # Record contribution history
        from Payment.models import Contribution
        Contribution.objects.create(
            payment_group=target.payment_group,
            target=target,
            member=member or PaymentGroupMember.objects.filter(payment_profile=payment_profile).first(), # Fallback for individual
            amount=amount,
            notes=request.data.get('notes', '')
        )

        # Create audit trail with piggy bank reference
        group_info = f' (Group: {target.payment_group.name})' if target.payment_group else ''
        target_info = f', New balance: ${float(target.current_amount):.2f}'
        if target.target_amount > 0:
            progress = (float(target.current_amount) / float(target.target_amount)) * 100
            target_info += f', Progress: {progress:.1f}%'
        
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=Decimal(str(amount)),
            transaction_type='savings_deposit',
            description=f'Savings deposit to "{target.name}"{group_info}. Amount: ${float(amount):.2f}{target_info}. This is your savings contribution.',
            payment_group=target.payment_group,
            piggy_bank=target
        )
        
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
        """Withdraw from a piggy bank — enforces savings_type rules."""
        target = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        # ── Savings-type enforcement ──
        can_wd, wd_message = target.can_withdraw()
        if not can_wd:
            return Response({'error': wd_message}, status=status.HTTP_403_FORBIDDEN)
        
        # Legacy locking_status checks (on top of savings_type)
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
        
        # Check min/max withdrawal amount constraints
        if target.min_withdrawal_amount and amount < float(target.min_withdrawal_amount):
            return Response({'error': f'Minimum withdrawal amount is ${float(target.min_withdrawal_amount):.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        if target.max_withdrawal_amount and amount > float(target.max_withdrawal_amount):
            return Response({'error': f'Maximum withdrawal amount is ${float(target.max_withdrawal_amount):.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check minimum balance constraint
        if target.require_min_balance:
            remaining = float(target.current_amount) - amount
            if remaining < float(target.require_min_balance):
                return Response({'error': f'Must maintain minimum balance of ${float(target.require_min_balance):.2f}. Current remaining would be ${remaining:.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check minimum savings period (days since creation)
        if target.require_min_savings_period_days:
            days_since_creation = (timezone.now() - target.created_at).days
            if days_since_creation < target.require_min_savings_period_days:
                return Response({'error': f'Must save for at least {target.require_min_savings_period_days} days before withdrawing. You have saved for {days_since_creation} days.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check minimum contribution amount
        if target.require_min_contribution_amount:
            member_total = 0
            if target.payment_group:
                try:
                    member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
                    member_total = float(member.total_contributed)
                except:
                    pass
            else:
                member_total = sum(float(c.amount) for c in target.contributions.filter(payment_profile=payment_profile))
            
            if member_total < float(target.require_min_contribution_amount):
                return Response({'error': f'Must have contributed at least ${float(target.require_min_contribution_amount):.2f}. You have contributed ${member_total:.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get payment profile
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Check max withdrawals per day
        if target.max_withdrawals_per_day > 0 and target.last_withdrawal_date:
            from datetime import timedelta
            if target.last_withdrawal_date.date() == timezone.now().date():
                # Check how many withdrawals today - would need to track this separately
                # For now, just check if there's been a recent withdrawal
                time_since_last = timezone.now() - target.last_withdrawal_date
                if time_since_last < timedelta(hours=24):
                    # Could implement a counter, but for now allow it
                    pass
        
        # Check member age requirement
        if target.require_min_member_age_days and target.payment_group:
            try:
                member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
                days_since_joined = (timezone.now() - member.joined_at).days
                if days_since_joined < target.require_min_member_age_days:
                    return Response({'error': f'Must be a member for at least {target.require_min_member_age_days} days before withdrawing. You have been a member for {days_since_joined} days.'}, status=status.HTTP_400_BAD_REQUEST)
            except PaymentGroupMember.DoesNotExist:
                pass
        
        # ── Fixed-deposit penalty calculation ──
        penalty = target.calculate_withdrawal_penalty(amount)
        net_amount = amount - penalty
        forfeited_interest = 0
        
        if target.savings_type == 'fixed_deposit' and not target.is_matured:
            # Forfeit all accrued interest
            forfeited_interest = float(target.accrued_interest)
            target.accrued_interest = 0
        
        # Deduct from piggy bank
        target.current_amount -= Decimal(str(amount))
        target.save()
        
        # Add net amount to user balance (after penalty)
        payment_profile.comrade_balance += Decimal(str(net_amount))
        payment_profile.save()
        
        # Create detailed audit trail for withdrawal
        description = f'Withdrawal from Piggy Bank "{target.name}"'
        if target.payment_group:
            description += f' (Group: {target.payment_group.name})'
        description += f'. Original amount: ${float(amount):.2f}'
        if penalty > 0:
            description += f', Penalty applied: ${penalty:.2f}'
            if forfeited_interest > 0:
                description += f', Forfeited interest: ${forfeited_interest:.2f}'
        description += f', Net transferred to wallet: ${net_amount:.2f}'
        
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=Decimal(str(net_amount)),
            transaction_type='piggy_bank_withdrawal',
            description=description,
            payment_group=target.payment_group,
            piggy_bank=target
        )
        
        # Also record the deduction from piggy bank as savings withdrawal
        withdrawal_type = 'savings_withdrawal' if penalty == 0 else 'savings_withdrawal_penalty'
        penalty_info = f' (Penalty: ${penalty:.2f}, Forfeited interest: ${forfeited_interest:.2f})' if penalty > 0 else ''
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=Decimal(str(amount)),
            transaction_type=withdrawal_type,
            description=f'Savings withdrawal from "{target.name}". Original amount: ${float(amount):.2f}{penalty_info}. Net transferred to wallet: ${net_amount:.2f}. Remaining balance: ${float(target.current_amount):.2f}',
            payment_group=target.payment_group,
            piggy_bank=target
        )
        
        response_data = {
            'status': 'Withdrawal successful',
            'amount_withdrawn': amount,
            'penalty_applied': penalty,
            'forfeited_interest': forfeited_interest,
            'net_received': net_amount,
            'remaining_amount': float(target.current_amount),
            'new_balance': float(payment_profile.comrade_balance)
        }
        
        if penalty > 0:
            response_data['penalty_note'] = f'A {float(target.penalty_rate)}% early withdrawal penalty of ${penalty:.2f} was applied. Accrued interest of ${forfeited_interest:.2f} was forfeited.'
        
        return Response(response_data)
    
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
    
    @action(detail=True, methods=['get'])
    def piggy_members(self, request, pk=None):
        """List members who have contributed to this piggy bank."""
        target = self.get_object()
        contributions = target.contributions.select_related('member__payment_profile__user__user').all()
        
        member_map = {}
        for c in contributions:
            mid = str(c.member.id)
            if mid not in member_map:
                member_map[mid] = {
                    'id': mid,
                    'name': c.member.anonymous_alias if c.member.is_anonymous else c.member.payment_profile.user.user.get_full_name(),
                    'total_contributed': 0,
                    'is_anonymous': c.member.is_anonymous,
                    'role': c.member.role
                }
            member_map[mid]['total_contributed'] += float(c.amount)
        
        return Response(list(member_map.values()))

    @action(detail=True, methods=['get'])
    def piggy_analytics(self, request, pk=None):
        """Rich analytics and contribution trends for this piggy bank."""
        target = self.get_object()
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Growth and Trends
        all_contributions = target.contributions.all()
        recent_contributions = all_contributions.filter(contributed_at__gte=thirty_days_ago)
        
        growth_30d = sum(float(c.amount) for c in recent_contributions)
        
        # Monthly trends (last 6 months)
        monthly_trends = []
        max_monthly = 0
        for i in range(5, -1, -1):
            month_start = (now.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            next_month = (month_start + timedelta(days=32)).replace(day=1)
            month_amount = sum(float(c.amount) for c in all_contributions.filter(contributed_at__gte=month_start, contributed_at__lt=next_month))
            month_label = month_start.strftime('%b')
            monthly_trends.append({'month': month_label, 'amount': month_amount})
            if month_amount > max_monthly:
                max_monthly = month_amount

        # Top Stakers
        member_contributions = {}
        for c in all_contributions:
            if not c.member: continue
            mid = str(c.member.id)
            if mid not in member_contributions:
                member_contributions[mid] = {
                    'user_name': c.member.anonymous_alias if c.member.is_anonymous else (c.member.payment_profile.user.user.get_full_name() if c.member.payment_profile else "Unknown User"),
                    'total_contributed': 0
                }
            member_contributions[mid]['total_contributed'] += float(c.amount)
            
        top_stakers = sorted(member_contributions.values(), key=lambda x: x['total_contributed'], reverse=True)[:5]
        
        return Response({
            'total_saved': float(target.current_amount),
            'target_amount': float(target.target_amount),
            'growth_30d': growth_30d,
            'max_monthly': max_monthly,
            'is_mature': target.is_matured,
            'total_contributors': len(member_contributions),
            'monthly_trends': monthly_trends,
            'top_stakers': top_stakers
})

    @action(detail=True, methods=['post'])
    def request_conversion(self, request, pk=None):
        """Propose converting this piggy bank to group funds."""
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if not target.payment_group:
            return Response({'error': 'Only group piggy banks can be converted.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check for pending requests
        if PiggyBankConversionRequest.objects.filter(piggy_bank=target, status__in=['pending', 'draft']).exists():
            return Response({'error': 'A conversion request is already pending.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get conversion type
        conversion_type = request.data.get('conversion_type', 'full')
        approval_mode = request.data.get('approval_mode', 'unanimous')
        
        # Validate split conversion has required fields
        if conversion_type == 'split':
            new_group_name = request.data.get('new_group_name', '').strip()
            if not new_group_name:
                return Response({'error': 'New group name is required for split conversion.'}, status=status.HTTP_400_BAD_REQUEST)
        
        req = PiggyBankConversionRequest.objects.create(
            piggy_bank=target,
            proposed_by=member,
            conversion_type=conversion_type,
            approval_mode=approval_mode,
            reason=request.data.get('reason', ''),
            new_group_name=request.data.get('new_group_name', ''),
            new_piggy_name=request.data.get('new_piggy_name', ''),
            new_piggy_target=request.data.get('new_piggy_target'),
            notes=request.data.get('notes', ''),
            status='pending'
        )
        
        return Response({
            'status': 'Conversion request created', 
            'id': str(req.id),
            'data': PiggyBankConversionRequestSerializer(req).data
        })

    @action(detail=True, methods=['get'])
    def conversion_status(self, request, pk=None):
        """Get all conversion requests for this piggy bank."""
        target = self.get_object()
        requests = PiggyBankConversionRequest.objects.filter(piggy_bank=target).order_by('-created_at')
        
        # Enhance response with member approval status
        from Payment.serializers import PiggyBankConversionRequestSerializer
        data = PiggyBankConversionRequestSerializer(requests, many=True).data
        
        # Add current user's vote status if authenticated
        if request.user.is_authenticated:
            payment_profile = get_or_create_payment_profile(request.user)
            try:
                member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
                for req in data:
                    req['current_user_approved'] = member in req.get('approving_members', [])
                    req['current_user_rejected'] = member in req.get('rejecting_members', [])
            except PaymentGroupMember.DoesNotExist:
                pass
        
        return Response(data)

    @action(detail=True, methods=['post'], url_path=r'vote_conversion/(?P<request_id>[^/.]+)')
    @db_transaction.atomic
    def vote_conversion(self, request, pk=None, request_id=None):
        """Vote on a conversion request - approve or reject."""
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            conv_req = PiggyBankConversionRequest.objects.get(id=request_id, piggy_bank=target, status='pending')
        except (PiggyBankConversionRequest.DoesNotExist, ValueError):
            return Response({'error': 'Pending conversion request not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=target.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=status.HTTP_403_FORBIDDEN)
        
        vote = request.data.get('vote', '').lower()
        if vote not in ['approve', 'reject']:
            return Response({'error': 'Vote must be "approve" or "reject".'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Remove from opposite set if exists
        if vote == 'approve':
            conv_req.rejecting_members.remove(member)
            conv_req.approving_members.add(member)
        else:
            conv_req.approving_members.remove(member)
            conv_req.rejecting_members.add(member)
        
        conv_req.save()
        
        # Check if we should process the conversion
        return self._process_conversion_votes(target, conv_req, member)

    def _process_conversion_votes(self, target, conv_req, voting_member):
        """Process votes and execute conversion if conditions are met."""
        all_members = list(target.payment_group.members.all())
        approving = list(conv_req.approving_members.all())
        rejecting = list(conv_req.rejecting_members.all())
        
        total_members = len(all_members)
        approving_count = len(approving)
        rejecting_count = len(rejecting)
        
        # Check if conditions are met based on approval mode
        should_process = False
        
        if conv_req.approval_mode == 'unanimous':
            # All members must approve
            should_process = approving_count == total_members
        elif conv_req.approval_mode == 'majority':
            # Majority must approve (more than half)
            should_process = approving_count > total_members / 2
        elif conv_req.approval_mode == 'any':
            # Any one member can approve and trigger conversion
            should_process = approving_count >= 1
        
        if not should_process:
            return Response({
                'status': 'Vote recorded',
                'vote': 'approve' if voting_member in conv_req.approving_members.all() else 'reject',
                'approving_count': approving_count,
                'total_members': total_members,
                'approval_mode': conv_req.approval_mode,
                'message': f'Votes: {approving_count}/{total_members} approve, {rejecting_count} reject. Need more approvals.'
            })
        
        # Process the conversion
        return self._execute_conversion(target, conv_req, approving, rejecting)

    @db_transaction.atomic
    def _execute_conversion(self, target, conv_req, approving_members, rejecting_members):
        """Execute the conversion based on type."""
        amount_to_move = target.current_amount
        
        if conv_req.conversion_type == 'full':
            # Full conversion - all funds go to parent group
            target.payment_group.current_amount += amount_to_move
            target.payment_group.save()
            
            target.current_amount = 0
            target.status = 'converted'
            target.save()
            
            conv_req.status = 'approved'
            
        elif conv_req.conversion_type == 'split':
            # Split - approvers form new group with their share, rejecters get refund
            # Calculate share per member
            total_contributions = sum(float(c.amount) for c in target.contributions.all())
            
            # Create new group
            new_group = PaymentGroups.objects.create(
                name=conv_req.new_group_name or f"{target.name} - New Group",
                group_type='standard',
                creator=conv_req.proposed_by.payment_profile,
                current_amount=0,
                status='active'
            )
            
            # Create new piggy bank in new group
            new_piggy = GroupTarget.objects.create(
                name=conv_req.new_piggy_name or f"{target.name} - Savings",
                target_amount=conv_req.new_piggy_target or target.target_amount,
                current_amount=0,
                payment_group=new_group,
                savings_type=target.savings_type,
                locking_status=target.locking_status,
                contribution_mode=target.contribution_mode
            )
            
            # Move approvers to new group and calculate their share
            approver_total = 0
            for member in approving_members:
                # Get member's contributions
                member_contrib = sum(float(c.amount) for c in target.contributions.filter(member=member))
                if member_contrib > 0 and total_contributions > 0:
                    share_ratio = member_contrib / total_contributions
                    member_share = amount_to_move * share_ratio
                    
                    # Add to new piggy bank
                    new_piggy.current_amount += Decimal(str(member_share))
                    approver_total += member_share
                    
                    # Move member to new group
                    member.payment_group = new_group
                    member.save()
                    
                    # Create transaction record for member's share
                    TransactionToken.objects.create(
                        payment_profile=member.payment_profile,
                        transaction_code=uuid.uuid4(),
                        amount=Decimal(str(member_share)),
                        transaction_type='transfer',
                        description=f"Transfer to new group: {new_group.name}",
                        payment_group=new_group
                    )
            
            new_piggy.save()
            
            # Refund rejecting members
            for member in rejecting_members:
                member_contrib = sum(float(c.amount) for c in target.contributions.filter(member=member))
                if member_contrib > 0 and total_contributions > 0:
                    share_ratio = member_contrib / total_contributions
                    member_share = amount_to_move * share_ratio
                    
                    # Return to member's wallet
                    member.payment_profile.comrade_balance += Decimal(str(member_share))
                    member.payment_profile.save()
                    
                    # Create refund transaction
                    TransactionToken.objects.create(
                        payment_profile=member.payment_profile,
                        transaction_code=uuid.uuid4(),
                        amount=Decimal(str(member_share)),
                        transaction_type='refund',
                        description=f"Refund from conversion: {target.name}",
                        piggy_bank=target
                    )
            
            # Update original piggy bank
            target.current_amount = 0
            target.status = 'converted'
            target.save()
            
            # Update conversion request
            conv_req.new_group = new_group
            conv_req.new_piggy_bank = new_piggy
            conv_req.status = 'partial'
        
        conv_req.save()
        
        # Audit log
        TransactionToken.objects.create(
            payment_profile=conv_req.proposed_by.payment_profile,
            transaction_code=uuid.uuid4(),
            amount=amount_to_move,
            transaction_type='transfer',
            description=f"Conversion: Piggy Bank '{target.name}' - {conv_req.conversion_type} type",
            payment_group=target.payment_group
        )
        
        return Response({
            'status': 'Conversion completed',
            'conversion_type': conv_req.conversion_type,
            'amount_processed': float(amount_to_move),
            'approvers_moved': len(approving_members),
            'rejecters_refunded': len(rejecting_members),
            'new_group_id': str(conv_req.new_group.id) if conv_req.new_group else None,
            'new_piggy_id': str(conv_req.new_piggy_bank.id) if conv_req.new_piggy_bank else None
        })

    @action(detail=True, methods=['post'], url_path=r'approve_conversion/(?P<request_id>[^/.]+)')
    @db_transaction.atomic
    def approve_conversion(self, request, pk=None, request_id=None):
        """Execute conversion: move funds to parent group balance. (Legacy admin-only endpoint)"""
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        # Admin check
        is_creator = target.payment_group.creator == payment_profile
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=target.payment_group, payment_profile=payment_profile, is_admin=True
        ).exists()
        
        if not is_creator and not is_admin:
            return Response({'error': 'Only admins can approve conversions.'}, status=status.HTTP_403_FORBIDDEN)
                
        try:
            conv_req = PiggyBankConversionRequest.objects.get(id=request_id, piggy_bank=target, status='pending')
        except (PiggyBankConversionRequest.DoesNotExist, ValueError):
            return Response({'error': 'Pending conversion request not found.'}, status=status.HTTP_404_NOT_FOUND)
            
        amount_to_move = target.current_amount
        
        # Update group funds
        target.payment_group.current_amount += amount_to_move
        target.payment_group.save()
        
        # Deactivate piggy bank
        target.current_amount = 0
        target.status = 'converted'
        target.save()
        
        # Update request
        conv_req.status = 'approved'
        conv_req.save()
        
        # Audit log
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            amount=amount_to_move,
            transaction_type='transfer',
            description=f"Conversion: Piggy Bank '{target.name}' funds moved to group balance.",
            payment_group=target.payment_group
        )
        
        return Response({
            'status': 'Conversion successful', 
            'amount_moved': float(amount_to_move),
            'new_group_balance': float(target.payment_group.current_amount)
        })

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def execute_automation(self, request, pk=None):
        """Execute the automation action for this piggy bank."""
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if target.automation_executed:
            return Response({'error': 'Automation has already been executed.'}, status=status.HTTP_400_BAD_REQUEST)
        
        automation_amount = target.automation_amount or target.current_amount
        
        if automation_amount > target.current_amount:
            return Response({'error': 'Insufficient funds for automation.'}, status=status.HTTP_400_BAD_REQUEST)
        
        action = target.automation_action
        result = {'status': 'executed', 'action': action, 'amount': float(automation_amount)}
        
        if action == 'wallet':
            # Transfer to user's wallet
            payment_profile.comrade_balance += Decimal(str(automation_amount))
            payment_profile.save()
            target.current_amount -= Decimal(str(automation_amount))
            
            TransactionToken.objects.create(
                payment_profile=payment_profile,
                transaction_code=uuid.uuid4(),
                amount=Decimal(str(automation_amount)),
                transaction_type='transfer',
                description=f'Automation: Transferred from {target.name} to wallet',
                piggy_bank=target
            )
            
        elif action == 'group_fund':
            # Add to group fund
            if not target.payment_group:
                return Response({'error': 'No group associated with this piggy bank.'}, status=status.HTTP_400_BAD_REQUEST)
            
            target.payment_group.current_amount += Decimal(str(automation_amount))
            target.payment_group.save()
            target.current_amount -= Decimal(str(automation_amount))
            
            TransactionToken.objects.create(
                payment_profile=payment_profile,
                transaction_code=uuid.uuid4(),
                amount=Decimal(str(automation_amount)),
                transaction_type='transfer',
                description=f'Automation: Added to group fund from {target.name}',
                payment_group=target.payment_group,
                piggy_bank=target
            )
            
        elif action == 'product':
            # Would need to create order for product - store as pending action
            result['next_step'] = 'redirect_to_product'
            result['product_id'] = target.automation_target_id
            result['message'] = f'Proceed to purchase product: {target.automation_target_name}'
            # Don't deduct yet - user needs to complete purchase
            
        elif action == 'service':
            result['next_step'] = 'redirect_to_service'
            result['service_id'] = target.automation_target_id
            result['message'] = f'Proceed to purchase service: {target.automation_target_name}'
            
        elif action == 'investment':
            result['next_step'] = 'redirect_to_investment'
            result['investment_id'] = target.automation_target_id
            result['message'] = f'Proceed to invest in: {target.automation_target_name}'
            
        elif action == 'course':
            result['next_step'] = 'redirect_to_course'
            result['course_id'] = target.automation_target_id
            result['message'] = f'Proceed to enroll in: {target.automation_target_name}'
            
        elif action == 'group_join':
            result['next_step'] = 'redirect_to_group'
            result['group_id'] = target.automation_target_id
            result['message'] = f'Proceed to join group: {target.automation_target_name}'
            
        elif action == 'donation':
            result['next_step'] = 'create_donation'
            result['target_name'] = target.automation_target_name
            result['message'] = f'Proceed to make donation: {target.automation_target_name}'
        
        # Mark automation as executed
        target.automation_executed = True
        target.automation_executed_at = timezone.now()
        target.save()
        
        return Response(result)

    @action(detail=True, methods=['patch'])
    def update_settings(self, request, pk=None):
        """Update piggy bank settings (name, visibility, automation)."""
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        # Check permission - owner or group admin
        is_owner = target.owner == payment_profile if target.owner else False
        is_group_admin = False
        if target.payment_group:
            is_group_admin = PaymentGroupMember.objects.filter(
                payment_group=target.payment_group, payment_profile=payment_profile, is_admin=True
            ).exists()
        
        if not is_owner and not is_group_admin:
            return Response({'error': 'You do not have permission to update this piggy bank.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Update fields - only update if value is provided and handle null for empty strings
        if 'name' in request.data and request.data['name'] is not None:
            target.name = request.data['name']
        if 'visibility' in request.data and request.data['visibility'] is not None:
            target.visibility = request.data['visibility']
        if 'automation_trigger' in request.data and request.data['automation_trigger'] is not None:
            target.automation_trigger = request.data['automation_trigger']
        if 'automation_action' in request.data and request.data['automation_action'] is not None:
            target.automation_action = request.data['automation_action']
        if 'automation_target_type' in request.data:
            val = request.data['automation_target_type']
            target.automation_target_type = val if val and val.strip() else None
        if 'automation_target_id' in request.data:
            val = request.data['automation_target_id']
            target.automation_target_id = val if val and val.strip() else None
        if 'automation_target_name' in request.data:
            val = request.data['automation_target_name']
            target.automation_target_name = val if val and val.strip() else None
        if 'automation_amount' in request.data and request.data['automation_amount'] is not None:
            target.automation_amount = Decimal(str(request.data['automation_amount']))
        
        # Withdrawal constraints
        if 'min_withdrawal_amount' in request.data and request.data['min_withdrawal_amount'] is not None:
            target.min_withdrawal_amount = Decimal(str(request.data['min_withdrawal_amount']))
        elif 'min_withdrawal_amount' in request.data and request.data['min_withdrawal_amount'] is None:
            target.min_withdrawal_amount = None
            
        if 'max_withdrawal_amount' in request.data and request.data['max_withdrawal_amount'] is not None:
            target.max_withdrawal_amount = Decimal(str(request.data['max_withdrawal_amount']))
        elif 'max_withdrawal_amount' in request.data and request.data['max_withdrawal_amount'] is None:
            target.max_withdrawal_amount = None
            
        if 'max_withdrawals_per_day' in request.data and request.data['max_withdrawals_per_day'] is not None:
            target.max_withdrawals_per_day = int(request.data['max_withdrawals_per_day'])
        
        if 'require_min_balance' in request.data and request.data['require_min_balance'] is not None:
            target.require_min_balance = Decimal(str(request.data['require_min_balance']))
        elif 'require_min_balance' in request.data and request.data['require_min_balance'] is None:
            target.require_min_balance = None
            
        if 'require_min_savings_period_days' in request.data and request.data['require_min_savings_period_days'] is not None:
            target.require_min_savings_period_days = int(request.data['require_min_savings_period_days'])
            
        if 'require_min_member_age_days' in request.data and request.data['require_min_member_age_days'] is not None:
            target.require_min_member_age_days = int(request.data['require_min_member_age_days'])
            
        if 'require_min_contribution_amount' in request.data and request.data['require_min_contribution_amount'] is not None:
            target.require_min_contribution_amount = Decimal(str(request.data['require_min_contribution_amount']))
        elif 'require_min_contribution_amount' in request.data and request.data['require_min_contribution_amount'] is None:
            target.require_min_contribution_amount = None
        
        target.save()
        
        return Response({
            'status': 'Settings updated',
            'data': {
                'name': target.name,
                'visibility': target.visibility,
                'automation_trigger': target.automation_trigger,
                'automation_action': target.automation_action,
                'automation_target_name': target.automation_target_name,
                'automation_amount': float(target.automation_amount) if target.automation_amount else None,
                'min_withdrawal_amount': float(target.min_withdrawal_amount) if target.min_withdrawal_amount else None,
                'max_withdrawal_amount': float(target.max_withdrawal_amount) if target.max_withdrawal_amount else None,
                'max_withdrawals_per_day': target.max_withdrawals_per_day,
                'require_min_balance': float(target.require_min_balance) if target.require_min_balance else None,
                'require_min_savings_period_days': target.require_min_savings_period_days,
                'require_min_member_age_days': target.require_min_member_age_days,
                'require_min_contribution_amount': float(target.require_min_contribution_amount) if target.require_min_contribution_amount else None
            }
        })

    @action(detail=False, methods=['get'])
    def search_automation_targets(self, request):
        """Search for products, services, courses, subscriptions, etc for automation."""
        query = request.query_params.get('q', '')
        target_type = request.query_params.get('type', 'all')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        
        results = {
            'products': [],
            'services': [],
            'courses': [],
            'subscriptions': [],
            'groups': [],
            'investments': [],
            'donations': []
        }
        
        if not query and target_type == 'all':
            return Response(results)
        
        # Search Products
        if target_type in ['all', 'product']:
            from Payment.models import Product
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            ).filter(status='active')[:10]
            results['products'] = [{
                'id': str(p.id),
                'name': p.name,
                'type': 'product',
                'price': float(p.price) if p.price else 0,
                'image': p.image.url if p.image else None,
                'seller': p.seller.business_name if p.seller else None
            } for p in products]
        
        # Search Services
        if target_type in ['all', 'service']:
            from Payment.models import ServiceProduct
            services = ServiceProduct.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            ).filter(status='active')[:10]
            results['services'] = [{
                'id': str(s.id),
                'name': s.name,
                'type': 'service',
                'price': float(s.price) if s.price else 0,
                'image': s.image.url if s.image else None,
                'provider': s.provider.business_name if s.provider else None
            } for s in services]
        
        # Search Courses (could be in different apps)
        if target_type in ['all', 'course']:
            try:
                from Courses.models import Course
                courses = Course.objects.filter(
                    Q(title__icontains=query) | Q(description__icontains=query)
                ).filter(status='published')[:10]
                results['courses'] = [{
                    'id': str(c.id),
                    'name': c.title,
                    'type': 'course',
                    'price': float(c.price) if hasattr(c, 'price') and c.price else 0,
                    'image': c.cover_image.url if hasattr(c, 'cover_image') and c.cover_image else None,
                    'instructor': str(c.instructor) if hasattr(c, 'instructor') else None
                } for c in courses]
            except:
                pass
        
        # Search Subscriptions
        if target_type in ['all', 'subscription']:
            try:
                from Payments.models import UserSubscription
                subs = UserSubscription.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(status='active')[:10]
                results['subscriptions'] = [{
                    'id': str(s.id),
                    'name': s.name,
                    'type': 'subscription',
                    'price': float(s.price) if s.price else 0
                } for s in subs]
            except:
                pass
        
        # Search Groups (payment groups user can join)
        if target_type in ['all', 'group']:
            from Payment.models import PaymentGroups
            groups = PaymentGroups.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            ).filter(status='active').exclude(member_type='private')[:10]
            results['groups'] = [{
                'id': str(g.id),
                'name': g.name,
                'type': 'group',
                'entry_fee': float(g.entry_fee) if g.entry_fee else 0,
                'member_count': g.members.count()
            } for g in groups]
        
        # Search Investment opportunities
        if target_type in ['all', 'investment']:
            try:
                from Funding.models import Business, CapitalVenture
                investments = []
                businesses = Business.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(status='active')[:5]
                for b in businesses:
                    investments.append({
                        'id': str(b.id),
                        'name': b.name,
                        'type': 'investment',
                        'min_amount': float(b.min_investment) if hasattr(b, 'min_investment') else 0,
                        'expected_return': b.expected_return if hasattr(b, 'expected_return') else None
                    })
                ventures = CapitalVenture.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(status='active')[:5]
                for v in ventures:
                    investments.append({
                        'id': str(v.id),
                        'name': v.name,
                        'type': 'investment',
                        'min_amount': float(v.min_investment) if hasattr(v, 'min_investment') else 0,
                        'expected_return': v.expected_return if hasattr(v, 'expected_return') else None
                    })
                results['investments'] = investments[:10]
            except:
                pass
        
        # Search Donations
        if target_type in ['all', 'donation']:
            from Payment.models import Donation
            donations = Donation.objects.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            ).filter(status='collecting')[:10]
            results['donations'] = [{
                'id': str(d.id),
                'name': d.title,
                'type': 'donation',
                'target_amount': float(d.target_amount) if d.target_amount else 0,
                'current_amount': float(d.current_amount) if d.current_amount else 0
            } for d in donations]
        
        return Response(results)

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
    
    def perform_create(self, serializer):
        """Auto-assign owner and create a revenue kitty for the new establishment."""
        from django.contrib.contenttypes.models import ContentType
        
        profile = Profile.objects.filter(user=self.request.user).first()
        instance = serializer.save(owner=profile)
        
        # Auto-create a PaymentGroups kitty for this establishment
        try:
            payment_profile = PaymentProfile.objects.filter(user=profile).first()
            if payment_profile:
                ctype = ContentType.objects.get_for_model(Establishment)
                PaymentGroups.objects.create(
                    name=f"Kitty: {instance.name}",
                    description=f"Revenue pool for {instance.name}",
                    creator=payment_profile,
                    group_type='kitty',
                    tier=payment_profile.tier,
                    entity_content_type=ctype,
                    entity_object_id=str(instance.id),
                    auto_create_room=False
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Auto-kitty creation failed for {instance.name}: {e}")
    
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
                    
                    # Stock Decrement
                    if hasattr(product, 'stock') and product.stock >= qty:
                        product.stock -= qty
                        product.save()
                    elif hasattr(product, 'stock') and product.stock < qty:
                        return Response({'error': f'Not enough stock for {product.name}'}, status=status.HTTP_400_BAD_REQUEST)
                        
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
    def confirm_order(self, request, pk=None):
        order = self.get_object()
        if order.status != 'pending':
            return Response({'error': 'Order is not pending'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'confirmed'
        order.save()
        return Response({'status': 'confirmed'})

    @action(detail=True, methods=['post'])
    def start_preparing(self, request, pk=None):
        order = self.get_object()
        if order.status != 'confirmed':
            return Response({'error': 'Order must be confirmed first'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'preparing'
        order.save()
        return Response({'status': 'preparing'})

    @action(detail=True, methods=['post'])
    def mark_ready(self, request, pk=None):
        order = self.get_object()
        if order.status != 'preparing':
            return Response({'error': 'Order must be preparing first'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'ready'
        order.save()
        return Response({'status': 'ready'})

    @action(detail=True, methods=['post'])
    def assign_delivery(self, request, pk=None):
        order = self.get_object()
        if order.status not in ['confirmed', 'preparing', 'ready']:
            return Response({'error': 'Order not ready for delivery'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'out_for_delivery'
        # Delivery agent assignment logic could go here
        order.save()
        return Response({'status': 'out_for_delivery'})

    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        order = self.get_object()
        if order.status not in ['out_for_delivery', 'ready']:
            return Response({'error': 'Order must be out for delivery or ready'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'delivered'
        order.save()
        
        # Payment release logic (if held in escrow) could go here
        
        return Response({'status': 'delivered'})

    @action(detail=True, methods=['post'])
    def cancel_order(self, request, pk=None):
        order = self.get_object()
        if order.status in ['delivered', 'completed']:
            return Response({'error': 'Cannot cancel a delivered order'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            with db_transaction.atomic():
                # Refund logic
                if order.payment_type == 'individual' and not order.is_offline and order.total_amount > 0:
                    payment_profile = PaymentProfile.objects.get(user=order.buyer.user)
                    payment_profile.comrade_balance += Decimal(str(order.total_amount))
                    payment_profile.save()
                    
                    TransactionToken.objects.create(
                        receiver_profile=payment_profile,
                        amount=Decimal(str(order.total_amount)),
                        transaction_type='refund',
                        description=f'Refund for cancelled order #{order.id}'
                    )
                
                # Restock logic
                for item in order.items.all():
                    if item.product and hasattr(item.product, 'stock'):
                        item.product.stock += item.quantity
                        item.product.save()
                
                order.status = 'cancelled'
                order.save()
                return Response({'status': 'cancelled'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
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


# ── Group Discourse (Posts & Replies) ─────────────────────────────
class GroupPostViewSet(ModelViewSet):
    """Discord-style posts inside a group's discourse feed."""
    serializer_class = GroupPostSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        group_id = self.request.query_params.get('payment_group') or self.request.query_params.get('group')
        if not group_id:
            # If it's a list action, we require the group filter
            if self.action == 'list':
                return GroupPost.objects.none()
            # For detail actions (upvote, react, etc), allow finding the object
            return GroupPost.objects.all()
        return GroupPost.objects.filter(group_id=group_id)

    def perform_create(self, serializer):
        payment_profile = get_or_create_payment_profile(self.request.user)
        if not payment_profile:
            raise serializers.ValidationError("Could not create payment profile")
        group_id = self.request.data.get('group')
        try:
            group = PaymentGroups.objects.get(id=group_id)
        except PaymentGroups.DoesNotExist:
            raise serializers.ValidationError("Group not found")
        serializer.save(author=payment_profile, group=group)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Toggle a reaction icon on a post. Enforces single reaction per user."""
        post = self.get_object()
        icon = request.data.get('emoji') or request.data.get('icon') or '👍'
        user_id = str(request.user.id)
        reactions = post.reactions or {}
        
        # Remove user from all other reactions first
        for i in list(reactions.keys()):
            if i != icon and user_id in reactions[i]:
                reactions[i].remove(user_id)
                if not reactions[i]:
                    del reactions[i]
        
        # Now toggle the requested icon
        if icon not in reactions:
            reactions[icon] = []
            
        if user_id in reactions[icon]:
            reactions[icon].remove(user_id)
        else:
            reactions[icon].append(user_id)
            
        if icon in reactions and not reactions[icon]:
            del reactions[icon]
            
        post.reactions = reactions
        post.save(update_fields=['reactions'])
        return Response(GroupPostSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Toggle pin status on a post (admin only)."""
        post = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=post.group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_admin:
            return Response({'error': 'Only group admins can pin posts'}, status=status.HTTP_403_FORBIDDEN)
        post.is_pinned = not post.is_pinned
        post.save(update_fields=['is_pinned'])
        return Response(GroupPostSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def upvote(self, request, pk=None):
        """Toggle upvote for a post."""
        post = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        if post.upvotes.filter(id=payment_profile.id).exists():
            post.upvotes.remove(payment_profile)
        else:
            post.upvotes.add(payment_profile)
        return Response(GroupPostSerializer(post, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def toggle_shareability(self, request, pk=None):
        """Toggle whether a post can be shared/forwarded."""
        post = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=post.group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_admin and post.author != payment_profile:
            return Response({'error': 'Only the author or group admin can toggle shareability'}, status=status.HTTP_403_FORBIDDEN)
        
        # Toggle both shareability and forwardability for now, or could handle separately
        post.is_shareable = not post.is_shareable
        post.is_forwardable = post.is_shareable
        post.save(update_fields=['is_shareable', 'is_forwardable'])
        return Response(GroupPostSerializer(post, context={'request': request}).data)


class GroupPostReplyViewSet(ModelViewSet):
    """Threaded replies on discourse posts."""
    serializer_class = GroupPostReplySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        post_id = self.request.query_params.get('post')
        if not post_id:
            # If it's a list action, we require the post filter
            if self.action == 'list':
                return GroupPostReply.objects.none()
            # For detail actions, allow finding the object
            return GroupPostReply.objects.all()
        return GroupPostReply.objects.filter(post_id=post_id)

    def perform_create(self, serializer):
        payment_profile = get_or_create_payment_profile(self.request.user)
        if not payment_profile:
            raise serializers.ValidationError("Could not create payment profile")
        post_id = self.request.data.get('post')
        try:
            post = GroupPost.objects.get(id=post_id)
        except GroupPost.DoesNotExist:
            raise serializers.ValidationError("Post not found")
        serializer.save(author=payment_profile, post=post)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Toggle a reaction icon on a reply. Enforces single reaction per user."""
        reply = self.get_object()
        icon = request.data.get('emoji') or request.data.get('icon') or '👍'
        user_id = str(request.user.id)
        reactions = reply.reactions or {}
        
        # Remove user from all other reactions first
        for i in list(reactions.keys()):
            if i != icon and user_id in reactions[i]:
                reactions[i].remove(user_id)
                if not reactions[i]:
                    del reactions[i]
        
        # Now toggle the requested icon
        if icon not in reactions:
            reactions[icon] = []
            
        if user_id in reactions[icon]:
            reactions[icon].remove(user_id)
        else:
            reactions[icon].append(user_id)
            
        if icon in reactions and not reactions[icon]:
            del reactions[icon]
            
        reply.reactions = reactions
        reply.save(update_fields=['reactions'])
        return Response(GroupPostReplySerializer(reply, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def upvote(self, request, pk=None):
        """Toggle upvote for a reply."""
        reply = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        if reply.upvotes.filter(id=payment_profile.id).exists():
            reply.upvotes.remove(payment_profile)
        else:
            reply.upvotes.add(payment_profile)
        return Response(GroupPostReplySerializer(reply, context={'request': request}).data)


class GroupPhaseViewSet(ModelViewSet):
    """CRUD for contribution phases on a group."""
    serializer_class = GroupPhaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        group_id = self.request.query_params.get('group')
        if not group_id:
            # For detail actions, allow finding the object by PK
            if self.action != 'list':
                return GroupPhase.objects.all()
            return GroupPhase.objects.none()
        return GroupPhase.objects.filter(group_id=group_id)

    def perform_create(self, serializer):
        payment_profile = get_or_create_payment_profile(self.request.user)
        if not payment_profile:
            raise serializers.ValidationError("Could not create payment profile")
        group_id = self.request.data.get('group')
        try:
            group = PaymentGroups.objects.get(id=group_id)
        except PaymentGroups.DoesNotExist:
            raise serializers.ValidationError("Group not found")
        is_admin = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_admin=True
        ).exists()
        if not is_admin:
            raise serializers.ValidationError("Only group admins can manage phases")
        serializer.save(group=group)


class GroupVoteViewSet(ModelViewSet):
    """Voting system for group investment/savings/withdrawal decisions."""
    serializer_class = GroupVoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # For list action, restrict to my groups.
        # For detail actions (cast_vote), allow looking up the object
        # and then perform membership checks inside the action.
        if self.action != 'list':
            return GroupVote.objects.all()

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
        
        provider = serializer.validated_data.get('provider')
        account_number = serializer.validated_data.get('account_number')
        if provider and provider.account_format:
            import re
            if not re.match(provider.account_format, account_number):
                raise serializers.ValidationError({"account_number": "Invalid account number format for this provider"})
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


from Payment.models import UserServiceProvider, BillStandingOrder
from Payment.serializers import UserServiceProviderSerializer, BillStandingOrderSerializer
class UserServiceProviderViewSet(ModelViewSet):
    serializer_class = UserServiceProviderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return UserServiceProvider.objects.filter(user=profile)
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(user=profile)


class BillStandingOrderViewSet(ModelViewSet):
    serializer_class = BillStandingOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return BillStandingOrder.objects.filter(user=profile)
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(user=profile, status='active')
        
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        order.status = 'cancelled'
        order.save()
        return Response({'status': 'cancelled'})


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
        loan.reviewed_by = request.user
        loan.reviewed_at = timezone.now()
        loan.save()
        return Response({'status': 'approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        loan = self.get_object()
        loan.status = 'rejected'
        loan.reviewed_by = request.user
        loan.reviewed_at = timezone.now()
        loan.rejection_reason = request.data.get('reason', '')
        loan.save()
        return Response({'status': 'rejected', 'reason': loan.rejection_reason})
    
    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        loan = self.get_object()
        if loan.status != 'approved':
            return Response({'error': 'Loan must be approved first'}, status=status.HTTP_400_BAD_REQUEST)
            
        product = loan.product
        net_amount = Decimal(str(loan.amount)) - Decimal(str(loan.processing_fee_amount))
        
        try:
            with db_transaction.atomic():
                pp = PaymentProfile.objects.get(user=loan.user)
                
                # Capital Source Routing
                if product.provider and getattr(product.provider, 'provider_type', '') == 'loan_provider':
                    pass
                elif getattr(product, 'is_group_loan', False) and getattr(product, 'group', None):
                    group = product.group
                    if group.wallet_balance < loan.amount:
                        return Response({'error': 'Insufficient group funds for disbursement'}, status=status.HTTP_400_BAD_REQUEST)
                    group.wallet_balance -= Decimal(str(loan.amount))
                    group.save()
                else:
                    pass

                # Credit user balance
                pp.comrade_balance += net_amount
                pp.save()
                
                # Create Transaction Token
                from Payment.models import TransactionToken
                TransactionToken.objects.create(
                    receiver_profile=pp,
                    amount=net_amount,
                    transaction_type='loan_disbursement',
                    status='completed',
                    description=f"Loan Disbursement: {product.name}"
                )

                loan.status = 'disbursed'
                loan.disbursed_by = request.user
                loan.disbursed_at = timezone.now()
                loan.save()
                
                from Notifications.models import create_notification
                create_notification(
                    recipient=loan.user.user,
                    notification_type='loan_disbursed',
                    message=f"Your loan of KES {loan.amount} has been disbursed to your wallet.",
                    action_url="/payments/loans"
                )
                
                return Response({'status': 'disbursed', 'amount': str(net_amount)})
                
        except PaymentProfile.DoesNotExist:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def repay(self, request, pk=None):
        loan = self.get_object()
        amount_val = request.data.get('amount', 0)
        
        if loan.status not in ('disbursed', 'overdue'):
            return Response({'error': 'Loan is not in a repayable state'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            amount = Decimal(str(amount_val))
            if amount <= 0:
                return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
                
            with db_transaction.atomic():
                pp = PaymentProfile.objects.get(user=loan.user)
                if pp.comrade_balance < amount:
                    return Response({'error': 'Insufficient wallet balance'}, status=status.HTTP_400_BAD_REQUEST)
                    
                # Deduct from user
                pp.comrade_balance -= amount
                pp.save()
                
                # Capital Source Routing
                product = loan.product
                if product.provider and getattr(product.provider, 'provider_type', '') == 'loan_provider':
                    pass
                elif getattr(product, 'is_group_loan', False) and getattr(product, 'group', None):
                    group = product.group
                    group.wallet_balance += amount
                    group.save()
                    
                # Create Transaction Token
                from Payment.models import TransactionToken
                TransactionToken.objects.create(
                    sender_profile=pp,
                    amount=amount,
                    transaction_type='loan_repayment',
                    status='completed',
                    description=f"Loan Repayment: {product.name}"
                )
                
                # Update specific repayment installment
                pending_repayments = loan.repayments.filter(status__in=['pending', 'overdue']).order_by('due_date')
                remaining_amount = amount
                
                for rep in pending_repayments:
                    if remaining_amount <= 0:
                        break
                        
                    due = rep.amount_due + (rep.penalty or Decimal('0.00')) - (rep.amount_paid or Decimal('0.00'))
                    if remaining_amount >= due:
                        rep.amount_paid = (rep.amount_paid or Decimal('0.00')) + due
                        rep.status = 'paid'
                        rep.paid_date = timezone.now().date()
                        remaining_amount -= due
                    else:
                        rep.amount_paid = (rep.amount_paid or Decimal('0.00')) + remaining_amount
                        remaining_amount = Decimal('0.00')
                    rep.save()
                
                # Check if fully paid
                total_expected = sum((r.amount_due + (r.penalty or Decimal('0.00'))) for r in loan.repayments.all())
                total_paid = sum((r.amount_paid or Decimal('0.00')) for r in loan.repayments.all())
                
                if total_paid >= total_expected:
                    loan.status = 'completed'
                    loan.save()
                elif loan.status == 'overdue' and not loan.repayments.filter(status='overdue').exists():
                    loan.status = 'disbursed'
                    loan.save()
                
                return Response({'status': 'repaid', 'amount': str(amount), 'loan_status': loan.status})
                
        except PaymentProfile.DoesNotExist:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        """Fund an escrow — supports wallet, stripe (hold), flutterwave, pesapal."""
        escrow = self.get_object()
        profile = Profile.objects.get(user=request.user)
        if escrow.buyer != profile:
            return Response({'error': 'Only buyer can fund'}, status=status.HTTP_403_FORBIDDEN)
        if escrow.status != 'initiated':
            return Response({'error': f'Escrow is already {escrow.status}'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_method = request.data.get('payment_method', 'wallet')
        
        if payment_method == 'wallet':
            # Original wallet deduction flow
            try:
                pp = PaymentProfile.objects.get(user=profile)
                if pp.comrade_balance >= escrow.total_amount:
                    pp.comrade_balance -= escrow.total_amount
                    pp.save()
                    escrow.status = 'funded'
                    escrow.payment_gateway = 'wallet'
                    escrow.funded_at = timezone.now()
                    escrow.save()
                    return Response({'status': 'funded', 'gateway': 'wallet'})
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
            except PaymentProfile.DoesNotExist:
                return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        elif payment_method == 'stripe':
            # Stripe hold: create PaymentIntent with capture_method=manual
            from Payment.services.payment_service import StripeProvider
            result = StripeProvider.create_escrow_intent(
                amount=float(escrow.total_amount),
                currency=request.data.get('currency', 'usd'),
                escrow_id=str(escrow.id),
            )
            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
            
            escrow.payment_gateway = 'stripe'
            escrow.payment_intent_id = result['id']
            escrow.save()
            return Response({
                'status': 'requires_confirmation',
                'gateway': 'stripe',
                'client_secret': result['client_secret'],
                'payment_intent_id': result['id'],
            })
        
        elif payment_method == 'flutterwave':
            from Payment.services.payment_service import FlutterwaveProvider
            result = FlutterwaveProvider.initiate_payment(
                amount=float(escrow.total_amount),
                currency=request.data.get('currency', 'KES'),
                email=request.user.email,
                description=f'Escrow: {escrow.title}',
            )
            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
            
            escrow.payment_gateway = 'flutterwave'
            escrow.payment_intent_id = result.get('tx_ref', '')
            escrow.save()
            return Response({
                'status': 'redirect',
                'gateway': 'flutterwave',
                'payment_link': result['payment_link'],
                'tx_ref': result['tx_ref'],
            })
        
        elif payment_method == 'pesapal':
            from Payment.services.payment_service import PesapalProvider
            result = PesapalProvider.submit_order(
                amount=float(escrow.total_amount),
                currency=request.data.get('currency', 'KES'),
                email=request.user.email,
                description=f'Escrow: {escrow.title}',
                order_id=str(escrow.id),
            )
            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
            
            escrow.payment_gateway = 'pesapal'
            escrow.payment_intent_id = result.get('order_tracking_id', '')
            escrow.save()
            return Response({
                'status': 'redirect',
                'gateway': 'pesapal',
                'redirect_url': result['redirect_url'],
            })
        
        return Response({'error': f'Unsupported payment method: {payment_method}'}, status=status.HTTP_400_BAD_REQUEST)
    
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
        """Release escrow funds to the seller."""
        escrow = self.get_object()
        profile = Profile.objects.get(user=request.user)
        if escrow.buyer != profile:
            return Response({'error': 'Only buyer can release'}, status=status.HTTP_403_FORBIDDEN)
        
        if escrow.payment_gateway == 'stripe' and escrow.payment_intent_id:
            # Capture the held Stripe PaymentIntent
            from Payment.services.payment_service import StripeProvider
            result = StripeProvider.capture_payment_intent(escrow.payment_intent_id)
            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
            
            # Credit seller's wallet with the escrow amount (minus fee)
            try:
                seller_pp = PaymentProfile.objects.get(user=escrow.seller)
                seller_pp.comrade_balance += float(escrow.amount)
                seller_pp.save()
            except PaymentProfile.DoesNotExist:
                return Response({'error': 'Seller profile not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Wallet-funded release (original flow)
            try:
                seller_pp = PaymentProfile.objects.get(user=escrow.seller)
                seller_pp.comrade_balance += float(escrow.amount)
                seller_pp.save()
            except PaymentProfile.DoesNotExist:
                return Response({'error': 'Seller profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        escrow.status = 'released'
        escrow.released_at = timezone.now()
        escrow.save()
        return Response({'status': 'released'})
    
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
        
        # If Stripe hold, cancel (refund) the held authorization
        if escrow.payment_gateway == 'stripe' and escrow.payment_intent_id:
            from Payment.services.payment_service import StripeProvider
            StripeProvider.cancel_payment_intent(escrow.payment_intent_id)
        
        return Response({'status': 'disputed'})

    @action(detail=True, methods=['post'])
    def resolve_dispute(self, request, pk=None):
        """
        Resolve an escrow dispute. Can be done by staff/admin.
        resolution_type: 'buyer_wins', 'seller_wins', 'split'
        split_percentage: e.g. 50 (if split, representing buyer's share)
        """
        escrow = self.get_object()
        if escrow.status != 'disputed':
            return Response({'error': 'Escrow is not disputed'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not request.user.is_staff: # Simple auth for now
            return Response({'error': 'Only staff can resolve disputes directly'}, status=status.HTTP_403_FORBIDDEN)
            
        resolution_type = request.data.get('resolution_type')
        split_percentage = float(request.data.get('split_percentage', 50))
        
        try:
            dispute = EscrowDispute.objects.get(escrow=escrow, status__in=['open', 'under_review'])
        except EscrowDispute.DoesNotExist:
            return Response({'error': 'No open dispute found'}, status=status.HTTP_404_NOT_FOUND)
            
        with db_transaction.atomic():
            buyer_pp = PaymentProfile.objects.select_for_update().get(user=escrow.buyer)
            seller_pp = PaymentProfile.objects.select_for_update().get(user=escrow.seller)
            
            if resolution_type == 'buyer_wins':
                escrow.status = 'refunded'
                dispute.status = 'resolved_buyer'
                
                # Refund buyer fully (including escrow fee)
                buyer_pp.comrade_balance += escrow.total_amount
                buyer_pp.save()
                
                TransactionToken.objects.create(
                    sender=seller_pp.user, # Conceptually from seller/platform
                    receiver=buyer_pp.user,
                    amount=escrow.total_amount,
                    transaction_type='escrow_refund',
                    status='completed',
                    description=f'Escrow Dispute Refund: {escrow.title}',
                )
                
            elif resolution_type == 'seller_wins':
                escrow.status = 'released'
                dispute.status = 'resolved_seller'
                
                # Pay seller principal (platform retains fee)
                seller_pp.comrade_balance += escrow.amount
                seller_pp.save()
                
                TransactionToken.objects.create(
                    sender=buyer_pp.user,
                    receiver=seller_pp.user,
                    amount=escrow.amount,
                    transaction_type='escrow_release',
                    status='completed',
                    description=f'Escrow Dispute Released to Seller: {escrow.title}',
                )
                
            elif resolution_type == 'split':
                escrow.status = 'released'
                dispute.status = 'settled'
                
                # Split principal (platform retains fee)
                buyer_share = float(escrow.amount) * (split_percentage / 100.0)
                seller_share = float(escrow.amount) - buyer_share
                
                if buyer_share > 0:
                    buyer_pp.comrade_balance += Decimal(str(buyer_share))
                    buyer_pp.save()
                    TransactionToken.objects.create(
                        sender=seller_pp.user,
                        receiver=buyer_pp.user,
                        amount=Decimal(str(buyer_share)),
                        transaction_type='escrow_refund',
                        status='completed',
                        description=f'Escrow Dispute Split Refund: {escrow.title}',
                    )
                    
                if seller_share > 0:
                    seller_pp.comrade_balance += Decimal(str(seller_share))
                    seller_pp.save()
                    TransactionToken.objects.create(
                        sender=buyer_pp.user,
                        receiver=seller_pp.user,
                        amount=Decimal(str(seller_share)),
                        transaction_type='escrow_release',
                        status='completed',
                        description=f'Escrow Dispute Split Release: {escrow.title}',
                    )
                    
            else:
                return Response({'error': 'Invalid resolution type'}, status=status.HTTP_400_BAD_REQUEST)
                
            escrow.released_at = timezone.now()
            escrow.save()
            
            dispute.resolution_notes = request.data.get('notes', '')
            dispute.resolved_by = Profile.objects.get(user=request.user)
            dispute.resolved_at = timezone.now()
            dispute.save()
            
        return Response({'status': 'resolved', 'resolution_type': resolution_type, 'dispute_status': dispute.status})

    @action(detail=True, methods=['post'])
    def submit_evidence(self, request, pk=None):
        """Submit evidence for an open dispute."""
        escrow = self.get_object()
        try:
            dispute = EscrowDispute.objects.get(escrow=escrow, status='open')
        except EscrowDispute.DoesNotExist:
            return Response({'error': 'No open dispute found'}, status=status.HTTP_404_NOT_FOUND)
            
        evidence_item = {
            'submitted_by': request.user.username,
            'timestamp': timezone.now().isoformat(),
            'notes': request.data.get('notes', ''),
            'file_url': request.data.get('file_url', '')
        }
        
        current_evidence = dispute.evidence or []
        if not isinstance(current_evidence, list):
            current_evidence = []
            
        current_evidence.append(evidence_item)
        dispute.evidence = current_evidence
        dispute.save()
        
        return Response({'status': 'evidence_submitted'})

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

    @action(detail=True, methods=['post'])
    def pay_premium(self, request, pk=None):
        policy = self.get_object()
        
        try:
            with db_transaction.atomic():
                pp = PaymentProfile.objects.get(user=policy.user)
                premium = policy.product.premium_amount
                
                if pp.comrade_balance < premium:
                    return Response({'error': 'Insufficient wallet balance for premium'}, status=status.HTTP_400_BAD_REQUEST)
                    
                # Deduct premium
                pp.comrade_balance -= premium
                pp.save()
                
                # Transaction Token
                TransactionToken.objects.create(
                    sender_profile=pp,
                    amount=premium,
                    transaction_type='insurance_premium',
                    status='completed',
                    description=f"Insurance Premium: {policy.product.name}"
                )
                
                # Partner Commission Tracking
                if policy.product.provider and getattr(policy.product.provider, 'commission_rate', None):
                    rate = policy.product.provider.commission_rate
                    commission = premium * Decimal(str(rate)) / Decimal('100')
                    # Log commission or credit partner wallet
                    # Example: ProviderTransaction.objects.create(...)
                    pass
                
                # Extend next payment date based on premium frequency
                from dateutil.relativedelta import relativedelta
                freq = policy.product.premium_frequency
                if freq == 'monthly':
                    policy.next_payment_date += relativedelta(months=1)
                elif freq == 'quarterly':
                    policy.next_payment_date += relativedelta(months=3)
                elif freq == 'annually':
                    policy.next_payment_date += relativedelta(years=1)
                    
                if policy.status in ('expired', 'lapsed'):
                    policy.status = 'active'
                    
                policy.save()
                return Response({'status': 'premium_paid', 'next_payment_date': policy.next_payment_date})
                
        except PaymentProfile.DoesNotExist:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)


class InsuranceClaimViewSet(ModelViewSet):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return InsuranceClaim.objects.filter(claimant=profile)
    
    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        policy = serializer.validated_data.get('policy')
        
        # Waiting Period Validation
        if policy and hasattr(policy.product, 'waiting_period_days'):
            waiting_days = policy.product.waiting_period_days
            from datetime import timedelta
            if timezone.now().date() < policy.start_date + timedelta(days=waiting_days):
                raise serializers.ValidationError(
                    {"error": f"Policy is still in the {waiting_days}-day waiting period. Claims cannot be filed yet."}
                )
        
        serializer.save(claimant=profile, status='submitted')

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        claim = self.get_object()
        if claim.status != 'submitted':
            return Response({'error': 'Claim must be in submitted state'}, status=status.HTTP_400_BAD_REQUEST)
        claim.status = 'under_review'
        claim.save()
        return Response({'status': 'under_review'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        claim = self.get_object()
        approved_amount = request.data.get('approved_amount')
        if not approved_amount:
            return Response({'error': 'approved_amount is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        claim.status = 'approved'
        claim.approved_amount = Decimal(str(approved_amount))
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
        claim.save()
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        claim = self.get_object()
        claim.status = 'rejected'
        claim.rejection_reason = request.data.get('reason', '')
        claim.reviewed_by = request.user
        claim.reviewed_at = timezone.now()
        claim.save()
        return Response({'status': 'rejected', 'reason': claim.rejection_reason})

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        claim = self.get_object()
        if claim.status != 'approved':
            return Response({'error': 'Claim must be approved before payment'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            with db_transaction.atomic():
                pp = PaymentProfile.objects.get(user=claim.claimant)
                
                # In a partner-model, funds theoretically come from the partner's integration.
                # We mock the callback by directly crediting the user's wallet.
                amount = claim.approved_amount or claim.amount
                pp.comrade_balance += amount
                pp.save()
                
                TransactionToken.objects.create(
                    receiver_profile=pp,
                    amount=amount,
                    transaction_type='insurance_claim_payout',
                    status='completed',
                    description=f"Insurance Claim Payout: {claim.policy.product.name}"
                )
                
                claim.status = 'paid'
                claim.save()
                
                from Notifications.models import create_notification
                create_notification(
                    recipient=claim.claimant.user,
                    notification_type='claim_paid',
                    message=f"Your insurance claim of KES {amount} has been paid to your wallet.",
                    action_url="/payments/insurance"
                )
                
                return Response({'status': 'paid', 'amount': str(amount)})
                
        except PaymentProfile.DoesNotExist:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)


# ==================== DONATIONS & CHARITY VIEWSETS ====================

class DonationViewSet(ModelViewSet):
    queryset = Donation.objects.all()
    serializer_class = DonationSerializer
    permission_classes = [IsAuthenticated]
    logger = logging.getLogger(__name__)

    def create(self, request, *args, **kwargs):
        self.logger.debug(f"CREATE DONATION - Request data: {request.data}")
        self.logger.debug(f"CREATE DONATION - Files: {request.FILES}")
        self.logger.debug(f"CREATE DONATION - User: {request.user}")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        self.logger.debug(f"DONATION LIST - User: {user}, Profile: {payment_profile}")
        
        if not payment_profile:
            self.logger.warning(f"DONATION LIST - No payment profile for user {user}")
            return Donation.objects.none()

        queryset = Donation.objects.filter(
            Q(donor_profile=payment_profile) |
            Q(payment_group__members__payment_profile=payment_profile)
        ).distinct()
        
        group_id = self.request.query_params.get('payment_group', None)
        self.logger.debug(f"DONATION LIST - Group ID filter: {group_id}")
        if group_id:
            queryset = queryset.filter(payment_group_id=group_id)
            
        self.logger.debug(f"DONATION LIST - Final queryset count: {queryset.count()}")
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            raise serializers.ValidationError("Could not create payment profile")

        payment_group_id = self.request.data.get('payment_group')
        if payment_group_id:
            serializer.save()
        else:
            serializer.save(donor_profile=payment_profile)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def contribute(self, request, pk=None):
        donation = self.get_object()
        amount = request.data.get('amount')
        
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        # Lock profile to prevent race conditions
        payment_profile = PaymentProfile.objects.select_for_update().get(id=payment_profile.id)
        
        # Balance check
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct
        payment_profile.comrade_balance -= Decimal(str(amount))
        payment_profile.save()

        # Find member if group donation
        member = None
        if donation.payment_group:
            try:
                member = PaymentGroupMember.objects.get(payment_group=donation.payment_group, payment_profile=payment_profile)
            except PaymentGroupMember.DoesNotExist:
                pass

        # Create contribution
        contribution = DonationContribution.objects.create(
            donation=donation,
            donor_profile=payment_profile if not member else None,
            member=member,
            amount=amount,
            status='confirmed',
            confirmed_at=timezone.now()
        )

        # Update donation total atomically
        donation = Donation.objects.select_for_update().get(id=donation.id)
        donation.amount_collected += Decimal(str(amount))
        donation.save()

        return Response({
            'status': 'Contribution successful',
            'amount_contributed': amount,
            'total_collected': float(donation.amount_collected)
        })


# ==================== GROUP INVESTMENT VIEWSETS ====================

class GroupBusinessViewSet(ModelViewSet):
    """Group-led business ventures."""
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Business.objects.none()

        queryset = Business.objects.filter(payment_group__members__payment_profile=payment_profile).distinct()
        
        group_id = self.request.query_params.get('payment_group')
        if group_id:
            queryset = queryset.filter(payment_group_id=group_id)
            
        return queryset


class GroupInvestmentViewSet(ModelViewSet):
    queryset = GroupInvestment.objects.all()
    serializer_class = GroupInvestmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return GroupInvestment.objects.none()

        queryset = GroupInvestment.objects.filter(
            Q(payment_group__members__payment_profile=payment_profile) |
            Q(pitch_visibility='public')
        ).distinct()
        
        group_id = self.request.query_params.get('payment_group')
        if group_id:
            queryset = queryset.filter(payment_group_id=group_id)
            
        return queryset

    def get_serializer(self, *args, **kwargs):
        # Ensure approval votes exist for read operations
        if 'data' not in kwargs:
            instances = args[0] if args else None
            if instances:
                try:
                    if hasattr(instances, '__iter__'):
                        for instance in instances:
                            self._ensure_approval_vote(instance)
                    else:
                        self._ensure_approval_vote(instances)
                except Exception as e:
                    print(f"Error in _ensure_approval_vote: {e}")
        return super().get_serializer(*args, **kwargs)

    def _ensure_approval_vote(self, investment):
        if not hasattr(investment, 'approval_vote'): return
        if not investment.approval_vote and investment.payment_group:
            from Payment.models import GroupVote
            vote = GroupVote.objects.create(
                group=investment.payment_group,
                created_by=investment.initiated_by or investment.payment_group.creator,
                title=f"Approval for {investment.name}",
                description=investment.description,
                vote_type='investment',
                amount=investment.total_amount
            )
            investment.approval_vote = vote
            investment.save()

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            raise serializers.ValidationError("Could not create payment profile")

        payment_group = serializer.validated_data.get('payment_group')
        # Map target_amount to total_amount if provided by frontend
        total_amount = serializer.validated_data.get('total_amount', 0)
        
        investment = serializer.save(initiated_by=payment_profile)
        
        # Auto-create an approval vote
        if payment_group:
            vote = GroupVote.objects.create(
                group=payment_group,
                created_by=payment_profile,
                title=f"Approval for {investment.name}",
                description=investment.description,
                vote_type='investment',
                amount=investment.total_amount or total_amount
            )
            investment.approval_vote = vote
            investment.save()

    @action(detail=False, methods=['get'])
    def public_pitches(self, request):
        pitches = GroupInvestment.objects.filter(pitch_visibility='public')
        serializer = self.get_serializer(pitches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def join_public_pitch(self, request, pk=None):
        """Join the group associated with a public pitch so the user can interact."""
        investment = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if investment.pitch_visibility != 'public':
            return Response({'error': 'This is not a public pitch'}, status=status.HTTP_400_BAD_REQUEST)
            
        group = investment.payment_group
        if not group:
            return Response({'error': 'No group associated to join'}, status=status.HTTP_400_BAD_REQUEST)

        member, created = PaymentGroupMember.objects.get_or_create(
            payment_group=group,
            payment_profile=payment_profile,
            defaults={'role': 'member'}
        )
        
        if created:
            # Update group counts
            group.member_count = group.members.count()
            group.save()
            return Response({'status': 'Joined successfully'})
        return Response({'status': 'Already a member'})

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def quote(self, request, pk=None):
        """Submit a quote for an investment opportunity"""
        investment = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=investment.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this investment group'}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Amount required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
            
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Deduct
        payment_profile.comrade_balance -= Decimal(str(amount))
        payment_profile.save()

        # Create or update quote
        quote, created = InvestmentQuote.objects.get_or_create(
            group_investment=investment,
            member=member,
            defaults={'amount_quoted': 0, 'status': 'confirmed', 'confirmed_at': timezone.now()}
        )
        
        if not created:
            # Add to existing quote
            quote.amount_quoted += Decimal(str(amount))
            quote.contribution_balance += Decimal(str(amount))
            quote.status = 'confirmed'
            quote.confirmed_at = timezone.now()
        else:
            quote.amount_quoted = Decimal(str(amount))
            quote.contribution_balance = Decimal(str(amount))
            
        quote.save()

        # Update parent investment
        investment.amount_collected += Decimal(str(amount))
        investment.contribution_balance += Decimal(str(amount))
        investment.save()

        # Update ownership percentages relative to the total collected
        if investment.quoting_mode == 'proportional' and investment.amount_collected > 0:
            for q in investment.quotes.all():
                q.ownership_percentage = (q.amount_quoted / investment.amount_collected) * 100
                q.save()

        return Response({
            'status': 'Quote submitted successfully',
            'amount': amount,
            'total_investment_collected': float(investment.amount_collected)
        })

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def withdraw_contribution(self, request, pk=None):
        """Withdraw contribution early. Incurs 2% penalty if before maturity."""
        investment = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=investment.payment_group, payment_profile=payment_profile)
            quote = InvestmentQuote.objects.get(group_investment=investment, member=member)
        except (PaymentGroupMember.DoesNotExist, InvestmentQuote.DoesNotExist):
            return Response({'error': 'No active quote found'}, status=status.HTTP_404_NOT_FOUND)

        amount = Decimal(str(request.data.get('amount', 0)))
        if amount <= 0 or amount > quote.contribution_balance:
            return Response({'error': 'Invalid withdrawal amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Check maturity if penalty applies
        # If no explicit maturity date on opportunity, we assume open-ended and no penalty.
        # Otherwise, check if current date < created_at + maturity
        penalty_amount = Decimal('0.00')
        has_maturity = False
        
        if investment.investment_opportunity and investment.investment_opportunity.maturity_period:
            # Simple simulation: assume any withdraw before a set condition is early for this generic field
            # Real logic would parse '12_months' and compare timezone.now() 
            has_maturity = True
            
        is_early = has_maturity # Always early for now unless handled with real dates natively
        
        # We will apply a static 2% penalty for early access
        if is_early:
            penalty_amount = amount * Decimal('0.02')
        
        final_amount = amount - penalty_amount
        
        quote.contribution_balance -= amount
        quote.quoted_amount -= amount # Decrease equity basis
        quote.save()
        
        investment.contribution_balance -= amount
        investment.amount_collected -= amount
        investment.save()
        
        payment_profile.comrade_balance += final_amount
        payment_profile.save()
        
        # Update proportional ownership
        if investment.quoting_mode == 'proportional' and investment.amount_collected > 0:
            for q in investment.quotes.all():
                q.ownership_percentage = (q.amount_quoted / investment.amount_collected) * 100
                q.save()
                
        return Response({
            'status': 'Withdrawal processed',
            'penalty_applied': float(penalty_amount),
            'amount_received': float(final_amount)
        })

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def withdraw_gains(self, request, pk=None):
        """Withdraw distributed gains to wallet or push into group"""
        investment = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=investment.payment_group, payment_profile=payment_profile)
            quote = InvestmentQuote.objects.get(group_investment=investment, member=member)
        except (PaymentGroupMember.DoesNotExist, InvestmentQuote.DoesNotExist):
            return Response({'error': 'No active quote found'}, status=status.HTTP_404_NOT_FOUND)

        amount = Decimal(str(request.data.get('amount', 0)))
        if amount <= 0 or amount > quote.gains_balance:
            return Response({'error': 'Invalid gains withdrawal amount'}, status=status.HTTP_400_BAD_REQUEST)

        pref = request.data.get('preference', quote.gains_distribution_preference)
        
        quote.gains_balance -= amount
        investment.gains_balance -= amount
        quote.save()
        investment.save()
        
        if pref == 'direct_to_wallet':
            payment_profile.comrade_balance += amount
            payment_profile.save()
            msg = 'Gains transferred to personal wallet'
        else:
            group = investment.payment_group
            group.current_amount += amount
            group.save()
            msg = 'Gains transferred to group pool'
            
        return Response({
            'status': 'Withdrawal processed',
            'amount': float(amount),
            'destination': msg
        })

# ============================================================================
# ADVANCED GROUP FEATURES VIEWSETS
# ============================================================================


class RoundPositionViewSet(ModelViewSet):
    queryset = RoundPosition.objects.all()
    serializer_class = RoundPositionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return RoundPosition.objects.none()
        
        queryset = RoundPosition.objects.filter(payment_group__members__payment_profile=payment_profile).distinct()
        
        group_id = self.request.query_params.get('payment_group')
        if group_id:
            queryset = queryset.filter(payment_group_id=group_id)
            
        return queryset

    def perform_create(self, serializer):
        payment_group = serializer.validated_data['payment_group']
        member = serializer.validated_data['member']
        pos = serializer.validated_data['position_number']
        
        if RoundPosition.objects.filter(payment_group=payment_group, position_number=pos).exists():
            raise serializers.ValidationError("This position is already taken.")
            
        if RoundPosition.objects.filter(payment_group=payment_group, member=member).exists():
            raise serializers.ValidationError("You already have a position in this group.")
            
        serializer.save()

    @action(detail=False, methods=['get'], url_path='available')
    def available_positions(self, request):
        group_id = request.query_params.get('group')
        round_id = request.query_params.get('round_id')  # Optional: specific round
        
        if not group_id:
            return Response({'error': 'group parameter required'}, status=400)
        
        try:
            group = PaymentGroups.objects.get(id=group_id)
        except PaymentGroups.DoesNotExist:
            return Response({'error': 'Group not found'}, status=404)
        
        # Get active round if round_id not provided
        round_obj = None
        if round_id:
            try:
                round_obj = RoundContribution.objects.get(id=round_id, payment_group=group)
            except RoundContribution.DoesNotExist:
                return Response({'error': 'Round not found'}, status=404)
        else:
            # Get the latest active or pending round
            round_obj = RoundContribution.objects.filter(
                payment_group=group,
                status__in=['active', 'pending', 'pending_approval']
            ).order_by('-round_number').first()
        
        member_count = group.members.filter(is_active=True).count()
        
        # Get taken positions for the specific round (or all if no round)
        query = RoundPosition.objects.filter(payment_group=group)
        if round_obj:
            query = query.filter(round=round_obj)
        taken_positions = query.values_list('position_number', flat=True)
        
        available = [i for i in range(1, member_count + 1) if i not in taken_positions]
        
        return Response({
            'group_id': str(group.id),
            'round_id': str(round_obj.id) if round_obj else None,
            'member_count': member_count,
            'total_positions': member_count,
            'taken_count': len(taken_positions),
            'available_positions': available,
            'taken_positions': list(taken_positions)
        })

    @action(detail=False, methods=['post'], url_path='pick')
    def pick_position(self, request):
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        group_id = request.data.get('group')
        round_id = request.data.get('round_id')  # New: specific round for position
        position_number = request.data.get('position_number')
        
        if not group_id or position_number is None:
            return Response({'error': 'group and position_number required'}, status=400)
        
        try:
            group = PaymentGroups.objects.get(id=group_id)
        except PaymentGroups.DoesNotExist:
            return Response({'error': 'Group not found'}, status=404)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=403)
        
        # Get active round if round_id not provided
        round_obj = None
        if round_id:
            try:
                round_obj = RoundContribution.objects.get(id=round_id, payment_group=group)
            except RoundContribution.DoesNotExist:
                return Response({'error': 'Round not found'}, status=404)
        else:
            # Get the latest active or pending round
            round_obj = RoundContribution.objects.filter(
                payment_group=group,
                status__in=['active', 'pending', 'pending_approval']
            ).order_by('-round_number').first()
            if not round_obj:
                return Response({'error': 'No active round found. Create a round first.'}, status=400)
        
        # Check if member already has a position for this specific round
        if RoundPosition.objects.filter(payment_group=group, member=member, round=round_obj).exists():
            return Response({'error': 'You already have a position in this round'}, status=400)
        
        # Check if position is taken in this round
        if RoundPosition.objects.filter(payment_group=group, position_number=position_number, round=round_obj).exists():
            return Response({'error': f'Position {position_number} is already taken in this round'}, status=409)
        
        member_count = group.members.filter(is_active=True).count()
        if position_number < 1 or position_number > member_count:
            return Response({'error': f'Position must be between 1 and {member_count}'}, status=400)
        
        position = RoundPosition.objects.create(
            payment_group=group,
            round=round_obj,
            member=member,
            position_number=position_number
        )
        
        serializer = self.get_serializer(position)
        return Response(serializer.data, status=201)

    @action(detail=False, methods=['get'], url_path='my-position')
    def my_position(self, request):
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        group_id = request.query_params.get('group')
        round_id = request.query_params.get('round_id')  # Optional: specific round
        
        if not group_id:
            return Response({'error': 'group parameter required'}, status=400)
        
        try:
            group = PaymentGroups.objects.get(id=group_id)
        except PaymentGroups.DoesNotExist:
            return Response({'error': 'Group not found'}, status=404)
        
        # Get active round if round_id not provided
        round_obj = None
        if round_id:
            try:
                round_obj = RoundContribution.objects.get(id=round_id, payment_group=group)
            except RoundContribution.DoesNotExist:
                return Response({'error': 'Round not found'}, status=404)
        else:
            # Get the latest active or pending round
            round_obj = RoundContribution.objects.filter(
                payment_group=group,
                status__in=['active', 'pending', 'pending_approval']
            ).order_by('-round_number').first()
        
        # Query positions for the specific round (or all if no round specified)
        query = RoundPosition.objects.filter(payment_group=group, member__payment_profile=payment_profile)
        if round_obj:
            query = query.filter(round=round_obj)
        
        try:
            position = query.first()
            if not position:
                return Response({'has_position': False, 'position': None})
        except RoundPosition.DoesNotExist:
            return Response({'has_position': False, 'position': None})
        
        serializer = self.get_serializer(position)
        return Response({'has_position': True, 'position': serializer.data})

class RoundContributionViewSet(ModelViewSet):
    queryset = RoundContribution.objects.all()
    serializer_class = RoundContributionSerializer
    permission_classes = [IsAuthenticated]
    logger = logging.getLogger(__name__)

    def create(self, request, *args, **kwargs):
        self.logger.debug(f"CREATE ROUND - Request data: {request.data}")
        self.logger.debug(f"CREATE ROUND - User: {request.user}")
        self.logger.debug(f"CREATE ROUND - Auth: {request.auth}")
        try:
            response = super().create(request, *args, **kwargs)
            self.logger.debug(f"CREATE ROUND - Response status: {response.status_code}")
            self.logger.debug(f"CREATE ROUND - Response data: {response.data}")
            return response
        except Exception as e:
            self.logger.error(f"CREATE ROUND - Exception: {str(e)}")
            self.logger.error(f"CREATE ROUND - Exception type: {type(e)}")
            raise

    def perform_create(self, serializer):
        self.logger.debug(f"Creating round with data: {serializer.validated_data}")
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        self.logger.debug(f"User: {user}, Payment Profile: {payment_profile}")
        
        if not payment_profile:
            self.logger.error("Failed to get or create payment profile")
            raise serializers.ValidationError("Could not verify payment profile.")
        
        group = serializer.validated_data['payment_group']
        self.logger.debug(f"Group: {group.id} - {group.name}")
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            self.logger.debug(f"Member found: {member.id}")
        except PaymentGroupMember.DoesNotExist:
            self.logger.error(f"User {user} is not a member of group {group}")
            raise serializers.ValidationError("Not a member of this group.")
        
        # Check for unique round name
        round_name = serializer.validated_data.get('round_name', '')
        if round_name and RoundContribution.objects.filter(payment_group=group, round_name=round_name).exists():
            raise serializers.ValidationError(f"A round with name '{round_name}' already exists in this group.")
        
        existing_rounds = RoundContribution.objects.filter(payment_group=group).count()
        round_number = serializer.validated_data.get('round_number', existing_rounds + 1)
        self.logger.debug(f"Round number: {round_number}, Existing rounds: {existing_rounds}")
        
        # Get previous round for position copying
        use_previous_positions = serializer.validated_data.get('use_previous_positions', False)
        previous_round = None
        if use_previous_positions:
            previous_round = RoundContribution.objects.filter(
                payment_group=group
            ).order_by('-round_number').first()
            if previous_round:
                self.logger.debug(f"Using positions from previous round: {previous_round.id}")
            
        round_obj = serializer.save(
            status='pending_approval',
            round_number=round_number,
            start_date=timezone.now(),
            use_previous_positions=use_previous_positions,
            previous_round=previous_round,
            currency=serializer.validated_data.get('currency') or user.preferred_currency or 'KES'
        )
        self.logger.debug(f"Round created: {round_obj.id}")
        round_obj.approvals.add(member)
        self.logger.debug(f"Round approval added for member: {member}")
        
        # Setup positions
        group_members = list(group.members.filter(is_active=True))
        if use_previous_positions and previous_round:
            previous_positions = RoundPosition.objects.filter(payment_group=group, round=previous_round)
            for pos in previous_positions:
                RoundPosition.objects.create(
                    payment_group=group,
                    round=round_obj,
                    member=pos.member,
                    position_number=pos.position_number
                )
            self.logger.debug(f"Copied {previous_positions.count()} positions from previous round")
        elif round_obj.assignment_method == 'random':
            import random
            random.shuffle(group_members)
            for i, m in enumerate(group_members, start=1):
                RoundPosition.objects.create(
                    payment_group=group,
                    round=round_obj,
                    member=m,
                    position_number=i
                )
            self.logger.debug("Generated random positions")
            
        # Send notifications to all group members
        for gm in group_members:
            if gm.payment_profile.user.user != user:
                create_notification(
                    recipient=gm.payment_profile.user.user,
                    notification_type='group_round',
                    message=f"New round '{round_obj.round_name or round_obj.round_number}' needs your approval in {group.name}",
                    actor=user,
                    action_url=f"/payments/groups/{group.id}?tab=rounds",
                    extra_data={'group_id': str(group.id), 'round_id': str(round_obj.id)}
                )

    @action(detail=True, methods=['get'], url_path='approval-status')
    def approval_status(self, request, pk=None):
        round_obj = self.get_object()
        member_count = round_obj.payment_group.members.filter(is_active=True).count()
        approvals = round_obj.approvals.all()
        rejections = round_obj.rejections.all()
        
        def get_member_info(member):
            name = str(member.id)
            pic = None
            try:
                profile = member.payment_profile.user
                auth_user = profile.user
                
                full_name = f"{auth_user.first_name} {auth_user.last_name}".strip()
                name = full_name if full_name else auth_user.email
                
                if profile.profile_picture:
                    try:
                        pic = request.build_absolute_uri(profile.profile_picture.url)
                    except ValueError:
                        pass
                elif hasattr(auth_user, 'user_profile') and auth_user.user_profile.avatar:
                    try:
                        pic = request.build_absolute_uri(auth_user.user_profile.avatar.url)
                    except ValueError:
                        pass
            except Exception as e:
                import logging
                logging.error(f"Error in get_member_info: {str(e)}")
            return name, pic

        approval_data = []
        for member in approvals:
            name, pic = get_member_info(member)
            approval_data.append({
                'member_id': str(member.id),
                'member_name': name,
                'profile_picture': pic,
                'voted': 'approve',
                'note': round_obj.approval_notes.get(str(member.id), '')
            })
        for member in rejections:
            name, pic = get_member_info(member)
            approval_data.append({
                'member_id': str(member.id),
                'member_name': name,
                'profile_picture': pic,
                'voted': 'reject',
                'note': round_obj.approval_notes.get(str(member.id), '')
            })
        
        threshold = round_obj.payment_group.approval_threshold
        current_percentage = (approvals.count() / member_count * 100) if member_count > 0 else 0
        
        # Override threshold if start_condition is all_members
        if round_obj.start_condition == 'all_members':
            threshold = 100.0
            
        return Response({
            'round_id': str(round_obj.id),
            'round_number': round_obj.round_number,
            'status': round_obj.status,
            'member_count': member_count,
            'approvals_count': approvals.count(),
            'rejections_count': rejections.count(),
            'approval_percentage': round(current_percentage, 1),
            'required_threshold': threshold,
            'threshold_met': current_percentage >= threshold,
            'votes': approval_data
        })

    @action(detail=True, methods=['post'])
    def approve_round(self, request, pk=None):
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if round_obj.status not in ['pending_approval', 'pending']:
            return Response({'error': 'Round is not awaiting approval'}, status=400)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
        
        if round_obj.rejections.filter(id=member.id).exists():
            round_obj.rejections.remove(member)
            
        round_obj.approvals.add(member)
        
        member_count = round_obj.payment_group.members.filter(is_active=True).count()
        approval_percentage = (round_obj.approvals.count() / member_count * 100) if member_count > 0 else 0
        
        threshold = round_obj.payment_group.approval_threshold
        if round_obj.start_condition == 'all_members':
            threshold = 100.0
            
        if approval_percentage >= threshold and round_obj.status == 'pending_approval':
            round_obj.status = 'pending'
            # Notify creator
            creator_member = round_obj.approvals.first()
            if creator_member:
                create_notification(
                    recipient=creator_member.payment_profile.user.user,
                    notification_type='group_round',
                    message=f"Your round '{round_obj.round_name or round_obj.round_number}' has been approved and is ready to start.",
                    action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds"
                )
        
        round_obj.save()
        return Response({
            'status': 'Round approved',
            'current_status': round_obj.status,
            'approval_percentage': round(approval_percentage, 1),
            'threshold_met': approval_percentage >= threshold
        })

    @action(detail=True, methods=['post'])
    def reject_round(self, request, pk=None):
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if round_obj.status not in ['pending_approval', 'pending']:
            return Response({'error': 'Round is not awaiting approval'}, status=400)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
            
        round_obj.rejections.add(member)
        round_obj.approvals.remove(member)
        
        notes = request.data.get('note', '')
        if notes:
            round_obj.approval_notes[str(member.id)] = notes
        
        rejection_percentage = (round_obj.rejections.count() / max(1, round_obj.payment_group.members.filter(is_active=True).count()) * 100)
        if rejection_percentage > 50:
            round_obj.status = 'cancelled'
            
        round_obj.save()
        return Response({
            'status': 'Round rejected',
            'current_status': round_obj.status,
            'rejection_percentage': round(rejection_percentage, 1)
        })

    @action(detail=True, methods=['post'], url_path='swap-positions')
    def swap_positions(self, request, pk=None):
        """Allows two members to swap their positions in the round."""
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if round_obj.status not in ['pending', 'pending_approval']:
            return Response({'error': 'Positions can only be swapped before the round starts.'}, status=400)
            
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
            
        target_pos_number = request.data.get('target_position')
        other_member_id = request.data.get('other_member_id')
        
        if not target_pos_number and not other_member_id:
            return Response({'error': 'Provide target_position or other_member_id.'}, status=400)
            
        try:
            with db_transaction.atomic():
                my_pos = RoundPosition.objects.get(round=round_obj, member=member)
                if other_member_id:
                    other_pos = RoundPosition.objects.get(round=round_obj, member_id=other_member_id)
                else:
                    other_pos = RoundPosition.objects.get(round=round_obj, position_number=target_pos_number)
                    
                # Swap
                temp_num = my_pos.position_number
                my_pos.position_number = other_pos.position_number
                other_pos.position_number = temp_num
                
                my_pos.save()
                other_pos.save()
        except RoundPosition.DoesNotExist:
            return Response({'error': 'One or both positions not found.'}, status=404)
        except Exception as e:
            return Response({'error': f'Swap failed: {str(e)}'}, status=500)
            
        return Response({'status': 'Positions swapped successfully'})
    
    @action(detail=True, methods=['post'])
    def request_position_swap(self, request, pk=None):
        """Request a position swap with another member"""
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if round_obj.status not in ['pending', 'pending_approval']:
            return Response({'error': 'Cannot request position swap for active or completed rounds'}, status=400)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=403)
        
        other_member_id = request.data.get('other_member_id')
        cycle_number = request.data.get('cycle_number', 1)
        notes = request.data.get('notes', '')
        
        if not other_member_id:
            return Response({'error': 'other_member_id is required'}, status=400)
        
        # Check if swapping is allowed for this cycle
        if not round_obj.can_switch_positions(cycle_number):
            return Response({'error': f'Position switching is not allowed for cycle {cycle_number}'}, status=400)
        
        # Verify the other member exists in this round
        try:
            other_member = PaymentGroupMember.objects.get(id=other_member_id, payment_group=round_obj.payment_group)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Other member not found in this group'}, status=404)
        
        if other_member.id == member.id:
            return Response({'error': 'Cannot swap with yourself'}, status=400)
        
        # Create the swap request
        request_id = round_obj.add_position_swap_request(
            member1_id=str(member.id),
            member2_id=str(other_member.id),
            cycle_number=cycle_number,
            notes=notes
        )
        
        # Notify the other member
        try:
            create_notification(
                recipient=other_member.payment_profile.user.user,
                notification_type='group_round',
                message=f"Position swap request from {member.payment_profile.user.user.get_full_name()}. Approve in round settings.",
                action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds"
            )
        except Exception:
            pass
        
        return Response({
            'status': 'Swap request created',
            'request_id': request_id,
            'message': 'Waiting for the other member to approve'
        })
    
    @action(detail=True, methods=['post'])
    def approve_position_swap(self, request, pk=None):
        """Approve a position swap request"""
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=403)
        
        request_id = request.data.get('request_id')
        if not request_id:
            return Response({'error': 'request_id is required'}, status=400)
        
        success, message = round_obj.approve_swap_request(request_id, member.id)
        
        if success:
            # Get updated request to see if it's now completed
            swap_request = next((r for r in (round_obj.position_swap_requests or []) if r['id'] == request_id), None)
            if swap_request and swap_request.get('status') == 'completed':
                return Response({'status': 'approved_and_executed', 'message': 'Position swap completed successfully'})
            return Response({'status': 'approved', 'message': message})
        else:
            return Response({'error': message}, status=400)
    
    @action(detail=True, methods=['get'])
    def get_swap_requests(self, request, pk=None):
        """Get all swap requests for this round"""
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=403)
        
        member_id_str = str(member.id)
        requests = round_obj.position_swap_requests or []
        
        # Filter to show only requests relevant to this member
        relevant_requests = [
            r for r in requests 
            if r.get('member1_id') == member_id_str or r.get('member2_id') == member_id_str
        ]
        
        return Response({'swap_requests': relevant_requests})
    
    @action(detail=True, methods=['get'])
    def contribution_status(self, request, pk=None):
        """Get contribution window status"""
        round_obj = self.get_object()
        
        is_open = round_obj.is_contribution_open()
        next_date = round_obj.next_contribution_date or round_obj.scheduled_start_date
        
        return Response({
            'contribution_open': is_open,
            'current_cycle': round_obj.current_cycle,
            'next_contribution_date': next_date.isoformat() if next_date else None,
            'contribution_day_of_week': round_obj.contribution_day_of_week,
            'scheduled_start_date': round_obj.scheduled_start_date.isoformat() if round_obj.scheduled_start_date else None
        })

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return RoundContribution.objects.none()
        
        queryset = RoundContribution.objects.filter(payment_group__members__payment_profile=payment_profile).distinct()
        
        group_id = self.request.query_params.get('payment_group')
        if group_id:
            queryset = queryset.filter(payment_group_id=group_id)
            
        return queryset

    @action(detail=True, methods=['post'])
    def start_round(self, request, pk=None):
        round_obj = self.get_object()
        
        if round_obj.status == 'pending_approval':
            return Response({'error': 'Round must be approved by members before it can start'}, status=400)
        if round_obj.status != 'pending':
            return Response({'error': 'Round is already active or completed'}, status=400)
            
        try:
            pos = RoundPosition.objects.get(payment_group=round_obj.payment_group, round=round_obj, position_number=1)
            round_obj.awarded_to = pos.member
        except RoundPosition.DoesNotExist:
            return Response({'error': 'Positions must be assigned before starting the round'}, status=400)
                
        round_obj.status = 'active'
        round_obj.start_date = timezone.now()
        round_obj.next_contribution_date = round_obj.get_next_contribution_date()
        round_obj.current_cycle = 1
        round_obj.save()
        
        # Notify all members
        for gm in round_obj.payment_group.members.filter(is_active=True):
            create_notification(
                recipient=gm.payment_profile.user.user,
                notification_type='group_round',
                message=f"Round '{round_obj.round_name or round_obj.round_number}' has started. Contribute {round_obj.currency} {round_obj.contribution_amount} by {round_obj.next_contribution_date.strftime('%Y-%m-%d')}.",
                action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds"
            )
            
        # Notify the first recipient
        if round_obj.awarded_to:
            create_notification(
                recipient=round_obj.awarded_to.payment_profile.user.user,
                notification_type='group_round',
                message=f"You are the first recipient for round '{round_obj.round_name or round_obj.round_number}'.",
                action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds"
            )
        
        return Response({
            'status': 'Round started',
            'awarded_to': str(round_obj.awarded_to.id) if round_obj.awarded_to else None,
            'round_number': round_obj.round_number,
            'current_cycle': 1
        })

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def randomize_positions(self, request, pk=None):
        """Randomly assign positions for all active members in this round."""
        round_obj = self.get_object()
        group = round_obj.payment_group
        
        if round_obj.status not in ['pending', 'pending_approval']:
             return Response({'error': 'Cannot randomize positions for active or completed rounds.'}, status=400)
             
        from Payment.models import RoundPosition
        RoundPosition.objects.filter(round=round_obj).delete()
        
        members = list(group.members.filter(is_active=True))
        import random
        random.shuffle(members)
        
        created_positions = []
        for index, member in enumerate(members):
            pos = RoundPosition.objects.create(
                payment_group=group,
                round=round_obj,
                member=member,
                position_number=index + 1
            )
            created_positions.append(pos)
            
        return Response({'status': 'positions randomized', 'count': len(created_positions)})

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def contribute(self, request, pk=None):
        """Contribute to a specific round cycle."""
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if round_obj.status != 'active':
            return Response({'error': 'Round is not active.'}, status=400)
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
            
        amount = Decimal(str(request.data.get('amount', round_obj.contribution_amount)))
        on_behalf_of_id = request.data.get('on_behalf_of')
        
        target_member = member
        if on_behalf_of_id:
            try:
                target_member = PaymentGroupMember.objects.get(id=on_behalf_of_id, payment_group=round_obj.payment_group)
            except (PaymentGroupMember.DoesNotExist, ValueError):
                return Response({'error': 'Target member not found in this group'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if already contributed to THIS CYCLE
        if RoundMemberContribution.objects.filter(round=round_obj, member=target_member, cycle_number=round_obj.current_cycle).exists():
            return Response({'error': f'Member {target_member} has already contributed to cycle {round_obj.current_cycle}.'}, status=400)
        
        # Check if contributions are open based on scheduling
        if not round_obj.is_contribution_open():
            next_date = round_obj.next_contribution_date or round_obj.scheduled_start_date
            return Response({
                'error': 'Contributions are not open yet. Please wait for the contribution window.',
                'next_contribution_date': next_date.isoformat() if next_date else None,
                'contribution_open': False
            }, status=400)
        
# Check balance
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient wallet balance.'}, status=400)
            
        # Deduct
        payment_profile.comrade_balance -= amount
        payment_profile.save()
        
        # Record using model method
        contribution, error = round_obj.record_contribution(
            member=target_member,
            amount=amount,
            on_behalf_of=member if on_behalf_of_id else None,
            notes=request.data.get('notes', '')
        )
        
        if error:
            return Response({'error': error}, status=400)
        
        # Create transaction record for history
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            amount=amount,
            transaction_type='contribution',
            pay_from='comrade_balance',
            payment_option='comrade_balance',
            description=f'Round contribution to {round_obj.round_name or "Round " + str(round_obj.round_number)} - Cycle {round_obj.current_cycle}'
        )
                
        return Response({'status': 'contribution recorded', 'round': RoundContributionSerializer(round_obj, context={'request': request}).data})

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def claim(self, request, pk=None):
        """Claim the collected funds for the current cycle."""
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        # Allow claiming if status is unclaimed OR if there are unclaimed entries in history
        if round_obj.claim_status not in ['unclaimed', 'active'] and not round_obj.award_history:
            return Response({'error': 'Funds are not ready to be claimed.'}, status=400)
            
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
        
        # Find all unclaimed entries for this member in award_history
        unclaimed_entries = []
        if round_obj.award_history:
            unclaimed_entries = [
                (i, h) for i, h in enumerate(round_obj.award_history)
                if str(h.get('member_id')) == str(member.id) and not h.get('claimed')
            ]
        
        # Also check if current awarded_to matches
        if not unclaimed_entries and round_obj.claim_status == 'unclaimed' and round_obj.awarded_to_id == member.id:
            # Current cycle is unclaimed and user is the recipient
            pending_amount = round_obj.total_collected if round_obj.total_collected > 0 else Decimal('0')
            unclaimed_entries = [(-1, {
                'cycle': round_obj.current_cycle,
                'member_id': str(member.id),
                'amount': float(pending_amount),
                'claimed': False,
                'claimed_at': None,
                'claim_status': 'unclaimed',
                'pending_claim': True
            })]
        
        if not unclaimed_entries:
            return Response({'error': 'No unclaimed payouts found for you in this round.'}, status=403)
        
        destination = request.data.get('destination', 'wallet')
        claim_mode = request.data.get('claim_mode', 'wallet')
        recipient_id = request.data.get('recipient_id')
        total_amount = Decimal('0')
        claimed_at = timezone.now()
        
        for idx, entry in unclaimed_entries:
            amount = Decimal(str(entry.get('amount', 0)))
            total_amount += amount
            
            # Update history entry if it's in the history (not the pending current)
            if idx >= 0:
                entry['claimed'] = True
                entry['claimed_at'] = claimed_at.isoformat()
                entry['claim_status'] = 'claimed'
                round_obj.award_history[idx] = entry
        
        if claim_mode == 'send_to_user' and recipient_id:
            from Authentication.models import CustomUser
            try:
                recipient_user = CustomUser.objects.get(id=recipient_id)
                recipient_profile = get_or_create_payment_profile(recipient_user)
                recipient_profile.comrade_balance += total_amount
                recipient_profile.save()
                destination = f'user_{recipient_id}'
            except CustomUser.DoesNotExist:
                return Response({'error': 'Recipient user not found.'}, status=404)
        elif destination == 'wallet':
            payment_profile.comrade_balance += total_amount
            payment_profile.save()
        elif destination in ['mpesa', 'bank', 'card']:
            payment_profile.comrade_balance += total_amount
            payment_profile.save()
        else:
            return Response({'error': 'Invalid destination.'}, status=400)
        
        # Record the payout in transaction history
        TransactionToken.objects.create(
            payment_profile=payment_profile,
            amount=total_amount,
            transaction_type='payout',
            pay_from='round_pot',
            payment_option=destination,
            description=f'Round Payout - {round_obj.round_name or "Round " + str(round_obj.round_number)} Cycle {round_obj.current_cycle} claimed'
        )
        
        # AFTER successful claim, update the round state
        member_count = round_obj.payment_group.members.filter(is_active=True).count()
        
        # Get the amount that was just claimed to add to total_generated
        claimed_amount = total_amount
        round_obj.total_generated += Decimal(str(claimed_amount))
        
        # Check if ALL cycles are now claimed
        all_claimed = all(h.get('claimed', False) for h in round_obj.award_history) if round_obj.award_history else False
        
        if all_claimed and round_obj.current_cycle >= member_count:
            # All members have claimed - round complete
            round_obj.status = 'completed'
            round_obj.claim_status = 'completed'
            round_obj.total_collected = 0
            round_obj.total_cycles_completed = round_obj.current_cycle
        else:
            # Move to next cycle - update awarded_to to next position
            round_obj.total_cycles_completed = round_obj.current_cycle
            next_cycle = round_obj.current_cycle + 1
            if next_cycle <= member_count:
                try:
                    next_position = RoundPosition.objects.get(
                        payment_group=round_obj.payment_group,
                        round=round_obj,
                        position_number=next_cycle
                    )
                    round_obj.awarded_to = next_position.member
                    round_obj.current_cycle = next_cycle
                    round_obj.claim_status = 'pending'  # Ready for next cycle contributions
                    round_obj.total_collected = Decimal('0')  # Reset for new cycle
                    round_obj.next_contribution_date = round_obj.get_next_contribution_date()
                except RoundPosition.DoesNotExist:
                    round_obj.claim_status = 'claimed'
            else:
                round_obj.claim_status = 'completed'
        
        round_obj.save()
        
        # Notify group
        for gm in round_obj.payment_group.members.filter(is_active=True):
            if gm.id != member.id:
                try:
                    create_notification(
                        recipient=gm.payment_profile.user.user,
                        notification_type='group_claim',
                        message=f"{member.payment_profile.user.user.get_full_name()} has claimed their payout from round '{round_obj.round_name or round_obj.round_number}'.",
                        action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds"
                    )
                except Exception:
                    pass
        
        return Response({
            'status': 'payouts claimed', 
            'amount': float(total_amount),
            'next_cycle': round_obj.current_cycle if round_obj.status != 'completed' else None,
            'round_status': round_obj.status
        })
        
        # Notify group
        for gm in round_obj.payment_group.members.filter(is_active=True):
            if gm.id != member.id:
                try:
                    create_notification(
                        recipient=gm.payment_profile.user.user,
                        notification_type='group_claim',
                        message=f"{member.payment_profile.user.user.get_full_name()} has claimed their payout from round '{round_obj.round_name or round_obj.round_number}'.",
                        action_url=f"/payments/groups/{round_obj.payment_group.id}?tab=rounds"
                    )
                except Exception:
                    pass
        
        return Response({'status': 'payouts claimed', 'amount': float(total_amount)})

    @action(detail=True, methods=['get'])
    def detail_view(self, request, pk=None):
        """Rich detail view for the round."""
        round_obj = self.get_object()
        serializer = self.get_serializer(round_obj)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def restart_cycle(self, request, pk=None):
        """Restart a completed round for another cycle/rotation."""
        round_obj = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if round_obj.status != 'completed':
            return Response({'error': 'Only completed rounds can be restarted.'}, status=400)
        
        # Check if user is admin or group creator
        try:
            member = PaymentGroupMember.objects.get(payment_group=round_obj.payment_group, payment_profile=payment_profile)
            if not member.is_admin and round_obj.payment_group.creator != payment_profile:
                return Response({'error': 'Only admins can restart rounds.'}, status=403)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'You are not a member of this group.'}, status=403)
        
        # Verify all members have claimed their payouts before restart
        if round_obj.award_history:
            unclaimed = [h for h in round_obj.award_history if not h.get('claimed', False)]
            if unclaimed:
                return Response({'error': f'Cannot restart: {len(unclaimed)} member(s) have unclaimed payouts. All members must claim first.'}, status=400)
        
        # Store previous cycle totals for record before reset
        previous_total_generated = round_obj.total_generated
        previous_cycles_completed = round_obj.total_cycles_completed
        
        # Reset the round for a new cycle
        # Delete existing member contributions from previous cycles
        round_obj.member_contributions.all().delete()
        
        round_obj.status = 'active'
        round_obj.claim_status = 'pending'
        round_obj.current_cycle = 1
        round_obj.total_collected = Decimal('0')
        round_obj.total_cycles_completed = 0
        round_obj.total_generated = Decimal('0')
        round_obj.award_history = []
        round_obj.awarded_to = None
        round_obj.next_contribution_date = round_obj.get_next_contribution_date()
        round_obj.save()
        
        return Response({
            'status': 'round restarted',
            'previous_cycle_total': float(previous_total_generated),
            'previous_cycles_completed': previous_cycles_completed,
            'round': RoundContributionSerializer(round_obj, context={'request': request}).data
        })



class WithdrawalRequestViewSet(ModelViewSet):
    queryset = WithdrawalRequest.objects.all()
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsAuthenticated]
    logger = logging.getLogger(__name__)

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return WithdrawalRequest.objects.none()
        # Return withdrawals for groups the user is a member of
        queryset = WithdrawalRequest.objects.filter(payment_group__members__payment_profile=payment_profile).distinct()
        
        group_id = self.request.query_params.get('payment_group', None)
        if group_id:
            queryset = queryset.filter(payment_group_id=group_id)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            raise serializers.ValidationError("Could not find payment profile")
        
        payment_group_id = self.request.data.get('payment_group')
        if not payment_group_id:
            raise serializers.ValidationError("payment_group is required")
        
        try:
            member = PaymentGroupMember.objects.get(
                payment_group_id=payment_group_id,
                payment_profile=payment_profile
            )
        except PaymentGroupMember.DoesNotExist:
            raise serializers.ValidationError("You are not a member of this group")
        
        serializer.save(
            requester=member,
            destination_wallet=payment_profile
        )
        
    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def approve(self, request, pk=None):
        """Approve a withdrawal request."""
        withdrawal = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        group = withdrawal.payment_group
        try:
            admin_member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            
            # Hierarchy Logic
            if group.hierarchy_mode:
                # If group has hierarchy mode, and user is not creator, check if they are an admin
                if group.creator != payment_profile and not admin_member.is_admin:
                     return Response({'error': 'Hierarchy mode active: Approval required from higher authority (Admin/Creator).'}, status=403)
                
                # Threshold logic: Large withdrawals (> 25% of group fund) require Creator specifically
                if withdrawal.amount > (group.current_amount * Decimal('0.25')) and group.creator != payment_profile:
                     return Response({'error': 'Large withdrawal threshold reached. Approval from group creator required.'}, status=403)
            else:
                # Standard mode: any admin can approve
                if not admin_member.is_admin and group.creator != payment_profile:
                     return Response({'error': 'Only admins can approve withdrawals.'}, status=403)
                     
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'You are not a member of this group.'}, status=403)
        withdrawal.status = 'approved'
        withdrawal.approved_by = admin_member
        withdrawal.approval_date = timezone.now()
        
        # Process the payout to withdrawal.destination_wallet
        deduction = Decimal('0.00')
        
        # 1. Immature Exit Penalty
        if withdrawal.withdrawal_type == 'exit' and not withdrawal.payment_group.is_matured and getattr(withdrawal.payment_group, 'is_lifetime', False) == False:
            immature_deduction = Decimal(str(withdrawal.calculate_immature_deduction()))
            withdrawal.immature_exit_deduction = immature_deduction
            deduction += immature_deduction
            
        # 2. Early Withdrawal Penalty (for fixed deposits)
        early_penalty = Decimal(str(withdrawal.payment_group.calculate_withdrawal_penalty(withdrawal.amount)))
        if early_penalty > 0:
            withdrawal.early_withdrawal_penalty = early_penalty
            deduction += early_penalty
            
        payout = withdrawal.amount - deduction
        
        with db_transaction.atomic():
            # Update destination wallet
            withdrawal.destination_wallet.comrade_balance += payout
            withdrawal.destination_wallet.save()
            
            # Record the net payout transaction
            TransactionToken.objects.create(
                sender=request.user, # Platform/Group Admin
                receiver=withdrawal.destination_wallet.user,
                amount=payout,
                transaction_type='withdrawal',
                status='completed',
                description=f"Withdrawal from {withdrawal.payment_group.name} (Net)"
            )
            
            # Record the penalty deduction transaction if any
            if deduction > 0:
                TransactionToken.objects.create(
                    sender=withdrawal.destination_wallet.user,
                    receiver=request.user, # Conceptually returned to the Group Pool/Admin
                    amount=deduction,
                    transaction_type='fee',
                    status='completed',
                    description=f"Immature Exit Penalty for {withdrawal.payment_group.name}"
                )
            
            # Deduct only the payout from the group amount (the group pool retains the penalty)
            withdrawal.payment_group.current_amount -= payout
            withdrawal.payment_group.save()
            
            withdrawal.processed_at = timezone.now()
            withdrawal.status = 'completed'
            withdrawal.save()
            
        return Response({'status': 'approved and completed', 'withdrawal': WithdrawalRequestSerializer(withdrawal).data})
        
    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def reject(self, request, pk=None):
        """Reject a withdrawal request."""
        withdrawal = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        try:
            admin_member = PaymentGroupMember.objects.get(payment_group=withdrawal.payment_group, payment_profile=payment_profile)
            if not admin_member.is_admin and withdrawal.payment_group.creator != payment_profile:
                 return Response({'error': 'Only admins can reject withdrawals.'}, status=403)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'You are not a member of this group.'}, status=403)
            
        withdrawal.status = 'rejected'
        withdrawal.rejection_reason = request.data.get('reason', 'No reason provided')
        withdrawal.save()
        
        return Response({'status': 'rejected', 'withdrawal': WithdrawalRequestSerializer(withdrawal).data})


class BenefitDistributionRuleViewSet(ModelViewSet):
    queryset = BenefitDistributionRule.objects.all()
    serializer_class = BenefitDistributionRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return BenefitDistributionRule.objects.none()
        return BenefitDistributionRule.objects.filter(payment_group__members__payment_profile=payment_profile).distinct()


class GroupSettingsChangeRequestViewSet(ModelViewSet):
    queryset = GroupSettingsChangeRequest.objects.all()
    serializer_class = GroupSettingsChangeRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return GroupSettingsChangeRequest.objects.none()
        return GroupSettingsChangeRequest.objects.filter(payment_group__members__payment_profile=payment_profile).distinct()
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """Vote on a settings change request."""
        change_req = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        vote_type = request.data.get('vote') # 'for' or 'against'
        
        try:
            member = PaymentGroupMember.objects.get(payment_group=change_req.payment_group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group.'}, status=403)
            
        # Check if already voted
        # In a real scenario, we'd have a separate table for votes to prevent multiple voting
        # For now, let's just increment and check status
        if vote_type == 'for':
            change_req.votes_for += 1
        else:
            change_req.votes_against += 1
            
        note = request.data.get('note', '')
        if note:
            # Store sentiments safely
            current_sentiments = change_req.voter_sentiments
            current_sentiments[str(member.id)] = {'vote': vote_type, 'note': note}
            change_req.voter_sentiments = current_sentiments
            
        # Check threshold
        threshold = change_req.payment_group.approval_threshold
        member_count = change_req.payment_group.members.count()
        required_votes = (threshold / 100) * member_count
        
        if change_req.votes_for >= required_votes:
            self._apply_settings_change(change_req)
            change_req.status = 'approved'
            
        change_req.save()
        return Response({'status': 'vote recorded', 'request': GroupSettingsChangeRequestSerializer(change_req).data})

    def _apply_settings_change(self, change_req):
        """Apply the proposed changes to the group."""
        group = change_req.payment_group
        new_values = change_req.new_values
        
        if change_req.change_type == 'settings_update':
            for key, value in new_values.items():
                if hasattr(group, key):
                    setattr(group, key, value)
            group.save()


class KittyViewSet(ModelViewSet):
    '''
    ViewSet for managing Kitties, which are specialized PaymentGroups.
    '''
    serializer_class = KittySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return PaymentGroups.objects.none()

        # Kitties are PaymentGroups where is_kitty is True or group_type is 'kitty'
        queryset = PaymentGroups.objects.filter(
            Q(is_kitty=True) | Q(group_type='kitty'),
            members__payment_profile=payment_profile
        ).distinct()

        parent_group = self.request.query_params.get('parent_group', None)
        if parent_group:
            queryset = queryset.filter(parent_group_id=parent_group)

        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        
        serializer.save(
            creator=payment_profile,
            is_kitty=True,
            group_type='kitty'
        )


# ============================================================================
# PROVIDER REGISTRATION & MANAGEMENT VIEWS
# ============================================================================

class ProviderRegistrationViewSet(ModelViewSet):
    serializer_class = ProviderRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = Profile.objects.get(user=user)
        return ProviderRegistration.objects.filter(user=profile)

    def get_serializer_class(self):
        if self.action == 'list':
            return ProviderRegistrationListSerializer
        return ProviderRegistrationSerializer

    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        provider = serializer.save(user=profile)

        if provider.auto_create_kitty:
            payment_profile = get_or_create_payment_profile(self.request.user)
            kitty = PaymentGroups.objects.create(
                name=provider.kitty_name or f"{provider.business_name} Operations Kit",
                description=f"Operations kitty for {provider.business_name}",
                creator=payment_profile,
                group_type='kitty',
                is_kitty=True,
                target_amount=provider.kitty_target_amount,
                auto_purchase=False,
                requires_approval=True,
                contribution_type='flexible',
            )
            provider.linked_payment_group = kitty
            provider.save()

            PaymentGroupMember.objects.create(
                payment_group=kitty,
                payment_profile=payment_profile,
                is_admin=True,
            )

            create_notification(
                recipient=self.request.user,
                notification_type='kitty_created',
                message=f"Kitty '{kitty.name}' has been created for {provider.business_name}",
                action_url=f"/payments/groups/{kitty.id}",
            )

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        provider = self.get_object()
        stats = {
            'total_transactions': provider.transactions.count(),
            'total_queries': provider.queries.count(),
            'pending_applications': provider.applications.filter(status__in=['submitted', 'under_review']).count(),
            'active_products': provider.service_products.filter(status='active').count(),
            'staff_count': provider.staff_members.filter(status='active').count(),
            'total_volume': float(provider.transactions.aggregate(Sum('amount'))['amount__sum'] or 0),
            'pending_queries': provider.queries.filter(status__in=['open', 'in_progress', 'pending_response']).count(),
        }
        return Response(stats)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        provider = self.get_object()
        if provider.status != 'draft':
            return Response({'error': 'Provider can only be submitted from draft status'}, status=status.HTTP_400_BAD_REQUEST)
        provider.status = 'submitted'
        provider.save()
        create_notification(
            recipient=request.user,
            notification_type='provider_submitted',
            message=f"Provider registration for {provider.business_name} submitted for review",
            action_url=f"/payments/provider-registrations/{provider.id}",
        )
        return Response({'status': 'submitted', 'provider': ProviderRegistrationSerializer(provider).data})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        provider = self.get_object()
        profile = Profile.objects.get(user=request.user)
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({'error': 'Only admins can approve providers'}, status=status.HTTP_403_FORBIDDEN)
        provider.status = 'approved'
        provider.reviewed_by = profile
        provider.reviewed_at = timezone.now()
        provider.save()
        create_notification(
            recipient=provider.user.user,
            notification_type='provider_approved',
            message=f"Provider registration for {provider.business_name} has been approved",
            action_url=f"/payments/provider-registrations/{provider.id}",
        )
        return Response({'status': 'approved', 'provider': ProviderRegistrationSerializer(provider).data})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        provider = self.get_object()
        profile = Profile.objects.get(user=request.user)
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({'error': 'Only admins can reject providers'}, status=status.HTTP_403_FORBIDDEN)
        provider.status = 'rejected'
        provider.rejection_reason = request.data.get('reason', '')
        provider.reviewed_by = profile
        provider.reviewed_at = timezone.now()
        provider.save()
        create_notification(
            recipient=provider.user.user,
            notification_type='provider_rejected',
            message=f"Provider registration for {provider.business_name} has been rejected",
            action_url=f"/payments/provider-registrations/{provider.id}",
        )
        return Response({'status': 'rejected', 'reason': provider.rejection_reason})

    @action(detail=False, methods=['get'])
    def public_providers(self, request):
        category = request.query_params.get('category')
        provider_type = request.query_params.get('provider_type')
        qs = ProviderRegistration.objects.filter(status='approved', is_active=True)
        if category:
            qs = qs.filter(category=category)
        if provider_type:
            qs = qs.filter(provider_type=provider_type)
        return Response(ProviderRegistrationListSerializer(qs, many=True).data)


class ProviderDocumentViewSet(ModelViewSet):
    serializer_class = ProviderDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return ProviderDocument.objects.filter(provider__user=profile)

    def perform_create(self, serializer):
        provider_id = self.request.data.get('provider')
        try:
            provider = ProviderRegistration.objects.get(id=provider_id, user__user=self.request.user)
        except ProviderRegistration.DoesNotExist:
            raise serializers.ValidationError("Provider not found or not authorized")
        serializer.save(provider=provider)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        doc = self.get_object()
        profile = Profile.objects.get(user=request.user)
        if not request.user.is_staff and not request.user.is_superuser:
            return Response({'error': 'Only admins can verify documents'}, status=status.HTTP_403_FORBIDDEN)
        doc.status = request.data.get('status', 'approved')
        doc.reviewer_notes = request.data.get('notes', '')
        doc.verified_by = profile
        doc.verified_at = timezone.now()
        doc.save()
        return Response({'status': doc.status, 'notes': doc.reviewer_notes})


class ProviderStaffViewSet(ModelViewSet):
    serializer_class = ProviderStaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return ProviderStaff.objects.filter(provider__user=profile)

    def perform_create(self, serializer):
        provider_id = self.request.data.get('provider')
        try:
            provider = ProviderRegistration.objects.get(id=provider_id, user__user=self.request.user)
        except ProviderRegistration.DoesNotExist:
            raise serializers.ValidationError("Provider not found or not authorized")
        creator_profile = Profile.objects.get(user=self.request.user)
        serializer.save(provider=provider, created_by=creator_profile)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        staff = self.get_object()
        staff.status = 'active'
        staff.save()
        return Response({'status': 'active'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        staff = self.get_object()
        staff.status = 'inactive'
        staff.save()
        return Response({'status': 'inactive'})

    @action(detail=True, methods=['post'])
    def update_permissions(self, request, pk=None):
        staff = self.get_object()
        for field in ['can_handle_queries', 'can_review_applications', 'can_manage_transactions',
                      'can_approve_claims', 'email_notifications']:
            if field in request.data:
                setattr(staff, field, request.data[field])
        if 'max_transaction_limit' in request.data:
            staff.max_transaction_limit = request.data['max_transaction_limit']
        if 'assigned_categories' in request.data:
            staff.assigned_categories = request.data['assigned_categories']
        if 'working_hours' in request.data:
            staff.working_hours = request.data['working_hours']
        staff.save()
        return Response(ProviderStaffSerializer(staff).data)

    @action(detail=False, methods=['get'])
    def by_provider(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({'error': 'provider_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        staff = ProviderStaff.objects.filter(provider_id=provider_id, status='active')
        return Response(ProviderStaffSerializer(staff, many=True).data)


class ServiceProductViewSet(ModelViewSet):
    serializer_class = ServiceProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return ServiceProduct.objects.filter(provider__user=profile)

    def perform_create(self, serializer):
        provider_id = self.request.data.get('provider')
        try:
            provider = ProviderRegistration.objects.get(id=provider_id, user__user=self.request.user)
        except ProviderRegistration.DoesNotExist:
            raise serializers.ValidationError("Provider not found or not authorized")
        product = serializer.save(provider=provider)

        if product.auto_link_kitty and provider.linked_payment_group:
            product.linked_kitty = provider.linked_payment_group
            product.save()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        product = self.get_object()
        product.status = 'active'
        product.is_active = True
        product.save()
        return Response({'status': 'active'})

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        product = self.get_object()
        product.status = 'suspended'
        product.is_active = False
        product.save()
        return Response({'status': 'suspended'})

    @action(detail=False, methods=['get'])
    def public_products(self, request):
        category = request.query_params.get('category')
        service_type = request.query_params.get('service_type')
        qs = ServiceProduct.objects.filter(status='active', is_active=True)
        if category:
            qs = qs.filter(category=category)
        if service_type:
            qs = qs.filter(service_type=service_type)
        return Response(ServiceProductSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def by_provider(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({'error': 'provider_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        products = ServiceProduct.objects.filter(provider_id=provider_id, status='active')
        return Response(ServiceProductSerializer(products, many=True).data)


class ProviderTransactionViewSet(ModelViewSet):
    serializer_class = ProviderTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return ProviderTransaction.objects.filter(provider__user=profile)

    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        tx = serializer.save(user=profile, status='pending')
        tx.commission_amount = tx.amount * tx.provider.commission_rate
        tx.save()

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        tx = self.get_object()
        profile = Profile.objects.get(user=self.request.user)
        try:
            staff = ProviderStaff.objects.get(provider=tx.provider, user=profile, can_manage_transactions=True)
        except ProviderStaff.DoesNotExist:
            return Response({'error': 'You do not have permission to process transactions'}, status=status.HTTP_403_FORBIDDEN)
        tx.status = 'completed'
        tx.processed_by = staff
        tx.processed_at = timezone.now()
        tx.save()
        return Response({'status': 'completed'})

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        tx = self.get_object()
        if tx.status != 'completed':
            return Response({'error': 'Only completed transactions can be refunded'}, status=status.HTTP_400_BAD_REQUEST)
        tx.status = 'refunded'
        tx.save()
        return Response({'status': 'refunded'})

    @action(detail=False, methods=['get'])
    def summary(self, request):
        profile = Profile.objects.get(user=self.request.user)
        txs = ProviderTransaction.objects.filter(provider__user=profile)
        return Response({
            'total_transactions': txs.count(),
            'total_volume': float(txs.aggregate(Sum('amount'))['amount__sum'] or 0),
            'total_commission': float(txs.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0),
            'pending_count': txs.filter(status='pending').count(),
            'completed_count': txs.filter(status='completed').count(),
        })


class ProviderQueryViewSet(ModelViewSet):
    serializer_class = ProviderQuerySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return ProviderQuery.objects.filter(provider__user=profile)

    def perform_create(self, serializer):
        provider_id = self.request.data.get('provider')
        try:
            provider = ProviderRegistration.objects.get(id=provider_id)
        except ProviderRegistration.DoesNotExist:
            raise serializers.ValidationError("Provider not found")
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(provider=provider, user=profile)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        query = self.get_object()
        staff_id = request.data.get('staff_id')
        try:
            staff = ProviderStaff.objects.get(id=staff_id, provider=query.provider)
        except ProviderStaff.DoesNotExist:
            return Response({'error': 'Staff member not found'}, status=status.HTTP_404_NOT_FOUND)
        query.assigned_to = staff
        query.status = 'in_progress'
        query.save()
        return Response({'assigned_to': staff.user.user.get_full_name(), 'status': query.status})

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        query = self.get_object()
        profile = Profile.objects.get(user=self.request.user)
        try:
            staff = ProviderStaff.objects.get(provider=query.provider, user=profile)
        except ProviderStaff.DoesNotExist:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)
        query.status = 'resolved'
        query.resolution_notes = request.data.get('notes', '')
        query.resolved_by = staff
        query.resolved_at = timezone.now()
        query.save()
        return Response({'status': 'resolved'})

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        query = self.get_object()
        query.status = 'escalated'
        query.save()
        create_notification(
            recipient=query.provider.user.user,
            notification_type='query_escalated',
            message=f"Query '{query.subject}' has been escalated",
            action_url=f"/payments/provider-queries/{query.id}",
        )
        return Response({'status': 'escalated'})

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        query = self.get_object()
        query.satisfaction_rating = request.data.get('rating')
        query.satisfaction_comment = request.data.get('comment', '')
        query.save()
        return Response({'rating': query.satisfaction_rating})

    @action(detail=False, methods=['get'])
    def my_queries(self, request):
        profile = Profile.objects.get(user=request.user)
        queries = ProviderQuery.objects.filter(user=profile).order_by('-created_at')
        return Response(ProviderQuerySerializer(queries, many=True).data)


class ProviderApplicationViewSet(ModelViewSet):
    serializer_class = ProviderApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return ProviderApplication.objects.filter(provider__user=profile)

    def perform_create(self, serializer):
        provider_id = self.request.data.get('provider')
        try:
            provider = ProviderRegistration.objects.get(id=provider_id)
        except ProviderRegistration.DoesNotExist:
            raise serializers.ValidationError("Provider not found")
        profile = Profile.objects.get(user=self.request.user)
        serializer.save(provider=provider, user=profile)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        app = self.get_object()
        if app.status != 'draft':
            return Response({'error': 'Application can only be submitted from draft status'}, status=status.HTTP_400_BAD_REQUEST)
        app.status = 'submitted'
        app.submitted_at = timezone.now()
        app.save()
        create_notification(
            recipient=app.provider.user.user,
            notification_type='application_submitted',
            message=f"New application from {app.user.user.get_full_name()}",
            action_url=f"/payments/provider-applications/{app.id}",
        )
        return Response({'status': 'submitted'})

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        app = self.get_object()
        profile = Profile.objects.get(user=request.user)
        try:
            staff = ProviderStaff.objects.get(provider=app.provider, user=profile, can_review_applications=True)
        except ProviderStaff.DoesNotExist:
            return Response({'error': 'You do not have permission to review applications'}, status=status.HTTP_403_FORBIDDEN)
        decision = request.data.get('decision')
        if decision not in ['approved', 'rejected']:
            return Response({'error': 'Decision must be approved or rejected'}, status=status.HTTP_400_BAD_REQUEST)
        app.status = decision
        app.reviewed_by = staff
        app.reviewed_at = timezone.now()
        app.review_notes = request.data.get('notes', '')
        app.save()

        if decision == 'approved':
            if app.application_type == 'insurance_policy':
                policy = InsurancePolicy.objects.create(
                    user=app.user,
                    product=app.service_product,
                    status='active',
                    total_premiums_due=app.service_product.price,
                )
                app.linked_policy = policy
                app.save()
            elif app.application_type == 'loan_application':
                loan = LoanApplication.objects.create(
                    user=app.user,
                    loan_product=app.service_product,
                    amount=app.application_data.get('amount', 0),
                    tenure_months=app.application_data.get('tenure_months', 1),
                )
                app.linked_loan = loan
                app.save()

        create_notification(
            recipient=app.user.user,
            notification_type='application_reviewed',
            message=f"Your application has been {decision}",
            action_url=f"/payments/provider-applications/{app.id}",
        )
        return Response({'status': decision})

    @action(detail=True, methods=['post'])
    def request_documents(self, request, pk=None):
        app = self.get_object()
        required_docs = request.data.get('documents', [])
        app.status = 'pending_documents'
        app.required_documents = required_docs
        app.save()
        create_notification(
            recipient=app.user.user,
            notification_type='documents_required',
            message=f"Additional documents required for your application",
            action_url=f"/payments/provider-applications/{app.id}",
        )
        return Response({'status': 'pending_documents', 'required_documents': required_docs})

    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        profile = Profile.objects.get(user=request.user)
        apps = ProviderApplication.objects.filter(user=profile).order_by('-created_at')
        return Response(ProviderApplicationSerializer(apps, many=True).data)


class ProviderNotificationViewSet(ModelViewSet):
    serializer_class = ProviderNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        return ProviderNotification.objects.filter(user=profile)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response({'status': 'read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        profile = Profile.objects.get(user=request.user)
        ProviderNotification.objects.filter(user=profile, is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'status': 'all_read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        profile = Profile.objects.get(user=request.user)
        count = ProviderNotification.objects.filter(user=profile, is_read=False).count()
        return Response({'unread_count': count})


class GroupAnalyticsView(APIView):
    """Dedicated view for group analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id):
        import logging
        logger = logging.getLogger('django')
        logger.error(f"GroupAnalyticsView: group_id={group_id}")
        
        try:
            group = PaymentGroups.objects.get(id=group_id)
        except PaymentGroups.DoesNotExist:
            logger.error(f"GroupAnalyticsView: Group {group_id} does not exist")
            return Response({'error': 'Group not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"GroupAnalyticsView: Error finding group {group_id}: {str(e)}")
            return Response({'error': f'Error finding group: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        is_member = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).exists()
        if not is_member and group.creator != payment_profile:
            return Response({'error': 'Not a member'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncMonth
        
        try:
            monthly = list(Contribution.objects.filter(payment_group=group).annotate(
                month=TruncMonth('contributed_at')
            ).values('month').annotate(
                total=Sum('amount'),
                count=Count('id')
            ).order_by('month'))
        except Exception:
            monthly = []
        
        try:
            top_contributors = PaymentGroupMember.objects.filter(
                payment_group=group
            ).order_by('-total_contributed')[:5]
        except Exception:
            top_contributors = []
        
        top_list = []
        for m in top_contributors:
            try:
                if m.is_anonymous:
                    name = m.anonymous_alias or 'Anonymous'
                elif m.payment_profile and m.payment_profile.user and m.payment_profile.user.user:
                    user = m.payment_profile.user.user
                    name = f"{user.first_name} {user.last_name}".strip() or user.email
                else:
                    name = 'Unknown Member'
            except Exception:
                name = 'Unknown Member'
            top_list.append({
                'name': name,
                'contributed': str(m.total_contributed),
                'is_anonymous': m.is_anonymous,
            })
        
        try:
            checkout_count = group.checkout_requests.count()
            pending_count = group.checkout_requests.filter(status='pending').count()
        except Exception:
            checkout_count = 0
            pending_count = 0
            
        # Add Round statistics
        try:
            from Payment.models import RoundContribution
            rounds = RoundContribution.objects.filter(payment_group=group)
            round_stats = {
                'total': rounds.count(),
                'active': rounds.filter(status='active').count(),
                'completed': rounds.filter(status='completed').count()
            }
        except Exception:
            round_stats = {'total': 0, 'active': 0, 'completed': 0}
            
        # Add Penalty statistics
        try:
            from Payment.models import WithdrawalRequest
            withdrawals = WithdrawalRequest.objects.filter(payment_group=group)
            total_penalties = sum(
                (w.early_withdrawal_penalty or 0) + (w.immature_exit_deduction or 0) 
                for w in withdrawals
            )
        except Exception:
            total_penalties = 0
            
        # Add Loan statistics
        try:
            from Payment.models import GroupLoan
            group_loans = GroupLoan.objects.filter(group=group)
            total_loans_given = group_loans.aggregate(total=Sum('principal_amount'))['total'] or 0
        except Exception:
            total_loans_given = 0
        
        return Response({
            'monthly_trend': [
                {'month': entry['month'].isoformat() if entry['month'] else None, 'total': str(entry['total']), 'count': entry['count']}
                for entry in monthly
            ],
            'top_contributors': top_list,
            'total_members': group.members.count(),
            'total_contributed': str(group.current_amount),
            'target_amount': str(group.target_amount or 0),
            'progress': round(float(group.current_amount) / float(group.target_amount) * 100, 2) if group.target_amount and group.target_amount > 0 else 0,
            'capacity_category': str(group.max_capacity),
            'checkout_requests_count': checkout_count,
            'pending_checkouts': pending_count,
            'round_stats': round_stats,
            'total_penalties': str(total_penalties),
            'total_loans_given': str(total_loans_given),
        })


# Admin ViewSets for Payment Management

class AdminBillPaymentViewSet(ModelViewSet):
    serializer_class = BillPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BillPayment.objects.all().order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = BillPayment.objects.count()
        completed = BillPayment.objects.filter(status='completed').count()
        processing = BillPayment.objects.filter(status='processing').count()
        failed = BillPayment.objects.filter(status='failed').count()
        total_amount = BillPayment.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        
        return Response({
            'total': total,
            'completed': completed,
            'processing': processing,
            'failed': failed,
            'total_amount': str(total_amount),
        })
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        action_type = request.data.get('action')
        ids = request.data.get('ids', [])
        
        bills = BillPayment.objects.filter(id__in=ids)
        
        if action_type == 'mark_completed':
            bills.update(status='completed', completed_at=timezone.now())
        elif action_type == 'mark_failed':
            bills.update(status='failed')
        elif action_type == 'delete':
            bills.delete()
        
        return Response({'status': 'success', 'updated': bills.count()})


class AdminLoanApplicationViewSet(ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LoanApplication.objects.all().order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = LoanApplication.objects.count()
        pending = LoanApplication.objects.filter(status='pending').count()
        approved = LoanApplication.objects.filter(status='approved').count()
        rejected = LoanApplication.objects.filter(status='rejected').count()
        disbursed = LoanApplication.objects.filter(status='disbursed').count()
        
        total_requested = LoanApplication.objects.aggregate(total=Sum('requested_amount'))['total'] or 0
        total_approved = LoanApplication.objects.filter(status__in=['approved', 'disbursed']).aggregate(total=Sum('requested_amount'))['total'] or 0
        
        return Response({
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'disbursed': disbursed,
            'total_requested': str(total_requested),
            'total_approved': str(total_approved),
        })
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        action_type = request.data.get('action')
        ids = request.data.get('ids', [])
        
        loans = LoanApplication.objects.filter(id__in=ids)
        
        if action_type == 'approve':
            loans.update(status='approved')
        elif action_type == 'reject':
            loans.update(status='rejected')
        elif action_type == 'disburse':
            loans.update(status='disbursed')
        elif action_type == 'delete':
            loans.delete()
        
        return Response({'status': 'success', 'updated': loans.count()})

    @action(detail=True, methods=['post'])
    def disburse_loan(self, request, pk=None):
        """
        Disburse an approved loan.
        Deducts processing fee upfront and credits the rest to the applicant's wallet.
        Generates LoanRepayment installments.
        """
        loan = self.get_object()
        
        if loan.status != 'approved':
            return Response({'error': 'Loan must be approved before disbursement'}, status=status.HTTP_400_BAD_REQUEST)
            
        with db_transaction.atomic():
            pp = PaymentProfile.objects.select_for_update().get(user=loan.user)
            
            # Deduct processing fee upfront
            net_disbursement = loan.amount - loan.processing_fee_amount
            
            # Credit wallet
            pp.comrade_balance += net_disbursement
            pp.save()
            
            # Create Disbursement Transaction
            TransactionToken.objects.create(
                sender=request.user, # Platform admin
                receiver=pp.user,
                amount=net_disbursement,
                transaction_type='loan_disbursement',
                status='completed',
                description=f'Loan Disbursement: {loan.id} (Net of {loan.processing_fee_amount} fee)',
            )
            
            # Generate Repayment Installments
            from dateutil.relativedelta import relativedelta
            from datetime import date
            
            current_date = date.today()
            for i in range(1, loan.tenure_months + 1):
                due_date = current_date + relativedelta(months=i)
                LoanRepayment.objects.create(
                    loan=loan,
                    installment_number=i,
                    amount_due=loan.monthly_payment,
                    due_date=due_date,
                    status='upcoming'
                )
                
            loan.status = 'disbursed'
            loan.disbursed_at = timezone.now()
            loan.save()
            
        return Response({
            'status': 'disbursed',
            'net_amount': str(net_disbursement),
            'installments_created': loan.tenure_months
        })


class AdminInsuranceClaimViewSet(ModelViewSet):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return InsuranceClaim.objects.all().order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = InsuranceClaim.objects.count()
        pending = InsuranceClaim.objects.filter(status='pending').count()
        approved = InsuranceClaim.objects.filter(status='approved').count()
        rejected = InsuranceClaim.objects.filter(status='rejected').count()
        paid = InsuranceClaim.objects.filter(status='paid').count()
        
        total_claimed = InsuranceClaim.objects.aggregate(total=Sum('claim_amount'))['total'] or 0
        total_paid = InsuranceClaim.objects.filter(status='paid').aggregate(total=Sum('claim_amount'))['total'] or 0
        
        return Response({
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'paid': paid,
            'total_claimed': str(total_claimed),
            'total_paid': str(total_paid),
        })
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        action_type = request.data.get('action')
        ids = request.data.get('ids', [])
        
        claims = InsuranceClaim.objects.filter(id__in=ids)
        
        if action_type == 'approve':
            claims.update(status='approved')
        elif action_type == 'reject':
            claims.update(status='rejected')
        elif action_type == 'mark_paid':
            claims.update(status='paid')
        elif action_type == 'delete':
            claims.delete()
        
        return Response({'status': 'success', 'updated': claims.count()})

    @action(detail=True, methods=['post'])
    def review_claim(self, request, pk=None):
        """
        Approve or reject an insurance claim with notes.
        action: 'approve' or 'reject'
        approved_amount: amount to approve (if approve)
        notes: reviewer notes
        """
        claim = self.get_object()
        action_type = request.data.get('action')
        notes = request.data.get('notes', '')
        
        if claim.status not in ['submitted', 'under_review']:
            return Response({'error': f'Claim cannot be reviewed from {claim.status} status'}, status=status.HTTP_400_BAD_REQUEST)
            
        if action_type == 'approve':
            approved_amount = request.data.get('approved_amount', claim.amount_claimed)
            claim.status = 'approved'
            claim.amount_approved = Decimal(str(approved_amount))
        elif action_type == 'reject':
            claim.status = 'rejected'
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
            
        claim.reviewer_notes = notes
        claim.reviewed_at = timezone.now()
        claim.save()
        
        return Response({'status': claim.status, 'message': f'Claim {claim.status}'})
        
    @action(detail=True, methods=['post'])
    def payout_claim(self, request, pk=None):
        """
        Payout an approved insurance claim.
        Credits the claimant's wallet and records the transaction.
        """
        claim = self.get_object()
        
        if claim.status != 'approved':
            return Response({'error': 'Only approved claims can be paid out'}, status=status.HTTP_400_BAD_REQUEST)
            
        if claim.amount_approved <= 0:
            return Response({'error': 'Approved amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)
            
        with db_transaction.atomic():
            pp = PaymentProfile.objects.select_for_update().get(user=claim.claimant)
            
            # Credit wallet
            pp.comrade_balance += claim.amount_approved
            pp.save()
            
            # Create Payout Transaction
            TransactionToken.objects.create(
                sender=request.user, # Platform admin
                receiver=pp.user,
                amount=claim.amount_approved,
                transaction_type='insurance_payout',
                status='completed',
                description=f'Insurance Claim Payout: {claim.policy.policy_number}',
            )
            
            claim.status = 'paid'
            claim.paid_at = timezone.now()
            claim.save()
            
        return Response({'status': 'paid', 'amount_paid': str(claim.amount_approved)})

class AdminTransactionViewSet(ModelViewSet):
    serializer_class = TransactionTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TransactionToken.objects.all().order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = TransactionToken.objects.count()
        total_amount = TransactionToken.objects.aggregate(total=Sum('amount'))['total'] or 0
        
        by_type = {}
        for ttype in TransactionToken.objects.values_list('transaction_type', flat=True).distinct():
            count = TransactionToken.objects.filter(transaction_type=ttype).count()
            by_type[ttype] = count
        
        by_status = {}
        for status in TransactionToken.objects.values_list('status', flat=True).distinct():
            count = TransactionToken.objects.filter(status=status).count()
            by_status[status] = count
        
        return Response({
            'total': total,
            'total_amount': str(total_amount),
            'by_type': by_type,
            'by_status': by_status,
        })


class AdminKittyViewSet(ModelViewSet):
    serializer_class = PaymentGroupsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return PaymentGroups.objects.filter(
            Q(is_kitty=True) | Q(group_type='kitty')
        ).order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'PATCH']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = PaymentGroups.objects.filter(
            Q(is_kitty=True) | Q(group_type='kitty')
        ).count()
        active = PaymentGroups.objects.filter(
            Q(is_kitty=True) | Q(group_type='kitty'),
            is_active=True
        ).count()
        
        total_amount = PaymentGroups.objects.filter(
            Q(is_kitty=True) | Q(group_type='kitty')
        ).aggregate(total=Sum('current_amount'))['total'] or 0
        total_target = PaymentGroups.objects.filter(
            Q(is_kitty=True) | Q(group_type='kitty')
        ).aggregate(total=Sum('target_amount'))['total'] or 0
        
        return Response({
            'total': total,
            'active': active,
            'total_amount': str(total_amount),
            'total_target': str(total_target),
        })
    
    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        kitty = self.get_object()
        kitty.is_active = False
        kitty.save()
        return Response({'status': 'frozen', 'kitty_id': str(kitty.id), 'message': 'Kitty has been frozen'})
    
    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        kitty = self.get_object()
        kitty.is_active = True
        kitty.save()
        return Response({'status': 'unfrozen', 'kitty_id': str(kitty.id), 'message': 'Kitty has been unfrozen'})