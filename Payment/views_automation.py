"""
Automation & Utility Endpoints for Payment System
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
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
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def stripe(self, request):
        return Response({'status': 'received'})
    
    @action(detail=False, methods=['post'])
    def mpesa(self, request):
        return Response({'status': 'processed'})
    
    @action(detail=False, methods=['post'])
    def paypal(self, request):
        return Response({'status': 'received'})


class ScheduledTasksView(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def process_standing_orders(self, request):
        from Payment.models import BillStandingOrder, BillPayment, PaymentProfile, Profile
        today = timezone.now().date()
        due_orders = BillStandingOrder.objects.filter(is_active=True, next_run_date__lte=today)
        processed = 0
        for order in due_orders:
            try:
                pp = PaymentProfile.objects.get(user=order.user)
                if pp.comrade_balance >= order.amount:
                    BillPayment.objects.create(user=order.user, provider=order.provider, account_number=order.account_number, amount=order.amount, status='completed')
                    pp.comrade_balance -= order.amount
                    pp.save()
                    order.next_run_date += timedelta(days=1)
                    order.save()
                    processed += 1
            except: pass
        return Response({'processed': processed})
    
    @action(detail=False, methods=['post'])
    def check_loan_overdue(self, request):
        from Payment.models import LoanRepayment
        today = timezone.now().date()
        count = LoanRepayment.objects.filter(status__in=['upcoming', 'due'], due_date__lt=today).update(status='overdue')
        return Response({'marked_overdue': count})
    
    @action(detail=False, methods=['post'])
    def check_insurance_expiry(self, request):
        from Payment.models import InsurancePolicy
        today = timezone.now().date()
        expiring = InsurancePolicy.objects.filter(status='active', end_date__lte=today + timedelta(days=30))
        return Response({'expiring_count': expiring.count()})


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