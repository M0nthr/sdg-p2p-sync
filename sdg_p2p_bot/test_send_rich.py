import requests
import sys
import time
import json

sys.stdout.reconfigure(encoding='utf-8')

TOKEN = '9146323294:AAF4QgGnQRpv3SkL-ieMY1ZKxkXjS8plPK4'
url = f'https://api.telegram.org/bot{TOKEN}/sendRichMessage'

now_unix = int(time.time())

html_clean = f'''
<h1>💵 أسعار الصرف | USDT — P2P</h1>
<p><tg-time unix="{now_unix}" format="wDT">الخميس، 29 أكتوبر 2026</tg-time></p>
<hr/>

<table bordered striped>
  <caption>منصة بايننس (Binance P2P)</caption>
  <tr>
    <th align="right">البيان</th>
    <th align="center">السعر (SDG)</th>
  </tr>
  <tr>
    <td align="right">💵 <b>المتوسط العام</b></td>
    <td align="center"><code>10,265</code></td>
  </tr>
  <tr>
    <td align="right">🟢 <b>متوسط الشراء</b></td>
    <td align="center"><code>10,284</code></td>
  </tr>
  <tr>
    <td align="right">📈 أعلى سعر شراء</td>
    <td align="center"><code>10,298</code></td>
  </tr>
  <tr>
    <td align="right">📉 أدنى سعر شراء</td>
    <td align="center"><code>10,250</code></td>
  </tr>
  <tr>
    <td align="right">🔴 <b>متوسط البيع</b></td>
    <td align="center"><code>10,245</code></td>
  </tr>
  <tr>
    <td align="right">📈 أعلى سعر بيع</td>
    <td align="center"><code>10,260</code></td>
  </tr>
  <tr>
    <td align="right">📉 أدنى سعر بيع</td>
    <td align="center"><code>10,221</code></td>
  </tr>
</table>

<table bordered>
  <caption>تطبيق السوق (Alsoug)</caption>
  <tr>
    <td align="right">🏪 <b>السعر الموازي</b></td>
    <td align="center"><code>10,310 SDG</code></td>
  </tr>
</table>

<footer>تحديث دوري كل 70 ثانية عبر تصفية العروض واستبعاد القيم الشاذة إحصائياً.</footer>
'''

payload = {
    'chat_id': 5561387511,
    'rich_message': json.dumps({
        'html': html_clean.strip(),
        'is_rtl': True
    }, ensure_ascii=False),
    'reply_markup': json.dumps({
        'inline_keyboard': [
            [{'text': 'عملات أخرى', 'callback_data': 'cb:currencies'}, {'text': 'كيفية الإستخدام', 'callback_data': 'cb:help'}]
        ]
    }, ensure_ascii=False)
}

r = requests.post(url, json=payload)
print('Status:', r.status_code, 'OK:', r.json().get('ok'))
