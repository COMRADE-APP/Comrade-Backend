from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db.models import Sum, Avg, Count
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import uuid
import secrets

from .models import CryptoAsset, Wallet, WalletTransaction, Trade, Portfolio, TradingPair, Order
from .serializers import (
    CryptoAssetSerializer, WalletSerializer, WalletDetailSerializer,
    WalletTransactionSerializer, DepositSerializer, WithdrawSerializer,
    TradeSerializer, TradeCreateSerializer, PortfolioSerializer,
    PortfolioSummarySerializer, TradingPairSerializer, OrderSerializer,
    OrderCreateSerializer, MarketStatsSerializer
)


def generate_reference():
    return f"TRD-{uuid.uuid4().hex[:12].upper()}"


class CryptoAssetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CryptoAsset.objects.filter(is_active=True)
    serializer_class = CryptoAssetSerializer
    permission_classes = [AllowAny]
    search_fields = ['name', 'symbol']
    filterset_fields = ['symbol']


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WalletDetailSerializer
        return WalletSerializer

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        wallet = self.get_object()
        transactions = wallet.transactions.all()
        serializer = WalletTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


class DepositView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DepositSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        crypto_id = serializer.validated_data['crypto_id']
        amount = serializer.validated_data['amount']
        payment_method = serializer.validated_data['payment_method']

        try:
            crypto = CryptoAsset.objects.get(id=crypto_id, is_active=True)
        except CryptoAsset.DoesNotExist:
            return Response({'error': 'Cryptocurrency not found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            wallet, created = Wallet.objects.get_or_create(
                user=request.user,
                crypto=crypto,
                defaults={'balance': 0, 'locked_balance': 0}
            )

            wallet.balance += amount
            wallet.save()

            reference = serializer.validated_data.get('reference') or generate_reference()
            while WalletTransaction.objects.filter(reference=reference).exists():
                reference = generate_reference()

            tx = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='deposit',
                amount=amount,
                fee=0,
                total_amount=amount,
                status='completed',
                reference=reference,
                description=f"Deposit via {payment_method}",
                completed_at=timezone.now()
            )

        return Response({
            'message': 'Deposit successful',
            'transaction': WalletTransactionSerializer(tx).data,
            'wallet': WalletSerializer(wallet).data
        }, status=status.HTTP_201_CREATED)


