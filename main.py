import os, time, gzip, json, datetime, logging, requests
from flask import Flask

# ================== CONFIG ==================
EDITOR_BOT_TOKEN = "8993922841:AAFKjjZqiWHe8AEY1t4f86d1h7BcZXT5rIM"  # <-- এখানে বট টোকেন দিন
ADMIN_CHAT_ID = "2035024902"                # <-- আপনার ইউজার আইডি
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def home():
    return "Backup Editor Bot Running!"

sessions = {}

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    url = f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup: payload["reply_markup"] = reply_markup
    if parse_mode: payload["parse_mode"] = parse_mode
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

# ================== KEYBOARD (updated with new button) ==================
main_menu_kb = {
    "keyboard": [
        ["⚙️ কনফিগ", "💰 ব্যালেন্স"],
        ["🎮 গেম ব্যালেন্স", "👥 ইউজার তথ্য"],
        ["🎁 ফ্রি মাদার", "🛒 পেইড মাদার"],
        ["📤 সাবমিশন", "💸 উইথড্র"],
        ["📥 ডিপোজিট", "🏆 লিডারবোর্ড"],
        ["🔗 রেফারেল", "📜 ট্রানজেকশন"],
        ["🔄 সাবমিটেড ইউজারনেম", "📊 RPS উইনস"],
        ["📋 ইউজার ভার্সন"],
        ["📝 টেক্সট → .gz", "📄 .gz → টেক্সট"],
        ["✅ /done"]
    ],
    "resize_keyboard": True
}

def show_main_menu(chat_id):
    send_message(chat_id, "🔧 ব্যাকআপ এডিটর - প্রধান মেনু\n\nব্যাকআপ ফাইল পাঠান অথবা নিচের বাটন ব্যবহার করুন।",
                 reply_markup=main_menu_kb)

# ================== SECTION HELPERS (unchanged) ==================
def list_items(chat_id, title, items, limit=30, formatter=None):
    if not items:
        send_message(chat_id, f"{title} খালি।")
        return
    lines = [f"{title}:\n"]
    if isinstance(items, dict):
        for k, v in list(items.items())[:limit]:
            lines.append(formatter(k, v) if formatter else f"{k}: {v}")
    elif isinstance(items, list):
        for i, item in enumerate(items[:limit], 1):
            lines.append(formatter(i, item) if formatter else f"{i}. {item}")
    else:
        lines.append(str(items))
    send_message(chat_id, "\n".join(lines))

def handle_config(chat_id, data):
    config = data.get("config", {})
    list_items(chat_id, "⚙️ কনফিগ", config, formatter=lambda k, v: f"`{k}` = `{v}`")
    send_message(chat_id, "✏️ বদলাতে: /setconfig <key> <value>")

def handle_balances(chat_id, data):
    bal = data.get("user_balances", {})
    list_items(chat_id, "💰 ব্যালেন্স", bal, formatter=lambda k, v: f"{k}: {v} টাকা")
    send_message(chat_id, "✏️ সেট করতে: /setbalance <user_id> <amount>")

def handle_game_balances(chat_id, data):
    gb = data.get("game_balances", {})
    list_items(chat_id, "🎮 গেম ব্যালেন্স", gb, formatter=lambda k, v: f"{k}: {v} টাকা")
    send_message(chat_id, "✏️ সেট করতে: /setgamebalance <user_id> <amount>")

def handle_user_info(chat_id, data):
    info = data.get("user_info", {})
    list_items(chat_id, "👤 ইউজার তথ্য", info, formatter=lambda k, v: f"{k}: {v}")
    send_message(chat_id, "✏️ বদলাতে: /setuserinfo <user_id> <নাম>")

def handle_free_mothers(chat_id, data):
    mothers = data.get("mother_accounts", [])
    if not mothers:
        send_message(chat_id, "🎁 ফ্রি মাদার খালি।")
        return
    lines = ["🎁 ফ্রি মাদার:\n"]
    for i, m in enumerate(mothers[:20], 1):
        assigned = m.get("assigned_to", "না")
        lines.append(f"{i}. {m['username']} | {m['password']} | {m.get('fa_key','')} | বরাদ্দ: {assigned}")
    send_message(chat_id, "\n".join(lines))
    send_message(chat_id, "✏️ যোগ: /addfreemother <username> <password> [2fa]\n🗑️ মুছতে: /delfreemother <ইনডেক্স>")

