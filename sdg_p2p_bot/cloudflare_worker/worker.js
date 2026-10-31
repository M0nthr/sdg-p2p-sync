/**
 * P2P Live Telegram Bot - Cloudflare Worker
 * Fully Serverless, Zero-Cold-Start, High-Performance Edge Bot (Rich Message Edition)
 */

const BOT_TOKEN = "9146323294:AAF4QgGnQRpv3SkL-ieMY1ZKxkXjS8plPK4";
const BASE_TG_URL = `https://api.telegram.org/bot${BOT_TOKEN}`;

const ALLOWED_GROUP_ID = -1001382291757;
const ADMIN_USER_ID = 5561387511;

const BINANCE_URLS = [
  "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
  "https://c2c.binance.com/bapi/c2c/v2/friendly/c2c/adv/search",
  "https://www.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
];

const BINANCE_HEADERS = {
  "Content-Type": "application/json",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Accept": "*/*",
  "Accept-Language": "en-US,en;q=0.9",
  "Origin": "https://p2p.binance.com",
  "Referer": "https://p2p.binance.com/en/trade/all-payments/USDT?fiat=SDG",
  "clienttype": "web"
};

const BINANCE_MOBILE_HEADERS = {
  "Content-Type": "application/json",
  "User-Agent": "Binance/2.80.0 (Android 14; Mobile)",
  "clienttype": "android",
  "lang": "en"
};

const TOP_CURRENCIES = ["SAR", "AED", "QAR", "KWD", "OMR", "BHD", "EGP", "EUR", "GBP", "TRY"];

const CURRENCY_MAP = {
  sar: "SAR", "ريال": "SAR", "﷼": "SAR", "سعودي": "SAR",
  usd: "USDT", usdt: "USDT", "دولار": "USDT", "$": "USDT",
  egp: "EGP", "مصري": "EGP", "جنيه مصري": "EGP",
  aed: "AED", "درهم": "AED", "إماراتي": "AED",
  eur: "EUR", "يورو": "EUR", "€": "EUR",
  gbp: "GBP", "استرليني": "GBP", "إسترليني": "GBP", "£": "GBP",
  qar: "QAR", "قطري": "QAR",
  kwd: "KWD", "كويتي": "KWD",
  omr: "OMR", "عماني": "OMR",
  bhd: "BHD", "بحريني": "BHD",
  try: "TRY", "تركي": "TRY", "ليرة": "TRY", "₺": "TRY",
  sdg: "SDG", "سوداني": "SDG", "جنيه": "SDG", "ج.س": "SDG"
};

let memoryCache = {
  lastUpdate: 0,
  lastFiatUpdate: 0,
  sdg_data: null,
  alsoug_usd: 0,
  fiat_rates: {},
  history: []
};

const MAIN_KEYBOARD = {
  inline_keyboard: [
    [
      { text: "عملات أخرى", callback_data: "cb:currencies" },
      { text: "كيفية الإستخدام", callback_data: "cb:help" }
    ],
    [
      { text: "📊 مؤشرات تغير السعر", callback_data: "cb:history" }
    ]
  ]
};

const BACK_KEYBOARD = {
  inline_keyboard: [
    [
      { text: "↩️ الرئيسية", callback_data: "cb:main" }
    ]
  ]
};

function formatNumber(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val)) return "0";
  if (decimals === 0 || val === Math.floor(val)) {
    return Math.floor(val).toLocaleString("en-US");
  }
  return val.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function formatSudanDateTime(unixSec) {
  const d = new Date(unixSec * 1000);
  const months = [
    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
  ];
  // Sudan timezone is UTC+2
  const sudanDate = new Date(d.getTime() + 2 * 3600 * 1000);
  const day = sudanDate.getUTCDate();
  const month = months[sudanDate.getUTCMonth()];
  const year = sudanDate.getUTCFullYear();
  let hours = sudanDate.getUTCHours();
  const minutes = sudanDate.getUTCMinutes().toString().padStart(2, "0");
  const period = hours >= 12 ? "م" : "ص";
  hours = hours % 12 || 12;
  const hoursStr = hours.toString().padStart(2, "0");
  return `${day} ${month} ${year} — ${hoursStr}:${minutes} ${period}`;
}

function filterOutliers(prices) {
  if (!prices || prices.length === 0) return [];
  prices.sort((a, b) => a - b);
  const mid = Math.floor(prices.length / 2);
  const median = prices.length % 2 !== 0 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2;
  const devs = prices.map(p => Math.abs(p - median)).sort((a, b) => a - b);
  const mad = devs.length % 2 !== 0 ? devs[mid] : (devs[mid - 1] + devs[mid]) / 2;
  const band = 2.5 * (mad > 50 ? mad : 100);
  const filtered = prices.filter(p => Math.abs(p - median) <= band);
  return filtered.length > 0 ? filtered : prices;
}

async function fetchBinanceSDG(tradeType) {
  // Strategy 1: Binance Public C2C Ad List (GET) - Most reliable, unblocked by Cloudflare WAF
  const publicAdUrls = [
    `https://www.binance.com/bapi/c2c/v1/public/c2c/agent/ad-list?fiat=SDG&asset=USDT&tradeType=${tradeType}`,
    `https://p2p.binance.com/bapi/c2c/v1/public/c2c/agent/ad-list?fiat=SDG&asset=USDT&tradeType=${tradeType}`
  ];

  for (const url of publicAdUrls) {
    try {
      const res = await fetch(url, {
        headers: {
          "Accept": "application/json, text/plain, */*",
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
      });
      if (!res.ok) continue;
      const text = await res.text();
      if (!text || text.trim().startsWith("<")) continue;
      let data;
      try { data = JSON.parse(text); } catch(e) { continue; }
      const items = data?.data?.items || [];
      const prices = [];
      const merchants = new Set();
      for (const item of items) {
        const p = parseFloat(item.price || 0);
        const amt = parseFloat(item.tradableAmount || 0);
        const nick = item.advertiser?.nickName;
        if (p >= 8000 && amt >= 10) {
          prices.push(p);
          if (nick) merchants.add(nick);
        }
      }
      if (prices.length > 0) {
        return { prices: filterOutliers(prices), merchants };
      }
    } catch (err) {
      console.warn(`Public ad-list error [${tradeType}]:`, err);
    }
  }

  // Strategy 2: Binance Public Quote-Price (GET)
  const quoteUrls = [
    `https://www.binance.com/bapi/c2c/v1/public/c2c/agent/quote-price?fiat=SDG&asset=USDT&tradeType=${tradeType}`,
    `https://p2p.binance.com/bapi/c2c/v1/public/c2c/agent/quote-price?fiat=SDG&asset=USDT&tradeType=${tradeType}`
  ];

  for (const url of quoteUrls) {
    try {
      const res = await fetch(url, {
        headers: {
          "Accept": "application/json, text/plain, */*",
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
      });
      if (!res.ok) continue;
      const text = await res.text();
      if (!text || text.trim().startsWith("<")) continue;
      let data;
      try { data = JSON.parse(text); } catch(e) { continue; }
      const p = parseFloat(data?.data?.price || 0);
      if (p >= 8000) {
        return { prices: [p], merchants: new Set(["BinanceP2P"]) };
      }
    } catch (err) {
      console.warn(`Public quote-price error [${tradeType}]:`, err);
    }
  }

  // Strategy 3: Traditional Binance POST search (fallback)
  for (const apiUrl of BINANCE_URLS) {
    try {
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: BINANCE_HEADERS,
        body: JSON.stringify({
          asset: "USDT",
          fiat: "SDG",
          tradeType: tradeType,
          page: 1,
          rows: 30,
          payTypes: []
        })
      });

      if (!res.ok) continue;
      const text = await res.text();
      if (!text || text.trim().startsWith("<")) continue;

      let data;
      try { data = JSON.parse(text); } catch (err) { continue; }
      const items = data?.data || [];
      const prices = [];
      const merchants = new Set();
      for (const item of items) {
        const adv = item.adv || {};
        const advertiser = item.advertiser || {};
        const p = parseFloat(adv.price || 0);
        const surplus = parseFloat(adv.surplusAmount || 0);
        const nick = advertiser.nickName;
        if (p >= 8000 && surplus >= 10) {
          prices.push(p);
          if (nick) merchants.add(nick);
        }
      }
      if (prices.length > 0) {
        return { prices: filterOutliers(prices), merchants };
      }
    } catch (err) {
      console.error(`Error fetching Binance SDG ${tradeType} from ${apiUrl}:`, err);
    }
  }
  return { prices: [], merchants: new Set() };
}

