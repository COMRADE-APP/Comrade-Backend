"""
Payment Processing Views
Handles payment methods, processing, refunds, and webhooks for multiple providers
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
import stripe
import json
from Payment.models import TransactionToken, TransactionHistory, PaymentProfile, PaymentLog
from Payment.serializers import TransactionTokenSerializer, TransactionHistorySerializer
from Payment.services.payment_service import PaymentService
from Payment.utils import get_or_create_payment_profile
from datetime import datetime


# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


class PaymentMethodViewSet(ModelViewSet):
    """Manage saved payment methods"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # TODO: Create PaymentMethod model
        # return PaymentMethod.objects.filter(user=self.request.user)
        return []
    
    def create(self, request):
        """Add new payment method"""
        # TODO: Implement payment method creation
        # Stripe: create payment method, attach to customer
        # M-Pesa: save phone number
        # PayPal: OAuth flow
        return Response({
            'message': 'Payment method creation not yet implemented'
        }, status=status.HTTP_501_NOT_IMPLEMENTED)


class ProcessPaymentView(APIView):
    """Process a payment transaction"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'USD')
        payment_method = request.data.get('payment_method')  # stripe, paypal, mpesa
        payment_method_id = request.data.get('payment_method_id')
        description = request.data.get('description', '')
        
        if not amount or not payment_method:
            return Response(
                {'error': 'Amount and payment method are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Prepare details for service
            details = {
                'description': description,
                'payment_method_id': payment_method_id
            }
            
            # Call Payment Service
            response = PaymentService.process_payment(amount, currency, payment_method, details)
            
            if "error" in response:
                return Response({'error': response['error']}, status=status.HTTP_400_BAD_REQUEST)
                
            # Ensure payment profile exists
            payment_profile = get_or_create_payment_profile(request.user)
            
            # Create transaction token record (Generalized)
            transaction_token = TransactionToken.objects.create(
                payment_profile=payment_profile,
                transaction_code=response.get('id', f'txn_{datetime.now().timestamp()}'),
                amount=amount,
                transaction_type='payment',
                notes=description
            )
            
            # Create transaction history
            # Status depends on provider response
            txn_status = 'completed' if response.get('status') == 'succeeded' else 'pending'
            
            TransactionHistory.objects.create(
                transaction_token=transaction_token,
                status=txn_status,
                timestamp=datetime.now()
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
            if transaction.transaction_type == 'stripe' or transaction.notes.startswith('Stripe'):
                # Process Stripe refund
                refund = stripe.Refund.create(
                    payment_intent=transaction.transaction_code,
                    amount=int(float(amount) * 100) if amount else None,
                    reason=reason or 'requested_by_customer'
                )
                
                # Create refund history record
                TransactionHistory.objects.create(
                    transaction_token=transaction,
                    status='refunded',
                    timestamp=datetime.now()
                )
                
                return Response({
                    'message': 'Refund processed successfully',
                    'refund_id': refund.id,
                    'amount': refund.amount / 100
                })
            
            else:
                return Response({
                    'error': f'Refunds not supported for {transaction.payment_method}'
                }, status=status.HTTP_501_NOT_IMPLEMENTED)
        
        except Exception as e:
            return Response(
                {'error': f'Refund failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            # Update transaction status
            try:
                transaction = TransactionToken.objects.get(transaction_code=payment_intent['id'])
                TransactionHistory.objects.create(
                    transaction_token=transaction,
                    status='completed',
                    timestamp=datetime.now()
                )
            except TransactionToken.DoesNotExist:
                pass
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            try:
                transaction = TransactionToken.objects.get(transaction_code=payment_intent['id'])
                TransactionHistory.objects.create(
                    transaction_token=transaction,
                    status='failed',
                    timestamp=datetime.now()
                )
            except TransactionToken.DoesNotExist:
                pass
        
        return Response({'status': 'success'})


class PayPalWebhookView(APIView):
    """Handle PayPal webhooks"""
    permission_classes = []
    
    def post(self, request):
        # TODO: Implement PayPal webhook verification and processing
        return Response({
            'message': 'PayPal webhook received'
        })


class MpesaCallbackView(APIView):
    """Handle M-Pesa callback"""
    permission_classes = []
    
    def post(self, request):
        # TODO: Implement M-Pesa callback processing
        # Handle STK Push callback
        # Update transaction status
        return Response({
            'ResultCode': 0,
            'ResultDesc': 'Success'
        })
