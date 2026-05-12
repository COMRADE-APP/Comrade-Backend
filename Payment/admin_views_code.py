# Admin ViewSets for Payment Management

class AdminBillPaymentViewSet(ModelViewSet):
    serializer_class = BillPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BillPayment.objects.all().order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method in ['GET', 'POST']:
            return [IsAdminUser()]
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
    serializer_class = KittySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Kitty.objects.all().order_by('-created_at')
    
    def get_permissions(self):
        if self.request.method in ['GET', 'POST', 'PATCH']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total = Kitty.objects.count()
        active = Kitty.objects.filter(is_active=True).count()
        frozen = Kitty.objects.filter(is_frozen=True).count()
        
        total_amount = Kitty.objects.aggregate(total=Sum('current_amount'))['total'] or 0
        total_target = Kitty.objects.aggregate(total=Sum('target_amount'))['total'] or 0
        
        return Response({
            'total': total,
            'active': active,
            'frozen': frozen,
            'total_amount': str(total_amount),
            'total_target': str(total_target),
        })
    
    @action(detail=True, methods=['post'])
    def freeze(self, request, pk=None):
        kitty = self.get_object()
        kitty.is_frozen = True
        kitty.save()
        return Response({'status': 'frozen', 'kitty_id': str(kitty.id)})
    
    @action(detail=True, methods=['post'])
    def unfreeze(self, request, pk=None):
        kitty = self.get_object()
        kitty.is_frozen = False
        kitty.save()
        return Response({'status': 'unfrozen', 'kitty_id': str(kitty.id)})