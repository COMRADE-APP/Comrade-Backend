"""
Automation & Utility Endpoints for Payment System
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
import requests
import logging

logger = logging.getLogger(__name__)


class CurrencyConversionView(viewsets.ViewSet):
    """Convert amounts between currencies"""
    FALLBACK_RATES = {'USD': 1.0, 'EUR': 0.85, 'GBP': 0.73, 'KES': 110.0, 'NGN': 410.0, 'ZAR': 15.0}
    
    @action(detail=False, methods=['get'])
    def convert(self, request):
        from_curr = request.query_params.get('from', 'USD').upper()
        to_curr = request.query_params.get('to', 'KES').upper()
        amount = float(request.query_params.get('amount', 0))
        rate = self.FALLBACK_RATES.get(to_curr, 1)
        return Response({'from': from_curr, 'to': to_curr, 'amount': amount, 'converted': amount * rate, 'rate': rate})


class NotificationServiceView(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def send(self, request):
        logger.info(f"Notification: {request.data.get('title')}")
        return Response({'status': 'sent', 'timestamp': timezone.now().isoformat()})


class WebhookHandlerView(viewsets.ViewSet):
    """DISABLED STUB: previously returned fake success for provider webhooks
    without any signature verification. Real, signature-verified webhook views
    live in Payment.views_payment (StripeWebhookView, MpesaCallbackView,
    PayPalWebhookView, PaystackWebhookView). Do not re-enable until this
    endpoint performs full provider-specific verification."""

    @action(detail=False, methods=['post'], url_path='stripe')
    def stripe(self, request):
        return Response({'detail': 'Deprecated stub endpoint.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=['post'], url_path='mpesa')
    def mpesa(self, request):
        return Response({'detail': 'Deprecated stub endpoint.'}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=['post'], url_path='paypal')
    def paypal(self, request):
        return Response({'detail': 'Deprecated stub endpoint.'}, status=status.HTTP_501_NOT_IMPLEMENTED)


class ScheduledTasksView(viewsets.ViewSet):
    """Manual triggers for scheduled money jobs. Admin-only: these mutate
    balances. Logic lives in Payment.tasks — do not duplicate here."""
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=['post'])
    def process_standing_orders(self, request):
        from Payment.tasks import process_standing_orders
        result = process_standing_orders.apply(args=(), kwargs={}).get()
        return Response({'result': result})

    @action(detail=False, methods=['post'])
    def check_loan_overdue(self, request):
        from Payment.tasks import check_loan_overdue
        result = check_loan_overdue.apply(args=(), kwargs={}).get()
        return Response({'result': result})

    @action(detail=False, methods=['post'])
    def check_insurance_expiry(self, request):
        from Payment.tasks import check_insurance_expiry
        result = check_insurance_expiry.apply(args=(), kwargs={}).get()
        return Response({'result': result})


class AnalyticsView(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        from Payment.models import TransactionHistory, BillPayment, LoanApplication, InsurancePolicy, PaymentGroups
        period = int(request.query_params.get('period', 30))
        start_date = timezone.now() - timedelta(days=period)
        return Response({
            'transactions': TransactionHistory.objects.filter(created_at__gte=start_date).count(),
            'bill_payments': BillPayment.objects.filter(created_at__gte=start_date).count(),
            'loans': LoanApplication.objects.filter(created_at__gte=start_date).count(),
            'insurance': InsurancePolicy.objects.filter(created_at__gte=start_date).count(),
            'kitties': PaymentGroups.objects.filter(is_kitty=True).count(),
        })


class SecurityView(viewsets.ViewSet):
    @action(detail=False, methods=['get'])
    def check_rate_limit(self, request):
        return Response({'remaining': 100})
    
    @action(detail=False, methods=['post'])
    def report_suspicious(self, request):
        return Response({'status': 'reported'})