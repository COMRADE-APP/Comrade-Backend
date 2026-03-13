import os
import random
import urllib.request
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from Authentication.models import CustomUser, Profile
from Payment.models import Establishment, MenuItem, HotelRoom, ServiceOffering

class Command(BaseCommand):
    help = 'Populates the DB with Establishments, Menus, Hotels, and Services'

    def download_image(self, url, folder, filename):
        media_dir = os.path.join(settings.MEDIA_ROOT, folder)
        os.makedirs(media_dir, exist_ok=True)
        file_path = os.path.join(media_dir, filename)
        
        if not os.path.exists(file_path):
            self.stdout.write(f"  Downloading image for {filename}...")
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
                    out_file.write(response.read())
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Failed to download image: {e}"))
        
        if os.path.exists(file_path):
            return f"/{folder}/{filename}"
        return url

    def handle(self, *args, **options):
        # Ensure we have a profile to own these establishments
        user = CustomUser.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(self.style.ERROR("No active user found to own establishments. Please create one first."))
            return
        profile, created = Profile.objects.get_or_create(user=user)

        establishments_data = [
            {
                'type': 'restaurant',
                'name': 'The Great Feast',
                'description': 'A fine dining restaurant offering the best culinary experience.',
                'items': [
                    {'name': 'Grilled Salmon', 'price': '25.99', 'cat': 'Main Course'},
                    {'name': 'Caesar Salad', 'price': '12.50', 'cat': 'Appetizers'},
                    {'name': 'Beef Steak', 'price': '35.00', 'cat': 'Main Course'},
                    {'name': 'Cheesecake', 'price': '8.50', 'cat': 'Desserts'},
                    {'name': 'Margarita Pizza', 'price': '15.00', 'cat': 'Main Course'},
                    {'name': 'Red Wine Glass', 'price': '10.00', 'cat': 'Beverages'}
                ]
            },
            {
                'type': 'hotel',
                'name': 'Grand Horizon Hotel',
                'description': 'Luxury stay with ocean views and premium amenities.',
                'items': [
                    {'name': 'Ocean View Suite', 'price': '250.00', 'type': 'suite'},
                    {'name': 'Deluxe King Room', 'price': '150.00', 'type': 'deluxe'},
                    {'name': 'Standard Double', 'price': '100.00', 'type': 'standard'},
                    {'name': 'Presidential Suite', 'price': '500.00', 'type': 'suite'},
                    {'name': 'Grand Conference Room', 'price': '800.00', 'type': 'conference_room'},
                    {'name': 'Garden Event Room', 'price': '600.00', 'type': 'event_room'}
                ]
            },
            {
                'type': 'supermarket',
                'name': 'Fresh Mart Daily',
                'description': 'Your everyday grocery needs in one place.',
                'items': [
                    {'name': 'Organic Bananas (1kg)', 'price': '3.99', 'cat': 'Produce'},
                    {'name': 'Whole Milk (1L)', 'price': '2.50', 'cat': 'Dairy'},
                    {'name': 'Artisan Bread', 'price': '4.00', 'cat': 'Bakery'},
                    {'name': 'Free Range Eggs (12)', 'price': '5.50', 'cat': 'Dairy'},
                    {'name': 'Roasted Coffee Beans', 'price': '12.99', 'cat': 'Pantry'},
                    {'name': 'Laundry Detergent', 'price': '15.00', 'cat': 'Household'}
                ]
            },
            {
                'type': 'service_provider',
                'name': 'Elite Home Services',
                'description': 'Professional cleaning, plumbing, and electrical services.',
                'items': [
                    {'name': 'Deep House Cleaning', 'price': '150.00', 'cat': 'Cleaning'},
                    {'name': 'Plumbing Repair', 'price': '80.00', 'cat': 'Plumbing'},
                    {'name': 'Electrical Maintenance', 'price': '90.00', 'cat': 'Electrical'},
                    {'name': 'AC Servicing', 'price': '120.00', 'cat': 'HVAC'},
                    {'name': 'Carpentry Work', 'price': '100.00', 'cat': 'Carpentry'},
                    {'name': 'Pest Control', 'price': '200.00', 'cat': 'Maintenance'}
                ]
            }
        ]

        for est_data in establishments_data:
            est_type = est_data['type']
            est_name = est_data['name']
            self.stdout.write(f"\nProcessing {est_type}: {est_name}")

            # Download logo and banner
            slug = est_name.lower().replace(' ', '-')
            logo_url = self.download_image(f"https://picsum.photos/seed/{slug}_logo/200/200", 'establishments/logos', f"{slug}_logo.jpg")
            banner_url = self.download_image(f"https://picsum.photos/seed/{slug}_banner/1200/400", 'establishments/banners', f"{slug}_banner.jpg")

            establishment, created = Establishment.objects.update_or_create(
                slug=slug,
                defaults={
                    'owner': profile,
                    'name': est_name,
                    'description': est_data['description'],
                    'establishment_type': est_type,
                    'city': 'Metropolis',
                    'country': 'Wonderland',
                    'is_verified': True,
                    'is_active': True,
                    'rating': Decimal('4.5'),
                    'review_count': 120,
                    'logo': logo_url,
                    'banner': banner_url
                }
            )

            # Create items
            for i, item in enumerate(est_data['items']):
                item_name = item['name']
                item_slug = item_name.lower().replace(' ', '-')
                
                if est_type in ['restaurant', 'supermarket']:
                    img_url = self.download_image(f"https://picsum.photos/seed/{item_slug}/600/400", 'menu_items', f"{item_slug}.jpg")
                    MenuItem.objects.update_or_create(
                        establishment=establishment,
                        name=item_name,
                        defaults={
                            'description': f"Delicious {item_name}.",
                            'price': Decimal(item['price']),
                            'category': item['cat'],
                            'image': img_url,
                            'is_available': True
                        }
                    )
                elif est_type == 'hotel':
                    img_url = self.download_image(f"https://picsum.photos/seed/{item_slug}/800/600", 'hotel_rooms', f"{item_slug}.jpg")
                    HotelRoom.objects.update_or_create(
                        establishment=establishment,
                        name=item_name,
                        defaults={
                            'room_type': item['type'],
                            'description': f"Beautiful {item_name} with great views.",
                            'price_per_night': Decimal(item['price']),
                            'images': [img_url, img_url], # HotelRoom uses JSONField images
                            'is_available': True
                        }
                    )
                elif est_type == 'service_provider':
                    img_url = self.download_image(f"https://picsum.photos/seed/{item_slug}/600/400", 'services', f"{item_slug}.jpg")
                    ServiceOffering.objects.update_or_create(
                        provider=profile,
                        name=item_name,
                        defaults={
                            'establishment': establishment,
                            'description': f"Top notch {item_name} service.",
                            'price': Decimal(item['price']),
                            'category': item['cat'],
                            'image': img_url,
                            'is_active': True
                        }
                    )
                
                self.stdout.write(f"  Created item: {item_name}")

        self.stdout.write(self.style.SUCCESS('\nSuccessfully populated Establishments and their items!'))
