import re

CURRENCY_MAP = {
    # Saudi Riyal
    'sar': 'SAR', 'ريال': 'SAR', '﷼': 'SAR', 'سعودي': 'SAR',
    # US Dollar / USDT
    'usd': 'USDT', 'usdt': 'USDT', 'دولار': 'USDT', '$': 'USDT',
    # Egyptian Pound
    'egp': 'EGP', 'مصري': 'EGP', 'جنيه مصري': 'EGP',
    # UAE Dirham
    'aed': 'AED', 'درهم': 'AED', 'إماراتي': 'AED',
    # Euro
    'eur': 'EUR', 'يورو': 'EUR', '€': 'EUR',
    # British Pound
    'gbp': 'GBP', 'استرليني': 'GBP', 'إسترليني': 'GBP', '£': 'GBP',
    # Qatari Riyal
    'qar': 'QAR', 'قطري': 'QAR',
    # Kuwaiti Dinar
    'kwd': 'KWD', 'كويتي': 'KWD', 'دينار كويتي': 'KWD',
    # Omani Rial
    'omr': 'OMR', 'عماني': 'OMR',
    # Bahraini Dinar
    'bhd': 'BHD', 'بحريني': 'BHD',
    # Turkish Lira
    'try': 'TRY', 'تركي': 'TRY', 'ليرة': 'TRY', '₺': 'TRY',
    # Sudanese Pound
    'sdg': 'SDG', 'سوداني': 'SDG', 'جنيه': 'SDG', 'ج.س': 'SDG'
}

# Regex for "X to Y" with optional amount: e.g. "50 sar to sdg", "usdt to sar", "30 usdt to egp"
# Using regex that captures amount, cur1, and cur2
TO_REGEX = re.compile(
    r'^(?:(?P<amount>\d*\.?\d+)\s*)?'
    r'(?P<cur1>[a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669\$\€\£\﷼\₺]+)\s+'
    r'to\s+'
    r'(?P<cur2>[a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669\$\€\£\﷼\₺]+)$',
    re.IGNORECASE
)

# Regex for direct amount + currency: e.g. "50 sar", "5 usdt", "10 دولار", "500 مصري", "500﷼"
DIRECT_REGEX_1 = re.compile(
    r'^(?P<amount>\d*\.?\d+)\s*(?P<cur>[a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669\$\€\£\﷼\₺]+)$',
    re.IGNORECASE
)

# Regex for currency + amount: e.g. "دولار 10", "ريال 50", "$50"
DIRECT_REGEX_2 = re.compile(
    r'^(?P<cur>[a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669\$\€\£\﷼\₺]+)\s*(?P<amount>\d*\.?\d+)$',
    re.IGNORECASE
)

def normalize_currency(raw):
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return CURRENCY_MAP.get(cleaned)

def parse_input(text):
    if not text:
        return None
    text = re.sub(r'@P2P_Live_robot', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'(\d+),(\d+)', r'\1.\2', text)
    if not text:
        return None
        
    # Check "X to Y"
    m_to = TO_REGEX.match(text)
    if m_to:
        raw_amt = m_to.group('amount')
        amount = float(raw_amt) if raw_amt else 1.0
        c1 = normalize_currency(m_to.group('cur1'))
        c2 = normalize_currency(m_to.group('cur2'))
        if c1 and c2 and c1 != c2:
            return {'type': 'convert_pair', 'amount': amount, 'from': c1, 'to': c2}
            
    # Check direct amount + currency
    m_d1 = DIRECT_REGEX_1.match(text)
    if m_d1:
        amount = float(m_d1.group('amount'))
        c = normalize_currency(m_d1.group('cur'))
        if c:
            # If target currency is SDG, e.g. "50000 sdg" -> convert to USD
            target = 'USDT' if c == 'SDG' else 'SDG'
            return {'type': 'direct', 'amount': amount, 'from': c, 'to': target}
            
    # Check currency + amount
    m_d2 = DIRECT_REGEX_2.match(text)
    if m_d2:
        amount = float(m_d2.group('amount'))
        c = normalize_currency(m_d2.group('cur'))
        if c:
            target = 'USDT' if c == 'SDG' else 'SDG'
            return {'type': 'direct', 'amount': amount, 'from': c, 'to': target}
            
    return None

if __name__ == '__main__':
    test_cases = [
        '50 sar', '50SAR', '30 usdt', 'usdt to sar', '50 sar to sdg',
        '30 usdt to egp', '10 دولار', '50 ريال', '500 مصري', '100 درهم',
        '500﷼', '20 يورو', '15 استرليني', 'دولار', 'ريال', '100 sdg to sar'
    ]
    for tc in test_cases:
        res = parse_input(tc)
        print(f'{tc:18} -> {res}')
