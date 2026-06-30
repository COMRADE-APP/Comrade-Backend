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
from django.db.models import Q, Sum, F, Avg
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import uuid
import secrets

from django.contrib.contenttypes.models import ContentType
from Funding.models import Business, CapitalVenture, InvestmentOpportunity
from Funding.serializers import InvestmentOpportunitySerializer

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
    PiggyBankConversionRequest, PiggyBankTransaction, PiggyBankMember,
    ProviderRegistration, ProviderDocument, ProviderStaff, ServiceProduct,
    ProviderTransaction, ProviderQuery, ProviderApplication, ProviderNotification,
    ProviderRating
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
    PiggyBankConversionRequestSerializer, PiggyBankMemberSerializer,
    ProviderRegistrationSerializer, ProviderRegistrationListSerializer, ProviderDocumentSerializer,
    ProviderStaffSerializer, ServiceProductSerializer, ProviderTransactionSerializer,
    ProviderQuerySerializer, ProviderApplicationSerializer, ProviderNotificationSerializer,
    ProviderRatingSerializer, ProviderRatingCreateSerializer
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
                    transaction = TransactionToken.objects.create(
                        payment_profile=payment_profile,
                        transaction_code=uuid.uuid4(),
                        amount=amount,
                        transaction_type='piggy_bank_contribution',
                        description=f'Contribution to Piggy Bank: {target.name}',
                        payment_group=target.payment_group,
                        piggy_bank=target
                    )
                    # Create user-facing transaction history
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
                        status='completed',
                        transaction_category='piggy_bank_contribution',
                        payment_type='group' if target.payment_group else 'individual',
                        balance_after=payment_profile.comrade_balance,
                        group_member_balance_after=member.total_contributed if member else None
                    )
                    # Log to dedicated piggy bank event log
                    PiggyBankTransaction.objects.create(
                        piggy_bank=target,
                        event_type='contribution',
                        amount=amount,
                        performed_by=payment_profile,
                        balance_after=target.current_amount,
                        note=item.get('notes', ''),
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

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Fetch all actionable pending approvals for the current user."""
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_404_NOT_FOUND)
        
        unified_list = []

        # 1. Group Checkout Requests (Pending votes from members/creator)
        checkout_requests = GroupCheckoutRequest.objects.filter(
            Q(group__members__payment_profile=payment_profile) | Q(group__creator=payment_profile),
            status='pending'
        ).distinct()

        for req in checkout_requests:
            has_voted = req.approvals.filter(id=payment_profile.id).exists() or req.rejections.filter(id=payment_profile.id).exists()

            if not has_voted:
                initiator_name = req.initiator.user.user.first_name if (req.initiator and hasattr(req.initiator, 'user') and hasattr(req.initiator.user, 'user')) else 'Anonymous'
                unified_list.append({
                    "id": str(req.id),
                    "request_type": "checkout",
                    "title": "Group Checkout Request",
                    "amount": str(req.amount),
                    "status": req.status,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                    "initiator_name": initiator_name,
                    "group_name": req.group.name if req.group else None,
                    "group_id": str(req.group.id) if req.group else None,
                    "target_id": str(req.id),
                    "approvals_count": req.approvals.count(),
                    "rejections_count": req.rejections.count(),
                    "total_members": req.group.members.count() if req.group else 0,
                    "metadata": {
                        "items_payload": req.items_payload
                    }
                })

        # 2. Withdrawal Requests (Needs approval from Admin/Creator)
        withdrawal_requests = WithdrawalRequest.objects.filter(
            payment_group__members__payment_profile=payment_profile,
            payment_group__members__is_admin=True,
            status='pending'
        ).distinct()

        for req in withdrawal_requests:
            initiator_name = req.requester.user.user.first_name if (req.requester and hasattr(req.requester, 'user') and hasattr(req.requester.user, 'user')) else 'Anonymous'
            unified_list.append({
                "id": str(req.id),
                "request_type": "withdrawal",
                "title": f"Withdrawal ({req.get_withdrawal_type_display()})",
                "amount": str(req.amount),
                "status": req.status,
                "created_at": req.created_at.isoformat() if hasattr(req, 'created_at') and req.created_at else None,
                "initiator_name": initiator_name,
                "group_name": req.payment_group.name if req.payment_group else None,
                "group_id": str(req.payment_group.id) if req.payment_group else None,
                "target_id": str(req.id),
                "approvals_count": 0,
                "rejections_count": 0,
                "total_members": 1,
                "metadata": {
                    "reason": req.reason
                }
            })

        # 3. Piggy Bank Conversions (Needs votes from group members)
        piggy_requests = PiggyBankConversionRequest.objects.filter(
            piggy_bank__payment_group__members__payment_profile=payment_profile,
            status='pending'
        ).distinct()

        for req in piggy_requests:
            try:
                member = PaymentGroupMember.objects.get(payment_group=req.piggy_bank.payment_group, payment_profile=payment_profile)
                has_voted = req.approving_members.filter(id=member.id).exists() or req.rejecting_members.filter(id=member.id).exists()
            except PaymentGroupMember.DoesNotExist:
                has_voted = False
                
            if not has_voted:
                unified_list.append({
                    "id": str(req.id),
                    "request_type": "piggy_bank",
                    "title": f"Piggy Bank Conversion ({req.get_conversion_type_display()})",
                    "amount": str(req.piggy_bank.current_amount) if req.piggy_bank else "0.00",
                    "status": req.status,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                    "initiator_name": "Group Member",
                    "group_name": req.piggy_bank.payment_group.name if req.piggy_bank and req.piggy_bank.payment_group else None,
                    "group_id": str(req.piggy_bank.payment_group.id) if req.piggy_bank and req.piggy_bank.payment_group else None,
                    "target_id": str(req.piggy_bank.id) if req.piggy_bank else None,
                    "approvals_count": req.approving_members.count(),
                    "rejections_count": req.rejecting_members.count(),
                    "total_members": req.piggy_bank.payment_group.members.count() if req.piggy_bank and req.piggy_bank.payment_group else 0,
                    "metadata": {
                        "piggy_bank_name": req.piggy_bank.name if req.piggy_bank else None,
                        "reason": req.reason
                    }
                })

        # 4. Loan Applications (Group loans needing Admin approval)
        from Payment.models import LoanApplication
        loan_requests = LoanApplication.objects.filter(
            group__members__payment_profile=payment_profile,
            group__members__is_admin=True,
            status='pending'
        ).distinct()

        for req in loan_requests:
            initiator_name = req.user.user.first_name if hasattr(req.user, 'user') else 'Anonymous'
            unified_list.append({
                "id": str(req.id),
                "request_type": "loan",
                "title": f"Loan Application ({req.loan_product.name if req.loan_product else 'Loan'})",
                "amount": str(req.amount),
                "status": req.status,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "initiator_name": initiator_name,
                "group_name": req.group.name if req.group else None,
                "group_id": str(req.group.id) if req.group else None,
                "target_id": str(req.id),
                "approvals_count": 0,
                "rejections_count": 0,
                "total_members": 1,
                "metadata": {
                    "purpose": req.purpose,
                    "tenure_months": req.tenure_months
                }
            })

        # 5. Escrow Transactions (Buyer needs to release funds when delivered/funded)
        from Payment.models import EscrowTransaction
        escrow_requests = EscrowTransaction.objects.filter(
            buyer=payment_profile.user,
            status__in=['funded', 'delivered']
        ).distinct()

        for req in escrow_requests:
            seller_name = req.seller.user.first_name if (req.seller and hasattr(req.seller, 'user')) else 'Anonymous Seller'
            unified_list.append({
                "id": str(req.id),
                "request_type": "escrow",
                "title": f"Escrow Release ({req.title})",
                "amount": str(req.total_amount),
                "status": req.status,
                "created_at": req.created_at.isoformat() if hasattr(req, 'created_at') and req.created_at else None,
                "initiator_name": seller_name,
                "group_name": None,
                "group_id": None,
                "target_id": str(req.id),
                "approvals_count": 0,
                "rejections_count": 0,
                "total_members": 1,
                "metadata": {
                    "escrow_type": req.escrow_type
                }
            })

        # 6. Group Invitations
        from Payment.models import GroupInvitation
        invitations = GroupInvitation.objects.filter(
            Q(invited_email=request.user.email) | Q(invited_profile=payment_profile),
            status='pending'
        ).distinct()

        for req in invitations:
            initiator_name = req.invited_by.user.user.first_name if (req.invited_by and hasattr(req.invited_by, 'user') and hasattr(req.invited_by.user, 'user')) else 'Group Admin'
            unified_list.append({
                "id": str(req.id),
                "request_type": "group_invitation",
                "title": f"Group Invitation to {req.payment_group.name if req.payment_group else 'Group'}",
                "amount": "0.00",
                "status": req.status,
                "created_at": req.created_at.isoformat() if hasattr(req, 'created_at') and req.created_at else None,
                "initiator_name": initiator_name,
                "group_name": req.payment_group.name if req.payment_group else None,
                "group_id": str(req.payment_group.id) if req.payment_group else None,
                "target_id": str(req.id),
                "approvals_count": 0,
                "rejections_count": 0,
                "total_members": 1,
                "metadata": {
                    "role": "Member" # Assuming role mapping here is simplified since it wasn't on the model directly
                }
            })

        # 7. Group Automations (Standing Orders requiring vote)
        from Payment.models import StandingOrder
        automations = StandingOrder.objects.filter(
            member__payment_group__members__payment_profile=payment_profile,
            status='pending_vote'
        ).distinct()
        
        for req in automations:
            try:
                member = PaymentGroupMember.objects.get(payment_group=req.member.payment_group, payment_profile=payment_profile)
                member_id = str(member.id)
                has_voted = (req.approval_votes and member_id in req.approval_votes) or (req.rejection_votes and member_id in req.rejection_votes)
            except PaymentGroupMember.DoesNotExist:
                has_voted = False

            if not has_voted:
                initiator_name = req.member.user.user.first_name if (req.member and hasattr(req.member, 'user') and hasattr(req.member.user, 'user')) else 'Anonymous'
                unified_list.append({
                    "id": str(req.id),
                    "request_type": "automation",
                    "title": f"Group Automation ({req.get_automation_type_display()})",
                    "amount": str(req.amount),
                    "status": req.status,
                    "created_at": req.created_at.isoformat() if hasattr(req, 'created_at') and req.created_at else None,
                    "initiator_name": initiator_name,
                    "group_name": req.member.payment_group.name if req.member.payment_group else None,
                    "group_id": str(req.member.payment_group.id) if req.member.payment_group else None,
                    "target_id": str(req.id),
                    "approvals_count": len(req.approval_votes) if req.approval_votes else 0,
                    "rejections_count": len(req.rejection_votes) if req.rejection_votes else 0,
                    "total_members": req.member.payment_group.members.count() if req.member.payment_group else 0,
                    "metadata": {
                        "frequency": req.frequency,
                    }
                })

        # 8. Piggy Bank Action Requests (Merge, Extend, Dissolve, Leave needing votes)
        from Payment.models import PiggyBankActionRequest
        piggy_action_requests = PiggyBankActionRequest.objects.filter(
            status='pending'
        ).exclude(
            action_type='withdraw'
        ).filter(
            Q(piggy_bank__payment_group__members__payment_profile=payment_profile) |
            Q(piggy_bank__owner=payment_profile) |
            Q(piggy_bank__piggy_members__payment_profile=payment_profile)
        ).distinct()

        for req in piggy_action_requests:
            has_voted = req.votes.filter(voter=payment_profile).exists()
            if not has_voted:
                initiator_name = 'Unknown'
                try:
                    initiator_name = req.requested_by.user.user.first_name if (req.requested_by and hasattr(req.requested_by, 'user') and hasattr(req.requested_by.user, 'user')) else 'Member'
                except Exception:
                    pass
                unified_list.append({
                    "id": str(req.id),
                    "request_type": "piggy_bank_action",
                    "title": f"Piggy Bank {req.get_action_type_display()} Request",
                    "amount": str(req.amount or 0),
                    "status": req.status,
                    "created_at": req.created_at.isoformat() if req.created_at else None,
                    "initiator_name": initiator_name,
                    "group_name": req.piggy_bank.payment_group.name if req.piggy_bank and req.piggy_bank.payment_group else None,
                    "group_id": str(req.piggy_bank.payment_group.id) if req.piggy_bank and req.piggy_bank.payment_group else None,
                    "target_id": str(req.piggy_bank.id) if req.piggy_bank else None,
                    "approvals_count": req.votes.filter(vote='approve').count(),
                    "rejections_count": req.votes.filter(vote='reject').count(),
                    "total_members": PiggyBankMember.objects.filter(piggy_bank=req.piggy_bank, is_active=True).count() if req.piggy_bank else 1,
                    "metadata": {
                        "action_type": req.action_type,
                        "piggy_bank_name": req.piggy_bank.name if req.piggy_bank else None,
                        "reason": req.reason,
                        "new_maturity_date": req.new_maturity_date.isoformat() if req.new_maturity_date else None,
                    }
                })

        # Sort combined list by created_at descending
        unified_list.sort(key=lambda x: x.get('created_at') or '', reverse=True)

        return Response(unified_list)

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
            
            serializer = TransactionTokenSerializer(tokens, many=True, context={'request': request})
            for t, t_data in zip(tokens, serializer.data):
                combined.append({
                    'id': str(t.transaction_code),
                    'transaction_code': str(t.transaction_code),
                    'type': t.transaction_type,
                    'transaction_type': t.transaction_type,
                    'transaction_category': t.transaction_type,
                    'amount': str(t.amount),
                    'status': t.status,
                    'created_at': t.created_at.isoformat() if t.created_at else None,
                    'description': t.description or f"{t.get_transaction_type_display()} - {t.get_payment_option_display()}",
                    'reference': str(t.transaction_code),
                    'source': 'transaction',
                    'payment_option': t.payment_option,
                    'direction': t_data.get('direction', 'unknown'),
                    'recipient_email': t_data.get('recipient_email'),
                    'recipient_name': t_data.get('recipient_name'),
                    'sender_email': t_data.get('sender_email'),
                    'sender_name': t_data.get('initiator_name'),
                    'initiator_name': t_data.get('initiator_name'),
                    'group_id': t_data.get('group_id'),
                    'group_name': t_data.get('group_name'),
                    'group_cover_photo': t_data.get('group_cover_photo'),
                    'payment_type': 'group' if t_data.get('group_id') else 'individual',
                    'can_be_reversed': t.status in ['completed', 'verified', 'settled'] and not t.reversed_at,
                    'balance_after': str(t.balance_after) if getattr(t, 'balance_after', None) is not None else None,
                    'transaction_details': t_data
                })
        except Exception as e:
            import logging
            logging.error(f"Error fetching TransactionToken: {e}")
        
        # Get Orders
        try:
            from Payment.models import Order
            orders = Order.objects.filter(
                buyer__user=user
            ).distinct().select_related('buyer', 'buyer__user', 'payment_group').prefetch_related('items', 'items__product').order_by('-created_at')[:100]
            
            for order in orders:
                combined.append({
                    'id': str(order.id),
                    'transaction_code': str(order.id),
                    'type': 'purchase',
                    'transaction_type': 'purchase',
                    'transaction_category': 'purchase',
                    'amount': str(order.total_amount),
                    'status': order.status,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'description': order.notes or f"Order #{order.order_number or str(order.id)[:8]} - {order.get_status_display()}",
                    'reference': str(order.id),
                    'source': 'order',
                    'payment_option': 'Wallet',
                    'direction': 'sent',
                    'recipient_email': None,
                    'recipient_name': 'Qomrade Shop',
                    'sender_email': user.email,
                    'sender_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'initiator_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'group_id': str(order.payment_group.id) if order.payment_group else None,
                    'group_name': order.payment_group.name if order.payment_group else None,
                    'group_cover_photo': order.payment_group.cover_photo.url if order.payment_group and order.payment_group.cover_photo else None,
                    'payment_type': order.payment_type or 'individual',
                    'can_be_reversed': False,
                    'balance_after': str(order.transaction_tokens.first().balance_after) if hasattr(order, 'transaction_tokens') and order.transaction_tokens.exists() and order.transaction_tokens.first().balance_after else None,
                    'transaction_details': {
                        'group_id': str(order.payment_group.id) if order.payment_group else None,
                        'group_name': order.payment_group.name if order.payment_group else None,
                        'recipient_name': 'Qomrade Shop',
                        'initiator_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    }
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

        # Only the sender can reverse a transaction
        if not is_sender:
            return Response({'error': 'Only the sender can reverse this transaction'}, status=status.HTTP_403_FORBIDDEN)

        sender_profile = transaction.payment_profile
        recipient_profile = transaction.recipient_profile

        # Lock both profiles for atomicity
        if recipient_profile:
            sender_profile = PaymentProfile.objects.select_for_update().get(pk=sender_profile.pk)
            recipient_profile = PaymentProfile.objects.select_for_update().get(pk=recipient_profile.pk)

            # Atomic deduction from recipient, credit to sender
            PaymentProfile.objects.filter(pk=recipient_profile.pk).update(
                comrade_balance=F('comrade_balance') - Decimal(str(transaction.amount))
            )
            PaymentProfile.objects.filter(pk=sender_profile.pk).update(
                comrade_balance=F('comrade_balance') + Decimal(str(transaction.amount))
            )
            sender_profile.refresh_from_db()
            recipient_profile.refresh_from_db()

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
            'new_balance': float(sender_profile.comrade_balance) if is_sender else float(recipient_profile.comrade_balance) if recipient_profile else 0
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
        
        # Create transaction record (pending — webhook will confirm)
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_type='deposit',
            amount=amount,
            payment_option=payment_method,
            pay_from='external',
            status='pending'
        )
        
        # Create history record (pending until webhook confirmation)
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
            status='pending'
        )
        
        return Response({
            'status': 'pending',
            'message': f'Deposit of ${amount:.2f} initiated. Awaiting payment confirmation.',
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
        inflow_types = ['contribution', 'deposit', 'round_contribution', 'loan_repayment', 'penalty_fee', 'fee', 'donation', 'piggy_bank_contribution']
        outflow_types = ['withdrawal', 'group_withdrawal', 'kitty_withdrawal', 'loan_disbursement', 'round_claim', 'round_payout', 'investment_payout', 'piggy_bank_withdrawal', 'refund']

        total_inflow = transactions.filter(
            transaction_type__in=inflow_types
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_outflow = transactions.filter(
            transaction_type__in=outflow_types
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Monthly trends (last 12 months)
        twelve_months_ago = timezone.now() - timedelta(days=365)
        monthly_trends = transactions.filter(
            created_at__gte=twelve_months_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            inflow=Sum('amount', filter=Q(transaction_type__in=inflow_types)),
            outflow=Sum('amount', filter=Q(transaction_type__in=outflow_types)),
            tx_count=Count('transaction_code')
        ).order_by('month')
        
        # Member contribution heatmap (member_id -> {month -> amount})
        member_heatmap = []
        for member in members.select_related('payment_profile', 'payment_profile__user'):
            member_txs = transactions.filter(
                payment_profile=member.payment_profile,
                transaction_type__in=['contribution', 'deposit', 'round_contribution', 'piggy_bank_contribution', 'donation'],
                created_at__gte=twelve_months_ago
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                total=Sum('amount')
            ).order_by('month')
            
            pp = member.payment_profile
            user_obj = pp.user.user if (pp and pp.user) else None
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
            transaction_type__in=inflow_types,
            created_at__month=timezone.now().month,
            created_at__year=timezone.now().year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        last_month = timezone.now() - timedelta(days=30)
        prev_month_inflow = transactions.filter(
            transaction_type__in=inflow_types,
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
        inflow_types = ['contribution', 'deposit', 'round_contribution', 'loan_repayment', 'penalty_fee', 'fee', 'donation', 'piggy_bank_contribution']
        outflow_types = ['withdrawal', 'group_withdrawal', 'kitty_withdrawal', 'loan_disbursement', 'round_claim', 'round_payout', 'investment_payout', 'piggy_bank_withdrawal', 'refund']

        inflow = transactions.filter(
            transaction_type__in=inflow_types
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        outflow = transactions.filter(
            transaction_type__in=outflow_types
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Category breakdown
        category_breakdown = transactions.values('transaction_type').annotate(
            total=Sum('amount'),
            count=Count('transaction_code')
        ).order_by('-total')
        
        # Monthly P&L
        monthly_pnl = transactions.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            income=Sum('amount', filter=Q(transaction_type__in=inflow_types)),
            expenses=Sum('amount', filter=Q(transaction_type__in=outflow_types)),
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
            user_obj = pp.user.user if (pp and pp.user) else None
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
    @db_transaction.atomic
    def leave(self, request, pk=None):
        """Leave a payment group. Processes financial exit and deactivates membership."""
        group = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Payment profile not found'}, status=status.HTTP_400_BAD_REQUEST)

        member = PaymentGroupMember.objects.filter(
            payment_group=group, payment_profile=payment_profile, is_active=True
        ).first()
        if not member:
            return Response({'error': 'You are not an active member of this group'}, status=status.HTTP_403_FORBIDDEN)

        # Calculate financial stake
        balance = float(member.total_contributed or 0)

        if balance > 0:
            # Process withdrawal back to wallet
            penalty_rate = group.immature_exit_penalty_rate if not group.is_matured else 0
            penalty_amount = balance * (float(penalty_rate) / 100) if penalty_rate > 0 else 0
            payout_amount = balance - penalty_amount

            if payout_amount > 0:
                payment_profile.comrade_balance += Decimal(str(payout_amount))
                payment_profile.save()

                TransactionToken.objects.create(
                    payment_profile=payment_profile,
                    transaction_type='withdrawal',
                    amount=Decimal(str(payout_amount)),
                    pay_from='internal',
                    payment_option='comrade_balance',
                    description=f'Exit payout from group: {group.name}',
                    payment_group=group,
                    status='completed',
                )

            if penalty_amount > 0:
                TransactionToken.objects.create(
                    payment_profile=payment_profile,
                    transaction_type='fee',
                    amount=Decimal(str(penalty_amount)),
                    pay_from='internal',
                    payment_option='comrade_balance',
                    description=f'Early exit penalty ({penalty_rate}%) from group: {group.name}',
                    payment_group=group,
                    status='completed',
                )

        member.is_active = False
        member.save()

        return Response({
            'status': 'Successfully left the group',
            'balance_withdrawn': balance,
            'penalty_applied': penalty_amount if balance > 0 else 0,
            'payout_amount': payout_amount if balance > 0 else 0,
        })
    
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
                target_member = PaymentGroupMember.objects.select_for_update().get(id=on_behalf_of_id, payment_group=group)
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
        
        # Create audit trail with dual-recording
        import secrets
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=amount,
            transaction_type='contribution',
            description=f'Contribution to group: {group.name}',
            payment_group=group,
            payment_option='comrade_balance' if payment_method == 'wallet' else payment_method,
            balance_after=group.current_amount
        )
        
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
            status='completed',
            transaction_category='contribution',
            payment_type='group',
            balance_after=payment_profile.comrade_balance,
            group_member_balance_after=target_member.total_contributed
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

    @action(detail=True, methods=['get', 'post', 'patch'])
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
            
            # Extract fields
            frequency = request.data.get('frequency', 'monthly')
            amount = request.data.get('amount')
            automation_type = request.data.get('automation_type', 'contribute')
            
            # Calculate next contribution date
            from datetime import datetime, timedelta
            now = datetime.now()
            
            start_date_str = request.data.get('start_date')
            if start_date_str == "":
                start_date_str = None
                
            if start_date_str:
                try:
                    next_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                except ValueError:
                    return Response({'error': 'Invalid start_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                if frequency == 'daily':
                    next_date = now + timedelta(days=1)
                elif frequency == 'weekly':
                    next_date = now + timedelta(weeks=1)
                elif frequency == 'fortnight':
                    next_date = now + timedelta(days=14)
                else:  # monthly
                    execution_day = int(request.data.get('execution_day', 1) or 1)
                    next_date = now.replace(day=min(execution_day, 28))
                    if next_date <= now:
                        next_date = (now.replace(day=1) + timedelta(days=32)).replace(day=min(execution_day, 28))
            
            # Map frontend fields to model fields
            def clean_empty(val):
                return None if val == "" else val

            data = {
                'member': member.id,
                'amount': amount,
                'frequency': frequency,
                'next_contribution_date': next_date,
                'automation_type': automation_type,
                'target_type': clean_empty(request.data.get('target_type')),
                'target_id': clean_empty(request.data.get('target_id')),
                'target_name': clean_empty(request.data.get('target_name')),
                'withdrawal_mode': request.data.get('withdrawal_mode', 'all') or 'all',
                'withdrawal_recipients': request.data.get('withdrawal_recipients', []),
                'withdrawal_sequence': request.data.get('withdrawal_sequence', []),
                'status': 'pending_vote', # Default to pending vote
                'is_active': False, # Inactive until approved
                'start_date': clean_empty(start_date_str),
                'execution_day': request.data.get('execution_day', 1) or 1,
                'execution_day_of_week': clean_empty(request.data.get('execution_day_of_week')),
                'execution_time_start': clean_empty(request.data.get('execution_time_start')),
                'execution_time_end': clean_empty(request.data.get('execution_time_end')),
            }
            
            serializer = StandingOrderSerializer(data=data)
            if serializer.is_valid():
                automation = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        elif request.method == 'PATCH':
            automation_id = request.data.get('automation_id')
            if not automation_id:
                return Response({'error': 'automation_id is required'}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                automation = StandingOrder.objects.get(id=automation_id, member__payment_group=group)
            except StandingOrder.DoesNotExist:
                return Response({'error': 'Automation not found'}, status=status.HTTP_404_NOT_FOUND)
                
            payment_profile = get_or_create_payment_profile(request.user)
            try:
                member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
            except PaymentGroupMember.DoesNotExist:
                return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
                
            if 'is_active' in request.data:
                if automation.status not in ['approved', 'active', 'paused']:
                    return Response({'error': 'Cannot toggle active state of unapproved automation'}, status=status.HTTP_400_BAD_REQUEST)
                
                automation.is_active = request.data['is_active']
                automation.status = 'active' if automation.is_active else 'paused'
                
            if 'withdrawal_sequence' in request.data:
                automation.withdrawal_sequence = request.data['withdrawal_sequence']
                
            if 'withdrawal_current_index' in request.data:
                automation.withdrawal_current_index = int(request.data['withdrawal_current_index'])
                
            automation.save()
            return Response(StandingOrderSerializer(automation).data)

        # GET method
        automations = StandingOrder.objects.filter(
            member__payment_group=group
        ).select_related('member', 'member__payment_profile')
        return Response(StandingOrderSerializer(automations, many=True).data)

    @action(detail=True, methods=['post'], url_path='vote_automation')
    def vote_automation(self, request, pk=None):
        group = self.get_object()
        automation_id = request.data.get('automation_id')
        vote = request.data.get('vote') # 'approve' or 'reject'
        
        if not automation_id or not vote:
            return Response({'error': 'automation_id and vote are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            automation = StandingOrder.objects.get(id=automation_id, member__payment_group=group)
        except StandingOrder.DoesNotExist:
            return Response({'error': 'Automation not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if automation.status != 'pending_vote':
            return Response({'error': 'This automation is not pending a vote'}, status=status.HTTP_400_BAD_REQUEST)
            
        payment_profile = get_or_create_payment_profile(request.user)
        try:
            member = PaymentGroupMember.objects.get(payment_group=group, payment_profile=payment_profile)
        except PaymentGroupMember.DoesNotExist:
            return Response({'error': 'Not a member of this group'}, status=status.HTTP_403_FORBIDDEN)
            
        # Initialize lists if empty
        if automation.approval_votes is None: automation.approval_votes = []
        if automation.rejection_votes is None: automation.rejection_votes = []
        
        member_id = str(member.id)
        
        # Remove previous vote if exists
        if member_id in automation.approval_votes:
            automation.approval_votes.remove(member_id)
        if member_id in automation.rejection_votes:
            automation.rejection_votes.remove(member_id)
            
        # Add new vote
        if vote == 'approve':
            automation.approval_votes.append(member_id)
        elif vote == 'reject':
            automation.rejection_votes.append(member_id)
        else:
            return Response({'error': 'Invalid vote choice'}, status=status.HTTP_400_BAD_REQUEST)
            
        automation.save()
        
        # Check threshold
        total_members = group.members.count()
        approvals = len(automation.approval_votes)
        
        threshold_percent = group.approval_threshold or 51
        actual_percent = (approvals / total_members) * 100 if total_members > 0 else 0
        
        if actual_percent >= threshold_percent:
            automation.status = 'approved'
            automation.is_active = True
            automation.save()
            
        return Response(StandingOrderSerializer(automation).data)

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
        """Manually override max_capacity. Admin/creator only."""
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

        new_capacity = request.data.get('max_capacity')
        if not new_capacity or not str(new_capacity).isdigit() or int(new_capacity) < 1:
            return Response({'error': 'max_capacity must be a positive integer'}, status=status.HTTP_400_BAD_REQUEST)

        group.max_capacity = int(new_capacity)
        group.save(update_fields=['max_capacity', 'updated_at'])
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
        from Payment.models import TransactionToken, TransactionHistory, PaymentAuthorization, PaymentVerification, PaymentGroupMember, Order, OrderItem, Product
        from Authentication.models import Profile
        
        member = PaymentGroupMember.objects.filter(payment_group=group, payment_profile=payment_profile).first()
        
        import secrets
        import uuid
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=amount,
            transaction_type='purchase',
            pay_from='group_wallet',
            payment_option='group_wallet',
            description=f'Group checkout for {group.name}',
            payment_group=group,
            balance_after=group.current_amount
        )
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
            status='completed',
            transaction_category='purchase',
            payment_type='group',
            balance_after=payment_profile.comrade_balance,
            group_member_balance_after=member.total_contributed if member else None
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
            description=f'Kitty withdrawal from: {kitty.name} (funds remain in kitty ecosystem)',
            payment_group=kitty
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
        
        logger.info(f"Kitty withdrawal: {amount} from {kitty.name} - funds kept in kitty ecosystem")
        
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
        """Sync inventory from hardcoded data or parsed file data (staff only)"""
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)
        
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
            
        def resolve_image_url(path):
            if not path:
                return None
            path_str = str(path)
            if path_str.startswith('http://') or path_str.startswith('https://'):
                return path_str
            return request.build_absolute_uri(path_str)
            
        serialized_data = ProductSerializer(products, many=True).data
        for item in serialized_data:
            if item.get('image_url'):
                item['image_url'] = resolve_image_url(item['image_url'])
        return Response(serialized_data)

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
            Q(payment_group__members__payment_profile=payment_profile) |  # Group piggy banks
            Q(visibility='public', status='active')  # Public piggy banks for non-member discovery
        ).distinct()

    @action(detail=False, methods=['get'])
    def discover(self, request):
        """Return public, active piggy banks the user is not already a member of."""
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
            return Response({'results': []})

        member_piggy_ids = PiggyBankMember.objects.filter(
            payment_profile=payment_profile, is_active=True
        ).values_list('piggy_bank_id', flat=True)

        queryset = GroupTarget.objects.filter(
            visibility='public', status='active', owner__isnull=True
        ).exclude(id__in=list(member_piggy_ids))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = GroupTargetSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = GroupTargetSerializer(queryset, many=True, context={'request': request})
        return Response({'results': serializer.data})

    def perform_create(self, serializer):
        user = self.request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             raise serializers.ValidationError("Could not create payment profile")
        
        # Check if individual or group piggy bank
        payment_group_id = self.request.data.get('payment_group')
        
        if payment_group_id:
            member_group_piggy_count = PiggyBankMember.objects.filter(
                payment_profile=payment_profile,
                is_active=True
            ).count()
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
            serializer.save(owner=payment_profile, visibility='private')

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
        
        # Check membership — only PiggyBankMembers can contribute
        piggy_member = PiggyBankMember.objects.filter(
            piggy_bank=target, payment_profile=payment_profile, is_active=True
        ).first()
        if not piggy_member:
            return Response({'error': 'You must be a member of this piggy bank to contribute'}, status=status.HTTP_403_FORBIDDEN)

        # Check for pending leave vote — block contributions during leave voting
        if PiggyBankActionRequest.objects.filter(
            piggy_bank=target, requested_by=payment_profile,
            action_type='leave', status='pending'
        ).exists():
            return Response({'error': 'You have a pending leave request. Cannot contribute until resolved.'}, status=status.HTTP_403_FORBIDDEN)

        # Deduct from user balance
        payment_profile.comrade_balance -= Decimal(str(amount))
        payment_profile.save()
        
        # Create wallet transaction
        # Add to piggy bank balance atomically
        target = GroupTarget.objects.select_for_update().get(id=target.id)
        target.current_amount += Decimal(str(amount))
        target.save()

        # Update PiggyBankMember total contribution
        piggy_member.total_contributed += Decimal(str(amount))
        piggy_member.save()

        # Create wallet transaction
        import secrets
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_type='piggy_bank_contribution',
            amount=amount,
            payment_option='comrade_balance',
            description=f'Piggy bank contribution to {target.name}',
            payment_group=target.payment_group if target.payment_group else None,
            piggy_bank=target,
            balance_after=target.current_amount
        )
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
            status='completed',
            transaction_category='piggy_bank_contribution',
            payment_type='group' if target.payment_group else 'individual',
            balance_after=payment_profile.comrade_balance,
            group_member_balance_after=float(piggy_member.total_contributed)
        )

        # Record contribution history
        from Payment.models import Contribution
        Contribution.objects.create(
            payment_group=target.payment_group,
            target=target,
            member=PaymentGroupMember.objects.filter(payment_profile=payment_profile).first(),
            amount=amount,
            notes=request.data.get('notes', '')
        )

        # Log to dedicated piggy bank event log
        PiggyBankTransaction.objects.create(
            piggy_bank=target,
            event_type='contribution',
            amount=amount,
            performed_by=payment_profile,
            balance_after=target.current_amount,
            note=request.data.get('notes', ''),
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
            
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
             return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if target.payment_group:
            from Payment.models import PiggyBankActionRequest
            # Check membership via PiggyBankMember
            piggy_member = PiggyBankMember.objects.filter(
                piggy_bank=target, payment_profile=payment_profile, is_active=True
            ).first()
            if not piggy_member:
                return Response({'error': 'Not a member of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)

            # If sole member → 100% consensus is already met, execute immediately
            total_members = PiggyBankMember.objects.filter(piggy_bank=target, is_active=True).count()
            if total_members <= 1:
                PiggyBankTransaction.objects.create(
                    piggy_bank=target,
                    event_type='approval_approved',
                    amount=amount,
                    performed_by=payment_profile,
                    note='Sole member withdrawal — auto-approved',
                )
                return self._execute_withdraw_internal(target, amount, payment_profile, request)

            # Multi-member group → create approval request
            req = PiggyBankActionRequest.objects.create(
                piggy_bank=target,
                requested_by=payment_profile,
                action_type='withdraw',
                amount=amount,
                reason=request.data.get('reason', '')
            )
            PiggyBankTransaction.objects.create(
                piggy_bank=target,
                event_type='approval_requested',
                amount=amount,
                performed_by=payment_profile,
                note=f"Withdrawal approval requested: {request.data.get('reason', '')}",
            )
            return Response({'status': 'Withdrawal request created, pending group approval', 'request_id': str(req.id)})
        else:
            # Individual Piggy Bank → execute immediately
            PiggyBankTransaction.objects.create(
                piggy_bank=target,
                event_type='approval_approved',
                amount=amount,
                performed_by=payment_profile,
                note='Individual piggy bank withdrawal — auto-approved',
            )
            return self._execute_withdraw_internal(target, amount, payment_profile, request)

    def _execute_withdraw_internal(self, target, amount, payment_profile, request):
        from decimal import Decimal
        from Payment.models import TransactionToken, TransactionHistory, PaymentAuthorization, PaymentVerification, PaymentGroupMember
        import uuid
        import secrets
        from django.utils import timezone
        
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
            piggy_member = PiggyBankMember.objects.filter(
                piggy_bank=target, payment_profile=payment_profile, is_active=True
            ).first()
            member_total = float(piggy_member.total_contributed) if piggy_member else 0
            if member_total < float(target.require_min_contribution_amount):
                return Response({'error': f'Must have contributed at least ${float(target.require_min_contribution_amount):.2f}. You have contributed ${member_total:.2f}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check max withdrawals per day
        if target.max_withdrawals_per_day > 0 and target.last_withdrawal_date:
            from datetime import timedelta
            if target.last_withdrawal_date.date() == timezone.now().date():
                time_since_last = timezone.now() - target.last_withdrawal_date
                if time_since_last < timedelta(hours=24):
                    pass
        
        # Check member age requirement
        if target.require_min_member_age_days:
            piggy_member = PiggyBankMember.objects.filter(
                piggy_bank=target, payment_profile=payment_profile, is_active=True
            ).first()
            if piggy_member:
                days_since_joined = (timezone.now() - piggy_member.joined_at).days
                if days_since_joined < target.require_min_member_age_days:
                    return Response({'error': f'Must be a member for at least {target.require_min_member_age_days} days before withdrawing. You have been a member for {days_since_joined} days.'}, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        t1 = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=Decimal(str(amount)),
            transaction_type='piggy_bank_withdrawal',
            description=description,
            payment_group=target.payment_group,
            piggy_bank=target,
            balance_after=target.current_amount,
            pay_from='internal',
            payment_option='wallet'
        )
        
        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=t1,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=Decimal(str(net_amount)),
            status='completed',
            transaction_category='piggy_bank_withdrawal',
            payment_type='group' if target.payment_group else 'individual',
            balance_after=payment_profile.comrade_balance
        )

        # Log to dedicated piggy bank event log
        PiggyBankTransaction.objects.create(
            piggy_bank=target,
            event_type='withdrawal',
            amount=Decimal(str(amount)),
            performed_by=payment_profile,
            balance_after=target.current_amount,
            note=description,
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
    def extend_maturity(self, request, pk=None):
        target = self.get_object()
        new_date_str = request.data.get('maturity_date')
        if not new_date_str:
            return Response({'error': 'New maturity date is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from dateutil.parser import parse
        try:
            new_date = parse(new_date_str)
        except Exception:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
            
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if target.payment_group:
            from Payment.models import PiggyBankActionRequest
            if not PiggyBankMember.objects.filter(piggy_bank=target, payment_profile=payment_profile, is_active=True).exists():
                return Response({'error': 'Not a member of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)
            req = PiggyBankActionRequest.objects.create(
                piggy_bank=target,
                requested_by=payment_profile,
                action_type='extend_maturity',
                new_maturity_date=new_date,
                reason=request.data.get('reason', '')
            )
            return Response({'status': 'Maturity extension request created, pending group approval', 'request_id': str(req.id)})
        else:
            return self._execute_extend_maturity_internal(target, new_date)

    def _execute_extend_maturity_internal(self, target, new_date):
        target.maturity_date = new_date
        target.save()
        return Response({'status': 'Maturity date extended successfully', 'new_maturity_date': target.maturity_date})
        
    @action(detail=True, methods=['post'])
    def dissolve(self, request, pk=None):
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        if target.payment_group:
            from Payment.models import PiggyBankActionRequest
            if not PiggyBankMember.objects.filter(piggy_bank=target, payment_profile=payment_profile, is_active=True).exists():
                return Response({'error': 'Not a member of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)
            req = PiggyBankActionRequest.objects.create(
                piggy_bank=target,
                requested_by=payment_profile,
                action_type='dissolve',
                reason=request.data.get('reason', '')
            )
            return Response({'status': 'Dissolve request created, pending group approval', 'request_id': str(req.id)})
        else:
            return self._execute_dissolve_internal(target, payment_profile, request)

    def _execute_dissolve_internal(self, target, payment_profile, request):
        amount = float(target.current_amount)
        if amount > 0:
            wd_res = self._execute_withdraw_internal(target, amount, payment_profile, request)
            if wd_res.status_code != 200:
                return wd_res
        
        target.status = 'inactive'
        target.is_active = False
        target.save()
        return Response({'status': 'Piggy bank dissolved and deactivated successfully', 'withdrawn_amount': amount})

    @action(detail=True, methods=['get'])
    def action_requests(self, request, pk=None):
        import traceback
        try:
            target = self.get_object()
            from Payment.models import PiggyBankActionRequest, PiggyBankActionRequestVote
            from Payment.serializers import PiggyBankActionRequestSerializer
            reqs = PiggyBankActionRequest.objects.filter(piggy_bank=target).order_by('-created_at')
            data = PiggyBankActionRequestSerializer(reqs, many=True, context={'request': request}).data
            
            # add user vote status
            payment_profile = get_or_create_payment_profile(request.user)
            for r in data:
                vote = PiggyBankActionRequestVote.objects.filter(request_id=r['id'], voter=payment_profile).first()
                r['current_user_vote'] = vote.vote if vote else None
                
            return Response(data)
        except Exception as e:
            print('ERROR in action_requests:', str(e))
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def vote_action(self, request, pk=None):
        target = self.get_object()
        request_id = request.data.get('request_id')
        vote_choice = request.data.get('vote')
        
        if vote_choice not in ['approve', 'reject']:
            return Response({'error': 'Invalid vote'}, status=status.HTTP_400_BAD_REQUEST)
            
        from Payment.models import PiggyBankActionRequest, PiggyBankActionRequestVote
        action_req = PiggyBankActionRequest.objects.filter(id=request_id, piggy_bank=target).first()
        if not action_req:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if action_req.status != 'pending':
            return Response({'error': f'Request already {action_req.status}'}, status=status.HTTP_400_BAD_REQUEST)
            
        payment_profile = get_or_create_payment_profile(request.user)
        piggy_member = PiggyBankMember.objects.filter(
            piggy_bank=target, payment_profile=payment_profile, is_active=True
        ).first()
        if not piggy_member and target.owner != payment_profile:
            return Response({'error': 'Not a member of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)
        total_members = PiggyBankMember.objects.filter(piggy_bank=target, is_active=True).count()
            
        vote_obj, created = PiggyBankActionRequestVote.objects.update_or_create(
            request=action_req,
            voter=payment_profile,
            defaults={'vote': vote_choice}
        )
        
        # check 100% consensus
        approvals = action_req.votes.filter(vote='approve').count()
        rejections = action_req.votes.filter(vote='reject').count()
        
        if approvals == total_members:
            action_req.status = 'approved'
            action_req.save()

            # Execute the action and surface the real result
            if action_req.action_type == 'withdraw':
                exec_res = self._execute_withdraw_internal(
                    target, float(action_req.amount), action_req.requested_by, request
                )
                if exec_res.status_code == 200:
                    action_req.status = 'executed'
                    action_req.save()
                    PiggyBankTransaction.objects.create(
                        piggy_bank=target,
                        event_type='approval_approved',
                        amount=action_req.amount,
                        performed_by=action_req.requested_by,
                        note=f"Withdrawal approved by consensus — {action_req.reason or ''}",
                    )
                    return Response({
                        'status': 'Vote recorded and action executed due to 100% consensus',
                        'executed': True
                    })
                else:
                    action_req.status = 'failed'
                    action_req.save()
                    error_detail = exec_res.data.get('error', 'Execution failed') if hasattr(exec_res, 'data') else 'Execution failed'
                    return Response({
                        'status': 'Vote recorded but execution failed',
                        'executed': False,
                        'error': error_detail
                    }, status=status.HTTP_200_OK)

            elif action_req.action_type == 'extend_maturity':
                self._execute_extend_maturity_internal(target, action_req.new_maturity_date)
                action_req.status = 'executed'
                action_req.save()
            elif action_req.action_type == 'dissolve':
                exec_res = self._execute_dissolve_internal(target, action_req.requested_by, request)
                action_req.status = 'executed' if exec_res.status_code == 200 else 'failed'
                action_req.save()
            elif action_req.action_type == 'merge':
                from decimal import Decimal
                source_pbs = action_req.target_piggy_banks.all()
                total_transferred = Decimal('0')
                source_names = []
                for source in source_pbs:
                    amt = source.current_amount
                    target.current_amount += amt
                    source.current_amount = Decimal('0')
                    source.status = 'inactive'
                    source.is_active = False
                    source.save()
                    total_transferred += amt
                    source_names.append(source.name)
                    PiggyBankTransaction.objects.create(
                        piggy_bank=source,
                        event_type='transfer_out',
                        amount=float(amt),
                        performed_by=action_req.requested_by,
                        note=f'Merged into {target.name}'
                    )
                    PiggyBankTransaction.objects.create(
                        piggy_bank=target,
                        event_type='transfer_in',
                        amount=float(amt),
                        performed_by=action_req.requested_by,
                        note=f'Merged from {source.name}'
                    )
                    # Re-parent source PiggyBankMember records to target
                    source.piggy_members.all().update(piggy_bank=target)
                target.save()
                action_req.status = 'executed'
                action_req.save()
                PiggyBankTransaction.objects.create(
                    piggy_bank=target,
                    event_type='approval_approved',
                    amount=float(total_transferred),
                    performed_by=action_req.requested_by,
                    note=f'Merge approved by consensus — {action_req.reason or ""}',
                )
                try:
                    requester_user = action_req.requested_by.user.user
                    src_list = ', '.join(source_names)
                    create_notification(
                        recipient=requester_user,
                        actor=request.user,
                        notification_type='system',
                        title='Merge Approved',
                        message=f'Your merge request to combine into "{target.name}" was approved and executed. ${float(total_transferred):.2f} transferred from: {src_list}',
                        action_url=f'/payments/piggy-banks/{target.id}',
                    )
                    for m in PiggyBankMember.objects.filter(piggy_bank=target, is_active=True).exclude(payment_profile=action_req.requested_by).exclude(payment_profile=payment_profile).select_related('payment_profile__user__user'):
                        cu = m.payment_profile.user.user
                        if cu.id != requester_user.id and cu.id != request.user.id:
                            create_notification(
                                recipient=cu,
                                actor=request.user,
                                notification_type='system',
                                title='Merge Approved',
                                message=f'The merge into "{target.name}" was approved by consensus. ${float(total_transferred):.2f} transferred.',
                                action_url=f'/payments/piggy-banks/{target.id}',
                            )
                except Exception:
                    pass

            elif action_req.action_type == 'leave':
                from decimal import Decimal
                exec_res = self._execute_leave_internal(target, action_req, request)
                if exec_res.status_code == 200:
                    action_req.status = 'executed'
                    action_req.save()
                    PiggyBankTransaction.objects.create(
                        piggy_bank=target,
                        event_type='approval_approved',
                        amount=action_req.amount,
                        performed_by=action_req.requested_by,
                        note=f'Leave approved by consensus — {action_req.reason or ""}',
                    )
                else:
                    action_req.status = 'failed'
                    action_req.save()

            return Response({'status': 'Vote recorded and action executed due to 100% consensus', 'executed': True})
        
        if rejections > 0:
            # Any rejection kills consensus
            action_req.status = 'rejected'
            action_req.save()
            PiggyBankTransaction.objects.create(
                piggy_bank=target,
                event_type='approval_rejected',
                amount=action_req.amount,
                performed_by=payment_profile,
                note=f"{action_req.get_action_type_display()} rejected — {action_req.reason or ''}",
            )
            try:
                requester_user = action_req.requested_by.user.user
                create_notification(
                    recipient=requester_user,
                    actor=request.user,
                    notification_type='system',
                    title=f'{action_req.get_action_type_display()} Rejected',
                    message=f'Your {action_req.get_action_type_display().lower()} request for "{target.name}" was rejected by a group member.',
                    action_url=f'/payments/piggy-banks/{target.id}',
                )
                for m in PiggyBankMember.objects.filter(piggy_bank=target, is_active=True).exclude(payment_profile=action_req.requested_by).exclude(payment_profile=payment_profile).select_related('payment_profile__user__user'):
                    cu = m.payment_profile.user.user
                    if cu.id != requester_user.id and cu.id != request.user.id:
                        create_notification(
                            recipient=cu,
                            actor=request.user,
                            notification_type='system',
                            title=f'{action_req.get_action_type_display()} Rejected',
                            message=f'A {action_req.get_action_type_display().lower()} request for "{target.name}" was rejected.',
                            action_url=f'/payments/piggy-banks/{target.id}',
                        )
            except Exception:
                pass
            return Response({'status': 'Vote recorded. Action rejected because 100% consensus is required.'})
            
        return Response({'status': 'Vote recorded successfully', 'approvals': approvals, 'total': total_members})

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a piggy bank as a member."""
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)

        if PiggyBankMember.objects.filter(piggy_bank=target, payment_profile=payment_profile, is_active=True).exists():
            return Response({'error': 'Already a member of this piggy bank'}, status=status.HTTP_400_BAD_REQUEST)

        # Check 3-group-piggy-membership cap
        current_memberships = PiggyBankMember.objects.filter(payment_profile=payment_profile, is_active=True).count()
        if current_memberships >= GroupTarget.MAX_GROUP_PIGGY_MEMBERSHIPS:
            return Response({'error': f'You can be a member of at most {GroupTarget.MAX_GROUP_PIGGY_MEMBERSHIPS} piggy banks.'}, status=status.HTTP_400_BAD_REQUEST)

        member = PiggyBankMember.objects.create(
            piggy_bank=target,
            payment_profile=payment_profile,
            is_admin=False,
            is_active=True,
        )

        PiggyBankTransaction.objects.create(
            piggy_bank=target,
            event_type='member_joined',
            performed_by=payment_profile,
            note=f'{payment_profile.user.user.get_full_name() or payment_profile.user.user.username} joined this piggy bank',
        )

        from Payment.serializers import PiggyBankMemberSerializer
        return Response(PiggyBankMemberSerializer(member).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def leave(self, request, pk=None):
        """Leave a piggy bank. Triggers withdrawal of total_contributed."""
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)

        piggy_member = PiggyBankMember.objects.filter(
            piggy_bank=target, payment_profile=payment_profile, is_active=True
        ).first()
        if not piggy_member:
            return Response({'error': 'Not a member of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)

        withdraw_amount = float(piggy_member.total_contributed - piggy_member.total_withdrawn)
        if withdraw_amount <= 0:
            return Response({'error': 'You have no balance to withdraw. Leave request denied.'}, status=status.HTTP_400_BAD_REQUEST)

        if target.leave_requires_vote and PiggyBankMember.objects.filter(piggy_bank=target, is_active=True).count() > 1:
            from Payment.models import PiggyBankActionRequest
            req = PiggyBankActionRequest.objects.create(
                piggy_bank=target,
                requested_by=payment_profile,
                action_type='leave',
                amount=withdraw_amount,
                reason=request.data.get('reason', '')
            )
            PiggyBankTransaction.objects.create(
                piggy_bank=target,
                event_type='approval_requested',
                amount=withdraw_amount,
                performed_by=payment_profile,
                note=f'Leave request created: {request.data.get("reason", "")}',
            )
            return Response({'status': 'Leave request created, pending group approval', 'request_id': str(req.id)})
        else:
            return self._execute_leave_internal(target, piggy_member, request)

    def _execute_leave_internal(self, target, piggy_member_or_req, request):
        """Execute leave: withdraw total_contributed - total_withdrawn, apply fee, mark member inactive."""
        if isinstance(piggy_member_or_req, PiggyBankActionRequest):
            action_req = piggy_member_or_req
            payment_profile = action_req.requested_by
            piggy_member = PiggyBankMember.objects.filter(
                piggy_bank=target, payment_profile=payment_profile, is_active=True
            ).first()
            if not piggy_member:
                return Response({'error': 'Member not found'}, status=status.HTTP_404_NOT_FOUND)
            waive_penalty = target.leave_vote_waives_penalty
        else:
            piggy_member = piggy_member_or_req
            payment_profile = piggy_member.payment_profile
            waive_penalty = False
            action_req = None

        withdraw_amount = float(piggy_member.total_contributed - piggy_member.total_withdrawn)
        if withdraw_amount <= 0:
            piggy_member.is_active = False
            piggy_member.save()
            PiggyBankTransaction.objects.create(
                piggy_bank=target,
                event_type='member_left',
                performed_by=payment_profile,
                note=f'{payment_profile.user.user.get_full_name() or payment_profile.user.user.username} left (no balance to withdraw)',
            )
            return Response({'status': 'Left piggy bank (no balance to withdraw)', 'amount_withdrawn': 0})

        # If voting waived penalty, temporarily override savings_type for this withdrawal
        original_penalty_rate = None
        if waive_penalty and target.savings_type == 'fixed_deposit' and not target.is_matured:
            original_penalty_rate = target.penalty_rate
            target.penalty_rate = Decimal('0')

        # Execute the withdrawal
        exec_res = self._execute_withdraw_internal(target, withdraw_amount, payment_profile, request)

        # Restore penalty rate if we overrode it
        if original_penalty_rate is not None:
            target.penalty_rate = original_penalty_rate
            target.save()

        if exec_res.status_code != 200:
            return exec_res

        # Apply inconvenience fee (stays in piggy bank)
        if target.leave_inconvenience_fee_percentage > 0 and not waive_penalty:
            fee_amount = withdraw_amount * (float(target.leave_inconvenience_fee_percentage) / 100)
            if fee_amount > 0:
                # Fee stays in piggy bank: re-deduct from user balance, add to target
                payment_profile.comrade_balance -= Decimal(str(fee_amount))
                payment_profile.save()
                target.current_amount += Decimal(str(fee_amount))
                target.save()
                PiggyBankTransaction.objects.create(
                    piggy_bank=target,
                    event_type='withdrawal',
                    amount=fee_amount,
                    performed_by=payment_profile,
                    note=f'Inconvenience fee ({target.leave_inconvenience_fee_percentage}%) for leaving — stays in piggy bank',
                )

        # Update member totals
        piggy_member.total_withdrawn += Decimal(str(withdraw_amount))
        piggy_member.is_active = False
        piggy_member.save()

        PiggyBankTransaction.objects.create(
            piggy_bank=target,
            event_type='member_left',
            performed_by=payment_profile,
            note=f'{payment_profile.user.user.get_full_name() or payment_profile.user.user.username} left the piggy bank',
        )

        return Response({
            'status': 'Successfully left piggy bank',
            'amount_withdrawn': withdraw_amount,
            'fee_applied': target.leave_inconvenience_fee_percentage if not waive_penalty else 0,
            'penalty_waived': waive_penalty,
        })

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def transfer(self, request, pk=None):
        """Transfer funds between two piggy banks."""
        source = self.get_object()
        target_id = request.data.get('target_id')
        amount = request.data.get('amount')
        if not target_id or not amount:
            return Response({'error': 'target_id and amount are required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)
        from Payment.models import GroupTarget, PaymentGroupMember
        target_pb = GroupTarget.objects.filter(id=target_id).first()
        if not target_pb:
            return Response({'error': 'Target piggy bank not found'}, status=status.HTTP_404_NOT_FOUND)
        if source.id == target_pb.id:
            return Response({'error': 'Cannot transfer to the same piggy bank'}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        if not payment_profile:
            return Response({'error': 'Could not create payment profile'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        def user_can_access(pb):
            if not pb.payment_group:
                return pb.owner == payment_profile
            return PiggyBankMember.objects.filter(piggy_bank=pb, payment_profile=payment_profile, is_active=True).exists()
        if not user_can_access(source):
            return Response({'error': 'Not authorized to access source piggy bank'}, status=status.HTTP_403_FORBIDDEN)
        if not user_can_access(target_pb):
            return Response({'error': 'Not authorized to access target piggy bank'}, status=status.HTTP_403_FORBIDDEN)
        if source.current_amount < amount:
            return Response({'error': 'Insufficient funds in source piggy bank'}, status=status.HTTP_400_BAD_REQUEST)
        if source.locking_status in ('locked', 'locked_time', 'locked_goal'):
            can_wd, wd_message = source.can_withdraw()
            if not can_wd:
                return Response({'error': f'Source piggy bank is locked: {wd_message}'}, status=status.HTTP_403_FORBIDDEN)
        from decimal import Decimal
        from Payment.models import PiggyBankTransaction
        source.current_amount -= Decimal(str(amount))
        source.save()
        target_pb.current_amount += Decimal(str(amount))
        target_pb.save()
        PiggyBankTransaction.objects.create(piggy_bank=source, event_type='transfer_out', amount=amount, performed_by=payment_profile, note=f'Transferred ${amount:.2f} to {target_pb.name}')
        PiggyBankTransaction.objects.create(piggy_bank=target_pb, event_type='transfer_in', amount=amount, performed_by=payment_profile, note=f'Received ${amount:.2f} from {source.name}')
        return Response({'status': 'Transfer successful', 'source_balance': float(source.current_amount), 'target_balance': float(target_pb.current_amount)})

    @action(detail=True, methods=['get'])
    def available_for_merge(self, request, pk=None):
        try:
            target = self.get_object()
            user = request.user
            payment_profile = get_or_create_payment_profile(user)
            from Payment.models import GroupTarget
            if target.payment_group:
                if not PiggyBankMember.objects.filter(piggy_bank=target, payment_profile=payment_profile, is_active=True).exists():
                    return Response({'error': 'Not a member of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)
                available = GroupTarget.objects.filter(payment_group=target.payment_group, status='active').exclude(id=target.id).exclude(locking_status__in=['locked', 'locked_time', 'locked_goal'])
            else:
                if target.owner != payment_profile:
                    return Response({'error': 'Not the owner of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)
                own_pbs = GroupTarget.objects.filter(owner=payment_profile, status='active').exclude(id=target.id).exclude(locking_status__in=['locked', 'locked_time', 'locked_goal'])
                member_piggy_ids = PiggyBankMember.objects.filter(payment_profile=payment_profile, is_active=True).values_list('piggy_bank_id', flat=True)
                group_pbs = GroupTarget.objects.filter(id__in=list(member_piggy_ids), status='active').exclude(locking_status__in=['locked', 'locked_time', 'locked_goal'])
                available = own_pbs | group_pbs
            from Payment.serializers import GroupTargetSerializer
            data = GroupTargetSerializer(available.distinct(), many=True, context={'request': request}).data
            return Response(data)
        except Exception as e:
            self.logger.error(f"available_for_merge failed: {str(e)}", exc_info=True)
            return Response({'error': f'available_for_merge: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    @db_transaction.atomic
    def request_merge(self, request, pk=None):
        target = self.get_object()
        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        from Payment.models import GroupTarget, PiggyBankActionRequest
        source_ids = request.data.get('source_ids', [])
        reason = request.data.get('reason', '')
        if not source_ids or not isinstance(source_ids, list):
            return Response({'error': 'source_ids list is required'}, status=status.HTTP_400_BAD_REQUEST)
        if target.payment_group:
            if not PiggyBankMember.objects.filter(piggy_bank=target, payment_profile=payment_profile, is_active=True).exists():
                return Response({'error': 'Not a member of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)
            source_pbs = GroupTarget.objects.filter(id__in=source_ids, payment_group=target.payment_group, status='active')
        else:
            if target.owner != payment_profile:
                return Response({'error': 'Not the owner of this piggy bank'}, status=status.HTTP_403_FORBIDDEN)
            own_member_ids = PiggyBankMember.objects.filter(payment_profile=payment_profile, is_active=True).values_list('piggy_bank_id', flat=True)
            source_pbs = GroupTarget.objects.filter(id__in=source_ids, status='active').filter(
                Q(owner=payment_profile) | Q(id__in=list(own_member_ids))
            )
        if len(source_pbs) != len(source_ids):
            return Response({'error': 'One or more source piggy banks not found or not available for merge'}, status=status.HTTP_400_BAD_REQUEST)
        for pb in source_pbs:
            if pb.locking_status in ('locked', 'locked_time', 'locked_goal'):
                return Response({'error': f'Piggy bank "{pb.name}" is locked and cannot be merged'}, status=status.HTTP_400_BAD_REQUEST)
        merge_req = PiggyBankActionRequest.objects.create(piggy_bank=target, requested_by=payment_profile, action_type='merge', reason=reason, amount=sum(pb.current_amount for pb in source_pbs))
        merge_req.target_piggy_banks.set(source_pbs)
        from Payment.models import PiggyBankTransaction
        approval_needed = PiggyBankMember.objects.filter(piggy_bank=target, is_active=True).count() > 1
        source_names = ', '.join(pb.name for pb in source_pbs)
        PiggyBankTransaction.objects.create(piggy_bank=target, event_type='approval_requested', amount=float(merge_req.amount) if merge_req.amount else 0, performed_by=payment_profile, note=f'Merge request created: merge {len(source_pbs)} piggy bank(s) into {target.name}')
        if not approval_needed:
            from Payment.models import PiggyBankActionRequestVote
            PiggyBankActionRequestVote.objects.create(request=merge_req, voter=payment_profile, vote='approve')
            merge_req.status = 'approved'
            merge_req.save()
            from decimal import Decimal
            total_transferred = Decimal('0')
            for source in source_pbs:
                amt = source.current_amount
                target.current_amount += amt
                source.current_amount = Decimal('0')
                source.status = 'inactive'
                source.is_active = False
                source.save()
                total_transferred += amt
                source.piggy_members.all().update(piggy_bank=target)
                PiggyBankTransaction.objects.create(piggy_bank=source, event_type='transfer_out', amount=float(amt), performed_by=payment_profile, note=f'Merged into {target.name}')
                PiggyBankTransaction.objects.create(piggy_bank=target, event_type='transfer_in', amount=float(amt), performed_by=payment_profile, note=f'Merged from {source.name}')
            target.save()
            merge_req.status = 'executed'
            merge_req.save()
            PiggyBankTransaction.objects.create(piggy_bank=target, event_type='approval_approved', amount=float(total_transferred), performed_by=payment_profile, note=f'Merge auto-approved — {reason or ""}')
            try:
                create_notification(
                    recipient=payment_profile.user.user,
                    actor=request.user,
                    notification_type='system',
                    title='Merge Completed',
                    message=f'Your merge request to combine {len(source_pbs)} piggy bank(s) into "{target.name}" was auto-approved and executed. ${float(total_transferred):.2f} transferred.',
                    action_url=f'/payments/piggy-banks/{target.id}',
                )
            except Exception:
                pass
            return Response({'status': 'Merge executed successfully (auto-approved)', 'request_id': str(merge_req.id), 'total_amount': float(total_transferred)})
        # Notify other piggy bank members about the pending vote
        try:
            other_members = PiggyBankMember.objects.filter(piggy_bank=target, is_active=True).exclude(payment_profile=payment_profile).select_related('payment_profile__user__user')
            for m in other_members:
                custom_user = m.payment_profile.user.user
                if custom_user.id != request.user.id:
                    create_notification(
                        recipient=custom_user,
                        actor=request.user,
                        notification_type='system',
                        title='Merge Vote Required',
                        message=f'A merge request to combine {len(source_pbs)} piggy bank(s) into "{target.name}" needs your approval. Source(s): {source_names}',
                        action_url=f'/payments/piggy-banks/{target.id}',
                    )
        except Exception:
            pass
        return Response({'status': 'Merge request created, pending group approval', 'request_id': str(merge_req.id), 'total_amount': float(merge_req.amount) if merge_req.amount else 0})

    @action(detail=True, methods=['get'])
    def my_merge_requests(self, request, pk=None):
        try:
            target = self.get_object()
            user = request.user
            payment_profile = get_or_create_payment_profile(user)
            from Payment.models import PiggyBankActionRequest, PiggyBankActionRequestVote
            from Payment.serializers import PiggyBankActionRequestSerializer
            reqs = PiggyBankActionRequest.objects.filter(action_type='merge').filter(Q(piggy_bank=target) | Q(target_piggy_banks=target)).order_by('-created_at').distinct()
            data = PiggyBankActionRequestSerializer(reqs, many=True, context={'request': request}).data
            for r in data:
                vote = PiggyBankActionRequestVote.objects.filter(request_id=r['id'], voter=payment_profile).first()
                r['current_user_vote'] = vote.vote if vote else None
            return Response(data)
        except Exception as e:
            self.logger.error(f"my_merge_requests failed: {str(e)}", exc_info=True)
            return Response({'error': f'my_merge_requests: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """Lock a piggy bank with validation"""
        target = self.get_object()
        lock_type = request.data.get('lock_type', 'locked')
        maturity_date = request.data.get('maturity_date')
        
        valid_lock_types = ['none', 'locked', 'locked_time', 'locked_goal']
        if lock_type not in valid_lock_types:
            return Response({'error': f'Invalid lock_type. Must be one of: {", ".join(valid_lock_types)}'}, status=status.HTTP_400_BAD_REQUEST)
        
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
                user_obj = c.member.payment_profile.user.user
                profile_obj = c.member.payment_profile.user
                member_map[mid] = {
                    'id': mid,
                    'name': user_obj.get_full_name() or user_obj.username or user_obj.email,
                    'email': user_obj.email,
                    'profile_picture': profile_obj.profile_picture.url if profile_obj.profile_picture else '',
                    'is_anonymous': c.member.is_anonymous,
                    'anonymous_alias': c.member.anonymous_alias,
                    'total_contributed': str(c.amount),
                    'last_contributed_at': c.contributed_at.isoformat(),
                    'contribution_count': 1,
                }
            else:
                member_map[mid]['total_contributed'] = str(
                    Decimal(member_map[mid]['total_contributed']) + Decimal(str(c.amount))
                )
                member_map[mid]['contribution_count'] += 1
                if c.contributed_at.isoformat() > member_map[mid]['last_contributed_at']:
                    member_map[mid]['last_contributed_at'] = c.contributed_at.isoformat()

        return Response(list(member_map.values()))

    @action(detail=True, methods=['get'])
    def member_stats(self, request, pk=None):
        """Aggregate stats about this piggy bank's members for non-member discovery."""
        target = self.get_object()

        from Payment.models import PiggyBankTransaction, PiggyBankConversionRequest
        from django.db.models import Sum, Max
        from django.utils import timezone
        from decimal import Decimal

        members = PiggyBankMember.objects.filter(piggy_bank=target, is_active=True)
        member_count = members.count()

        avg_contribution = 0
        if member_count > 0:
            total = target.current_amount
            avg_contribution = round(float(total) / member_count, 2)

        # Nationalities from CustomUser.country_of_origin
        nationalities = []
        for m in members.select_related('payment_profile__user__user').iterator():
            try:
                code = m.payment_profile.user.user.country_of_origin
            except AttributeError:
                code = None
            if code:
                nationalities.append(code)
        unique_nationalities = list(dict.fromkeys(nationalities))

        # Top/bottom contributors from transactions
        txns = PiggyBankTransaction.objects.filter(
            piggy_bank=target, event_type='contribution'
        ).values('performed_by__user__user__first_name',
                 'performed_by__user__user__last_name')\
         .annotate(total=Sum('amount')).order_by('-total')

        top = None
        bottom = None
        if txns:
            first = txns.first()
            top = {'name': f"{first['performed_by__user__user__first_name']} {first['performed_by__user__user__last_name']}".strip(),
                   'amount': float(first['total'])}
            last = txns.last()
            bottom = {'name': f"{last['performed_by__user__user__first_name']} {last['performed_by__user__user__last_name']}".strip(),
                      'amount': float(last['total'])}

        # Aggregate contribution stats for discovery
        contrib_agg = PiggyBankTransaction.objects.filter(
            piggy_bank=target, event_type='contribution'
        ).aggregate(
            total_contributions=Sum('amount'),
            contribution_count=Sum('amount'),  # count placeholder — recount properly
            last_contribution_date=Max('created_at')
        )
        total_contributions = float(contrib_agg['total_contributions'] or 0)
        contribution_count = PiggyBankTransaction.objects.filter(
            piggy_bank=target, event_type='contribution'
        ).count()
        last_contribution_date = contrib_agg['last_contribution_date']
        created_days_ago = (timezone.now() - target.created_at).days if target.created_at else 0

        # Group conversion status
        conversion_status = None
        conv = PiggyBankConversionRequest.objects.filter(
            piggy_bank=target, status='pending'
        ).first()
        if conv:
            conversion_status = conv.status
        elif PiggyBankConversionRequest.objects.filter(piggy_bank=target, status='approved').exists():
            conversion_status = 'approved'

        return Response({
            'member_count': member_count,
            'average_contribution': avg_contribution,
            'member_nationalities': unique_nationalities,
            'top_contributor': top,
            'bottom_contributor': bottom,
            'group_conversion_status': conversion_status,
            'total_contributions': total_contributions,
            'contribution_count': contribution_count,
            'last_contribution_date': last_contribution_date.isoformat() if last_contribution_date else None,
            'created_days_ago': created_days_ago,
        })

    @action(detail=True, methods=['get'])
    def piggy_analytics(self, request, pk=None):
        """Rich analytics and contribution trends for this piggy bank using PiggyBankTransaction."""
        target = self.get_object()
        profile = get_or_create_payment_profile(request.user)
        if not PiggyBankMember.objects.filter(piggy_bank=target, payment_profile=profile, is_active=True).exists():
            return Response({'error': 'Only members can view analytics'}, status=403)
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        from Payment.models import PiggyBankTransaction

        # Growth and Trends from events
        all_events = target.piggy_events.all()
        recent_events = all_events.filter(created_at__gte=thirty_days_ago, event_type='contribution')
        growth_30d = sum(float(e.amount) for e in recent_events)

        # Build month buckets (last 6 months)
        month_buckets = []
        for i in range(5, -1, -1):
            month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            next_month = (month_start + timedelta(days=32)).replace(day=1)
            month_buckets.append((month_start.strftime('%b'), month_start, next_month))

        # Monthly trends: contributions + withdrawals + conversions side-by-side
        monthly_trends = []
        max_monthly = 0
        for label, m_start, m_end in month_buckets:
            month_contribs = all_events.filter(event_type='contribution', created_at__gte=m_start, created_at__lt=m_end)
            month_amount = sum(float(e.amount) for e in month_contribs)
            month_wd_txns = all_events.filter(event_type='withdrawal', created_at__gte=m_start, created_at__lt=m_end)
            month_withdrawals = sum(float(e.amount) for e in month_wd_txns)
            month_conv_txns = all_events.filter(event_type='conversion', created_at__gte=m_start, created_at__lt=m_end)
            month_conversions = sum(float(e.amount) for e in month_conv_txns)
            monthly_trends.append({
                'month': label,
                'amount': month_amount,
                'withdrawals': month_withdrawals,
                'conversions': month_conversions,
                'contribution_count': month_contribs.count(),
                'withdrawal_count': month_wd_txns.count(),
                'conversion_count': month_conv_txns.count(),
            })
            if month_amount > max_monthly:
                max_monthly = month_amount

        # Top Stakers — keyed by performed_by (PaymentProfile)
        member_contributions = {}
        for e in all_events.filter(event_type='contribution').select_related('performed_by__user__user'):
            if not e.performed_by:
                continue
            pid = str(e.performed_by_id)
            if pid not in member_contributions:
                try:
                    name = e.performed_by.user.user.get_full_name() or e.performed_by.user.user.username
                except Exception:
                    name = 'Unknown User'
                profile_obj = e.performed_by.user
                pic_url = profile_obj.profile_picture.url if profile_obj.profile_picture else ''
                member_contributions[pid] = {'user_name': name, 'total_contributed': 0, 'profile_picture': pic_url}
            member_contributions[pid]['total_contributed'] += float(e.amount)
        top_stakers = sorted(member_contributions.values(), key=lambda x: x['total_contributed'], reverse=True)[:5]

        # Stats from events (conversions count as withdrawals but tracked separately)
        total_withdrawn = sum(float(e.amount) for e in all_events.filter(event_type__in=['withdrawal', 'conversion']))
        withdrawal_count = all_events.filter(event_type__in=['withdrawal', 'conversion']).count()
        total_converted = sum(float(e.amount) for e in all_events.filter(event_type='conversion'))
        conversion_count = all_events.filter(event_type='conversion').count()

        # Approval request stats — combine PiggyBankActionRequest (voting) with
        # PiggyBankTransaction (auto-approvals for sole-member + vote outcomes)
        from Payment.models import PiggyBankActionRequest
        action_reqs = PiggyBankActionRequest.objects.filter(piggy_bank=target)
        pbt_approved = PiggyBankTransaction.objects.filter(
            piggy_bank=target, event_type='approval_approved'
        ).count()
        pbt_rejected = PiggyBankTransaction.objects.filter(
            piggy_bank=target, event_type='approval_rejected'
        ).count()
        # Non-withdraw action requests (extend_maturity, dissolve) don't log to PBT
        ar_approved = action_reqs.filter(
            status__in=['approved', 'executed']
        ).exclude(action_type='withdraw').count()
        ar_rejected = action_reqs.filter(
            status='rejected'
        ).exclude(action_type='withdraw').count()
        
        # Member activity
        members_joined = 0
        members_left = 0
        member_join_trend = []
        if target.payment_group:
            group_members = target.payment_group.members.all()
            members_joined = group_members.count()
            members_left = group_members.filter(is_active=False).count()
            for label, m_start, m_end in month_buckets:
                joined_this_month = group_members.filter(joined_at__gte=m_start, joined_at__lt=m_end).count()
                member_join_trend.append({'month': label, 'joined': joined_this_month})

        active_contrib_months = [m for m in monthly_trends if m['amount'] > 0]
        avg_monthly_contribution = (sum(m['amount'] for m in active_contrib_months) / len(active_contrib_months)) if active_contrib_months else 0
        active_wd_months = [m for m in monthly_trends if m['withdrawals'] > 0]
        avg_monthly_withdrawal = (sum(m['withdrawals'] for m in active_wd_months) / len(active_wd_months)) if active_wd_months else 0
        active_conv_months = [m for m in monthly_trends if m['conversions'] > 0]
        avg_monthly_conversion = (sum(m['conversions'] for m in active_conv_months) / len(active_conv_months)) if active_conv_months else 0

        # Merge analytics — was this piggy bank merged into another?
        merged_into_target = None
        merge_as_source_req = target.merge_requests.filter(status__in=['executed', 'approved']).first()
        if merge_as_source_req:
            merged_into_target = {
                'target_id': str(merge_as_source_req.piggy_bank.id),
                'target_name': merge_as_source_req.piggy_bank.name,
                'amount': float(merge_as_source_req.amount or 0),
                'executed_at': merge_as_source_req.updated_at.isoformat() if merge_as_source_req.updated_at else None,
            }

        # Merge analytics — was this piggy bank a merge target that absorbed sources?
        merged_sources = []
        merge_as_target_reqs = action_reqs.filter(action_type='merge', status__in=['executed', 'approved'])
        for m_req in merge_as_target_reqs:
            for src in m_req.target_piggy_banks.all():
                src_member_count = 0
                if src.payment_group:
                    src_member_count = src.payment_group.members.count()
                else:
                    src_member_count = 1 if src.owner else 0
                src_contrib_total = sum(float(e.amount) for e in PiggyBankTransaction.objects.filter(piggy_bank=src, event_type='contribution'))
                src_wd_total = sum(float(e.amount) for e in PiggyBankTransaction.objects.filter(piggy_bank=src, event_type__in=['withdrawal', 'conversion']))
                out_event = PiggyBankTransaction.objects.filter(
                    piggy_bank=src,
                    event_type='transfer_out',
                    note__startswith='Merged into'
                ).first()
                merged_sources.append({
                    'source_id': str(src.id),
                    'source_name': src.name,
                    'amount_transferred': float(out_event.amount) if out_event else 0,
                    'member_count': src_member_count,
                    'total_contributions': round(src_contrib_total, 2),
                    'total_withdrawals': round(src_wd_total, 2),
                    'merged_at': m_req.updated_at.isoformat() if m_req.updated_at else None,
                })

        return Response({
            'total_saved': float(target.current_amount),
            'target_amount': float(target.target_amount),
            'growth_30d': growth_30d,
            'max_monthly': max_monthly,
            'is_mature': target.is_matured,
            'total_contributors': len(member_contributions),
            'monthly_trends': monthly_trends,
            'top_stakers': top_stakers,
            'total_withdrawn': total_withdrawn,
            'withdrawal_count': withdrawal_count,
            'total_converted': total_converted,
            'conversion_count': conversion_count,
            'avg_monthly_contribution': round(avg_monthly_contribution, 2),
            'avg_monthly_withdrawal': round(avg_monthly_withdrawal, 2),
            'avg_monthly_conversion': round(avg_monthly_conversion, 2),
            'total_approval_requests': action_reqs.count() + pbt_approved + pbt_rejected,
            'approvals_approved': ar_approved + pbt_approved,
            'approvals_rejected': ar_rejected + pbt_rejected,
            'approvals_pending': action_reqs.filter(status='pending').count(),
            'members_joined': members_joined,
            'members_left': members_left,
            'member_join_trend': member_join_trend,
            'merged_into_target': merged_into_target,
            'merged_sources': merged_sources,
            'total_merged_sources': len(merged_sources),
            'total_merged_amount': sum(s['amount_transferred'] for s in merged_sources),
        })

    @action(detail=True, methods=['post'])
    def backfill_piggy_events(self, request, pk=None):
        """
        One-time backfill: migrate existing TransactionToken records for this piggy bank
        into PiggyBankTransaction so historical data appears in analytics.
        Safe to call repeatedly — skips records already imported.
        """
        target = self.get_object()
        payment_profile = get_or_create_payment_profile(request.user)

        # Permission: owner of individual piggy or group admin
        is_owner = (not target.payment_group) and getattr(target, 'creator', None) == payment_profile
        is_admin = target.payment_group and target.payment_group.creator == payment_profile
        if not (is_owner or is_admin):
            return Response({'error': 'Only the owner or group admin can trigger a backfill.'}, status=403)

        contrib_created = 0
        wd_created = 0
        transfer_created = 0

        for txn in target.transactions.filter(transaction_type='piggy_bank_contribution'):
            if not PiggyBankTransaction.objects.filter(
                piggy_bank=target, event_type='contribution',
                performed_by=txn.payment_profile, created_at=txn.created_at
            ).exists():
                PiggyBankTransaction.objects.create(
                    piggy_bank=target, event_type='contribution',
                    amount=txn.amount, performed_by=txn.payment_profile,
                    balance_after=txn.balance_after, note=txn.description or '',
                    created_at=txn.created_at,
                )
                contrib_created += 1

        for txn in target.transactions.filter(transaction_type='piggy_bank_withdrawal'):
            if not PiggyBankTransaction.objects.filter(
                piggy_bank=target, event_type='withdrawal',
                performed_by=txn.payment_profile, created_at=txn.created_at
            ).exists():
                PiggyBankTransaction.objects.create(
                    piggy_bank=target, event_type='withdrawal',
                    amount=txn.amount, performed_by=txn.payment_profile,
                    balance_after=txn.balance_after, note=txn.description or '',
                    created_at=txn.created_at,
                )
                wd_created += 1

        for txn in target.transactions.filter(transaction_type='transfer'):
            if not PiggyBankTransaction.objects.filter(
                piggy_bank=target, event_type='withdrawal',
                performed_by=txn.payment_profile, created_at=txn.created_at
            ).exists():
                PiggyBankTransaction.objects.create(
                    piggy_bank=target, event_type='withdrawal',
                    amount=txn.amount, performed_by=txn.payment_profile,
                    balance_after=txn.balance_after, note=txn.description or '',
                    created_at=txn.created_at,
                )
                transfer_created += 1

        return Response({
            'status': 'Backfill complete',
            'contributions_imported': contrib_created,
            'withdrawals_imported': wd_created,
            'transfers_imported': transfer_created,
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
        profile = get_or_create_payment_profile(request.user)
        if not PiggyBankMember.objects.filter(piggy_bank=target, payment_profile=profile, is_active=True).exists():
            return Response({'error': 'Only members can view conversion status'}, status=403)
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
                        payment_group=target.payment_group,
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
        import secrets
        txn_token = TransactionToken.objects.create(
            payment_profile=conv_req.proposed_by.payment_profile,
            transaction_code=uuid.uuid4(),
            amount=amount_to_move,
            transaction_type='transfer',
            description=f"Conversion: Piggy Bank '{target.name}' - {conv_req.conversion_type} type",
            payment_group=target.payment_group
        )
        TransactionHistory.objects.create(
            payment_profile=conv_req.proposed_by.payment_profile,
            transaction_token=txn_token,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=conv_req.proposed_by.payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=conv_req.proposed_by.payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=amount_to_move,
            status='completed',
            transaction_category='transfer',
            payment_type='group' if target.payment_group else 'individual',
            balance_after=conv_req.proposed_by.payment_profile.comrade_balance,
        )
        PiggyBankTransaction.objects.create(
            piggy_bank=target,
            event_type='conversion',
            amount=amount_to_move,
            performed_by=conv_req.proposed_by.payment_profile,
            balance_after=target.current_amount,
            note=f"Conversion: {conv_req.conversion_type} type - {conv_req.reason or ''}",
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
        import secrets
        txn_token = TransactionToken.objects.create(
            payment_profile=payment_profile,
            amount=amount_to_move,
            transaction_type='transfer',
            description=f"Conversion: Piggy Bank '{target.name}' funds moved to group balance.",
            payment_group=target.payment_group
        )
        TransactionHistory.objects.create(
            payment_profile=payment_profile,
            transaction_token=txn_token,
            authorization_token=PaymentAuthorization.objects.create(
                payment_profile=payment_profile,
                authorization_code=secrets.token_hex(16)
            ),
            verification_token=PaymentVerification.objects.create(
                payment_profile=payment_profile,
                verification_code=secrets.token_hex(16)
            ),
            amount=amount_to_move,
            status='completed',
            transaction_category='transfer',
            payment_type='group' if target.payment_group else 'individual',
            balance_after=payment_profile.comrade_balance,
        )
        PiggyBankTransaction.objects.create(
            piggy_bank=target,
            event_type='conversion',
            amount=amount_to_move,
            performed_by=payment_profile,
            balance_after=target.current_amount,
            note=f"Conversion approved by admin",
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
            target.save()
            
            import secrets
            member = None
            if target.payment_group:
                member = PaymentGroupMember.objects.filter(payment_group=target.payment_group, payment_profile=payment_profile).first()
                
            transaction = TransactionToken.objects.create(
                payment_profile=payment_profile,
                transaction_code=uuid.uuid4(),
                amount=Decimal(str(automation_amount)),
                transaction_type='transfer',
                description=f'Automation: Transferred from {target.name} to wallet',
                payment_group=target.payment_group,
                piggy_bank=target,
                balance_after=target.current_amount
            )
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
                amount=Decimal(str(automation_amount)),
                status='completed',
                transaction_category='transfer',
                payment_type='group' if target.payment_group else 'individual',
                balance_after=payment_profile.comrade_balance,
                group_member_balance_after=member.total_contributed if member else None
            )
            PiggyBankTransaction.objects.create(
                piggy_bank=target,
                event_type='withdrawal',
                amount=automation_amount,
                performed_by=payment_profile,
                balance_after=target.current_amount,
                note=f'Automation: Transferred to wallet',
            )
            
        elif action == 'group_fund':
            # Add to group fund
            if not target.payment_group:
                return Response({'error': 'No group associated with this piggy bank.'}, status=status.HTTP_400_BAD_REQUEST)
            
            target.payment_group.current_amount += Decimal(str(automation_amount))
            target.payment_group.save()
            target.current_amount -= Decimal(str(automation_amount))
            target.save()
            
            import secrets
            member = PaymentGroupMember.objects.filter(payment_group=target.payment_group, payment_profile=payment_profile).first()
            
            transaction = TransactionToken.objects.create(
                payment_profile=payment_profile,
                transaction_code=uuid.uuid4(),
                amount=Decimal(str(automation_amount)),
                transaction_type='transfer',
                description=f'Automation: Added to group fund from {target.name}',
                payment_group=target.payment_group,
                piggy_bank=target,
                balance_after=target.payment_group.current_amount
            )
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
                amount=Decimal(str(automation_amount)),
                status='completed',
                transaction_category='transfer',
                payment_type='group',
                balance_after=payment_profile.comrade_balance,
                group_member_balance_after=member.total_contributed if member else None
            )
            PiggyBankTransaction.objects.create(
                piggy_bank=target,
                event_type='withdrawal',
                amount=automation_amount,
                performed_by=payment_profile,
                balance_after=target.current_amount,
                note=f'Automation: Transferred to group fund',
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
        if 'description' in request.data:
            val = request.data['description']
            target.description = val if val else ''
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
        
        # Leave rules
        if 'leave_requires_vote' in request.data:
            target.leave_requires_vote = bool(request.data['leave_requires_vote'])
        if 'leave_inconvenience_fee_percentage' in request.data and request.data['leave_inconvenience_fee_percentage'] is not None:
            target.leave_inconvenience_fee_percentage = Decimal(str(request.data['leave_inconvenience_fee_percentage']))
        if 'leave_vote_waives_penalty' in request.data:
            target.leave_vote_waives_penalty = bool(request.data['leave_vote_waives_penalty'])
        
        target.save()
        
        return Response({
            'status': 'Settings updated',
            'data': {
                'name': target.name,
                'description': target.description,
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
                'require_min_contribution_amount': float(target.require_min_contribution_amount) if target.require_min_contribution_amount else None,
                'leave_requires_vote': target.leave_requires_vote,
                'leave_inconvenience_fee_percentage': float(target.leave_inconvenience_fee_percentage),
                'leave_vote_waives_penalty': target.leave_vote_waives_penalty
            }
        })

    @action(detail=False, methods=['get'])
    def search_automation_targets(self, request):
        """Search for products, services, courses, subscriptions, etc for automation."""
        query = request.query_params.get('q', '')
        target_type = request.query_params.get('type', 'all')
        
        def resolve_image_url(req, path):
            if not path:
                return None
            path_str = str(path)
            if path_str.startswith('http://') or path_str.startswith('https://'):
                return path_str
            return req.build_absolute_uri(path_str)

        results = {
            'products': [],
            'services': [],
            'courses': [],
            'subscriptions': [],
            'groups': [],
            'investments': [],
            'donations': [],
            'loans': [],
            'bills': [],
            'insurance': []
        }
        
        # Search Products
        if target_type in ['all', 'product']:
            from Payment.models import Product
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )[:10]
            
            if not products.exists() and len(query.split()) > 1:
                query_words = query.split()
                q_object = Q()
                for word in query_words:
                    q_object |= Q(name__icontains=word)
                products = Product.objects.filter(q_object)[:10]
            results['products'] = [{
                'id': str(p.id),
                'name': p.name,
                'type': 'product',
                'price': float(p.price) if p.price else 0,
                'image': resolve_image_url(request, p.image_url) if p.image_url else None,
                'seller': None
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
                'image': resolve_image_url(request, s.image.url) if s.image else None,
                'provider': s.provider.business_name if s.provider else None
            } for s in services]
        
        # Search Courses (Specialization app)
        if target_type in ['all', 'course']:
            try:
                from Specialization.models import Specialization, Stack
                
                # Fetch Specializations, Courses, Masterclasses that are paid (not free)
                specialization_query = Specialization.objects.filter(is_paid=True, price__gt=0)
                if query:
                    specialization_query = specialization_query.filter(
                        Q(name__icontains=query) | Q(description__icontains=query)
                    )
                
                course_list = []
                for c in specialization_query[:15]:
                    course_list.append({
                        'id': str(c.id),
                        'name': f"{c.get_learning_type_display()}: {c.name}" if c.learning_type else c.name,
                        'type': c.learning_type or 'course',
                        'price': float(c.price) if c.price else 0,
                        'image': resolve_image_url(request, c.image_url) if c.image_url else None,
                        'instructor': None
                    })
                
                # Fetch Stacks belonging to any paid specialization
                stack_query = Stack.objects.filter(specialization_stacks__is_paid=True, specialization_stacks__price__gt=0).distinct()
                if query:
                    stack_query = stack_query.filter(
                        Q(name__icontains=query) | Q(description__icontains=query)
                    )
                
                for st in stack_query[:15]:
                    parent_spec = st.specialization_stacks.filter(is_paid=True, price__gt=0).first()
                    price = float(parent_spec.price) if parent_spec and parent_spec.price else 49.99
                    course_list.append({
                        'id': str(st.id),
                        'name': f"Stack: {st.name}",
                        'type': 'stack',
                        'price': price,
                        'image': resolve_image_url(request, st.image_url) if st.image_url else None,
                        'instructor': None
                    })
                
                results['courses'] = course_list
            except Exception as e:
                print(f"Error fetching courses: {e}")
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
        
        # Search Bookings
        if target_type in ['all', 'booking']:
            try:
                from Payment.models import Booking
                bookings = Booking.objects.filter(
                    Q(establishment__name__icontains=query) | Q(booking_type__icontains=query)
                ).filter(status='confirmed')[:10]
                results['bookings'] = [{
                    'id': str(b.id),
                    'name': f"{b.get_booking_type_display()} at {b.establishment.name}",
                    'type': 'booking',
                    'price': float(b.total_price) if b.total_price else 0,
                    'image': resolve_image_url(request, b.establishment.logo.url) if b.establishment.logo else None
                } for b in bookings]
            except:
                pass
        
        # Search Groups
        if target_type in ['all', 'group']:
            try:
                from Payment.models import PaymentGroups
                groups = PaymentGroups.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(is_active=True, is_public=True)[:10]
                results['groups'] = [{
                    'id': str(g.id),
                    'name': g.name,
                    'type': 'group',
                    'entry_fee': float(g.entry_fee_amount) if g.entry_fee_required and g.entry_fee_amount else 0,
                    'member_count': g.members.count()
                } for g in groups]
            except Exception:
                pass
        
        # Search Investment opportunities
        if target_type in ['all', 'investment']:
            try:
                from Funding.models import Business, CapitalVenture
                investments = []
                businesses = Business.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(status='active')[:5]
                for b in businesses:
                    image_path = b.cover_photo.url if hasattr(b, 'cover_photo') and b.cover_photo else (b.logo.url if hasattr(b, 'logo') and b.logo else None)
                    investments.append({
                        'id': str(b.id),
                        'name': b.name,
                        'type': 'investment',
                        'price': float(b.min_investment) if hasattr(b, 'min_investment') else 0,
                        'min_amount': float(b.min_investment) if hasattr(b, 'min_investment') else 0,
                        'expected_return': b.expected_return if hasattr(b, 'expected_return') else None,
                        'image': resolve_image_url(request, image_path) if image_path else None
                    })
                ventures = CapitalVenture.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(status='active')[:5]
                for v in ventures:
                    image_path = v.cover_photo.url if hasattr(v, 'cover_photo') and v.cover_photo else (v.logo.url if hasattr(v, 'logo') and v.logo else None)
                    investments.append({
                        'id': str(v.id),
                        'name': v.name,
                        'type': 'investment',
                        'price': float(v.min_investment) if hasattr(v, 'min_investment') else 0,
                        'min_amount': float(v.min_investment) if hasattr(v, 'min_investment') else 0,
                        'expected_return': v.expected_return if hasattr(v, 'expected_return') else None,
                        'image': resolve_image_url(request, image_path) if image_path else None
                    })
                results['investments'] = investments[:10]
            except:
                pass
        
        # Search Donations
        if target_type in ['all', 'donation']:
            try:
                from Payment.models import Donation
                donations = Donation.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(status='collecting')[:10]
                results['donations'] = [{
                    'id': str(d.id),
                    'name': d.name,
                    'type': 'donation',
                    'target_amount': float(d.total_amount) if d.total_amount else 0,
                    'current_amount': float(d.amount_collected) if d.amount_collected else 0
                } for d in donations]
            except Exception:
                pass

        # Search Loans (active loan applications for repayment)
        if target_type in ['all', 'loan_repayment', 'loan']:
            try:
                from Payment.models import LoanApplication
                from Authentication.models import Profile
                try:
                    profile = Profile.objects.get(user=request.user)
                except Exception:
                    profile = None
                
                group_id = request.query_params.get('group_id')
                
                loans_qs = LoanApplication.objects.filter(status__in=['disbursed', 'repaying'])
                if group_id:
                    loans_qs = loans_qs.filter(group_id=group_id)
                elif profile:
                    loans_qs = loans_qs.filter(user=profile)
                
                loans = loans_qs[:10]
                results['loans'] = [{
                    'id': str(l.id),
                    'name': f"Loan #{str(l.id)[:8]} - KES {l.amount} ({l.loan_product.name})",
                    'type': 'loan_repayment',
                    'amount': float(l.amount),
                    'total_repayment': float(l.total_repayment),
                    'monthly_payment': float(l.monthly_payment),
                    'status': l.status
                } for l in loans]
            except Exception as e:
                print(f"Error fetching loans: {e}")
                pass

        # Search Bills
        if target_type in ['all', 'bills', 'bill_payment']:
            try:
                from Payment.models import BillProvider
                providers = BillProvider.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(is_active=True)[:10]
                results['bills'] = [{
                    'id': str(bp.id),
                    'name': bp.name,
                    'type': 'bills',
                    'category': bp.category,
                    'image': resolve_image_url(request, bp.logo.url) if bp.logo else None,
                    'min_amount': float(bp.min_amount),
                    'max_amount': float(bp.max_amount)
                } for bp in providers]
            except Exception as e:
                print(f"Error fetching bills: {e}")
                pass

        # Search Insurance (ServiceProducts of type insurance)
        if target_type in ['all', 'insurance']:
            try:
                from Payment.models import ServiceProduct
                insurance_products = ServiceProduct.objects.filter(
                    Q(name__icontains=query) | Q(description__icontains=query)
                ).filter(service_type='insurance', status='active')[:10]
                results['insurance'] = [{
                    'id': str(ip.id),
                    'name': ip.name,
                    'type': 'insurance',
                    'price': float(ip.price) if ip.price else 0,
                    'image': resolve_image_url(request, ip.image.url) if ip.image else None,
                    'provider': ip.provider.business_name if ip.provider else None
                } for ip in insurance_products]
            except Exception as e:
                print(f"Error fetching insurance: {e}")
                pass
        
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
            payment_profile.comrade_balance -= Decimal(str(total))
            payment_profile.save()
            
            # Create a TransactionToken for the purchase
            import secrets
            import uuid
            transaction = TransactionToken.objects.create(
                payment_profile=payment_profile,
                transaction_code=uuid.uuid4(),
                amount=Decimal(str(total)),
                transaction_type='purchase',
                pay_from='wallet',
                payment_option='comrade_balance',
                description='Online purchase order'
            )
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
                amount=Decimal(str(total)),
                status='completed',
                transaction_category='purchase',
                payment_type='individual',
                balance_after=payment_profile.comrade_balance,
                group_member_balance_after=None
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


class StandingOrderViewSet(ModelViewSet):
    serializer_class = StandingOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        payment_profile = get_or_create_payment_profile(self.request.user)
        if not payment_profile:
            return StandingOrder.objects.none()
        return StandingOrder.objects.filter(member__payment_profile=payment_profile).order_by('-created_at')

    def perform_create(self, serializer):
        payment_profile = get_or_create_payment_profile(self.request.user)
        if not payment_profile:
            raise serializers.ValidationError("Payment profile not found")
        group_id = self.request.data.get('group_id')
        if group_id:
            try:
                member = PaymentGroupMember.objects.get(payment_group_id=group_id, payment_profile=payment_profile)
            except PaymentGroupMember.DoesNotExist:
                raise serializers.ValidationError("You are not a member of this payment group")
            serializer.save(member=member)
        else:
            serializer.save()

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        order = self.get_object()
        is_active = request.data.get('is_active', not order.is_active)
        order.is_active = is_active
        order.status = 'active' if is_active else 'paused'
        order.save()
        return Response(StandingOrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        order.status = 'rejected'
        order.is_active = False
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

        # Always recompute from real data — scores should be fresh
        from Payment.services.credit_scoring import compute_credit_score
        result = compute_credit_score(profile)

        score.score = result['total_score']
        score.savings_score = result['savings_score']
        score.repayment_score = result['repayment_score']
        score.group_score = result['group_score']
        score.transaction_score = result['transaction_score']
        score.tenure_score = result['tenure_score']
        score.factors = result['factors']
        score.risk_level = (
            'very_low' if result['total_score'] > 700 else
            'low' if result['total_score'] > 600 else
            'moderate' if result['total_score'] > 450 else
            'high' if result['total_score'] > 300 else
            'very_high'
        )
        score.computed_at = timezone.now()
        score.save()

        return Response(CreditScoreSerializer(score).data)


class LoanRepaymentViewSet(ModelViewSet):
    """
    ViewSet for LoanRepayment — enables listing and managing individual loan repayments.
    Previously this was only accessible via the LoanApplication serializer.
    """
    serializer_class = LoanRepaymentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    def get_queryset(self):
        profile = get_or_create_payment_profile(self.request.user)
        return LoanRepayment.objects.filter(loan__user=profile).order_by('due_date')

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        profile = get_or_create_payment_profile(request.user)
        repayments = LoanRepayment.objects.filter(
            loan__user=profile,
            status__in=['upcoming', 'due']
        ).order_by('due_date')
        serializer = LoanRepaymentSerializer(repayments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        profile = get_or_create_payment_profile(request.user)
        repayments = LoanRepayment.objects.filter(
            loan__user=profile,
            status='overdue'
        ).order_by('due_date')
        serializer = LoanRepaymentSerializer(repayments, many=True)
        return Response(serializer.data)


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
        product = loan.loan_product

        min_score = product.min_credit_score
        if min_score and min_score > 0:
            credit = getattr(loan.user, 'credit_score', None)
            if credit is None:
                return Response(
                    {'error': 'Credit score not yet computed. Complete more transactions to generate a score.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if credit.score < min_score:
                loan.status = 'rejected'
                loan.rejection_reason = (
                    f'Credit score {credit.score} is below the minimum {min_score} '
                    f'required for {product.name}.'
                )
                loan.reviewed_by = request.user
                loan.reviewed_at = timezone.now()
                loan.save()
                return Response(
                    {'status': 'rejected', 'reason': loan.rejection_reason},
                    status=status.HTTP_400_BAD_REQUEST
                )

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
                    description=f"Loan Disbursement: {product.name}",
                    payment_group=product.group if (getattr(product, 'is_group_loan', False) and getattr(product, 'group', None)) else None
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
                    description=f"Loan Repayment: {product.name}",
                    payment_group=product.group if (getattr(product, 'is_group_loan', False) and getattr(product, 'group', None)) else None
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
        """Fund an escrow — supports wallet, stripe (hold), flutterwave, paystack, pesapal."""
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
        
        elif payment_method == 'paystack':
            from Payment.services.payment_service import PaystackProvider
            result = PaystackProvider.initiate_payment(
                amount=float(escrow.total_amount),
                currency=request.data.get('currency', 'KES'),
                email=request.user.email,
                description=f'Escrow: {escrow.title}',
            )
            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
            
            escrow.payment_gateway = 'paystack'
            escrow.payment_intent_id = result.get('reference', '')
            escrow.save()
            return Response({
                'status': 'redirect',
                'gateway': 'paystack',
                'authorization_url': result['authorization_url'],
                'reference': result['reference'],
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
        provider_id = self.request.query_params.get('provider_registration')
        if provider_id:
            qs = qs.filter(provider_registration_id=provider_id)
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
            from decimal import Decimal
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        payment_profile = get_or_create_payment_profile(user)
        
        # Lock profile to prevent race conditions
        payment_profile = PaymentProfile.objects.select_for_update().get(id=payment_profile.id)
        
        # Balance check
        if payment_profile.comrade_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct
        payment_profile.comrade_balance -= amount
        payment_profile.save()
        
        # Update donation total atomically
        donation = Donation.objects.select_for_update().get(id=donation.id)
        donation.amount_collected += Decimal(str(amount))
        donation.save()
        
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
            donor_profile=payment_profile,
            member=member,
            amount=amount,
            status='confirmed',
            confirmed_at=timezone.now()
        )
        
        # Create wallet transaction
        import secrets
        import uuid
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            transaction_type='contribution',
            amount=amount,
            payment_option='comrade_balance',
            description=f'Donation contribution to {donation.name}',
            payment_group=donation.payment_group if donation.payment_group else None,
            balance_after=donation.amount_collected
        )
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
            status='completed',
            transaction_category='contribution',
            payment_type='group' if donation.payment_group else 'individual',
            balance_after=payment_profile.comrade_balance,
            group_member_balance_after=member.total_contributed if member else None
        )

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
        
        # Create transaction record
        transaction = TransactionToken.objects.create(
            payment_profile=payment_profile,
            transaction_code=uuid.uuid4(),
            amount=final_amount,
            transaction_type='investment_withdrawal',
            description=f'Early withdrawal from investment. Penalty: {penalty_amount}',
            payment_group=investment.payment_group,
        )
        
        # Create History
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
            amount=final_amount,
            status='completed'
        )
        
        # Update proportional ownership
        if investment.quoting_mode == 'proportional' and investment.amount_collected > 0:
            for q in investment.quotes.all():
                q.ownership_percentage = (q.amount_quoted / investment.amount_collected) * 100
                q.save()
                
        return Response({
            'status': 'Withdrawal processed',
            'penalty_applied': float(penalty_amount),
            'amount_received': float(final_amount),
            'new_balance': float(payment_profile.comrade_balance)
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
            description=f'Round contribution to {round_obj.round_name or "Round " + str(round_obj.round_number)} - Cycle {round_obj.current_cycle}',
            payment_group=round_obj.payment_group
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
            description=f'Round Payout - {round_obj.round_name or "Round " + str(round_obj.round_number)} Cycle {round_obj.current_cycle} claimed',
            payment_group=round_obj.payment_group
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
        # PaymentGroups has no calculate_withdrawal_penalty; that is on GroupTarget.
        # Setting to 0.00 to prevent AttributeError.
        early_penalty = Decimal('0.00')
        if early_penalty > 0:
            withdrawal.early_withdrawal_penalty = early_penalty
            deduction += early_penalty
            
        payout = withdrawal.amount - deduction
        
        with db_transaction.atomic():
            # Update destination wallet
            withdrawal.destination_wallet.comrade_balance += payout
            withdrawal.destination_wallet.save()
            
            # Deduct only the payout from the group amount (the group pool retains the penalty)
            withdrawal.payment_group.current_amount -= payout
            withdrawal.payment_group.save()
            
            # Record the net payout transaction
            transaction = TransactionToken.objects.create(
                payment_profile=payment_profile, # Platform/Group Admin
                recipient_profile=withdrawal.destination_wallet,
                amount=payout,
                transaction_type='withdrawal',
                status='completed',
                description=f"Withdrawal from {withdrawal.payment_group.name} (Net)",
                payment_group=withdrawal.payment_group,
                payment_option='comrade_balance',
                pay_from='internal',
                balance_after=withdrawal.payment_group.current_amount
            )
            
            from Payment.models import TransactionHistory, PaymentAuthorization, PaymentVerification
            import secrets
            TransactionHistory.objects.create(
                payment_profile=withdrawal.destination_wallet,
                transaction_token=transaction,
                authorization_token=PaymentAuthorization.objects.create(
                    payment_profile=withdrawal.destination_wallet,
                    authorization_code=secrets.token_hex(16)
                ),
                verification_token=PaymentVerification.objects.create(
                    payment_profile=withdrawal.destination_wallet,
                    verification_code=secrets.token_hex(16)
                ),
                amount=payout,
                status='completed',
                transaction_category='withdrawal',
                payment_type='group',
                balance_after=withdrawal.destination_wallet.comrade_balance
            )
            
            # Record the penalty deduction transaction if any
            if deduction > 0:
                TransactionToken.objects.create(
                    payment_profile=withdrawal.destination_wallet,
                    recipient_profile=payment_profile, # Conceptually returned to the Group Pool/Admin
                    amount=deduction,
                    transaction_type='fee',
                    status='completed',
                    description=f"Immature Exit Penalty for {withdrawal.payment_group.name}",
                    payment_group=withdrawal.payment_group,
                    balance_after=withdrawal.payment_group.current_amount + deduction # Optional
                )
            
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
        from django.db.models.functions import TruncDate
        from datetime import timedelta, datetime
        from django.utils import timezone

        kitty_balance = 0.0
        if provider.linked_payment_group:
            kitty_balance = float(provider.linked_payment_group.current_amount or 0)

        pending_applications_count = provider.applications.filter(
            status__in=['submitted', 'under_review']
        ).count()
        pending_queries_count = provider.queries.filter(
            status__in=['open', 'in_progress', 'pending_response']
        ).count()
        active_products_count = provider.service_products.filter(status='active').count()
        staff_count = provider.staff_members.filter(status='active').count()

        total_volume = float(provider.transactions.aggregate(Sum('amount'))['amount__sum'] or 0)

        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_qs = provider.transactions.filter(
            created_at__gte=thirty_days_ago
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            daily_total=Sum('amount')
        ).order_by('date')
        daily_revenue = [
            {'date': str(entry['date']), 'amount': float(entry['daily_total'] or 0)}
            for entry in daily_qs
        ]

        recent_items = []
        for txn in provider.transactions.order_by('-created_at')[:5]:
            recent_items.append({
                'type': 'transaction',
                'id': str(txn.id),
                'description': txn.description or f'Transaction {txn.reference_number}',
                'amount': float(txn.amount),
                'status': txn.status,
                'timestamp': txn.created_at.isoformat(),
            })
        for query in provider.queries.order_by('-created_at')[:5]:
            recent_items.append({
                'type': 'query',
                'id': str(query.id),
                'description': query.subject,
                'status': query.status,
                'priority': query.priority,
                'timestamp': query.created_at.isoformat(),
            })
        for app in provider.applications.order_by('-created_at')[:5]:
            recent_items.append({
                'type': 'application',
                'id': str(app.id),
                'description': app.application_type.replace('_', ' ').title(),
                'status': app.status,
                'timestamp': app.created_at.isoformat(),
            })
        recent_items.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_activity = recent_items[:8]

        stats = {
            'total_transactions': provider.transactions.count(),
            'total_queries': provider.queries.count(),
            'pending_applications': pending_applications_count,
            'active_products': active_products_count,
            'staff_count': staff_count,
            'total_volume': total_volume,
            'pending_queries': pending_queries_count,
            'kitty_balance': kitty_balance,
            'daily_revenue': daily_revenue,
            'recent_activity': recent_activity,
        }
        return Response(stats)

    @action(detail=True, methods=['get'])
    def kitty_analytics(self, request, pk=None):
        provider = self.get_object()
        kitty = provider.linked_payment_group
        from django.db.models import Sum
        from datetime import timedelta

        kitty_balance = float(kitty.current_amount or 0) if kitty else 0.0

        # ── Transactions from ProviderTransaction ──
        ptxns = provider.transactions.all()
        total_inflows = float(ptxns.filter(
            transaction_type__in=['payment', 'commission', 'payout']
        ).aggregate(Sum('amount'))['amount__sum'] or 0)
        total_outflows = float(ptxns.filter(
            transaction_type__in=['refund', 'fee', 'adjustment']
        ).aggregate(Sum('amount'))['amount__sum'] or 0)
        net_profit_loss = total_inflows - total_outflows

        # ── Monthly trend (last 12 months) ──
        monthly_trend = []
        for i in range(11, -1, -1):
            start = timezone.now().replace(day=1) - timedelta(days=30 * i)
            end = (start + timedelta(days=32)).replace(day=1)
            inflows = float(ptxns.filter(
                created_at__gte=start, created_at__lt=end,
                transaction_type__in=['payment', 'commission', 'payout']
            ).aggregate(Sum('amount'))['amount__sum'] or 0)
            outflows = float(ptxns.filter(
                created_at__gte=start, created_at__lt=end,
                transaction_type__in=['refund', 'fee', 'adjustment']
            ).aggregate(Sum('amount'))['amount__sum'] or 0)
            monthly_trend.append({
                'month': start.strftime('%Y-%m'),
                'revenue': inflows,
                'expenses': outflows,
            })

        # ── Service breakdown ──
        service_revenue = []
        for svc_type, svc_label in [
            ('bill_payment', 'Bills'), ('insurance', 'Insurance'),
            ('loan', 'Loans'), ('investment', 'Investments'),
            ('course', 'Courses'), ('other', 'Other'),
        ]:
            products = provider.service_products.filter(service_type=svc_type)
            prod_ids = products.values_list('id', flat=True)
            rev = float(ProviderTransaction.objects.filter(
                provider=provider, service_product_id__in=prod_ids,
                transaction_type='payment'
            ).aggregate(Sum('amount'))['amount__sum'] or 0)
            if rev > 0:
                service_revenue.append({'type': svc_label, 'amount': rev})

        active_products_count = provider.service_products.filter(status='active').count()

        performance_score = min(100, int(
            (kitty_balance / 10000) * 20 +
            (ptxns.count() * 2) + (active_products_count * 10)
        )) if active_products_count or kitty_balance else 0

        stats = {
            'current_balance': kitty_balance,
            'total_inflows': total_inflows,
            'total_outflows': total_outflows,
            'net_profit_loss': net_profit_loss,
            'monthly_trend': monthly_trend,
            'service_revenue': service_revenue,
            'performance_score': performance_score,
            'total_products': active_products_count,
            'total_transactions': ptxns.count(),
        }
        return Response(stats)

    @action(detail=True, methods=['post'])
    def publish_opportunity(self, request, pk=None):
        """
        Publish an investment opportunity linked to this provider registration.
        """
        provider = self.get_object()
        title = request.data.get('title')
        description = request.data.get('description', '')
        opp_type = request.data.get('type', 'stock')
        expected_return = request.data.get('expected_return', '')
        risk_level = request.data.get('risk_level', 'medium')
        min_individual_entry = request.data.get('min_individual_entry', 0)
        min_group_entry = request.data.get('min_group_entry', 0)
        gain_intervals = request.data.get('gain_intervals', 'monthly')
        maturity_period = request.data.get('maturity_period', '')
        link = request.data.get('link', '')

        if not title:
            return Response({'error': 'Title is required'}, status=status.HTTP_400_BAD_REQUEST)

        if provider.status != 'approved':
            return Response({'error': 'Provider must be approved to publish opportunities'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            opportunity = InvestmentOpportunity.objects.create(
                title=title,
                description=description,
                provider=provider.business_name,
                provider_registration=provider,
                type=opp_type,
                expected_return=expected_return,
                risk_level=risk_level,
                min_investment=min_individual_entry,
                min_individual_entry=min_individual_entry,
                min_group_entry=min_group_entry,
                gain_intervals=gain_intervals,
                maturity_period=maturity_period or None,
                link=link or None,
                is_active=True,
            )
            serializer = InvestmentOpportunitySerializer(opportunity)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def my_loan_products(self, request, pk=None):
        provider = self.get_object()
        products = LoanProduct.objects.filter(
            provider_registration=provider
        ).order_by('interest_rate')
        serializer = LoanProductSerializer(products, many=True)
        return Response(serializer.data)

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
    def request_payout(self, request, pk=None):
        """
        Request a payout of funds from the Provider's kitty/wallet to their external bank account.
        """
        provider = self.get_object()
        
        # Security: Only authorized staff or admins can request payouts
        profile = Profile.objects.get(user=request.user)
        try:
            staff = ProviderStaff.objects.get(provider=provider, user=profile)
            if not staff.can_manage_transactions and not request.user.is_staff:
                return Response({'error': 'You do not have permission to request payouts'}, status=status.HTTP_403_FORBIDDEN)
        except ProviderStaff.DoesNotExist:
            if not request.user.is_staff and not request.user.is_superuser:
                return Response({'error': 'You do not have permission to request payouts'}, status=status.HTTP_403_FORBIDDEN)

        amount_str = request.data.get('amount')
        payout_method = request.data.get('method', 'stripe') # stripe, flutterwave, paystack, mpesa
        destination_account = request.data.get('destination_account')
        
        if not amount_str or not destination_account:
            return Response({'error': 'amount and destination_account are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            amount = Decimal(amount_str)
        except:
            return Response({'error': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)
            
        if amount <= 0:
            return Response({'error': 'Payout amount must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)

        kitty = provider.linked_payment_group
        if not kitty or kitty.balance < amount:
            return Response({'error': 'Insufficient funds in provider kitty'}, status=status.HTTP_400_BAD_REQUEST)

        # Process the Payout via selected Gateway
        # Note: In production, Stripe payouts use the Stripe Connect Transfers API.
        # For this prototype/MVP, we'll log it as a transaction and deduct the balance.
        
        with db_transaction.atomic():
            kitty.balance -= amount
            kitty.save()
            
            # Create a ProviderTransaction for the ledger
            tx = ProviderTransaction.objects.create(
                provider=provider,
                user=profile,
                transaction_type='payout',
                amount=amount,
                payment_method=payout_method,
                status='completed', # Assuming synchronous for MVP
                reference_number=f"PAYOUT-{uuid.uuid4().hex[:10].upper()}",
                description=f"Automated Payout to {destination_account}"
            )
            
            # Optionally trigger Flutterwave/Stripe actual transfer API here 
            # if payout_method == 'flutterwave':
            #    res = FlutterwaveProvider.initiate_transfer(...)
            
        create_notification(
            user=profile.user,
            title="Payout Processed",
            message=f"A payout of {amount} has been initiated to your {payout_method} account.",
            notification_type='payment'
        )

        return Response({
            'status': 'success',
            'message': 'Payout processed successfully',
            'transaction_id': tx.id,
            'amount': float(amount)
        })

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
        
        if tx.status not in ['completed', 'pending']:
            return Response({'error': f'Transaction cannot be refunded from status: {tx.status}'}, status=status.HTTP_400_BAD_REQUEST)

        profile = Profile.objects.get(user=self.request.user)
        try:
            staff = ProviderStaff.objects.get(provider=tx.provider, user=profile, can_manage_transactions=True)
        except ProviderStaff.DoesNotExist:
            return Response({'error': 'You do not have permission to refund transactions'}, status=status.HTTP_403_FORBIDDEN)
            
        reason = request.data.get('reason', 'requested_by_customer')
        refund_amount_str = request.data.get('amount', str(tx.amount))
        try:
            refund_amount = Decimal(refund_amount_str)
        except:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
            
        if refund_amount > tx.amount:
            return Response({'error': 'Refund amount cannot exceed original transaction amount'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. External Gateway Refund (Stripe)
        if tx.payment_method == 'stripe':
            # Check if we have a Stripe payment intent ID
            stripe_id = None
            if tx.reference_number and tx.reference_number.startswith('pi_'):
                stripe_id = tx.reference_number
            elif tx.linked_transaction and tx.linked_transaction.payment_number and tx.linked_transaction.payment_number.startswith('pi_'):
                stripe_id = tx.linked_transaction.payment_number

            if stripe_id:
                stripe_res = StripeProvider.create_refund(
                    payment_intent_id=stripe_id,
                    amount=float(refund_amount),
                    reason=reason
                )
                if 'error' in stripe_res:
                    return Response({'error': stripe_res['error']}, status=status.HTTP_400_BAD_REQUEST)
                    
                # Update TransactionToken
                if tx.linked_transaction:
                    tx.linked_transaction.status = 'refunded' if refund_amount == tx.amount else 'partially_refunded'
                    tx.linked_transaction.reversal_reason = reason
                    tx.linked_transaction.save()
            else:
                return Response({'error': 'Could not locate Stripe Payment Intent ID for this transaction'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Comrade Balance Refund (Internal Ledger)
        elif tx.payment_method == 'comrade_balance':
            buyer_wallet = get_or_create_payment_profile(tx.user.user)
            provider_kitty = tx.provider.linked_payment_group
            
            if provider_kitty and provider_kitty.balance < refund_amount:
                return Response({'error': 'Provider Kitty has insufficient balance to cover this refund'}, status=status.HTTP_400_BAD_REQUEST)

            with db_transaction.atomic():
                if buyer_wallet:
                    buyer_wallet.balance += refund_amount
                    buyer_wallet.save()
                    
                if provider_kitty:
                    provider_kitty.balance -= refund_amount
                    provider_kitty.save()
                    
                if tx.linked_transaction:
                    tx.linked_transaction.status = 'refunded' if refund_amount == tx.amount else 'partially_refunded'
                    tx.linked_transaction.reversal_reason = reason
                    tx.linked_transaction.save()

        # Update ProviderTransaction status
        tx.status = 'refunded' if refund_amount == tx.amount else 'partially_refunded'
        tx.metadata['refund_reason'] = reason
        tx.metadata['refund_amount'] = str(refund_amount)
        tx.save()
        
        # Notify user about refund
        create_notification(
            recipient=tx.user.user,
            notification_type='provider_transaction_refund',
            title='Refund Issued',
            message=f"A refund of {refund_amount} has been issued by {tx.provider.business_name}.",
            action_url=f"/payments/transactions/{tx.id}",
            extra_data={
                'provider': tx.provider.business_name,
                'amount': str(refund_amount),
                'reason': reason,
                'reference': tx.reference_number,
                'transaction_id': str(tx.id),
            }
        )
        
        return Response({'status': tx.status, 'refunded_amount': float(refund_amount)})

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
        query = serializer.save(provider=provider, user=profile)
        
        create_notification(
            recipient=provider.user.user,
            notification_type='provider_new_query',
            title='New Query Received',
            message=f"You have a new query from {profile.user.get_full_name()}: {query.subject}",
            action_url=f"/providers/dashboard?tab=queries",
        )

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
        
        create_notification(
            recipient=query.user.user,
            notification_type='query_assigned',
            title='Query Now In Progress',
            message=f"Your query '{query.subject}' is now being handled by {staff.user.user.get_full_name()}",
            action_url=f"/payments/queries/{query.id}",
        )
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
        
        create_notification(
            recipient=query.user.user,
            notification_type='query_resolved',
            title='Query Resolved',
            message=f"Your query '{query.subject}' has been resolved by {staff.user.user.get_full_name()}",
            action_url=f"/payments/queries/{query.id}",
        )
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
        
        # Notify provider staff about new application
        create_notification(
            recipient=app.provider.user.user,
            notification_type='provider_application_submitted',
            title='New Application',
            message=f"New application from {app.user.user.get_full_name()} for {app.service_product.name}",
            action_url=f"/payments/provider-applications/{app.id}",
            extra_data={
                'provider': app.provider.business_name,
                'service_name': app.service_product.name,
                'application_id': str(app.id),
            }
        )
        
        # Notify user about submission confirmation
        create_notification(
            recipient=app.user.user,
            notification_type='provider_application_submitted',
            title='Application Submitted',
            message=f"Your application to {app.provider.business_name} for {app.service_product.name} has been submitted.",
            action_url=f"/payments/my-applications/{app.id}",
            extra_data={
                'provider': app.provider.business_name,
                'service_name': app.service_product.name,
                'application_id': str(app.id),
            }
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

        notification_type = 'provider_application_approved' if decision == 'approved' else 'provider_application_rejected'
        create_notification(
            recipient=app.user.user,
            notification_type=notification_type,
            title=f"Application {decision.title()}",
            message=f"Your application to {app.provider.business_name} for {app.service_product.name} has been {decision}.",
            action_url=f"/payments/provider-applications/{app.id}",
            extra_data={
                'provider': app.provider.business_name,
                'service_name': app.service_product.name,
                'application_id': str(app.id),
            }
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
            notification_type='provider_application_requires_changes',
            title='Action Required',
            message=f"{app.provider.business_name} has requested additional documents for your application.",
            action_url=f"/payments/provider-applications/{app.id}",
            extra_data={
                'provider': app.provider.business_name,
                'service_name': app.service_product.name,
                'application_id': str(app.id),
                'reason': f"Required documents: {', '.join(required_docs)}",
            }
        )
        return Response({'status': 'pending_documents', 'required_documents': required_docs})

    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        profile = Profile.objects.get(user=request.user)
        apps = ProviderApplication.objects.filter(user=profile).order_by('-created_at')
        return Response(ProviderApplicationSerializer(apps, many=True).data)


class ProviderRatingViewSet(ModelViewSet):
    serializer_class = ProviderRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        provider_id = self.request.query_params.get('provider')
        
        if provider_id:
            return ProviderRating.objects.filter(provider_id=provider_id, is_approved=True)
        
        return ProviderRating.objects.filter(user=profile)

    def get_serializer_class(self):
        if self.action == 'create':
            return ProviderRatingCreateSerializer
        return ProviderRatingSerializer

    def perform_create(self, serializer):
        profile = Profile.objects.get(user=self.request.user)
        
        transaction_id = self.request.data.get('related_transaction')
        application_id = self.request.data.get('related_application')
        
        if transaction_id:
            try:
                transaction = ProviderTransaction.objects.get(id=transaction_id, user=profile)
                serializer.save(user=profile, related_transaction=transaction, is_verified=True)
                return
            except ProviderTransaction.DoesNotExist:
                pass
        
        if application_id:
            try:
                application = ProviderApplication.objects.get(id=application_id, user=profile, status='approved')
                serializer.save(user=profile, related_application=application, is_verified=True)
                return
            except ProviderApplication.DoesNotExist:
                pass
        
        serializer.save(user=profile)

    @action(detail=False, methods=['get'])
    def for_provider(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({'error': 'provider_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ratings = ProviderRating.objects.filter(
            provider_id=provider_id,
            is_approved=True
        ).order_by('-created_at')
        
        return Response(ProviderRatingSerializer(ratings, many=True).data)

    @action(detail=False, methods=['get'])
    def provider_stats(self, request):
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({'error': 'provider_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        ratings = ProviderRating.objects.filter(provider_id=provider_id, is_approved=True)
        
        if not ratings.exists():
            return Response({
                'average_rating': 0,
                'total_reviews': 0,
                'five_star': 0, 'four_star': 0, 'three_star': 0, 'two_star': 0, 'one_star': 0
            })
        
        avg_rating = ratings.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0
        
        return Response({
            'average_rating': round(avg_rating, 1),
            'total_reviews': ratings.count(),
            'five_star': ratings.filter(overall_rating=5).count(),
            'four_star': ratings.filter(overall_rating=4).count(),
            'three_star': ratings.filter(overall_rating=3).count(),
            'two_star': ratings.filter(overall_rating=2).count(),
            'one_star': ratings.filter(overall_rating=1).count(),
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        rating = self.get_object()
        rating.is_approved = True
        rating.save()
        return Response({'is_approved': True})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        rating = self.get_object()
        rating.is_approved = False
        rating.save()
        return Response({'is_approved': False})


class InsuranceClaimReviewViewSet(ModelViewSet):
    """
    Provider-facing viewset for reviewing and processing insurance claims.
    Only provider staff with can_approve_claims can approve/reject.
    Staff can escalate to platform admins.
    """
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        profile = Profile.objects.get(user=self.request.user)
        provider_regs = ProviderRegistration.objects.filter(user=profile)
        provider_ids = provider_regs.values_list('id', flat=True)
        return InsuranceClaim.objects.filter(
            policy__product__provider_registration__id__in=provider_ids
        ).order_by('-created_at')

    def _check_staff_permission(self, claim):
        profile = Profile.objects.get(user=self.request.user)
        provider_reg_id = claim.policy.product.provider_registration_id
        if not provider_reg_id:
            return False, 'No provider linked to this insurance product'
        try:
            provider = ProviderRegistration.objects.get(id=provider_reg_id)
            staff = ProviderStaff.objects.get(provider=provider, user=profile)
            if not staff.can_approve_claims:
                return False, 'You do not have permission to review claims'
            return True, staff
        except ProviderStaff.DoesNotExist:
            return False, 'You are not authorized staff for this provider'

    @action(detail=True, methods=['post'])
    def review_claim(self, request, pk=None):
        claim = self.get_object()
        action = request.data.get('action')
        notes = request.data.get('notes', '')

        if action not in ['approve', 'reject', 'request_info']:
            return Response({'error': 'Invalid action. Use approve, reject, or request_info'},
                            status=status.HTTP_400_BAD_REQUEST)

        has_permission, result = self._check_staff_permission(claim)
        if not has_permission and not request.user.is_staff:
            return Response({'error': result}, status=status.HTTP_403_FORBIDDEN)

        if action == 'approve':
            claim.status = 'approved'
            claim.amount_approved = request.data.get('amount_approved', claim.amount_claimed)
        elif action == 'reject':
            claim.status = 'rejected'
        elif action == 'request_info':
            claim.status = 'under_review'

        claim.reviewer_notes = notes
        claim.reviewed_at = timezone.now()
        claim.save()

        return Response(InsuranceClaimSerializer(claim).data)

    @action(detail=True, methods=['post'])
    def payout_claim(self, request, pk=None):
        claim = self.get_object()

        if claim.status != 'approved':
            return Response({'error': 'Claim must be approved before payout'}, status=status.HTTP_400_BAD_REQUEST)

        has_permission, _ = self._check_staff_permission(claim)
        if not has_permission and not request.user.is_staff:
            return Response({'error': 'You do not have permission to process payouts'}, status=status.HTTP_403_FORBIDDEN)

        provider_reg_id = claim.policy.product.provider_registration_id
        provider = ProviderRegistration.objects.get(id=provider_reg_id) if provider_reg_id else None

        try:
            with db_transaction.atomic():
                payout_amount = claim.amount_approved or claim.amount_claimed
                claim.status = 'paid'
                claim.paid_at = timezone.now()
                claim.save()

                if provider and provider.linked_payment_group:
                    kitty = provider.linked_payment_group
                    if kitty.wallet_balance >= payout_amount:
                        kitty.wallet_balance -= Decimal(str(payout_amount))
                        kitty.save()

                claimant_pp = get_or_create_payment_profile(claim.claimant.user)
                claimant_pp.comrade_balance += Decimal(str(payout_amount))
                claimant_pp.save()

                TransactionToken.objects.create(
                    receiver_profile=claimant_pp,
                    amount=payout_amount,
                    transaction_type='insurance_payout',
                    status='completed',
                    description=f"Insurance payout: {claim.policy.policy_number}",
                    payment_group=provider.linked_payment_group if provider else None,
                )

                return Response({'status': 'paid', 'amount_paid': str(payout_amount)})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        claim = self.get_object()
        reason = request.data.get('reason', 'Escalated for admin review')
        claim.status = 'under_review'
        claim.reviewer_notes = f"{claim.reviewer_notes or ''}\nESCALATED: {reason}".strip()
        claim.save()
        return Response(InsuranceClaimSerializer(claim).data)


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
                payment_group=loan.group if loan.group else None
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