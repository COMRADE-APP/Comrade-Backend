from django.contrib import admin
from Payment.models import (
    PaymentProfile, PaymentItem, PaymentLog, PaymentGroups,
    TransactionToken, PaymentAuthorization, PaymentVerification,
    TransactionHistory, TransactionTracker, PaymentGroupMember,
    Contribution, StandingOrder, GroupInvitation, GroupTarget,
    Product, UserSubscription, IndividualShare, Partner, PartnerApplication,
    # Bills & Airtime
    BillProvider, BillPayment, BillStandingOrder,
    # Loans & Credit
    LoanProduct, LoanApplication, LoanRepayment,
    # Insurance
    InsuranceProduct, InsurancePolicy, InsuranceClaim
)

admin.site.register(PaymentProfile)
admin.site.register(PaymentItem)
admin.site.register(PaymentLog)
admin.site.register(PaymentGroups)
admin.site.register(TransactionToken)
admin.site.register(PaymentAuthorization)
admin.site.register(PaymentVerification)
admin.site.register(TransactionHistory)
admin.site.register(TransactionTracker)
admin.site.register(PaymentGroupMember)
admin.site.register(Contribution)
admin.site.register(StandingOrder)
admin.site.register(GroupInvitation)
admin.site.register(GroupTarget)
admin.site.register(Product)
admin.site.register(UserSubscription)
admin.site.register(IndividualShare)


# ============== BILLS & AIRTIME ==============

@admin.register(BillProvider)
class BillProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'commission_rate', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'account_label']
    readonly_fields = ['created_at']


@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'provider', 'amount', 'status', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['reference', 'account_number', 'user__user__email']
    readonly_fields = ['reference', 'commission', 'total_amount', 'created_at', 'completed_at']
    date_hierarchy = 'created_at'


@admin.register(BillStandingOrder)
class BillStandingOrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'amount', 'frequency', 'is_active', 'next_run_date']
    list_filter = ['is_active', 'frequency', 'provider']
    search_fields = ['user__user__email', 'provider__name']


# ============== LOANS & CREDIT ==============

@admin.register(LoanProduct)
class LoanProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'loan_type', 'min_amount', 'max_amount', 'interest_rate', 'is_active']
    list_filter = ['loan_type', 'is_active', 'provider']
    search_fields = ['name', 'provider__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'product', 'amount', 'status', 'created_at']
    list_filter = ['status', 'product', 'created_at']
    search_fields = ['reference', 'user__user__email', 'product__name']
    readonly_fields = ['reference', 'credit_score', 'risk_level', 'created_at', 'reviewed_at', 'disbursed_at']
    date_hierarchy = 'created_at'
    actions = ['approve_applications', 'reject_applications', 'disburse_applications']
    
    def approve_applications(self, request, queryset):
        queryset.update(status='approved', reviewed_by=request.user)
    approve_applications.short_description = 'Approve selected applications'
    
    def reject_applications(self, request, queryset):
        queryset.update(status='rejected', reviewed_by=request.user)
    reject_applications.short_description = 'Reject selected applications'
    
    def disburse_applications(self, request, queryset):
        queryset.update(status='disbursed', disbursed_by=request.user)
    disburse_applications.short_description = 'Disburse selected applications'


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ['loan', 'amount', 'due_date', 'status', 'paid_at']
    list_filter = ['status', 'due_date']
    search_fields = ['loan__reference', 'loan__user__user__email']
    readonly_fields = ['created_at', 'paid_at']
    date_hierarchy = 'due_date'


# ============== INSURANCE ==============

@admin.register(InsuranceProduct)
class InsuranceProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'insurance_type', 'premium_min', 'premium_max', 'is_active']
    list_filter = ['insurance_type', 'is_active', 'provider']
    search_fields = ['name', 'provider__name']
    readonly_fields = ['created_at']


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_number', 'user', 'product', 'premium', 'status', 'start_date', 'end_date']
    list_filter = ['status', 'product', 'start_date']
    search_fields = ['policy_number', 'user__user__email', 'product__name']
    readonly_fields = ['policy_number', 'created_at', 'activated_at', 'cancelled_at']
    date_hierarchy = 'start_date'


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'policy', 'claimed_amount', 'approved_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['claim_number', 'policy__policy_number', 'policy__user__user__email']
    readonly_fields = ['claim_number', 'created_at', 'reviewed_at', 'processed_at']
    date_hierarchy = 'created_at'
    actions = ['approve_claims', 'reject_claims']
    
    def approve_claims(self, request, queryset):
        queryset.update(status='approved', reviewed_by=request.user)
    approve_claims.short_description = 'Approve selected claims'
    
    def reject_claims(self, request, queryset):
        queryset.update(status='rejected', reviewed_by=request.user)
    reject_claims.short_description = 'Reject selected claims'


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'partner_type', 'status', 'verified', 'commission_rate', 'created_at']
    list_filter = ['partner_type', 'status', 'verified']
    search_fields = ['business_name', 'contact_email', 'user__user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'partner_type', 'status', 'applicant', 'created_at']
    list_filter = ['partner_type', 'status']
    search_fields = ['business_name', 'contact_email', 'applicant__user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
