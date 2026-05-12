from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

CustomUser = get_user_model()


class PaymentProfileTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='payment@example.com',
            password='pass123',
            first_name='Payment',
        )

    def test_payment_profile_auto_created(self):
        from Payment.models import PaymentProfile
        profile = PaymentProfile.objects.filter(user=self.user).first()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.tier, 'free')

    def test_payment_profile_tier_upgrade(self):
        from Payment.models import PaymentProfile
        profile = PaymentProfile.objects.get(user=self.user)
        profile.tier = 'premium'
        profile.save()
        self.assertEqual(profile.tier, 'premium')


class TransactionTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='transaction@example.com',
            password='pass123',
        )
        from Payment.models import PaymentProfile
        self.profile = PaymentProfile.objects.get(user=self.user)

    def test_create_transaction(self):
        from Payment.models import TransactionHistory
        transaction = TransactionHistory.objects.create(
            sender=self.profile,
            amount=100.00,
            transaction_type='deposit',
            status='completed'
        )
        self.assertEqual(transaction.amount, 100.00)
        self.assertEqual(transaction.status, 'completed')


class PaymentGroupTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='group@example.com',
            password='pass123',
            first_name='Group',
        )
        from Payment.models import PaymentProfile
        self.profile = PaymentProfile.objects.get(user=self.user)

    def test_create_payment_group(self):
        from Payment.models import PaymentGroups
        group = PaymentGroups.objects.create(
            name='Test Group',
            creator=self.profile,
            group_type='savings'
        )
        self.assertEqual(group.name, 'Test Group')
        self.assertEqual(group.members.count(), 1)


class PaymentAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email='api-payment@example.com',
            password='pass123',
        )
        self.client.force_authenticate(user=self.user)

    def test_get_payment_profile(self):
        response = self.client.get('/api/payments/profiles/my_profile/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_get_balance(self):
        response = self.client.get('/api/payments/profiles/balance/')
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_unauthenticated_payment_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/payments/profiles/my_profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
