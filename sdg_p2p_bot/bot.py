import time
import json
import threading
import requests
import traceback
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from price_engine import PriceEngine
from parser import parse_input
from templates import (
    render_main_page,
    render_currencies_page,
    render_help_page,
    render_history_page,
    render_conversion
)

TOKEN = "9146323294:AAF4QgGnQRpv3SkL-ieMY1ZKxkXjS8plPK4"
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

ALLOWED_GROUP_ID = -1001382291757
ADMIN_USER_ID = 5561387511

engine = PriceEngine()

MAIN_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "عملات أخرى", "callback_data": "cb:currencies"},
            {"text": "كيفية الإستخدام", "callback_data": "cb:help"}
        ],
        [
            {"text": "📊 مؤشرات تغير السعر", "callback_data": "cb:history"}
        ]
    ]
}

BACK_KEYBOARD = {
    "inline_keyboard": [
        [
            {"text": "↩️ الرئيسية", "callback_data": "cb:main"}
        ]
    ]
}

session = requests.Session()

def tg_post(method, payload):
    try:
        r = session.post(f"{BASE_URL}/{method}", json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"Error calling {method}: {e}")
        return None

def send_rich_message(chat_id, html_content, reply_markup=None, reply_to_message_id=None):
    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "html": html_content,
            "is_rtl": True
        }
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    return tg_post("sendRichMessage", payload)

def edit_rich_message(html_content, reply_markup=None, chat_id=None, message_id=None, inline_message_id=None):
    payload = {
        "rich_message": {
            "html": html_content,
            "is_rtl": True
        }
    }
    if inline_message_id:
        payload["inline_message_id"] = inline_message_id
    else:
        payload["chat_id"] = chat_id
        payload["message_id"] = message_id
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_post("editMessageText", payload)

def answer_callback(callback_id):
    return tg_post("answerCallbackQuery", {"callback_query_id": callback_id})

def answer_inline(inline_query_id, results):
    payload = {
        "inline_query_id": inline_query_id,
        "results": results,
        "cache_time": 10,
        "is_personal": True
    }
    return tg_post("answerInlineQuery", payload)

def background_refresh_loop():
    while True:
        try:
            engine.refresh(force=True)
        except Exception as e:
            print(f"Error in background refresh: {e}")
        time.sleep(70)

def handle_guest_message(gm):
    guest_query_id = gm.get("guest_query_id")
    if not guest_query_id:
        return
        
    chat = gm.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    
    # Check permissions: allow any private chat, restrict groups to ALLOWED_GROUP_ID
    if chat_type != "private" and chat_id and chat_id != ALLOWED_GROUP_ID:
        return
        
    raw_text = gm.get("text", "").strip()
    import re
    clean_text = re.sub(r'@P2P_Live_robot', '', raw_text, flags=re.IGNORECASE).strip()
    
    if not clean_text or clean_text.lower() in ["/start", "/price", "/سعر"]:
        html = render_main_page(engine)
        markup = MAIN_KEYBOARD
    else:
        parsed = parse_input(clean_text)
        if parsed:
            html = render_conversion(parsed, engine)
            markup = None
        else:
            html = render_main_page(engine)
            markup = MAIN_KEYBOARD
            
    result_obj = {
        "type": "article",
        "id": f"guest_{int(time.time())}",
        "title": "USDT P2P Live",
        "input_message_content": {
            "rich_message": {
                "html": html,
                "is_rtl": True
            }
        }
    }
    if markup:
        result_obj["reply_markup"] = markup

    payload = {
        "guest_query_id": guest_query_id,
        "result": result_obj
    }
    res = tg_post("answerGuestQuery", payload)
    print(f"answerGuestQuery response: {res}")

