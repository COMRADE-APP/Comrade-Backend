# Generated manually — backfill PiggyBankMember from existing PaymentGroupMember records

from django.db import migrations
from decimal import Decimal


def backfill_piggy_bank_members(apps, schema_editor):
    GroupTarget = apps.get_model("Payment", "GroupTarget")
    PiggyBankMember = apps.get_model("Payment", "PiggyBankMember")
    PaymentGroupMember = apps.get_model("Payment", "PaymentGroupMember")
    PiggyBankTransaction = apps.get_model("Payment", "PiggyBankTransaction")
    PaymentProfile = apps.get_model("Payment", "PaymentProfile")

    # 1. Group piggy banks: backfill from PaymentGroupMember
    for target in GroupTarget.objects.filter(payment_group__isnull=False).iterator():
        for pgm in PaymentGroupMember.objects.filter(
            payment_group=target.payment_group, is_active=True
        ).iterator():
            PiggyBankMember.objects.get_or_create(
                piggy_bank=target,
                payment_profile=pgm.payment_profile,
                defaults={
                    "is_admin": pgm.is_admin,
                    "total_contributed": pgm.total_contributed,
                    "is_active": True,
                },
            )

    # 2. Individual piggy banks: backfill from owner
    for target in GroupTarget.objects.filter(owner__isnull=False).iterator():
        tc = Decimal("0.00")
        tw = Decimal("0.00")
        for txn in PiggyBankTransaction.objects.filter(
            piggy_bank=target, event_type="contribution"
        ).iterator():
            tc += Decimal(str(txn.amount))
        for txn in PiggyBankTransaction.objects.filter(
            piggy_bank=target, event_type="withdrawal"
        ).iterator():
            tw += Decimal(str(txn.amount))
        PiggyBankMember.objects.get_or_create(
            piggy_bank=target,
            payment_profile=target.owner,
            defaults={
                "is_admin": True,
                "total_contributed": tc,
                "total_withdrawn": tw,
                "is_active": True,
            },
        )


def reverse_backfill(apps, schema_editor):
    PiggyBankMember = apps.get_model("Payment", "PiggyBankMember")
    PiggyBankMember.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Payment", "0077_piggybankmember_leave_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_piggy_bank_members, reverse_backfill),
    ]
