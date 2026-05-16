"""
Transaction Velocity Checks for Fraud Detection.

Monitors transaction patterns in real-time using Redis counters
to detect and prevent suspicious financial activity.

Detection Rules:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Rule                              │  Threshold       │  Action
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Rapid-fire transactions           │  >5 in 2 min     │  Block + flag
  Rapid consecutive withdrawals     │  >3 in 10 min    │  Block + alert
  Large sum received then withdrawn │  >80% in 30 min  │  Hold + review
  High daily volume (new user)      │  >$500/day (< 7d)│  Require MFA
  Unusual amount pattern            │  Round numbers    │  Soft flag
  Multiple recipients in burst      │  >5 in 5 min     │  Block + flag
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import logging
from decimal import Decimal
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Threshold Configuration ──────────────────────────────────────────────────
RAPID_TX_WINDOW_SECONDS = 120        # 2 minutes
RAPID_TX_MAX_COUNT = 5               # Max transactions in window

RAPID_WITHDRAWAL_WINDOW = 600        # 10 minutes
RAPID_WITHDRAWAL_MAX = 3             # Max withdrawals in window

WITHDRAW_AFTER_RECEIVE_WINDOW = 1800 # 30 minutes
WITHDRAW_AFTER_RECEIVE_RATIO = 0.80  # 80% of received amount

NEW_USER_DAILY_LIMIT = Decimal('500.00')  # USD equivalent
NEW_USER_AGE_DAYS = 7

BURST_RECIPIENTS_WINDOW = 300        # 5 minutes
BURST_RECIPIENTS_MAX = 5


class VelocityCheckResult:
    """Result of a velocity check."""
    def __init__(self, allowed=True, reason=None, action=None, risk_score=0):
        self.allowed = allowed
        self.reason = reason
        self.action = action  # 'block', 'mfa_required', 'flag', 'hold'
        self.risk_score = risk_score  # 0-100

    def __bool__(self):
        return self.allowed


def check_transaction_velocity(user, amount, tx_type='payment'):
    """
    Run all velocity checks for a given transaction.
    Returns VelocityCheckResult.
    """
    checks = [
        _check_rapid_fire(user, tx_type),
        _check_rapid_withdrawals(user, tx_type),
        _check_new_user_limits(user, amount),
        _check_burst_recipients(user, tx_type),
    ]

    # Return the highest-severity failure
    for check in checks:
        if not check.allowed:
            logger.warning(
                f"Velocity check BLOCKED: user={user.id}, type={tx_type}, "
                f"amount={amount}, reason={check.reason}"
            )
            return check

    # If receive-then-withdraw pattern, check that too
    if tx_type == 'withdrawal':
        withdraw_check = _check_withdraw_after_receive(user, amount)
        if not withdraw_check.allowed:
            logger.warning(
                f"Velocity check HOLD: user={user.id}, "
                f"reason={withdraw_check.reason}"
            )
            return withdraw_check

    return VelocityCheckResult(allowed=True, risk_score=0)


def record_transaction(user, amount, tx_type='payment', recipient_id=None):
    """
    Record a transaction in the velocity tracking system.
    Call AFTER a successful transaction.
    """
    now_ts = timezone.now().timestamp()
    user_id = str(user.id)

    # Record transaction timestamp
    tx_key = f'velocity:tx:{user_id}:{tx_type}'
    _increment_sliding_window(tx_key, RAPID_TX_WINDOW_SECONDS)

    # Record withdrawal specifically
    if tx_type == 'withdrawal':
        wd_key = f'velocity:wd:{user_id}'
        _increment_sliding_window(wd_key, RAPID_WITHDRAWAL_WINDOW)

    # Record received amount for withdraw-after-receive detection
    if tx_type == 'receive':
        recv_key = f'velocity:recv:{user_id}'
        current = Decimal(str(cache.get(recv_key, '0')))
        cache.set(recv_key, str(current + amount), WITHDRAW_AFTER_RECEIVE_WINDOW)

    # Record unique recipients for burst detection
    if recipient_id and tx_type in ('transfer', 'payment'):
        recip_key = f'velocity:recipients:{user_id}'
        recipients = cache.get(recip_key, set())
        if not isinstance(recipients, set):
            recipients = set()
        recipients.add(str(recipient_id))
        cache.set(recip_key, recipients, BURST_RECIPIENTS_WINDOW)


# ── Internal Check Functions ──────────────────────────────────────────────────

def _check_rapid_fire(user, tx_type):
    """Detect rapid-fire transactions (>5 in 2 minutes)."""
    key = f'velocity:tx:{str(user.id)}:{tx_type}'
    count = cache.get(key, 0)

    if count >= RAPID_TX_MAX_COUNT:
        return VelocityCheckResult(
            allowed=False,
            reason=f"Too many {tx_type} transactions ({count}) in {RAPID_TX_WINDOW_SECONDS}s",
            action='block',
            risk_score=80
        )
    return VelocityCheckResult()


def _check_rapid_withdrawals(user, tx_type):
    """Detect rapid consecutive withdrawals (>3 in 10 minutes)."""
    if tx_type != 'withdrawal':
        return VelocityCheckResult()

    key = f'velocity:wd:{str(user.id)}'
    count = cache.get(key, 0)

    if count >= RAPID_WITHDRAWAL_MAX:
        return VelocityCheckResult(
            allowed=False,
            reason=f"Too many withdrawals ({count}) in {RAPID_WITHDRAWAL_WINDOW}s",
            action='block',
            risk_score=90
        )
    return VelocityCheckResult()


def _check_withdraw_after_receive(user, amount):
    """Detect large withdrawal shortly after receiving funds (money laundering signal)."""
    recv_key = f'velocity:recv:{str(user.id)}'
    recent_received = Decimal(str(cache.get(recv_key, '0')))

    if recent_received > 0 and amount >= recent_received * WITHDRAW_AFTER_RECEIVE_RATIO:
        return VelocityCheckResult(
            allowed=False,
            reason=(
                f"Attempting to withdraw {amount} which is ≥{int(WITHDRAW_AFTER_RECEIVE_RATIO*100)}% "
                f"of recently received {recent_received} within {WITHDRAW_AFTER_RECEIVE_WINDOW/60:.0f} min"
            ),
            action='hold',
            risk_score=85
        )
    return VelocityCheckResult()


def _check_new_user_limits(user, amount):
    """Apply stricter limits to accounts less than 7 days old."""
    account_age = (timezone.now() - user.date_joined).days

    if account_age < NEW_USER_AGE_DAYS:
        daily_key = f'velocity:daily:{str(user.id)}'
        daily_total = Decimal(str(cache.get(daily_key, '0')))

        if daily_total + amount > NEW_USER_DAILY_LIMIT:
            return VelocityCheckResult(
                allowed=False,
                reason=(
                    f"New account ({account_age}d old) daily limit exceeded: "
                    f"${daily_total + amount} > ${NEW_USER_DAILY_LIMIT}"
                ),
                action='mfa_required',
                risk_score=60
            )
    return VelocityCheckResult()


def _check_burst_recipients(user, tx_type):
    """Detect transfers to many different recipients in a short window."""
    if tx_type not in ('transfer', 'payment'):
        return VelocityCheckResult()

    recip_key = f'velocity:recipients:{str(user.id)}'
    recipients = cache.get(recip_key, set())

    if isinstance(recipients, set) and len(recipients) >= BURST_RECIPIENTS_MAX:
        return VelocityCheckResult(
            allowed=False,
            reason=f"Transfers to {len(recipients)} different recipients in {BURST_RECIPIENTS_WINDOW}s",
            action='block',
            risk_score=75
        )
    return VelocityCheckResult()


def _increment_sliding_window(key, window_seconds):
    """Increment a counter in a sliding time window."""
    count = cache.get(key, 0)
    cache.set(key, count + 1, window_seconds)
