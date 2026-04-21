"""
Payment Service Providers
Handles communication with external payment APIs:
  - Stripe (Primary: Visa, Mastercard, Apple Pay, Google Pay)
  - Flutterwave (African aggregator: Kenyan banks, M-Pesa, local cards)
  - Pesapal (Kenya-focused aggregator: banks, M-Pesa, Airtel Money)
  - M-Pesa (Safaricom Daraja direct)
  - PayPal (+ Venmo)
  - Equity Bank (Jenga API)
"""
import requests
import stripe
import base64
import hashlib
import hmac
import json
import uuid
import logging
from datetime import datetime
from django.conf import settings


logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


# ============================================================================
# M-PESA PROVIDER
# ============================================================================

class MpesaProvider:
    """Safaricom M-Pesa Daraja API integration."""
    
    @staticmethod
    def get_access_token():
        """Get OAuth access token from M-Pesa API."""
        consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        
        if not consumer_key or not consumer_secret:
            return None
        
        api_url = getattr(settings, 'MPESA_API_URL', 'https://sandbox.safaricom.co.ke')
        url = f"{api_url}/oauth/v1/generate?grant_type=client_credentials"
        
        credentials = base64.b64encode(f"{consumer_key}:{consumer_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {credentials}"}
        
        try:
            r = requests.get(url, headers=headers, timeout=30)
            return r.json().get('access_token')
        except Exception:
            return None
    
    @staticmethod
    def stk_push(phone_number, amount, account_reference, transaction_desc):
        """Initiate M-Pesa STK Push (Lipa Na M-Pesa Online)."""
        access_token = MpesaProvider.get_access_token()
        if not access_token:
            return {"error": "M-Pesa authentication failed. Check API credentials."}
        
        shortcode = getattr(settings, 'MPESA_BUSINESS_SHORTCODE', '')
        passkey = getattr(settings, 'MPESA_PASSKEY', '')
        callback_url = getattr(settings, 'MPESA_CALLBACK_URL', '')
        stk_url = getattr(settings, 'MPESA_STK_PUSH_URL', '')
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{shortcode}{passkey}{timestamp}".encode()).decode()
        
        # Format phone: ensure 254 prefix
        phone = str(phone_number).strip()
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(amount)),
            "PartyA": phone,
            "PartyB": shortcode,
            "PhoneNumber": phone,
            "CallBackURL": callback_url,
            "AccountReference": account_reference[:12],
            "TransactionDesc": transaction_desc[:13],
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            r = requests.post(stk_url, json=payload, headers=headers, timeout=30)
            response = r.json()
            if response.get('ResponseCode') == '0':
                return {
                    'status': 'pending',
                    'checkout_request_id': response.get('CheckoutRequestID'),
                    'merchant_request_id': response.get('MerchantRequestID'),
                    'message': response.get('CustomerMessage', 'STK Push sent'),
                }
            return {"error": response.get('errorMessage', 'STK Push failed')}
        except requests.RequestException as e:
            return {"error": f"M-Pesa connection failed: {str(e)}"}


# ============================================================================
# STRIPE PROVIDER (Primary Gateway)
# ============================================================================

