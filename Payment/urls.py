from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Payment import views
from Payment.views_payment import (
    PaymentMethodViewSet, ProcessPaymentView, RefundPaymentView,
    StripeWebhookView, PayPalWebhookView, MpesaCallbackView,
    DetectPaymentMethodView
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

# Marketplace routes
router.register(r'establishments', views.EstablishmentViewSet, basename='establishment')
router.register(r'menu-items', views.MenuItemViewSet, basename='menu-item')
router.register(r'hotel-rooms', views.HotelRoomViewSet, basename='hotel-room')
router.register(r'bookings', views.BookingViewSet, basename='booking')
router.register(r'services', views.ServiceOfferingViewSet, basename='service-offering')
router.register(r'time-slots', views.ServiceTimeSlotViewSet, basename='time-slot')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'reviews', views.ReviewViewSet, basename='review')

# Group Discourse & Voting
router.register(r'join-requests', views.GroupJoinRequestViewSet, basename='join-request')
router.register(r'group-votes', views.GroupVoteViewSet, basename='group-vote')
router.register(r'group-posts', views.GroupPostViewSet, basename='group-post')
router.register(r'group-post-replies', views.GroupPostReplyViewSet, basename='group-post-reply')
router.register(r'group-phases', views.GroupPhaseViewSet, basename='group-phase')

# Bill Payments automation
router.register(r'bill-providers', views.BillProviderViewSet, basename='bill-provider')
router.register(r'service-providers', views.UserServiceProviderViewSet, basename='my-service-provider')
router.register(r'bill-payments', views.BillPaymentViewSet, basename='bill-payment')
router.register(r'standing-orders', views.BillStandingOrderViewSet, basename='standing-order')

# Loans & Credit
router.register(r'loan-products', views.LoanProductViewSet, basename='loan-product')
router.register(r'credit-scores', views.CreditScoreViewSet, basename='credit-score')
router.register(r'loan-applications', views.LoanApplicationViewSet, basename='loan-application')

# Escrow
router.register(r'escrow', views.EscrowTransactionViewSet, basename='escrow')

# Insurance
router.register(r'insurance-products', views.InsuranceProductViewSet, basename='insurance-product')
router.register(r'insurance-policies', views.InsurancePolicyViewSet, basename='insurance-policy')
router.register(r'insurance-claims', views.InsuranceClaimViewSet, basename='insurance-claim')

# Donations & Charity
router.register(r'donations', views.DonationViewSet, basename='donation')

# Group Investments
router.register(r'group-investments', views.GroupInvestmentViewSet, basename='group-investment')

urlpatterns = [
    path('', include(router.urls)),
    
    # Payment processing
    path('process/', ProcessPaymentView.as_view(), name='process-payment'),
    path('refund/', RefundPaymentView.as_view(), name='refund-payment'),
    path('detect-method/', DetectPaymentMethodView.as_view(), name='detect-payment-method'),
    
    # Transaction Actions
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('withdraw/', WithdrawView.as_view(), name='withdraw'),
    path('transfer/', TransferView.as_view(), name='transfer'),
    path('verify-account/', VerifyAccountView.as_view(), name='verify-account'),
    
    # Webhooks
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('paypal/webhook/', PayPalWebhookView.as_view(), name='paypal-webhook'),
    path('mpesa/callback/', MpesaCallbackView.as_view(), name='mpesa-callback'),
    
    # Dynamic Pricing (RL Model)
    path('pricing/<int:product_id>/', views.DynamicPriceView.as_view(), name='dynamic-price'),
    path('pricing/tier-recommendation/', views.TierRecommendationView.as_view(), name='tier-recommendation'),
    path('pricing/accept/', views.PriceAcceptView.as_view(), name='pricing-accept'),
    
    # ML Monitoring
    path('ml-dashboard/', views.MLDashboardView.as_view(), name='ml-dashboard'),
    
    # Student Verification
    path('student/verify/', views.StudentVerificationView.as_view(), name='student-verify'),
    
    # Group Portfolio Analytics
    path('group-portfolio/<uuid:group_id>/', views.GroupPortfolioView.as_view(), name='group-portfolio'),
]

