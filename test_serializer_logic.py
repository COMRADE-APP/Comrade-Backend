import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import RoundContribution, PaymentGroupMember
from Authentication.models import CustomUser

user = CustomUser.objects.get(email='jmbngugimbugua@gmail.com')
round_obj = RoundContribution.objects.filter(round_number=3).first()

print(f"Checking for User: {user.id} ({user.email})")
print(f"Round Group: {round_obj.payment_group.id}")

try:
    member = PaymentGroupMember.objects.get(
        payment_group=round_obj.payment_group,
        payment_profile__user__user=user
    )
    print(f"Found Member: {member.id}")
    
    award_history = round_obj.award_history
    print(f"Award History: {award_history}")
    
    has_unclaimed = any(str(h.get('member_id')) == str(member.id) and not h.get('claimed') for h in award_history)
    print(f"Has Unclaimed Payout: {has_unclaimed}")
    
    # Check is_recipient logic
    is_recipient = (round_obj.awarded_to_id == member.id) or has_unclaimed
    print(f"Is Recipient: {is_recipient}")

except Exception as e:
    print(f"Error: {e}")
