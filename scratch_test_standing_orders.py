import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import force_authenticate
from Authentication.models import CustomUser
from Payment.views import BillStandingOrderViewSet
from Payment.models import UserServiceProvider

rf = RequestFactory()
user = CustomUser.objects.filter(is_active=True).first()

# Create or fetch a UserServiceProvider for this user's profile
from Specialization.models import Profile
profile = Profile.objects.filter(user=user).first()
provider = UserServiceProvider.objects.filter(user=profile).first()
if not provider:
    provider = UserServiceProvider.objects.create(
        user=profile,
        name="TEST: Product",
        category="other",
        account_number="12345",
        destination_account="12345",
        destination_type="internal_wallet"
    )

print("--- TESTING POST STANDING-ORDERS ---")
req = rf.post('/api/payments/standing-orders/', {
    'provider': provider.id,
    'amount': 20.00,
    'frequency': 'monthly',
    'start_date': '2026-05-18'
}, format='json')

if user:
    force_authenticate(req, user=user)

view = BillStandingOrderViewSet.as_view({'post': 'create'})
res = view(req)
print(f"Status: {res.status_code}")
data = res.data if hasattr(res, 'data') else None
print(f"Response: {data}")
