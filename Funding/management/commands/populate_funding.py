from django.core.management.base import BaseCommand
from Funding.models import Business, InvestmentOpportunity
from Authentication.models import CustomUser
from django.utils import timezone
import random

class Command(BaseCommand):
    help = 'Populates the database with initial funding data'

    def handle(self, *args, **options):
        self.stdout.write('Starting funding data population...')
        
        # Ensure a user exists for creating businesses
        user = CustomUser.objects.filter(email='admin@comrade.com').first()
        if not user:
            user = CustomUser.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write("No user found to assign businesses to. Creating default admin.")
            user = CustomUser.objects.create_user(
                email='admin@comrade.com',
                password='password123',
                first_name='Admin',
                last_name='User',
                user_type='admin'
            )

        # 1. Populate Charities (Business model)
        CHARITY_DATA = [
            { 'name': 'Clean Water Initiative Kenya', 'industry': 'other', 'description': 'Providing clean drinking water to 50 rural communities in arid Kenya regions.', 'goal': 5000000, 'raised': 3200000 },
            { 'name': 'Girls Education Fund', 'industry': 'educ', 'description': 'Scholarships for 1000 girls in secondary school across East Africa.', 'goal': 8000000, 'raised': 5500000 },
            { 'name': 'Feed the Children Campaign', 'industry': 'other', 'description': 'Emergency food relief for drought-affected families in Northern Kenya.', 'goal': 3000000, 'raised': 2100000 },
            { 'name': 'Plant 1 Million Trees', 'industry': 'agri', 'description': 'Reforestation campaign to restore degraded forest lands and fight climate change.', 'goal': 10000000, 'raised': 4800000 },
            { 'name': 'Rural Healthcare Access', 'industry': 'health', 'description': 'Mobile clinics providing primary healthcare to underserved rural communities.', 'goal': 15000000, 'raised': 9000000 },
            { 'name': 'Youth Digital Skills', 'industry': 'tech', 'description': 'Training 5000 youth in digital literacy and coding across informal settlements.', 'goal': 4000000, 'raised': 1200000 },
            { 'name': 'Women Empowerment Hub', 'industry': 'other', 'description': 'Business incubation and mentorship for 500 women entrepreneurs.', 'goal': 6000000, 'raised': 3800000 },
            { 'name': 'Mental Health Awareness', 'industry': 'health', 'description': 'Nationwide campaign to destigmatize mental health and provide counseling services.', 'goal': 2500000, 'raised': 800000 },
            { 'name': 'Disability Support Network', 'industry': 'other', 'description': 'Assistive devices and vocational training for persons with disabilities.', 'goal': 4500000, 'raised': 2200000 },
            { 'name': 'Anti-Poaching Campaign', 'industry': 'other', 'description': 'Protecting endangered wildlife through technology-driven anti-poaching patrols.', 'goal': 12000000, 'raised': 7500000 },
            { 'name': 'Solar for Schools', 'industry': 'energy', 'description': 'Installing solar panels in 200 off-grid schools for sustainable learning.', 'goal': 7000000, 'raised': 3500000 },
        ]
        
        for item in CHARITY_DATA:
            if not Business.objects.filter(name=item['name'], is_charity=True).exists():
                Business.objects.create(
                    founder=user,
                    name=item['name'],
                    industry=item['industry'],
                    description=item['description'],
                    is_charity=True,
                    charity_goal=item['goal'],
                    charity_raised=item['raised'],
                    stage='growth'
                )
                self.stdout.write(self.style.SUCCESS(f"Created charity: {item['name']}"))
        
        # 2. Populate Investment Opportunities
        
        # MMF
        MMF_DATA = [
            { 'title': 'CIC Money Market Fund', 'provider': 'CIC Asset Management', 'return': '14.5%', 'min': 1000, 'risk': 'low' },
            { 'title': 'Cytonn Money Market Fund', 'provider': 'Cytonn Investments', 'return': '16.2%', 'min': 1000, 'risk': 'low' },
            { 'title': 'Sanlam Money Market Fund', 'provider': 'Sanlam Kenya', 'return': '13.8%', 'min': 5000, 'risk': 'low' },
            { 'title': 'Zimele Money Market Fund', 'provider': 'Zimele Asset Mgmt', 'return': '15.1%', 'min': 1000, 'risk': 'low' },
            { 'title': 'ICEA Lion Money Market', 'provider': 'ICEA Lion', 'return': '14.0%', 'min': 5000, 'risk': 'low' },
            { 'title': 'GenAfrica Money Market', 'provider': 'GenAfrica Asset Mgmt', 'return': '14.8%', 'min': 1000, 'risk': 'low' },
            { 'title': 'Nabo Africa MMF', 'provider': 'Nabo Capital', 'return': '15.5%', 'min': 10000, 'risk': 'low' },
            { 'title': 'KCB Money Market Fund', 'provider': 'KCB Investment', 'return': '13.2%', 'min': 2500, 'risk': 'low' },
            { 'title': 'Britam Money Market Fund', 'provider': 'Britam Asset Mgmt', 'return': '14.3%', 'min': 1000, 'risk': 'low' },
            { 'title': 'Old Mutual Money Market', 'provider': 'Old Mutual Investment', 'return': '13.9%', 'min': 5000, 'risk': 'low' },
            { 'title': 'Madison Money Market Fund', 'provider': 'Madison Investment', 'return': '14.7%', 'min': 1000, 'risk': 'low' },
        ]

        for item in MMF_DATA:
            if not InvestmentOpportunity.objects.filter(title=item['title'], type='mmf').exists():
                InvestmentOpportunity.objects.create(
                    title=item['title'],
                    provider=item['provider'],
                    type='mmf',
                    min_investment=item['min'],
                    expected_return=item['return'],
                    risk_level=item['risk'],
                    description=f"Money Market Fund by {item['provider']}"
                )
                self.stdout.write(self.style.SUCCESS(f"Created MMF: {item['title']}"))

        # Stocks
        STOCKS_DATA = [
            { 'name': 'Safaricom PLC', 'ticker': 'SCOM', 'price': 28.50, 'sector': 'Telecommunications' },
            { 'name': 'Equity Group Holdings', 'ticker': 'EQTY', 'price': 45.75, 'sector': 'Banking' },
            { 'name': 'KCB Group PLC', 'ticker': 'KCB', 'price': 32.10, 'sector': 'Banking' },
            { 'name': 'East African Breweries', 'ticker': 'EABL', 'price': 165.00, 'sector': 'Manufacturing' },
            { 'name': 'BAT Kenya', 'ticker': 'BAT', 'price': 350.00, 'sector': 'Manufacturing' },
            { 'name': 'ABSA Bank Kenya', 'ticker': 'ABSA', 'price': 14.20, 'sector': 'Banking' },
            { 'name': 'Co-operative Bank', 'ticker': 'COOP', 'price': 13.80, 'sector': 'Banking' },
            { 'name': 'Kenya Power', 'ticker': 'KPLC', 'price': 3.20, 'sector': 'Energy' },
            { 'name': 'Nation Media Group', 'ticker': 'NMG', 'price': 18.50, 'sector': 'Media' },
            { 'name': 'Standard Chartered KE', 'ticker': 'SCBK', 'price': 185.00, 'sector': 'Banking' },
            { 'name': 'Jubilee Holdings', 'ticker': 'JUB', 'price': 210.00, 'sector': 'Insurance' },
        ]

        for item in STOCKS_DATA:
            if not InvestmentOpportunity.objects.filter(title=item['name'], type='stock').exists():
                InvestmentOpportunity.objects.create(
                    title=item['name'],
                    provider='NSE', # Assuming generic provider
                    type='stock',
                    min_investment=item['price'], # Using current price as min investment
                    expected_return='Variable',
                    risk_level='medium',
                    description=f"{item['name']} ({item['ticker']}) - {item['sector']}"
                )
                self.stdout.write(self.style.SUCCESS(f"Created Stock: {item['name']}"))

        # Domestic Bonds
        BONDS_DOMESTIC_DATA = [
            { 'name': 'Kenya Infrastructure Bond 2027', 'issuer': 'Government of Kenya', 'coupon': '14.5%', 'min': 50000 },
            { 'name': 'KE Treasury Bond FXD1/2026', 'issuer': 'Central Bank of Kenya', 'coupon': '13.2%', 'min': 50000 },
            { 'name': 'KE Treasury Bond IFB1/2030', 'issuer': 'Central Bank of Kenya', 'coupon': '12.8%', 'min': 50000 },
            { 'name': 'Safaricom Corporate Bond', 'issuer': 'Safaricom PLC', 'coupon': '13.0%', 'min': 100000 },
            { 'name': 'M-AKIBA Retail Bond', 'issuer': 'Government of Kenya', 'coupon': '10.0%', 'min': 3000 },
            { 'name': 'KE Green Bond IFB2/2029', 'issuer': 'Central Bank of Kenya', 'coupon': '11.5%', 'min': 50000 },
            { 'name': 'Equity Group Corporate Bond', 'issuer': 'Equity Group', 'coupon': '12.5%', 'min': 100000 },
            { 'name': 'KE Treasury Bill 91-Day', 'issuer': 'Central Bank of Kenya', 'coupon': '16.1%', 'min': 100000 },
            { 'name': 'KE Treasury Bill 182-Day', 'issuer': 'Central Bank of Kenya', 'coupon': '16.5%', 'min': 100000 },
            { 'name': 'KE Treasury Bill 364-Day', 'issuer': 'Central Bank of Kenya', 'coupon': '16.8%', 'min': 100000 },
        ]
        
        for item in BONDS_DOMESTIC_DATA:
             if not InvestmentOpportunity.objects.filter(title=item['name'], type='bond_domestic').exists():
                InvestmentOpportunity.objects.create(
                    title=item['name'],
                    provider=item['issuer'],
                    type='bond_domestic',
                    min_investment=item['min'],
                    expected_return=item['coupon'],
                    risk_level='low',
                    description=f"{item['name']} issued by {item['issuer']}"
                )
                self.stdout.write(self.style.SUCCESS(f"Created Domestic Bond: {item['name']}"))

        # Foreign Bonds
        BONDS_FOREIGN_DATA = [
            { 'name': 'US Treasury Bond 10-Year', 'issuer': 'US Government', 'coupon': '4.3%', 'min': 1000 },
            { 'name': 'UK Gilt 2030', 'issuer': 'UK Government', 'coupon': '4.1%', 'min': 1000 },
            { 'name': 'Euro Bond EUAFR/2028', 'issuer': 'African Development Bank', 'coupon': '5.5%', 'min': 5000 },
            { 'name': 'Kenya Eurobond 2031', 'issuer': 'Republic of Kenya', 'coupon': '7.0%', 'min': 10000 },
            { 'name': 'South Africa Govt Bond', 'issuer': 'Republic of SA', 'coupon': '8.5%', 'min': 5000 },
            { 'name': 'Nigeria Eurobond 2033', 'issuer': 'Federal Govt Nigeria', 'coupon': '8.3%', 'min': 10000 },
            { 'name': 'IFC Green Bond', 'issuer': 'Intl Finance Corp', 'coupon': '3.8%', 'min': 5000 },
            { 'name': 'Japan Govt Bond 5-Year', 'issuer': 'Govt of Japan', 'coupon': '0.8%', 'min': 10000 },
            { 'name': 'Ghana Eurobond 2030', 'issuer': 'Republic of Ghana', 'coupon': '9.2%', 'min': 10000 },
            { 'name': 'World Bank Bond 2027', 'issuer': 'World Bank (IBRD)', 'coupon': '4.0%', 'min': 5000 },
        ]

        for item in BONDS_FOREIGN_DATA:
             if not InvestmentOpportunity.objects.filter(title=item['name'], type='bond_foreign').exists():
                InvestmentOpportunity.objects.create(
                    title=item['name'],
                    provider=item['issuer'],
                    type='bond_foreign',
                    min_investment=item['min'],
                    expected_return=item['coupon'],
                    risk_level='medium',
                    description=f"{item['name']} issued by {item['issuer']}"
                )
                self.stdout.write(self.style.SUCCESS(f"Created Foreign Bond: {item['name']}"))

        # Agencies
        AGENCY_DATA = [
            { 'name': 'Genghis Capital', 'type': 'Full Service Broker', 'min': 10000 },
            { 'name': 'Faida Investment Bank', 'type': 'Investment Bank', 'min': 25000 },
            { 'name': 'SBG Securities', 'type': 'Stockbroker', 'min': 5000 },
            { 'name': 'Cytonn Investments', 'type': 'Alternative Investment', 'min': 1000 },
            { 'name': 'Nabo Capital', 'type': 'Wealth Management', 'min': 50000 },
            { 'name': 'KCB Capital', 'type': 'Investment Banking', 'min': 10000 },
            { 'name': 'AIB-AXYS Africa', 'type': 'Stockbroker', 'min': 15000 },
            { 'name': 'EFG Hermes Kenya', 'type': 'Investment Bank', 'min': 100000 },
            { 'name': 'Sterling Capital', 'type': 'Stockbroker', 'min': 5000 },
            { 'name': 'ABC Capital', 'type': 'Investment Services', 'min': 10000 },
        ]

        for item in AGENCY_DATA:
             if not InvestmentOpportunity.objects.filter(title=item['name'], type='agency').exists():
                InvestmentOpportunity.objects.create(
                    title=item['name'],
                    provider=item['type'], # Using type as provider for agencies
                    type='agency',
                    min_investment=item['min'],
                    expected_return='N/A',
                    risk_level='low',
                    description=f"{item['name']} - {item['type']}"
                )
                self.stdout.write(self.style.SUCCESS(f"Created Agency: {item['name']}"))

        self.stdout.write(self.style.SUCCESS('Data population complete.'))
