"""
Utilities for inferring user currency and language from email TLD and browser locale.
"""

# Map country-code TLDs to ISO 4217 currency codes
EMAIL_TLD_TO_CURRENCY = {
    'ke': 'KES',   # Kenya
    'ug': 'UGX',   # Uganda
    'tz': 'TZS',   # Tanzania
    'rw': 'RWF',   # Rwanda
    'et': 'ETB',   # Ethiopia
    'ng': 'NGN',   # Nigeria
    'gh': 'GHS',   # Ghana
    'za': 'ZAR',   # South Africa
    'eg': 'EGP',   # Egypt
    'ma': 'MAD',   # Morocco
    'uk': 'GBP',   # United Kingdom
    'gb': 'GBP',   # Great Britain (alias)
    'us': 'USD',   # United States
    'ca': 'CAD',   # Canada
    'au': 'AUD',   # Australia
    'nz': 'NZD',   # New Zealand
    'in': 'INR',   # India
    'jp': 'JPY',   # Japan
    'cn': 'CNY',   # China
    'kr': 'KRW',   # South Korea
    'br': 'BRL',   # Brazil
    'mx': 'MXN',   # Mexico
    'de': 'EUR',   # Germany
    'fr': 'EUR',   # France
    'it': 'EUR',   # Italy
    'es': 'EUR',   # Spain
    'nl': 'EUR',   # Netherlands
    'pt': 'EUR',   # Portugal
    'be': 'EUR',   # Belgium
    'at': 'EUR',   # Austria
    'ie': 'EUR',   # Ireland
    'fi': 'EUR',   # Finland
    'se': 'SEK',   # Sweden
    'no': 'NOK',   # Norway
    'dk': 'DKK',   # Denmark
    'ch': 'CHF',   # Switzerland
    'pl': 'PLN',   # Poland
    'ru': 'RUB',   # Russia
    'ae': 'AED',   # UAE
    'sa': 'SAR',   # Saudi Arabia
    'sg': 'SGD',   # Singapore
    'my': 'MYR',   # Malaysia
    'ph': 'PHP',   # Philippines
    'th': 'THB',   # Thailand
    'id': 'IDR',   # Indonesia
    'pk': 'PKR',   # Pakistan
}

# Map browser locale prefixes to ISO 4217 currency codes
LOCALE_TO_CURRENCY = {
    'en-US': 'USD',
    'en-GB': 'GBP',
    'en-AU': 'AUD',
    'en-CA': 'CAD',
    'en-NZ': 'NZD',
    'en-KE': 'KES',
    'en-NG': 'NGN',
    'en-ZA': 'ZAR',
    'en-GH': 'GHS',
    'en-IN': 'INR',
    'en-SG': 'SGD',
    'en-PH': 'PHP',
    'sw': 'KES',       # Swahili → Kenya
    'sw-KE': 'KES',
    'sw-TZ': 'TZS',
    'fr-FR': 'EUR',
    'fr-CA': 'CAD',
    'fr-BE': 'EUR',
    'fr-CH': 'CHF',
    'de-DE': 'EUR',
    'de-AT': 'EUR',
    'de-CH': 'CHF',
    'es-ES': 'EUR',
    'es-MX': 'MXN',
    'pt-BR': 'BRL',
    'pt-PT': 'EUR',
    'it-IT': 'EUR',
    'nl-NL': 'EUR',
    'ja-JP': 'JPY',
    'ko-KR': 'KRW',
    'zh-CN': 'CNY',
    'ar-AE': 'AED',
    'ar-SA': 'SAR',
    'ar-EG': 'EGP',
    'hi-IN': 'INR',
    'ms-MY': 'MYR',
    'th-TH': 'THB',
    'id-ID': 'IDR',
    'ru-RU': 'RUB',
    'sv-SE': 'SEK',
    'nb-NO': 'NOK',
    'da-DK': 'DKK',
    'pl-PL': 'PLN',
}

