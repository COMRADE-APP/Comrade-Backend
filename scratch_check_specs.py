import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Specialization.models import Specialization, Stack

with open("scratch_out_specs.txt", "w") as f:
    f.write("--- Specializations ---\n")
    for s in Specialization.objects.all():
        f.write(f"Name: {s.name} | Type: {s.learning_type} | Is Paid: {s.is_paid} | Price: {s.price} | Stacks Count: {s.stacks.count()}\n")
        for st in s.stacks.all():
            f.write(f"  -> Stack Name: {st.name}\n")
            
    f.write("\n--- Stacks ---\n")
    for st in Stack.objects.all():
        f.write(f"Stack Name: {st.name} | Associated specs: {[s.name for s in st.specialization_stacks.all()]}\n")
