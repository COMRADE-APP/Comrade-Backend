from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal

CustomUser = get_user_model()


class BusinessModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='founder@example.com',
            password='pass123',
            first_name='Founder',
            last_name='User'
        )

    def test_create_business(self):
        from Funding.models import Business
        business = Business.objects.create(
            founder=self.user,
            name='Test Startup',
            industry='tech',
            description='A test startup',
            stage='idea'
        )
        self.assertEqual(business.name, 'Test Startup')
        self.assertEqual(business.industry, 'tech')
        self.assertEqual(business.stage, 'idea')
        self.assertEqual(business.founder, self.user)

    def test_business_str(self):
        from Funding.models import Business
        business = Business.objects.create(
            founder=self.user,
            name='My Business',
            industry='tech',
            description='Description'
        )
        self.assertEqual(str(business), 'My Business')

    def test_business_industry_choices(self):
        from Funding.models import Business
        industries = ['tech', 'agri', 'fin', 'retail', 'health', 'educ', 'energy', 'events', 'other']
        for industry in industries:
            business = Business.objects.create(
                founder=self.user,
                name=f'Business {industry}',
                industry=industry,
                description='Description'
            )
            self.assertEqual(business.industry, industry)

    def test_business_stage_choices(self):
        from Funding.models import Business
        stages = ['idea', 'mvp', 'pre_seed', 'seed', 'series_a', 'growth']
        for stage in stages:
            business = Business.objects.create(
                founder=self.user,
                name=f'Business {stage}',
                industry='tech',
                description='Description',
                stage=stage
            )
            self.assertEqual(business.stage, stage)

    def test_business_charity_progress(self):
        from Funding.models import Business
        business = Business.objects.create(
            founder=self.user,
            name='Charity Business',
            industry='other',
            description='Description',
            is_charity=True,
            charity_goal=Decimal('10000.00'),
            charity_raised=Decimal('2500.00')
        )
        self.assertEqual(business.charity_progress, 25.0)

    def test_business_charity_progress_no_goal(self):
        from Funding.models import Business
        business = Business.objects.create(
            founder=self.user,
            name='Charity No Goal',
            industry='other',
            description='Description',
            is_charity=True,
            charity_raised=Decimal('1000.00')
        )
        self.assertEqual(business.charity_progress, 0)

    def test_business_verification(self):
        from Funding.models import Business
        business = Business.objects.create(
            founder=self.user,
            name='Verified Business',
            industry='tech',
            description='Description',
            is_verified=True
        )
        self.assertTrue(business.is_verified)


class FundingDocumentModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='docuser@example.com',
            password='pass123'
        )
        from Funding.models import Business
        self.business = Business.objects.create(
            founder=self.user,
            name='Doc Business',
            industry='tech',
            description='Description'
        )

    def test_create_funding_document(self):
        from Funding.models import FundingDocument
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        doc = FundingDocument.objects.create(
            business=self.business,
            title='Test Document',
            file=file,
            doc_type='pitch_deck'
        )
        self.assertEqual(doc.title, 'Test Document')
        self.assertEqual(doc.doc_type, 'pitch_deck')
        self.assertEqual(doc.scan_status, 'pending')

    def test_funding_document_str(self):
        from Funding.models import FundingDocument
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        doc = FundingDocument.objects.create(
            business=self.business,
            title='My Doc',
            file=file,
            doc_type='license'
        )
        expected = f"{self.business.name} - My Doc"
        self.assertEqual(str(doc), expected)

    def test_funding_document_is_safe(self):
        from Funding.models import FundingDocument
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        doc = FundingDocument.objects.create(
            business=self.business,
            title='Clean Doc',
            file=file,
            doc_type='license',
            scan_status='clean'
        )
        self.assertTrue(doc.is_safe)

    def test_funding_document_scan_status_choices(self):
        from Funding.models import FundingDocument
        from django.core.files.uploadedfile import SimpleUploadedFile
        file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        statuses = ['pending', 'scanning', 'clean', 'malware', 'nsfw_rejected', 'error']
        for status in statuses:
            doc = FundingDocument.objects.create(
                business=self.business,
                title=f'Doc {status}',
                file=file,
                doc_type='license',
                scan_status=status
            )
            self.assertEqual(doc.scan_status, status)


class FundingRequestModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='requestuser@example.com',
            password='pass123'
        )
        from Funding.models import Business
        self.business = Business.objects.create(
            founder=self.user,
            name='Request Business',
            industry='tech',
            description='Description'
        )

    def test_create_funding_request(self):
        from Funding.models import FundingRequest
        request = FundingRequest.objects.create(
            business=self.business,
            amount_needed=Decimal('50000.00'),
            equity_offered=Decimal('10.00'),
            use_of_funds='Growth and expansion'
        )
        self.assertEqual(request.amount_needed, Decimal('50000.00'))
        self.assertEqual(request.equity_offered, Decimal('10.00'))
        self.assertEqual(request.status, 'draft')

    def test_funding_request_str(self):
        from Funding.models import FundingRequest
        request = FundingRequest.objects.create(
            business=self.business,
            amount_needed=Decimal('100000.00'),
            equity_offered=Decimal('15.00'),
            use_of_funds='Marketing'
        )
        expected = f"{self.business.name} seeking {request.amount_needed}"
        self.assertEqual(str(request), expected)

    def test_funding_request_status_choices(self):
        from Funding.models import FundingRequest
        statuses = ['draft', 'submitted', 'under_review', 'due_diligence', 
                    'negotiating', 'approved', 'funded', 'rejected', 'withdrawn', 'closed']
        for status in statuses:
            request = FundingRequest.objects.create(
                business=self.business,
                amount_needed=Decimal('10000.00'),
                equity_offered=Decimal('5.00'),
                use_of_funds='Test',
                status=status
            )
            self.assertEqual(request.status, status)


class InvestmentOpportunityModelTest(TestCase):
    def test_create_investment_opportunity(self):
        from Funding.models import InvestmentOpportunity
        opp = InvestmentOpportunity.objects.create(
            title='Stock Opportunity',
            description='Invest in tech stocks',
            provider='Tech Investments Ltd',
            type='stock',
            min_individual_entry=Decimal('100.00'),
            expected_return='15% p.a.',
            risk_level='medium'
        )
        self.assertEqual(opp.title, 'Stock Opportunity')
        self.assertEqual(opp.type, 'stock')
        self.assertTrue(opp.is_active)

    def test_investment_opportunity_str(self):
        from Funding.models import InvestmentOpportunity
        opp = InvestmentOpportunity.objects.create(
            title='MMF Fund',
            description='Money market fund',
            provider='Bank Africa',
            type='mmf',
            expected_return='8% p.a.',
            risk_level='low'
        )
        expected = "MMF Fund (Bank Africa)"
        self.assertEqual(str(opp), expected)

    def test_investment_opportunity_type_choices(self):
        from Funding.models import InvestmentOpportunity
        types = ['stock', 'mmf', 'bond_domestic', 'bond_foreign', 'lending', 'crypto', 'agency']
        for type_choice in types:
            opp = InvestmentOpportunity.objects.create(
                title=f'Opp {type_choice}',
                description='Description',
                provider='Provider',
                type=type_choice,
                expected_return='5%',
                risk_level='low'
            )
            self.assertEqual(opp.type, type_choice)


class FundingResponseModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='responseuser@example.com',
            password='pass123'
        )
        self.researcher = CustomUser.objects.create_user(
            email='funder@example.com',
            password='pass123'
        )
        from Funding.models import Business, FundingRequest
        self.business = Business.objects.create(
            founder=self.user,
            name='Response Business',
            industry='tech',
            description='Description'
        )
        self.funding_request = FundingRequest.objects.create(
            business=self.business,
            amount_needed=Decimal('50000.00'),
            equity_offered=Decimal('10.00'),
            use_of_funds='Test'
        )

    def test_create_funding_response(self):
        from Funding.models import FundingResponse
        response = FundingResponse.objects.create(
            funding_request=self.funding_request,
            responder=self.researcher,
            response_type='comment',
            content='Great project!'
        )
        self.assertEqual(response.response_type, 'comment')
        self.assertEqual(response.content, 'Great project!')

    def test_funding_response_str(self):
        from Funding.models import FundingResponse
        response = FundingResponse.objects.create(
            funding_request=self.funding_request,
            responder=self.researcher,
            response_type='offer',
            content='Offer content'
        )
        expected = f"{self.researcher} - offer on {self.funding_request}"
        self.assertEqual(str(response), expected)


class FundingNegotiationModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='neguser@example.com',
            password='pass123'
        )
        self.investor = CustomUser.objects.create_user(
            email='investor@example.com',
            password='pass123'
        )
        from Funding.models import Business, FundingRequest
        self.business = Business.objects.create(
            founder=self.user,
            name='Negotiation Business',
            industry='tech',
            description='Description'
        )
        self.funding_request = FundingRequest.objects.create(
            business=self.business,
            amount_needed=Decimal('50000.00'),
            equity_offered=Decimal('10.00'),
            use_of_funds='Test'
        )

    def test_create_funding_negotiation(self):
        from Funding.models import FundingNegotiation
        negotiation = FundingNegotiation.objects.create(
            funding_request=self.funding_request,
            investor=self.investor,
            founder=self.user
        )
        self.assertTrue(negotiation.is_active)
        self.assertEqual(negotiation.investor, self.investor)
        self.assertEqual(negotiation.founder, self.user)

    def test_funding_negotiation_str(self):
        from Funding.models import FundingNegotiation
        negotiation = FundingNegotiation.objects.create(
            funding_request=self.funding_request,
            investor=self.investor,
            founder=self.user
        )
        expected = f"Negotiation: {self.investor} <> {self.user}"
        self.assertEqual(str(negotiation), expected)


class NegotiationMessageModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='msguser@example.com',
            password='pass123'
        )
        self.investor = CustomUser.objects.create_user(
            email='msginvestor@example.com',
            password='pass123'
        )
        from Funding.models import Business, FundingRequest, FundingNegotiation
        self.business = Business.objects.create(
            founder=self.user,
            name='Message Business',
            industry='tech',
            description='Description'
        )
        self.funding_request = FundingRequest.objects.create(
            business=self.business,
            amount_needed=Decimal('50000.00'),
            equity_offered=Decimal('10.00'),
            use_of_funds='Test'
        )
        self.negotiation = FundingNegotiation.objects.create(
            funding_request=self.funding_request,
            investor=self.investor,
            founder=self.user
        )

    def test_create_negotiation_message(self):
        from Funding.models import NegotiationMessage
        message = NegotiationMessage.objects.create(
            negotiation=self.negotiation,
            sender=self.user,
            content='Let us discuss the terms.'
        )
        self.assertEqual(message.content, 'Let us discuss the terms.')
        self.assertFalse(message.is_read)


class FundingReactionModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='reactuser@example.com',
            password='pass123'
        )
        from Funding.models import Business, FundingRequest
        self.business = Business.objects.create(
            founder=self.user,
            name='Reaction Business',
            industry='tech',
            description='Description'
        )
        self.funding_request = FundingRequest.objects.create(
            business=self.business,
            amount_needed=Decimal('50000.00'),
            equity_offered=Decimal('10.00'),
            use_of_funds='Test'
        )

    def test_create_funding_reaction(self):
        from Funding.models import FundingReaction
        reaction = FundingReaction.objects.create(
            funding_request=self.funding_request,
            user=self.user,
            reaction_type='interested'
        )
        self.assertEqual(reaction.reaction_type, 'interested')

    def test_funding_reaction_types(self):
        from Funding.models import FundingReaction
        types = ['interested', 'promising', 'caution', 'like']
        for reaction_type in types:
            reaction = FundingReaction.objects.create(
                funding_request=self.funding_request,
                user=self.user,
                reaction_type=reaction_type
            )
            self.assertEqual(reaction.reaction_type, reaction_type)


class CapitalVentureModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='ventureuser@example.com',
            password='pass123'
        )

    def test_create_capital_venture(self):
        from Funding.models import CapitalVenture
        venture = CapitalVenture.objects.create(
            name='Tech Venture Fund',
            description='Investment fund for tech startups',
            total_fund=Decimal('1000000.00'),
            available_fund=Decimal('500000.00'),
            investment_criteria='Tech startups with high growth potential',
            max_investment=Decimal('100000.00')
        )
        self.assertEqual(venture.name, 'Tech Venture Fund')
        self.assertTrue(venture.is_active)

    def test_capital_venture_str(self):
        from Funding.models import CapitalVenture
        venture = CapitalVenture.objects.create(
            name='My Venture',
            description='Description',
            total_fund=Decimal('100000.00'),
            available_fund=Decimal('50000.00'),
            max_investment=Decimal('10000.00')
        )
        self.assertEqual(str(venture), 'My Venture')


class VentureBidModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='biduser@example.com',
            password='pass123'
        )
        from Funding.models import Business, FundingRequest, CapitalVenture
        self.business = Business.objects.create(
            founder=self.user,
            name='Bid Business',
            industry='tech',
            description='Description'
        )
        self.funding_request = FundingRequest.objects.create(
            business=self.business,
            amount_needed=Decimal('50000.00'),
            equity_offered=Decimal('10.00'),
            use_of_funds='Test'
        )
        self.venture = CapitalVenture.objects.create(
            name='Bid Venture',
            description='Description',
            total_fund=Decimal('1000000.00'),
            available_fund=Decimal('500000.00'),
            max_investment=Decimal('100000.00')
        )

    def test_create_venture_bid(self):
        from Funding.models import VentureBid
        bid = VentureBid.objects.create(
            venture=self.venture,
            funding_request=self.funding_request,
            proposed_amount=Decimal('25000.00'),
            proposed_equity=Decimal('5.00')
        )
        self.assertEqual(bid.proposed_amount, Decimal('25000.00'))
        self.assertEqual(bid.status, 'pending')

    def test_venture_bid_str(self):
        from Funding.models import VentureBid
        bid = VentureBid.objects.create(
            venture=self.venture,
            funding_request=self.funding_request,
            proposed_amount=Decimal('25000.00'),
            proposed_equity=Decimal('5.00')
        )
        expected = f"{self.venture.name} bid on {self.funding_request}"
        self.assertEqual(str(bid), expected)


class InvestmentAgreementModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='agreementuser@example.com',
            password='pass123'
        )
        from Funding.models import CapitalVenture
        self.venture = CapitalVenture.objects.create(
            name='Agreement Venture',
            description='Description',
            total_fund=Decimal('1000000.00'),
            available_fund=Decimal('500000.00'),
            max_investment=Decimal('100000.00')
        )

    def test_create_investment_agreement(self):
        from Funding.models import InvestmentAgreement
        agreement = InvestmentAgreement.objects.create(
            investor=self.user,
            venture=self.venture,
            kyc_data={'name': 'Test User', 'id_number': '12345'},
            digital_signature='signed_by_user_123'
        )
        self.assertTrue(agreement.terms_accepted)
        self.assertTrue(agreement.risk_acknowledged)

    def test_investment_agreement_str(self):
        from Funding.models import InvestmentAgreement
        agreement = InvestmentAgreement.objects.create(
            investor=self.user,
            venture=self.venture,
            digital_signature='signature'
        )
        expected = f"Agreement: {self.user.email} → {self.venture.name}"
        self.assertEqual(str(agreement), expected)


class InvestorProfileModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email='investorprofile@example.com',
            password='pass123'
        )

    def test_create_investor_profile(self):
        from Funding.models import InvestorProfile
        from datetime import date
        profile = InvestorProfile.objects.create(
            user=self.user,
            full_name='John Doe',
            id_number='ID123456',
            id_type='national_id',
            nationality='Kenya',
            date_of_birth=date(1990, 1, 1)
        )
        self.assertEqual(profile.full_name, 'John Doe')
        self.assertTrue(profile.is_complete)

    def test_investor_profile_str(self):
        from Funding.models import InvestorProfile
        profile = InvestorProfile.objects.create(
            user=self.user,
            full_name='Jane Doe',
            id_number='ID789',
            nationality='USA'
        )
        expected = "InvestorProfile: Jane Doe (investorprofile@example.com)"
        self.assertEqual(str(profile), expected)

    def test_investor_profile_is_complete(self):
        from Funding.models import InvestorProfile
        profile = InvestorProfile.objects.create(
            user=self.user,
            full_name='Complete Investor',
            id_number='ID123',
            nationality='Nigeria'
        )
        self.assertTrue(profile.is_complete)

    def test_investor_profile_not_complete(self):
        from Funding.models import InvestorProfile
        profile = InvestorProfile.objects.create(
            user=self.user,
            full_name='Incomplete Investor'
        )
        self.assertFalse(profile.is_complete)