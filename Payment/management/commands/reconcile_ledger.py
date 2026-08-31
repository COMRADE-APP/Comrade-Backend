"""Run the ledger reconciliation report (see Payment/reconcile.py)."""
from django.core.management.base import BaseCommand

from Payment.reconcile import run_reconciliation


class Command(BaseCommand):
    help = "Reconcile wallet ledger: negative balances, stuck pendings, missing history, divergence."

    def add_arguments(self, parser):
        parser.add_argument(
            "--stuck-hours",
            type=int,
            default=None,
            help="Pending transactions older than this many hours are flagged (default: settings.PENDING_TX_STUCK_HOURS or 24).",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print the full JSON report to stdout.",
        )

    def handle(self, *args, **options):
        import json

        summary = run_reconciliation(stuck_hours=options["stuck_hours"])
        if options["json"]:
            self.stdout.write(json.dumps(summary, indent=2, default=str))
        if summary["healthy"]:
            self.stdout.write(self.style.SUCCESS("Ledger healthy — no anomalies detected."))
        else:
            self.stdout.write(self.style.WARNING("Ledger anomalies detected — see log / --json output."))