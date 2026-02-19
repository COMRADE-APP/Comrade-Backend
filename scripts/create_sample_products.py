"""
Sample Products Data Script
Run this script to populate the database with sample products for the shop
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import Product

SAMPLE_PRODUCTS = [
    # Physical Products
    {
        'name': 'Qomrade Branded Notebook',
        'description': 'Premium quality notebook with the Qomrade logo. Perfect for taking notes during lectures.',
        'price': 12.99,
        'product_type': 'physical',
        'is_sharable': True,
    },
    {
        'name': 'Student Starter Kit',
        'description': 'Everything you need to start your academic journey - includes pen set, highlighters, and organizer.',
        'price': 29.99,
        'product_type': 'physical',
        'is_sharable': True,
    },
    {
        'name': 'Qomrade T-Shirt',
        'description': 'Comfortable cotton t-shirt with Qomrade branding. Available in multiple sizes.',
        'price': 24.99,
        'product_type': 'physical',
        'is_sharable': False,
    },
    
    # Digital Products
    {
        'name': 'Study Template Pack',
        'description': 'Collection of 50+ study templates including planners, schedulers, and note templates.',
        'price': 9.99,
        'product_type': 'digital',
        'is_sharable': True,
    },
    {
        'name': 'Academic Research Guide',
        'description': 'Comprehensive PDF guide on conducting academic research and writing papers.',
        'price': 14.99,
        'product_type': 'digital',
        'is_sharable': True,
    },
    
    # Services
    {
        'name': 'Resume Review Service',
        'description': 'Professional review and feedback on your resume by industry experts.',
        'price': 49.99,
        'product_type': 'service',
        'is_sharable': False,
    },
    {
        'name': 'Career Counseling Session',
        'description': '1-hour personalized career guidance session with an experienced counselor.',
        'price': 79.99,
        'product_type': 'service',
        'is_sharable': False,
    },
    
    # Subscriptions
    {
        'name': 'Premium Resources Access',
        'description': 'Unlimited access to all premium learning resources for 30 days.',
        'price': 19.99,
        'product_type': 'subscription',
        'requires_subscription': True,
        'duration_days': 30,
        'is_sharable': False,
    },
    {
        'name': 'Research Database Access',
        'description': 'Access to extensive research papers and academic journals.',
        'price': 29.99,
        'product_type': 'subscription',
        'requires_subscription': True,
        'duration_days': 30,
        'is_sharable': False,
    },
    {
        'name': 'Specialization Course Bundle',
        'description': 'Access to all specialization courses and certifications for a year.',
        'price': 199.99,
        'product_type': 'subscription',
        'requires_subscription': True,
        'duration_days': 365,
        'is_sharable': False,
    },
    
    # Recommendations
    {
        'name': 'Recommended: Study Lamp',
        'description': 'Ergonomic LED study lamp with adjustable brightness. Perfect for late-night study sessions.',
        'price': 34.99,
        'product_type': 'recommendation',
        'is_sharable': True,
    },
    {
        'name': 'Recommended: Noise-Canceling Headphones',
        'description': 'High-quality wireless headphones for focused study sessions.',
        'price': 89.99,
        'product_type': 'recommendation',
        'is_sharable': True,
    },
    {
        'name': 'Recommended: Ergonomic Chair',
        'description': 'Comfortable study chair with lumbar support for long study sessions.',
        'price': 149.99,
        'product_type': 'recommendation',
        'is_sharable': True,
    },
]


def create_sample_products():
    """Create sample products in the database"""
    created_count = 0
    updated_count = 0
    
    for product_data in SAMPLE_PRODUCTS:
        product, created = Product.objects.update_or_create(
            name=product_data['name'],
            defaults=product_data
        )
        
        if created:
            created_count += 1
            print(f"Created: {product.name}")
        else:
            updated_count += 1
            print(f"Updated: {product.name}")
    
    print(f"\n✓ {created_count} products created, {updated_count} products updated")
    print(f"Total products in database: {Product.objects.count()}")


if __name__ == '__main__':
    print("Creating sample products...\n")
    create_sample_products()