# Map browser locale prefixes to supported platform languages (BCP 47)
LOCALE_TO_LANGUAGE = {
    'en': 'en',
    'sw': 'sw',
    'fr': 'fr',
    'es': 'es',
    'de': 'de',
    'pt': 'pt',
    'ar': 'ar',
    'zh': 'zh',
    'ja': 'ja',
    'ko': 'ko',
    'hi': 'hi',
    'it': 'it',
    'nl': 'nl',
    'ru': 'ru',
    'sv': 'sv',
    'pl': 'pl',
}

# Map TLDs to language (best-guess)
EMAIL_TLD_TO_LANGUAGE = {
    'ke': 'en',
    'ug': 'en',
    'tz': 'sw',
    'rw': 'en',
    'ng': 'en',
    'gh': 'en',
    'za': 'en',
    'uk': 'en',
    'gb': 'en',
    'us': 'en',
    'ca': 'en',
    'au': 'en',
    'nz': 'en',
    'in': 'en',
    'ph': 'en',
    'sg': 'en',
    'fr': 'fr',
    'be': 'fr',
    'ch': 'de',
    'de': 'de',
    'at': 'de',
    'es': 'es',
    'mx': 'es',
    'it': 'it',
    'pt': 'pt',
    'br': 'pt',
    'nl': 'nl',
    'jp': 'ja',
    'kr': 'ko',
    'cn': 'zh',
    'ru': 'ru',
    'ae': 'ar',
    'sa': 'ar',
    'eg': 'ar',
    'se': 'sv',
    'no': 'en',   # Most Norwegians use English platforms
    'dk': 'en',
    'pl': 'pl',
}

# Supported currencies with display info
CURRENCY_INFO = {
    'USD': {'symbol': '$',   'name': 'US Dollar'},
    'KES': {'symbol': 'KSh', 'name': 'Kenyan Shilling'},
    'GBP': {'symbol': '£',   'name': 'British Pound'},
    'EUR': {'symbol': '€',   'name': 'Euro'},
    'NGN': {'symbol': '₦',   'name': 'Nigerian Naira'},
    'GHS': {'symbol': 'GH₵', 'name': 'Ghanaian Cedi'},
    'ZAR': {'symbol': 'R',   'name': 'South African Rand'},
    'UGX': {'symbol': 'USh', 'name': 'Ugandan Shilling'},
    'TZS': {'symbol': 'TSh', 'name': 'Tanzanian Shilling'},
    'RWF': {'symbol': 'FRw', 'name': 'Rwandan Franc'},
    'ETB': {'symbol': 'Br',  'name': 'Ethiopian Birr'},
    'EGP': {'symbol': 'E£',  'name': 'Egyptian Pound'},
    'MAD': {'symbol': 'MAD', 'name': 'Moroccan Dirham'},
    'INR': {'symbol': '₹',   'name': 'Indian Rupee'},
    'CAD': {'symbol': 'C$',  'name': 'Canadian Dollar'},
    'AUD': {'symbol': 'A$',  'name': 'Australian Dollar'},
    'NZD': {'symbol': 'NZ$', 'name': 'New Zealand Dollar'},
    'JPY': {'symbol': '¥',   'name': 'Japanese Yen'},
    'CNY': {'symbol': '¥',   'name': 'Chinese Yuan'},
    'KRW': {'symbol': '₩',   'name': 'South Korean Won'},
    'BRL': {'symbol': 'R$',  'name': 'Brazilian Real'},
    'MXN': {'symbol': 'MX$', 'name': 'Mexican Peso'},
    'SEK': {'symbol': 'kr',  'name': 'Swedish Krona'},
    'NOK': {'symbol': 'kr',  'name': 'Norwegian Krone'},
    'DKK': {'symbol': 'kr',  'name': 'Danish Krone'},
    'CHF': {'symbol': 'CHF', 'name': 'Swiss Franc'},
    'PLN': {'symbol': 'zł',  'name': 'Polish Zloty'},
    'RUB': {'symbol': '₽',   'name': 'Russian Ruble'},
    'AED': {'symbol': 'AED', 'name': 'UAE Dirham'},
    'SAR': {'symbol': 'SAR', 'name': 'Saudi Riyal'},
    'SGD': {'symbol': 'S$',  'name': 'Singapore Dollar'},
    'MYR': {'symbol': 'RM',  'name': 'Malaysian Ringgit'},
    'PHP': {'symbol': '₱',   'name': 'Philippine Peso'},
    'THB': {'symbol': '฿',   'name': 'Thai Baht'},
    'IDR': {'symbol': 'Rp',  'name': 'Indonesian Rupiah'},
    'PKR': {'symbol': '₨',   'name': 'Pakistani Rupee'},
}

