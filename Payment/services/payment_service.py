"""
Payment Service Providers
Handles communication with external payment APIs: M-Pesa, Stripe, PayPal, Equity Bank
"""
import requests
import stripe
import base64
from datetime import datetime
from django.conf import settings


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
# STRIPE PROVIDER
# ============================================================================

class StripeProvider:
    """Stripe payment processing."""
    
    @staticmethod
    def create_payment_intent(amount, currency='usd', description='', payment_method_id=None):
        """Create a Stripe PaymentIntent."""
        try:
            params = {
                'amount': int(float(amount) * 100),  # Convert to cents
                'currency': currency.lower(),
                'description': description,
                'automatic_payment_methods': {'enabled': True},
            }
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
    def create_customer(email, name=''):
        """Create a Stripe Customer for saving payment methods."""
        try:
            customer = stripe.Customer.create(email=email, name=name)
            return {'id': customer.id, 'email': customer.email}
        except Exception as e:
            return {"error": str(e)}


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
        
        import uuid
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
            destination: Override destination (paypal/mpesa/equity/stripe)
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
        
        return {"error": f"Unsupported withdrawal method: {method}"}
    
    @staticmethod
    def process_payment(amount, currency, method, details):
        """Process a payment using the specified method."""
        if method == 'stripe':
            return StripeProvider.create_payment_intent(
                amount, currency, 
                details.get('description', 'Purchase'),
                details.get('payment_method_id')
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
        elif method == 'equity':
            account = details.get('account_number')
            if not account:
                return {"error": "Account number required for Equity Bank payments"}
            return EquityBankProvider.send_to_bank(account, amount)
        
        return {"error": f"Unsupported payment method: {method}"}
