"""
Management command to populate the shop with sample products.
"""
from django.core.management.base import BaseCommand
from Payment.models import Product


PRODUCTS = [
    {
        'name': 'ProSound Wireless Headphones',
        'description': 'Premium noise-cancelling wireless headphones with 40-hour battery life, Hi-Res Audio, and ultra-soft memory foam ear cushions. Perfect for studying and music.',
        'price': 89.99,
        'product_type': 'physical',
        'is_sharable': False,
        'allow_group_purchase': True,
        'requires_subscription': False,
        'image_url': '/media/products/wireless_headphones.png',
    },
    {
        'name': 'Academic E-Book Bundle',
        'description': 'Curated collection of 25+ digital textbooks covering programming, data science, and business management. Lifetime access with regular updates.',
        'price': 49.99,
        'product_type': 'digital',
        'is_sharable': True,
        'allow_group_purchase': True,
        'requires_subscription': False,
        'image_url': '/media/products/ebook_bundle.png',
    },
    {
        'name': 'LumiDesk LED Study Lamp',
        'description': 'Adjustable LED desk lamp with 5 brightness levels and 3 color temperatures. USB charging port built-in. Eye-care technology reduces fatigue.',
        'price': 34.99,
        'product_type': 'physical',
        'is_sharable': False,
        'allow_group_purchase': True,
        'requires_subscription': False,
        'image_url': '/media/products/study_desk_lamp.png',
    },
    {
        'name': 'Qomrade Pro Learning Subscription',
        'description': 'Unlimited access to premium courses, live workshops, exclusive mentorship sessions, and certification programs. Learn at your own pace.',
        'price': 19.99,
        'product_type': 'subscription',
        'is_sharable': True,
        'allow_group_purchase': True,
        'requires_subscription': True,
        'duration_days': 30,
        'image_url': '/media/products/online_course.png',
    },
    {
        'name': 'Campus Classic Hoodie',
        'description': 'Premium heavyweight cotton-blend hoodie with embroidered university crest. Available in navy, charcoal, and forest green. Unisex fit.',
        'price': 45.00,
        'product_type': 'physical',
        'is_sharable': False,
        'allow_group_purchase': False,
        'requires_subscription': False,
        'image_url': '/media/products/campus_hoodie.png',
    },
    {
        'name': 'SlimGuard Laptop Sleeve',
        'description': 'Water-resistant neoprene laptop sleeve fits 13-15" devices. Scratch-proof interior lining, magnetic closure, and front accessory pocket.',
        'price': 24.99,
        'product_type': 'physical',
        'is_sharable': False,
        'allow_group_purchase': True,
        'requires_subscription': False,
        'image_url': '/media/products/laptop_sleeve.png',
    },
]


class Command(BaseCommand):
    help = 'Populate the shop with sample products and images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing products before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted_count, _ = Product.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted_count} existing products.'))

        created_count = 0
        for product_data in PRODUCTS:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {product.name} (${product.price})'))
            else:
                # Update existing product with new data
                for key, value in product_data.items():
                    setattr(product, key, value)
                product.save()
                self.stdout.write(self.style.NOTICE(f'  Updated: {product.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! {created_count} new products created, {len(PRODUCTS) - created_count} updated.'
        ))
