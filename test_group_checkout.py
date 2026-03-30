import os
import sys
import django

# Setup django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comrade.settings")
django.setup()

from Authentication.models import CustomUser
from Payment.models import PaymentGroups
from Payment.views import PaymentGroupsViewSet
from rest_framework.test import APIRequestFactory

user = CustomUser.objects.first()
group = PaymentGroups.objects.first()

factory = APIRequestFactory()
data = {
    "amount": 271.72,
    "items": [
        {"id": 1, "type": "product", "price": 39.31, "qty": 1, "name": "Ultimate Coding Resources"},
        {"id": 2, "type": "product", "price": 193.10, "qty": 1, "name": "Budget Travel Itineraries"}
    ]
}

request = factory.post(f'/api/payments/payment-groups/{group.id}/checkout/', data, format='json')
from rest_framework.request import Request
request.user = user

view = PaymentGroupsViewSet.as_view({'post': 'group_checkout'})
try:
    response = view(request, pk=group.id)
    print("Status code:", response.status_code)
    print("Response:", response.data)
except Exception as e:
    import traceback
    traceback.print_exc()
