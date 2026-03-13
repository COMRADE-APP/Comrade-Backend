import os
import random
import urllib.request
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from Payment.models import Product

class Command(BaseCommand):
    help = 'Populates the DB with 6 products for each category with pictures'

    def handle(self, *args, **options):
        categories = {
            'physical': [
                "Wireless Noise-Canceling Headphones",
                "Ergonomic Office Chair",
                "Mechanical Gaming Keyboard",
                "Stainless Steel Water Bottle",
                "Yoga Mat with Alignment Lines",
                "Smart Fitness Watch"
            ],
            'digital': [
                "UI/UX Design Masterclass (Video)",
                "Complete Web Development E-Book",
                "Business Proposal Template Pack",
                "Digital Marketing Checklists",
                "Stock Photography Bundle",
                "Premium Lightroom Presets"
            ],
            'service': [
                "1-on-1 Career Coaching",
                "Resume Review Service",
                "Personalized Fitness Plan",
                "Graphic Design Consultation",
                "Tax Preparation Service",
                "Language Translation Service"
            ],
            'subscription': [
                "Pro Tools Monthly Access",
                "Premium Content Newsletter",
                "Online Library Membership",
                "Design Assets Subscription",
                "Weekly Meal Plan Delivery",
                "Cloud Storage 1TB Plan"
            ],
            'recommendation': [
                "Must-Read Tech Books 2026",
                "Top Productivity Apps Setup",
                "Best Podcasting Microphones",
                "Home Office Setup Guide",
                "Budget Travel Itineraries",
                "Ultimate Coding Resources"
            ]
        }

        # Ensure media directory exists
        media_dir = os.path.join(settings.MEDIA_ROOT, 'products')
        os.makedirs(media_dir, exist_ok=True)

        for cat, products in categories.items():
            self.stdout.write(f"Processing category: {cat}")
            for i, p_name in enumerate(products):
                seed = f"{cat}{i}"
                img_url = f"https://picsum.photos/seed/{seed}/800/600"
                file_name = f"{seed}.jpg"
                file_path = os.path.join(media_dir, file_name)
                
                if not os.path.exists(file_path):
                    self.stdout.write(f"  Downloading image for {p_name}...")
                    try:
                        req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response, open(file_path, 'wb') as out_file:
                            out_file.write(response.read())
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Failed to download image: {e}"))
                        # Just use the URL directly if download fails
                        pass

                price = Decimal(str(round(random.uniform(10.0, 200.0), 2)))
                description = f"This is a premium {cat} item: {p_name}. Highly recommended for all members."
                
                # Check if file was actually downloaded to form correct image_url
                if os.path.exists(file_path):
                    final_image_url = f"/media/products/{file_name}"
                else:
                    final_image_url = img_url

                product, created = Product.objects.update_or_create(
                    name=p_name,
                    product_type=cat,
                    defaults={
                        'description': description,
                        'price': price,
                        'image_url': final_image_url,
                        'is_sharable': True,
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  Created: {p_name}"))
                else:
                    self.stdout.write(f"  Updated: {p_name}")

        self.stdout.write(self.style.SUCCESS('Successfully populated shop products!'))
