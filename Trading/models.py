from django.db import models
from django.conf import settings
from django.utils import timezone


class CryptoAsset(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10, unique=True)
    name_plural = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(blank=True)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    market_cap = models.DecimalField(max_digits=30, decimal_places=2, default=0)
    volume_24h = models.DecimalField(max_digits=30, decimal_places=2, default=0)
    price_change_24h = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_change_percent_24h = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    min_trade_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0.0001)
    max_trade_amount = models.DecimalField(max_digits=20, decimal_places=8, default=1000000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class Wallet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trading_wallets')
    crypto = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='wallets')
    balance = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    locked_balance = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'crypto')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.email} - {self.crypto.symbol}"

    @property
    def available_balance(self):
        return self.balance - self.locked_balance


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=30, decimal_places=8)
    fee = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    total_amount = models.DecimalField(max_digits=30, decimal_places=8)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.transaction_type} - {self.amount}"


class Trade(models.Model):
    ORDER_TYPES = (
        ('market', 'Market'),
        ('limit', 'Limit'),
    )

    ORDER_SIDES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trades')
    crypto = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='trades')
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES)
    side = models.CharField(max_length=10, choices=ORDER_SIDES)
    quantity = models.DecimalField(max_digits=30, decimal_places=8)
    price = models.DecimalField(max_digits=30, decimal_places=8)
    total = models.DecimalField(max_digits=30, decimal_places=8)
    fee = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.side} {self.quantity} {self.crypto.symbol}"


class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portfolios')
    crypto = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='portfolio_items')
    quantity = models.DecimalField(max_digits=30, decimal_places=8)
    avg_buy_price = models.DecimalField(max_digits=30, decimal_places=8)
    current_price = models.DecimalField(max_digits=30, decimal_places=8)
    total_value = models.DecimalField(max_digits=30, decimal_places=8)
    profit_loss = models.DecimalField(max_digits=30, decimal_places=8)
    profit_loss_percent = models.DecimalField(max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        unique_together = ('user', 'crypto', 'recorded_at')

    def __str__(self):
        return f"{self.user.email} - {self.crypto.symbol}"


class TradingPair(models.Model):
    base_crypto = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='base_pairs')
    quote_crypto = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='quote_pairs')
    min_order_size = models.DecimalField(max_digits=30, decimal_places=8, default=0.0001)
    max_order_size = models.DecimalField(max_digits=30, decimal_places=8, default=1000000)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.1)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('base_crypto', 'quote_crypto')

    def __str__(self):
        return f"{self.base_crypto.symbol}/{self.quote_crypto.symbol}"


class Order(models.Model):
    ORDER_TYPES = (
        ('market', 'Market'),
        ('limit', 'Limit'),
    )

    ORDER_SIDES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('filled', 'Filled'),
        ('partially_filled', 'Partially Filled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    trading_pair = models.ForeignKey(TradingPair, on_delete=models.CASCADE, related_name='orders')
    order_type = models.CharField(max_length=10, choices=ORDER_TYPES)
    side = models.CharField(max_length=10, choices=ORDER_SIDES)
    quantity = models.DecimalField(max_digits=30, decimal_places=8)
    price = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True)
    filled_quantity = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    filled_price = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference} - {self.side} {self.quantity} @ {self.price or 'market'}"