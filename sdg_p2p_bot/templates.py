import time
from datetime import datetime, timezone, timedelta

def format_number(val, decimals=2):
    if val is None:
        return "0"
    if decimals == 0 or val == int(val):
        return f"{int(val):,}"
    return f"{val:,.{decimals}f}"

def format_sudan_datetime(unix_sec):
    months = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
    ]
    sudan_tz = timezone(timedelta(hours=2))
    dt = datetime.fromtimestamp(unix_sec, tz=sudan_tz)
    month = months[dt.month - 1]
    hour = dt.hour
    period = "م" if hour >= 12 else "ص"
    hour12 = hour % 12 or 12
    return f"{dt.day} {month} {dt.year} — {hour12:02d}:{dt.minute:02d} {period}"

def render_main_page(engine):
    sdg = engine.sdg_data
    alsoug = engine.alsoug_usd
    now_unix = int(time.time())
    sudan_time_str = format_sudan_datetime(now_unix)
    
    avg_str = format_number(sdg['avg'], 0)
    buy_avg_str = format_number(sdg['buy_avg'], 0)
    buy_max_str = format_number(sdg['buy_max'], 0)
    buy_min_str = format_number(sdg['buy_min'], 0)
    
    sell_avg_str = format_number(sdg['sell_avg'], 0)
    sell_max_str = format_number(sdg['sell_max'], 0)
    sell_min_str = format_number(sdg['sell_min'], 0)
    
    alsoug_str = format_number(alsoug, 0)
    
    tc = sdg.get('traders_count', 14)
    traders_str = f"👥 {tc} تجار" if 3 <= tc <= 10 else f"👥 {tc} تاجر"
    
    html = f'''
<h1>🌍 أسعار الصرف مقابل الجنيه السوداني</h1>
<p>🕒 <tg-time unix="{now_unix}" format="wDT">{sudan_time_str}</tg-time></p>
<hr/>

<table bordered striped>
  <caption>منصة بايننس (Binance P2P)</caption>
  <tr>
    <th align="center">النطاق</th>
    <th align="center">السعر (SDG)</th>
    <th align="center">المؤشر</th>
  </tr>
  <tr>
    <td align="center">{traders_str}</td>
    <td align="center"><code>{avg_str}</code></td>
    <td align="center">💵 <b>السعر العام</b></td>
  </tr>
  <tr>
    <td align="center">{buy_min_str} 📉 | {buy_max_str} 📈</td>
    <td align="center"><code>{buy_avg_str}</code></td>
    <td align="center">🟢 <b>الشراء</b></td>
  </tr>
  <tr>
    <td align="center">{sell_min_str} 📉 | {sell_max_str} 📈</td>
    <td align="center"><code>{sell_avg_str}</code></td>
    <td align="center">🔴 <b>البيع</b></td>
  </tr>
</table>

<table bordered>
  <caption>تطبيق السوق (Alsoug)</caption>
  <tr>
    <td align="center"><code>\u200E{alsoug_str} SDG</code></td>
    <td align="center">🏪 <b>السوق الموازي</b></td>
  </tr>
</table>
'''
    return html.strip()

def render_currencies_page(engine):
    currencies_info = [
        ("🇸🇦", "الريال السعودي", "SAR"),
        ("🇦🇪", "الدرهم الإماراتي", "AED"),
        ("🇶🇦", "الريال القطري", "QAR"),
        ("🇰🇼", "الدينار الكويتي", "KWD"),
        ("🇴🇲", "الريال العماني", "OMR"),
        ("🇧🇭", "الدينار البحريني", "BHD"),
        ("🇪🇬", "الجنيه المصري", "EGP"),
        ("🇪🇺", "اليورو", "EUR"),
        ("🇬🇧", "الجنيه الإسترليني", "GBP"),
        ("🇹🇷", "الليرة التركية", "TRY"),
    ]
    
    rows = []
    for flag, name, code in currencies_info:
        rate = engine.get_currency_sdg_rate(code)
        decimals = 1 if rate < 1000 else 0
        rate_str = format_number(rate, decimals)
        rows.append(f'''  <tr>
    <td align="center"><code>\u200E{rate_str} SDG</code></td>
    <td align="center">{flag} <b>{name}</b> ({code})</td>
  </tr>''')
        
    table_rows = "\n".join(rows)
    
    html = f'''
<h1>🌍 أسعار العملات مقابل الجنيه السوداني</h1>
<p>أسعار العملات في السوق الموازي</p>
<hr/>

<table bordered striped>
  <caption>قائمة العملات (P2P)</caption>
  <tr>
    <th align="center">السعر بالسوداني</th>
    <th align="center">العملة</th>
  </tr>
{table_rows}
</table>
'''
    return html.strip()

def render_help_page():
    html = '''
<h1>📖 دليل الاستخدام</h1>
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
<p>• أو اكتب <code>@P2P_Live_robot 50 ريال</code> لإجراء التحويل الفوري في أي شات.</p>
'''
    return html.strip()

