import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import PaymentGroups, GroupCertificate

def check_integrity():
    print("Checking PaymentGroups...")
    for pg in PaymentGroups.objects.all():
        try:
            uuid.UUID(str(pg.id))
        except ValueError:
            print(f"Invalid UUID for PaymentGroup: {pg.id}")
            
    print("Checking GroupCertificate...")
    for gc in GroupCertificate.objects.all():
        try:
            uuid.UUID(str(gc.id))
        except ValueError:
            print(f"Invalid UUID for GroupCertificate ID: {gc.id}")
        
        try:
            # Check the foreign key to payment_group
            # If it's a OneToOneField, gc.payment_group_id should be a UUID
            if gc.payment_group_id:
                 uuid.UUID(str(gc.payment_group_id))
        except ValueError:
            print(f"Invalid UUID for GroupCertificate payment_group_id: {gc.payment_group_id} (GC ID: {gc.id})")

if __name__ == "__main__":
    check_integrity()
