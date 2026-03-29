"""
Management command to backfill usernames for existing users.
Generates usernames from first_name + last_name with uniqueness handling.
"""
from django.core.management.base import BaseCommand
from Authentication.models import CustomUser


class Command(BaseCommand):
    help = 'Generate usernames for all users that don\'t have one'

    def handle(self, *args, **options):
        users = CustomUser.objects.filter(username__isnull=True) | CustomUser.objects.filter(username='')
        total = users.count()
        self.stdout.write(f'Found {total} users without usernames')

        updated = 0
        for user in users:
            user.username = None  # Force regeneration
            user.save()  # save() calls _generate_unique_username
            updated += 1
            if updated % 100 == 0:
                self.stdout.write(f'  Processed {updated}/{total}...')

        self.stdout.write(self.style.SUCCESS(f'Successfully generated usernames for {updated} users'))
