"""Nightly ledger reconciliation for the Qomrade wallet system.

The TransactionToken/TransactionHistory schema is not a strict double-entry
ledger, so full balance reconstruction is impossible. Instead this report
detects the anomalies that matter operationally:

1. Negative wallet balances (must never happen — critical).
2. Stuck pending transactions older than PENDING_TX_STUCK_HOURS.
3. 'completed' deposit/contribution tokens with no matching TransactionHistory
   row (audit-trail gaps).
4. Wallet balance diverging from the latest known balance_after snapshot.

Report-only by design: fixing money records requires human review. The JSON
summary is logged (WARNING when anomalies exist) so alerting can key off it,
and the nightly Celery task stores the result in the cache for dashboards.
"""
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Max, Q
from django.utils import timezone

from Payment.models import PaymentProfile, TransactionHistory, TransactionToken

logger = logging.getLogger(__name__)

CACHE_KEY = "reconcile_ledger:last_report"


def run_reconciliation(stuck_hours=None, store=True):
    """Run all ledger checks; returns a JSON-serialisable summary dict."""
    now = timezone.now()
    if stuck_hours is None:
        from django.conf import settings as dj_settings
        stuck_hours = int(getattr(dj_settings, "PENDING_TX_STUCK_HOURS", 24))
    stuck_cutoff = now - timedelta(hours=stuck_hours)

    # 1. Negative balances — critical integrity violation
    negative = list(
        PaymentProfile.objects.filter(comrade_balance__lt=0)
        .values_list("id", "comrade_balance")[:50]
    )

    # 2. Stuck pending transactions
    stuck = list(
        TransactionToken.objects.filter(status="pending", created_at__lt=stuck_cutoff)
        .order_by("created_at")
        .values("transaction_code", "transaction_type", "amount", "created_at")[:100]
    )
    stuck_count = TransactionToken.objects.filter(
        status="pending", created_at__lt=stuck_cutoff
    ).count()

    # 3. Completed money tokens missing their history row
    history_tokens = set(
        TransactionHistory.objects.values_list("transaction_token_id", flat=True)
    )
    completed_tokens = list(
        TransactionToken.objects.filter(
            status="completed",
            transaction_type__in=["deposit", "withdrawal", "contribution"],
        )
        .exclude(pk__in=history_tokens)
        .order_by("-created_at")
        .values("transaction_code", "transaction_type", "amount", "created_at")[:100]
    )
    missing_history_count = TransactionToken.objects.filter(
        status="completed",
        transaction_type__in=["deposit", "withdrawal", "contribution"],
    ).exclude(pk__in=history_tokens).count()

    # 4. Balance vs latest recorded balance_after divergence
    divergent = []
    latest = (
        TransactionHistory.objects.values("payment_profile_id")
        .annotate(latest_id=Max("id"))
        .values_list("latest_id", flat=True)
    )
    for hist in TransactionHistory.objects.filter(
        id__in=latest, balance_after__isnull=False
    ).select_related("payment_profile"):
        profile = hist.payment_profile
        if profile.comrade_balance != hist.balance_after:
            divergent.append(
                {
                    "profile": str(profile.id),
                    "wallet_balance": str(profile.comrade_balance),
                    "last_recorded": str(hist.balance_after),
                    "delta": str(profile.comrade_balance - hist.balance_after),
                }
            )
        if len(divergent) >= 50:
            break

    summary = {
        "ran_at": now.isoformat(),
        "negative_balances": {
            "count": len(negative),
            "items": [
                {"profile": str(pid), "balance": str(bal)} for pid, bal in negative
            ],
        },
        "stuck_pending_transactions": {"count": stuck_count, "items": stuck},
        "completed_without_history": {
            "count": missing_history_count,
            "items": completed_tokens,
        },
        "balance_divergence": {"count_checked": len(divergent), "items": divergent},
        "healthy": not (negative or stuck_count or missing_history_count or divergent),
    }

    level = logger.warning if not summary["healthy"] else logger.info
    level(
        "Ledger reconciliation: negative=%s stuck=%s no_history=%s divergence=%s",
        len(negative), stuck_count, missing_history_count, len(divergent),
    )

    if store:
        cache.set(CACHE_KEY, summary, timeout=48 * 3600)
    return summary
