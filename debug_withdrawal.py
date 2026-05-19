import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comrade.settings")
django.setup()

from Payment.models import WithdrawalRequest, TransactionToken

try:
    req = WithdrawalRequest.objects.last()
    if not req:
        print("No withdrawal requests")
    else:
        print(f"Request ID: {req.id}, Status: {req.status}, Amount: {req.amount}, Group: {req.payment_group_id}")
        
        # Try to simulate approval logic
        admin_profile = req.payment_group.creator
        withdrawal = req
        
        payout = withdrawal.amount
        print(f"Payout: {payout}")
        try:
            TransactionToken.objects.create(
                payment_profile=admin_profile,
                recipient_profile=withdrawal.destination_wallet,
                amount=payout,
                transaction_type='withdrawal',
                status='completed',
                description=f"Withdrawal from {withdrawal.payment_group.name} (Net)"
            )
            print("TransactionToken creation SUCCESS!")
        except Exception as e:
            import traceback
            print(f"TransactionToken creation FAILED: {str(e)}")
            traceback.print_exc()

except Exception as e:
    import traceback
    traceback.print_exc()