# Supported platform languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'sw': 'Kiswahili',
    'fr': 'Français',
    'es': 'Español',
    'de': 'Deutsch',
    'pt': 'Português',
    'ar': 'العربية',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
    'hi': 'हिन्दी',
    'it': 'Italiano',
    'nl': 'Nederlands',
    'ru': 'Русский',
    'sv': 'Svenska',
    'pl': 'Polski',
}


def infer_currency_from_email(email):
    """
    Extract TLD from email domain and map to currency.
    Returns currency code or None.
    """
    if not email or '@' not in email:
        return None
    domain = email.rsplit('@', 1)[-1].lower()
    tld = domain.rsplit('.', 1)[-1]
    return EMAIL_TLD_TO_CURRENCY.get(tld)


def infer_language_from_email(email):
    """
    Extract TLD from email domain and map to language.
    Returns language code or None.
    """
    if not email or '@' not in email:
        return None
    domain = email.rsplit('@', 1)[-1].lower()
    tld = domain.rsplit('.', 1)[-1]
    return EMAIL_TLD_TO_LANGUAGE.get(tld)


def infer_currency_from_locale(locale_str):
    """
    Map a browser locale string (e.g. 'en-US', 'sw-KE') to a currency.
    Tries exact match first, then the language prefix.
    Returns currency code or None.
    """
    if not locale_str:
        return None
    locale_str = locale_str.strip()
    # Try exact match
    if locale_str in LOCALE_TO_CURRENCY:
        return LOCALE_TO_CURRENCY[locale_str]
    # Try with region normalized (en-us → en-US)
    parts = locale_str.split('-')
    if len(parts) == 2:
        normalized = f"{parts[0].lower()}-{parts[1].upper()}"
        if normalized in LOCALE_TO_CURRENCY:
            return LOCALE_TO_CURRENCY[normalized]
    return None


def infer_language_from_locale(locale_str):
    """
    Map a browser locale string to a platform language.
    Returns language code or 'en' as default.
    """
    if not locale_str:
        return 'en'
    locale_str = locale_str.strip()
    # Try exact match
    if locale_str in LOCALE_TO_LANGUAGE:
        return LOCALE_TO_LANGUAGE[locale_str]
    # Try language prefix (e.g. 'en-US' → 'en')
    lang_prefix = locale_str.split('-')[0].lower()
    return LOCALE_TO_LANGUAGE.get(lang_prefix, 'en')


def get_currency_symbol(currency_code):
    """Return the display symbol for a currency code."""
    info = CURRENCY_INFO.get(currency_code)
    return info['symbol'] if info else currency_code


def get_currency_name(currency_code):
    """Return the display name for a currency code."""
    info = CURRENCY_INFO.get(currency_code)
    return info['name'] if info else currency_code