def handle_callback_query(cq):
    cq_id = cq.get("id")
    data = cq.get("data")
    inline_msg_id = cq.get("inline_message_id")
    msg = cq.get("message")
    
    chat_id = msg.get("chat", {}).get("id") if msg else None
    message_id = msg.get("message_id") if msg else None

    # Check permissions
    chat_type = msg.get("chat", {}).get("type") if msg else None
    if chat_type != "private" and chat_id and chat_id != ALLOWED_GROUP_ID:
        answer_callback(cq_id)
        return

    answer_callback(cq_id)

    if data == "cb:currencies":
        html = render_currencies_page(engine)
        edit_rich_message(html, BACK_KEYBOARD, chat_id=chat_id, message_id=message_id, inline_message_id=inline_msg_id)
    elif data == "cb:help":
        html = render_help_page()
        edit_rich_message(html, BACK_KEYBOARD, chat_id=chat_id, message_id=message_id, inline_message_id=inline_msg_id)
    elif data == "cb:history":
        html = render_history_page(engine)
        edit_rich_message(html, BACK_KEYBOARD, chat_id=chat_id, message_id=message_id, inline_message_id=inline_msg_id)
    elif data == "cb:main":
        html = render_main_page(engine)
        edit_rich_message(html, MAIN_KEYBOARD, chat_id=chat_id, message_id=message_id, inline_message_id=inline_msg_id)

def handle_inline_query(iq):
    iq_id = iq.get("id")
    query = iq.get("query", "").strip()

    results = []

    if query:
        parsed = parse_input(query)
        if parsed:
            conv_html = render_conversion(parsed, engine)
            results.append({
                "type": "article",
                "id": "conv_1",
                "title": f"🧮 تحويل: {query}",
                "description": f"حساب القيمة اللحظية الفورية",
                "input_message_content": {
                    "rich_message": {
                        "html": conv_html,
                        "is_rtl": True
                    }
                }
            })

    # Always include Main dashboard
    main_html = render_main_page(engine)
    results.append({
        "type": "article",
        "id": "main_p2p",
        "title": "💵 USDT — P2P — أسعار الصرف بالسودان",
        "description": f"المتوسط العام: {engine.sdg_data['avg']:,} SDG",
        "input_message_content": {
            "rich_message": {
                "html": main_html,
                "is_rtl": True
            }
        },
        "reply_markup": MAIN_KEYBOARD
    })

    answer_inline(iq_id, results)

def handle_message(msg):
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")
    from_user = msg.get("from", {})
    user_id = from_user.get("id")
    msg_id = msg.get("message_id")
    text = msg.get("text", "").strip()

    # Access control: allow anyone in private chat, restrict groups to ALLOWED_GROUP_ID
    if chat_type != "private" and chat_id != ALLOWED_GROUP_ID:
        return

    if not text:
        return

    import re
    clean_text = re.sub(r'@P2P_Live_robot', '', text, flags=re.IGNORECASE).strip()

    if not clean_text or clean_text.lower() in ["/start", "/price", "/سعر", "أسعار", "اسعار", "سعر"]:
        send_rich_message(chat_id, render_main_page(engine), reply_markup=MAIN_KEYBOARD, reply_to_message_id=msg_id)
        return

    to_parse = clean_text
    if to_parse.lower().startswith("/calc "):
        to_parse = to_parse[6:].strip()
    elif to_parse.lower().startswith("/تحويل "):
        to_parse = to_parse[7:].strip()

    # Natural Language / Currency Check
    parsed = parse_input(to_parse)
    if parsed:
        send_rich_message(chat_id, render_conversion(parsed, engine), reply_to_message_id=msg_id)
        return

def main():
    print("=" * 50)
    print("Starting P2P Live Telegram Bot (Rich Message Edition)...")
    print(f"Allowed Group ID: {ALLOWED_GROUP_ID}")
    print(f"Admin User ID: {ADMIN_USER_ID}")
    print("=" * 50)

    engine.refresh(force=True)

    t = threading.Thread(target=background_refresh_loop, daemon=True)
    t.start()

    offset = 0
    tg_post("deleteWebhook", {"drop_pending_updates": False})

    while True:
        try:
            updates = tg_post("getUpdates", {"offset": offset, "timeout": 20})
            if updates and updates.get("ok"):
                for u in updates.get("result", []):
                    offset = u["update_id"] + 1

                    if "guest_message" in u:
                        handle_guest_message(u["guest_message"])
                    elif "callback_query" in u:
                        handle_callback_query(u["callback_query"])
                    elif "inline_query" in u:
                        handle_inline_query(u["inline_query"])
                    elif "message" in u:
                        handle_message(u["message"])
            else:
                time.sleep(1)
        except Exception as e:
            print(f"Polling error: {e}")
            traceback.print_exc()
            time.sleep(2)

if __name__ == "__main__":
    main()
