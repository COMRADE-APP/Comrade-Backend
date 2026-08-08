"""Views for the Compliance app.

Exposes:
  GET  /api/v1/compliance/status/   -> aggregated compliance posture
  GET/POST /api/v1/compliance/cdd/  -> self-service KYC (CDD) submission
"""
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Compliance.models import CDDRecord, CustomerRiskProfile, SafeguardingAccount
from Compliance.serializers import (
    CDDRecordSerializer,
    ComplianceStatusSerializer,
    CustomerRiskProfileSerializer,
    SafeguardingAccountSerializer,
)


class ComplianceStatusView(APIView):
    """Return the authenticated user's aggregate compliance posture."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        cdd_records = CDDRecord.objects.filter(customer=user).order_by('-updated_at')
        latest_cdd = cdd_records.first()
        risk_profiles = CustomerRiskProfile.objects.filter(customer=user)
        latest_risk = risk_profiles.order_by('-updated_at').first()
        safeguarding = SafeguardingAccount.objects.filter(customer=user)

        if latest_cdd is None:
            kyc_status = 'not_started'
            kyc_verification_required = True
            message = 'Complete identity verification (KYC) to unlock full platform features.'
        elif latest_cdd.status == 'cleared':
            kyc_status = 'cleared'
            kyc_verification_required = False
            message = 'Identity verified. Full platform features are unlocked.'
        elif latest_cdd.status == 'flagged':
            kyc_status = 'flagged'
            kyc_verification_required = True
            message = 'Additional information is required to complete verification.'
        else:
            kyc_status = latest_cdd.status
            kyc_verification_required = True
            message = 'Your verification is under review.'

        data = {
            'kyc_status': kyc_status,
            'kyc_verification_required': kyc_verification_required,
            'risk_level': latest_risk.risk_level if latest_risk else 'unassessed',
            'risk_score': latest_risk.score if latest_risk else 0,
            'politically_exposed': latest_risk.politically_exposed if latest_risk else False,
            'safeguarding_accounts': SafeguardingAccountSerializer(safeguarding, many=True).data,
            'cdd_records': CDDRecordSerializer(cdd_records, many=True).data,
            'message': message,
        }
        serializer = ComplianceStatusSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class CDDRecordViewSet(viewsets.ModelViewSet):
    """Self-service KYC submission. Users may only see/own their own records."""

    permission_classes = [IsAuthenticated]
    serializer_class = CDDRecordSerializer

    def get_queryset(self):
        return CDDRecord.objects.filter(customer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)
