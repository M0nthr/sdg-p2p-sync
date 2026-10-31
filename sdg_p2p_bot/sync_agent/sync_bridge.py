"""
Binance P2P Real-Time Sync Bridge
Runs in GitHub Actions (or locally) to bypass datacenter IP restrictions
and sync 100% genuine Binance P2P rates directly into Cloudflare Worker KV.
"""

import json
import urllib.request
import urllib.error
import re
import sys

# Ensure UTF-8 stdout on Windows and CI runners
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

WORKER_SYNC_URL = "https://sdg-p2p-bot.mondon909.workers.dev/api/sync"
SYNC_SECRET = "p2p_sdg_bridge_secure_key_2026"

BINANCE_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Origin": "https://p2p.binance.com",
    "Referer": "https://p2p.binance.com/en/trade/all-payments/USDT?fiat=SDG",
    "clienttype": "web"
}

TOP_CURRENCIES = ["SAR", "AED", "QAR", "KWD", "OMR", "BHD", "EGP", "EUR", "GBP", "TRY"]

def filter_outliers(prices):
    if not prices:
        return []
    prices.sort()
    n = len(prices)
    mid = n // 2
    median = prices[mid] if n % 2 != 0 else (prices[mid - 1] + prices[mid]) / 2.0
    # Wide tolerance threshold: only filter out extreme prices deviating by 500 SDG or more
    band = 500.0
    filtered = [p for p in prices if abs(p - median) <= band]
    return filtered if filtered else prices

def fetch_binance_sdg(trade_type):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    payload = json.dumps({
        "asset": "USDT",
        "fiat": "SDG",
        "tradeType": trade_type,
        "page": 1,
        "rows": 30,
        "payTypes": []
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers=BINANCE_HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            if res.status != 200:
                print(f"[-] Binance {trade_type} returned status {res.status}")
                return [], set()
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("data", [])
            prices = []
            merchants = set()
            ads = []
            for item in items:
                adv = item.get("adv", {})
                advertiser = item.get("advertiser", {})
                adv_no = str(adv.get("advNo", ""))
                p = float(adv.get("price", 0))
                surplus = float(adv.get("surplusAmount", 0))
                nick = advertiser.get("nickName", "")
                if p >= 8000 and surplus >= 10:
                    prices.append(p)
                    if nick:
                        merchants.add(nick)
                    if adv_no:
                        ads.append({
                            "advNo": adv_no,
                            "price": p,
                            "surplus": surplus,
                            "nick": nick,
                            "type": "شراء" if trade_type == "BUY" else "بيع"
                        })
            print(f"[+] Binance {trade_type}: Fetched {len(prices)} prices from {len(merchants)} merchants, {len(ads)} active ads tracked.")
            return filter_outliers(prices), merchants, ads
    except Exception as e:
        print(f"[-] Error fetching Binance {trade_type}: {e}")
        return [], set(), []

def fetch_alsoug():
    url = "https://www.alsoug.com/currency"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en;q=0.9"
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            html = res.read().decode("utf-8")
            tr_match = re.search(r"<tr[^>]*>[\s\S]*?الدولار[\s\S]*?<\/tr>", html, re.I)
            if tr_match:
                tds = re.findall(r"<td[^>]*>([\s\S]*?)<\/td>", tr_match.group(0), re.I)
                clean_tds = [re.sub(r"<[^>]+>", "", td).strip() for td in tds]
                raw_val = clean_tds[2] if len(clean_tds) > 2 else (clean_tds[1] if len(clean_tds) > 1 else None)
                if raw_val:
                    val = float(raw_val.replace(",", "").strip())
                    if val > 5000:
                        return val
    except Exception as e:
        print(f"[-] Error fetching Alsoug: {e}")
    return 0.0

def fetch_fiat_rates():
    fiat_rates = {}
    for cur in TOP_CURRENCIES:
        url = f"https://www.binance.com/bapi/c2c/v1/public/c2c/agent/quote-price?fiat={cur}&asset=USDT&tradeType=BUY"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode("utf-8"))
                    p = float(data.get("data", {}).get("price", 0))
                    if p > 0:
                        fiat_rates[cur] = p
        except Exception:
            pass
    return fiat_rates

def sync_to_cloudflare(payload):
    url = f"{WORKER_SYNC_URL}?secret={SYNC_SECRET}"
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            raw_resp = res.read().decode("utf-8")
            try:
                resp_data = json.loads(raw_resp)
                print(f"[SUCCESS] Cloudflare Worker response: {json.dumps(resp_data, indent=2, ensure_ascii=False)}")
            except Exception:
                print(f"[SUCCESS] Cloudflare Worker response: {raw_resp}")
            return True
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        print(f"[FAIL] HTTP error {e.code}: {err_msg}")
    except Exception as e:
        print(f"[FAIL] Error posting to Cloudflare: {e}")
    return False

def main():
    print("=" * 60)
    print("🚀 Starting Binance P2P Sync to Cloudflare Worker...")
    print("=" * 60)

    buy_prices, buy_merchants, buy_ads = fetch_binance_sdg("BUY")
    sell_prices, sell_merchants, sell_ads = fetch_binance_sdg("SELL")
    alsoug_rate = fetch_alsoug()
    fiat_rates = fetch_fiat_rates()

    all_merchants = buy_merchants.union(sell_merchants)
    all_ads = buy_ads + sell_ads

    if buy_prices and sell_prices:
        buy_avg = sum(buy_prices) / len(buy_prices)
        sell_avg = sum(sell_prices) / len(sell_prices)
        b_avg = round(buy_avg)
        s_avg = round(sell_avg)
        g_avg = round((buy_avg + sell_avg) / 2)
        
        sdg_data = {
            "avg": g_avg,
            "buy_avg": b_avg,
            "buy_max": round(max(buy_prices)),
            "buy_min": round(min(buy_prices)),
            "sell_avg": s_avg,
            "sell_max": round(max(sell_prices)),
            "sell_min": round(min(sell_prices)),
            "traders_count": len(all_merchants) if all_merchants else (len(buy_prices) + len(sell_prices))
        }
        print(f"\n📊 Calculated Real-Time Binance P2P Rates:")
        print(f"  • General Average : {g_avg:,} SDG")
        print(f"  • Buy Average     : {b_avg:,} SDG (Min: {sdg_data['buy_min']:,} | Max: {sdg_data['buy_max']:,})")
        print(f"  • Sell Average    : {s_avg:,} SDG (Min: {sdg_data['sell_min']:,} | Max: {sdg_data['sell_max']:,})")
        print(f"  • Active Traders  : {sdg_data['traders_count']} merchants")
        print(f"  • Tracked Ads     : {len(all_ads)} active advertisements")
        alsoug_disp = f"{int(alsoug_rate):,} SDG" if alsoug_rate > 0 else "غير متوفر"
        print(f"  • Alsoug Rate     : {alsoug_disp}\n")
    else:
        print("[-] Could not fetch Binance prices. Aborting sync.")
        sys.exit(1)

    payload = {
        "sdg_data": sdg_data,
        "alsoug_usd": alsoug_rate,
        "fiat_rates": fiat_rates,
        "ads": all_ads
    }

    print("[*] Syncing data to Cloudflare Worker...")
    success = sync_to_cloudflare(payload)
    if success:
        print("\n✅ Sync Completed Successfully! Cloudflare Worker KV is now 100% up to date.")
    else:
        print("\n❌ Sync Failed. Check Worker secret or URL.")
        sys.exit(1)

if __name__ == "__main__":
    main()
