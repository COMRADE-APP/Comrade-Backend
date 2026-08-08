"""Serializers for the Compliance app (self-service + staff views)."""
from rest_framework import serializers

from Compliance.models import (
    CDDRecord,
    ComplianceRecord,
    CustomerRiskProfile,
    EDDRecord,
    SafeguardingAccount,
    SuspiciousTransactionReport,
)


class CDDRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CDDRecord
        fields = [
            'id', 'customer_type', 'full_name', 'date_of_birth',
            'national_id', 'passport_number', 'phone_number', 'email',
            'address', 'status', 'identification_verified',
            'address_verified', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'identification_verified',
            'address_verified', 'created_at', 'updated_at',
        ]


class CustomerRiskProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRiskProfile
        fields = [
            'id', 'customer_type', 'risk_level', 'score', 'reason',
            'source_of_funds', 'occupation', 'country_of_residence',
            'politically_exposed', 'reviewed_at', 'updated_at',
        ]
        read_only_fields = fields


class SafeguardingAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafeguardingAccount
        fields = [
            'id', 'account_name', 'account_number', 'provider',
            'funds_pooled', 'ring_fenced', 'fully_backed', 'balance',
            'reconciled_at', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class EDDRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EDDRecord
        fields = [
            'id', 'reason_for_edd', 'source_of_funds_documented',
            'source_of_wealth_documented', 'senior_approval_obtained',
            'status', 'approved_at', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class SuspiciousTransactionReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuspiciousTransactionReport
        fields = [
            'id', 'transaction_reference', 'amount', 'currency',
            'suspicious_reason', 'risk_level', 'status', 'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ComplianceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceRecord
        fields = [
            'id', 'record_type', 'reference', 'retention_until',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ComplianceStatusSerializer(serializers.Serializer):
    """Aggregated compliance posture for the authenticated user."""

    kyc_status = serializers.CharField()
    kyc_verification_required = serializers.BooleanField()
    risk_level = serializers.CharField()
    risk_score = serializers.IntegerField()
    politically_exposed = serializers.BooleanField()
    safeguarding_accounts = SafeguardingAccountSerializer(many=True, read_only=True)
    cdd_records = CDDRecordSerializer(many=True, read_only=True)
    message = serializers.CharField(required=False, allow_blank=True)
