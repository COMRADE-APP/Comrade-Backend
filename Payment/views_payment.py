"""
Payment Processing Views
Handles payment methods, processing, refunds, webhooks, and payment method detection
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from django.conf import settings
import stripe
import json
import re
from Payment.models import (
    TransactionToken, TransactionHistory, PaymentProfile, PaymentLog,
    SavedPaymentMethod
)
from Payment.serializers import (
    TransactionTokenSerializer, TransactionHistorySerializer,
    SavedPaymentMethodSerializer, SavedPaymentMethodCreateSerializer
)
from Payment.services.payment_service import PaymentService
from Payment.utils import get_or_create_payment_profile
from datetime import datetime


# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


# ============================================================================
# CARD BRAND DETECTION UTILITY
# ============================================================================

def detect_card_brand(card_number):
    """Detect card brand from card number prefix (BIN)."""
    num = card_number.replace(' ', '').replace('-', '')
    if not num.isdigit():
        return 'unknown'
    
    # Visa: starts with 4
    if re.match(r'^4', num):
        return 'visa'
    # Mastercard: 51-55 or 2221-2720
    if re.match(r'^5[1-5]', num) or re.match(r'^2(2[2-9][1-9]|2[3-9]\d|[3-6]\d{2}|7[0-1]\d|720)', num):
        return 'mastercard'
    # Amex: 34 or 37
    if re.match(r'^3[47]', num):
        return 'amex'
    # Discover: 6011, 622126-622925, 644-649, 65
    if re.match(r'^6011', num) or re.match(r'^65', num) or re.match(r'^64[4-9]', num):
        return 'discover'
    # JCB: 3528-3589
    if re.match(r'^35(2[89]|[3-8]\d)', num):
        return 'jcb'
    # Diners Club: 300-305, 36, 38
    if re.match(r'^3(0[0-5]|[68])', num):
        return 'diners_club'
    # UnionPay: 62
    if re.match(r'^62', num):
        return 'unionpay'
    # Maestro: 5018, 5020, 5038, 6304, 6759, 6761, 6762, 6763
    if re.match(r'^(5018|5020|5038|6304|6759|676[1-3])', num):
        return 'maestro'
    
    return 'unknown'


def detect_payment_method_type(value):
    """Auto-detect whether input is a card number, phone number, or email."""
    value = value.strip()
    
    # Email check (PayPal)
    if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
        return {
            'method_type': 'paypal',
            'brand': 'paypal',
            'icon': 'paypal',
            'is_valid': True,
            'display': f'PayPal ({value})',
        }
    
    # Strip non-digits for number-based checks
    digits = re.sub(r'[\s\-\+\(\)]', '', value)
    
    if not digits.isdigit():
        return {
            'method_type': 'unknown',
            'brand': None,
            'icon': None,
            'is_valid': False,
            'display': 'Unknown format',
        }
    
    # Phone number patterns (M-Pesa / mobile money)
    # Kenya: 254..., 07..., 01...
    if re.match(r'^(254|0)(7|1)\d{8}$', digits) or re.match(r'^(254)\d{9}$', digits):
        return {
            'method_type': 'mpesa',
            'brand': 'mpesa',
            'icon': 'phone',
            'is_valid': True,
            'display': f'M-Pesa ({value})',
        }
    
    # General phone number (9-15 digits starting with country code or 0)
    if len(digits) >= 9 and len(digits) <= 15 and (digits.startswith('0') or len(digits) > 10):
        # Could be a phone number but not definitively M-Pesa
        return {
            'method_type': 'phone',
            'brand': 'mobile_money',
            'icon': 'phone',
            'is_valid': True,
            'display': f'Mobile Money ({value})',
        }
    
    # Card number (13-19 digits)
    if len(digits) >= 13 and len(digits) <= 19:
        brand = detect_card_brand(digits)
        brand_names = {
            'visa': 'Visa', 'mastercard': 'Mastercard', 'amex': 'American Express',
            'discover': 'Discover', 'jcb': 'JCB', 'diners_club': "Diner's Club",
            'unionpay': 'UnionPay', 'maestro': 'Maestro', 'unknown': 'Card',
        }
        return {
            'method_type': 'card',
            'brand': brand,
            'icon': brand,
            'is_valid': brand != 'unknown',
            'display': f'{brand_names.get(brand, "Card")} ending {digits[-4:]}',
        }
    
    return {
        'method_type': 'unknown',
        'brand': None,
        'icon': None,
        'is_valid': False,
        'display': 'Unknown format',
    }


# ============================================================================
# PAYMENT METHOD VIEWS
# ============================================================================

class PaymentMethodViewSet(ModelViewSet):
    """Manage saved payment methods"""
    permission_classes = [IsAuthenticated]
    serializer_class = SavedPaymentMethodSerializer
    
    def get_queryset(self):
        payment_profile = get_or_create_payment_profile(self.request.user)
        return SavedPaymentMethod.objects.filter(payment_profile=payment_profile)
    
    def create(self, request):
        """Add new payment method with validation and brand detection."""
        serializer = SavedPaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        payment_profile = get_or_create_payment_profile(request.user)
        method_type = data['method_type']
        
        # Build the saved method
        saved_method = SavedPaymentMethod(
            payment_profile=payment_profile,
            method_type=method_type,
            nickname=data.get('nickname', ''),
            is_default=data.get('is_default', False),
        )
        
        if method_type == 'card':
            card_number = data['card_number']
            saved_method.last_four = card_number[-4:]
            saved_method.card_brand = detect_card_brand(card_number)
            saved_method.expiry_month = data['expiry_month']
            saved_method.expiry_year = data['expiry_year']
            saved_method.billing_zip = data.get('billing_zip', '')
            saved_method.provider = 'stripe'
            
            # Create Stripe payment method token (if Stripe key is configured)
            if stripe.api_key:
                try:
                    pm = stripe.PaymentMethod.create(
                        type='card',
                        card={
                            'number': card_number,
                            'exp_month': data['expiry_month'],
                            'exp_year': data['expiry_year'],
                            'cvc': data['cvc'],
                        },
                    )
                    saved_method.provider_token = pm.id
                    saved_method.is_verified = True
                except stripe.error.CardError as e:
                    return Response(
                        {'error': f'Card verification failed: {e.user_message}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except Exception as e:
                    # Still save but mark as unverified
                    saved_method.is_verified = False
            
        elif method_type == 'mpesa':
            saved_method.phone_number = data['phone_number']
            saved_method.provider = 'mpesa'
            saved_method.is_verified = True  # M-Pesa verifies on transaction
            
        elif method_type == 'paypal':
            saved_method.paypal_email = data['paypal_email']
            saved_method.provider = 'paypal'
            
        elif method_type in ('bank_transfer', 'equity'):
            account = data['account_number']
            saved_method.bank_account_last_four = account[-4:]
            saved_method.bank_name = data.get('bank_name', 'Equity Bank' if method_type == 'equity' else '')
            saved_method.provider = 'equity' if method_type == 'equity' else 'bank'
        
        saved_method.save()
        
        return Response(
            SavedPaymentMethodSerializer(saved_method).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set a payment method as the default."""
        method = self.get_object()
        method.is_default = True
        method.save()  # save() automatically unsets other defaults
        return Response(SavedPaymentMethodSerializer(method).data)
    
    def partial_update(self, request, *args, **kwargs):
        """Update payment method details (nickname, phone, email, etc.)."""
        instance = self.get_object()
        
        # If setting as default, unset all others first
        if request.data.get('is_default'):
            SavedPaymentMethod.objects.filter(
                payment_profile=instance.payment_profile, is_default=True
            ).exclude(pk=instance.pk).update(is_default=False)
        
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Delete a saved payment method."""
        method = self.get_object()
        # If deleting default, set another as default
        was_default = method.is_default
        method.delete()
        if was_default:
            remaining = SavedPaymentMethod.objects.filter(
                payment_profile=get_or_create_payment_profile(request.user)
            ).first()
            if remaining:
                remaining.is_default = True
                remaining.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================================
# PAYMENT METHOD DETECTION API
# ============================================================================

class DetectPaymentMethodView(APIView):
    """Auto-detect payment method type from input value."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        value = request.data.get('value', '')
        if not value:
            return Response(
                {'error': 'A value (card number, phone number, or email) is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = detect_payment_method_type(value)
        return Response(result)


# ============================================================================
# PAYMENT PROCESSING
# ============================================================================

class ProcessPaymentView(APIView):
    """Process a payment transaction"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'USD')
        payment_method = request.data.get('payment_method')  # stripe, paypal, mpesa
        payment_method_id = request.data.get('payment_method_id')
        description = request.data.get('description', '')
        saved_method_id = request.data.get('saved_method_id')  # Use saved payment method
        
        if not amount or not payment_method:
            return Response(
                {'error': 'Amount and payment method are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = float(amount)
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be greater than zero'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid amount format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # If using a saved payment method, retrieve the provider token
            details = {
                'description': description,
                'payment_method_id': payment_method_id
            }
            
            if saved_method_id:
                try:
                    saved = SavedPaymentMethod.objects.get(
                        id=saved_method_id,
                        payment_profile=get_or_create_payment_profile(request.user)
                    )
                    details['payment_method_id'] = saved.provider_token
                    if saved.method_type == 'mpesa':
                        details['phone_number'] = saved.phone_number
                except SavedPaymentMethod.DoesNotExist:
                    return Response(
                        {'error': 'Saved payment method not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Call Payment Service
            response = PaymentService.process_payment(amount, currency, payment_method, details)
            
            if "error" in response:
                return Response({'error': response['error']}, status=status.HTTP_400_BAD_REQUEST)
                
            # Ensure payment profile exists
            payment_profile = get_or_create_payment_profile(request.user)
            
            # Create transaction token record
            transaction_token = TransactionToken.objects.create(
                payment_profile=payment_profile,
                amount=amount,
                transaction_type='purchase',
                payment_option=payment_method,
                description=description
            )
            
            # Create transaction history
            txn_status = 'completed' if response.get('status') == 'succeeded' else 'pending'
            
            TransactionHistory.objects.create(
                payment_profile=payment_profile,
                transaction_token=transaction_token,
                status=txn_status,
            )
            
            serializer = TransactionTokenSerializer(transaction_token)
            
            return Response({
                'message': 'Payment processed successfully',
                'transaction': serializer.data,
                'provider_response': response
            })
        
        except Exception as e:
            return Response(
                {'error': f'Payment failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefundPaymentView(APIView):
    """Process payment refund"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        amount = request.data.get('amount')  # Optional partial refund
        reason = request.data.get('reason', '')
        
        if not transaction_id:
            return Response(
                {'error': 'Transaction ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            transaction = TransactionToken.objects.get(
                transaction_code=transaction_id
            )
        except TransactionToken.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already refunded via history
        recent_history = TransactionHistory.objects.filter(
            transaction_token=transaction
        ).last()
        
        if recent_history and recent_history.status == 'refunded':
            return Response(
                {'error': 'Transaction already refunded'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            if transaction.payment_option in ('stripe', 'visa', 'mastercard'):
                # Process Stripe refund
                refund = stripe.Refund.create(
                    payment_intent=str(transaction.transaction_code),
                    amount=int(float(amount) * 100) if amount else None,
                    reason=reason or 'requested_by_customer'
                )
                
                # Create refund history record
                TransactionHistory.objects.create(
                    payment_profile=transaction.payment_profile,
                    transaction_token=transaction,
                    status='refunded',
                )
                
                return Response({
                    'message': 'Refund processed successfully',
                    'refund_id': refund.id,
                    'amount': refund.amount / 100
                })
            
            else:
                return Response({
                    'error': f'Refunds not yet supported for {transaction.payment_option}. '
                             f'Please contact support for manual refund processing.'
                }, status=status.HTTP_501_NOT_IMPLEMENTED)
        
        except stripe.error.InvalidRequestError as e:
            return Response(
                {'error': f'Refund failed: {e.user_message}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Refund failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# WEBHOOKS
# ============================================================================

class StripeWebhookView(APIView):
    """Handle Stripe webhooks"""
    permission_classes = []  # Public endpoint
    
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            return Response({'error': 'Invalid payload'}, status=400)
        except stripe.error.SignatureVerificationError:
            return Response({'error': 'Invalid signature'}, status=400)
        
        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            try:
                transaction = TransactionToken.objects.get(transaction_code=payment_intent['id'])
                TransactionHistory.objects.create(
                    payment_profile=transaction.payment_profile,
                    transaction_token=transaction,
                    status='completed',
                )
            except TransactionToken.DoesNotExist:
                pass
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            try:
                transaction = TransactionToken.objects.get(transaction_code=payment_intent['id'])
                TransactionHistory.objects.create(
                    payment_profile=transaction.payment_profile,
                    transaction_token=transaction,
                    status='failed',
                )
            except TransactionToken.DoesNotExist:
                pass
        
        return Response({'status': 'success'})


class PayPalWebhookView(APIView):
    """Handle PayPal webhooks"""
    permission_classes = []
    
    def post(self, request):
        event_type = request.data.get('event_type', '')
        resource = request.data.get('resource', {})
        
        if event_type == 'PAYMENT.CAPTURE.COMPLETED':
            order_id = resource.get('supplementary_data', {}).get('related_ids', {}).get('order_id')
            if order_id:
                try:
                    transaction = TransactionToken.objects.get(transaction_code=order_id)
                    TransactionHistory.objects.create(
                        payment_profile=transaction.payment_profile,
                        transaction_token=transaction,
                        status='completed',
                    )
                except TransactionToken.DoesNotExist:
                    pass
        
        return Response({'message': 'PayPal webhook received'})


class MpesaCallbackView(APIView):
    """Handle M-Pesa callback"""
    permission_classes = []
    
    def post(self, request):
        body = request.data.get('Body', {})
        callback = body.get('stkCallback', {})
        result_code = callback.get('ResultCode', -1)
        checkout_request_id = callback.get('CheckoutRequestID', '')
        
        if result_code == 0 and checkout_request_id:
            # Payment successful
            try:
                transaction = TransactionToken.objects.get(
                    description__contains=checkout_request_id
                )
                TransactionHistory.objects.create(
                    payment_profile=transaction.payment_profile,
                    transaction_token=transaction,
                    status='completed',
                )
            except TransactionToken.DoesNotExist:
                pass
        
        return Response({
            'ResultCode': 0,
            'ResultDesc': 'Success'
        })
