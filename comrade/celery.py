"""
Celery configuration for comrade project.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')

app = Celery('comrade')

# Use Django settings for Celery config, prefixed with CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# ============================================================================
# CELERY BEAT SCHEDULE — All automated financial cron jobs
# ============================================================================

app.conf.beat_schedule = {
    # ── Daily Tasks ──────────────────────────────────────────────────────
    'expire-group-invitations': {
        'task': 'Payment.tasks.expire_group_invitations',
        'schedule': crontab(hour=0, minute=30),   # Daily 00:30
    },
    'accrue-piggy-bank-interest': {
        'task': 'Payment.tasks.accrue_piggy_bank_interest',
        'schedule': crontab(hour=1, minute=0),     # Daily 01:00
    },
    'process-standing-orders': {
        'task': 'Payment.tasks.process_standing_orders',
        'schedule': crontab(hour=6, minute=0),     # Daily 06:00
    },
    'check-loan-overdue': {
        'task': 'Payment.tasks.check_loan_overdue',
        'schedule': crontab(hour=7, minute=0),     # Daily 07:00
    },
    'check-insurance-expiry': {
        'task': 'Payment.tasks.check_insurance_expiry',
        'schedule': crontab(hour=7, minute=30),    # Daily 07:30
    },
    'send-round-contribution-reminders': {
        'task': 'Payment.tasks.send_round_contribution_reminders',
        'schedule': crontab(hour=8, minute=0),     # Daily 08:00
    },
    'apply-late-penalties': {
        'task': 'Payment.tasks.apply_late_penalties',
        'schedule': crontab(hour=9, minute=0),     # Daily 09:00
    },
    'check-dispute-timeouts': {
        'task': 'Payment.tasks.check_dispute_timeouts',
        'schedule': crontab(hour=10, minute=0),    # Daily 10:00
    },
    'reconcile-ledger-nightly': {
        'task': 'Payment.tasks.reconcile_ledger_nightly',
        'schedule': crontab(hour=2, minute=0),     # Daily 02:00
    },

    # ── Weekly Tasks ─────────────────────────────────────────────────────
    'recompute-credit-scores': {
        'task': 'Payment.tasks.recompute_credit_scores',
        'schedule': crontab(hour=2, minute=0, day_of_week='sunday'),  # Sunday 02:00
    },

    # ── Research Tasks ───────────────────────────────────────────────────
    'run-periodic-matching': {
        'task': 'Research.tasks.run_periodic_matching',
        'schedule': crontab(hour=3, minute=0),     # Daily 03:00
    },
    'notify-matched-participants': {
        'task': 'Research.tasks.notify_matched_participants',
        'schedule': crontab(hour=9, minute=30),    # Daily 09:30
    },
    'remind-unpaid-compensation': {
        'task': 'Research.tasks.remind_unpaid_compensation',
        'schedule': crontab(hour=10, minute=0, day_of_week='monday'),  # Monday 10:00
    },

    # ── Platform Heartbeat ───────────────────────────────────────────────
    'process-group-automations': {
        'task': 'Payment.tasks.process_group_automations',
        'schedule': crontab(minute='*/5'),         # Every 5 minutes
    },
    'system-heartbeat': {
        'task': 'comrade.tasks.system_heartbeat',
        'schedule': crontab(minute='*/5'),         # Every 5 minutes
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
