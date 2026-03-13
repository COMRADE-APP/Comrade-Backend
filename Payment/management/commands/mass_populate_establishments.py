import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from Authentication.models import CustomUser, Profile
from Payment.models import Establishment, MenuItem, HotelRoom, ServiceOffering

class Command(BaseCommand):
    help = 'Populates the DB with 100+ Establishments, Menus, Hotels, and Services'

    def handle(self, *args, **options):
        # We'll use loremflickr to seed images quickly and accurately without downloading
        # The frontend supports external URLs directly.
        
        user = CustomUser.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(self.style.ERROR("No active user found. Cannot proceed."))
            return
        profile, created = Profile.objects.get_or_create(user=user)

        # Generative data sets
        restaurant_names = ["The Golden Fork", "Bella Italia", "Spice Garden", "Ocean Breeze Seafood", "Urban Grill", "Sushi Master", "Taco Fiesta", "Vegan Delight", "Steak & Co", "The Rustic Spoon", "Noodle House", "Bistro 33", "Cafe Latte", "Dim Sum Go", "Pancake Heaven", "Mamma Mia's", "Royal Curry", "The Burger Joint", "Green Bowl", "Miso & Maki", "Street Food Central", "Firewood Pizza", "The Breakfast Club", "Crepe Corner", "Seaside Dining"]
        hotel_names = ["Grand Horizon Hotel", "Oceanview Resort", "The Royal Palace", "City Center Inn", "Mountain Retreat", "Sunset Boulevard Hotel", "Emerald Suites", "Sapphire Lodge", "Golden Tulip", "Silver Sands Resort", "The Imperial Stay", "Cosmic Towers", "Urban Stay Hotel", "The Boutique Inn", "Lakefront Resort", "Palm Tree Paradise", "The Heritage Hotel", "Skyline Views", "Riverside Cabins", "Oasis Springs", "Desert Rose Inn", "Alpine Ski Resort", "The Platinum Hotel", "Crystal Waters", "Tranquil Nights Hotel"]
        supermarket_names = ["Fresh Mart Daily", "City Superstore", "Green Grocers", "Mega Value Market", "The Daily Needs", "Sunrise Supermarket", "Prime Foods", "Choice Market", "Organic Wholefoods", "Corner Store Plus", "Family Groceries", "Express Mart", "Farm To Table", "Global Foods", "Budget Supermarket", "Quality Provisions", "The Deli Shop", "Fresh Produce Hub", "Neighborhood Grocer", "Village Market", "Pantry Essentials", "Sav-A-Lot", "Gourmet Selections", "Value King", "Smart Shopper"]
        service_names = ["Elite Home Services", "Pro Plumbing Solutions", "QuickFix Electric", "Prime Cleaners", "Green Thumb Gardening", "Master Tutors", "Sparkle Maid Services", "A1 Auto Repair", "Trusty Handyman", "Tech Support Pros", "Smooth Moves Relocation", "Crystal Clear Windows", "Pest Control Ninjas", "Flawless Painting", "Safe Guard Security", "Rapid Courier", "Smart Fit Personal Training", "Yoga Zen Studio", "Creative Design Agency", "Legal Aid Consult", "Tax Experts Hub", "Language Masters", "Event Planners Inc", "Catering Delights", "Pet Groomers Extravaganza", "Home Spa Mobile", "Mobile Car Wash", "Roofing Specialists", "Paving & Driveways", "AC Servicing Masters"]

        # 25 + 25 + 25 + 30 = 105 establishments

        total_establishments = 0
        total_items = 0

        # Restaurant Logic
        for i, r_name in enumerate(restaurant_names):
            slug = f"rest-{i}-{r_name.lower().replace(' ', '-')[:20]}"
            logo_url = f"https://loremflickr.com/200/200/restaurant,food?lock={i+100}"
            banner_url = f"https://loremflickr.com/1200/400/restaurant?lock={i+100}"
            
            est, _ = Establishment.objects.update_or_create(
                slug=slug,
                defaults={
                    'owner': profile,
                    'name': r_name,
                    'description': f"Welcome to {r_name}, providing the best culinary experiences and top-quality food for our beloved customers.",
                    'establishment_type': 'restaurant',
                    'city': 'Metropolis',
                    'country': 'US',
                    'is_verified': True,
                    'is_active': True,
                    'rating': Decimal(str(round(random.uniform(3.5, 5.0), 1))),
                    'review_count': random.randint(10, 500),
                    'logo': logo_url,
                    'banner': banner_url
                }
            )
            total_establishments += 1
            
            # Generate 5-8 menu items
            menu_cats = ['Appetizers', 'Main Course', 'Desserts', 'Beverages']
            for j in range(random.randint(5, 8)):
                m_name = f"Delicious Dish {j+1}"
                cat = random.choice(menu_cats)
                keyword = "pizza" if "Main" in cat else "salad" if "Appetizer" in cat else "cake" if "Dessert" in cat else "drink"
                img_url = f"https://loremflickr.com/400/400/{keyword}?lock={i*10 + j}"
                
                MenuItem.objects.update_or_create(
                    establishment=est,
                    name=f"Signature {cat[:-1]} {j+1}",
                    defaults={
                        'description': f"A mouth-watering {cat.lower()[:-1]} specially prepared by our head chef.",
                        'price': Decimal(str(round(random.uniform(5.0, 45.0), 2))),
                        'category': cat,
                        'image': img_url,
                        'is_available': True
                    }
                )
                total_items += 1

        # Hotel Logic
        for i, h_name in enumerate(hotel_names):
            slug = f"hotl-{i}-{h_name.lower().replace(' ', '-')[:20]}"
            logo_url = f"https://loremflickr.com/200/200/hotel,logo?lock={i+200}"
            banner_url = f"https://loremflickr.com/1200/400/hotel?lock={i+200}"
            
            est, _ = Establishment.objects.update_or_create(
                slug=slug,
                defaults={
                    'owner': profile,
                    'name': h_name,
                    'description': f"Stay at {h_name} for unparalleled luxury, comfort, and service that treats you like royalty.",
                    'establishment_type': 'hotel',
                    'city': 'Metropolis',
                    'country': 'US',
                    'is_verified': True,
                    'is_active': True,
                    'rating': Decimal(str(round(random.uniform(3.8, 5.0), 1))),
                    'review_count': random.randint(20, 1000),
                    'logo': logo_url,
                    'banner': banner_url
                }
            )
            total_establishments += 1
            
            rooms_list = [
                ('Standard Room', 'standard', 100, 2),
                ('Deluxe King', 'deluxe', 200, 2),
                ('Luxury Suite', 'suite', 450, 4),
                ('Executive Event Room', 'event_room', 800, 100),
                ('Grand Conference', 'conference_room', 1200, 300)
            ]
            for j in range(random.randint(3, 5)):
                r_name, r_type, base_price, cap = rooms_list[j]
                img_url = f"https://loremflickr.com/600/400/bedroom,hotel?lock={i*10 + j}"
                HotelRoom.objects.update_or_create(
                    establishment=est,
                    name=r_name,
                    defaults={
                        'room_type': r_type,
                        'description': f"Experience the finest stay in our {r_name}. Fully equipped with premium amenities.",
                        'price_per_night': Decimal(str(base_price + random.randint(-20, 50))),
                        'capacity': cap,
                        'images': [img_url, img_url],
                        'is_available': True
                    }
                )
                total_items += 1

        # Supermarket Logic
        for i, s_name in enumerate(supermarket_names):
            slug = f"supr-{i}-{s_name.lower().replace(' ', '-')[:20]}"
            logo_url = f"https://loremflickr.com/200/200/supermarket,logo?lock={i+300}"
            banner_url = f"https://loremflickr.com/1200/400/supermarket?lock={i+300}"
            
            est, _ = Establishment.objects.update_or_create(
                slug=slug,
                defaults={
                    'owner': profile,
                    'name': s_name,
                    'description': f"From fresh produce to daily household essentials, {s_name} has it all at unbeatable prices.",
                    'establishment_type': 'supermarket',
                    'city': 'Metropolis',
                    'country': 'US',
                    'is_verified': True,
                    'is_active': True,
                    'rating': Decimal(str(round(random.uniform(3.5, 4.8), 1))),
                    'review_count': random.randint(5, 300),
                    'logo': logo_url,
                    'banner': banner_url
                }
            )
            total_establishments += 1
            
            prod_cats = ['Produce', 'Dairy', 'Bakery', 'Household']
            for j in range(random.randint(6, 10)):
                cat = random.choice(prod_cats)
                keyword = "vegetables" if "Produce" in cat else "milk" if "Dairy" in cat else "bread" if "Bakery" in cat else "cleaning"
                img_url = f"https://loremflickr.com/400/400/{keyword}?lock={i*10 + j}"
                
                MenuItem.objects.update_or_create(
                    establishment=est,
                    name=f"Premium {cat} Item {j+1}",
                    defaults={
                        'description': f"High quality {cat.lower()} product freshly stocked in our aisles.",
                        'price': Decimal(str(round(random.uniform(2.0, 25.0), 2))),
                        'category': cat,
                        'image': img_url,
                        'is_available': True
                    }
                )
                total_items += 1

        # Service Provider Logic
        for i, sp_name in enumerate(service_names):
            slug = f"serv-{i}-{sp_name.lower().replace(' ', '-')[:20]}"
            logo_url = f"https://loremflickr.com/200/200/business,logo?lock={i+400}"
            banner_url = f"https://loremflickr.com/1200/400/office?lock={i+400}"
            
            est, _ = Establishment.objects.update_or_create(
                slug=slug,
                defaults={
                    'owner': profile,
                    'name': sp_name,
                    'description': f"{sp_name} delivers reliable, professional, and efficient services to meet your every need.",
                    'establishment_type': 'service_provider',
                    'city': 'Metropolis',
                    'country': 'US',
                    'is_verified': True,
                    'is_active': True,
                    'rating': Decimal(str(round(random.uniform(4.0, 5.0), 1))),
                    'review_count': random.randint(15, 200),
                    'logo': logo_url,
                    'banner': banner_url
                }
            )
            total_establishments += 1
            
            for j in range(random.randint(3, 6)):
                img_url = f"https://loremflickr.com/400/400/work,service?lock={i*10 + j}"
                ServiceOffering.objects.update_or_create(
                    provider=profile,
                    name=f"Standard Service {j+1}",
                    defaults={
                        'establishment': est,
                        'description': f"A comprehensive service package handled by our certified professionals.",
                        'price': Decimal(str(round(random.uniform(30.0, 300.0), 2))),
                        'category': 'General Service',
                        'image': img_url,
                        'is_active': True
                    }
                )
                total_items += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully populated {total_establishments} Establishments and {total_items} items/services!'))
