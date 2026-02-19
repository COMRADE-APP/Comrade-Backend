from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from decimal import Decimal
from Payment.models import PaymentProfile, PaymentGroups, PaymentGroupMember, GroupInvitation

User = get_user_model()


class PaymentGroupBaseTestCase(TestCase):
    """Base class with shared setup for payment group tests"""
    
    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(
            email='admin@test.com', password='testpass123',
            first_name='Admin', last_name='User'
        )
        self.user2 = User.objects.create_user(
            email='member@test.com', password='testpass123',
            first_name='Member', last_name='User'
        )
        self.user3 = User.objects.create_user(
            email='other@test.com', password='testpass123',
            first_name='Other', last_name='User'
        )
        
        # Create payment profiles using the same helper the views use
        from Payment.utils import get_or_create_payment_profile
        self.profile1 = get_or_create_payment_profile(self.user1)
        self.profile1.comrade_balance = Decimal('1000.00')
        self.profile1.save()
        
        self.profile2 = get_or_create_payment_profile(self.user2)
        self.profile2.comrade_balance = Decimal('500.00')
        self.profile2.save()
        
        self.profile3 = get_or_create_payment_profile(self.user3)
        self.profile3.comrade_balance = Decimal('200.00')
        self.profile3.save()
        
        # Create a group
        self.group = PaymentGroups.objects.create(
            name='Test Group',
            description='A test payment group',
            creator=self.profile1,
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('0.00'),
            max_capacity=10,
            deadline=timezone.now() + timedelta(days=30),
            expiry_date=timezone.now() + timedelta(days=30),
        )
        
        # Add creator as admin member
        PaymentGroupMember.objects.create(
            payment_group=self.group,
            payment_profile=self.profile1,
            is_admin=True,
        )
        
        # API clients
        self.client1 = APIClient()
        self.client1.force_authenticate(user=self.user1)
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)
        self.client3 = APIClient()
        self.client3.force_authenticate(user=self.user3)


