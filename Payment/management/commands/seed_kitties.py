"""
seed_kitties – Populate kitty fund pools with sample data that matches the
mock data previously shown on the frontend KittyManagement page.
Usage: python manage.py seed_kitties
"""
import uuid
import random
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from Payment.models import (
    PaymentGroups, PaymentGroupMember, PaymentProfile, Contribution,
)
from Authentication.models import Profile, CustomUser

logger = logging.getLogger(__name__)


# ── The four kitties from the frontend mock ──────────────────────────
KITTIES_DATA = [
    {
        'name': 'Solar for Schools',
        'description': 'Community solar energy initiative for rural schools',
        'type_label': 'Charity',
        'balance': 245000,
        'total_inflow': 890000,
        'monthly': [
            ('Sep', 85000, 42000), ('Oct', 120000, 95000), ('Nov', 95000, 68000),
            ('Dec', 140000, 110000), ('Jan', 180000, 130000), ('Feb', 150000, 100000),
            ('Mar', 120000, 100000),
        ],
    },
    {
        'name': 'TechHub Ventures',
        'description': 'Technology venture capital fund',
        'type_label': 'Capital Venture',
        'balance': 1250000,
        'total_inflow': 3200000,
        'monthly': [
            ('Sep', 350000, 200000), ('Oct', 480000, 310000), ('Nov', 520000, 280000),
            ('Dec', 600000, 400000), ('Jan', 450000, 260000), ('Feb', 400000, 250000),
            ('Mar', 400000, 250000),
        ],
    },
    {
        'name': 'Mama Mboga Supplies',
        'description': 'Fresh produce and grocery supply shop',
        'type_label': 'Shop',
        'balance': 45200,
        'total_inflow': 320000,
        'monthly': [
            ('Jan', 80000, 65000), ('Feb', 120000, 109800), ('Mar', 120000, 100000),
        ],
    },
    {
        'name': 'GreenBuild Co.',
        'description': 'Sustainable construction materials company',
        'type_label': 'Business',
        'balance': 780000,
        'total_inflow': 2100000,
        'monthly': [
            ('Sep', 200000, 120000), ('Oct', 280000, 170000), ('Nov', 350000, 230000),
            ('Dec', 400000, 280000), ('Jan', 320000, 200000), ('Feb', 300000, 180000),
            ('Mar', 250000, 140000),
        ],
    },
]

# Months mapped to approximate dates so contributions have realistic timestamps
MONTH_MAP = {
    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
    'Jan': 1, 'Feb': 2, 'Mar': 3,
}


class Command(BaseCommand):
    help = 'Seed the database with sample kitty fund pools and contributions.'

    def handle(self, *args, **options):
        # Find or create a seed user's payment profile (use first superuser or first user)
        owner_user = CustomUser.objects.filter(is_superuser=True).first() or CustomUser.objects.first()
        if not owner_user:
            self.stderr.write(self.style.ERROR('No users in the database. Create one first.'))
            return

        owner_profile = Profile.objects.filter(user=owner_user).first()
        if not owner_profile:
            self.stderr.write(self.style.ERROR(f'No Profile for user {owner_user.email}. Run ensure_profiles first.'))
            return

        payment_profile, _ = PaymentProfile.objects.get_or_create(user=owner_profile)

        created_count = 0
        for kd in KITTIES_DATA:
            # Don't duplicate
            if PaymentGroups.objects.filter(name=f"{kd['name']} Fund Pool", group_type='kitty').exists():
                self.stdout.write(f"  [SKIP] Kitty '{kd['name']}' already exists, skipping.")
                continue

            kitty = PaymentGroups.objects.create(
                name=f"{kd['name']} Fund Pool",
                description=kd['description'],
                creator=payment_profile,
                group_type='kitty',
                current_amount=Decimal(str(kd['balance'])),
                target_amount=Decimal(str(kd['total_inflow'])),
                contribution_type='flexible',
                frequency='one_time',
                is_public=False,
                requires_approval=False,
            )

            # Add creator as admin member
            member, _ = PaymentGroupMember.objects.get_or_create(
                payment_group=kitty,
                payment_profile=payment_profile,
                defaults={'is_admin': True},
            )

            # Create contribution records from the monthly data
            now = timezone.now()
            year = now.year
            for month_label, inflow, outflow in kd['monthly']:
                month_num = MONTH_MAP.get(month_label, 1)
                # Use current year for Jan-Mar, previous year for Sep-Dec
                contrib_year = year if month_num <= 3 else year - 1
                contrib_date = timezone.make_aware(
                    timezone.datetime(contrib_year, month_num, random.randint(1, 28), 12, 0)
                ) if timezone.is_naive(timezone.datetime(contrib_year, month_num, 1)) else timezone.datetime(
                    contrib_year, month_num, random.randint(1, 28), 12, 0, tzinfo=timezone.utc
                )

                Contribution.objects.create(
                    payment_group=kitty,
                    member=member,
                    amount=Decimal(str(inflow)),
                    contributed_at=contrib_date,
                    notes=f'Seed contribution – {month_label} inflow',
                )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"  [OK] Created kitty '{kitty.name}' with {len(kd['monthly'])} contributions"))

        self.stdout.write(self.style.SUCCESS(f'\nDone. Created {created_count} new kitties.'))
