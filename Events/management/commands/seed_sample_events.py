from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from Events.models import Event, EventCategory, EventCategoryAssignment
import random
import uuid

CustomUser = get_user_model()

SAMPLE_DATA = {
    'Concert': [
        {'name': 'Summer Jazz Night', 'desc': 'An enchanting evening of live jazz under the stars featuring the city\'s finest brass and rhythm sections.', 'loc': 'Brooklyn, NY', 'price': 45},
        {'name': 'Indie Rock Fest', 'desc': 'Three up-and-coming indie rock bands take the stage for an electrifying night of original music.', 'loc': 'Austin, TX', 'price': 25},
        {'name': 'Classical Piano Recital', 'desc': 'Award-winning pianist performs Chopin, Debussy, and Rachmaninoff in an intimate setting.', 'loc': 'Chicago, IL', 'price': 60},
    ],
    'Festival': [
        {'name': 'City Arts & Music Festival', 'desc': 'A weekend-long celebration of local art, live music, food trucks, and interactive installations for all ages.', 'loc': 'San Francisco, CA', 'price': 0},
        {'name': 'Harvest Moon Festival', 'desc': 'Celebrate the autumn harvest with pumpkin carving, hayrides, live folk music, and farm-to-table dining.', 'loc': 'Portland, OR', 'price': 15},
    ],
    'Potluck': [
        {'name': 'Neighborhood Community Potluck', 'desc': 'Bring your favorite dish and meet your neighbors at this monthly community gathering in the park.', 'loc': 'Denver, CO', 'price': 0},
        {'name': 'International Cuisine Exchange', 'desc': 'Share and sample dishes from around the world — each guest brings a dish representing their heritage.', 'loc': 'Toronto, ON', 'price': 0},
    ],
    'Movie Screening': [
        {'name': 'Classic Film Night: Casablanca', 'desc': 'Experience the timeless romance of Casablanca on the big screen with restored 4K projection.', 'loc': 'Los Angeles, CA', 'price': 12},
        {'name': 'Indie Shorts Showcase', 'desc': 'A curated selection of the year\'s best independent short films followed by a Q&A with the directors.', 'loc': 'New York, NY', 'price': 10},
    ],
    'Stand-up Comedy': [
        {'name': 'Laugh Factory Open Mic', 'desc': 'The city\'s funniest comedians test new material at this legendary open mic night.', 'loc': 'Los Angeles, CA', 'price': 10},
        {'name': 'Comedy Night ft. Headliner', 'desc': 'A nationally touring headliner plus three hot opening acts for a night of non-stop laughter.', 'loc': 'Nashville, TN', 'price': 30},
    ],
    'Theatre': [
        {'name': 'Hamlet — Modern Revival', 'desc': 'A bold contemporary reimagining of Shakespeare\'s classic tragedy set in a modern corporate world.', 'loc': 'London, UK', 'price': 55},
        {'name': 'The Importance of Being Earnest', 'desc': 'Oscar Wilde\'s brilliant comedy of manners performed by an award-winning local company.', 'loc': 'Boston, MA', 'price': 40},
    ],
    'Opera': [
        {'name': 'La Traviata — Evening Performance', 'desc': 'Verdi\'s masterpiece performed by the city opera company with full orchestra and chorus.', 'loc': 'Milan, IT', 'price': 85},
        {'name': 'Opera Gala: Best of Puccini', 'desc': 'A selection of the most beloved arias from Puccini\'s greatest works in a gala format.', 'loc': 'New York, NY', 'price': 75},
    ],
    'Talent Show': [
        {'name': 'City\'s Got Talent — Qualifiers', 'desc': 'Amazing contestants from across the region compete for a spot in the grand finale.', 'loc': 'Atlanta, GA', 'price': 15},
        {'name': 'Youth Talent Showcase', 'desc': 'Young performers ages 8–18 display their skills in music, dance, comedy, and more.', 'loc': 'Seattle, WA', 'price': 5},
    ],
    'Roadshow': [
        {'name': 'Antiques Roadshow Appraisal Event', 'desc': 'Bring your family heirlooms and collectibles for free appraisal by expert authenticators.', 'loc': 'Philadelphia, PA', 'price': 0},
        {'name': 'Tech Innovation Roadshow', 'desc': 'A touring exhibition of cutting-edge startups demonstrating their products to investors.', 'loc': 'San Jose, CA', 'price': 20},
    ],
    'Tour': [
        {'name': 'Historic Downtown Walking Tour', 'desc': 'Explore the hidden history and architecture of downtown with a licensed tour guide.', 'loc': 'Boston, MA', 'price': 25},
        {'name': 'Wine Country Bus Tour', 'desc': 'A full-day guided tour through three renowned vineyards with tastings and lunch included.', 'loc': 'Sonoma, CA', 'price': 120},
        {'name': 'Street Art & Graffiti Tour', 'desc': 'Discover vibrant murals and hidden street art gems while learning about the artists and culture.', 'loc': 'Berlin, DE', 'price': 18},
    ],
    'Expo': [
        {'name': 'Home & Garden Expo', 'desc': 'Hundreds of vendors showcase the latest in home improvement, landscaping, and interior design.', 'loc': 'Dallas, TX', 'price': 12},
        {'name': 'Career & Education Expo', 'desc': 'Meet recruiters from top companies and universities offering jobs, internships, and scholarships.', 'loc': 'Washington, DC', 'price': 0},
    ],
    'Exhibition': [
        {'name': 'Impressionists: Light & Color', 'desc': 'A rare collection of Monet, Renoir, and Degas masterpieces on loan from international museums.', 'loc': 'Paris, FR', 'price': 25},
        {'name': 'Modern Sculpture Garden', 'desc': 'An outdoor exhibition of large-scale contemporary sculptures set in a botanical garden.', 'loc': 'Miami, FL', 'price': 18},
    ],
    'Workshop': [
        {'name': 'Watercolor Painting for Beginners', 'desc': 'Learn fundamental watercolor techniques in a relaxed two-hour workshop. All materials provided.', 'loc': 'Portland, OR', 'price': 35},
        {'name': 'Introduction to Python Programming', 'desc': 'A hands-on coding workshop for absolute beginners. Build your first project by the end of the session.', 'loc': 'San Francisco, CA', 'price': 50},
    ],
    'Conference': [
        {'name': 'Tech Leaders Summit 2026', 'desc': 'Industry pioneers share insights on AI, cloud computing, cybersecurity, and the future of technology.', 'loc': 'Las Vegas, NV', 'price': 299},
        {'name': 'Women in Business Conference', 'desc': 'Empowering female entrepreneurs through keynote talks, panel discussions, and networking sessions.', 'loc': 'New York, NY', 'price': 149},
    ],
    'Networking': [
        {'name': 'Startup Mixer & Happy Hour', 'desc': 'Connect with founders, investors, and tech professionals over drinks and appetizers.', 'loc': 'Austin, TX', 'price': 15},
        {'name': 'Creative Professionals Meetup', 'desc': 'Designers, writers, and artists gather for casual conversation and collaboration.', 'loc': 'Brooklyn, NY', 'price': 5},
    ],
    'Sports': [
        {'name': 'Community 5K Fun Run', 'desc': 'A family-friendly 5K run through the park supporting local youth sports programs.', 'loc': 'San Diego, CA', 'price': 0},
        {'name': 'Pickleball Tournament', 'desc': 'Doubles pickleball tournament open to all skill levels. Prizes for top three teams.', 'loc': 'Phoenix, AZ', 'price': 20},
    ],
    'Charity / Gala': [
        {'name': 'Annual Red Cross Charity Gala', 'desc': 'An elegant evening of dinner, dancing, and auctions to support disaster relief efforts.', 'loc': 'Washington, DC', 'price': 200},
        {'name': 'Benefit Concert for Food Banks', 'desc': 'Live music from local bands with all proceeds going to regional food banks.', 'loc': 'Seattle, WA', 'price': 25},
    ],
    'Performance': [
        {'name': 'Contemporary Dance Ensemble', 'desc': 'A breathtaking fusion of ballet and modern dance performed by an internationally acclaimed troupe.', 'loc': 'Montreal, QC', 'price': 45},
        {'name': 'Fire Spinners Night', 'desc': 'Mesmerizing fire dance and flow arts performance under the night sky.', 'loc': 'Albuquerque, NM', 'price': 12},
    ],
    'Dance': [
        {'name': 'Salsa Night — Beginner Lesson + Social', 'desc': 'Learn salsa basics in a one-hour lesson followed by open social dancing until midnight.', 'loc': 'Miami, FL', 'price': 15},
        {'name': 'Swing Dance Workshop & Dance', 'desc': 'Vintage swing dancing with live big band music. No partner needed.', 'loc': 'New Orleans, LA', 'price': 18},
    ],
    'DJ / Nightlife': [
        {'name': 'Underground Electronic Night', 'desc': 'A curated night of deep house and techno with guest DJs from Berlin\'s renowned club scene.', 'loc': 'Berlin, DE', 'price': 20},
        {'name': 'Neon Glow Party', 'desc': 'UV lights, glow paint, and top-40 DJ spinning your favorite dance hits all night long.', 'loc': 'Las Vegas, NV', 'price': 30},
    ],
    'Food & Drink': [
        {'name': 'Farm-to-Table Dinner Experience', 'desc': 'A five-course seasonal tasting menu prepared by a Michelin-starred chef using local ingredients.', 'loc': 'Napa, CA', 'price': 150},
        {'name': 'Craft Beer & Bites Festival', 'desc': 'Sample over 50 craft brews paired with gourmet small plates from local restaurants.', 'loc': 'Portland, OR', 'price': 45},
    ],
    'Market': [
        {'name': 'Weekend Farmers Market', 'desc': 'Fresh produce, artisan breads, local honey, handmade crafts, and live acoustic music.', 'loc': 'Santa Monica, CA', 'price': 0},
        {'name': 'Vintage & Thrift Flea Market', 'desc': 'Hundreds of vendors selling vintage clothing, antiques, vinyl records, and collectibles.', 'loc': 'London, UK', 'price': 2},
    ],
    'Seminar': [
        {'name': 'Personal Finance Bootcamp', 'desc': 'Learn budgeting, investing, and tax strategies from certified financial planners.', 'loc': 'Chicago, IL', 'price': 30},
        {'name': 'Mindfulness & Meditation Seminar', 'desc': 'A half-day retreat exploring meditation techniques, breathwork, and stress management.', 'loc': 'Sedona, AZ', 'price': 40},
    ],
    'Panel Discussion': [
        {'name': 'Future of AI in Healthcare', 'desc': 'Leading doctors, researchers, and AI ethicists discuss how machine learning is transforming medicine.', 'loc': 'Boston, MA', 'price': 0},
        {'name': 'Climate Action: Local Solutions', 'desc': 'Environmental leaders share actionable strategies for reducing carbon footprints at the community level.', 'loc': 'Vancouver, BC', 'price': 0},
    ],
    'Book Reading / Signing': [
        {'name': 'Author Talk: New York Times Bestseller', 'desc': 'Meet the author of this year\'s most talked-about novel for a reading, discussion, and book signing.', 'loc': 'New York, NY', 'price': 5},
        {'name': 'Poetry Open Mic & Reading', 'desc': 'Share your own work or listen to featured local poets in an intimate bookstore setting.', 'loc': 'Portland, OR', 'price': 0},
    ],
    'Art Opening': [
        {'name': 'Emerging Artists: Spring Collection', 'desc': 'Opening reception for a group exhibition featuring works by twelve rising contemporary artists.', 'loc': 'Los Angeles, CA', 'price': 0},
        {'name': 'Photography Exhibition: Urban Landscapes', 'desc': 'Stunning black-and-white photography capturing the soul of cities around the world.', 'loc': 'Tokyo, JP', 'price': 8},
    ],
    'Film Festival': [
        {'name': 'Independent Film Festival — Day Pass', 'desc': 'A full day of independent films, documentaries, and short films from emerging filmmakers worldwide.', 'loc': 'Toronto, ON', 'price': 35},
        {'name': 'Horror Movie Marathon', 'desc': 'Back-to-back classic horror films with themed cocktails and costume contest.', 'loc': 'Los Angeles, CA', 'price': 20},
    ],
    'Trade Show': [
        {'name': 'Automotive Parts & Accessories Expo', 'desc': 'Industry professionals showcase the latest in auto parts, tools, and aftermarket accessories.', 'loc': 'Detroit, MI', 'price': 40},
        {'name': 'B2B SaaS Trade Show', 'desc': 'Connect with enterprise software vendors offering solutions for sales, marketing, and operations.', 'loc': 'San Francisco, CA', 'price': 150},
    ],
    'Fashion Show': [
        {'name': 'Spring/Summer Collection Preview', 'desc': 'Local designers debut their latest collections on the runway with VIP seating available.', 'loc': 'Milan, IT', 'price': 75},
        {'name': 'Sustainable Fashion Showcase', 'desc': 'Eco-friendly designers present clothing made from recycled and ethically sourced materials.', 'loc': 'London, UK', 'price': 30},
    ],
    'Cultural Celebration': [
        {'name': 'Lunar New Year Festival', 'desc': 'Dragon dances, traditional music, lantern making, and authentic cuisine ring in the new year.', 'loc': 'San Francisco, CA', 'price': 0},
        {'name': 'Diwali Festival of Lights', 'desc': 'Celebrate with candlelit ceremonies, rangoli art,Indian dance performances, and festive sweets.', 'loc': 'Edmonton, AB', 'price': 5},
    ],
    'Community Service': [
        {'name': 'Beach Cleanup Volunteer Day', 'desc': 'Join fellow volunteers for a morning of beach cleanup followed by complimentary lunch.', 'loc': 'Santa Cruz, CA', 'price': 0},
        {'name': 'Habitat for Humanity Build Day', 'desc': 'Help construct affordable housing for families in need. No construction experience required.', 'loc': 'Houston, TX', 'price': 0},
    ],
    'Health & Wellness': [
        {'name': 'Sunrise Yoga in the Park', 'desc': 'Start your day with gentle vinyasa yoga led by a certified instructor in a serene park setting.', 'loc': 'Boulder, CO', 'price': 10},
        {'name': 'Holistic Health Fair', 'desc': 'Explore alternative medicine, nutrition counseling, acupuncture demos, and wellness products.', 'loc': 'Sedona, AZ', 'price': 0},
    ],
    'Tech Talk': [
        {'name': 'Building Scalable Microservices', 'desc': 'A senior architect walks through real-world patterns for designing and deploying microservices.', 'loc': 'Seattle, WA', 'price': 0},
        {'name': 'Introduction to Blockchain Technology', 'desc': 'Demystifying blockchain, smart contracts, and decentralized applications for non-technical audiences.', 'loc': 'Austin, TX', 'price': 10},
    ],
    'Kids / Family': [
        {'name': 'Kids Science Fair', 'desc': 'Interactive experiments, rocket launches, and chemistry shows designed to spark curiosity in young minds.', 'loc': 'Orlando, FL', 'price': 8},
        {'name': 'Family Movie Night Under the Stars', 'desc': 'Bring blankets and snacks for an outdoor screening of a beloved family animated film.', 'loc': 'San Diego, CA', 'price': 0},
    ],
    'Outdoor Adventure': [
        {'name': 'Guided Mountain Hike', 'desc': 'A moderately challenging hike through scenic alpine trails with a knowledgeable wilderness guide.', 'loc': 'Denver, CO', 'price': 15},
        {'name': 'Kayaking Sunset Tour', 'desc': 'Paddle through calm coastal waters as the sun sets, with snacks and refreshments on board.', 'loc': 'Honolulu, HI', 'price': 65},
    ],
    'Religious / Spiritual': [
        {'name': 'Interfaith Harmony Gathering', 'desc': 'Leaders from diverse faith traditions come together for dialogue, prayer, and community building.', 'loc': 'Jerusalem, IL', 'price': 0},
        {'name': 'Full Moon Meditation Circle', 'desc': 'Guided group meditation and intention-setting under the light of the full moon.', 'loc': 'Sedona, AZ', 'price': 10},
    ],
    'Political / Civic': [
        {'name': 'Town Hall: Local Council Meeting', 'desc': 'An open forum for residents to voice concerns and hear updates from city council representatives.', 'loc': 'Minneapolis, MN', 'price': 0},
        {'name': 'Youth Civic Engagement Workshop', 'desc': 'Empowering young people to understand local government, advocacy, and the voting process.', 'loc': 'Atlanta, GA', 'price': 0},
    ],
    'Virtual Event': [
        {'name': 'Virtual Art Workshop: Acrylics', 'desc': 'Join live on Zoom for a guided acrylic painting session. Supply list sent upon registration.', 'loc': 'Online', 'price': 20},
        {'name': 'Webinar: Remote Work Best Practices', 'desc': 'Experts share productivity tips, communication tools, and work-life balance strategies for remote teams.', 'loc': 'Online', 'price': 0},
        {'name': 'Online Trivia Night', 'desc': 'Test your knowledge across six rounds of general trivia. Play solo or form a team with friends.', 'loc': 'Online', 'price': 5},
    ],
}

