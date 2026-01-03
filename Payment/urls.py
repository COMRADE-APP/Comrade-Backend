from django.urls import path
from rest_framework.routers import DefaultRouter
# Simplified to only import what exists
from Payment import views

router = DefaultRouter()

# Register only routes that correspond to actual views
router.register('products', views.ProductViewSet, basename='product')
router.register('targets', views.GroupTargetViewSet, basename='grouptarget')
router.register('subscriptions', views.UserSubscriptionViewSet, basename='usersubscription')

urlpatterns = []
urlpatterns += router.urls
