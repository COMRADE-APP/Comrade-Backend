from django.contrib import admin
from .models import CryptoAsset, Wallet, WalletTransaction, Trade, Portfolio, TradingPair, Order


@admin.register(CryptoAsset)
class CryptoAssetAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'current_price', 'is_active', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name', 'symbol']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'crypto', 'balance', 'locked_balance', 'updated_at']
    list_filter = ['crypto']
    search_fields = ['user__email', 'crypto__symbol']


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'wallet', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status']
    search_fields = ['reference', 'wallet__user__email']


@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'crypto', 'side', 'quantity', 'price', 'status', 'created_at']
    list_filter = ['side', 'status']
    search_fields = ['reference', 'user__email', 'crypto__symbol']


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ['user', 'crypto', 'quantity', 'total_value', 'profit_loss', 'profit_loss_percent', 'recorded_at']
    list_filter = ['crypto']
    search_fields = ['user__email', 'crypto__symbol']


@admin.register(TradingPair)
class TradingPairAdmin(admin.ModelAdmin):
    list_display = ['base_crypto', 'quote_crypto', 'fee_percent', 'is_active']
    list_filter = ['is_active']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'trading_pair', 'side', 'quantity', 'price', 'status', 'created_at']
    list_filter = ['side', 'status', 'order_type']
    search_fields = ['reference', 'user__email']