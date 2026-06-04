"""
Audit and optionally fix PiggyBankTransaction consistency.

Compares TransactionHistory records (piggy-bank-related) against
PiggyBankTransaction to find gaps where analytics would miss data.

Run with: python manage.py audit_piggy_analytics
          python manage.py audit_piggy_analytics --fix
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal
import secrets


class Command(BaseCommand):
    help = 'Audit PiggyBankTransaction consistency with TransactionHistory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Create missing PiggyBankTransaction records',
        )

    def handle(self, *args, **options):
        from Payment.models import (
            TransactionHistory, TransactionToken,
            PiggyBankTransaction, PaymentAuthorization,
            PaymentVerification,
        )

        should_fix = options['fix']

        piggy_histories = TransactionHistory.objects.filter(
            transaction_token__piggy_bank__isnull=False
        ).select_related(
            'transaction_token__piggy_bank',
            'payment_profile',
        ).order_by('created_at')

        total = piggy_histories.count()
        self.stdout.write(f'Found {total} TransactionHistory records linked to piggy banks.\n')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No gaps found — everything is consistent.'))
            return

        missing = []
        ok_count = 0

        for th in piggy_histories:
            txn_token = th.transaction_token
            piggy_bank = txn_token.piggy_bank

            if not piggy_bank:
                continue

            event_type = self._map_event_type(th.transaction_category)
            if event_type is None:
                self.stdout.write(f'  Skipping id={th.id}: unknown category={th.transaction_category}')
                continue

            exists = PiggyBankTransaction.objects.filter(
                piggy_bank=piggy_bank,
                event_type=event_type,
                created_at=th.created_at,
                amount=th.amount,
            ).exists()

            if exists:
                ok_count += 1
            else:
                missing.append({
                    'th_id': th.id,
                    'piggy_bank_id': str(piggy_bank.id),
                    'piggy_bank_name': piggy_bank.name,
                    'amount': th.amount,
                    'category': th.transaction_category,
                    'mapped_event': event_type,
                    'created_at': th.created_at,
                    'payment_profile_id': th.payment_profile_id,
                })

        self.stdout.write(f'  Matched: {ok_count}')
        self.stdout.write(f'  Missing: {len(missing)}\n')

        if not missing:
            self.stdout.write(self.style.SUCCESS('All TransactionHistory records have matching PiggyBankTransaction entries.'))
            return

        self.stdout.write(self.style.WARNING('--- Missing PiggyBankTransaction Records ---'))
        for m in missing:
            self.stdout.write(
                f"  TH#{m['th_id']} | PiggyBank: {m['piggy_bank_name']} ({m['piggy_bank_id']}) | "
                f"Amount: {m['amount']} | Category: {m['category']} → {m['mapped_event']} | "
                f"Date: {m['created_at'].isoformat()}"
            )

        if should_fix:
            self.stdout.write('\nCreating missing records...')
            created_count = 0
            for m in missing:
                try:
                    th = TransactionHistory.objects.get(id=m['th_id'])
                    txn_token = th.transaction_token
                    PiggyBankTransaction.objects.create(
                        piggy_bank_id=m['piggy_bank_id'],
                        event_type=m['mapped_event'],
                        amount=m['amount'],
                        performed_by=th.payment_profile,
                        balance_after=txn_token.balance_after if txn_token else None,
                        note=txn_token.description if txn_token else '',
                        created_at=m['created_at'],
                    )
                    created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error creating for TH#{m['th_id']}: {e}"))

            self.stdout.write(self.style.SUCCESS(f'Created {created_count} missing PiggyBankTransaction records.'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'\nRun with --fix to create {len(missing)} missing PiggyBankTransaction records.'
                )
            )

    def _map_event_type(self, category):
        mapping = {
            'piggy_bank_contribution': 'contribution',
            'piggy_bank_withdrawal': 'withdrawal',
            'transfer': 'withdrawal',
        }
        return mapping.get(category)
