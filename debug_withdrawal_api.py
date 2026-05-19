import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comrade.settings")
django.setup()

from Payment.models import WithdrawalRequest, PaymentProfile
from Payment.views import WithdrawalRequestViewSet
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import User

try:
    req = WithdrawalRequest.objects.filter(status='pending').last()
    if not req:
        print("No pending withdrawal requests")
    else:
        print(f"Request ID: {req.id}, Status: {req.status}, Amount: {req.amount}")
        
        admin_profile = req.payment_group.creator
        admin_user = admin_profile.user.user
        
        factory = APIRequestFactory()
        request = factory.post(f'/api/payments/withdrawal-requests/{req.id}/approve/')
        from rest_framework.request import Request
        request.user = admin_user
        
        view = WithdrawalRequestViewSet.as_view({'post': 'approve'})
        response = view(request, pk=req.id)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Data: {response.data}")

except Exception as e:
    import traceback
    traceback.print_exc()
