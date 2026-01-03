from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Payment import views

router = DefaultRouter()
router.register(r'payment-profiles', views.PaymentProfileViewSet, basename='payment-profile')
router.register(r'transactions', views.TransactionViewSet, basename='transaction')
router.register(r'payment-groups', views.PaymentGroupsViewSet, basename='payment-group')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'subscriptions', views.UserSubscriptionViewSet, basename='subscription')
router.register(r'items', views.PaymentItemViewSet, basename='payment-item')
router.register(r'targets', views.GroupTargetViewSet, basename='group-target')

urlpatterns = [
    path('', include(router.urls)),
]
