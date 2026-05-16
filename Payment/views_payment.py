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
import hmac
import hashlib
import logging
import requests as http_requests
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

logger = logging.getLogger(__name__)

# Safaricom M-Pesa production IP ranges (for webhook IP whitelisting)
MPESA_ALLOWED_IPS = [
    '196.201.214.',   # Safaricom production
    '196.201.213.',   # Safaricom production
    '192.168.',       # Local dev / tunnel
    '127.0.0.1',      # Localhost
]


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
            provider_token = data.get('provider_token')
            if not provider_token or not provider_token.startswith('pm_'):
                return Response(
                    {'error': 'Invalid or missing provider_token. Cards must be tokenized on the frontend for PCI compliance.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if stripe.api_key:
                try:
                    # Retrieve the fully tokenized payment method from Stripe
                    pm = stripe.PaymentMethod.retrieve(provider_token)
                    card = pm.card
                    
                    saved_method.last_four = card.last4
                    saved_method.card_brand = card.brand
                    saved_method.expiry_month = card.exp_month
                    saved_method.expiry_year = card.exp_year
                    saved_method.billing_zip = pm.billing_details.address.postal_code if (pm.billing_details and pm.billing_details.address) else data.get('billing_zip', '')
                    saved_method.provider = 'stripe'
                    saved_method.provider_token = provider_token
                    saved_method.is_verified = True
                except stripe.error.StripeError as e:
                    return Response(
                        {'error': f'Card verification failed: {e.user_message}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except Exception as e:
                    logger.error(f'Error retrieving Strip PaymentMethod: {str(e)}')
                    saved_method.is_verified = False
            else:
                return Response({'error': 'Stripe is not configured on the server.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
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
        
        event_type = event.get('type', '')
        event_id = event.get('id', '')
        
        from Payment.idempotency import is_webhook_idempotent
        if not is_webhook_idempotent(event_id, prefix="stripe"):
            return Response({'status': 'ignored duplicate event'})
        
        # Support for Thin Events (Event Destinations V2) & standard Webhooks (V1)
        if 'data' in event and 'object' in event['data']:
            data_object = event['data']['object']
        else:
            # Thin Event - we must fetch the snapshot of the object
            related_object = event.get('related_object', {})
            object_id = related_object.get('id')
            
            if not object_id:
                return Response({'status': 'ignored, no related_object.id found'}, status=200)
                
            try:
                if 'payment_intent' in event_type:
                    data_object = stripe.PaymentIntent.retrieve(object_id)
                elif 'checkout.session' in event_type:
                    data_object = stripe.checkout.Session.retrieve(object_id)
                else:
                    return Response({'status': f'ignored event type {event_type}'}, status=200)
            except Exception as e:
                logger.error(f'Error retrieving Stripe snapshot: {str(e)}')
                return Response({'error': 'Failed to fetch event snapshot'}, status=500)
                
            # Normalize v2 thin event types (e.g., v1.payment_intent.succeeded -> payment_intent.succeeded)
            if event_type.startswith('v1.'):
                event_type = event_type[3:]
        
        # Handle different event types
        if event_type == 'payment_intent.succeeded':
            self._handle_payment_succeeded(data_object)
        
        elif event_type == 'payment_intent.payment_failed':
            self._handle_payment_failed(data_object)
        
        elif event_type == 'checkout.session.completed':
            self._handle_checkout_completed(data_object)
        
        elif event_type == 'payment_intent.amount_capturable_updated':
            # Escrow: funds authorized and held, ready for capture
            self._handle_escrow_authorized(data_object)
        
        return Response({'status': 'success'})
    
    def _handle_payment_succeeded(self, payment_intent):
        try:
            transaction = TransactionToken.objects.get(transaction_code=payment_intent['id'])
            TransactionHistory.objects.create(
                payment_profile=transaction.payment_profile,
                transaction_token=transaction,
                status='completed',
            )
            # Credit wallet if this is a deposit
            if transaction.transaction_type == 'deposit':
                pp = transaction.payment_profile
                pp.comrade_balance += float(transaction.amount)
                pp.save()
                logger.info(f'Stripe deposit completed: {payment_intent["id"]} — credited {transaction.amount}')
        except TransactionToken.DoesNotExist:
            logger.debug(f'Stripe webhook: no matching token for PI {payment_intent["id"]}')
    
    def _handle_payment_failed(self, payment_intent):
        try:
            transaction = TransactionToken.objects.get(transaction_code=payment_intent['id'])
            TransactionHistory.objects.create(
                payment_profile=transaction.payment_profile,
                transaction_token=transaction,
                status='failed',
            )
        except TransactionToken.DoesNotExist:
            pass
    
    def _handle_checkout_completed(self, session):
        """Handle Stripe Checkout Session completion."""
        try:
            transaction = TransactionToken.objects.get(transaction_code=session['id'])
            TransactionHistory.objects.create(
                payment_profile=transaction.payment_profile,
                transaction_token=transaction,
                status='completed',
            )
            if transaction.transaction_type == 'deposit':
                pp = transaction.payment_profile
                pp.comrade_balance += float(transaction.amount)
                pp.save()
        except TransactionToken.DoesNotExist:
            logger.debug(f'Stripe checkout session webhook: no token for {session["id"]}')
    
    def _handle_escrow_authorized(self, payment_intent):
        """Handle escrow hold authorization — funds are capturable."""
        from Payment.models import EscrowTransaction
        escrow_id = payment_intent.get('metadata', {}).get('escrow_id')
        if escrow_id:
            try:
                escrow = EscrowTransaction.objects.get(id=escrow_id)
                if escrow.status == 'initiated':
                    escrow.status = 'funded'
                    escrow.payment_intent_id = payment_intent['id']
                    from django.utils import timezone
                    escrow.funded_at = timezone.now()
                    escrow.save()
                    logger.info(f'Escrow {escrow_id} funded via Stripe hold')
            except EscrowTransaction.DoesNotExist:
                logger.warning(f'Escrow webhook: no escrow {escrow_id}')


class FlutterwaveWebhookView(APIView):
    """Handle Flutterwave payment webhook notifications.
    
    Flutterwave signs webhooks using a secret hash sent in the
    'verif-hash' header. We compare it against FLUTTERWAVE_SECRET_HASH.
    """
    permission_classes = []
    
    def post(self, request):
        # Verify signature
        signature = request.META.get('HTTP_VERIF_HASH', '')
        secret_hash = getattr(settings, 'FLUTTERWAVE_SECRET_HASH', '')
        
        if not secret_hash:
            logger.warning('FLUTTERWAVE_SECRET_HASH not configured — accepting in dev mode')
        elif signature != secret_hash:
            logger.warning(f'Flutterwave webhook signature mismatch')
            return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)
        
        event_data = request.data
        event_type = event_data.get('event', '')
        data = event_data.get('data', {})
        event_id = event_data.get('id') or data.get('id', '')
        
        from Payment.idempotency import is_webhook_idempotent
        if event_id and not is_webhook_idempotent(event_id, prefix="flw"):
            return Response({'status': 'ignored duplicate event'})
        
        if event_type == 'charge.completed' and data.get('status') == 'successful':
            tx_ref = data.get('tx_ref', '')
            amount = data.get('amount', 0)
            flw_ref = data.get('flw_ref', '')
            
            # Verify the transaction with Flutterwave
            from Payment.services.payment_service import FlutterwaveProvider
            verification = FlutterwaveProvider.verify_transaction(data.get('id'))
            
            if verification.get('status') == 'completed':
                try:
                    transaction = TransactionToken.objects.get(transaction_code=tx_ref)
                    TransactionHistory.objects.create(
                        payment_profile=transaction.payment_profile,
                        transaction_token=transaction,
                        status='completed',
                    )
                    if transaction.transaction_type == 'deposit':
                        pp = transaction.payment_profile
                        pp.comrade_balance += float(transaction.amount)
                        pp.save()
                    logger.info(f'Flutterwave payment completed: {tx_ref} (FLW: {flw_ref})')
                except TransactionToken.DoesNotExist:
                    logger.debug(f'Flutterwave webhook: no token for tx_ref {tx_ref}')
        
        return Response({'status': 'success'})


class PesapalIPNView(APIView):
    """Handle Pesapal Instant Payment Notifications (IPN).
    
    Pesapal sends a GET or POST with OrderTrackingId and 
    OrderMerchantReference when payment status changes.
    """
    permission_classes = []
    
    def get(self, request):
        """Pesapal IPN can come via GET."""
        return self._handle_ipn(request)
    
    def post(self, request):
        """Pesapal IPN can also come via POST."""
        return self._handle_ipn(request)
    
    def _handle_ipn(self, request):
        order_tracking_id = request.query_params.get('OrderTrackingId') or request.data.get('OrderTrackingId', '')
        merchant_reference = request.query_params.get('OrderMerchantReference') or request.data.get('OrderMerchantReference', '')
        
        if not order_tracking_id:
            return Response({'error': 'Missing OrderTrackingId'}, status=status.HTTP_400_BAD_REQUEST)
            
        from Payment.idempotency import is_webhook_idempotent
        if not is_webhook_idempotent(order_tracking_id, prefix="pesapal"):
            return Response({
                'orderTrackingId': order_tracking_id,
                'orderMerchantReference': merchant_reference,
                'status': 'already_processed',
            })
        
        # Verify transaction status with Pesapal API
        from Payment.services.payment_service import PesapalProvider
        status_result = PesapalProvider.get_transaction_status(order_tracking_id)
        
        if status_result.get('status') == 'completed':
            try:
                transaction = TransactionToken.objects.get(transaction_code=merchant_reference)
                # Avoid duplicate completion
                existing = TransactionHistory.objects.filter(
                    transaction_token=transaction, status='completed'
                ).exists()
                if not existing:
                    TransactionHistory.objects.create(
                        payment_profile=transaction.payment_profile,
                        transaction_token=transaction,
                        status='completed',
                    )
                    if transaction.transaction_type == 'deposit':
                        pp = transaction.payment_profile
                        pp.comrade_balance += float(transaction.amount)
                        pp.save()
                    logger.info(f'Pesapal payment completed: {merchant_reference}')
            except TransactionToken.DoesNotExist:
                logger.debug(f'Pesapal IPN: no token for ref {merchant_reference}')
        
        return Response({
            'orderTrackingId': order_tracking_id,
            'orderMerchantReference': merchant_reference,
            'status': status_result.get('status', 'unknown'),
        })


class PayPalWebhookView(APIView):
    """Handle PayPal webhooks with signature verification"""
    permission_classes = []
    
    def _verify_paypal_signature(self, request):
        """Verify PayPal webhook signature using the PayPal API."""
        webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', '')
        if not webhook_id:
            logger.warning('PAYPAL_WEBHOOK_ID not configured — skipping signature verification')
            return True  # Allow in dev when webhook ID isn't set
        
        # PayPal sends these headers for verification
        transmission_id = request.META.get('HTTP_PAYPAL_TRANSMISSION_ID', '')
        timestamp = request.META.get('HTTP_PAYPAL_TRANSMISSION_TIME', '')
        cert_url = request.META.get('HTTP_PAYPAL_CERT_URL', '')
        auth_algo = request.META.get('HTTP_PAYPAL_AUTH_ALGO', '')
        transmission_sig = request.META.get('HTTP_PAYPAL_TRANSMISSION_SIG', '')
        
        if not all([transmission_id, timestamp, cert_url, transmission_sig]):
            logger.warning('PayPal webhook missing verification headers')
            return False
        
        # Verify via PayPal's verification endpoint
        try:
            paypal_api_url = getattr(settings, 'PAYPAL_API_URL', 'https://api-m.sandbox.paypal.com')
            client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
            client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
            
            # Get access token
            auth_resp = http_requests.post(
                f'{paypal_api_url}/v1/oauth2/token',
                data={'grant_type': 'client_credentials'},
                auth=(client_id, client_secret),
                timeout=10
            )
            if auth_resp.status_code != 200:
                logger.error('PayPal auth failed during webhook verification')
                return False
            
            access_token = auth_resp.json().get('access_token')
            
            # Verify the webhook signature
            verify_resp = http_requests.post(
                f'{paypal_api_url}/v1/notifications/verify-webhook-signature',
                json={
                    'auth_algo': auth_algo,
                    'cert_url': cert_url,
                    'transmission_id': transmission_id,
                    'transmission_sig': transmission_sig,
                    'transmission_time': timestamp,
                    'webhook_id': webhook_id,
                    'webhook_event': request.data,
                },
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            
            result = verify_resp.json()
            return result.get('verification_status') == 'SUCCESS'
        except Exception as e:
            logger.error(f'PayPal webhook verification error: {e}')
            return False
    
    def post(self, request):
        # Verify signature
        if not self._verify_paypal_signature(request):
            logger.warning('PayPal webhook signature verification failed')
            return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)
        
        event_type = request.data.get('event_type', '')
        resource = request.data.get('resource', {})
        event_id = request.data.get('id', '')
        
        from Payment.idempotency import is_webhook_idempotent
        if event_id and not is_webhook_idempotent(event_id, prefix="paypal"):
            return Response({'message': 'ignored duplicate event'})
        
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
    """Handle M-Pesa callback with IP whitelist verification"""
    permission_classes = []
    
    def _verify_mpesa_source(self, request):
        """Verify the request comes from Safaricom's IP range."""
        # Get the real IP (behind reverse proxy)
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        client_ip = forwarded_for.split(',')[0].strip() if forwarded_for else request.META.get('REMOTE_ADDR', '')
        
        # In DEBUG mode, allow all IPs for sandbox testing
        if getattr(settings, 'DEBUG', False):
            return True
        
        for allowed in MPESA_ALLOWED_IPS:
            if client_ip.startswith(allowed):
                return True
        
        logger.warning(f'M-Pesa callback from unauthorized IP: {client_ip}')
        return False
    
    def post(self, request):
        # Verify source IP
        if not self._verify_mpesa_source(request):
            return Response({'ResultCode': 1, 'ResultDesc': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        
        body = request.data.get('Body', {})
        callback = body.get('stkCallback', {})
        result_code = callback.get('ResultCode', -1)
        checkout_request_id = callback.get('CheckoutRequestID', '')
        
        if result_code == 0 and checkout_request_id:
            from Payment.idempotency import is_webhook_idempotent
            if not is_webhook_idempotent(checkout_request_id, prefix="mpesa"):
                return Response({
                    'ResultCode': 0,
                    'ResultDesc': 'Success (Duplicate)'
                })
                
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
                # Credit wallet for deposits
                if transaction.transaction_type == 'deposit':
                    pp = transaction.payment_profile
                    pp.comrade_balance += float(transaction.amount)
                    pp.save()
                logger.info(f'M-Pesa payment completed: {checkout_request_id}')
            except TransactionToken.DoesNotExist:
                logger.warning(f'M-Pesa callback for unknown checkout: {checkout_request_id}')
        
        return Response({
            'ResultCode': 0,
            'ResultDesc': 'Success'
        })


# ============================================================================
# GATEWAY CONFIGURATION ENDPOINT
# ============================================================================

class GatewayConfigView(APIView):
    """Return available payment gateways and their public keys.
    
    The frontend calls this on load to know which payment buttons to show
    and to initialize Stripe Elements with the correct publishable key.
    """
    permission_classes = []  # Public — only exposes public keys
    
    def get(self, request):
        from Payment.services.payment_service import PaymentService
        gateways = PaymentService.get_available_gateways()
        return Response({
            'gateways': gateways,
            'default_gateway': getattr(settings, 'PAYMENT_DESTINATION', 'stripe'),
        })