# Map ISO 3166-1 alpha-2 country codes to currencies
COUNTRY_TO_CURRENCY = {
    # Africa
    'KE': 'KES',   # Kenya
    'UG': 'UGX',   # Uganda
    'TZ': 'TZS',   # Tanzania
    'RW': 'RWF',   # Rwanda
    'ET': 'ETB',   # Ethiopia
    'NG': 'NGN',   # Nigeria
    'GH': 'GHS',   # Ghana
    'ZA': 'ZAR',   # South Africa
    'EG': 'EGP',   # Egypt
    'MA': 'MAD',   # Morocco
    'DZ': 'DZD',   # Algeria
    'TN': 'TND',   # Tunisia
    'LY': 'LYD',   # Libya
    'SD': 'SDG',   # Sudan
    'CM': 'XAF',   # Cameroon (CFA Franc)
    'CI': 'XOF',   # Ivory Coast (CFA Franc)
    'SN': 'XOF',   # Senegal (CFA Franc)
    'BF': 'XOF',   # Burkina Faso (CFA Franc)
    'ML': 'XOF',   # Mali (CFA Franc)
    'NE': 'XOF',   # Niger (CFA Franc)
    'TG': 'XOF',   # Togo (CFA Franc)
    'BJ': 'XOF',   # Benin (CFA Franc)
    'GA': 'XAF',   # Gabon (CFA Franc)
    'CG': 'XAF',   # Republic of Congo (CFA Franc)
    'CD': 'CDF',   # DRC Congo
    'AO': 'AOA',   # Angola
    'MZ': 'MZN',   # Mozambique
    'ZM': 'ZMW',   # Zambia
    'ZW': 'ZWL',   # Zimbabwe
    'MW': 'MWK',   # Malawi
    'BW': 'BWP',   # Botswana
    'NA': 'NAD',   # Namibia
    'LS': 'LSL',   # Lesotho
    'SZ': 'SZL',   # Eswatini
    'DJ': 'DJF',   # Djibouti
    'ER': 'ERN',   # Eritrea
    'SO': 'SOS',   # Somalia
    'SS': 'SSP',   # South Sudan
    'CF': 'XAF',   # Central African Republic

    # Europe
    'GB': 'GBP',   # United Kingdom
    'UK': 'GBP',   # Great Britain (alias)
    'US': 'USD',   # United States
    'CA': 'CAD',   # Canada
    'AU': 'AUD',   # Australia
    'NZ': 'NZD',   # New Zealand
    'DE': 'EUR',   # Germany
    'FR': 'EUR',   # France
    'IT': 'EUR',   # Italy
    'ES': 'EUR',   # Spain
    'NL': 'EUR',   # Netherlands
    'PT': 'EUR',   # Portugal
    'BE': 'EUR',   # Belgium
    'AT': 'EUR',   # Austria
    'IE': 'EUR',   # Ireland
    'FI': 'EUR',   # Finland
    'GR': 'EUR',   # Greece
    'EE': 'EUR',   # Estonia
    'LV': 'EUR',   # Latvia
    'LT': 'EUR',   # Lithuania
    'SK': 'EUR',   # Slovakia
    'SI': 'EUR',   # Slovenia
    'MT': 'EUR',   # Malta
    'CY': 'EUR',   # Cyprus
    'SE': 'SEK',   # Sweden
    'NO': 'NOK',   # Norway
    'DK': 'DKK',   # Denmark
    'CH': 'CHF',   # Switzerland
    'PL': 'PLN',   # Poland
    'CZ': 'CZK',   # Czech Republic
    'HU': 'HUF',   # Hungary
    'RO': 'RON',   # Romania
    'BG': 'BGN',   # Bulgaria
    'HR': 'EUR',   # Croatia (Euro)
    'RS': 'RSD',   # Serbia
    'BA': 'BAM',   # Bosnia
    'AL': 'ALL',   # Albania
    'MK': 'MKD',   # North Macedonia
    'XK': 'EUR',   # Kosovo
    'ME': 'EUR',   # Montenegro
    'UA': 'UAH',   # Ukraine
    'BY': 'BYN',   # Belarus
    'MD': 'MDL',   # Moldova
    'TR': 'TRY',   # Turkey

    # Asia
    'IN': 'INR',   # India
    'JP': 'JPY',   # Japan
    'CN': 'CNY',   # China
    'KR': 'KRW',   # South Korea
    'HK': 'HKD',   # Hong Kong
    'TW': 'TWD',   # Taiwan
    'SG': 'SGD',   # Singapore
    'MY': 'MYR',   # Malaysia
    'TH': 'THB',   # Thailand
    'ID': 'IDR',   # Indonesia
    'PH': 'PHP',   # Philippines
    'VN': 'VND',   # Vietnam
    'MM': 'MMK',   # Myanmar
    'KH': 'KHR',   # Cambodia
    'LA': 'LAK',   # Laos
    'BN': 'BND',   # Brunei
    'TL': 'USD',   # Timor-Leste
    'NP': 'NPR',   # Nepal
    'BT': 'INR',   # Bhutan
    'LK': 'LKR',   # Sri Lanka
    'MV': 'MVR',   # Maldives
    'PK': 'PKR',   # Pakistan
    'BD': 'BDT',   # Bangladesh
    'AF': 'AFN',   # Afghanistan
    'IR': 'IRR',   # Iran
    'IQ': 'IQD',   # Iraq
    'SA': 'SAR',   # Saudi Arabia
    'AE': 'AED',   # UAE
    'QA': 'QAR',   # Qatar
    'KW': 'KWD',   # Kuwait
    'BH': 'BHD',   # Bahrain
    'OM': 'OMR',   # Oman
    'YE': 'YER',   # Yemen
    'JO': 'JOD',   # Jordan
    'LB': 'LBP',   # Lebanon
    'SY': 'SYP',   # Syria
    'IL': 'ILS',   # Israel
    'PS': 'ILS',   # Palestine

    # Americas
    'BR': 'BRL',   # Brazil
    'MX': 'MXN',   # Mexico
    'AR': 'ARS',   # Argentina
    'CL': 'CLP',   # Chile
    'CO': 'COP',   # Colombia
    'PE': 'PEN',   # Peru
    'VE': 'VES',   # Venezuela
    'EC': 'USD',   # Ecuador (uses USD)
    'BO': 'BOB',   # Bolivia
    'PY': 'PYG',   # Paraguay
    'UY': 'UYU',   # Uruguay
    'GY': 'GYD',   # Guyana
    'SR': 'SRD',   # Suriname
}

