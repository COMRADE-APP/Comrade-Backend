import uuid

from django.db import migrations, models


def populate_event_uuids(apps, schema_editor):
    Event = apps.get_model('Events', 'Event')
    for event in Event.objects.filter(uuid__isnull=True):
        event.uuid = uuid.uuid4()
        event.save(update_fields=['uuid'])


def populate_booking_uuids(apps, schema_editor):
    EventSlotBooking = apps.get_model('Events', 'EventSlotBooking')
    for booking in EventSlotBooking.objects.filter(uuid__isnull=True):
        booking.uuid = uuid.uuid4()
        booking.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ("Events", "0017_booking_attendee_info"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="eventslotbooking",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="event",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="eventslotbooking",
            name="attendees",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Array of {name, email, phone} for all people admitted",
            ),
        ),
        migrations.AddField(
            model_name="eventslotbooking",
            name="group_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Group name (for group tickets)",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="eventslotbooking",
            name="shared_with",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Array of user IDs this ticket is shared with",
            ),
        ),
        migrations.AddField(
            model_name="eventslotbooking",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="tickettier",
            name="category",
            field=models.CharField(
                choices=[
                    ("individual", "Individual"),
                    ("couple", "Couple"),
                    ("group", "Group"),
                ],
                default="individual",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="tickettier",
            name="tier",
            field=models.CharField(
                choices=[
                    ("regular", "Regular"),
                    ("early_bird", "Early Bird"),
                    ("vip", "VIP"),
                    ("vvip", "VVIP"),
                ],
                default="regular",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="eventslotbooking",
            name="attendee_name",
            field=models.CharField(
                blank=True, default="", help_text="Ticket holder name", max_length=200
            ),
        ),
        migrations.AlterField(
            model_name="eventslotbooking",
            name="quantity",
            field=models.IntegerField(
                default=1,
                help_text="Number of people this ticket admits (e.g., 2 for couple)",
            ),
        ),
        migrations.RunPython(populate_event_uuids, migrations.RunPython.noop),
        migrations.RunPython(populate_booking_uuids, migrations.RunPython.noop),
    ]