async function fetchAlsoug() {
  try {
    const res = await fetch("https://www.alsoug.com/currency", {
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" }
    });
    if (!res.ok) return memoryCache.alsoug_usd;
    const text = await res.text();
    const trMatch = text.match(/<tr[^>]*>[\s\S]*?الدولار[\s\S]*?<\/tr>/i);
    if (trMatch) {
      const tdMatches = [...trMatch[0].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/gi)].map(m => m[1].replace(/<[^>]+>/g, "").trim());
      // tdMatches[1] is bank rate, tdMatches[2] is parallel rate
      const rawVal = tdMatches[2] || tdMatches[1];
      if (rawVal) {
        const val = parseFloat(rawVal.replace(/,/g, ""));
        if (val > 5000) return val;
      }
    }
  } catch (err) {
    console.error("Error fetching Alsoug:", err);
  }
  return memoryCache.alsoug_usd;
}

async function fetchFiatP2P(fiat) {
  // Strategy 1: Public Quote-Price (GET) - instant, never blocked
  try {
    const quoteUrl = `https://www.binance.com/bapi/c2c/v1/public/c2c/agent/quote-price?fiat=${fiat}&asset=USDT&tradeType=BUY`;
    const res = await fetch(quoteUrl, {
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" }
    });
    if (res.ok) {
      const text = await res.text();
      if (text && !text.trim().startsWith("<")) {
        const data = JSON.parse(text);
        const p = parseFloat(data?.data?.price || 0);
        if (p > 0) return p;
      }
    }
  } catch(e) {}

  // Strategy 2: POST fallback
  for (const apiUrl of BINANCE_URLS) {
    try {
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: BINANCE_HEADERS,
        body: JSON.stringify({
          asset: "USDT",
          fiat: fiat,
          tradeType: "BUY",
          page: 1,
          rows: 5,
          payTypes: []
        })
      });
      if (!res.ok) continue;
      const text = await res.text();
      if (!text || text.trim().startsWith("<")) continue;
      let data;
      try {
        data = JSON.parse(text);
      } catch (err) {
        continue;
      }
      const items = data?.data || [];
      const prices = items.map(x => parseFloat(x?.adv?.price || 0)).filter(p => p > 0);
      if (prices.length > 0) {
        prices.sort((a, b) => a - b);
        return prices[Math.floor(prices.length / 2)];
      }
    } catch (err) {
      // ignore and keep cached
    }
  }
  return (memoryCache.fiat_rates && memoryCache.fiat_rates[fiat]) ? memoryCache.fiat_rates[fiat] : 0;
}

