from django.db import migrations

CATEGORIES = [
    'Concert', 'Festival', 'Potluck', 'Movie Screening', 'Stand-up Comedy',
    'Theatre', 'Opera', 'Talent Show', 'Roadshow', 'Tour', 'Expo',
    'Exhibition', 'Workshop', 'Conference', 'Networking', 'Sports',
    'Charity / Gala', 'Performance', 'Dance', 'DJ / Nightlife',
    'Food & Drink', 'Market', 'Seminar', 'Panel Discussion',
    'Book Reading / Signing', 'Art Opening', 'Film Festival',
    'Trade Show', 'Fashion Show', 'Cultural Celebration',
    'Community Service', 'Health & Wellness', 'Tech Talk',
    'Kids / Family', 'Outdoor Adventure', 'Religious / Spiritual',
    'Political / Civic', 'Virtual Event',
]

def seed_categories(apps, schema_editor):
    EventCategory = apps.get_model('Events', 'EventCategory')
    for name in CATEGORIES:
        EventCategory.objects.get_or_create(name=name, defaults={
            'description': f'{name} event category'
        })

def reverse_categories(apps, schema_editor):
    EventCategory = apps.get_model('Events', 'EventCategory')
    EventCategory.objects.filter(name__in=CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("Events", "0013_eventsponsor_contribution_amount_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_categories),
    ]
