from django.contrib import admin
from .models import (
    Business, FundingDocument, FundingRequest, InvestmentOpportunity,
    FundingResponse, FundingNegotiation, NegotiationMessage, FundingReaction,
    CapitalVenture, VentureBid
)

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'founder', 'industry', 'stage', 'is_charity', 'created_at')
    search_fields = ('name', 'founder__email', 'industry')
    list_filter = ('industry', 'stage', 'is_charity', 'created_at')

@admin.register(FundingDocument)
class FundingDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'business', 'doc_type', 'scan_status', 'is_viewable', 'uploaded_at')
    search_fields = ('title', 'business__name')
    list_filter = ('doc_type', 'scan_status', 'is_viewable', 'uploaded_at')

@admin.register(FundingRequest)
class FundingRequestAdmin(admin.ModelAdmin):
    list_display = ('business', 'amount_needed', 'equity_offered', 'status', 'created_at')
    search_fields = ('business__name',)
    list_filter = ('status', 'created_at')

@admin.register(InvestmentOpportunity)
class InvestmentOpportunityAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'provider', 'min_investment', 'risk_level', 'is_active')
    search_fields = ('title', 'provider')
    list_filter = ('type', 'risk_level', 'is_active')


# ==============================================================================
# FUNDING RESPONSES & INTERACTIONS
# ==============================================================================

@admin.register(FundingResponse)
class FundingResponseAdmin(admin.ModelAdmin):
    list_display = ('funding_request', 'responder', 'response_type', 'offer_amount', 'created_at')
    search_fields = ('funding_request__business__name', 'responder__email')
    list_filter = ('response_type', 'created_at')

@admin.register(FundingNegotiation)
class FundingNegotiationAdmin(admin.ModelAdmin):
    list_display = ('funding_request', 'investor', 'founder', 'is_active', 'created_at')
    search_fields = ('investor__email', 'founder__email')
    list_filter = ('is_active', 'created_at')

@admin.register(NegotiationMessage)
class NegotiationMessageAdmin(admin.ModelAdmin):
    list_display = ('negotiation', 'sender', 'is_read', 'created_at')
    search_fields = ('sender__email', 'content')
    list_filter = ('is_read', 'created_at')

@admin.register(FundingReaction)
class FundingReactionAdmin(admin.ModelAdmin):
    list_display = ('funding_request', 'user', 'reaction_type', 'created_at')
    search_fields = ('user__email',)
    list_filter = ('reaction_type', 'created_at')


# ==============================================================================
# CAPITAL VENTURES
# ==============================================================================

@admin.register(CapitalVenture)
class CapitalVentureAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_fund', 'available_fund', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('is_active', 'created_at')

@admin.register(VentureBid)
class VentureBidAdmin(admin.ModelAdmin):
    list_display = ('venture', 'funding_request', 'proposed_amount', 'proposed_equity', 'status', 'created_at')
    search_fields = ('venture__name', 'funding_request__business__name')
    list_filter = ('status', 'created_at')

