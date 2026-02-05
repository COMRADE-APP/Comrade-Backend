from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import PaymentProfile, TransactionToken, TransactionHistory, PaymentLog
from .serializers import TransactionTokenSerializer, PaymentProfileSerializer
from .utils import check_purchase_limit, increment_purchase_count
from Authentication.models import Profile

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
            
        # Simulate API check
        # For demo purposes, we return a mock name based on the number presence
        if len(str(account_number)) < 5:
             return Response(
                {"detail": "Invalid account number."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mock response
        return Response({
            "account_name": "JOHN DOE",
            "account_number": account_number,
            "provider": payment_method,
            "verified": True
        })


class DepositView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Initiate a deposit from an external source to Comrade Balance.
        """
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'mpesa')
        phone_number = request.data.get('phone_number')
        
        if not amount or float(amount) <= 0:
             return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = PaymentProfile.objects.select_for_update().get(user=request.user.profile)
        except PaymentProfile.DoesNotExist:
             return Response({"detail": "Payment profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Create Pending Transaction
        token = TransactionToken.objects.create(
            payment_profile=profile,
            amount=amount,
            transaction_type='deposit',
            payment_option=payment_method,
            payment_number=phone_number if phone_number else profile.payment_number,
            description=f"Deposit via {payment_method}"
        )

        # 1. Trigger STK Push or Payment Gateway Request here (Simulated success)
        # In real world: Wait for callback. For demo: Immediate success.
        
        # Update Balance
        profile.comrade_balance += float(amount)
        profile.save()

        # Log History
        TransactionHistory.objects.create(
            payment_profile=profile,
            transaction_token=token,
            transaction_category='deposit',
            payment_type='individual',
            status='completed',
            amount=amount
        )
        
        return Response({
            "detail": "Deposit successful.",
            "new_balance": profile.comrade_balance,
            "transaction_code": token.transaction_code
        })


class WithdrawView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Withdraw from Comrade Balance to external account.
        """
        amount = request.data.get('amount')
        account_number = request.data.get('account_number')
        payment_method = request.data.get('payment_method', 'mpesa')
        
        if not amount or float(amount) <= 0:
             return Response({"detail": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = PaymentProfile.objects.select_for_update().get(user=request.user.profile)
        except PaymentProfile.DoesNotExist:
             return Response({"detail": "Payment profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if profile.comrade_balance < float(amount):
            return Response({"detail": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        # Create Pending Transaction
        token = TransactionToken.objects.create(
            payment_profile=profile,
            amount=amount,
            transaction_type='withdrawal',
            payment_option=payment_method,
            payment_number=account_number,
            description=f"Withdrawal to {payment_method} - {account_number}"
        )

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
             
        sender_profile = get_object_or_404(PaymentProfile.objects.select_for_update(), user=request.user.profile)
        
        if sender_profile.comrade_balance < float(amount):
            return Response({"detail": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Find recipient
        try:
            recipient_user = Profile.objects.get(user__email=recipient_email)
            recipient_profile = PaymentProfile.objects.select_for_update().get(user=recipient_user)
        except (Profile.DoesNotExist, PaymentProfile.DoesNotExist):
            return Response({"detail": "Recipient not found."}, status=status.HTTP_404_NOT_FOUND)
            
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
