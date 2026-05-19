import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import force_authenticate
from Authentication.models import CustomUser
from Payment.views import ProductViewSet, GroupTargetViewSet

rf = RequestFactory()
user = CustomUser.objects.filter(is_active=True).first()

print("--- TESTING SEARCH AUTOMATION TARGETS (COURSE) ---")
req = rf.get('/api/payments/targets/search_automation_targets/', {'type': 'course', 'q': ''})
if user:
    force_authenticate(req, user=user)

view = GroupTargetViewSet.as_view({'get': 'search_automation_targets'})
res = view(req)
print(f"Status: {res.status_code}")
data = res.data if hasattr(res, 'data') else None
if data:
    courses = data.get('courses', [])
    print(f"Returned {len(courses)} courses:")
    for c in courses:
        print(f"  - [{c.get('type')}] {c.get('name')} | Price: {c.get('price')} | Image: {c.get('image')}")
else:
    print("No data returned!")

print("\n--- TESTING RECOMMENDATIONS ENDPOINT ---")
req_rec = rf.get('/api/payments/products/recommendations/')
if user:
    force_authenticate(req_rec, user=user)

view_rec = ProductViewSet.as_view({'get': 'recommendations'})
res_rec = view_rec(req_rec)
print(f"Status: {res_rec.status_code}")
data_rec = res_rec.data if hasattr(res_rec, 'data') else None
if isinstance(data_rec, list):
    print(f"Returned {len(data_rec)} recommended products:")
    for p in data_rec[:5]:
        print(f"  - {p.get('name')} | Type: {p.get('product_type')} | Price: {p.get('price')}")
else:
    print(f"Returned non-list data: {data_rec}")