def handle_paid_mothers(chat_id, data):
    stock = data.get("mother_stock", [])
    if not stock:
        send_message(chat_id, "🛒 পেইড মাদার স্টক খালি।")
        return
    lines = ["🛒 পেইড মাদার স্টক:\n"]
    for i, m in enumerate(stock[:20], 1):
        sold = "বিক্রি" if m.get("sold") else "আছে"
        lines.append(f"{i}. {m['username']} | {m['password']} | {m.get('fa_key','')} | {sold}")
    send_message(chat_id, "\n".join(lines))
    send_message(chat_id, "✏️ যোগ: /addpaidmother <username> <password> [2fa]\n🗑️ মুছতে: /delpaidmother <ইনডেক্স>")

def handle_submissions(chat_id, data):
    subs = data.get("submissions", [])
    list_items(chat_id, "📤 সাবমিশন", subs, limit=10,
               formatter=lambda i, s: f"{s['id']}: {s['username']} | {s['count']}pcs | {s['status']}")
    send_message(chat_id, "✏️ স্ট্যাটাস: /setsubstatus <sub_id> <approved/rejected/pending>")

def handle_withdraw_requests(chat_id, data):
    wd = data.get("withdraw_requests", [])
    list_items(chat_id, "💸 উইথড্র", wd, limit=10,
               formatter=lambda i, w: f"{w['id']}: {w['user_id']} | {w['amount']} টাকা | {w['status']}")
    send_message(chat_id, "✏️ স্ট্যাটাস: /setwdstatus <wd_id> <approved/rejected/pending>")

def handle_deposit_requests(chat_id, data):
    dep = data.get("deposit_requests", [])
    list_items(chat_id, "📥 ডিপোজিট", dep, limit=10,
               formatter=lambda i, d: f"{d['id']}: {d['user_id']} | {d['amount']} টাকা | {d['status']}")
    send_message(chat_id, "✏️ স্ট্যাটাস: /setdepstatus <dep_id> <approved/rejected/pending>")

def handle_leaderboard(chat_id, data):
    lb = data.get("leaderboard", {})
    if not lb:
        send_message(chat_id, "🏆 লিডারবোর্ড খালি।")
        return
    sorted_lb = sorted(lb.items(), key=lambda x: x[1].get("total_income", 0), reverse=True)[:20]
    list_items(chat_id, "🏆 লিডারবোর্ড", sorted_lb,
               formatter=lambda i, entry: f"{i}. {entry[0]}: {entry[1].get('total_income',0)} টাকা")
    send_message(chat_id, "✏️ ইনকাম সেট: /setleaderincome <user_id> <amount>")

def handle_referrals(chat_id, data):
    refs = data.get("referrals", {})
    list_items(chat_id, "🔗 রেফারেল", refs, formatter=lambda k, v: f"{k} -> {v}")
    send_message(chat_id, "✏️ যোগ: /setreferral <child_id> <parent_id>\n🗑️ মুছতে: /delreferral <child_id>")

def handle_transactions(chat_id, data):
    txns = data.get("transactions", [])
    list_items(chat_id, "📜 ট্রানজেকশন (শেষ ১০)", txns[-10:],
               formatter=lambda i, t: f"{t['id']}: {t['user_id']} | {t['description']} | {t['amount']} টাকা")

def handle_submitted_usernames(chat_id, data):
    us = data.get("submitted_usernames", [])
    send_message(chat_id, f"🔄 জমা ইউজারনেম: {len(us)} টি।\n🗑️ মুছতে: /clearsubmittednames")

def handle_rps_wins(chat_id, data):
    rps = data.get("rps_daily_wins", {})
    list_items(chat_id, "📊 RPS উইনস", rps, formatter=lambda k, v: f"{k}: {v.get('wins',0)} wins ({v.get('date','')})")

def handle_user_versions(chat_id, data):
    uv = data.get("user_versions", {})
    list_items(chat_id, "📋 ইউজার ভার্সন", uv, formatter=lambda k, v: f"{k}: {v}")