class WithdrawView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        crypto_id = serializer.validated_data['crypto_id']
        amount = serializer.validated_data['amount']
        wallet_address = serializer.validated_data['wallet_address']

        try:
            crypto = CryptoAsset.objects.get(id=crypto_id, is_active=True)
        except CryptoAsset.DoesNotExist:
            return Response({'error': 'Cryptocurrency not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            wallet = Wallet.objects.get(user=request.user, crypto=crypto)
        except Wallet.DoesNotExist:
            return Response({'error': 'Wallet not found'}, status=status.HTTP_404_NOT_FOUND)

        if wallet.available_balance < amount:
            return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            wallet.balance -= amount
            wallet.save()

            reference = generate_reference()
            while WalletTransaction.objects.filter(reference=reference).exists():
                reference = generate_reference()

            fee = amount * Decimal('0.001')
            total = amount - fee

            tx = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='withdraw',
                amount=amount,
                fee=fee,
                total_amount=total,
                status='completed',
                reference=reference,
                description=f"Withdrawal to {wallet_address}",
                completed_at=timezone.now()
            )

        return Response({
            'message': 'Withdrawal initiated',
            'transaction': WalletTransactionSerializer(tx).data,
            'wallet': WalletSerializer(wallet).data
        }, status=status.HTTP_201_CREATED)


class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Trade.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def execute(self, request):
        serializer = TradeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        crypto_id = serializer.validated_data['crypto_id']
        side = serializer.validated_data['side']
        quantity = serializer.validated_data['quantity']
        order_type = serializer.validated_data['order_type']
        price = serializer.validated_data.get('price')

        try:
            crypto = CryptoAsset.objects.get(id=crypto_id, is_active=True)
        except CryptoAsset.DoesNotExist:
            return Response({'error': 'Cryptocurrency not found'}, status=status.HTTP_404_NOT_FOUND)

        if order_type == 'market':
            execution_price = crypto.current_price
        else:
            execution_price = price

        total = quantity * execution_price
        fee = total * Decimal('0.001')

        try:
            wallet = Wallet.objects.get(user=request.user, crypto=crypto)
        except Wallet.DoesNotExist:
            wallet = Wallet.objects.create(user=request.user, crypto=crypto, balance=0, locked_balance=0)

        with transaction.atomic():
            if side == 'buy':
                quote_currency, _ = CryptoAsset.objects.get_or_create(
                    symbol='USDT',
                    defaults={'name': 'Tether', 'name_plural': 'Tethers', 'is_active': True}
                )
                try:
                    quote_wallet = Wallet.objects.get(user=request.user, crypto=quote_currency)
                except Wallet.DoesNotExist:
                    return Response({'error': 'No USDT wallet found. Please deposit USDT first.'}, status=status.HTTP_400_BAD_REQUEST)

                total_cost = total + fee
                if quote_wallet.available_balance < total_cost:
                    return Response({'error': 'Insufficient USDT balance'}, status=status.HTTP_400_BAD_REQUEST)

                quote_wallet.balance -= total_cost
                quote_wallet.save()

                WalletTransaction.objects.create(
                    wallet=quote_wallet,
                    transaction_type='buy',
                    amount=total,
                    fee=fee,
                    total_amount=total_cost,
                    status='completed',
                    reference=generate_reference(),
                    description=f"Bought {quantity} {crypto.symbol}",
                    completed_at=timezone.now()
                )

                wallet.balance += quantity
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='buy',
                    amount=quantity,
                    fee=0,
                    total_amount=quantity,
                    status='completed',
                    reference=generate_reference(),
                    description=f"Received {quantity} {crypto.symbol}",
                    completed_at=timezone.now()
                )

            else:
                if wallet.available_balance < quantity:
                    return Response({'error': 'Insufficient crypto balance'}, status=status.HTTP_400_BAD_REQUEST)

                wallet.balance -= quantity
                wallet.save()

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='sell',
                    amount=quantity,
                    fee=0,
                    total_amount=quantity,
                    status='completed',
                    reference=generate_reference(),
                    description=f"Sent {quantity} {crypto.symbol}",
                    completed_at=timezone.now()
                )

                quote_currency, _ = CryptoAsset.objects.get_or_create(
                    symbol='USDT',
                    defaults={'name': 'Tether', 'name_plural': 'Tethers', 'is_active': True}
                )
                try:
                    quote_wallet = Wallet.objects.get(user=request.user, crypto=quote_currency)
                except Wallet.DoesNotExist:
                    quote_wallet = Wallet.objects.create(user=request.user, crypto=quote_currency, balance=0, locked_balance=0)

                total_proceeds = total - fee
                quote_wallet.balance += total_proceeds
                quote_wallet.save()

                WalletTransaction.objects.create(
                    wallet=quote_wallet,
                    transaction_type='sell',
                    amount=total,
                    fee=fee,
                    total_amount=total_proceeds,
                    status='completed',
                    reference=generate_reference(),
                    description=f"Sold {quantity} {crypto.symbol}",
                    completed_at=timezone.now()
                )

            trade = Trade.objects.create(
                user=request.user,
                crypto=crypto,
                order_type=order_type,
                side=side,
                quantity=quantity,
                price=execution_price,
                total=total,
                fee=fee,
                status='completed',
                reference=generate_reference(),
                executed_at=timezone.now()
            )

            self._update_portfolio(request.user)

        return Response({
            'message': 'Trade executed successfully',
            'trade': TradeSerializer(trade).data
        }, status=status.HTTP_201_CREATED)

    def _update_portfolio(self, user):
        wallets = Wallet.objects.filter(user=user, balance__gt=0)
        now = timezone.now()

        Portfolio.objects.filter(user=user, recorded_at__lt=now - timezone.timedelta(hours=1)).delete()

        for wallet in wallets:
            current_value = wallet.balance * wallet.crypto.current_price
            portfolio_items = Portfolio.objects.filter(user=user, crypto=wallet.crypto)
            if portfolio_items.exists():
                avg_price = portfolio_items.first().avg_buy_price
            else:
                avg_price = wallet.crypto.current_price

            profit_loss = current_value - (wallet.balance * avg_price)
            profit_loss_percent = (profit_loss / (wallet.balance * avg_price) * 100) if avg_price > 0 else 0

            Portfolio.objects.create(
                user=user,
                crypto=wallet.crypto,
                quantity=wallet.balance,
                avg_buy_price=avg_price,
                current_price=wallet.crypto.current_price,
                total_value=current_value,
                profit_loss=profit_loss,
                profit_loss_percent=profit_loss_percent
            )


class PortfolioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        portfolios = self.get_queryset()

        total_value = sum(p.total_value for p in portfolios)
        total_cost = sum(p.quantity * p.avg_buy_price for p in portfolios)
        total_profit_loss = total_value - total_cost
        total_profit_loss_percent = (total_profit_loss / total_cost * 100) if total_cost > 0 else 0

        return Response({
            'total_value': total_value,
            'total_profit_loss': total_profit_loss,
            'total_profit_loss_percent': total_profit_loss_percent,
            'assets': PortfolioSerializer(portfolios, many=True).data
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        portfolios = self.get_queryset()
        trades = Trade.objects.filter(user=request.user).order_by('-created_at')[:10]

        top_performers = sorted(portfolios, key=lambda x: x.profit_loss_percent, reverse=True)[:3]
        worst_performers = sorted(portfolios, key=lambda x: x.profit_loss_percent)[:3]

        return Response({
            'total_portfolio_value': sum(p.total_value for p in portfolios),
            'top_performers': PortfolioSerializer(top_performers, many=True).data,
            'worst_performers': PortfolioSerializer(worst_performers, many=True).data,
            'recent_trades': TradeSerializer(trades, many=True).data
        })


class TradingPairViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TradingPair.objects.filter(is_active=True)
    serializer_class = TradingPairSerializer
    permission_classes = [AllowAny]


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        trading_pair_id = serializer.validated_data['trading_pair_id']
        order_type = serializer.validated_data['order_type']
        side = serializer.validated_data['side']
        quantity = serializer.validated_data['quantity']
        price = serializer.validated_data.get('price')

        try:
            trading_pair = TradingPair.objects.get(id=trading_pair_id, is_active=True)
        except TradingPair.DoesNotExist:
            return Response({'error': 'Trading pair not found'}, status=status.HTTP_404_NOT_FOUND)

        if quantity < trading_pair.min_order_size or quantity > trading_pair.max_order_size:
            return Response({'error': 'Quantity outside allowed range'}, status=status.HTTP_400_BAD_REQUEST)

        crypto = trading_pair.base_crypto

        if order_type == 'market':
            execution_price = crypto.current_price
        else:
            execution_price = price

        total = quantity * execution_price

        if side == 'buy':
            quote_crypto = trading_pair.quote_crypto
            try:
                quote_wallet = Wallet.objects.get(user=request.user, crypto=quote_crypto)
            except Wallet.DoesNotExist:
                return Response({'error': f'No {quote_crypto.symbol} wallet found'}, status=status.HTTP_400_BAD_REQUEST)

            if quote_wallet.available_balance < total:
                return Response({'error': 'Insufficient balance'}, status=status.HTTP_400_BAD_REQUEST)

            quote_wallet.locked_balance += total
            quote_wallet.save()
        else:
            try:
                wallet = Wallet.objects.get(user=request.user, crypto=crypto)
            except Wallet.DoesNotExist:
                return Response({'error': f'No {crypto.symbol} wallet found'}, status=status.HTTP_400_BAD_REQUEST)

            if wallet.available_balance < quantity:
                return Response({'error': 'Insufficient crypto balance'}, status=status.HTTP_400_BAD_REQUEST)

            wallet.locked_balance += quantity
            wallet.save()

        reference = generate_reference()
        while Order.objects.filter(reference=reference).exists():
            reference = generate_reference()

        expires_at = None
        if order_type == 'limit':
            from datetime import timedelta
            expires_at = timezone.now() + timedelta(days=7)

        order = Order.objects.create(
            user=request.user,
            trading_pair=trading_pair,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            status='pending',
            reference=reference,
            expires_at=expires_at
        )

        if order_type == 'market':
            self._execute_market_order(order)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def _execute_market_order(self, order):
        crypto = order.trading_pair.base_crypto
        execution_price = crypto.current_price

        with transaction.atomic():
            order.filled_quantity = order.quantity
            order.filled_price = execution_price
            order.status = 'filled'

            if order.side == 'buy':
                try:
                    base_wallet = Wallet.objects.get(user=order.user, crypto=crypto)
                except Wallet.DoesNotExist:
                    base_wallet = Wallet.objects.create(user=order.user, crypto=crypto, balance=0, locked_balance=0)

                base_wallet.balance += order.quantity
                base_wallet.locked_balance -= order.quantity * execution_price
                base_wallet.save()

                quote_wallet = Wallet.objects.get(user=order.user, crypto=order.trading_pair.quote_crypto)
                quote_wallet.locked_balance -= order.quantity * execution_price
                quote_wallet.save()

                WalletTransaction.objects.create(
                    wallet=base_wallet,
                    transaction_type='buy',
                    amount=order.quantity,
                    fee=0,
                    total_amount=order.quantity,
                    status='completed',
                    reference=generate_reference(),
                    description=f"Order {order.reference} executed",
                    completed_at=timezone.now()
                )
            else:
                base_wallet = Wallet.objects.get(user=order.user, crypto=crypto)
                base_wallet.balance -= order.quantity
                base_wallet.locked_balance -= order.quantity
                base_wallet.save()

                quote_wallet, _ = Wallet.objects.get_or_create(
                    user=order.user,
                    crypto=order.trading_pair.quote_crypto,
                    defaults={'balance': 0, 'locked_balance': 0}
                )
                quote_wallet.locked_balance -= order.quantity * execution_price
                total_proceeds = order.quantity * execution_price
                quote_wallet.balance += total_proceeds
                quote_wallet.save()

            order.save()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()

        if order.status != 'pending':
            return Response({'error': 'Only pending orders can be cancelled'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if order.side == 'buy':
                quote_wallet = Wallet.objects.get(user=request.user, crypto=order.trading_pair.quote_crypto)
                quote_wallet.locked_balance -= order.quantity * (order.price or order.trading_pair.base_crypto.current_price)
                quote_wallet.save()
            else:
                base_wallet = Wallet.objects.get(user=request.user, crypto=order.trading_pair.base_crypto)
                base_wallet.locked_balance -= order.quantity
                base_wallet.save()

            order.status = 'cancelled'
            order.save()

        return Response({'message': 'Order cancelled', 'order': OrderSerializer(order).data})


class MarketOverviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cryptos = CryptoAsset.objects.filter(is_active=True).order_by('-market_cap')[:20]
        serializer = CryptoAssetSerializer(cryptos, many=True)
        return Response(serializer.data)


class PriceHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, crypto_id):
        try:
            crypto = CryptoAsset.objects.get(id=crypto_id)
        except CryptoAsset.DoesNotExist:
            return Response({'error': 'Cryptocurrency not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'crypto': CryptoAssetSerializer(crypto).data,
            'current_price': crypto.current_price,
            'price_change_24h': crypto.price_change_24h,
            'price_change_percent_24h': crypto.price_change_percent_24h,
            'volume_24h': crypto.volume_24h,
            'market_cap': crypto.market_cap
        })