function getKV(env) {
  if (!env) return null;
  return env.PRICES_KV || env.STATS_KV || env.HISTORY_KV || env.KV || null;
}

async function loadState(env) {
  const kv = getKV(env);
  if (!kv) return;
  try {
    const cachedRates = await kv.get("latest_rates", "json");
    if (cachedRates && cachedRates.sdg_data) {
      memoryCache.sdg_data = cachedRates.sdg_data;
      if (cachedRates.alsoug_usd) memoryCache.alsoug_usd = cachedRates.alsoug_usd;
      if (cachedRates.fiat_rates) memoryCache.fiat_rates = cachedRates.fiat_rates;
      if (cachedRates.lastUpdate) memoryCache.lastUpdate = cachedRates.lastUpdate;
      if (cachedRates.lastFiatUpdate) memoryCache.lastFiatUpdate = cachedRates.lastFiatUpdate;
    }
    const cachedHist = await kv.get("price_history", "json");
    if (Array.isArray(cachedHist) && cachedHist.length > 0) {
      memoryCache.history = cachedHist;
    }
  } catch (e) {
    console.error("Error loading state from KV:", e);
  }
}

async function saveState(env) {
  const kv = getKV(env);
  if (!kv) return;
  try {
    await kv.put("latest_rates", JSON.stringify({
      sdg_data: memoryCache.sdg_data,
      alsoug_usd: memoryCache.alsoug_usd,
      fiat_rates: memoryCache.fiat_rates,
      lastUpdate: memoryCache.lastUpdate,
      lastFiatUpdate: memoryCache.lastFiatUpdate
    }));
    await kv.put("price_history", JSON.stringify(memoryCache.history));
  } catch (e) {
    console.error("Error saving state to KV:", e);
  }
}

async function recordSnapshot(env, currentPrice, currentAlsoug) {
  if (!currentPrice || currentPrice <= 0) return;
  const now = Date.now();
  const hist = memoryCache.history;
  
  // Save a snapshot every 15 minutes
  const lastSnap = hist.length > 0 ? hist[hist.length - 1] : null;
  if (!lastSnap || (now - lastSnap.t >= 15 * 60 * 1000)) {
    hist.push({ t: now, p: currentPrice, a: currentAlsoug });
    if (hist.length > 10000) {
      memoryCache.history = hist.slice(-10000);
    }
  }
}

function getHistoricalPoint(currentPrice, targetSeconds, timeFormat = "dM", defaultFallback = "—") {
  const hist = memoryCache.history;
  if (!hist || hist.length === 0 || !currentPrice) {
    return {
      available: false,
      changeStr: "غير متوفر",
      oldPriceStr: "—",
      dateTag: "—"
    };
  }

  const now = Date.now();
  const targetMs = targetSeconds * 1000;
  const minAgeMs = targetMs * 0.5;
  const maxAgeMs = targetMs * 1.8;

  const eligible = hist.filter(h => {
    const age = now - h.t;
    return age >= minAgeMs && age <= maxAgeMs && h.p > 0;
  });

  if (eligible.length === 0) {
    return {
      available: false,
      changeStr: "غير متوفر",
      oldPriceStr: "—",
      dateTag: "—"
    };
  }

  let closest = eligible[0];
  let minDiff = Math.abs((now - closest.t) - targetMs);
  for (const item of eligible) {
    const diff = Math.abs((now - item.t) - targetMs);
    if (diff < minDiff) {
      minDiff = diff;
      closest = item;
    }
  }

  const oldPrice = closest.p;
  if (!oldPrice || oldPrice <= 0) {
    return {
      available: false,
      changeStr: "غير متوفر",
      oldPriceStr: "—",
      dateTag: "—"
    };
  }

  const diffVal = currentPrice - oldPrice;
  const pct = (diffVal / oldPrice) * 100;
  const oldUnix = Math.floor(closest.t / 1000);

  let changeStr;
  if (Math.abs(diffVal) < 1) {
    changeStr = "\u200E➖ 0 (0.0%)";
  } else {
    const emoji = diffVal > 0 ? "📈" : "📉";
    const diffStr = formatNumber(Math.abs(diffVal), 0);
    const pctStr = formatNumber(Math.abs(pct), 2);
    const sign = diffVal > 0 ? "+" : "-";
    changeStr = `\u200E${emoji} ${sign}${diffStr} (${sign}${pctStr}%)`;
  }

  return {
    available: true,
    changeStr,
    oldPriceStr: `<code>${formatNumber(oldPrice, 0)}</code>`,
    dateTag: `<tg-time unix="${oldUnix}" format="${timeFormat}">${defaultFallback}</tg-time>`
  };
}

