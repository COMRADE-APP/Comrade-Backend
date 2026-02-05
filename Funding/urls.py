from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BusinessViewSet, FundingDocumentViewSet,
    FundingRequestViewSet, InvestmentOpportunityViewSet,
    FundingResponseViewSet, FundingNegotiationViewSet,
    FundingReactionViewSet, CapitalVentureViewSet, VentureBidViewSet
)

router = DefaultRouter()
router.register(r'businesses', BusinessViewSet)
router.register(r'documents', FundingDocumentViewSet)
router.register(r'requests', FundingRequestViewSet)
router.register(r'opportunities', InvestmentOpportunityViewSet)

# Funding interactions
router.register(r'responses', FundingResponseViewSet)
router.register(r'negotiations', FundingNegotiationViewSet)
router.register(r'reactions', FundingReactionViewSet)

# Capital ventures
router.register(r'ventures', CapitalVentureViewSet)
router.register(r'venture-bids', VentureBidViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

