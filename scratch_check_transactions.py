import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import EscrowTransaction

txns = EscrowTransaction.objects.all().order_by('-created_at')[:20]
print(f"Total transactions in database: {EscrowTransaction.objects.count()}")
for t in txns:
    print(f"ID: {t.id}")
    print(f"  Type: {t.transaction_type}")
    print(f"  Category: {t.transaction_category}")
    print(f"  Amount: {t.amount}")
    print(f"  Details: {t.transaction_details}")