async function refreshRates(force = false, env = null) {
  const now = Date.now();
  if (env) {
    await loadState(env);
  }

  // If data was synced recently from our external sync bridge, keep it!
  if (!force && memoryCache.lastUpdate && (now - memoryCache.lastUpdate < 30 * 60 * 1000)) {
    return;
  }

  const [buyRes, sellRes, alsoug] = await Promise.all([
    fetchBinanceSDG("BUY"),
    fetchBinanceSDG("SELL"),
    fetchAlsoug()
  ]);

  if (alsoug && alsoug > 5000) {
    memoryCache.alsoug_usd = alsoug;
  }

  const buyPrices = buyRes.prices;
  const sellPrices = sellRes.prices;
  const allMerchants = new Set([...buyRes.merchants, ...sellRes.merchants]);

  // Only update sdg_data if genuine Binance P2P prices were fetched
  if (buyPrices.length > 0 && sellPrices.length > 0) {
    const buyAvg = buyPrices.reduce((a, b) => a + b, 0) / buyPrices.length;
    const sellAvg = sellPrices.reduce((a, b) => a + b, 0) / sellPrices.length;
    const bAvg = Math.round(buyAvg);
    const sAvg = Math.round(sellAvg);
    const gAvg = Math.round((buyAvg + sellAvg) / 2);
    memoryCache.sdg_data = {
      avg: gAvg,
      buy_avg: bAvg,
      buy_max: Math.round(Math.max(...buyPrices)),
      buy_min: Math.round(Math.min(...buyPrices)),
      sell_avg: sAvg,
      sell_max: Math.round(Math.max(...sellPrices)),
      sell_min: Math.round(Math.min(...sellPrices)),
      traders_count: allMerchants.size > 0 ? allMerchants.size : (buyPrices.length + sellPrices.length)
    };
    memoryCache.lastUpdate = now;

    if (env) {
      await recordSnapshot(env, memoryCache.sdg_data.avg, memoryCache.alsoug_usd);
      await saveState(env);
    }
  }

  // Update foreign fiats gently once every 10 minutes (to prevent Binance rate-limiting)
  if (!memoryCache.lastFiatUpdate || (now - memoryCache.lastFiatUpdate >= 10 * 60 * 1000)) {
    for (const cur of TOP_CURRENCIES) {
      try {
        const val = await fetchFiatP2P(cur);
        if (val && val > 0) {
          memoryCache.fiat_rates[cur] = val;
        }
      } catch (e) {
        // keep cached
      }
    }
    memoryCache.lastFiatUpdate = now;
  }
}

function getCurrencySdgRate(cur) {
  if (!memoryCache.sdg_data || !memoryCache.sdg_data.avg || memoryCache.sdg_data.avg <= 0) {
    return 0;
  }
  const c = cur.toUpperCase();
  if (c === "USD" || c === "USDT") return memoryCache.sdg_data.avg;
  if (c === "SDG") return 1.0;
  const fRate = memoryCache.fiat_rates ? memoryCache.fiat_rates[c] : null;
  if (fRate && fRate > 0) {
    return memoryCache.sdg_data.avg / fRate;
  }
  return 0;
}

function renderMainPage() {
  const sdg = memoryCache.sdg_data;
  const alsoug = memoryCache.alsoug_usd;
  const nowUnix = Math.floor(Date.now() / 1000);
  const sudanTimeStr = formatSudanDateTime(nowUnix);

  const hasSdg = sdg && sdg.avg && sdg.avg > 0;

  const generalPriceStr = hasSdg ? `<code>${formatNumber(sdg.avg, 0)}</code>` : "<code>غير متوفر</code>";
  const buyAvgStr = hasSdg ? `<code>${formatNumber(sdg.buy_avg, 0)}</code>` : "<code>غير متوفر</code>";
  const sellAvgStr = hasSdg ? `<code>${formatNumber(sdg.sell_avg, 0)}</code>` : "<code>غير متوفر</code>";

  const buyRangeStr = hasSdg ? `${formatNumber(sdg.buy_min, 0)} 📉 | ${formatNumber(sdg.buy_max, 0)} 📈` : "— 📉 | — 📈";
  const sellRangeStr = hasSdg ? `${formatNumber(sdg.sell_min, 0)} 📉 | ${formatNumber(sdg.sell_max, 0)} 📈` : "— 📉 | — 📈";

  let tradersStr = "👥 —";
  if (hasSdg && sdg.traders_count) {
    const tc = sdg.traders_count;
    tradersStr = (tc >= 3 && tc <= 10) ? `👥 ${tc} تجار` : `👥 ${tc} تاجر`;
  }

  const alsougStr = (alsoug && alsoug > 0) ? `<code>\u200E${formatNumber(alsoug, 0)} SDG</code>` : "<code>غير متوفر</code>";

  return `<h1>🌍 أسعار الصرف مقابل الجنيه السوداني</h1>
<p>🕒 <tg-time unix="${nowUnix}" format="wDT">${sudanTimeStr}</tg-time></p>
<hr/>

<table bordered striped>
  <caption>منصة بايننس (Binance P2P)</caption>
  <tr>
    <th align="center">النطاق</th>
    <th align="center">السعر (SDG)</th>
    <th align="center">المؤشر</th>
  </tr>
  <tr>
    <td align="center">${tradersStr}</td>
    <td align="center">${generalPriceStr}</td>
    <td align="center">💵 <b>السعر العام</b></td>
  </tr>
  <tr>
    <td align="center">${buyRangeStr}</td>
    <td align="center">${buyAvgStr}</td>
    <td align="center">🟢 <b>الشراء</b></td>
  </tr>
  <tr>
    <td align="center">${sellRangeStr}</td>
    <td align="center">${sellAvgStr}</td>
    <td align="center">🔴 <b>البيع</b></td>
  </tr>
</table>

<table bordered>
  <caption>تطبيق السوق (Alsoug)</caption>
  <tr>
    <td align="center">${alsougStr}</td>
    <td align="center">🏪 <b>السوق الموازي</b></td>
  </tr>
</table>`;
}

