import time
import datetime
import requests
from bs4 import BeautifulSoup
import numpy as np

BINANCE_URL = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json'
}

TOP_CURRENCIES = ['SAR', 'AED', 'QAR', 'KWD', 'OMR', 'BHD', 'EGP', 'EUR', 'GBP', 'TRY']

class PriceEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last_update = 0
        self.cache_duration = 70  # seconds
        
        # Stored data
        self.sdg_data = {
            'avg': 10274.0,
            'buy_avg': 10295.0,
            'buy_max': 10320.0,
            'buy_min': 10250.0,
            'sell_avg': 10253.0,
            'sell_max': 10260.0,
            'sell_min': 10243.0,
        }
        self.alsoug_usd = 10310.0
        self.fiat_rates = {
            'SAR': 3.81,
            'AED': 3.675,
            'QAR': 3.79,
            'KWD': 0.312,
            'OMR': 0.389,
            'BHD': 0.382,
            'EGP': 56.25,
            'EUR': 0.899,
            'GBP': 0.762,
            'TRY': 51.67,
        }
        self.timestamp_str = ""

    def filter_outliers(self, raw_prices):
        if not raw_prices:
            return []
        prices = np.array(raw_prices)
        med = float(np.median(prices))
        mad = float(np.median(np.abs(prices - med)))
        if mad == 0:
            filtered = prices[np.abs(prices - med) <= 0.05 * med]
        else:
            band = 2.5 * (mad if mad > 50 else 100)
            filtered = prices[np.abs(prices - med) <= band]
        return [float(x) for x in filtered] if len(filtered) > 0 else raw_prices

    def fetch_binance_sdg(self, trade_type):
        payload = {
            'asset': 'USDT',
            'fiat': 'SDG',
            'tradeType': trade_type,
            'page': 1,
            'rows': 30,
            'payTypes': []
        }
        try:
            r = self.session.post(BINANCE_URL, json=payload, timeout=12)
            data = r.json().get('data', [])
            prices = []
            merchants = set()
            for item in data:
                adv = item.get('adv', {})
                advertiser = item.get('advertiser', {})
                p = float(adv.get('price', 0))
                surplus = float(adv.get('surplusAmount', 0))
                nick = advertiser.get('nickName')
                if p >= 8000 and surplus >= 10:  # Minimum safety filter
                    prices.append(p)
                    if nick:
                        merchants.add(nick)
            return self.filter_outliers(prices), merchants
        except Exception as e:
            print(f"Error fetching Binance SDG ({trade_type}): {e}")
            return [], set()

    def fetch_alsoug(self):
        try:
            r = self.session.get('https://www.alsoug.com/currency', timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for row in soup.find_all('tr'):
                txt = row.get_text(separator=' | ', strip=True)
                if 'الدولار' in txt:
                    parts = txt.split(' | ')
                    # parts example: ['$ الدولار الامريكي', '4886.38', '10310', 'اعرف المزيد>>']
                    for part in parts:
                        cleaned = part.replace(',', '').strip()
                        if cleaned.isdigit() and float(cleaned) > 5000:
                            return float(cleaned)
        except Exception as e:
            print(f"Error fetching Alsoug: {e}")
        return self.alsoug_usd

    def fetch_fiat_p2p(self, fiat):
        payload = {
            'asset': 'USDT',
            'fiat': fiat,
            'tradeType': 'BUY',
            'page': 1,
            'rows': 5,
            'payTypes': []
        }
        try:
            r = self.session.post(BINANCE_URL, json=payload, timeout=10)
            data = r.json().get('data', [])
            prices = [float(x['adv']['price']) for x in data if 'adv' in x and float(x['adv'].get('price', 0)) > 0]
            if prices:
                return float(np.median(prices))
        except Exception as e:
            print(f"Error fetching fiat {fiat}: {e}")
        return self.fiat_rates.get(fiat, 1.0)

    def refresh(self, force=False):
        now = time.time()
        if not force and (now - self.last_update < self.cache_duration):
            return

        print("Refreshing market prices...")
        # 1. Fetch Binance SDG
        buy_prices, buy_merchants = self.fetch_binance_sdg('BUY')
        sell_prices, sell_merchants = self.fetch_binance_sdg('SELL')
        all_merchants = buy_merchants.union(sell_merchants)

        if buy_prices and sell_prices:
            buy_avg = float(np.mean(buy_prices))
            sell_avg = float(np.mean(sell_prices))
            self.sdg_data = {
                'avg': round((buy_avg + sell_avg) / 2.0, 1),
                'buy_avg': round(buy_avg, 1),
                'buy_max': round(max(buy_prices), 1),
                'buy_min': round(min(buy_prices), 1),
                'sell_avg': round(sell_avg, 1),
                'sell_max': round(max(sell_prices), 1),
                'sell_min': round(min(sell_prices), 1),
                'traders_count': len(all_merchants) if len(all_merchants) > 0 else (len(buy_prices) + len(sell_prices)),
            }

        # 2. Fetch Alsoug
        alsoug_val = self.fetch_alsoug()
        if alsoug_val:
            self.alsoug_usd = alsoug_val

        # 3. Fetch Fiat P2P rates (quick batch)
        for cur in TOP_CURRENCIES:
            val = self.fetch_fiat_p2p(cur)
            if val:
                self.fiat_rates[cur] = val

        self.last_update = now
        
        # Formatted timestamp (UTC+2 / Sudan local time)
        # Using format: YYYY-MM-DD | HH:MM
        current_dt = datetime.datetime.now()
        self.timestamp_str = current_dt.strftime("%Y-%m-%d \\quad \\vert \\quad %H:%M")
        print(f"Refresh complete: USD/SDG = {self.sdg_data['avg']}, Alsoug = {self.alsoug_usd}")

        # Record history snapshot
        self.record_snapshot()

    def record_snapshot(self):
        now = time.time()
        price = self.sdg_data.get('avg', 0)
        if price <= 0:
            return
        if not hasattr(self, 'history'):
            self.history = self.load_history()
        
        last = self.history[-1] if self.history else None
        if not last or (now - last.get('t', 0) >= 1800):
            self.history.append({'t': now, 'p': price, 'a': self.alsoug_usd})
            self.save_history()

    def load_history(self):
        import os, json
        hist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_history.json")
        if os.path.exists(hist_path):
            try:
                with open(hist_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_history(self):
        import os, json
        hist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_history.json")
        try:
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f)
        except Exception:
            pass

    def get_historical_point(self, target_seconds, time_format="dM", default_fallback="—"):
        if not hasattr(self, 'history'):
            self.history = self.load_history()
        if not self.history:
            return {
                'available': False,
                'change_str': "غير متوفر",
                'old_price_str': "—",
                'date_tag': "—"
            }

        now = time.time()
        min_age = target_seconds * 0.5
        max_age = target_seconds * 1.8
        eligible = [h for h in self.history if min_age <= (now - h['t']) <= max_age and h.get('p', 0) > 0]
        if not eligible:
            return {
                'available': False,
                'change_str': "غير متوفر",
                'old_price_str': "—",
                'date_tag': "—"
            }

        closest = min(eligible, key=lambda h: abs((now - h['t']) - target_seconds))
        old_price = closest.get('p', 0)
        if old_price <= 0:
            return {
                'available': False,
                'change_str': "غير متوفر",
                'old_price_str': "—",
                'date_tag': "—"
            }

        cur_price = self.sdg_data.get('avg', 0)
        diff = cur_price - old_price
        pct = (diff / old_price) * 100
        old_unix = int(closest.get('t', now))

        if abs(diff) < 1:
            change_str = "\u200E➖ 0 (0.0%)"
        else:
            sign = "+" if diff > 0 else "-"
            emoji = "📈" if diff > 0 else "📉"
            diff_str = f"{abs(diff):,.0f}"
            pct_str = f"{abs(pct):.2f}"
            change_str = f"\u200E{emoji} {sign}{diff_str} ({sign}{pct_str}%)"

        return {
            'available': True,
            'change_str': change_str,
            'old_price_str': f"<code>{int(old_price):,}</code>",
            'date_tag': f'<tg-time unix="{old_unix}" format="{time_format}">{default_fallback}</tg-time>'
        }

    def calculate_change(self, target_seconds):
        if not hasattr(self, 'history'):
            self.history = self.load_history()
        if not self.history:
            return "غير متوفر"

        now = time.time()
        min_age = target_seconds * 0.7
        max_age = target_seconds * 1.5
        eligible = [h for h in self.history if min_age <= (now - h['t']) <= max_age]
        if not eligible:
            return "غير متوفر"

        closest = min(eligible, key=lambda h: abs((now - h['t']) - target_seconds))
        old_price = closest.get('p', 0)
        if old_price <= 0:
            return "غير متوفر"

        cur_price = self.sdg_data.get('avg', 0)
        diff = cur_price - old_price
        pct = (diff / old_price) * 100

        if abs(diff) < 1:
            return "\u200E➖ 0 SDG (0.0%)"

        sign = "+" if diff > 0 else "-"
        emoji = "📈" if diff > 0 else "📉"
        diff_str = f"{abs(diff):,.0f}"
        pct_str = f"{abs(pct):.2f}"
        return f"\u200E{emoji} {sign}{diff_str} SDG ({sign}{pct_str}%)"

    def get_currency_sdg_rate(self, currency_code):
        cur = currency_code.upper()
        if cur in ['USD', 'USDT']:
            return self.sdg_data['avg']
        if cur == 'SDG':
            return 1.0
        fiat_to_usdt = self.fiat_rates.get(cur)
        if fiat_to_usdt and fiat_to_usdt > 0:
            # 1 USDT = X Fiat, and 1 USDT = Y SDG
            # Therefore: 1 Fiat = (Y / X) SDG
            return self.sdg_data['avg'] / fiat_to_usdt
        return 0.0

    def get_fiat_rate(self, currency_code):
        cur = currency_code.upper()
        if cur in ['USD', 'USDT']:
            return 1.0
        return self.fiat_rates.get(cur, 0.0)
