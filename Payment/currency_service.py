from decimal import Decimal
from django.core.cache import cache
from django.conf import settings
from functools import lru_cache
import requests

# Import from Authentication's currency utilities
try:
    from Authentication.currency_utils import (
        COUNTRY_TO_CURRENCY,
        PLATFORM_CURRENCIES,
        get_currency_from_country,
        infer_currency_from_locale,
        CURRENCY_INFO
    )
except ImportError:
    COUNTRY_TO_CURRENCY = {}
    PLATFORM_CURRENCIES = ['USD', 'EUR', 'GBP', 'KES', 'ZAR', 'NGN', 'GHS', 'TZS', 'UGX']
    get_currency_from_country = lambda x: 'USD'
    infer_currency_from_locale = lambda x: None
    CURRENCY_INFO = {}


class CurrencyService:
    def __init__(self):
        self.provider = getattr(settings, 'CURRENCY_API_PROVIDER', 'currencybeacon')
        self.api_key = getattr(settings, 'CURRENCY_API_KEY', '')
        self.cache_timeout = getattr(settings, 'CURRENCY_CACHE_TIMEOUT', 3600)
        self.default_currency = getattr(settings, 'DEFAULT_CURRENCY', 'USD')
        self.platform_currency = getattr(settings, 'PLATFORM_CURRENCY', 'USD')
        self.supported_currencies = PLATFORM_CURRENCIES

    def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        if from_currency == to_currency:
            return Decimal('1.0')

        cache_key = f"fx_rate_{from_currency}_{to_currency}"
        cached_rate = cache.get(cache_key)
        if cached_rate:
            return Decimal(cached_rate)

        if self.provider == 'currencybeacon':
            rate = self._get_rate_currencybeacon(from_currency, to_currency)
        elif self.provider == 'openexchangerates':
            rate = self._get_rate_openexchangerates(from_currency, to_currency)
        else:
            rate = self._get_rate_forex_python(from_currency, to_currency)

        cache.set(cache_key, str(rate), self.cache_timeout)
        return rate

    def _get_rate_forex_python(self, from_currency: str, to_currency: str) -> Decimal:
        try:
            from forex_python.converter import get_rate
            rate = get_rate(from_currency, to_currency)
            return Decimal(str(rate))
        except Exception:
            return self._get_fallback_rate(from_currency, to_currency)

    def _get_rate_currencybeacon(self, from_currency: str, to_currency: str) -> Decimal:
        if not self.api_key:
            return self._get_rate_forex_python(from_currency, to_currency)

        try:
            url = "https://api.currencybeacon.com/v1/latest"
            params = {
                'base': from_currency,
                'symbols': to_currency,
                'api_key': self.api_key
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            meta = data.get('meta', {})
            if meta.get('code') == 200:
                rates = data.get('rates', {})
                rate = rates.get(to_currency)
                if rate:
                    return Decimal(str(rate))
        except Exception:
            pass
        return self._get_rate_forex_python(from_currency, to_currency)

    def _get_rate_openexchangerates(self, from_currency: str, to_currency: str) -> Decimal:
        if not self.api_key:
            return self._get_rate_forex_python(from_currency, to_currency)

        try:
            url = f"https://openexchangerates.org/api/convert/1/{from_currency}/{to_currency}"
            params = {'app_id': self.api_key}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if 'error' not in data:
                return Decimal(str(data['response']))
        except Exception:
            pass
        return self._get_rate_forex_python(from_currency, to_currency)

    def _get_fallback_rate(self, from_currency: str, to_currency: str) -> Decimal:
        fallback_rates = {
            ('USD', 'EUR'): Decimal('0.92'),
            ('USD', 'GBP'): Decimal('0.79'),
            ('USD', 'KES'): Decimal('130.50'),
            ('USD', 'ZAR'): Decimal('18.50'),
            ('USD', 'NGN'): Decimal('1550.00'),
            ('USD', 'GHS'): Decimal('15.20'),
            ('USD', 'TZS'): Decimal('2500.00'),
            ('USD', 'UGX'): Decimal('3850.00'),
            ('EUR', 'USD'): Decimal('1.09'),
            ('GBP', 'USD'): Decimal('1.27'),
        }
        key = (from_currency, to_currency)
        reverse_key = (to_currency, from_currency)
        if key in fallback_rates:
            return fallback_rates[key]
        if reverse_key in fallback_rates:
            return (Decimal('1.0') / fallback_rates[reverse_key])
        return Decimal('1.0')

    def convert(self, amount: Decimal, from_currency: str, to_currency: str) -> dict:
        rate = self.get_rate(from_currency, to_currency)
        converted_amount = amount * rate

        return {
            'original_amount': float(amount),
            'original_currency': from_currency,
            'converted_amount': round(float(converted_amount), 2),
            'target_currency': to_currency,
            'exchange_rate': float(rate),
            'provider': self.provider
        }

    def get_supported_currencies(self) -> list:
        return self.supported_currencies

    def get_currency_info(self, currency_code: str) -> dict:
        return CURRENCY_INFO.get(currency_code, {})

    def get_all_currencies_info(self) -> dict:
        return {code: CURRENCY_INFO.get(code, {}) for code in self.supported_currencies}

    def get_all_rates(self, base_currency: str = None) -> dict:
        if base_currency is None:
            base_currency = self.platform_currency

        cache_key = f"all_rates_{base_currency}"
        cached_rates = cache.get(cache_key)
        if cached_rates:
            return cached_rates

        rates = {}
        for currency in self.supported_currencies:
            if currency != base_currency:
                rate = self.get_rate(base_currency, currency)
                rates[currency] = float(rate)

        cache.set(cache_key, rates, self.cache_timeout)
        return rates

    def detect_currency_for_user(self, request) -> str:
        """Detect the best currency for a user based on their profile/location."""
        from Authentication.currency_utils import infer_currency_from_request
        return infer_currency_from_request(request)

    def convert_from_user_currency(self, amount: Decimal, user_currency: str = None) -> dict:
        """Convert amount from user's currency to platform currency."""
        if user_currency is None:
            user_currency = self.default_currency
        if user_currency == self.platform_currency:
            return {
                'original_amount': float(amount),
                'converted_amount': float(amount),
                'currency': self.platform_currency,
                'exchange_rate': 1.0
            }
        return self.convert(amount, user_currency, self.platform_currency)

    def convert_to_user_currency(self, amount: Decimal, user_currency: str = None) -> dict:
        """Convert amount from platform currency to user's preferred currency."""
        if user_currency is None:
            user_currency = self.default_currency
        if user_currency == self.platform_currency:
            return {
                'original_amount': float(amount),
                'converted_amount': float(amount),
                'currency': user_currency,
                'exchange_rate': 1.0
            }
        return self.convert(amount, self.platform_currency, user_currency)


currency_service = CurrencyService()


def convert_amount(amount, from_currency, to_currency):
    return currency_service.convert(Decimal(str(amount)), from_currency, to_currency)


def get_exchange_rate(from_currency, to_currency):
    return currency_service.get_rate(from_currency, to_currency)


def convert_to_platform_currency(amount, from_currency):
    """Convert any amount to platform currency (USD by default)."""
    if from_currency == currency_service.platform_currency:
        return {
            'original_amount': float(amount),
            'converted_amount': float(amount),
            'currency': currency_service.platform_currency,
            'exchange_rate': 1.0
        }
    result = currency_service.convert(Decimal(str(amount)), from_currency, currency_service.platform_currency)
    result['currency'] = currency_service.platform_currency
    return result


def convert_from_platform_currency(amount, to_currency):
    """Convert from platform currency to any supported currency."""
    if to_currency == currency_service.platform_currency:
        return {
            'original_amount': float(amount),
            'converted_amount': float(amount),
            'currency': to_currency,
            'exchange_rate': 1.0
        }
    result = currency_service.convert(Decimal(str(amount)), currency_service.platform_currency, to_currency)
    return result


def get_user_currency(request) -> str:
    """Get the appropriate currency for a user request."""
    return currency_service.detect_currency_for_user(request)


def format_currency(amount, currency_code, user_currency=None):
    """Format amount with currency symbol for display."""
    if user_currency and user_currency != currency_code:
        converted = currency_service.convert(Decimal(str(amount)), currency_code, user_currency)
        amount = converted['converted_amount']
        currency_code = user_currency

    info = CURRENCY_INFO.get(currency_code, {})
    symbol = info.get('symbol', currency_code)
    return f"{symbol}{amount:,.2f}"