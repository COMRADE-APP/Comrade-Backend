"""
Backfill PiggyBankTransaction records for ALL piggy banks.

Scans every GroupTarget and creates missing PiggyBankTransaction entries
from existing TransactionToken records. Safe to run repeatedly — skips
records already imported.

Run with: python manage.py backfill_all_piggy_analytics
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Backfill PiggyBankTransaction for all piggy banks from TransactionToken records'

    def handle(self, *args, **options):
        from Payment.models import GroupTarget, PiggyBankTransaction, PiggyBankActionRequest

        piggy_banks = GroupTarget.objects.all()
        total = piggy_banks.count()
        self.stdout.write(f'Scanning {total} piggy banks...\n')

        total_contrib = 0
        total_wd = 0
        total_transfer = 0
        total_approval_created = 0
        processed = 0
        errors = 0

        for target in piggy_banks:
            try:
                contrib_created = 0
                wd_created = 0
                transfer_created = 0
                approval_created = 0

                # Backfill contribution tokens
                for txn in target.transactions.filter(transaction_type='piggy_bank_contribution'):
                    if not PiggyBankTransaction.objects.filter(
                        piggy_bank=target, event_type='contribution',
                        performed_by=txn.payment_profile, created_at=txn.created_at
                    ).exists():
                        PiggyBankTransaction.objects.create(
                            piggy_bank=target, event_type='contribution',
                            amount=txn.amount, performed_by=txn.payment_profile,
                            balance_after=txn.balance_after, note=txn.description or '',
                            created_at=txn.created_at,
                        )
                        contrib_created += 1

                # Backfill withdrawal tokens
                for txn in target.transactions.filter(transaction_type='piggy_bank_withdrawal'):
                    if not PiggyBankTransaction.objects.filter(
                        piggy_bank=target, event_type='withdrawal',
                        performed_by=txn.payment_profile, created_at=txn.created_at
                    ).exists():
                        PiggyBankTransaction.objects.create(
                            piggy_bank=target, event_type='withdrawal',
                            amount=txn.amount, performed_by=txn.payment_profile,
                            balance_after=txn.balance_after, note=txn.description or '',
                            created_at=txn.created_at,
                        )
                        wd_created += 1

                # Backfill transfer tokens (automation/conversion — map to withdrawal)
                for txn in target.transactions.filter(transaction_type='transfer'):
                    if not PiggyBankTransaction.objects.filter(
                        piggy_bank=target, event_type='withdrawal',
                        performed_by=txn.payment_profile, created_at=txn.created_at
                    ).exists():
                        PiggyBankTransaction.objects.create(
                            piggy_bank=target, event_type='withdrawal',
                            amount=txn.amount, performed_by=txn.payment_profile,
                            balance_after=txn.balance_after, note=txn.description or '',
                            created_at=txn.created_at,
                        )
                        transfer_created += 1

                # Backfill approval events from existing action requests
                for ar in PiggyBankActionRequest.objects.filter(piggy_bank=target):
                    if ar.status in ('executed', 'approved'):
                        if not PiggyBankTransaction.objects.filter(
                            piggy_bank=target, event_type='approval_approved',
                            performed_by=ar.requested_by, created_at=ar.updated_at
                        ).exists():
                            PiggyBankTransaction.objects.create(
                                piggy_bank=target, event_type='approval_approved',
                                amount=ar.amount or 0, performed_by=ar.requested_by,
                                note=f"Backfill: {ar.action_type} approved — {ar.reason or ''}",
                                created_at=ar.updated_at,
                            )
                            approval_created += 1
                    elif ar.status == 'rejected':
                        if not PiggyBankTransaction.objects.filter(
                            piggy_bank=target, event_type='approval_rejected',
                            performed_by=ar.requested_by, created_at=ar.updated_at
                        ).exists():
                            PiggyBankTransaction.objects.create(
                                piggy_bank=target, event_type='approval_rejected',
                                amount=ar.amount or 0, performed_by=ar.requested_by,
                                note=f"Backfill: {ar.action_type} rejected — {ar.reason or ''}",
                                created_at=ar.updated_at,
                            )
                            approval_created += 1

                if contrib_created or wd_created or transfer_created or approval_created:
                    self.stdout.write(
                        f"  [{target.name[:40]:40s}] +{contrib_created}C / +{wd_created}W / +{transfer_created}T / +{approval_created}A"
                    )

                total_contrib += contrib_created
                total_wd += wd_created
                total_transfer += transfer_created
                total_approval_created += approval_created
                processed += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error processing '{target.name}' (id={target.id}): {e}"))
                errors += 1

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(
            f'Processed {processed}/{total} piggy banks ({errors} errors).\n'
            f'  Contributions imported: {total_contrib}\n'
            f'  Withdrawals imported:   {total_wd}\n'
            f'  Transfers imported:     {total_transfer}\n'
            f'  Approval events imported: {total_approval_created}\n'
            f'  Total records created:  {total_contrib + total_wd + total_transfer + total_approval_created}'
        ))