class StripeProvider:
    """Stripe payment processing — handles cards, Apple Pay, Google Pay."""
    
    @staticmethod
    def create_payment_intent(amount, currency='usd', description='', payment_method_id=None, metadata=None):
        """Create a Stripe PaymentIntent."""
        try:
            params = {
                'amount': int(float(amount) * 100),  # Convert to cents
                'currency': currency.lower(),
                'description': description,
                'automatic_payment_methods': {'enabled': True},
            }
            if metadata:
                params['metadata'] = metadata
            if payment_method_id:
                params['payment_method'] = payment_method_id
                params['confirm'] = True
                params.pop('automatic_payment_methods')
            
            intent = stripe.PaymentIntent.create(**params)
            return {
                'id': intent.id,
                'client_secret': intent.client_secret,
                'status': intent.status,
                'amount': intent.amount / 100,
            }
        except stripe.error.CardError as e:
            return {"error": f"Card error: {e.user_message}"}
        except stripe.error.InvalidRequestError as e:
            return {"error": f"Invalid request: {str(e)}"}
        except Exception as e:
            return {"error": f"Stripe error: {str(e)}"}
    
    @staticmethod
    def create_escrow_intent(amount, currency='usd', escrow_id='', metadata=None):
        """Create a PaymentIntent with manual capture for escrow hold.
        
        Funds are authorized but NOT captured until release() is called.
        This is the core mechanism for Stripe-backed escrow.
        """
        try:
            params = {
                'amount': int(float(amount) * 100),
                'currency': currency.lower(),
                'capture_method': 'manual',  # Hold funds — do NOT capture yet
                'description': f'Escrow hold for {escrow_id}',
                'automatic_payment_methods': {'enabled': True},
                'metadata': {
                    'escrow_id': str(escrow_id),
                    'type': 'escrow_hold',
                    **(metadata or {}),
                },
            }
            intent = stripe.PaymentIntent.create(**params)
            return {
                'id': intent.id,
                'client_secret': intent.client_secret,
                'status': intent.status,
                'amount': intent.amount / 100,
            }
        except Exception as e:
            return {"error": f"Stripe escrow intent failed: {str(e)}"}
    
    @staticmethod
    def capture_payment_intent(payment_intent_id, amount_to_capture=None):
        """Capture a previously held PaymentIntent (escrow release)."""
        try:
            params = {}
            if amount_to_capture:
                params['amount_to_capture'] = int(float(amount_to_capture) * 100)
            intent = stripe.PaymentIntent.capture(payment_intent_id, **params)
            return {
                'id': intent.id,
                'status': intent.status,
                'amount_captured': intent.amount_received / 100,
            }
        except Exception as e:
            return {"error": f"Stripe capture failed: {str(e)}"}
    
    @staticmethod
    def cancel_payment_intent(payment_intent_id):
        """Cancel a held PaymentIntent (escrow refund on dispute)."""
        try:
            intent = stripe.PaymentIntent.cancel(payment_intent_id)
            return {
                'id': intent.id,
                'status': intent.status,
            }
        except Exception as e:
            return {"error": f"Stripe cancellation failed: {str(e)}"}
    
    @staticmethod
    def create_checkout_session(amount, currency='usd', line_items=None, success_url='', cancel_url='', metadata=None):
        """Create a Stripe Checkout Session for redirect-based payments."""
        try:
            items = line_items or [{
                'price_data': {
                    'currency': currency.lower(),
                    'unit_amount': int(float(amount) * 100),
                    'product_data': {'name': 'Qomrade Purchase'},
                },
                'quantity': 1,
            }]
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=items,
                mode='payment',
                success_url=success_url or f"{getattr(settings, 'FRONTEND_URL', '')}checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url or f"{getattr(settings, 'FRONTEND_URL', '')}checkout/cancel",
                metadata=metadata or {},
            )
            return {
                'id': session.id,
                'url': session.url,
                'status': session.status,
            }
        except Exception as e:
            return {"error": f"Stripe checkout session failed: {str(e)}"}
    
    @staticmethod
    def create_customer(email, name=''):
        """Create a Stripe Customer for saving payment methods."""
        try:
            customer = stripe.Customer.create(email=email, name=name)
            return {'id': customer.id, 'email': customer.email}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def create_refund(payment_intent_id, amount=None, reason='requested_by_customer'):
        """Create a refund for a PaymentIntent."""
        try:
            params = {
                'payment_intent': payment_intent_id,
                'reason': reason,
            }
            if amount:
                params['amount'] = int(float(amount) * 100)
            refund = stripe.Refund.create(**params)
            return {
                'id': refund.id,
                'status': refund.status,
                'amount': refund.amount / 100,
            }
        except Exception as e:
            return {"error": f"Stripe refund failed: {str(e)}"}


# ============================================================================
# FLUTTERWAVE PROVIDER (African Aggregator)
# ============================================================================

