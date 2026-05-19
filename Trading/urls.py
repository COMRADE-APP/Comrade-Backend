from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CryptoAssetViewSet, WalletViewSet, DepositView, WithdrawView,
    TradeViewSet, PortfolioViewSet, TradingPairViewSet, OrderViewSet,
    MarketOverviewView, PriceHistoryView
)

router = DefaultRouter()
router.register(r'assets', CryptoAssetViewSet, basename='crypto-assets')
router.register(r'wallets', WalletViewSet, basename='wallets')
router.register(r'trades', TradeViewSet, basename='trades')
router.register(r'portfolio', PortfolioViewSet, basename='portfolio')
router.register(r'pairs', TradingPairViewSet, basename='trading-pairs')
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('', include(router.urls)),
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('withdraw/', WithdrawView.as_view(), name='withdraw'),
    path('market/', MarketOverviewView.as_view(), name='market-overview'),
    path('price/<int:crypto_id>/', PriceHistoryView.as_view(), name='price-history'),
]