# ================== TEXT to .gz ==================
def handle_text_to_backup(chat_id, msg):
    if "reply_to_message" in msg and "text" in msg["reply_to_message"]:
        json_text = msg["reply_to_message"]["text"]
        try:
            new_data = json.loads(json_text)
            json_bytes = json.dumps(new_data, indent=2, ensure_ascii=False).encode('utf-8')
            compressed = gzip.compress(json_bytes, compresslevel=6)
            fname = f"converted_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}.json.gz"
            send_document(chat_id, compressed, fname, "✅ টেক্সট থেকে ব্যাকআপ তৈরি হয়েছে।")
        except Exception as e:
            send_message(chat_id, f"❌ JSON পার্স করতে সমস্যা: {e}")
    else:
        send_message(chat_id, "❗ প্রথমে একটি JSON টেক্সট মেসেজে রিপ্লাই দিয়ে /tobackup অথবা 📝 টেক্সট → .gz বাটন চাপুন।")

# ================== .gz to TEXT (NEW) ==================
def handle_gz_to_text(chat_id, msg):
    if "reply_to_message" in msg and "document" in msg["reply_to_message"]:
        file_id = msg["reply_to_message"]["document"]["file_id"]
        try:
            file_info = requests.get(f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/getFile?file_id={file_id}").json()
            if not file_info.get("ok"):
                send_message(chat_id, "❌ ফাইল ডাউনলোড ব্যর্থ।")
                return
            file_path = file_info["result"]["file_path"]
            content = requests.get(f"https://api.telegram.org/file/bot{EDITOR_BOT_TOKEN}/{file_path}").content
            decompressed = gzip.decompress(content)
            text = decompressed.decode('utf-8')
            # বড় ফাইলের জন্য ভাগ করে পাঠানো
            max_len = 4000
            for i in range(0, len(text), max_len):
                send_message(chat_id, text[i:i+max_len])
            send_message(chat_id, "✅ .gz → টেক্সট কনভার্ট সম্পন্ন।")
        except Exception as e:
            send_message(chat_id, f"❌ কনভার্ট করতে সমস্যা: {e}")
    else:
        send_message(chat_id, "❗ একটি .json.gz ফাইলে রিপ্লাই দিয়ে 📄 .gz → টেক্সট বাটন চাপুন বা /gztotext কমান্ড দিন।")

# ================== COMMAND PROCESSOR ==================
def process_message(chat_id, msg):
    if "document" in msg and "reply_to_message" not in msg:  # শুধু সরাসরি ফাইল (রিপ্লাই নয়)
        file_id = msg["document"]["file_id"]
        file_info = requests.get(f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/getFile?file_id={file_id}").json()
        if not file_info.get("ok"):
            send_message(chat_id, "❌ ফাইল ডাউনলোড ব্যর্থ।")
            return
        file_path = file_info["result"]["file_path"]
        content = requests.get(f"https://api.telegram.org/file/bot{EDITOR_BOT_TOKEN}/{file_path}").content
        try:
            decompressed = gzip.decompress(content)
            data = json.loads(decompressed.decode('utf-8'))
        except Exception as e:
            send_message(chat_id, f"❌ ফাইল পার্স করতে সমস্যা: {e}")
            return
        sessions[chat_id] = {"data": data}
        show_main_menu(chat_id)
        return

    if "text" not in msg:
        return

    text = msg["text"].strip()
    # নতুন ইউজার যারা শুধু কনভার্টার ব্যবহার করতে চায়
    if text in ["📝 টেক্সট → .gz", "/tobackup"]:
        handle_text_to_backup(chat_id, msg)
        return
    if text in ["📄 .gz → টেক্সট", "/gztotext"]:
        handle_gz_to_text(chat_id, msg)
        return

    if chat_id not in sessions:
        send_message(chat_id, "📥 প্রথমে একটি ব্যাকআপ ফাইল (.json.gz) পাঠান।")
        return

    session = sessions[chat_id]
    data = session.get("data", {})

    section_map = {
        "⚙️ কনফিগ": handle_config,
        "💰 ব্যালেন্স": handle_balances,
        "🎮 গেম ব্যালেন্স": handle_game_balances,
        "👥 ইউজার তথ্য": handle_user_info,
        "🎁 ফ্রি মাদার": handle_free_mothers,
        "🛒 পেইড মাদার": handle_paid_mothers,
        "📤 সাবমিশন": handle_submissions,
        "💸 উইথড্র": handle_withdraw_requests,
        "📥 ডিপোজিট": handle_deposit_requests,
        "🏆 লিডারবোর্ড": handle_leaderboard,
        "🔗 রেফারেল": handle_referrals,
        "📜 ট্রানজেকশন": handle_transactions,
        "🔄 সাবমিটেড ইউজারনেম": handle_submitted_usernames,
        "📊 RPS উইনস": handle_rps_wins,
        "📋 ইউজার ভার্সন": handle_user_versions,
    }
    if text in section_map:
        section_map[text](chat_id, data)
        return

    if text in ["✅ /done", "/done"]:
        try:
            json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
            compressed = gzip.compress(json_bytes, compresslevel=6)
            fname = f"edited_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}.json.gz"
            send_document(chat_id, compressed, fname, "✅ সম্পাদিত ব্যাকআপ প্রস্তুত।")
            sessions.pop(chat_id, None)
            send_message(chat_id, "🔁 সেশন শেষ। আবার শুরু করতে নতুন ফাইল পাঠান।")
        except Exception as e:
            send_message(chat_id, f"❌ জেনারেট করতে সমস্যা: {e}")
        return

    # Editing commands (unchanged)
    if text.startswith("/setconfig"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setconfig <key> <value>"); return
        key, val = parts[1], " ".join(parts[2:])
        try:
            if val.lower() == "true": val = True
            elif val.lower() == "false": val = False
            else:
                try: val = float(val); val = int(val) if val.is_integer() else val
                except: pass
            data["config"][key] = val
            send_message(chat_id, f"✅ কনফিগ '{key}' = {val}")
        except: send_message(chat_id, "❌ আপডেট ব্যর্থ।")
    elif text.startswith("/setbalance"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setbalance <user_id> <amount>"); return
        uid, amt = parts[1], float(parts[2])
        data.setdefault("user_balances", {})[uid] = amt
        send_message(chat_id, f"✅ ব্যালেন্স {uid} -> {amt}")
    elif text.startswith("/setgamebalance"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setgamebalance <user_id> <amount>"); return
        uid, amt = parts[1], float(parts[2])
        data.setdefault("game_balances", {})[uid] = amt
        send_message(chat_id, f"✅ গেম ব্যালেন্স {uid} -> {amt}")
    elif text.startswith("/setuserinfo"):
        parts = text.split(maxsplit=2)
        if len(parts) < 3: send_message(chat_id, "❌ /setuserinfo <user_id> <নাম>"); return
        uid, name = parts[1], parts[2]
        data.setdefault("user_info", {})[uid] = name
        send_message(chat_id, f"✅ ইউজার তথ্য {uid} -> {name}")
    elif text.startswith("/addfreemother"):
        parts = text.split(maxsplit=3)
        if len(parts) < 3: send_message(chat_id, "❌ /addfreemother <username> <password> [2fa]"); return
        uname, pwd, fa = parts[1], parts[2], parts[3] if len(parts) > 3 else ""
        data.setdefault("mother_accounts", []).append({
            "username": uname, "password": pwd, "fa_key": fa,
            "assigned_to": None, "assigned_at": None
        })
        send_message(chat_id, f"✅ ফ্রি মাদার যোগ: {uname}")
    elif text.startswith("/delfreemother"):
        parts = text.split()
        if len(parts) < 2: send_message(chat_id, "❌ /delfreemother <ইনডেক্স>"); return
        idx = int(parts[1]) - 1
        arr = data.get("mother_accounts", [])
        if 0 <= idx < len(arr):
            deleted = arr.pop(idx)
            send_message(chat_id, f"🗑️ মাদার {deleted['username']} মুছে ফেলা হয়েছে।")
        else: send_message(chat_id, "❌ ভুল ইনডেক্স।")
    elif text.startswith("/addpaidmother"):
        parts = text.split(maxsplit=3)
        if len(parts) < 3: send_message(chat_id, "❌ /addpaidmother <username> <password> [2fa]"); return
        uname, pwd, fa = parts[1], parts[2], parts[3] if len(parts) > 3 else ""
        data.setdefault("mother_stock", []).append({
            "username": uname, "password": pwd, "fa_key": fa, "sold": False
        })
        send_message(chat_id, f"✅ পেইড মাদার যোগ: {uname}")
    elif text.startswith("/delpaidmother"):
        parts = text.split()
        if len(parts) < 2: send_message(chat_id, "❌ /delpaidmother <ইনডেক্স>"); return
        idx = int(parts[1]) - 1
        arr = data.get("mother_stock", [])
        if 0 <= idx < len(arr):
            deleted = arr.pop(idx)
            send_message(chat_id, f"🗑️ পেইড মাদার {deleted['username']} মুছে ফেলা হয়েছে।")
        else: send_message(chat_id, "❌ ভুল ইনডেক্স।")
    elif text.startswith("/setsubstatus"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setsubstatus <sub_id> <status>"); return
        sub_id, status = parts[1], parts[2]
        for sub in data.get("submissions", []):
            if sub["id"] == sub_id:
                sub["status"] = status
                send_message(chat_id, f"✅ সাবমিশন {sub_id} -> {status}")
                return
        send_message(chat_id, "❌ খুঁজে পাওয়া যায়নি।")
    elif text.startswith("/setwdstatus"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setwdstatus <wd_id> <status>"); return
        w_id, status = parts[1], parts[2]
        for w in data.get("withdraw_requests", []):
            if w["id"] == w_id:
                w["status"] = status
                send_message(chat_id, f"✅ উইথড্র {w_id} -> {status}")
                return
        send_message(chat_id, "❌ খুঁজে পাওয়া যায়নি।")
    elif text.startswith("/setdepstatus"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setdepstatus <dep_id> <status>"); return
        dep_id, status = parts[1], parts[2]
        for d in data.get("deposit_requests", []):
            if d["id"] == dep_id:
                d["status"] = status
                send_message(chat_id, f"✅ ডিপোজিট {dep_id} -> {status}")
                return
        send_message(chat_id, "❌ খুঁজে পাওয়া যায়নি।")
    elif text.startswith("/setleaderincome"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setleaderincome <user_id> <amount>"); return
        uid, amt = parts[1], float(parts[2])
        lb = data.setdefault("leaderboard", {})
        if uid not in lb: lb[uid] = {"total_income": 0}
        lb[uid]["total_income"] = amt
        send_message(chat_id, f"✅ লিডারবোর্ড ইনকাম {uid} -> {amt}")
    elif text.startswith("/setreferral"):
        parts = text.split()
        if len(parts) < 3: send_message(chat_id, "❌ /setreferral <child_id> <parent_id>"); return
        child, parent = parts[1], parts[2]
        data.setdefault("referrals", {})[child] = parent
        send_message(chat_id, f"✅ রেফারেল {child} -> {parent}")
    elif text.startswith("/delreferral"):
        parts = text.split()
        if len(parts) < 2: send_message(chat_id, "❌ /delreferral <child_id>"); return
        child = parts[1]
        refs = data.get("referrals", {})
        if child in refs:
            del refs[child]
            send_message(chat_id, f"🗑️ রেফারেল {child} মুছে ফেলা হয়েছে।")
        else: send_message(chat_id, "❌ পাওয়া যায়নি।")
    elif text.startswith("/clearsubmittednames"):
        data["submitted_usernames"] = []
        send_message(chat_id, "✅ জমা ইউজারনেম সাফ করা হয়েছে।")

def telegram_polling():
    offset = None
    while True:
        try:
            params = {"timeout": 30, "offset": offset}
            resp = requests.get(
                f"https://api.telegram.org/bot{EDITOR_BOT_TOKEN}/getUpdates",
                params=params, timeout=35
            ).json()
            if resp.get("ok") and resp.get("result"):
                for upd in resp["result"]:
                    offset = upd["update_id"] + 1
                    if "message" in upd:
                        msg = upd["message"]
                        chat_id = str(msg["chat"]["id"])
                        if chat_id != ADMIN_CHAT_ID:
                            send_message(chat_id, "⛔ আপনি অ্যাডমিন নন।")
                            continue
                        process_message(chat_id, msg)
        except Exception as e:
            logger.exception("Polling error:")
        time.sleep(1)

if __name__ == "__main__":
    import threading
    threading.Thread(target=telegram_polling, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
