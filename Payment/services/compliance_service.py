"""KYC/AML bridge between Payment flows and the Compliance app.

Phase 1 integrity layer: money movement now consults the customer's
compliance posture (CDD/KYC status + risk profile) before being allowed.

Design rules (all thresholds env-tunable via comrade/settings.py):
- Withdrawals always require *cleared* KYC.
- Deposits up to DEPOSIT_UNVERIFIED_LIMIT are allowed for unverified users
  (low friction onboarding); larger deposits require cleared KYC.
- Loans require cleared KYC.
- Users with risk_level 'prohibited' are blocked from all three.
- Transactions above HIGH_RISK_TX_THRESHOLD from non-cleared or high-risk /
  PEP customers still proceed (where allowed) but raise an internal STR so
  compliance can review — POCA(ML) monitoring hook.

Enforcement is globally switchable with KYC_ENFORCEMENT for sandboxes/tests.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _enabled():
    return getattr(settings, "KYC_ENFORCEMENT", True)


def get_kyc_summary(user):
    """Aggregate compliance posture for a user (mirrors Compliance app logic).

    Returns dict: kyc_status ('not_started'|...|'cleared'), kyc_verified,
    risk_level ('unassessed'|low|medium|high|prohibited), risk_score,
    politically_exposed.
    """
    from Compliance.models import CDDRecord, CustomerRiskProfile

    latest_cdd = CDDRecord.objects.filter(customer=user).order_by("-updated_at").first()
    if latest_cdd is None:
        kyc_status = "not_started"
    elif latest_cdd.status == "cleared":
        kyc_status = "cleared"
    elif latest_cdd.status == "flagged":
        kyc_status = "flagged"
    else:
        kyc_status = latest_cdd.status

    latest_risk = (
        CustomerRiskProfile.objects.filter(customer=user).order_by("-updated_at").first()
    )

    return {
        "kyc_status": kyc_status,
        "kyc_verified": kyc_status == "cleared",
        "risk_level": latest_risk.risk_level if latest_risk else "unassessed",
        "risk_score": latest_risk.score if latest_risk else 0,
        "politically_exposed": latest_risk.politically_exposed if latest_risk else False,
    }


def check_transaction_allowed(user, kind, amount):
    """Decide whether a money movement may proceed.

    kind: 'deposit' | 'withdrawal' | 'loan'
    Returns (allowed: bool, detail: str, summary: dict).
    """
    summary = get_kyc_summary(user)

    if not _enabled():
        return True, "", summary

    # Prohibited customers: hard block everywhere.
    if summary["risk_level"] == "prohibited":
        return (
            False,
            "Your account is restricted from financial activity. Contact support.",
            summary,
        )

    if not summary["kyc_verified"]:
        if kind == "withdrawal":
            return (
                False,
                "Identity verification is required before withdrawing funds. "
                "Complete KYC in Settings > Verification.",
                summary,
            )
        if kind == "loan":
            return (
                False,
                "Identity verification is required before applying for a loan. "
                "Complete KYC in Settings > Verification.",
                summary,
            )
        # deposit: allowed below the unverified ceiling only
        limit = getattr(settings, "DEPOSIT_UNVERIFIED_LIMIT", 30000)
        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = 0
        if amount_val > float(limit):
            return (
                False,
                f"Deposits above {limit:,.0f} require identity verification. "
                "Complete KYC in Settings > Verification to raise your limits.",
                summary,
            )

    return True, "", summary


def maybe_flag_transaction(user, kind, amount, reference=""):
    """AML monitoring hook: file an STR when a transaction looks risky.

    Risky = above HIGH_RISK_TX_THRESHOLD and (KYC not cleared OR high risk OR PEP).
    Never blocks; returns the created SuspiciousTransactionReport or None.
    """
    try:
        amount_val = float(amount)
    except (TypeError, ValueError):
        return None

    threshold = float(getattr(settings, "HIGH_RISK_TX_THRESHOLD", 150000))
    if amount_val < threshold:
        return None

    summary = get_kyc_summary(user)
    risky = (
        not summary["kyc_verified"]
        or summary["risk_level"] == "high"
        or summary["politically_exposed"]
    )
    if not risky:
        return None

    from Compliance.models import SuspiciousTransactionReport

    reason = (
        f"{kind.title()} of {amount_val:,.2f} exceeds high-risk threshold "
        f"({threshold:,.0f}) with kyc_status={summary['kyc_status']}, "
        f"risk_level={summary['risk_level']}, "
        f"PEP={summary['politically_exposed']}."
    )
    report = SuspiciousTransactionReport.objects.create(
        customer=user,
        transaction_reference=reference[:255],
        amount=amount,
        currency=getattr(settings, "PLATFORM_CURRENCY", "KES"),
        suspicious_reason=reason,
        risk_level="high",
        status="pending",
    )
    logger.warning("STR filed for user %s: %s", getattr(user, "id", "?"), reason)
    return report
