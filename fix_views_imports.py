
import os

file_path = r'C:\Users\Imani\Documents\Comrade\Comrade-Backend\Payment\views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add missing imports
imports = [
    "from django.shortcuts import render, get_object_or_404\n",
    "import math\n",
    "from Payment.utils import get_or_create_payment_profile\n"
]

for imp in reversed(imports):
    if imp.strip() not in content:
        content = imp + content

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("All missing imports in views.py added!")
