import requests, re, sys
sys.stdout.reconfigure(encoding='utf-8')

r = requests.get('https://core.telegram.org/bots/api', timeout=10)
text = r.text

def print_section(name):
    # Pattern to find h4 header
    pattern = r'<h4><a class="anchor" name="' + name.lower() + r'"[^>]*></a>' + name + r'</h4>(.*?)(?=<h4>)'
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if m:
        c = re.sub(r'<[^>]+>', ' ', m.group(1))
        c = re.sub(r'\s+', ' ', c).strip()
        print(f"=== {name} ===\n{c[:1500]}\n")
    else:
        print(f"=== {name} NOT FOUND ===")

for target in ['sendRichMessage', 'InputRichMessage', 'InputRichMessageContent']:
    print_section(target)
