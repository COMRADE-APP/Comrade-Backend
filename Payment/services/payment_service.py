import requests
import json
import base64
from datetime import datetime
from django.conf import settings
import stripe
from requests.auth import HTTPBasicAuth

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

class MpesaProvider:
    """Handles M-Pesa Daraja API interactions"""
    
    @staticmethod
    def get_access_token():
        consumer_key = getattr(settings, 'MPESA_CONSUMER_KEY', '')
        consumer_secret = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
        api_url = getattr(settings, 'MPESA_API_URL', 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials')
        
        try:
            r = requests.get(api_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))
            r.raise_for_status()
            return r.json()['access_token']
        except Exception as e:
            print(f"M-Pesa Token Error: {e}")
            return None

    @staticmethod
    def stk_push(phone_number, amount, account_reference, transaction_desc):
        token = MpesaProvider.get_access_token()
        if not token:
            return {"error": "Failed to authenticate with M-Pesa"}
            
        business_short_code = getattr(settings, 'MPESA_BUSINESS_SHORTCODE', '')
        passkey = getattr(settings, 'MPESA_PASSKEY', '')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(f"{business_short_code}{passkey}{timestamp}".encode()).decode('utf-8')
        
        # Validating phone format (254...)
        if phone_number.startswith('0'):
            phone_number = f"254{phone_number[1:]}"
        elif phone_number.startswith('+254'):
            phone_number = phone_number.replace('+', '')
            
        payload = {
            "BusinessShortCode": business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(amount)),
            "PartyA": phone_number,
            "PartyB": business_short_code,
            "PhoneNumber": phone_number,
            "CallBackURL": getattr(settings, 'MPESA_CALLBACK_URL', 'https://api.comrade.kv/payments/mpesa/callback/'),
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        
        api_url = getattr(settings, 'MPESA_STK_PUSH_URL', 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest')
        
        headers = { 'Authorization': f'Bearer {token}' }
        
        try:
            r = requests.post(api_url, json=payload, headers=headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"error": str(e)}

class StripeProvider:
    """Handles Stripe interactions"""
    
    @staticmethod
    def create_payment_intent(amount, currency='usd', description=''):
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(float(amount) * 100),
                currency=currency.lower(),
                description=description,
                automatic_payment_methods={'enabled': True},
            )
            return intent
        except Exception as e:
            return {"error": str(e)}

class PayPalProvider:
    """Handles PayPal interactions"""
    # Placeholder for PayPal implementation details
    pass

class PaymentService:
    @staticmethod
    def verify_account(method, account_number):
        """Verify external account details"""
        if method == 'mpesa':
            # Simple simulation for M-Pesa phone number validation
            if len(str(account_number)) < 9:
                return {"error": "Invalid M-Pesa number format"}
            return {
                "account_name": "M-PESA USER (VERIFIED)",
                "account_number": account_number,
                "provider": method,
                "verified": True
            }
        
        # Real verification logic would go here
        return {
            "account_name": "VERIFIED USER",
            "account_number": account_number,
            "provider": method,
            "verified": True
        }
    @staticmethod
    def initiate_deposit(user, amount, method, details):
        if method == 'mpesa':
            phone = details.get('phone_number')
            return MpesaProvider.stk_push(phone, amount, "Comrade Deposit", f"Deposit for {user.user.username}")
        elif method == 'stripe':
            # For deposits, typically we'd create a Checkout Session or Payment Intent
            return StripeProvider.create_payment_intent(amount, description=f"Deposit for {user.user.username}")
        
        return {"error": "Unsupported Method"}

    @staticmethod
    def initiate_withdrawal(user, amount, method, details):
        # Withdrawals often require B2C (Business to Customer) endpoints
        if method == 'mpesa':
            # Implement B2C
            pass
        return {"message": "Withdrawal initiated (Manual processing for now)"}

    @staticmethod
    def process_payment(amount, currency, method, details):
        if method == 'stripe':
            return StripeProvider.create_payment_intent(amount, currency, details.get('description', 'Purchase'))
        return {"error": "Unsupported Method"}
