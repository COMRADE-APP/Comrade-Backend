# Generated manually to add merge action type and target_piggy_banks field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Payment", "0075_piggybank_transaction_log"),
    ]

    operations = [
        migrations.AlterField(
            model_name="piggybankactionrequest",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("extend_maturity", "Extend Maturity Date"),
                    ("withdraw", "Withdraw Amount"),
                    ("dissolve", "Dissolve Piggy Bank"),
                    ("merge", "Merge Piggy Banks"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="piggybankactionrequest",
            name="target_piggy_banks",
            field=models.ManyToManyField(
                blank=True,
                help_text="Piggy banks to be merged into this one",
                related_name="merge_requests",
                to="Payment.GroupTarget",
            ),
        ),
    ]
