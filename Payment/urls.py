from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Payment import views
from Payment.views_payment import (
    PaymentMethodViewSet, ProcessPaymentView, RefundPaymentView,
    StripeWebhookView, PayPalWebhookView, MpesaCallbackView
)

router = DefaultRouter()
router.register(r'profiles', views.PaymentProfileViewSet, basename='payment-profile')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'groups', views.PaymentGroupsViewSet, basename='payment-group')
router.register(r'items', views.PaymentItemViewSet, basename='payment-item')
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'subscriptions', views.UserSubscriptionViewSet, basename='subscription')
router.register(r'targets', views.GroupTargetViewSet, basename='target')

urlpatterns = [
    path('', include(router.urls)),
    
    # Payment processing
    path('process/', ProcessPaymentView.as_view(), name='process-payment'),
    path('refund/', RefundPaymentView.as_view(), name='refund-payment'),
    
    # Webhooks
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('paypal/webhook/', PayPalWebhookView.as_view(), name='paypal-webhook'),
    path('mpesa/callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
]