class PaymentGroupCreationTests(PaymentGroupBaseTestCase):
    """Tests for payment group creation and basic operations"""
    
    def test_group_created_successfully(self):
        """Group should be created with correct defaults"""
        self.assertEqual(self.group.name, 'Test Group')
        self.assertTrue(self.group.is_active)
        self.assertFalse(self.group.is_matured)
        self.assertFalse(self.group.is_terminated)
        self.assertEqual(self.group.current_amount, Decimal('0.00'))
    
    def test_list_groups(self):
        """Authenticated user should be able to list groups"""
        resp = self.client1.get('/api/payments/groups/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
    
    def test_get_group_detail(self):
        """Should retrieve group details"""
        resp = self.client1.get(f'/api/payments/groups/{self.group.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['name'], 'Test Group')


class PaymentGroupContributionTests(PaymentGroupBaseTestCase):
    """Tests for contribution functionality with multiple payment methods"""
    
    def setUp(self):
        super().setUp()
        # Add user2 as member
        PaymentGroupMember.objects.create(
            payment_group=self.group,
            payment_profile=self.profile2,
            is_admin=False,
        )
    
    def test_wallet_contribution_success(self):
        """Wallet contribution should deduct balance and increase group amount"""
        resp = self.client2.post(
            f'/api/payments/groups/{self.group.id}/contribute/',
            {'amount': '100.00', 'payment_method': 'wallet'}
        )
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.group.refresh_from_db()
        self.profile2.refresh_from_db()
        self.assertEqual(self.group.current_amount, Decimal('100.00'))
        self.assertEqual(self.profile2.comrade_balance, Decimal('400.00'))
    
    def test_wallet_contribution_insufficient_balance(self):
        """Should reject contribution when balance is insufficient"""
        resp = self.client2.post(
            f'/api/payments/groups/{self.group.id}/contribute/',
            {'amount': '999999.00', 'payment_method': 'wallet'}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', resp.data)
    
    def test_mpesa_contribution_requires_phone(self):
        """M-Pesa contribution should require a phone number"""
        resp = self.client2.post(
            f'/api/payments/groups/{self.group.id}/contribute/',
            {'amount': '50.00', 'payment_method': 'mpesa'}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_unsupported_payment_method(self):
        """Should reject unsupported payment methods"""
        resp = self.client2.post(
            f'/api/payments/groups/{self.group.id}/contribute/',
            {'amount': '50.00', 'payment_method': 'bitcoin'}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_non_member_cannot_contribute(self):
        """Non-members should not be able to contribute"""
        resp = self.client3.post(
            f'/api/payments/groups/{self.group.id}/contribute/',
            {'amount': '50.00', 'payment_method': 'wallet'}
        )
        self.assertIn(resp.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])


class PaymentGroupInvitationTests(PaymentGroupBaseTestCase):
    """Tests for invitation flow: invite, accept, reject"""
    
    def test_invite_existing_user(self):
        """Should send invitation to an existing user"""
        resp = self.client1.post(
            f'/api/payments/groups/{self.group.id}/invite/',
            {'email': 'member@test.com'}
        )
        self.assertIn(resp.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
    
    def test_invite_nonexistent_user_requires_confirmation(self):
        """Inviting a non-existent user should prompt for confirmation"""
        resp = self.client1.post(
            f'/api/payments/groups/{self.group.id}/invite/',
            {'email': 'nonexistent@test.com'}
        )
        # Should either succeed or ask for confirmation
        self.assertIn(resp.status_code, [
            status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_404_NOT_FOUND
        ])
    
    def test_accept_invitation(self):
        """Accepting an invitation should add user to group"""
        invitation = GroupInvitation.objects.create(
            payment_group=self.group,
            invited_profile=self.profile2,
            invited_by=self.profile1,
            invited_email='member@test.com',
            status='pending',
            expires_at=timezone.now() + timedelta(days=7),
        )
        resp = self.client2.post(
            f'/api/payments/invitations/{invitation.id}/accept/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'accepted')
        # User should now be a member
        self.assertTrue(
            PaymentGroupMember.objects.filter(
                payment_group=self.group, payment_profile=self.profile2
            ).exists()
        )
    
    def test_reject_invitation(self):
        """Rejecting an invitation should update status"""
        invitation = GroupInvitation.objects.create(
            payment_group=self.group,
            invited_profile=self.profile2,
            invited_by=self.profile1,
            invited_email='member@test.com',
            status='pending',
            expires_at=timezone.now() + timedelta(days=7),
        )
        resp = self.client2.post(
            f'/api/payments/invitations/{invitation.id}/reject/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, 'rejected')
    
    def test_expired_invitation_cannot_be_accepted(self):
        """Expired invitations should fail acceptance"""
        invitation = GroupInvitation.objects.create(
            payment_group=self.group,
            invited_profile=self.profile2,
            invited_by=self.profile1,
            invited_email='member@test.com',
            status='pending',
            expires_at=timezone.now() - timedelta(days=1),
        )
        resp = self.client2.post(
            f'/api/payments/invitations/{invitation.id}/accept/'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_list_pending_invitations(self):
        """Should list pending invitations for the current user"""
        GroupInvitation.objects.create(
            payment_group=self.group,
            invited_profile=self.profile2,
            invited_by=self.profile1,
            invited_email='member@test.com',
            status='pending',
            expires_at=timezone.now() + timedelta(days=7),
        )
        resp = self.client2.get('/api/payments/invitations/pending/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class PaymentGroupDeadlineTests(PaymentGroupBaseTestCase):
    """Tests for deadline extension"""
    
    def test_admin_can_extend_deadline(self):
        """Group admin should be able to extend the deadline"""
        new_deadline = (timezone.now() + timedelta(days=60)).isoformat()
        resp = self.client1.post(
            f'/api/payments/groups/{self.group.id}/extend_deadline/',
            {'new_deadline': new_deadline}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertFalse(self.group.is_matured)
    
    def test_non_admin_cannot_extend_deadline(self):
        """Non-admin members should not extend the deadline"""
        PaymentGroupMember.objects.create(
            payment_group=self.group,
            payment_profile=self.profile2,
            is_admin=False,
        )
        new_deadline = (timezone.now() + timedelta(days=60)).isoformat()
        resp = self.client2.post(
            f'/api/payments/groups/{self.group.id}/extend_deadline/',
            {'new_deadline': new_deadline}
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_past_deadline_rejected(self):
        """Should reject a deadline in the past"""
        past_deadline = (timezone.now() - timedelta(days=1)).isoformat()
        resp = self.client1.post(
            f'/api/payments/groups/{self.group.id}/extend_deadline/',
            {'new_deadline': past_deadline}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_extend_resets_maturation(self):
        """Extending deadline should reset is_matured"""
        self.group.is_matured = True
        self.group.save()
        
        new_deadline = (timezone.now() + timedelta(days=60)).isoformat()
        resp = self.client1.post(
            f'/api/payments/groups/{self.group.id}/extend_deadline/',
            {'new_deadline': new_deadline}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertFalse(self.group.is_matured)


class PaymentGroupTerminationTests(PaymentGroupBaseTestCase):
    """Tests for group termination by mutual agreement"""
    
    def setUp(self):
        super().setUp()
        # Set deadline to past so group is matured
        self.group.deadline = timezone.now() - timedelta(days=1)
        self.group.expiry_date = timezone.now() - timedelta(days=1)
        self.group.save()
        
        # Add user2 as member
        PaymentGroupMember.objects.create(
            payment_group=self.group,
            payment_profile=self.profile2,
            is_admin=False,
        )
    
    def test_termination_before_deadline_rejected(self):
        """Cannot terminate before deadline"""
        # Reset deadline to future
        self.group.deadline = timezone.now() + timedelta(days=30)
        self.group.expiry_date = timezone.now() + timedelta(days=30)
        self.group.save()
        
        resp = self.client1.post(
            f'/api/payments/groups/{self.group.id}/request_termination/'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_single_termination_request(self):
        """Single termination request should record but not terminate"""
        resp = self.client1.post(
            f'/api/payments/groups/{self.group.id}/request_termination/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data['is_terminated'])
        self.assertEqual(resp.data['agreed'], 1)
    
    def test_mutual_termination(self):
        """All members agreeing should terminate the group"""
        # User 1 requests
        self.client1.post(
            f'/api/payments/groups/{self.group.id}/request_termination/'
        )
        # User 2 requests
        resp = self.client2.post(
            f'/api/payments/groups/{self.group.id}/request_termination/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['is_terminated'])
        
        self.group.refresh_from_db()
        self.assertTrue(self.group.is_terminated)
        self.assertFalse(self.group.is_active)
    
    def test_non_member_cannot_request_termination(self):
        """Non-members should not request termination"""
        resp = self.client3.post(
            f'/api/payments/groups/{self.group.id}/request_termination/'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class PaymentGroupStatusTests(PaymentGroupBaseTestCase):
    """Tests for group_status endpoint"""
    
    def test_status_returns_correct_fields(self):
        """Status endpoint should return all lifecycle fields"""
        resp = self.client1.get(
            f'/api/payments/groups/{self.group.id}/group_status/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('is_matured', resp.data)
        self.assertIn('is_terminated', resp.data)
        self.assertIn('is_active', resp.data)
        self.assertIn('termination_agreed', resp.data)
        self.assertIn('termination_total', resp.data)
    
    def test_auto_maturation_on_status_check(self):
        """Should auto-set is_matured when deadline has passed"""
        self.group.deadline = timezone.now() - timedelta(days=1)
        self.group.expiry_date = timezone.now() - timedelta(days=1)
        self.group.is_matured = False
        self.group.save()
        
        resp = self.client1.get(
            f'/api/payments/groups/{self.group.id}/group_status/'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['is_matured'])
        
        self.group.refresh_from_db()
        self.assertTrue(self.group.is_matured)


class PaymentGroupDeletionTests(PaymentGroupBaseTestCase):
    """Tests for group deletion restrictions"""
    
    def test_cannot_delete_before_deadline(self):
        """Should not delete a group before deadline passes"""
        resp = self.client1.delete(
            f'/api/payments/groups/{self.group.id}/'
        )
        self.assertIn(resp.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])
    
    def test_non_creator_cannot_delete(self):
        """Non-creator should not be able to delete"""
        PaymentGroupMember.objects.create(
            payment_group=self.group,
            payment_profile=self.profile2,
            is_admin=False,
        )
        resp = self.client2.delete(
            f'/api/payments/groups/{self.group.id}/'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_can_delete_after_termination(self):
        """Creator should delete after group is terminated"""
        self.group.deadline = timezone.now() - timedelta(days=1)
        self.group.expiry_date = timezone.now() - timedelta(days=1)
        self.group.is_terminated = True
        self.group.is_active = False
        self.group.save()
        
        resp = self.client1.delete(
            f'/api/payments/groups/{self.group.id}/'
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
