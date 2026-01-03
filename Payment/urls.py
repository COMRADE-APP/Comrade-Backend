from django.urls import path
from rest_framework.routers import DefaultRouter
from Payment import views

router = DefaultRouter()

# Payment Profile & Balance Management
router.register('payment-profiles', views.PaymentProfileViewSet, basename='payment-profile')

# Transaction Management
router.register('transactions', views.TransactionViewSet, basename='transaction')

# Payment Groups (Group Savings/Purchases)
router.register('payment-groups', views.PaymentGroupsViewSet, basename='payment-group')

# Payment Items
router.register('payment-items', views.PaymentItemViewSet, basename='payment-item')

# Shop / Product Management
router.register('products', views.ProductViewSet, basename='product')

# Piggy Bank / Group Targets
router.register('targets', views.GroupTargetViewSet, basename='grouptarget')

# Subscription Management
router.register('subscriptions', views.UserSubscriptionViewSet, basename='usersubscription')

urlpatterns = []
urlpatterns += router.urls
