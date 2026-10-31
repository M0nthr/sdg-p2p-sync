import requests
import json

TOKEN = '9146323294:AAF4QgGnQRpv3SkL-ieMY1ZKxkXjS8plPK4'
url = f'https://api.telegram.org/bot{TOKEN}/sendRichMessage'

# Test 1: table with dir='rtl' attribute
html_test1 = '''
<h1>تجربة 1: table مع dir=rtl</h1>
<table dir="rtl" bordered striped>
  <tr>
    <th align="right">المؤشر (يمين)</th>
    <th align="center">السعر (وسط)</th>
    <th align="left">النطاق (يسار)</th>
  </tr>
  <tr>
    <td align="right">💵 السعر العام</td>
    <td align="center">10,265</td>
    <td align="left">👥 52 تاجر</td>
  </tr>
</table>
'''

# Test 2: column order in HTML: [النطاق] ثم [السعر] ثم [المؤشر]
html_test2 = '''
<h1>تجربة 2: ترتيب الأعمدة معكوس برمجياً ليظهر المؤشر باليمين</h1>
<table bordered striped>
  <tr>
    <th align="left">النطاق</th>
    <th align="center">السعر (SDG)</th>
    <th align="right">المؤشر</th>
  </tr>
  <tr>
    <td align="left">👥 52 تاجر</td>
    <td align="center"><code>10,265</code></td>
    <td align="right">💵 <b>السعر العام</b></td>
  </tr>
  <tr>
    <td align="left">10,250 📉 | 10,298 📈</td>
    <td align="center"><code>10,284</code></td>
    <td align="right">🟢 <b>الشراء</b></td>
  </tr>
  <tr>
    <td align="left">10,221 📉 | 10,260 📈</td>
    <td align="center"><code>10,245</code></td>
    <td align="right">🔴 <b>البيع</b></td>
  </tr>
</table>
'''

for i, h in enumerate([html_test1, html_test2], 1):
    payload = {
        'chat_id': 5561387511,
        'rich_message': json.dumps({
            'html': h.strip(),
            'is_rtl': True
        }, ensure_ascii=False)
    }
    r = requests.post(url, json=payload)
    print(f'Test {i} status:', r.status_code, 'OK:', r.json().get('ok'))
