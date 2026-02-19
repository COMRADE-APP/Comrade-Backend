from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import PaymentProfile, TransactionToken, TransactionHistory, PaymentLog
from .serializers import TransactionTokenSerializer, PaymentProfileSerializer
from .utils import check_purchase_limit, increment_purchase_count, get_or_create_payment_profile
from Authentication.models import Profile
from Payment.services.payment_service import PaymentService

class VerifyAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Verify external account details (simulated).
        In a real app, this would call MPesa/Bank/PayPal APIs.
        """
        payment_method = request.data.get('payment_method')
        account_number = request.data.get('account_number')
        
        if not payment_method or not account_number:
            return Response(
                {"detail": "Payment method and account number are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Call Payment Service to verify
        response = PaymentService.verify_account(payment_method, account_number)
        
        if "error" in response:
             return Response({"detail": response["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response)


class DepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Initiate a deposit from an external source to Qomrade Balance.
        Accepts per-method fields and optionally saves payment details.
        """
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'mpesa')
        save_details = request.data.get('save_details', False)

        # Per-method fields
        phone_number = request.data.get('phone_number')
        email = request.data.get('email') or request.data.get('paypal_email')
        card_number = request.data.get('card_number')
        expiry_month = request.data.get('expiry_month')
        expiry_year = request.data.get('expiry_year')
        cvc = request.data.get('cvc')
        billing_zip = request.data.get('billing_zip')
        account_number = request.data.get('account_number')
        bank_name = request.data.get('bank_name')
        saved_method_id = request.data.get('saved_method_id')
        
        if not amount or float(amount) <= 0:
             return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate per-method required fields
        if payment_method == 'mpesa' and not phone_number and not saved_method_id:
            return Response({"detail": "Phone number is required for M-Pesa deposits."}, status=status.HTTP_400_BAD_REQUEST)
        if payment_method == 'paypal' and not email and not saved_method_id:
            return Response({"detail": "PayPal email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if payment_method in ('stripe', 'card') and not card_number and not saved_method_id:
            return Response({"detail": "Card details are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure profile exists and lock it
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
             return Response({"detail": "Could not create payment profile."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            profile = PaymentProfile.objects.select_for_update().get(id=payment_profile.id)
        except PaymentProfile.DoesNotExist:
             return Response({"detail": "Payment profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # If using a saved method, load its details
        if saved_method_id:
            try:
                from .models import SavedPaymentMethod
                saved = SavedPaymentMethod.objects.get(id=saved_method_id, payment_profile=profile)
                if saved.method_type == 'mpesa':
                    phone_number = phone_number or saved.phone_number
                elif saved.method_type == 'paypal':
                    email = email or saved.paypal_email
                elif saved.method_type == 'bank':
                    account_number = account_number or saved.bank_last_four
            except Exception:
                pass

        # Auto-save payment details for future use
        if save_details:
            try:
                from .models import SavedPaymentMethod
                if payment_method == 'mpesa' and phone_number:
                    SavedPaymentMethod.objects.get_or_create(
                        payment_profile=profile,
                        method_type='mpesa',
                        phone_number=phone_number,
                        defaults={'nickname': f"M-Pesa {phone_number[-4:]}"}
                    )
                elif payment_method == 'paypal' and email:
                    SavedPaymentMethod.objects.get_or_create(
                        payment_profile=profile,
                        method_type='paypal',
                        paypal_email=email,
                        defaults={'nickname': f"PayPal {email}"}
                    )
                elif payment_method in ('stripe', 'card') and card_number:
                    last_four = card_number.replace(' ', '')[-4:]
                    SavedPaymentMethod.objects.get_or_create(
                        payment_profile=profile,
                        method_type='card',
                        last_four=last_four,
                        defaults={
                            'expiry_month': int(expiry_month) if expiry_month else None,
                            'expiry_year': int(expiry_year) if expiry_year else None,
                            'billing_zip': billing_zip or '',
                            'nickname': f"Card •••• {last_four}",
                        }
                    )
                elif payment_method in ('equity', 'bank') and account_number:
                    SavedPaymentMethod.objects.get_or_create(
                        payment_profile=profile,
                        method_type='bank',
                        bank_last_four=account_number[-4:],
                        defaults={
                            'bank_name': bank_name or 'Bank',
                            'nickname': f"Bank •••• {account_number[-4:]}",
                        }
                    )
            except Exception as e:
                # Non-blocking; log but don't fail the deposit
                import logging
                logging.getLogger(__name__).warning(f"Failed to save payment details: {e}")

        # Create Pending Transaction
        payment_number = phone_number or email or account_number or (card_number[-4:] if card_number else profile.payment_number)
        token = TransactionToken.objects.create(
            payment_profile=profile,
            amount=amount,
            transaction_type='deposit',
            payment_option=payment_method,
            payment_number=payment_number or '',
            description=f"Deposit via {payment_method}"
        )

        # Call Payment Service
        details = {
            'phone_number': phone_number,
            'email': email,
            'transaction_code': str(token.transaction_code),
            'payment_method_id': request.data.get('payment_method_id'),
            'account_number': account_number,
        }
        response = PaymentService.initiate_deposit(profile, amount, payment_method, details)
        
        if "error" in response:
             return Response({"detail": response["error"]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "detail": "Deposit initiated. Check your phone/email for instructions.",
            "transaction_code": token.transaction_code,
            "provider_response": response
        })


class WithdrawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Withdraw from Qomrade Balance to external account.
        Accepts per-method fields and optionally saves payment details.
        """
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'mpesa')
        save_details = request.data.get('save_details', False)

        # Per-method fields
        phone_number = request.data.get('phone_number')
        email = request.data.get('email') or request.data.get('paypal_email')
        account_number = request.data.get('account_number')
        bank_name = request.data.get('bank_name')
        saved_method_id = request.data.get('saved_method_id')
        
        if not amount or float(amount) <= 0:
             return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate per-method required fields
        if payment_method == 'mpesa' and not phone_number and not saved_method_id:
            return Response({"detail": "Phone number is required for M-Pesa withdrawals."}, status=status.HTTP_400_BAD_REQUEST)
        if payment_method == 'paypal' and not email and not saved_method_id:
            return Response({"detail": "PayPal email is required."}, status=status.HTTP_400_BAD_REQUEST)
        if payment_method in ('equity', 'bank') and not account_number and not saved_method_id:
            return Response({"detail": "Account number is required for bank withdrawals."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure profile exists and lock it
        payment_profile = get_or_create_payment_profile(request.user)
        if not payment_profile:
             return Response({"detail": "Could not create payment profile."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            profile = PaymentProfile.objects.select_for_update().get(id=payment_profile.id)
        except PaymentProfile.DoesNotExist:
             return Response({"detail": "Payment profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if profile.comrade_balance < float(amount):
            return Response({"detail": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        # If using a saved method, load its details
        if saved_method_id:
            try:
                from .models import SavedPaymentMethod
                saved = SavedPaymentMethod.objects.get(id=saved_method_id, payment_profile=profile)
                if saved.method_type == 'mpesa':
                    phone_number = phone_number or saved.phone_number
                elif saved.method_type == 'paypal':
                    email = email or saved.paypal_email
                elif saved.method_type == 'bank':
                    account_number = account_number or saved.bank_last_four
            except Exception:
                pass

        # Auto-save withdrawal details for future use
        if save_details:
            try:
                from .models import SavedPaymentMethod
                if payment_method == 'mpesa' and phone_number:
                    SavedPaymentMethod.objects.get_or_create(
                        payment_profile=profile,
                        method_type='mpesa',
                        phone_number=phone_number,
                        defaults={'nickname': f"M-Pesa {phone_number[-4:]}"}
                    )
                elif payment_method == 'paypal' and email:
                    SavedPaymentMethod.objects.get_or_create(
                        payment_profile=profile,
                        method_type='paypal',
                        paypal_email=email,
                        defaults={'nickname': f"PayPal {email}"}
                    )
                elif payment_method in ('equity', 'bank') and account_number:
                    SavedPaymentMethod.objects.get_or_create(
                        payment_profile=profile,
                        method_type='bank',
                        bank_last_four=account_number[-4:],
                        defaults={
                            'bank_name': bank_name or 'Bank',
                            'nickname': f"Bank •••• {account_number[-4:]}",
                        }
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to save payment details: {e}")

        # Create Pending Transaction
        payment_number = phone_number or email or account_number or ''
        token = TransactionToken.objects.create(
            payment_profile=profile,
            amount=amount,
            transaction_type='withdrawal',
            payment_option=payment_method,
            payment_number=payment_number,
            description=f"Withdrawal to {payment_method} - {payment_number}"
        )

        # Call Payment Service
        details = {
            'phone_number': phone_number,
            'email': email,
            'account_number': account_number,
            'transaction_code': str(token.transaction_code),
        }
        response = PaymentService.initiate_withdrawal(profile, amount, payment_method, details)
        
        if "error" in response:
            return Response({"detail": response["error"]}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct Balance
        profile.comrade_balance -= float(amount)
        profile.save()

        # Log History
        TransactionHistory.objects.create(
            payment_profile=profile,
            transaction_token=token,
            transaction_category='withdrawal',
            payment_type='individual',
            status='completed',
            amount=amount
        )

        return Response({
            "detail": "Withdrawal initiated successfully.",
            "new_balance": profile.comrade_balance,
            "transaction_code": token.transaction_code
        })


class TransferView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Transfer funds internally to another user.
        """
        recipient_email = request.data.get('recipient_email')
        amount = request.data.get('amount')
        
        if not amount or float(amount) <= 0:
             return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not recipient_email:
             return Response({"detail": "Recipient email required."}, status=status.HTTP_400_BAD_REQUEST)
             
        # Ensure sender profile exists
        sender_profile_obj = get_or_create_payment_profile(request.user)
        if not sender_profile_obj:
            return Response({"detail": "Could not create sender profile."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        sender_profile = PaymentProfile.objects.select_for_update().get(id=sender_profile_obj.id)
        
        if sender_profile.comrade_balance < float(amount):
            return Response({"detail": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Find recipient
        try:
            from Authentication.models import CustomUser
            recipient_user = CustomUser.objects.get(email=recipient_email)
            recipient_profile_obj = get_or_create_payment_profile(recipient_user)
            if not recipient_profile_obj:
                return Response({"detail": "Could not create recipient profile."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            recipient_profile = PaymentProfile.objects.select_for_update().get(id=recipient_profile_obj.id)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Recipient user not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": f"Error finding recipient: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
        if sender_profile == recipient_profile:
             return Response({"detail": "Cannot transfer to self."}, status=status.HTTP_400_BAD_REQUEST)

        # Execute Transfer
        sender_profile.comrade_balance -= float(amount)
        recipient_profile.comrade_balance += float(amount)
        
        sender_profile.save()
        recipient_profile.save()
        
        # Log Transaction
        token = TransactionToken.objects.create(
            payment_profile=sender_profile,
            recipient_profile=recipient_profile,
            amount=amount,
            transaction_type='transfer',
            payment_option='comrade_balance',
            description=f"Transfer to {recipient_email}"
        )

        TransactionHistory.objects.create(
            payment_profile=sender_profile,
            transaction_token=token,
            transaction_category='transfer',
            payment_type='individual',
            status='completed',
            amount=amount
        )
        
        # We should also log for recipient seeing as they received money? 
        # Usually checking histories filters by payment_profile OR recipient_profile if implemented.
        # But let's stick to the sender log for now as the token links both.

        return Response({
            "detail": "Transfer successful.",
            "new_balance": sender_profile.comrade_balance,
            "transaction_code": token.transaction_code
        })
