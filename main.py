import os
import time
import gzip
import json
import datetime
import logging
import requests

# ================== CONFIG ==================
EDITOR_BOT_TOKEN = "8993922841:AAFKjjZqiWHe8AEY1t4f86d1h7BcZXT5rIM"  # আলাদা বট টোকেন দিন
ADMIN_CHAT_ID = "2035024902"                # আপনার ইউজার আইডি

# ================== LOGGING ==================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================== GLOBALS ==================
edit_session = {}  # {chat_id: {"data": ...}}

# ================== TELEGRAM HELPERS ==================
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")

def send_document(chat_id, file_bytes, filename, caption=""):
    url = f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/sendDocument"
    try:
        files = {'document': (filename, file_bytes, 'application/gzip')}
        requests.post(url, data={"chat_id": chat_id, "caption": caption}, files=files, timeout=30)
    except Exception as e:
        logger.error(f"Document send error: {e}")

# ================== MAIN PROCESSOR ==================
def process_message(chat_id, msg):
    # ---- ফাইল (ব্যাকআপ) আপলোড ----
    if "document" in msg:
        file_id = msg["document"]["file_id"]
        file_info = requests.get(
            f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/getFile?file_id={file_id}"
        ).json()
        if not file_info.get("ok"):
            send_message(chat_id, "❌ ফাইল ডাউনলোড ব্যর্থ।")
            return
        file_path = file_info["result"]["file_path"]
        content = requests.get(
            f"https://api.telegram.org/file/bot{EDITOR_BOT_TOKEN}/{file_path}"
        ).content

        try:
            decompressed = gzip.decompress(content)
            data = json.loads(decompressed.decode('utf-8'))
        except Exception as e:
            send_message(chat_id, f"❌ ফাইল পার্স করতে সমস্যা: {e}")
            return

        edit_session[chat_id] = {"data": data}
        show_main_menu(chat_id)

    # ---- টেক্সট কমান্ড ----
    elif "text" in msg:
        text = msg["text"].strip()
        if chat_id not in edit_session and text != "/tobackup":
            send_message(chat_id, "📥 প্রথমে একটি ব্যাকআপ ফাইল (.json.gz) পাঠান।")
            return

        data = edit_session.get(chat_id, {}).get("data", {})

        if text.startswith("/setconfig"):
            parts = text.split()
            if len(parts) < 3:
                send_message(chat_id, "❌ ফরম্যাট: /setconfig <key> <value>\nউদা: /setconfig price_2fa 4.0")
                return
            key = parts[1]
            value = " ".join(parts[2:])
            try:
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                else:
                    try:
                        value = float(value)
                        if value.is_integer():
                            value = int(value)
                    except:
                        pass
                data["config"][key] = value
                send_message(chat_id, f"✅ কনফিগ '{key}' আপডেট হয়েছে: {value}")
            except Exception as e:
                send_message(chat_id, f"❌ আপডেট ব্যর্থ: {e}")

        elif text.startswith("/setbalance"):
            parts = text.split()
            if len(parts) < 3:
                send_message(chat_id, "❌ ফরম্যাট: /setbalance <user_id> <amount>")
                return
            user_id = parts[1]
            amount = float(parts[2])
            if "user_balances" not in data:
                data["user_balances"] = {}
            data["user_balances"][user_id] = amount
            send_message(chat_id, f"✅ ইউজার {user_id} ব্যালেন্স সেট হয়েছে: {amount}")

        elif text.startswith("/setgamebalance"):
            parts = text.split()
            if len(parts) < 3:
                send_message(chat_id, "❌ ফরম্যাট: /setgamebalance <user_id> <amount>")
                return
            user_id = parts[1]
            amount = float(parts[2])
            if "game_balances" not in data:
                data["game_balances"] = {}
            data["game_balances"][user_id] = amount
            send_message(chat_id, f"✅ গেম ব্যালেন্স আপডেট: {user_id} -> {amount}")

        elif text == "/listconfig":
            config = data.get("config", {})
            lines = ["📋 **বর্তমান কনফিগ:**\n"]
            for k, v in config.items():
                lines.append(f"`{k}` = `{v}`")
            send_message(chat_id, "\n".join(lines))

        elif text == "/listusers":
            users = data.get("user_balances", {})
            if not users:
                send_message(chat_id, "কোনো ইউজার ব্যালেন্স নেই।")
            else:
                lines = ["👥 **ইউজার ব্যালেন্স:**\n"]
                for uid, bal in users.items():
                    lines.append(f"{uid}: {bal} টাকা")
                send_message(chat_id, "\n".join(lines))

        elif text == "/done":
            try:
                json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
                compressed = gzip.compress(json_bytes, compresslevel=6)
                filename = f"edited_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz"
                send_document(chat_id, compressed, filename, caption="✅ এডিটেড ব্যাকআপ প্রস্তুত।")
                del edit_session[chat_id]
                send_message(chat_id, "🔁 সেশন শেষ। নতুন ফাইল পাঠালে আবার শুরু হবে।")
            except Exception as e:
                send_message(chat_id, f"❌ জেনারেট করতে সমস্যা: {e}")

        # ===== নতুন ফিচার: টেক্সট থেকে .json.gz কনভার্ট =====
        elif text == "/tobackup":
            if "reply_to_message" in msg and "text" in msg["reply_to_message"]:
                json_text = msg["reply_to_message"]["text"]
                try:
                    data = json.loads(json_text)
                    json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
                    compressed = gzip.compress(json_bytes, compresslevel=6)
                    filename = f"converted_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz"
                    send_document(chat_id, compressed, filename, caption="✅ টেক্সট থেকে ব্যাকআপ তৈরি হয়েছে।")
                except json.JSONDecodeError as e:
                    send_message(chat_id, f"❌ JSON পার্স করতে সমস্যা: {e}")
                except Exception as e:
                    send_message(chat_id, f"❌ কনভার্ট করতে সমস্যা: {e}")
            else:
                send_message(chat_id, "❗ দয়া করে একটি JSON টেক্সট মেসেজে রিপ্লাই দিয়ে /tobackup কমান্ড দিন।")

        else:
            help_text = (
                "📋 **উপলব্ধ কমান্ড:**\n"
                "/setconfig key value - কনফিগ বদলান\n"
                "/setbalance user_id amount - ইউজার ব্যালেন্স সেট\n"
                "/setgamebalance user_id amount - গেম ব্যালেন্স সেট\n"
                "/listconfig - কনফিগ দেখুন\n"
                "/listusers - ইউজার ব্যালেন্স দেখুন\n"
                "/tobackup - রিপ্লাই করা JSON টেক্সট থেকে .json.gz তৈরি\n"
                "/done - নতুন ব্যাকআপ ফাইল ডাউনলোড করুন"
            )
            send_message(chat_id, help_text)

def show_main_menu(chat_id):
    menu = {
        "keyboard": [
            ["/listconfig", "/listusers"],
            ["/tobackup", "/done"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "🔧 ব্যাকআপ এডিটর রেডি। নিচের মেনু ব্যবহার করুন।", reply_markup=menu)

# ================== POLLING ==================
def main():
    offset = None
    while True:
        try:
            params = {"timeout": 30, "offset": offset}
            resp = requests.get(
                f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/getUpdates",
                params=params, timeout=35
            ).json()
            if resp.get("ok") and resp.get("result"):
                for update in resp["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        msg = update["message"]
                        chat_id = str(msg["chat"]["id"])
                        if chat_id != ADMIN_CHAT_ID:
                            send_message(chat_id, "⛔ আপনি অ্যাডমিন নন।")
                            continue
                        process_message(chat_id, msg)
        except Exception as e:
            logger.exception("Polling error:")
        time.sleep(1)

if __name__ == "__main__":
    main()