LOCATIONS_POOL = [
    'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX',
    'Phoenix, AZ', 'Philadelphia, PA', 'San Antonio, TX', 'San Diego, CA',
    'Dallas, TX', 'San Jose, CA', 'Austin, TX', 'Jacksonville, FL',
    'Fort Worth, TX', 'Columbus, OH', 'Charlotte, NC', 'Indianapolis, IN',
    'San Francisco, CA', 'Seattle, WA', 'Denver, CO', 'Nashville, TN',
    'Oklahoma City, OK', 'El Paso, TX', 'Washington, DC', 'Boston, MA',
    'Las Vegas, NV', 'Portland, OR', 'Memphis, TN', 'Louisville, KY',
    'Baltimore, MD', 'Milwaukee, WI', 'Albuquerque, NM', 'Tucson, AZ',
    'Miami, FL', 'Atlanta, GA', 'New Orleans, LA', 'Toronto, ON',
    'Vancouver, BC', 'Montreal, QC', 'London, UK', 'Paris, FR',
    'Berlin, DE', 'Tokyo, JP', 'Milan, IT', 'Online',
]

EVENT_TYPES = ['public', 'private', 'invite_only']
EVENT_LOCS = ['online', 'physical', 'hybrid']


def make_event_slug(name):
    return name.lower().replace(' ', '-').replace('/', '').replace(':', '')[:100]


