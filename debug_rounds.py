import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import RoundContribution

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

rounds = RoundContribution.objects.filter(round_number=3)
for r in rounds:
    print(f"ID: {r.id}")
    print(f"Status: {r.status}")
    print(f"Claim Status: {r.claim_status}")
    print(f"Awarded To: {r.awarded_to}")
    print(f"Award History: {json.dumps(r.award_history, default=decimal_default)}")
    print(f"Total Collected: {r.total_collected}")
    print("-" * 20)
