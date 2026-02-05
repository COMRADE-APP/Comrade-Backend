from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Payment import views
from Payment.views_payment import (
    PaymentMethodViewSet, ProcessPaymentView, RefundPaymentView,
    StripeWebhookView, PayPalWebhookView, MpesaCallbackView
)
from Payment.views_transactions import (
    DepositView, WithdrawView, TransferView, VerifyAccountView
)

router = DefaultRouter()
router.register(r'profiles', views.PaymentProfileViewSet, basename='payment-profile')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'groups', views.PaymentGroupsViewSet, basename='payment-group')
router.register(r'invitations', views.GroupInvitationViewSet, basename='invitation')
router.register(r'items', views.PaymentItemViewSet, basename='payment-item')
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'subscriptions', views.UserSubscriptionViewSet, basename='subscription')
router.register(r'targets', views.GroupTargetViewSet, basename='target')
router.register(r'partners', views.PartnerViewSet, basename='partner')
router.register(r'partner-applications', views.PartnerApplicationViewSet, basename='partner-application')
router.register(r'agent-applications', views.AgentApplicationViewSet, basename='agent-application')
router.register(r'supplier-applications', views.SupplierApplicationViewSet, basename='supplier-application')
router.register(r'shop-registrations', views.ShopRegistrationViewSet, basename='shop-registration')

urlpatterns = [
    path('', include(router.urls)),
    
    # Payment processing
    path('process/', ProcessPaymentView.as_view(), name='process-payment'),
    path('refund/', RefundPaymentView.as_view(), name='refund-payment'),
    
    # Transaction Actions
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('withdraw/', WithdrawView.as_view(), name='withdraw'),
    path('transfer/', TransferView.as_view(), name='transfer'),
    path('verify-account/', VerifyAccountView.as_view(), name='verify-account'),
    
    # Webhooks
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('paypal/webhook/', PayPalWebhookView.as_view(), name='paypal-webhook'),
    path('mpesa/callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
]