class Command(BaseCommand):
    help = 'Seed sample events across all 38 categories for demo/testing'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Replace existing sample events')
        parser.add_argument('--past-only', action='store_true', help='Only create past events')
        parser.add_argument('--future-only', action='store_true', help='Only create future events')
        parser.add_argument('--count', type=int, default=0, help='Events per category (0 = use all defined)')

    def handle(self, *args, **options):
        force = options['force']
        past_only = options['past_only']
        future_only = options['future_only']
        max_per_cat = options['count']

        # Resolve seed user
        user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            user = CustomUser.objects.filter(is_staff=True).first()
        if not user:
            email = 'seeder@events.local'
            user = CustomUser.objects.filter(email=email).first()
            if not user:
                user = CustomUser.objects.create_user(
                    email=email, password='SeedPass123!',
                    first_name='Event', last_name='Seeder',
                    is_staff=True,
                )
                self.stdout.write(self.style.SUCCESS(f'Created seed user: {email}'))

        now = timezone.now()

        created_count = 0
        skipped_count = 0

        for cat_name, events_list in SAMPLE_DATA.items():
            try:
                category = EventCategory.objects.get(name=cat_name)
            except EventCategory.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Category "{cat_name}" not found, skipping'))
                continue

            cat_events = events_list
            if max_per_cat > 0:
                cat_events = cat_events[:max_per_cat]

            for edata in cat_events:
                slug = make_event_slug(edata['name'])

                # Check duplicate
                existing = Event.objects.filter(name=edata['name'])
                if existing.exists():
                    if force:
                        existing.delete()
                        self.stdout.write(f'  Replaced: {edata["name"]}')
                    else:
                        skipped_count += 1
                        continue

                # Generate date
                if past_only:
                    days_offset = random.randint(-365, -1)
                elif future_only:
                    days_offset = random.randint(1, 365)
                else:
                    # Mix: 40% past, 40% future, 20% very recent/live
                    r = random.random()
                    if r < 0.4:
                        days_offset = random.randint(-365, -2)
                    elif r < 0.8:
                        days_offset = random.randint(2, 365)
                    else:
                        days_offset = random.randint(-1, 1)

                event_date = now + timedelta(days=days_offset)

                # Pick a specific location if defined, else random from pool
                location = edata.get('loc', random.choice(LOCATIONS_POOL))
                event_loc = 'online' if location == 'Online' else random.choice(EVENT_LOCS)

                # Duration
                duration_minutes = random.choice([60, 90, 120, 180, 240])
                from datetime import timedelta as td
                duration = td(minutes=duration_minutes)

                event = Event.objects.create(
                    name=edata['name'],
                    description=edata['desc'],
                    capacity=random.randint(20, 500),
                    duration=duration,
                    event_type=random.choice(EVENT_TYPES),
                    event_location=event_loc,
                    start_time=timezone.now().time(),
                    end_time=(timezone.now() + td(hours=random.choice([1, 2, 3, 4]))).time(),
                    booking_deadline=event_date - timedelta(days=random.randint(1, 7)),
                    status='active',
                    event_date=event_date,
                    location=location,
                    created_by=user,
                    image_url=f'https://picsum.photos/seed/{slug}/800/400',
                )
                # Set price via tickets if needed — the Event model doesn't have price,
                # but the card shows event.price. The price field isn't on Event model directly,
                # so we skip price for now unless there's a field.
                # Actually, Event model doesn't have a price field. The card reads event.price
                # which might be a property or annotation. Let's skip price.

                # Assign category
                EventCategoryAssignment.objects.create(event=event, category=category)

                created_count += 1
                self.stdout.write(f'  Created: {edata["name"]} [{cat_name}] — {"past" if event_date < now else "future"}')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count} events, skipped {skipped_count} duplicates.'
        ))
