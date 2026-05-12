"""
Admin Management Views for Bills, Loans, Insurance, Transactions, and Kitties
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count
from django.utils import timezone

from Payment.models import (
    BillPayment, BillProvider, LoanApplication, LoanProduct,
    InsuranceClaim, InsurancePolicy, TransactionHistory,
    PaymentGroups
)
from Payment.serializers import (
    BillPaymentSerializer, LoanApplicationSerializer,
    InsuranceClaimSerializer, TransactionHistorySerializer,
    PaymentGroupSerializer
)


class AdminBillPaymentViewSet(viewsets.ModelViewSet):
    serializer_class = BillPaymentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'post']
    
    def get_queryset(self):
        queryset = BillPayment.objects.select_related('user', 'provider').all()
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        provider_id = self.request.query_params.get('provider')
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        return queryset
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        action = request.data.get('action')
        payment_ids = request.data.get('payment_ids', [])
        if action == 'refund':
            count = sum(1 for pid in payment_ids 
                if (p := BillPayment.objects.filter(id=pid).first()) and p.status == 'completed' and (setattr(p, 'status', 'refunded') or p.save()))
            return Response({'refunded': count})
        return Response({'error': 'Invalid action'}, status=400)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        from django.db.models import Q
        total = BillPayment.objects.count()
        return Response({
            'total_transactions': total,
            'completed': BillPayment.objects.filter(status='completed').count(),
            'pending': BillPayment.objects.filter(status='pending').count(),
            'failed': BillPayment.objects.filter(status='failed').count(),
            'total_amount': str(BillPayment.objects.filter(status='completed').aggregate(t=Sum('amount'))['t'] or 0),
        })


class AdminLoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'post']
    
    def get_queryset(self):
        queryset = LoanApplication.objects.select_related('user', 'product').all()
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        action = request.data.get('action')
        application_ids = request.data.get('application_ids', [])
        count = 0
        for aid in application_ids:
            app = LoanApplication.objects.filter(id=aid).first()
            if not app:
                continue
            if action == 'approve':
                app.status = 'approved'
                app.reviewed_by = request.user
                app.reviewed_at = timezone.now()
                app.save()
                count += 1
            elif action == 'reject':
                app.status = 'rejected'
                app.reviewed_by = request.user
                app.reviewed_at = timezone.now()
                app.save()
                count += 1
            elif action == 'disburse':
                app.status = 'disbursed'
                app.disbursed_by = request.user
                app.disbursed_at = timezone.now()
                app.save()
                count += 1
        return Response({'updated': count})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        return Response({
            'total_applications': LoanApplication.objects.count(),
            'pending': LoanApplication.objects.filter(status='pending').count(),
            'approved': LoanApplication.objects.filter(status='approved').count(),
            'disbursed': LoanApplication.objects.filter(status='disbursed').count(),
        })


class AdminInsuranceClaimViewSet(viewsets.ModelViewSet):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'post']
    
    def get_queryset(self):
        return InsuranceClaim.objects.select_related('policy').all()
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        action = request.data.get('action')
        claim_ids = request.data.get('claim_ids', [])
        count = 0
        for cid in claim_ids:
            claim = InsuranceClaim.objects.filter(id=cid).first()
            if not claim:
                continue
            if action == 'approve':
                claim.status = 'approved'
                claim.reviewed_by = request.user
                claim.reviewed_at = timezone.now()
                claim.save()
                count += 1
            elif action == 'reject':
                claim.status = 'rejected'
                claim.reviewed_by = request.user
                claim.reviewed_at = timezone.now()
                claim.save()
                count += 1
        return Response({'updated': count})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        return Response({
            'total_claims': InsuranceClaim.objects.count(),
            'pending': InsuranceClaim.objects.filter(status='pending').count(),
            'approved': InsuranceClaim.objects.filter(status='approved').count(),
        })


class AdminTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionHistorySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']
    
    def get_queryset(self):
        return TransactionHistory.objects.select_related('user').all()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        return Response({
            'total_transactions': TransactionHistory.objects.count(),
            'completed': TransactionHistory.objects.filter(status='completed').count(),
        })


class AdminKittyViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentGroupSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch']
    
    def get_queryset(self):
        return PaymentGroups.objects.filter(is_kitty=True)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        return Response({
            'total_kitties': PaymentGroups.objects.filter(is_kitty=True).count(),
            'active_kitties': PaymentGroups.objects.filter(is_kitty=True, is_active=True).count(),
        })
    
    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        kitty = self.get_object()
        kitty.is_active = False
        kitty.save()
        return Response({'status': 'frozen'})
    
    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        kitty = self.get_object()
        kitty.is_active = True
        kitty.save()
        return Response({'status': 'active'})