def render_history_page(engine):
    p_4h = engine.get_historical_point(4 * 3600, "t", "قبل 4 س")
    p_1d = engine.get_historical_point(86400, "dM", "أمس")
    p_7d = engine.get_historical_point(7 * 86400, "dM", "قبل أسبوع")
    p_30d = engine.get_historical_point(30 * 86400, "dM", "قبل شهر")
    p_1y = engine.get_historical_point(365 * 86400, "yM", "قبل سنة")

    html = f'''
<h1>📊 مؤشرات حركة وتغير السعر</h1>
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
    <td align="center">{p_4h['change_str']}</td>
    <td align="center">{p_4h['old_price_str']}</td>
    <td align="center">{p_4h['date_tag']}</td>
    <td align="center"><b>4 ساعات</b></td>
  </tr>
  <tr>
    <td align="center">{p_1d['change_str']}</td>
    <td align="center">{p_1d['old_price_str']}</td>
    <td align="center">{p_1d['date_tag']}</td>
    <td align="center"><b>24 ساعة</b></td>
  </tr>
  <tr>
    <td align="center">{p_7d['change_str']}</td>
    <td align="center">{p_7d['old_price_str']}</td>
    <td align="center">{p_7d['date_tag']}</td>
    <td align="center"><b>7 أيام</b></td>
  </tr>
  <tr>
    <td align="center">{p_30d['change_str']}</td>
    <td align="center">{p_30d['old_price_str']}</td>
    <td align="center">{p_30d['date_tag']}</td>
    <td align="center"><b>30 يوماً</b></td>
  </tr>
  <tr>
    <td align="center">{p_1y['change_str']}</td>
    <td align="center">{p_1y['old_price_str']}</td>
    <td align="center">{p_1y['date_tag']}</td>
    <td align="center"><b>سنة</b></td>
  </tr>
</table>
'''
    return html.strip()

def render_conversion(parsed, engine):
    amt = parsed['amount']
    c_from = parsed['from'].upper()
    c_to = parsed['to'].upper()
    
    rate_from_to_sdg = engine.get_currency_sdg_rate(c_from)
    rate_to_to_sdg = engine.get_currency_sdg_rate(c_to)
    
    if rate_from_to_sdg <= 0 or rate_to_to_sdg <= 0:
        return "<b>عذراً، لم تتوفر بيانات كافية لحساب هذه العملة حالياً.</b>"
        
    unit_exchange = rate_from_to_sdg / rate_to_to_sdg
    total_result = amt * unit_exchange
    total_sdg = amt * rate_from_to_sdg
    
    amt_str = format_number(amt, 2 if amt != int(amt) else 0)
    dec_total = 2 if total_result < 100 or total_result != int(total_result) else 0
    total_str = format_number(total_result, dec_total)
    unit_str = format_number(unit_exchange, 4 if unit_exchange < 10 else 2)
    
    rows = [
        f'<tr><td align="center"><code>\u200E1 {c_from} = {unit_str} {c_to}</code></td><td align="center">سعر الصرف المباشر</td></tr>'
    ]
    
    if c_from != 'SDG' and c_to != 'SDG':
        total_sdg_str = format_number(total_sdg, 0)
        sdg_from_str = format_number(rate_from_to_sdg, 0 if rate_from_to_sdg >= 1000 else 1)
        sdg_to_str = format_number(rate_to_to_sdg, 0 if rate_to_to_sdg >= 1000 else 1)
        
        # Immediately add the SDG equivalent of the requested amount
        rows.append(f'<tr><td align="center"><code>\u200E{total_sdg_str} SDG</code></td><td align="center">المعادل بالسوداني ({amt_str} {c_from})</td></tr>')
        rows.append(f'<tr><td align="center"><code>\u200E1 {c_from} = {sdg_from_str} SDG</code></td><td align="center">سعر صرف {c_from}</td></tr>')
        rows.append(f'<tr><td align="center"><code>\u200E1 {c_to} = {sdg_to_str} SDG</code></td><td align="center">سعر صرف {c_to}</td></tr>')
    elif c_from != 'USDT' and c_to != 'USDT':
        usdt_sdg = format_number(engine.sdg_data['avg'], 0)
        rows.append(f'<tr><td align="center"><code>\u200E1 USDT = {usdt_sdg} SDG</code></td><td align="center">سعر دولار بايننس</td></tr>')
        target_code = c_from if c_to == 'SDG' else c_to
        fiat_usdt = engine.get_fiat_rate(target_code)
        if fiat_usdt > 0:
            fiat_u_str = format_number(fiat_usdt, 3)
            rows.append(f'<tr><td align="center"><code>\u200E1 USDT = {fiat_u_str} {target_code}</code></td><td align="center">سعر USDT مقابل {target_code}</td></tr>')

    details_table = "\n".join(rows)

    html = f'''
<tg-math-block>{amt_str} \\text{{ {c_from}}} = {total_str} \\text{{ {c_to}}}</tg-math-block>
<hr/>

<table bordered striped>
  <caption>تفاصيل أسعار الصرف</caption>
  <tr>
    <th align="center">القيمة المقابلة</th>
    <th align="center">البيان</th>
  </tr>
{details_table}
</table>
'''
    return html.strip()
