"""
Management command to create 300+ dummy data instances for testing the platform.
Run with: python manage.py create_dummy_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random
import uuid

class Command(BaseCommand):
    help = 'Creates 300+ dummy data instances for testing the platform'

    def handle(self, *args, **options):
        self.stdout.write('Creating massive dummy data (300+ per category)...')
        
        # Import models
        from Authentication.models import CustomUser, Profile
        from Payment.models import (
            Partner, Product, PaymentGroups, PaymentProfile,
            BillProvider, BillPayment, LoanProduct, CreditScore,
            LoanApplication, LoanRepayment, EscrowTransaction,
            InsuranceProduct, InsurancePolicy, InsuranceClaim,
        )
        from Events.models import Event
        from Research.models import ResearchProject
        
        # 1. Create or get test users & profiles
        self.stdout.write('Creating 50 Test Users...')
        test_users = []
        profiles = []
        payment_profiles = []
        for i in range(1, 51):
            email = f'massuser{i}@example.com'
            user, created = CustomUser.objects.get_or_create(
                email=email,
                defaults={
                    'username': f'massuser{i}_{uuid.uuid4().hex[:6]}',
                    'first_name': f'Mass{i}',
                    'last_name': f'User{i}',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            payment_profile, _ = PaymentProfile.objects.get_or_create(user=profile)
            
            test_users.append(user)
            profiles.append(profile)
            payment_profiles.append(payment_profile)
        
        # 2. Create 300 Partners
        self.stdout.write('Creating 300 Partners...')
        partner_types = ['distributor', 'publisher', 'author', 'supplier', 'content_creator', 'business', 'investor']
        countries = ['USA', 'UK', 'Canada', 'Australia', 'Germany', 'Kenya', 'Nigeria', 'India']
        
        partners_to_create = []
        existing_partners = Partner.objects.count()
        needed_partners = max(0, 300 - existing_partners)
        
        for i in range(needed_partners):
            p_type = random.choice(partner_types)
            profile = random.choice(profiles)
            Partner.objects.get_or_create(
                user=profile,
                business_name=f'Mass Business {uuid.uuid4().hex[:8]}',
                defaults={
                    'partner_type': p_type,
                    'contact_email': f'contact_{uuid.uuid4().hex[:6]}@example.com',
                    'city': 'Metropolis',
                    'country': random.choice(countries),
                    'status': 'approved',
                    'verified': True,
                    'commission_rate': Decimal(str(random.randint(5, 20))),
                    'description': f'A leading {p_type} auto-generated for testing.',
                }
            )
        
        # 3. Create 300 Products (Shop)
        self.stdout.write('Creating 300 Products...')
        product_types = ['digital', 'physical', 'subscription', 'service']
        categories = ['Tech', 'Education', 'Science', 'Art', 'Lifestyle']
        
        existing_products = Product.objects.count()
        needed_products = max(0, 300 - existing_products)
        
        for i in range(needed_products):
            p_type = random.choice(product_types)
            category = random.choice(categories)
            Product.objects.get_or_create(
                name=f'Product {category} {uuid.uuid4().hex[:8]}',
                defaults={
                    'description': f'Auto-generated {p_type} product in {category}',
                    'price': Decimal(str(random.uniform(5.0, 500.0)).split('.')[0] + '.' + str(random.randint(0, 99)).zfill(2)),
                    'product_type': p_type,
                    'is_sharable': random.choice([True, False]),
                }
            )
            
        # 4. Create 300 PaymentGroups
        self.stdout.write('Creating 300 Payment Groups...')
        group_types = ['standard', 'piggy_bank', 'kitty']
        
        existing_groups = PaymentGroups.objects.count()
        needed_groups = max(0, 300 - existing_groups)
        
        for i in range(needed_groups):
            g_type = random.choice(group_types)
            creator = random.choice(payment_profiles)
            PaymentGroups.objects.create(
                name=f'{g_type.title()} Group {uuid.uuid4().hex[:8]}',
                description=f'An auto-generated {g_type} for testing.',
                creator=creator,
                group_type=g_type,
                target_amount=Decimal(str(random.randint(1000, 50000))),
                is_public=True,
                auto_create_room=True,
            )
            
        # 5. Create 300 Events
        self.stdout.write('Creating 300 Events...')
        try:
            existing_events = Event.objects.count()
            needed_events = max(0, 300 - existing_events)
            
            for i in range(needed_events):
                Event.objects.create(
                    name=f'Mass Event {uuid.uuid4().hex[:8]}',
                    description='Join us for this auto-generated massive event. A great opportunity to connect.',
                    location='Virtual Convention Center',
                    event_date=timezone.now().date() + timedelta(days=random.randint(1, 100)),
                    start_time='09:00:00',
                    end_time='17:00:00',
                    capacity=random.randint(50, 500),
                    visibility='public',
                    status='active',
                    organizer=random.choice(profiles),
                )
        except Exception as e:
            self.stdout.write(f'  Skipping events error: {e}')
            
        # 6. Create 300 Research Projects
        self.stdout.write('Creating 300 Research Projects...')
        try:
            statuses = ['draft', 'in_progress', 'peer_review', 'published', 'archived']
            
            existing_research = ResearchProject.objects.count()
            needed_research = max(0, 300 - existing_research)
            
            for i in range(needed_research):
                ResearchProject.objects.create(
                    title=f'Research Study {uuid.uuid4().hex[:12]}',
                    abstract='Auto-generated research abstract investigating correlations in dummy datasets.',
                    description='A detailed study auto-generated with significant implications for testing.',
                    principal_investigator=random.choice(test_users),
                    status=random.choice(statuses),
                    ethics_approved=True,
                )
        except Exception as e:
            self.stdout.write(f'  Skipping research error: {e}')

        # ==================================================================
        # 7. BILL PROVIDERS — 23 providers across 8 categories
        # ==================================================================
        self.stdout.write('Creating Bill Providers...')

        bill_providers_data = [
            # Electricity
            {'name': 'Kenya Power (KPLC)', 'category': 'electricity', 'account_label': 'Meter Number', 'description': 'Prepaid & Postpaid electricity tokens', 'commission_rate': Decimal('0.0150')},
            {'name': 'Nairobi Power', 'category': 'electricity', 'account_label': 'Account Number', 'description': 'Nairobi metropolitan area electricity', 'commission_rate': Decimal('0.0150')},
            # Water
            {'name': 'Nairobi Water & Sewerage', 'category': 'water', 'account_label': 'Account Number', 'description': 'Water & sewerage bills for Nairobi', 'commission_rate': Decimal('0.0100')},
            {'name': 'Mombasa Water', 'category': 'water', 'account_label': 'Customer ID', 'description': 'Mombasa county water services', 'commission_rate': Decimal('0.0100')},
            # TV & Streaming
            {'name': 'DSTV / MultiChoice', 'category': 'tv', 'account_label': 'Smart Card Number', 'description': 'All DSTV subscription packages', 'commission_rate': Decimal('0.0200')},
            {'name': 'GOtv', 'category': 'tv', 'account_label': 'IUC Number', 'description': 'GOtv subscription packages', 'commission_rate': Decimal('0.0200')},
            {'name': 'StarTimes', 'category': 'tv', 'account_label': 'Card Number', 'description': 'StarTimes TV packages', 'commission_rate': Decimal('0.0200')},
            {'name': 'Showmax', 'category': 'tv', 'account_label': 'Email', 'description': 'Showmax streaming subscription', 'commission_rate': Decimal('0.0200')},
            # Airtime & Data
            {'name': 'Safaricom', 'category': 'airtime', 'account_label': 'Phone Number', 'description': 'Safaricom airtime & data bundles', 'commission_rate': Decimal('0.0300')},
            {'name': 'Airtel Kenya', 'category': 'airtime', 'account_label': 'Phone Number', 'description': 'Airtel airtime & data bundles', 'commission_rate': Decimal('0.0300')},
            {'name': 'Telkom Kenya', 'category': 'airtime', 'account_label': 'Phone Number', 'description': 'Telkom airtime & data', 'commission_rate': Decimal('0.0300')},
            {'name': 'Faiba', 'category': 'airtime', 'account_label': 'Phone Number', 'description': 'Faiba 4G data bundles', 'commission_rate': Decimal('0.0300')},
            # Internet
            {'name': 'Safaricom Home Fibre', 'category': 'internet', 'account_label': 'Account Number', 'description': 'Safaricom fibre internet', 'commission_rate': Decimal('0.0100')},
            {'name': 'Zuku Fibre', 'category': 'internet', 'account_label': 'Account Number', 'description': 'Zuku internet & TV bundle', 'commission_rate': Decimal('0.0100')},
            {'name': 'JTL Faiba', 'category': 'internet', 'account_label': 'Account Number', 'description': 'Faiba fibre internet', 'commission_rate': Decimal('0.0100')},
            # School Fees
            {'name': 'University of Nairobi', 'category': 'school_fees', 'account_label': 'Registration Number', 'description': 'UoN tuition & fees', 'commission_rate': Decimal('0.0050')},
            {'name': 'Kenyatta University', 'category': 'school_fees', 'account_label': 'Admission Number', 'description': 'KU fee payments', 'commission_rate': Decimal('0.0050')},
            {'name': 'JKUAT', 'category': 'school_fees', 'account_label': 'Registration Number', 'description': 'JKUAT tuition & hostel', 'commission_rate': Decimal('0.0050')},
            # Rent
            {'name': 'Direct Landlord', 'category': 'rent', 'account_label': 'Landlord M-Pesa', 'description': 'Pay rent directly to landlord', 'commission_rate': Decimal('0.0100')},
            # Government
            {'name': 'KRA (iTax)', 'category': 'government', 'account_label': 'KRA PIN', 'description': 'Kenya Revenue Authority tax payments', 'commission_rate': Decimal('0.0000')},
            {'name': 'eCitizen', 'category': 'government', 'account_label': 'ID Number', 'description': 'Government e-services', 'commission_rate': Decimal('0.0050')},
            {'name': 'NHIF', 'category': 'government', 'account_label': 'Member Number', 'description': 'National health insurance', 'commission_rate': Decimal('0.0000')},
            {'name': 'NSSF', 'category': 'government', 'account_label': 'Member Number', 'description': 'National social security fund', 'commission_rate': Decimal('0.0000')},
        ]

        for bp in bill_providers_data:
            BillProvider.objects.get_or_create(
                name=bp['name'],
                defaults=bp
            )
        self.stdout.write(f'  ✓ {BillProvider.objects.count()} bill providers')

        # ==================================================================
        # 8. LOAN PRODUCTS — 6 products
        # ==================================================================
        self.stdout.write('Creating Loan Products...')

        loan_products_data = [
            {
                'name': 'Quick Cash',
                'description': 'Instant micro-loan for emergencies. No guarantor needed.',
                'interest_rate': Decimal('5.00'), 'min_amount': Decimal('1000'), 'max_amount': Decimal('50000'),
                'min_tenure_months': 1, 'max_tenure_months': 6,
                'requires_guarantor': False, 'processing_fee': Decimal('2.50'),
                'icon': '⚡', 'color': 'from-amber-500 to-orange-600',
            },
            {
                'name': 'Business Boost',
                'description': 'Working capital for small businesses with competitive rates.',
                'interest_rate': Decimal('3.50'), 'min_amount': Decimal('10000'), 'max_amount': Decimal('500000'),
                'min_tenure_months': 3, 'max_tenure_months': 24,
                'requires_guarantor': True, 'guarantors_required': 2, 'processing_fee': Decimal('1.50'),
                'icon': '🚀', 'color': 'from-blue-500 to-indigo-600',
            },
            {
                'name': 'Salary Advance',
                'description': 'Borrow against your next paycheck. Fast disbursement.',
                'interest_rate': Decimal('4.00'), 'min_amount': Decimal('5000'), 'max_amount': Decimal('100000'),
                'min_tenure_months': 1, 'max_tenure_months': 3,
                'requires_guarantor': False, 'processing_fee': Decimal('2.00'),
                'icon': '💼', 'color': 'from-emerald-500 to-green-600',
            },
            {
                'name': 'Group Loan',
                'description': 'Borrow through your chama or investment group.',
                'interest_rate': Decimal('2.50'), 'min_amount': Decimal('5000'), 'max_amount': Decimal('200000'),
                'min_tenure_months': 1, 'max_tenure_months': 12,
                'requires_guarantor': True, 'is_group_loan': True, 'processing_fee': Decimal('1.00'),
                'icon': '👥', 'color': 'from-violet-500 to-purple-600',
            },
            {
                'name': 'Education Loan',
                'description': 'Fund your education with flexible repayment terms.',
                'interest_rate': Decimal('3.00'), 'min_amount': Decimal('20000'), 'max_amount': Decimal('1000000'),
                'min_tenure_months': 6, 'max_tenure_months': 24,
                'requires_guarantor': True, 'guarantors_required': 1, 'processing_fee': Decimal('1.50'),
                'icon': '🎓', 'color': 'from-rose-500 to-pink-600',
            },
            {
                'name': 'Asset Finance',
                'description': 'Finance purchase of equipment, electronics, or vehicles.',
                'interest_rate': Decimal('4.50'), 'min_amount': Decimal('50000'), 'max_amount': Decimal('2000000'),
                'min_tenure_months': 6, 'max_tenure_months': 24,
                'requires_guarantor': True, 'guarantors_required': 2, 'processing_fee': Decimal('2.00'),
                'icon': '🏗️', 'color': 'from-cyan-500 to-teal-600',
            },
        ]

        for lp in loan_products_data:
            LoanProduct.objects.get_or_create(name=lp['name'], defaults=lp)
        self.stdout.write(f'  ✓ {LoanProduct.objects.count()} loan products')

        # ==================================================================
        # 9. INSURANCE PRODUCTS — 6 products
        # ==================================================================
        self.stdout.write('Creating Insurance Products...')

        insurance_products_data = [
            {
                'name': 'Qomrade Health Basic', 'provider': 'Jubilee Insurance', 'category': 'health',
                'description': 'Basic outpatient and inpatient cover for individuals.',
                'premium_amount': Decimal('1500'), 'premium_frequency': 'monthly',
                'coverage_amount': Decimal('500000'), 'deductible': Decimal('2500'),
                'waiting_period_days': 30, 'rating': Decimal('4.5'), 'icon': '❤️',
                'color': 'from-rose-500 to-pink-600',
                'benefits': ['Outpatient visits', 'Inpatient care', 'Dental checkups', 'Lab tests', 'Prescription drugs'],
                'exclusions': ['Pre-existing conditions (first 12 months)', 'Cosmetic surgery'],
            },
            {
                'name': 'Device Guard Pro', 'provider': 'Britam', 'category': 'device',
                'description': 'Protect your smartphone, laptop, and electronics against theft & damage.',
                'premium_amount': Decimal('800'), 'premium_frequency': 'monthly',
                'coverage_amount': Decimal('150000'), 'deductible': Decimal('5000'),
                'waiting_period_days': 7, 'rating': Decimal('4.2'), 'icon': '📱',
                'color': 'from-blue-500 to-indigo-600',
                'benefits': ['Accidental damage', 'Theft & robbery', 'Screen damage', 'Water damage', 'Worldwide cover'],
                'exclusions': ['Lost devices', 'Wear and tear', 'Cosmetic damage'],
            },
            {
                'name': 'Safari Travel Shield', 'provider': 'APA Insurance', 'category': 'travel',
                'description': 'Comprehensive travel insurance for domestic and international trips.',
                'premium_amount': Decimal('500'), 'premium_frequency': 'one_time',
                'coverage_amount': Decimal('2000000'), 'deductible': Decimal('0'),
                'waiting_period_days': 0, 'rating': Decimal('4.7'), 'icon': '✈️',
                'color': 'from-cyan-500 to-blue-600',
                'benefits': ['Medical emergencies abroad', 'Trip cancellation', 'Lost luggage', 'Flight delays', 'Repatriation'],
                'exclusions': ['Adventure sports', 'Travel against government advisory'],
            },
            {
                'name': 'Mazao Crop Protect', 'provider': 'ACRE Africa', 'category': 'crop',
                'description': 'Weather-indexed insurance for small-scale farmers. Payout on adverse weather.',
                'premium_amount': Decimal('200'), 'premium_frequency': 'quarterly',
                'coverage_amount': Decimal('100000'), 'deductible': Decimal('0'),
                'waiting_period_days': 0, 'rating': Decimal('4.0'), 'icon': '🌾',
                'color': 'from-emerald-500 to-green-600',
                'benefits': ['Drought protection', 'Excess rain cover', 'Pest outbreak', 'Input cost recovery', 'Satellite-based claims'],
                'exclusions': ['Willful neglect', 'Unregistered crop types'],
            },
            {
                'name': 'Biashara Shield', 'provider': 'CIC Insurance', 'category': 'business',
                'description': 'Affordable business insurance for micro and small enterprises.',
                'premium_amount': Decimal('3000'), 'premium_frequency': 'monthly',
                'coverage_amount': Decimal('1000000'), 'deductible': Decimal('10000'),
                'waiting_period_days': 14, 'rating': Decimal('4.3'), 'icon': '💼',
                'color': 'from-amber-500 to-orange-600',
                'benefits': ['Fire & burglary', 'Stock damage', 'Business interruption', 'Employee liability', 'Money in transit'],
                'exclusions': ['Fraud by owner', 'Unregistered businesses'],
            },
            {
                'name': 'Nyumba Asset Cover', 'provider': 'Madison Insurance', 'category': 'asset',
                'description': 'Home contents and property protection from theft, fire, and natural disasters.',
                'premium_amount': Decimal('2000'), 'premium_frequency': 'monthly',
                'coverage_amount': Decimal('5000000'), 'deductible': Decimal('15000'),
                'waiting_period_days': 14, 'rating': Decimal('4.4'), 'icon': '🏠',
                'color': 'from-violet-500 to-purple-600',
                'benefits': ['Theft & burglary', 'Fire damage', 'Natural disasters', 'Electrical damage', 'Temporary accommodation'],
                'exclusions': ['War damage', 'Nuclear hazards', 'Gradual deterioration'],
            },
        ]

        for ip in insurance_products_data:
            InsuranceProduct.objects.get_or_create(name=ip['name'], defaults=ip)
        self.stdout.write(f'  ✓ {InsuranceProduct.objects.count()} insurance products')

        # ==================================================================
        # 10. CREDIT SCORES — for specific users (jay, peter mbugua, john wekesa) + test users
        # ==================================================================
        self.stdout.write('Creating Credit Scores...')

        # Specific users requested by platform owner
        named_users = {
            'jay': {'score': 742, 'risk_level': 'low', 'savings_score': 82, 'repayment_score': 90, 'group_score': 65, 'transaction_score': 78, 'tenure_score': 60},
            'peter': {'score': 685, 'risk_level': 'low', 'savings_score': 70, 'repayment_score': 80, 'group_score': 60, 'transaction_score': 72, 'tenure_score': 45},
            'john': {'score': 618, 'risk_level': 'moderate', 'savings_score': 55, 'repayment_score': 70, 'group_score': 50, 'transaction_score': 65, 'tenure_score': 40},
        }

        from django.db.models import Q
        for search, score_data in named_users.items():
            try:
                user = CustomUser.objects.filter(
                    Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
                ).first()
                if user:
                    profile = Profile.objects.filter(user=user).first()
                    if profile:
                        cs, created = CreditScore.objects.get_or_create(
                            user=profile,
                            defaults={
                                **score_data,
                                'factors': {
                                    'savings_consistency': f"{score_data['savings_score']}%",
                                    'repayment_history': f"{score_data['repayment_score']}%",
                                    'group_participation': f"{score_data['group_score']}%",
                                    'transaction_volume': f"{score_data['transaction_score']}%",
                                    'platform_tenure': f"{score_data['tenure_score']}%",
                                },
                                'computed_at': timezone.now(),
                            }
                        )
                        if not created:
                            for k, v in score_data.items():
                                setattr(cs, k, v)
                            cs.factors = {
                                'savings_consistency': f"{score_data['savings_score']}%",
                                'repayment_history': f"{score_data['repayment_score']}%",
                                'group_participation': f"{score_data['group_score']}%",
                                'transaction_volume': f"{score_data['transaction_score']}%",
                                'platform_tenure': f"{score_data['tenure_score']}%",
                            }
                            cs.computed_at = timezone.now()
                            cs.save()
                        self.stdout.write(f'  ✓ Credit score for {user.username}: {score_data["score"]}')
                else:
                    self.stdout.write(f'  ⚠ User matching "{search}" not found, skipping.')
            except Exception as e:
                self.stdout.write(f'  ⚠ Error creating credit score for {search}: {e}')

        # Random scores for test users
        for profile in profiles[:20]:
            score_val = random.randint(300, 850)
            risk = 'very_low' if score_val >= 800 else 'low' if score_val >= 700 else 'moderate' if score_val >= 500 else 'high' if score_val >= 300 else 'very_high'
            CreditScore.objects.get_or_create(
                user=profile,
                defaults={
                    'score': score_val, 'risk_level': risk,
                    'savings_score': random.randint(20, 95),
                    'repayment_score': random.randint(20, 95),
                    'group_score': random.randint(10, 90),
                    'transaction_score': random.randint(20, 95),
                    'tenure_score': random.randint(10, 80),
                    'factors': {},
                    'computed_at': timezone.now(),
                }
            )
        self.stdout.write(f'  ✓ {CreditScore.objects.count()} credit scores')

        # ==================================================================
        # 11. SAMPLE ESCROW TRANSACTIONS
        # ==================================================================
        self.stdout.write('Creating Sample Escrow Transactions...')

        if EscrowTransaction.objects.count() < 10:
            escrow_samples = [
                {'title': 'Web Development Project', 'escrow_type': 'gig', 'amount': Decimal('75000'), 'status': 'funded',
                 'milestones': [{'name': 'Design', 'amount': 25000, 'completed': True}, {'name': 'Frontend', 'amount': 25000, 'completed': True}, {'name': 'Backend', 'amount': 25000, 'completed': False}],
                 'description': 'Full-stack web application for e-commerce platform'},
                {'title': 'iPhone 15 Pro Purchase', 'escrow_type': 'marketplace', 'amount': Decimal('180000'), 'status': 'released',
                 'milestones': [], 'description': 'Brand new iPhone 15 Pro 256GB'},
                {'title': 'Land Survey Service', 'escrow_type': 'p2p', 'amount': Decimal('45000'), 'status': 'disputed',
                 'milestones': [], 'description': 'Professional land surveying in Kiambu county'},
                {'title': 'Logo Design', 'escrow_type': 'gig', 'amount': Decimal('15000'), 'status': 'delivered',
                 'milestones': [{'name': 'Concepts', 'amount': 5000, 'completed': True}, {'name': 'Final Design', 'amount': 10000, 'completed': True}],
                 'description': 'Brand logo design with 3 concept variations'},
                {'title': 'Group Investment — Real Estate Fund', 'escrow_type': 'group_investment', 'amount': Decimal('500000'), 'status': 'funded',
                 'milestones': [{'name': 'Due Diligence', 'amount': 50000, 'completed': True}, {'name': 'Investment', 'amount': 450000, 'completed': False}],
                 'description': 'Pooled investment in Nairobi commercial real estate'},
                {'title': 'Used Car Purchase', 'escrow_type': 'p2p', 'amount': Decimal('650000'), 'status': 'initiated',
                 'milestones': [], 'description': '2019 Toyota Rav4 purchase from individual seller'},
                {'title': 'Freelance Video Production', 'escrow_type': 'gig', 'amount': Decimal('120000'), 'status': 'in_progress',
                 'milestones': [{'name': 'Pre-production', 'amount': 30000, 'completed': True}, {'name': 'Shooting', 'amount': 50000, 'completed': False}, {'name': 'Post-production', 'amount': 40000, 'completed': False}],
                 'description': 'Corporate brand video production'},
                {'title': 'Laptop Purchase', 'escrow_type': 'marketplace', 'amount': Decimal('95000'), 'status': 'released',
                 'milestones': [], 'description': 'MacBook Air M2 from verified seller'},
            ]

            for es in escrow_samples:
                buyer = random.choice(profiles[:10])
                seller = random.choice(profiles[10:20])
                try:
                    EscrowTransaction.objects.create(
                        buyer=buyer, seller=seller,
                        escrow_type=es['escrow_type'], title=es['title'],
                        description=es['description'], amount=es['amount'],
                        status=es['status'], milestones=es['milestones'],
                        release_conditions='Upon delivery confirmation and inspection',
                    )
                except Exception as e:
                    self.stdout.write(f'  ⚠ Escrow error: {e}')

        self.stdout.write(f'  ✓ {EscrowTransaction.objects.count()} escrow transactions')

        # ==================================================================
        # 12. SAMPLE LOAN APPLICATIONS & REPAYMENTS
        # ==================================================================
        self.stdout.write('Creating Sample Loan Applications...')

        if LoanApplication.objects.count() < 5:
            products = list(LoanProduct.objects.all())
            if products:
                loan_samples = [
                    {'product_idx': 0, 'amount': Decimal('15000'), 'tenure': 3, 'status': 'repaying', 'purpose': 'Emergency medical expenses'},
                    {'product_idx': 1, 'amount': Decimal('100000'), 'tenure': 12, 'status': 'completed', 'purpose': 'Working capital for bakery business'},
                    {'product_idx': 2, 'amount': Decimal('25000'), 'tenure': 1, 'status': 'disbursed', 'purpose': 'Salary advance for rent'},
                    {'product_idx': 4, 'amount': Decimal('200000'), 'tenure': 24, 'status': 'pending', 'purpose': 'University fees for MBA program'},
                    {'product_idx': 0, 'amount': Decimal('8000'), 'tenure': 2, 'status': 'completed', 'purpose': 'Phone repair costs'},
                ]

                for ls in loan_samples:
                    profile = random.choice(profiles[:15])
                    try:
                        loan = LoanApplication.objects.create(
                            user=profile, loan_product=products[ls['product_idx']],
                            amount=ls['amount'], tenure_months=ls['tenure'],
                            purpose=ls['purpose'], status=ls['status'],
                            credit_score_at_application=random.randint(500, 800),
                        )
                        if ls['status'] in ('disbursed', 'repaying', 'completed'):
                            loan.disbursed_at = timezone.now() - timedelta(days=random.randint(30, 180))
                            loan.save()
                            # Create repayments
                            for inst in range(1, ls['tenure'] + 1):
                                due = loan.disbursed_at.date() + timedelta(days=30 * inst)
                                if ls['status'] == 'completed':
                                    r_status = 'paid'
                                elif due <= date.today():
                                    r_status = 'paid' if random.random() > 0.2 else 'overdue'
                                elif due <= date.today() + timedelta(days=7):
                                    r_status = 'due'
                                else:
                                    r_status = 'upcoming'
                                LoanRepayment.objects.create(
                                    loan=loan, installment_number=inst,
                                    amount_due=loan.monthly_payment,
                                    amount_paid=loan.monthly_payment if r_status == 'paid' else Decimal('0'),
                                    due_date=due, status=r_status,
                                    paid_date=timezone.now() - timedelta(days=random.randint(0, 5)) if r_status == 'paid' else None,
                                )
                    except Exception as e:
                        self.stdout.write(f'  ⚠ Loan error: {e}')

        self.stdout.write(f'  ✓ {LoanApplication.objects.count()} loan applications, {LoanRepayment.objects.count()} repayments')

        # ==================================================================
        # 13. SAMPLE INSURANCE POLICIES & CLAIMS
        # ==================================================================
        self.stdout.write('Creating Sample Insurance Policies & Claims...')

        if InsurancePolicy.objects.count() < 5:
            ins_products = list(InsuranceProduct.objects.all())
            if ins_products:
                for i, ip in enumerate(ins_products[:4]):
                    profile = random.choice(profiles[:10])
                    try:
                        start = date.today() - timedelta(days=random.randint(30, 180))
                        policy = InsurancePolicy.objects.create(
                            user=profile, product=ip,
                            status='active',
                            premium_paid=ip.premium_amount * Decimal(str(random.randint(3, 12))),
                            start_date=start,
                            end_date=start + timedelta(days=365),
                            next_payment_date=date.today() + timedelta(days=random.randint(1, 30)),
                        )
                        # Add a claim on the second policy
                        if i == 1:
                            InsuranceClaim.objects.create(
                                policy=policy, claimant=profile,
                                amount_claimed=Decimal('45000'),
                                amount_approved=Decimal('42000'),
                                reason='Phone screen cracked after accidental fall',
                                status='approved',
                                reviewer_notes='Claim verified with photo evidence. Approved minus deductible.',
                                reviewed_at=timezone.now() - timedelta(days=5),
                            )
                    except Exception as e:
                        self.stdout.write(f'  ⚠ Insurance error: {e}')

        self.stdout.write(f'  ✓ {InsurancePolicy.objects.count()} policies, {InsuranceClaim.objects.count()} claims')

        # ==================================================================
        # 14. SAMPLE BILL PAYMENTS
        # ==================================================================
        self.stdout.write('Creating Sample Bill Payments...')

        if BillPayment.objects.count() < 5:
            providers = list(BillProvider.objects.all())
            if providers:
                bill_samples = [
                    {'provider_name': 'Kenya Power (KPLC)', 'account': '54321098', 'amount': Decimal('1500'), 'status': 'completed'},
                    {'provider_name': 'Safaricom', 'account': '0712345678', 'amount': Decimal('500'), 'status': 'completed'},
                    {'provider_name': 'DSTV / MultiChoice', 'account': '10234567', 'amount': Decimal('3999'), 'status': 'completed'},
                    {'provider_name': 'Nairobi Water & Sewerage', 'account': 'NW-09876', 'amount': Decimal('2800'), 'status': 'failed'},
                    {'provider_name': 'NHIF', 'account': 'MEM-556677', 'amount': Decimal('1700'), 'status': 'completed'},
                    {'provider_name': 'Zuku Fibre', 'account': 'ZK-998877', 'amount': Decimal('4500'), 'status': 'completed'},
                ]
                for bs in bill_samples:
                    provider = BillProvider.objects.filter(name=bs['provider_name']).first()
                    if provider:
                        profile = random.choice(profiles[:10])
                        try:
                            BillPayment.objects.create(
                                user=profile, provider=provider,
                                account_number=bs['account'], amount=bs['amount'],
                                status=bs['status'], payment_method='comrade_balance',
                                created_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                                completed_at=timezone.now() - timedelta(days=random.randint(0, 1)) if bs['status'] == 'completed' else None,
                            )
                        except Exception as e:
                            self.stdout.write(f'  ⚠ Bill payment error: {e}')

        self.stdout.write(f'  ✓ {BillPayment.objects.count()} bill payments')

        self.stdout.write(self.style.SUCCESS(
            '✅ Full dummy data creation complete!\n'
            f'   Partners: {Partner.objects.count()}\n'
            f'   Products: {Product.objects.count()}\n' 
            f'   Groups: {PaymentGroups.objects.count()}\n'
            f'   Bill Providers: {BillProvider.objects.count()}\n'
            f'   Loan Products: {LoanProduct.objects.count()}\n'
            f'   Insurance Products: {InsuranceProduct.objects.count()}\n'
            f'   Credit Scores: {CreditScore.objects.count()}\n'
            f'   Escrow Txns: {EscrowTransaction.objects.count()}\n'
            f'   Loan Applications: {LoanApplication.objects.count()}\n'
            f'   Insurance Policies: {InsurancePolicy.objects.count()}\n'
        ))
