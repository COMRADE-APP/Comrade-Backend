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