function renderHistoryPage() {
  const currentPrice = (memoryCache.sdg_data && memoryCache.sdg_data.avg > 0) ? memoryCache.sdg_data.avg : 0;
  const p4H = getHistoricalPoint(currentPrice, 4 * 3600, "t", "قبل 4 س");
  const p1D = getHistoricalPoint(currentPrice, 86400, "dM", "أمس");
  const p7D = getHistoricalPoint(currentPrice, 7 * 86400, "dM", "قبل أسبوع");
  const p30D = getHistoricalPoint(currentPrice, 30 * 86400, "dM", "قبل شهر");
  const p1Y = getHistoricalPoint(currentPrice, 365 * 86400, "yM", "قبل سنة");

  return `<h1>📊 مؤشرات حركة وتغير السعر</h1>
<p>متابعة التغير التاريخي لسعر الدولار مقابل الجنيه السوداني</p>
<hr/>

<table bordered striped>
  <caption>مؤشرات حركة السعر بالتاريخ والأسعار السابقة</caption>
  <tr>
    <th align="center">التغير</th>
    <th align="center">السعر حينها</th>
    <th align="center">التاريخ</th>
    <th align="center">الفترة</th>
  </tr>
  <tr>
    <td align="center">${p4H.changeStr}</td>
    <td align="center">${p4H.oldPriceStr}</td>
    <td align="center">${p4H.dateTag}</td>
    <td align="center"><b>4 ساعات</b></td>
  </tr>
  <tr>
    <td align="center">${p1D.changeStr}</td>
    <td align="center">${p1D.oldPriceStr}</td>
    <td align="center">${p1D.dateTag}</td>
    <td align="center"><b>24 ساعة</b></td>
  </tr>
  <tr>
    <td align="center">${p7D.changeStr}</td>
    <td align="center">${p7D.oldPriceStr}</td>
    <td align="center">${p7D.dateTag}</td>
    <td align="center"><b>7 أيام</b></td>
  </tr>
  <tr>
    <td align="center">${p30D.changeStr}</td>
    <td align="center">${p30D.oldPriceStr}</td>
    <td align="center">${p30D.dateTag}</td>
    <td align="center"><b>30 يوماً</b></td>
  </tr>
  <tr>
    <td align="center">${p1Y.changeStr}</td>
    <td align="center">${p1Y.oldPriceStr}</td>
    <td align="center">${p1Y.dateTag}</td>
    <td align="center"><b>سنة</b></td>
  </tr>
</table>`;
}

function renderCurrenciesPage() {
  const currenciesInfo = [
    ["🇸🇦", "الريال السعودي", "SAR"],
    ["🇦🇪", "الدرهم الإماراتي", "AED"],
    ["🇶🇦", "الريال القطري", "QAR"],
    ["🇰🇼", "الدينار الكويتي", "KWD"],
    ["🇴🇲", "الريال العماني", "OMR"],
    ["🇧🇭", "الدينار البحريني", "BHD"],
    ["🇪🇬", "الجنيه المصري", "EGP"],
    ["🇪🇺", "اليورو", "EUR"],
    ["🇬🇧", "الجنيه الإسترليني", "GBP"],
    ["🇹🇷", "الليرة التركية", "TRY"],
  ];

  const rows = currenciesInfo.map(([flag, name, code]) => {
    const rate = getCurrencySdgRate(code);
    const rateCell = rate > 0
      ? `<code>\u200E${formatNumber(rate, rate < 1000 ? 1 : 0)} SDG</code>`
      : `<code>غير متوفر</code>`;
    return `  <tr>
    <td align="center">${rateCell}</td>
    <td align="center">${flag} <b>${name}</b> (${code})</td>
  </tr>`;
  });

  return `<h1>🌍 أسعار العملات مقابل الجنيه السوداني</h1>
<p>أسعار العملات في السوق الموازي</p>
<hr/>

<table bordered striped>
  <caption>قائمة العملات (P2P)</caption>
  <tr>
    <th align="center">السعر بالسوداني</th>
    <th align="center">العملة</th>
  </tr>
${rows.join("\n")}
</table>`;
}

