from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from decimal import Decimal

from Payment.models import TransactionToken, TransactionHistory
from Payment.utils import get_or_create_payment_profile

User = get_user_model()

class StripeWebhookTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='webhook@test.com', password='testpass123',
            first_name='Webhook', last_name='User'
        )
        self.profile = get_or_create_payment_profile(self.user)
        self.profile.comrade_balance = Decimal('0.00')
        self.profile.save()
        
        self.client = APIClient()

    @patch('stripe.Webhook.construct_event')
    def test_v1_payment_intent_succeeded(self, mock_construct):
        # create a transaction token
        tx = TransactionToken.objects.create(
            payment_profile=self.profile,
            transaction_type='deposit',
            amount=Decimal('10.00')
        )
        tx_code = str(tx.transaction_code)
        
        # mock standard v1 event
        mock_construct.return_value = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': tx_code,
                    'amount': 1000,
                }
            }
        }
        
        resp = self.client.post(
            '/api/payments/stripe/webhook/', 
            data='{"test": "payload"}', 
            content_type='application/json', 
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(TransactionHistory.objects.filter(transaction_token=tx, status='completed').exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.comrade_balance, Decimal('10.00'))

    @patch('stripe.PaymentIntent.retrieve')
    @patch('stripe.Webhook.construct_event')
    def test_v2_thin_event_payment_intent_succeeded(self, mock_construct, mock_retrieve):
        # create a transaction token
        tx = TransactionToken.objects.create(
            payment_profile=self.profile,
            transaction_type='deposit',
            amount=Decimal('20.00')
        )
        tx_code = str(tx.transaction_code)
        
        # mock thin event missing 'data'
        mock_construct.return_value = {
            'type': 'v1.payment_intent.succeeded',
            'related_object': {
                'id': tx_code,
                'type': 'payment_intent'
            }
        }
        # mock snapshot fetch
        mock_retrieve.return_value = {
            'id': tx_code,
            'amount': 2000,
        }
        
        resp = self.client.post(
            '/api/payments/stripe/webhook/', 
            data='{"thin": "event"}', 
            content_type='application/json', 
            HTTP_STRIPE_SIGNATURE='test_sig'
        )
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Ensure retrieve was called for snapshot
        mock_retrieve.assert_called_once_with(tx_code)
        
        self.assertTrue(TransactionHistory.objects.filter(transaction_token=tx, status='completed').exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.comrade_balance, Decimal('20.00'))
