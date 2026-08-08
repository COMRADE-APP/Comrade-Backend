"""Views for the Compliance app.

Exposes:
  GET  /api/v1/compliance/status/   -> aggregated compliance posture
  GET/POST /api/v1/compliance/cdd/  -> self-service KYC (CDD) submission
  GET/PATCH /api/v1/compliance/cdd/<id>/ -> view or resubmit a record
"""
from rest_framework import serializers, status, viewsets
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

#: Statuses that mean a submission is still "live" (no new submission allowed).
_ACTIVE_SUBMISSION_STATUSES = ('pending', 'in_progress', 'cleared')

#: Statuses a user may resubmit (a new/reviewed attempt is triggered).
_RESUBMITTABLE_STATUSES = ('flagged', 'rejected')


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
    """Self-service KYC submission.

    Users only ever see/own their own records. A new submission is only
    allowed when there is no live (pending/in_progress/cleared) record;
    resubmission happens by updating a flagged/rejected record, which
    moves it back to `pending` for review.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CDDRecordSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = CDDRecord.objects.filter(customer=self.request.user)
        requested_status = self.request.query_params.get('status')
        if requested_status:
            qs = qs.filter(status=requested_status)
        return qs

    def validate_documents(self, data):
        """Require at least one government ID document."""
        national_id = data.get('national_id')
        passport = data.get('passport_number')
        if not national_id and not passport:
            raise serializers.ValidationError(
                {'national_id': 'Provide a national ID or passport number.'}
            )
        return data

    def perform_create(self, serializer):
        user = self.request.user
        has_live = CDDRecord.objects.filter(
            customer=user,
            status__in=_ACTIVE_SUBMISSION_STATUSES,
        ).exists()
        if has_live:
            raise serializers.ValidationError(
                {'detail': 'You already have a verification in progress or completed.'}
            )
        self.validate_documents(serializer.validated_data)
        serializer.save(customer=user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.status not in _RESUBMITTABLE_STATUSES:
            raise serializers.ValidationError(
                {'detail': 'This submission is not open for re-submission.'}
            )
        self.validate_documents(serializer.validated_data)
        serializer.save(status='pending')
