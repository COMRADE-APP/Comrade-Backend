import os
import django
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Comrade.settings')
django.setup()

from Authentication.models import CustomUser, Profile
from Payment.models import PaymentProfile

def ensure_profiles():
    """
    Ensure every User has a Profile, and every Profile has a PaymentProfile.
    """
    print("Starting profile verification...")
    
    users = CustomUser.objects.all()
    print(f"Checking {users.count()} users...")
    
    # 1. Ensure Profile exists for every User
    for user in users:
        profile, created = Profile.objects.get_or_create(user=user)
        if created:
            print(f"Created missing Profile for user: {user.email}")
    
    profiles = Profile.objects.all()
    print(f"Checking {profiles.count()} profiles for payment profiles...")
    
    # 2. Ensure PaymentProfile exists for every Profile
    created_count = 0
    for profile in profiles:
        if not PaymentProfile.objects.filter(user=profile).exists():
            PaymentProfile.objects.create(
                user=profile,
                tier='free',
                comrade_balance=0.00,
                profile_token=f"PAY-{uuid.uuid4().hex[:12].upper()}",
                payment_option='comrade_balance'
            )
            created_count += 1
            print(f"Created PaymentProfile for: {profile.user.email}")
            
    if created_count == 0:
        print("All profiles already have payment profiles.")
    else:
        print(f"Successfully created {created_count} missing payment profiles.")

if __name__ == '__main__':
    ensure_profiles()
