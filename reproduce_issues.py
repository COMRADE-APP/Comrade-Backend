import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'comrade.settings')
django.setup()

from Payment.models import (
    PaymentGroups, PaymentGroupMember, PaymentProfile, 
    RoundContribution, RoundPosition, GroupPost, Donation,
    GroupInvestment
)
from Funding.models import Business
from Payment.serializers import DonationSerializer
from rest_framework.test import APIRequestFactory, force_authenticate
from Payment.views import (
    PaymentGroupsViewSet, DonationViewSet, GroupPostViewSet,
    GroupInvestmentViewSet, RoundPositionViewSet, RoundContributionViewSet,
    GroupBusinessViewSet
)
from rest_framework.response import Response

def test_endpoint(view_class, action, url, user, pk=None, query_params=None):
    print(f"\n--- Testing {view_class.__name__}.{action} at {url} ---")
    factory = APIRequestFactory()
    view = view_class.as_view({ 'get' if action != 'analytics' else 'get': action})
    
    if query_params:
        request = factory.get(url, query_params)
    else:
        request = factory.get(url)
        
    force_authenticate(request, user=user)
    
    try:
        if pk:
            response = view(request, pk=pk)
        else:
            response = view(request)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success!")
            # print(f"Data: {response.data}")
            if isinstance(response.data, list):
                print(f"Count: {len(response.data)}")
            elif isinstance(response.data, dict) and 'results' in response.data:
                print(f"Count (paginated): {len(response.data['results'])}")
        else:
            print(f"Error: {response.data}")
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Try to find a user who is a member of some groups
    member = PaymentGroupMember.objects.first()
    if not member:
        print("No group members found in DB.")
        return
    
    user = member.payment_profile.user.user
    group = member.payment_group
    
    print(f"Testing with User: {user.email} and Group: {group.name} (ID: {group.id})")
    
    # 1. My Groups
    test_endpoint(PaymentGroupsViewSet, 'my_groups', '/api/payments/groups/my_groups/', user)
    
    # 2. Analytics
    test_endpoint(PaymentGroupsViewSet, 'analytics', f'/api/payments/groups/{group.id}/analytics/', user, pk=group.id)
    
    # 3. Donations
    test_endpoint(DonationViewSet, 'list', '/api/payments/donations/', user, query_params={'payment_group': group.id})
    
    # 4. Discourse (GroupPost)
    test_endpoint(GroupPostViewSet, 'list', '/api/payments/posts/', user, query_params={'payment_group': group.id})
    
    # 5. Rounds (RoundContribution)
    test_endpoint(RoundContributionViewSet, 'list', '/api/payments/rounds/', user, query_params={'payment_group': group.id})
    
    # 6. GroupBusiness (Business)
    test_endpoint(GroupBusinessViewSet, 'list', '/api/payments/businesses/', user, query_params={'payment_group': group.id})

if __name__ == "__main__":
    main()