function renderHelpPage() {
  return `<h1>📖 دليل الاستخدام</h1>
<p>يمكنك استخدام البوت للتحويل اللحظي ومتابعة الأسعار بأسهل الطرق:</p>
<hr/>

<p><b>1. التحويل المباشر للجنيه السوداني</b></p>
<p>أرسل المبلغ متبوعاً بالعملة مباشرة لحساب المعادل بالسوداني:</p>
<p>• <code>50 ريال</code> أو <code>50 SAR</code></p>
<p>• <code>100 دولار</code> أو <code>100 USDT</code></p>
<p>• <code>500 مصري</code> أو <code>500 EGP</code></p>
<p>• <code>100 درهم</code> أو <code>100 AED</code></p>
<p>• <code>20 يورو</code> أو <code>20 EUR</code></p>
<p>• <code>15 استرليني</code> أو <code>15 GBP</code></p>

<p><b>2. التحويل بين عملتين مختلفتين</b></p>
<p>استخدم كلمة <code>to</code> للتحويل المباشر بين أي عملتين:</p>
<p>• <code>USDT to SAR</code> (لعرض سعر الصرف المباشر)</p>
<p>• <code>50 SAR to SDG</code></p>
<p>• <code>30 USDT to EGP</code></p>

<p><b>3. الاستدعاء المباشر في أي محادثة (وضع الضيف)</b></p>
<p>• اكتب <code>@P2P_Live_robot</code> فقط لعرض الأسعار ومشاركتها.</p>
<p>• أو اكتب <code>@P2P_Live_robot 50 ريال</code> لإجراء التحويل الفوري في أي شات.</p>`;
}

function renderConversion(parsed) {
  const { amount: amt, from: cFrom, to: cTo } = parsed;
  const rateFromToSdg = getCurrencySdgRate(cFrom);
  const rateToToSdg = getCurrencySdgRate(cTo);

  if (rateFromToSdg <= 0 || rateToToSdg <= 0) {
    return "<b>عذراً، لم تتوفر بيانات كافية لحساب هذه العملة حالياً.</b>";
  }

  const unitExchange = rateFromToSdg / rateToToSdg;
  const totalResult = amt * unitExchange;
  const totalSdg = amt * rateFromToSdg;

  const amtStr = formatNumber(amt, amt !== Math.floor(amt) ? 2 : 0);
  const decTotal = (totalResult < 100 || totalResult !== Math.floor(totalResult)) ? 2 : 0;
  const totalStr = formatNumber(totalResult, decTotal);
  const unitStr = formatNumber(unitExchange, unitExchange < 10 ? 4 : 2);

  const rows = [
    `<tr><td align="center"><code>\u200E1 ${cFrom} = ${unitStr} ${cTo}</code></td><td align="center">سعر الصرف المباشر</td></tr>`
  ];

  if (cFrom !== "SDG" && cTo !== "SDG") {
    const totalSdgStr = formatNumber(totalSdg, 0);
    const sdgFromStr = formatNumber(rateFromToSdg, rateFromToSdg >= 1000 ? 0 : 1);
    const sdgToStr = formatNumber(rateToToSdg, rateToToSdg >= 1000 ? 0 : 1);

    rows.push(`<tr><td align="center"><code>\u200E${totalSdgStr} SDG</code></td><td align="center">المعادل بالسوداني (${amtStr} ${cFrom})</td></tr>`);
    rows.push(`<tr><td align="center"><code>\u200E1 ${cFrom} = ${sdgFromStr} SDG</code></td><td align="center">سعر صرف ${cFrom}</td></tr>`);
    rows.push(`<tr><td align="center"><code>\u200E1 ${cTo} = ${sdgToStr} SDG</code></td><td align="center">سعر صرف ${cTo}</td></tr>`);
  } else if (cFrom !== "USDT" && cTo !== "USDT") {
    rows.push(`<tr><td align="center"><code>\u200E1 USDT = ${formatNumber(memoryCache.sdg_data.avg, 0)} SDG</code></td><td align="center">سعر دولار بايننس</td></tr>`);
    const fCode = cTo === "SDG" ? cFrom : cTo;
    const fRate = memoryCache.fiat_rates[fCode];
    if (fRate > 0) {
      rows.push(`<tr><td align="center"><code>\u200E1 USDT = ${formatNumber(fRate, 3)} ${fCode}</code></td><td align="center">سعر USDT مقابل ${fCode}</td></tr>`);
    }
  }

  return `<tg-math-block>${amtStr} \\text{ ${cFrom}} = ${totalStr} \\text{ ${cTo}}</tg-math-block>
<hr/>

<table bordered striped>
  <caption>تفاصيل أسعار الصرف</caption>
  <tr>
    <th align="center">القيمة المقابلة</th>
    <th align="center">البيان</th>
  </tr>
${rows.join("\n")}
</table>`;
}

