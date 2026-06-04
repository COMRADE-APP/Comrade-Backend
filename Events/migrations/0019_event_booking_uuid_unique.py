import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Events", "0018_ticket_tier_category_tier_and_booking_updates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="eventslotbooking",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