# Supported currencies by the platform
PLATFORM_CURRENCIES = [
    'USD', 'EUR', 'GBP', 'KES', 'ZAR', 'NGN', 'GHS', 'TZS', 'UGX',
    'BRL', 'INR', 'CNY', 'JPY', 'AUD', 'CAD', 'CHF', 'AED', 'SAR',
    'SGD', 'MYR', 'PHP', 'THB', 'IDR', 'PKR', 'MAD', 'EGP'
]


def get_currency_from_country(country_code):
    """Get currency code from ISO 3166-1 alpha-2 country code."""
    if not country_code:
        return 'USD'
    return COUNTRY_TO_CURRENCY.get(country_code.upper(), 'USD')


def infer_currency_from_request(request):
    """
    Infer currency from HTTP request headers and user profile.
    Priority: user preferred currency > country_code > Accept-Language > IP geolocation
    """
    from django.conf import settings

    currency = None

    # 1. Check if user is authenticated and has a preferred currency
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            profile = request.user.profile
            if hasattr(profile, 'preferred_currency') and profile.preferred_currency:
                return profile.preferred_currency
            if hasattr(profile, 'country_code') and profile.country_code:
                currency = get_currency_from_country(profile.country_code)
                if currency:
                    return currency
        except Exception:
            pass

    # 2. Check request headers
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    if accept_language:
        currency = infer_currency_from_locale(accept_language)
        if currency and currency in PLATFORM_CURRENCIES:
            return currency

    # 3. Check X-Country-Code header (can be set by frontend)
    country_code_header = request.META.get('HTTP_X_COUNTRY_CODE', '')
    if country_code_header:
        currency = get_currency_from_country(country_code_header)
        if currency:
            return currency

    # 4. Default to platform currency
    return getattr(settings, 'PLATFORM_CURRENCY', 'USD')
