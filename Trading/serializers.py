from rest_framework import serializers
from django.utils import timezone
from .models import CryptoAsset, Wallet, WalletTransaction, Trade, Portfolio, TradingPair, Order
import uuid


class CryptoAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CryptoAsset
        fields = '__all__'


class WalletSerializer(serializers.ModelSerializer):
    crypto = CryptoAssetSerializer(read_only=True)
    available_balance = serializers.DecimalField(max_digits=30, decimal_places=8, read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'crypto', 'balance', 'locked_balance', 'available_balance', 'created_at', 'updated_at']


class WalletDetailSerializer(serializers.ModelSerializer):
    crypto = CryptoAssetSerializer(read_only=True)
    available_balance = serializers.DecimalField(max_digits=30, decimal_places=8, read_only=True)
    transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['id', 'crypto', 'balance', 'locked_balance', 'available_balance', 'transactions', 'created_at', 'updated_at']

    def get_transactions(self, obj):
        transactions = obj.transactions.all()[:10]
        return WalletTransactionSerializer(transactions, many=True).data


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = '__all__'


class DepositSerializer(serializers.Serializer):
    crypto_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=30, decimal_places=8)
    payment_method = serializers.CharField(max_length=50)
    reference = serializers.CharField(max_length=100, required=False)

    def validate(self, data):
        if data['amount'] <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return data


class WithdrawSerializer(serializers.Serializer):
    crypto_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=30, decimal_places=8)
    wallet_address = serializers.CharField(max_length=200)

    def validate(self, data):
        if data['amount'] <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return data


class TradeSerializer(serializers.ModelSerializer):
    crypto = CryptoAssetSerializer(read_only=True)

    class Meta:
        model = Trade
        fields = '__all__'


class TradeCreateSerializer(serializers.Serializer):
    crypto_id = serializers.IntegerField()
    side = serializers.ChoiceField(choices=['buy', 'sell'])
    quantity = serializers.DecimalField(max_digits=30, decimal_places=8)
    order_type = serializers.ChoiceField(choices=['market', 'limit'])
    price = serializers.DecimalField(max_digits=30, decimal_places=8, required=False, allow_null=True)

    def validate(self, data):
        if data['order_type'] == 'limit' and not data.get('price'):
            raise serializers.ValidationError("Price is required for limit orders")
        if data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        if data['order_type'] == 'limit' and data['price'] <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return data


class PortfolioSerializer(serializers.ModelSerializer):
    crypto = CryptoAssetSerializer(read_only=True)

    class Meta:
        model = Portfolio
        fields = '__all__'


class PortfolioSummarySerializer(serializers.Serializer):
    total_value = serializers.DecimalField(max_digits=30, decimal_places=2)
    total_profit_loss = serializers.DecimalField(max_digits=30, decimal_places=2)
    total_profit_loss_percent = serializers.DecimalField(max_digits=10, decimal_places=2)
    assets = PortfolioSerializer(many=True)


class TradingPairSerializer(serializers.ModelSerializer):
    base_crypto = CryptoAssetSerializer(read_only=True)
    quote_crypto = CryptoAssetSerializer(read_only=True)

    class Meta:
        model = TradingPair
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    trading_pair = TradingPairSerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


class OrderCreateSerializer(serializers.Serializer):
    trading_pair_id = serializers.IntegerField()
    order_type = serializers.ChoiceField(choices=['market', 'limit'])
    side = serializers.ChoiceField(choices=['buy', 'sell'])
    quantity = serializers.DecimalField(max_digits=30, decimal_places=8)
    price = serializers.DecimalField(max_digits=30, decimal_places=8, required=False, allow_null=True)

    def validate(self, data):
        if data['order_type'] == 'limit' and not data.get('price'):
            raise serializers.ValidationError("Price is required for limit orders")
        if data['quantity'] <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return data


class MarketStatsSerializer(serializers.Serializer):
    total_portfolio_value = serializers.DecimalField(max_digits=30, decimal_places=2)
    top_performers = PortfolioSerializer(many=True)
    worst_performers = PortfolioSerializer(many=True)
    recent_trades = TradeSerializer(many=True)