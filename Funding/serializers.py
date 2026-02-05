from rest_framework import serializers
from .models import (
    Business, FundingDocument, FundingRequest, InvestmentOpportunity,
    FundingResponse, FundingNegotiation, NegotiationMessage, FundingReaction,
    CapitalVenture, VentureBid
)

class FundingDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingDocument
        fields = ['id', 'business', 'title', 'file', 'doc_type', 'uploaded_at', 
                  'scan_status', 'is_viewable', 'scanned_at']
        read_only_fields = ['id', 'uploaded_at', 'scan_status', 'is_viewable', 'scanned_at']

class FundingRequestSerializer(serializers.ModelSerializer):
    reactions_count = serializers.SerializerMethodField()
    responses_count = serializers.SerializerMethodField()

    class Meta:
        model = FundingRequest
        fields = ['id', 'business', 'amount_needed', 'equity_offered', 'use_of_funds', 
                  'min_investment', 'status', 'created_at', 'expires_at',
                  'reactions_count', 'responses_count']
        read_only_fields = ['id', 'created_at']

    def get_reactions_count(self, obj):
        return obj.reactions.count() if hasattr(obj, 'reactions') else 0

    def get_responses_count(self, obj):
        return obj.responses.count() if hasattr(obj, 'responses') else 0

class BusinessSerializer(serializers.ModelSerializer):
    documents = FundingDocumentSerializer(many=True, read_only=True)
    funding_requests = FundingRequestSerializer(many=True, read_only=True)
    founder_details = serializers.SerializerMethodField()
    charity_progress = serializers.ReadOnlyField()

    class Meta:
        model = Business
        fields = [
            'id', 'founder', 'name', 'industry', 'description', 'logo', 
            'stage', 'website', 'valuation', 'is_charity', 'charity_goal', 
            'charity_raised', 'charity_progress', 'created_at', 'updated_at',
            'documents', 'funding_requests', 'founder_details'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'founder']

    def get_founder_details(self, obj):
        return {
            "name": f"{obj.founder.first_name} {obj.founder.last_name}",
            "email": obj.founder.email
        }

class BusinessCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ['id', 'name', 'industry', 'description', 'stage', 'website', 
                  'valuation', 'is_charity', 'charity_goal']
        read_only_fields = ['id']

class InvestmentOpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestmentOpportunity
        fields = '__all__'


# ==============================================================================
# FUNDING RESPONSES & INTERACTIONS
# ==============================================================================

class FundingResponseSerializer(serializers.ModelSerializer):
    responder_name = serializers.SerializerMethodField()

    class Meta:
        model = FundingResponse
        fields = ['id', 'funding_request', 'responder', 'responder_name', 'response_type',
                  'content', 'offer_amount', 'equity_requested', 'created_at', 'updated_at']
        read_only_fields = ['id', 'responder', 'created_at', 'updated_at']

    def get_responder_name(self, obj):
        return f"{obj.responder.first_name} {obj.responder.last_name}".strip() or obj.responder.email


class NegotiationMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = NegotiationMessage
        fields = ['id', 'negotiation', 'sender', 'sender_name', 'content', 
                  'attachment', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip() or obj.sender.email


class FundingNegotiationSerializer(serializers.ModelSerializer):
    messages = NegotiationMessageSerializer(many=True, read_only=True)
    investor_name = serializers.SerializerMethodField()
    founder_name = serializers.SerializerMethodField()

    class Meta:
        model = FundingNegotiation
        fields = ['id', 'funding_request', 'investor', 'investor_name', 
                  'founder', 'founder_name', 'is_active', 'messages', 
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_investor_name(self, obj):
        return f"{obj.investor.first_name} {obj.investor.last_name}".strip() or obj.investor.email

    def get_founder_name(self, obj):
        return f"{obj.founder.first_name} {obj.founder.last_name}".strip() or obj.founder.email


class FundingReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundingReaction
        fields = ['id', 'funding_request', 'user', 'reaction_type', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


# ==============================================================================
# CAPITAL VENTURES
# ==============================================================================

class CapitalVentureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapitalVenture
        fields = ['id', 'name', 'description', 'organization_id', 'institution_id',
                  'total_fund', 'available_fund', 'investment_criteria',
                  'min_investment', 'max_investment', 'is_active', 
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class VentureBidSerializer(serializers.ModelSerializer):
    venture_name = serializers.SerializerMethodField()

    class Meta:
        model = VentureBid
        fields = ['id', 'venture', 'venture_name', 'funding_request', 
                  'proposed_amount', 'proposed_equity', 'terms', 'status',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_venture_name(self, obj):
        return obj.venture.name

