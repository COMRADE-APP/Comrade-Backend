from django.core.management.base import BaseCommand
from Authentication.models import CustomUser, Profile
from Payment.models import PaymentProfile
import uuid

class Command(BaseCommand):
    help = 'Ensures every user has a Profile and PaymentProfile'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting profile verification...")
        
        users = CustomUser.objects.all()
        self.stdout.write(f"Checking {users.count()} users...")
        
        profile_count = 0
        payment_profile_count = 0

        for user in users:
            # 1. Ensure Profile exists
            profile, created = Profile.objects.get_or_create(user=user)
            if created:
                profile_count += 1
            
            # 2. Ensure PaymentProfile exists
            if not PaymentProfile.objects.filter(user=profile).exists():
                PaymentProfile.objects.create(
                    user=profile,
                    tier='free',
                    comrade_balance=0.00,
                    profile_token=f"PAY-{uuid.uuid4().hex[:12].upper()}",
                    payment_option='comrade_balance'
                )
                payment_profile_count += 1
        
        self.stdout.write(self.style.SUCCESS(f"Created {profile_count} Profiles."))
        self.stdout.write(self.style.SUCCESS(f"Created {payment_profile_count} PaymentProfiles."))
