"""
Seed test Organizer and Sponsor profiles with cross-subscriptions
for testing partnerships, sponsorships, and follow features.
"""
from django.core.management.base import BaseCommand
from Authentication.models import CustomUser
from Events.models import OrganizerProfile, SponsorProfile, OrganizerFollow, SponsorFollow


class Command(BaseCommand):
    help = 'Seed test organizer and sponsor profiles with subscriptions'

    def handle(self, *args, **options):
        users = list(CustomUser.objects.all())

        if len(users) < 4:
            self.stdout.write(self.style.ERROR('Need at least 4 users. Run populate data first.'))
            return

        # ── Organizer Profiles ──
        org_data = [
            {'user_email': users[0].email, 'business_name': 'Nairobi Tech Events',
             'bio': 'Organizing the best tech events in Nairobi since 2024. Meetups, hackathons, and conferences.',
             'location': 'Nairobi, Kenya', 'website': 'https://nairobitech.events',
             'is_open_for_partnership': True},
            {'user_email': users[1].email if len(users) > 1 else users[0].email,
             'business_name': 'Creative Arts Collective',
             'bio': 'Bringing artists, musicians, and performers together. We curate cultural events across East Africa.',
             'location': 'Mombasa, Kenya', 'website': 'https://creativearts.co.ke',
             'is_open_for_partnership': True},
            {'user_email': users[2].email if len(users) > 2 else users[0].email,
             'business_name': 'Wellness & Yoga Retreats',
             'bio': 'Mindfulness retreats, yoga workshops, and wellness events. Corporate and private bookings available.',
             'location': 'Kisumu, Kenya', 'website': '',
             'is_open_for_partnership': True},
        ]

        for d in org_data:
            user = CustomUser.objects.get(email=d['user_email'])
            profile, created = OrganizerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'business_name': d['business_name'],
                    'bio': d['bio'],
                    'location': d['location'],
                    'website': d['website'],
                    'is_open_for_partnership': d['is_open_for_partnership'],
                }
            )
            if created:
                user.is_organizer = True
                user.save(update_fields=['is_organizer'])
            label = 'Created' if created else 'Already exists'
            self.stdout.write(f'  {label} Organizer: {profile.business_name} ({user.email})')

        # ── Sponsor Profiles ──
        sp_data = [
            {'user_email': users[3].email if len(users) > 3 else users[0].email,
             'company_name': 'SafariLink Telecom',
             'industry': 'Telecommunications',
             'description': 'Leading telecom provider in East Africa. We sponsor tech events, hackathons, and innovation summits.',
             'location': 'Nairobi, Kenya', 'website': 'https://safarilink.co.ke',
             'budget_range': '$5k-$20k per event', 'contact_email': 'sponsorship@safarilink.co.ke'},
            {'user_email': users[4].email if len(users) > 4 else users[0].email,
             'company_name': 'GreenEnergy Solutions',
             'industry': 'Renewable Energy',
             'description': 'Sustainable energy solutions across Africa. Supporting green events and environmental awareness campaigns.',
             'location': 'Lagos, Nigeria', 'website': '',
             'budget_range': '$2k-$10k per event', 'contact_email': 'partners@greenenergy.ng'},
            {'user_email': users[5].email if len(users) > 5 else users[0].email,
             'company_name': 'FinTech Africa Ventures',
             'industry': 'Financial Technology',
             'description': 'Investing in African fintech startups. Sponsor pitch competitions, demo days, and fintech conferences.',
             'location': 'Cape Town, South Africa', 'website': 'https://fintechafrica.vc',
             'budget_range': '$10k-$50k per event', 'contact_email': 'events@fintechafrica.vc'},
        ]

        for d in sp_data:
            user = CustomUser.objects.get(email=d['user_email'])
            profile, created = SponsorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company_name': d['company_name'],
                    'industry': d['industry'],
                    'description': d['description'],
                    'location': d['location'],
                    'website': d['website'],
                    'budget_range': d['budget_range'],
                    'contact_email': d['contact_email'],
                }
            )
            if created:
                user.is_sponsor = True
                user.save(update_fields=['is_sponsor'])
            label = 'Created' if created else 'Already exists'
            self.stdout.write(f'  {label} Sponsor: {profile.company_name} ({user.email})')

        # ── Cross-Subscriptions (Follows) ──
        orgs = list(OrganizerProfile.objects.all())
        sponsors = list(SponsorProfile.objects.all())

        follow_count = 0
        for i, org in enumerate(orgs):
            for j, sp in enumerate(sponsors):
                if i != j:  # Don't follow own profile
                    _, created = OrganizerFollow.objects.get_or_create(
                        follower=org.user, organizer=org,
                        defaults={'notifications_enabled': True}
                    )
                    if created:
                        follow_count += 1
                    _, created = SponsorFollow.objects.get_or_create(
                        follower=org.user, sponsor=sp,
                        defaults={'notifications_enabled': True}
                    )
                    if created:
                        follow_count += 1

        self.stdout.write(f'  Created {follow_count} cross-subscriptions')

        # ── Summary ──
        org_count = OrganizerProfile.objects.count()
        sp_count = SponsorProfile.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nSeed complete: {org_count} organizers, {sp_count} sponsors, {follow_count} follows'
        ))