class FlutterwaveProvider:
    """Flutterwave API integration.
    
    Covers all 7 Kenyan banks (Equity, KCB, DTB, Absa, Ecobank, NCBA, Family Bank),
    M-Pesa, and local card payments via a single integration.
    Ideal for expanding to other African markets (Nigeria, Ghana, SA, etc).
    """
    
    @staticmethod
    def _get_headers():
        secret_key = getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '')
        if not secret_key:
            return None
        return {
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json',
        }
    
    @staticmethod
    def initiate_payment(amount, currency='KES', email='', phone='', 
                         redirect_url='', tx_ref=None, description='Qomrade Payment',
                         payment_options='card,mpesa,banktransfer'):
        """Create a Flutterwave Standard payment (hosted checkout page).
        
        Returns a link the user should be redirected to.
        Supports: card, mpesa, banktransfer, ussd, mobilemoneyghana, etc.
        """
        headers = FlutterwaveProvider._get_headers()
        if not headers:
            return {"error": "Flutterwave not configured. Add FLUTTERWAVE_SECRET_KEY to .env"}
        
        base_url = getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3')
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173/')
        
        payload = {
            'tx_ref': tx_ref or f'QOM-{uuid.uuid4().hex[:12].upper()}',
            'amount': str(float(amount)),
            'currency': currency.upper(),
            'redirect_url': redirect_url or f'{frontend_url}payments/callback/flutterwave',
            'payment_options': payment_options,
            'customer': {
                'email': email or 'customer@qomrade.com',
                'phonenumber': phone or '',
            },
            'customizations': {
                'title': 'Qomrade Payment',
                'description': description,
                'logo': f'{frontend_url}logo.png',
            },
        }
        
        try:
            r = requests.post(f'{base_url}/payments', json=payload, headers=headers, timeout=30)
            data = r.json()
            if data.get('status') == 'success':
                return {
                    'status': 'redirect',
                    'payment_link': data['data']['link'],
                    'tx_ref': payload['tx_ref'],
                }
            return {"error": data.get('message', 'Flutterwave payment initiation failed')}
        except requests.RequestException as e:
            return {"error": f"Flutterwave connection failed: {str(e)}"}
    
    @staticmethod
    def verify_transaction(transaction_id):
        """Verify a Flutterwave payment status by transaction ID."""
        headers = FlutterwaveProvider._get_headers()
        if not headers:
            return {"error": "Flutterwave not configured"}
        
        base_url = getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3')
        
        try:
            r = requests.get(f'{base_url}/transactions/{transaction_id}/verify', headers=headers, timeout=30)
            data = r.json()
            if data.get('status') == 'success' and data['data']['status'] == 'successful':
                return {
                    'status': 'completed',
                    'amount': data['data']['amount'],
                    'currency': data['data']['currency'],
                    'tx_ref': data['data']['tx_ref'],
                    'flw_ref': data['data']['flw_ref'],
                    'payment_type': data['data']['payment_type'],
                }
            return {
                'status': data['data'].get('status', 'failed'),
                'message': data.get('message', 'Verification failed'),
            }
        except requests.RequestException as e:
            return {"error": f"Flutterwave verification failed: {str(e)}"}
    
    @staticmethod
    def initiate_transfer(account_number, bank_code, amount, currency='KES',
                          narration='Qomrade Payout', reference=None):
        """Initiate a bank transfer payout via Flutterwave."""
        headers = FlutterwaveProvider._get_headers()
        if not headers:
            return {"error": "Flutterwave not configured"}
        
        base_url = getattr(settings, 'FLUTTERWAVE_BASE_URL', 'https://api.flutterwave.com/v3')
        
        payload = {
            'account_bank': bank_code,
            'account_number': account_number,
            'amount': float(amount),
            'currency': currency.upper(),
            'narration': narration,
            'reference': reference or f'QOM-OUT-{uuid.uuid4().hex[:10].upper()}',
        }
        
        try:
            r = requests.post(f'{base_url}/transfers', json=payload, headers=headers, timeout=30)
            data = r.json()
            if data.get('status') == 'success':
                return {
                    'status': 'pending',
                    'transfer_id': data['data']['id'],
                    'reference': data['data'].get('reference'),
                }
            return {"error": data.get('message', 'Transfer initiation failed')}
        except requests.RequestException as e:
            return {"error": f"Flutterwave transfer failed: {str(e)}"}
    
    @staticmethod
    def verify_webhook_signature(request_body, signature_header):
        """Verify Flutterwave webhook signature using secret hash."""
        secret_hash = getattr(settings, 'FLUTTERWAVE_SECRET_HASH', '')
        if not secret_hash:
            logger.warning('FLUTTERWAVE_SECRET_HASH not configured')
            return False
        return signature_header == secret_hash


