from Authentication.models import Profile, CustomUser
from Payment.models import PaymentProfile, PaymentGroups, PaymentGroupMember
from django.db.models import Q

print("Searching for users...")
users = CustomUser.objects.filter(username='jay')

print(f"Found {users.count()} users: {[u.username for u in users]}")

for u in users:
    print(f"Processing user: {u.username} ({u.first_name} {u.last_name})")
    profile = Profile.objects.filter(user=u).first()
    if not profile:
        print(" -> No profile found")
        continue
        
    pay_profile = PaymentProfile.objects.filter(user=profile).first()
    if not pay_profile:
        print(" -> No payment profile found")
        continue

    pay_profile.comrade_balance = max(pay_profile.comrade_balance, 60948.00)
    pay_profile.save()
    print(f" -> Comrade balance updated to {pay_profile.comrade_balance}")

    memberships = PaymentGroupMember.objects.filter(payment_profile=pay_profile)
    for gm in memberships:
        grp = gm.payment_group
        grp.current_amount = max(grp.current_amount, 293984.00)
        grp.save()
        print(f" -> Group '{grp.name}' updated to {grp.current_amount}")

print("Done.")
