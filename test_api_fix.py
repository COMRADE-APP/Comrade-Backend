import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Authentication.models import CustomUser
from Payment.views import PaymentGroupsViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

def test_my_groups_endpoint():
    try:
        user = CustomUser.objects.get(id=1)
        factory = APIRequestFactory()
        view = PaymentGroupsViewSet.as_view({'get': 'my_groups'})
        
        request = factory.get('/api/payments/groups/my_groups/')
        force_authenticate(request, user=user)
        
        response = view(request)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Data serialized correctly.")
            # print(response.data)
        else:
            print(f"Error Response: {response.data}")
    except Exception as e:
        print(f"Crashed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_my_groups_endpoint()