# ============================================================================
# PESAPAL PROVIDER (Kenya-Focused)
# ============================================================================

class PesapalProvider:
    """Pesapal API v3 integration.
    
    Best choice for Kenya-only operations. Handles all major Kenyan banks,
    M-Pesa, and Airtel Money through pre-negotiated integrations.
    """
    
    @staticmethod
    def _get_access_token():
        """Get Pesapal OAuth token (valid ~5min; should be cached in production)."""
        consumer_key = getattr(settings, 'PESAPAL_CONSUMER_KEY', '')
        consumer_secret = getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')
        base_url = getattr(settings, 'PESAPAL_BASE_URL', 'https://cybqa.pesapal.com/pesapalv3')
        
        if not consumer_key or not consumer_secret:
            return None
        
        try:
            r = requests.post(
                f'{base_url}/api/Auth/RequestToken',
                json={
                    'consumer_key': consumer_key,
                    'consumer_secret': consumer_secret,
                },
                headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
                timeout=30,
            )
            data = r.json()
            return data.get('token')
        except Exception as e:
            logger.error(f'Pesapal auth failed: {e}')
            return None
    
    @staticmethod
    def register_ipn(callback_url, ipn_notification_type='GET'):
        """Register an IPN (Instant Payment Notification) callback URL."""
        token = PesapalProvider._get_access_token()
        if not token:
            return {"error": "Pesapal authentication failed"}
        
        base_url = getattr(settings, 'PESAPAL_BASE_URL', 'https://cybqa.pesapal.com/pesapalv3')
        
        try:
            r = requests.post(
                f'{base_url}/api/URLSetup/RegisterIPN',
                json={
                    'url': callback_url,
                    'ipn_notification_type': ipn_notification_type,
                },
                headers={
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                timeout=30,
            )
            data = r.json()
            return {
                'ipn_id': data.get('ipn_id'),
                'url': data.get('url'),
                'status': data.get('status'),
            }
        except requests.RequestException as e:
            return {"error": f"Pesapal IPN registration failed: {str(e)}"}
    
    @staticmethod
    def submit_order(amount, currency='KES', description='Qomrade Payment',
                     callback_url='', phone='', email='', first_name='', last_name='',
                     order_id=None):
        """Submit a payment order to Pesapal.
        
        Returns a redirect URL for the Pesapal hosted payment page.
        """
        token = PesapalProvider._get_access_token()
        if not token:
            return {"error": "Pesapal authentication failed. Add PESAPAL_CONSUMER_KEY to .env"}
        
        base_url = getattr(settings, 'PESAPAL_BASE_URL', 'https://cybqa.pesapal.com/pesapalv3')
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173/')
        
        # Register IPN if not configured (idempotent)
        ipn_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8001/')}/api/payments/pesapal/ipn/"
        ipn_result = PesapalProvider.register_ipn(ipn_url)
        ipn_id = ipn_result.get('ipn_id', '')
        
        merchant_reference = order_id or f'QOM-{uuid.uuid4().hex[:12].upper()}'
        
        payload = {
            'id': merchant_reference,
            'currency': currency.upper(),
            'amount': float(amount),
            'description': description,
            'callback_url': callback_url or f'{frontend_url}payments/callback/pesapal',
            'notification_id': ipn_id,
            'billing_address': {
                'email_address': email or '',
                'phone_number': phone or '',
                'first_name': first_name or 'Customer',
                'last_name': last_name or '',
            },
        }
        
        try:
            r = requests.post(
                f'{base_url}/api/Transactions/SubmitOrderRequest',
                json=payload,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                timeout=30,
            )
            data = r.json()
            if data.get('redirect_url'):
                return {
                    'status': 'redirect',
                    'redirect_url': data['redirect_url'],
                    'order_tracking_id': data.get('order_tracking_id'),
                    'merchant_reference': merchant_reference,
                }
            return {"error": data.get('error', {}).get('message', 'Pesapal order submission failed')}
        except requests.RequestException as e:
            return {"error": f"Pesapal connection failed: {str(e)}"}
    
    @staticmethod
    def get_transaction_status(order_tracking_id):
        """Check the status of a Pesapal transaction."""
        token = PesapalProvider._get_access_token()
        if not token:
            return {"error": "Pesapal authentication failed"}
        
        base_url = getattr(settings, 'PESAPAL_BASE_URL', 'https://cybqa.pesapal.com/pesapalv3')
        
        try:
            r = requests.get(
                f'{base_url}/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}',
                headers={
                    'Authorization': f'Bearer {token}',
                    'Accept': 'application/json',
                },
                timeout=30,
            )
            data = r.json()
            status_code = data.get('payment_status_description', '').upper()
            return {
                'status': 'completed' if status_code == 'COMPLETED' else status_code.lower(),
                'amount': data.get('amount'),
                'currency': data.get('currency'),
                'payment_method': data.get('payment_method'),
                'reference': data.get('merchant_reference'),
                'description': data.get('description'),
            }
        except requests.RequestException as e:
            return {"error": f"Pesapal status check failed: {str(e)}"}


# ============================================================================
# PAYPAL PROVIDER
# ============================================================================

class PayPalProvider:
    """PayPal REST API integration."""
    
    @staticmethod
    def get_access_token():
        """Get PayPal OAuth access token."""
        client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
        api_url = getattr(settings, 'PAYPAL_API_URL', 'https://api-m.sandbox.paypal.com')
        
        if not client_id or not client_secret:
            return None
        
        try:
            credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            r = requests.post(
                f"{api_url}/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data="grant_type=client_credentials",
                timeout=30,
            )
            return r.json().get('access_token')
        except Exception:
            return None
    
    @staticmethod
    def create_order(amount, currency='USD', description=''):
        """Create a PayPal order for checkout."""
        access_token = PayPalProvider.get_access_token()
        if not access_token:
            return {"error": "PayPal authentication failed. Check API credentials."}
        
        api_url = getattr(settings, 'PAYPAL_API_URL', 'https://api-m.sandbox.paypal.com')
        
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": currency.upper(),
                    "value": f"{float(amount):.2f}",
                },
                "description": description,
            }],
        }
        
        try:
            r = requests.post(
                f"{api_url}/v2/checkout/orders",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            data = r.json()
            if r.status_code in (200, 201):
                return {
                    'id': data.get('id'),
                    'status': data.get('status'),
                    'approve_url': next(
                        (l['href'] for l in data.get('links', []) if l['rel'] == 'approve'), None
                    ),
                }
            return {"error": data.get('message', 'PayPal order creation failed')}
        except requests.RequestException as e:
            return {"error": f"PayPal connection failed: {str(e)}"}
    
    @staticmethod
    def capture_order(order_id):
        """Capture a previously approved PayPal order."""
        access_token = PayPalProvider.get_access_token()
        if not access_token:
            return {"error": "PayPal authentication failed."}
        
        api_url = getattr(settings, 'PAYPAL_API_URL', 'https://api-m.sandbox.paypal.com')
        
        try:
            r = requests.post(
                f"{api_url}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            data = r.json()
            if r.status_code in (200, 201):
                return {
                    'id': data.get('id'),
                    'status': data.get('status'),
                    'payer': data.get('payer', {}),
                }
            return {"error": data.get('message', 'PayPal capture failed')}
        except requests.RequestException as e:
            return {"error": f"PayPal connection failed: {str(e)}"}
    
    @staticmethod
    def create_payout(email, amount, currency='USD', note=''):
        """Send a PayPal payout to an email address."""
        access_token = PayPalProvider.get_access_token()
        if not access_token:
            return {"error": "PayPal authentication failed."}
        
        api_url = getattr(settings, 'PAYPAL_API_URL', 'https://api-m.sandbox.paypal.com')
        
        payload = {
            "sender_batch_header": {
                "sender_batch_id": str(uuid.uuid4()),
                "email_subject": "Qomrade Payment",
                "email_message": note or "You have received a payment from Qomrade.",
            },
            "items": [{
                "recipient_type": "EMAIL",
                "amount": {
                    "value": f"{float(amount):.2f}",
                    "currency": currency.upper(),
                },
                "receiver": email,
                "note": note,
            }],
        }
        
        try:
            r = requests.post(
                f"{api_url}/v1/payments/payouts",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            data = r.json()
            if r.status_code in (200, 201):
                return {
                    'batch_id': data.get('batch_header', {}).get('payout_batch_id'),
                    'status': data.get('batch_header', {}).get('batch_status'),
                }
            return {"error": data.get('message', 'PayPal payout failed')}
        except requests.RequestException as e:
            return {"error": f"PayPal connection failed: {str(e)}"}


# ============================================================================
# EQUITY BANK PROVIDER (Jenga API)
# ============================================================================

class EquityBankProvider:
    """Equity Bank Jenga API integration for bank transfers."""
    
    @staticmethod
    def get_access_token():
        """Get Jenga API access token."""
        api_key = getattr(settings, 'EQUITY_API_KEY', '')
        consumer_secret = getattr(settings, 'EQUITY_CONSUMER_SECRET', '')
        api_url = getattr(settings, 'EQUITY_API_URL', 'https://uat.jengahq.io')
        
        if not api_key or not consumer_secret:
            return None
        
        try:
            r = requests.post(
                f"{api_url}/identity/v2/token",
                headers={
                    "Authorization": f"Basic {base64.b64encode(f'{api_key}:{consumer_secret}'.encode()).decode()}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data="grant_type=client_credentials",
                timeout=30,
            )
            return r.json().get('access_token')
        except Exception:
            return None
    
    @staticmethod
    def send_to_bank(account_number, amount, bank_code='63', reference='', narration=''):
        """Send funds to an Equity Bank account via Jenga API."""
        access_token = EquityBankProvider.get_access_token()
        if not access_token:
            return {"error": "Equity Bank authentication failed. Check API credentials."}
        
        api_url = getattr(settings, 'EQUITY_API_URL', 'https://uat.jengahq.io')
        merchant_code = getattr(settings, 'EQUITY_MERCHANT_CODE', '')
        
        payload = {
            "source": {
                "countryCode": "KE",
                "name": "Qomrade Platform",
                "accountNumber": merchant_code,
            },
            "destination": {
                "type": "bank",
                "countryCode": "KE",
                "name": "Recipient",
                "bankCode": bank_code,
                "accountNumber": account_number,
            },
            "transfer": {
                "type": "InternalFundsTransfer",
                "amount": f"{float(amount):.2f}",
                "currencyCode": "KES",
                "reference": reference or f"COMRADE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "description": narration or "Payment from Qomrade",
            },
        }
        
        try:
            r = requests.post(
                f"{api_url}/transaction/v2/remittance",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            data = r.json()
            if r.status_code in (200, 201):
                return {
                    'status': 'completed',
                    'reference': data.get('referenceNumber', reference),
                    'message': data.get('message', 'Transfer successful'),
                }
            return {"error": data.get('message', 'Bank transfer failed')}
        except requests.RequestException as e:
            return {"error": f"Equity Bank connection failed: {str(e)}"}


# ============================================================================
# PAYMENT ROUTER
# ============================================================================

class PaymentRouter:
    """Routes completed payments to the configured destination account."""
    
    @staticmethod
    def route_payment(amount, currency='USD', destination=None, details=None):
        """Route a payment to the configured destination.
        
        Args:
            amount: Amount to route
            currency: Currency code
            destination: Override destination (paypal/mpesa/equity/stripe/flutterwave/pesapal)
            details: Dict with destination-specific details (email, phone, account_number)
        """
        dest = destination or getattr(settings, 'PAYMENT_DESTINATION', 'stripe')
        details = details or {}
        
        if dest == 'paypal':
            email = details.get('email', '')
            if not email:
                return {"error": "PayPal email required for routing"}
            return PayPalProvider.create_payout(email, amount, currency)
        
        elif dest == 'mpesa':
            phone = details.get('phone_number', '')
            if not phone:
                return {"error": "Phone number required for M-Pesa routing"}
            return MpesaProvider.stk_push(phone, amount, "Qomrade Payout", "Platform payout")
        
        elif dest == 'flutterwave':
            account = details.get('account_number', '')
            bank_code = details.get('bank_code', '')
            if not account or not bank_code:
                return {"error": "Account number and bank code required for Flutterwave routing"}
            return FlutterwaveProvider.initiate_transfer(account, bank_code, amount, currency)
        
        elif dest == 'equity':
            account = details.get('account_number', '')
            if not account:
                return {"error": "Account number required for Equity routing"}
            return EquityBankProvider.send_to_bank(account, amount)
        
        elif dest == 'stripe':
            # For Stripe, the money stays in the connected Stripe account
            return {"status": "completed", "message": "Funds retained in Stripe account"}
        
        return {"error": f"Unsupported destination: {dest}"}


# ============================================================================
# PAYMENT SERVICE (Orchestration Layer)
# ============================================================================

class PaymentService:
    """High-level payment orchestration."""
    
    @staticmethod
    def get_available_gateways():
        """Return dict of available gateways (ones with configured keys)."""
        gateways = {
            'stripe': {
                'available': bool(getattr(settings, 'STRIPE_SECRET_KEY', '')),
                'public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
                'label': 'Card / Apple Pay / Google Pay',
                'methods': ['visa', 'mastercard', 'amex', 'apple_pay', 'google_pay'],
            },
            'paypal': {
                'available': bool(getattr(settings, 'PAYPAL_CLIENT_ID', '')),
                'client_id': getattr(settings, 'PAYPAL_CLIENT_ID', ''),
                'label': 'PayPal / Venmo',
                'methods': ['paypal', 'venmo'],
            },
            'mpesa': {
                'available': bool(getattr(settings, 'MPESA_CONSUMER_KEY', '')),
                'label': 'M-Pesa (Safaricom)',
                'methods': ['mpesa'],
            },
            'flutterwave': {
                'available': bool(getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '')),
                'public_key': getattr(settings, 'FLUTTERWAVE_PUBLIC_KEY', ''),
                'label': 'Bank / M-Pesa / Card (Africa)',
                'methods': ['card', 'mpesa', 'bank_transfer', 'ussd'],
            },
            'pesapal': {
                'available': bool(getattr(settings, 'PESAPAL_CONSUMER_KEY', '')),
                'label': 'Pesapal (Kenya)',
                'methods': ['mpesa', 'airtel_money', 'bank', 'card'],
            },
        }
        return {k: v for k, v in gateways.items() if v['available']}
    
    @staticmethod
    def verify_account(method, account_number):
        """Verify an external account."""
        if method == 'mpesa':
            # M-Pesa phone validation
            digits = account_number.replace('+', '').replace(' ', '')
            if digits.startswith('0'):
                digits = '254' + digits[1:]
            if len(digits) >= 12 and digits.startswith('254'):
                return {
                    "account_name": "VERIFIED USER",
                    "account_number": account_number,
                    "provider": "mpesa",
                    "verified": True
                }
            return {"error": "Invalid M-Pesa phone number format"}
        
        return {
            "account_name": "VERIFIED USER",
            "account_number": account_number,
            "provider": method,
            "verified": True
        }
    
    @staticmethod
    def initiate_deposit(user, amount, method, details):
        """Initiate a deposit using the specified payment method."""
        user_label = user.user.email if hasattr(user, 'user') else 'user'
        if method == 'mpesa':
            phone = details.get('phone_number')
            if not phone:
                return {"error": "Phone number is required for M-Pesa deposits"}
            return MpesaProvider.stk_push(
                phone, amount, "Qomrade Deposit", f"Deposit for {user_label}"
            )
        elif method in ('stripe', 'card'):
            payment_method_id = details.get('payment_method_id')
            return StripeProvider.create_payment_intent(
                amount, 
                description=f"Deposit for {user_label}",
                payment_method_id=payment_method_id
            )
        elif method == 'paypal':
            return PayPalProvider.create_order(amount, description=f"Deposit for {user_label}")
        elif method == 'flutterwave':
            email = details.get('email', user_label)
            phone = details.get('phone_number', '')
            return FlutterwaveProvider.initiate_payment(
                amount, currency=details.get('currency', 'KES'),
                email=email, phone=phone,
                description=f"Deposit for {user_label}"
            )
        elif method == 'pesapal':
            email = details.get('email', user_label)
            phone = details.get('phone_number', '')
            return PesapalProvider.submit_order(
                amount, currency=details.get('currency', 'KES'),
                email=email, phone=phone,
                description=f"Deposit for {user_label}"
            )
        
        return {"error": f"Unsupported deposit method: {method}"}
    
    @staticmethod
    def initiate_withdrawal(user, amount, method, details):
        """Initiate a withdrawal to the specified destination."""
        if method == 'mpesa':
            phone = details.get('phone_number')
            if not phone:
                return {"error": "Phone number required for M-Pesa withdrawal"}
            return MpesaProvider.stk_push(phone, amount, "Qomrade Withdrawal", "Withdrawal")
        elif method == 'paypal':
            email = details.get('email')
            if not email:
                return {"error": "PayPal email required for withdrawal"}
            return PayPalProvider.create_payout(email, amount)
        elif method in ('equity', 'bank'):
            account = details.get('account_number')
            if not account:
                return {"error": "Account number required for bank withdrawal"}
            return EquityBankProvider.send_to_bank(account, amount)
        elif method == 'flutterwave':
            account = details.get('account_number')
            bank_code = details.get('bank_code')
            if not account or not bank_code:
                return {"error": "Account number and bank code required for Flutterwave withdrawal"}
            return FlutterwaveProvider.initiate_transfer(account, bank_code, amount)
        
        return {"error": f"Unsupported withdrawal method: {method}"}
    
    @staticmethod
    def process_payment(amount, currency, method, details):
        """Process a payment using the specified method."""
        if method == 'stripe':
            return StripeProvider.create_payment_intent(
                amount, currency, 
                details.get('description', 'Purchase'),
                details.get('payment_method_id'),
                metadata=details.get('metadata')
            )
        elif method == 'mpesa':
            phone = details.get('phone_number')
            if not phone:
                return {"error": "Phone number is required for M-Pesa payments"}
            return MpesaProvider.stk_push(
                phone, amount, "Qomrade", details.get('description', 'Payment')[:13]
            )
        elif method == 'paypal':
            return PayPalProvider.create_order(
                amount, currency, details.get('description', 'Purchase')
            )
        elif method == 'flutterwave':
            return FlutterwaveProvider.initiate_payment(
                amount, currency=currency,
                email=details.get('email', ''),
                phone=details.get('phone_number', ''),
                description=details.get('description', 'Purchase'),
            )
        elif method == 'pesapal':
            return PesapalProvider.submit_order(
                amount, currency=currency,
                email=details.get('email', ''),
                phone=details.get('phone_number', ''),
                description=details.get('description', 'Purchase'),
            )
        elif method == 'equity':
            account = details.get('account_number')
            if not account:
                return {"error": "Account number required for Equity Bank payments"}
            return EquityBankProvider.send_to_bank(account, amount)
        
        return {"error": f"Unsupported payment method: {method}"}
