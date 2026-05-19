import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import Product

with open("scratch_out.txt", "w") as f:
    f.write("--- Products ---\n")
    for p in Product.objects.all():
        f.write(f"Name: {p.name} | Type: {p.product_type} | Price: {p.price}\n")
