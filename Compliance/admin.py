"""
Admin configuration for Compliance app
"""
from django.contrib import admin
from Compliance.models import (
    CustomerRiskProfile,
    CDDRecord,
    EDDRecord,
    SafeguardingAccount,
    SuspiciousTransactionReport,
    ComplianceRecord,
)


@admin.register(CustomerRiskProfile)
class CustomerRiskProfileAdmin(admin.ModelAdmin):
    list_display = ['customer', 'customer_type', 'risk_level', 'score', 'politically_exposed', 'reviewed_at']
    list_filter = ['customer_type', 'risk_level', 'politically_exposed']
    search_fields = ['customer__email', 'customer__first_name', 'customer__last_name', 'organisation', 'institution']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(CDDRecord)
class CDDRecordAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'customer_type', 'status', 'identification_verified', 'verified_at']
    list_filter = ['status', 'customer_type', 'identification_verified', 'address_verified']
    search_fields = ['full_name', 'national_id', 'passport_number', 'email', 'phone_number']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(EDDRecord)
class EDDRecordAdmin(admin.ModelAdmin):
    list_display = ['cdd_record', 'reason_for_edd', 'status', 'senior_approval_obtained', 'approved_at']
    list_filter = ['status', 'senior_approval_obtained']
    search_fields = ['reason_for_edd', 'cdd_record__full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(SafeguardingAccount)
class SafeguardingAccountAdmin(admin.ModelAdmin):
    list_display = ['account_name', 'customer', 'provider', 'ring_fenced', 'fully_backed', 'balance', 'reconciled_at']
    list_filter = ['ring_fenced', 'fully_backed', 'funds_pooled']
    search_fields = ['account_name', 'account_number', 'provider', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(SuspiciousTransactionReport)
class SuspiciousTransactionReportAdmin(admin.ModelAdmin):
    list_display = ['transaction_reference', 'customer', 'amount', 'currency', 'risk_level', 'status', 'filed_with_regulator', 'created_at']
    list_filter = ['status', 'risk_level', 'filed_with_regulator']
    search_fields = ['transaction_reference', 'customer__email', 'customer__first_name', 'customer__last_name', 'suspicious_reason']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ComplianceRecord)
class ComplianceRecordAdmin(admin.ModelAdmin):
    list_display = ['record_type', 'reference', 'customer', 'retention_until', 'created_at']
    list_filter = ['record_type']
    search_fields = ['record_type', 'reference', 'customer__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
