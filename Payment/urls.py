from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Payment import views
import Payment.views_automation as views_automation
from Payment.views_payment import (
    PaymentMethodViewSet, ProcessPaymentView, RefundPaymentView,
    StripeWebhookView, PayPalWebhookView, MpesaCallbackView,
    FlutterwaveWebhookView, PesapalIPNView, GatewayConfigView,
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

# Kitties (sub-funds)
router.register(r'kitties', views.KittyViewSet, basename='kitty')

# Group Investments
router.register(r'group-investments', views.GroupInvestmentViewSet, basename='group-investment')

# Advanced Group Features
router.register(r'round-contributions', views.RoundContributionViewSet, basename='round-contribution')
router.register(r'round-positions', views.RoundPositionViewSet, basename='round-position')
router.register(r'withdrawal-requests', views.WithdrawalRequestViewSet, basename='withdrawal-request')
router.register(r'benefit-rules', views.BenefitDistributionRuleViewSet, basename='benefit-rule')
router.register(r'group-settings-changes', views.GroupSettingsChangeRequestViewSet, basename='group-settings-change')

# Provider Management
router.register(r'provider-registrations', views.ProviderRegistrationViewSet, basename='provider-registration')
router.register(r'provider-documents', views.ProviderDocumentViewSet, basename='provider-document')
router.register(r'provider-staff', views.ProviderStaffViewSet, basename='provider-staff')
router.register(r'service-products', views.ServiceProductViewSet, basename='service-product')
router.register(r'provider-transactions', views.ProviderTransactionViewSet, basename='provider-transaction')
router.register(r'provider-queries', views.ProviderQueryViewSet, basename='provider-query')
router.register(r'provider-applications', views.ProviderApplicationViewSet, basename='provider-application')
router.register(r'provider-notifications', views.ProviderNotificationViewSet, basename='provider-notification')

urlpatterns = [
    path('', include(router.urls)),
    
    # Gateway Configuration
    path('gateway-config/', GatewayConfigView.as_view(), name='gateway-config'),
    
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
    path('flutterwave/webhook/', FlutterwaveWebhookView.as_view(), name='flutterwave-webhook'),
    path('pesapal/ipn/', PesapalIPNView.as_view(), name='pesapal-ipn'),
    
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
    
    # Group Analytics
    path('groups/<uuid:group_id>/group-analytics/', views.GroupAnalyticsView.as_view(), name='group-analytics'),
    
    # Admin Management Routes
    path('admin/bills/', views.AdminBillPaymentViewSet.as_view({'get': 'list', 'post': 'bulk_action'}), name='admin-bills'),
    path('admin/bills/stats/', views.AdminBillPaymentViewSet.as_view({'get': 'stats'}), name='admin-bills-stats'),
    path('admin/loans/', views.AdminLoanApplicationViewSet.as_view({'get': 'list', 'post': 'bulk_action'}), name='admin-loans'),
    path('admin/loans/stats/', views.AdminLoanApplicationViewSet.as_view({'get': 'stats'}), name='admin-loans-stats'),
    path('admin/insurance/', views.AdminInsuranceClaimViewSet.as_view({'get': 'list', 'post': 'bulk_action'}), name='admin-insurance'),
    path('admin/insurance/stats/', views.AdminInsuranceClaimViewSet.as_view({'get': 'stats'}), name='admin-insurance-stats'),
    path('admin/transactions/', views.AdminTransactionViewSet.as_view({'get': 'list'}), name='admin-transactions'),
    path('admin/transactions/stats/', views.AdminTransactionViewSet.as_view({'get': 'stats'}), name='admin-transactions-stats'),
    path('admin/kitties/', views.AdminKittyViewSet.as_view({'get': 'list', 'patch': 'partial_update'}), name='admin-kitties'),
    path('admin/kitties/stats/', views.AdminKittyViewSet.as_view({'get': 'stats'}), name='admin-kitties-stats'),
    path('admin/kitties/<uuid:pk>/freeze/', views.AdminKittyViewSet.as_view({'post': 'freeze'}), name='admin-kitty-freeze'),
    path('admin/kitties/<uuid:pk>/unfreeze/', views.AdminKittyViewSet.as_view({'post': 'unfreeze'}), name='admin-kitty-unfreeze'),
    
    # Automation & Utility Routes
    path('currency/convert/', views_automation.CurrencyConversionView.as_view({'get': 'convert'}), name='currency-convert'),
    path('currency/rates/', views_automation.CurrencyConversionView.as_view({'get': 'rates'}), name='currency-rates'),
    path('notifications/send/', views_automation.NotificationServiceView.as_view({'post': 'send'}), name='notification-send'),
    path('webhooks/stripe/', views_automation.WebhookHandlerView.as_view({'post': 'stripe'}), name='webhook-stripe'),
    path('webhooks/mpesa/', views_automation.WebhookHandlerView.as_view({'post': 'mpesa'}), name='webhook-mpesa'),
    path('webhooks/paypal/', views_automation.WebhookHandlerView.as_view({'post': 'paypal'}), name='webhook-paypal'),
    path('tasks/process-standing-orders/', views_automation.ScheduledTasksView.as_view({'post': 'process_standing_orders'}), name='task-standing-orders'),
    path('tasks/check-loan-overdue/', views_automation.ScheduledTasksView.as_view({'post': 'check_loan_overdue'}), name='task-loan-overdue'),
    path('tasks/check-insurance-expiry/', views_automation.ScheduledTasksView.as_view({'post': 'check_insurance_expiry'}), name='task-insurance-expiry'),
    path('analytics/dashboard/', views_automation.AnalyticsView.as_view({'get': 'dashboard'}), name='analytics-dashboard'),
    path('security/rate-limit/', views_automation.SecurityView.as_view({'get': 'check_rate_limit'}), name='security-rate-limit'),
    path('security/report-suspicious/', views_automation.SecurityView.as_view({'post': 'report_suspicious'}), name='security-report'),
]

