from django.urls import path
from rest_framework.routers import DefaultRouter
from Payment.views import PaymentItemViewSet, PaymentLogViewSet, PaymentSlotViewSet, PaymentGroupsViewSet, PaymentProfileViewSet

router = DefaultRouter()

router.register(r'payment_profiles', PaymentProfileViewSet, 'payment_profile')
router.register(r'payment_items', PaymentItemViewSet, 'payment_item')
router.register(r'payment_logs', PaymentLogViewSet, 'payment_log')
router.register(r'payment_groups', PaymentGroupsViewSet, 'payment_group')
router.register(r'payment_slots', PaymentSlotViewSet, 'payment_slot')

urlpatterns = [

]
urlpatterns += router.urls