function parseInput(text) {
  if (!text) return null;
  let t = text.trim();
  t = t.replace(/@P2P_Live_robot/gi, "").trim();
  t = t.replace(/(\d+),(\d+)/g, "$1.$2");

  const mTo = t.match(/^(?:(\d*\.?\d+)\s*)?([a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669$€£﷼₺]+)\s+to\s+([a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669$€£﷼₺]+)$/i);
  if (mTo) {
    const amt = mTo[1] ? parseFloat(mTo[1]) : 1.0;
    const c1 = CURRENCY_MAP[mTo[2].toLowerCase()];
    const c2 = CURRENCY_MAP[mTo[3].toLowerCase()];
    if (c1 && c2 && c1 !== c2) {
      return { type: "convert_pair", amount: amt, from: c1, to: c2 };
    }
  }

  const mD1 = t.match(/^(\d*\.?\d+)\s*([a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669$€£﷼₺]+)$/i);
  if (mD1) {
    const amt = parseFloat(mD1[1]);
    const c = CURRENCY_MAP[mD1[2].toLowerCase()];
    if (c) {
      return { type: "direct", amount: amt, from: c, to: c === "SDG" ? "USDT" : "SDG" };
    }
  }

  const mD2 = t.match(/^([a-zA-Z]{3,4}|[\u0621-\u064A\u0660-\u0669$€£﷼₺]+)\s*(\d*\.?\d+)$/i);
  if (mD2) {
    const amt = parseFloat(mD2[2]);
    const c = CURRENCY_MAP[mD2[1].toLowerCase()];
    if (c) {
      return { type: "direct", amount: amt, from: c, to: c === "SDG" ? "USDT" : "SDG" };
    }
  }

  return null;
}

