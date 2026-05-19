import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import Product

for p in Product.objects.filter(product_type='recommendation'):
    print(f"Name: {p.name} | Image URL: {p.image_url}")