async function callTelegram(method, payload) {
  try {
    const res = await fetch(`${BASE_TG_URL}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!data.ok) {
      console.error(`Telegram API Error [${method}]:`, JSON.stringify(data));
    }
    return data;
  } catch (err) {
    console.error(`Network error calling Telegram [${method}]:`, err);
    return null;
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Live diagnostics endpoint for testing in browser: /debug or /status
    if (url.pathname === "/debug" || url.pathname === "/status") {
      await loadState(env);

      const isSynced = !!(memoryCache.sdg_data && memoryCache.sdg_data.avg > 0);
      const kv = getKV(env);

      return new Response(JSON.stringify({
        status: isSynced ? "synced" : "waiting_for_sync",
        is_synced: isSynced,
        kv_bound: !!kv,
        lastUpdate: memoryCache.lastUpdate > 0 ? new Date(memoryCache.lastUpdate).toISOString() : "لم يتم التحديث بعد (0)",
        sdg_data: memoryCache.sdg_data || "غير متوفر (لم تتم المزامنة بعد)",
        alsoug_usd: memoryCache.alsoug_usd > 0 ? memoryCache.alsoug_usd : "غير متوفر",
        fiat_count: Object.keys(memoryCache.fiat_rates || {}).length,
        historyCount: memoryCache.history.length,
        note: isSynced 
          ? "البيانات حقيقية ومحدثة من Binance P2P بنجاح." 
          : "لا توجد أسعار افتراضية إطلاقاً. يرجى تشغيل sync_bridge.py لتحديث الأسعار الحقيقية من بايننس."
      }, null, 2), {
        headers: { "Content-Type": "application/json; charset=utf-8" }
      });
    }

    // Secure real-time sync endpoint for external bridge (e.g. GitHub Actions / Python runner)
    if (url.pathname === "/api/sync") {
      const secret = url.searchParams.get("secret") || request.headers.get("x-sync-secret");
      const EXPECTED_SECRET = env?.SYNC_SECRET || "p2p_sdg_bridge_secure_key_2026";
      if (secret !== EXPECTED_SECRET) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
      }

      if (request.method !== "POST") {
        return new Response(JSON.stringify({ error: "Method not allowed" }), { status: 405 });
      }

      try {
        const payload = await request.json();
        if (payload.sdg_data && payload.sdg_data.avg > 0) {
          memoryCache.sdg_data = payload.sdg_data;
          if (payload.alsoug_usd) memoryCache.alsoug_usd = payload.alsoug_usd;
          if (payload.fiat_rates) memoryCache.fiat_rates = payload.fiat_rates;
          memoryCache.lastUpdate = Date.now();
          memoryCache.lastFiatUpdate = Date.now();

          await recordSnapshot(env, memoryCache.sdg_data.avg, memoryCache.alsoug_usd);
          await saveState(env);

          return new Response(JSON.stringify({
            status: "ok",
            message: "Rates synced successfully into PRICES_KV",
            avg: memoryCache.sdg_data.avg,
            buy_avg: memoryCache.sdg_data.buy_avg,
            sell_avg: memoryCache.sdg_data.sell_avg,
            traders_count: memoryCache.sdg_data.traders_count,
            time: new Date(memoryCache.lastUpdate).toISOString()
          }, null, 2), { headers: { "Content-Type": "application/json" } });
        }
        return new Response(JSON.stringify({ error: "Invalid payload format" }), { status: 400 });
      } catch(e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 500 });
      }
    }

    if (request.method === "GET") {
      return new Response("P2P Live Telegram Bot Worker Active!", { status: 200 });
    }

    if (request.method === "POST") {
      try {
        const update = await request.json();
        ctx.waitUntil(handleUpdate(update, env));
        return new Response("OK", { status: 200 });
      } catch (err) {
        console.error("Worker error:", err);
        return new Response("Error", { status: 500 });
      }
    }

    return new Response("Method not allowed", { status: 405 });
  },

  // Cloudflare native Cron Trigger (heartbeat refresh every minute)
  async scheduled(event, env, ctx) {
    ctx.waitUntil(refreshRates(true, env));
  }
};

async function handleGuestMessage(gm) {
  const guestQueryId = gm.guest_query_id;
  if (!guestQueryId) return;

  const rawText = (gm.text || "").trim();
  const cleanText = rawText.replace(/@P2P_Live_robot/gi, "").trim();

  let html = "";
  let markup = MAIN_KEYBOARD;

  if (!cleanText || ["/start", "/price", "/سعر"].includes(cleanText.toLowerCase())) {
    html = renderMainPage();
    markup = MAIN_KEYBOARD;
  } else {
    const parsed = parseInput(cleanText);
    if (parsed) {
      html = renderConversion(parsed);
      markup = null;
    } else {
      html = renderMainPage();
      markup = MAIN_KEYBOARD;
    }
  }

  const resultObj = {
    type: "article",
    id: `guest_${Date.now()}`,
    title: "USDT P2P Live",
    input_message_content: {
      rich_message: {
        html: html,
        is_rtl: true
      }
    }
  };
  if (markup) {
    resultObj.reply_markup = markup;
  }

  const payload = {
    guest_query_id: guestQueryId,
    result: resultObj
  };

  await callTelegram("answerGuestQuery", payload);
}

async function handleUpdate(update, env) {
  await refreshRates(false, env);

  if (update.guest_message) {
    await handleGuestMessage(update.guest_message);
    return;
  }

  if (update.callback_query) {
    const cq = update.callback_query;
    const data = cq.data;
    const inlineMsgId = cq.inline_message_id;
    const msg = cq.message;
    const chatId = msg?.chat?.id;
    const chatType = msg?.chat?.type;
    const msgId = msg?.message_id;

    if (!inlineMsgId && chatType !== "private" && chatId && chatId !== ALLOWED_GROUP_ID) {
      await callTelegram("answerCallbackQuery", { callback_query_id: cq.id });
      return;
    }

    await callTelegram("answerCallbackQuery", { callback_query_id: cq.id });

    let html = "";
    let markup = MAIN_KEYBOARD;
    if (data === "cb:currencies") {
      html = renderCurrenciesPage();
      markup = BACK_KEYBOARD;
    } else if (data === "cb:help") {
      html = renderHelpPage();
      markup = BACK_KEYBOARD;
    } else if (data === "cb:history") {
      html = renderHistoryPage();
      markup = BACK_KEYBOARD;
    } else if (data === "cb:main") {
      html = renderMainPage();
      markup = MAIN_KEYBOARD;
    }

    if (html) {
      const payload = {
        rich_message: {
          html: html,
          is_rtl: true
        },
        reply_markup: markup
      };
      if (inlineMsgId) {
        payload.inline_message_id = inlineMsgId;
      } else {
        payload.chat_id = chatId;
        payload.message_id = msgId;
      }
      await callTelegram("editMessageText", payload);
    }
    return;
  }

  if (update.inline_query) {
    const iq = update.inline_query;
    const q = (iq.query || "").trim();
    const results = [];

    if (q) {
      const parsed = parseInput(q);
      if (parsed) {
        results.push({
          type: "article",
          id: "conv_1",
          title: `🧮 تحويل: ${q}`,
          description: "حساب القيمة اللحظية الفورية",
          input_message_content: {
            rich_message: {
              html: renderConversion(parsed),
              is_rtl: true
            }
          }
        });
      }
    }

    results.push({
      type: "article",
      id: "main_p2p",
      title: "💵 USDT — P2P — أسعار الصرف بالسودان",
      description: (memoryCache.sdg_data && memoryCache.sdg_data.avg > 0)
        ? `السعر العام: ${formatNumber(memoryCache.sdg_data.avg, 0)} SDG`
        : "السعر العام: غير متوفر حالياً",
      input_message_content: {
        rich_message: {
          html: renderMainPage(),
          is_rtl: true
        }
      },
      reply_markup: MAIN_KEYBOARD
    });

    await callTelegram("answerInlineQuery", {
      inline_query_id: iq.id,
      results: results,
      cache_time: 10,
      is_personal: true
    });
    return;
  }

  if (update.message) {
    const msg = update.message;
    const chatId = msg.chat?.id;
    const chatType = msg.chat?.type;
    const text = (msg.text || "").trim();
    const msgId = msg.message_id;

    if (chatType !== "private" && chatId !== ALLOWED_GROUP_ID) {
      return;
    }

    if (!text) return;

    const cleanText = text.replace(/@P2P_Live_robot/gi, "").trim();

    if (!cleanText || ["/start", "/price", "/سعر", "أسعار", "اسعار", "سعر"].includes(cleanText.toLowerCase())) {
      await callTelegram("sendRichMessage", {
        chat_id: chatId,
        rich_message: {
          html: renderMainPage(),
          is_rtl: true
        },
        reply_markup: MAIN_KEYBOARD,
        reply_to_message_id: msgId
      });
      return;
    }

    let toParse = cleanText;
    if (toParse.startsWith("/calc ")) toParse = toParse.slice(6).trim();
    if (toParse.startsWith("/تحويل ")) toParse = toParse.slice(7).trim();

    const parsed = parseInput(toParse);
    if (parsed) {
      await callTelegram("sendRichMessage", {
        chat_id: chatId,
        rich_message: {
          html: renderConversion(parsed),
          is_rtl: true
        },
        reply_to_message_id: msgId
      });
    }
  }
}
