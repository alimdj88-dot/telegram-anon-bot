import telebot
from telebot import types
import json, os, random
from datetime import datetime
from flask import Flask
from threading import Thread

# --- بخش جدید برای زنده نگه داشتن سرور ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ---------------------------------------

TOKEN = "8213706320:AAEICB4U73ucmYi9SJwj52wTsq2sPz0N9Q0"
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
CHATS_FILE = "chats.json"

users = {}
links = {}
waiting = {"male": [], "female": [], "any": []}
anon_pending = {}
chats = []

# ---------- load ----------
if os.path.exists(USERS_FILE):
    try:
        users = json.load(open(USERS_FILE, "r", encoding="utf-8"))
    except: users = {}
if os.path.exists(CHATS_FILE):
    try:
        chats = json.load(open(CHATS_FILE, "r", encoding="utf-8"))
    except: chats = []

def save_users():
    json.dump(users, open(USERS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def save_chats():
    json.dump(chats, open(CHATS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- keyboards ----------
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔗 به یه ناشناس وصل کن", "🔗 ساخت لینک ناشناس")
    return kb

def gender_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("پسر 👦", "دختر 👧")
    return kb

def end_chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ پایان چت")
    return kb

def cancel_search_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⛔ لغو جستجو")
    return kb

# ---------- main menu ----------
def main_menu(cid):
    users[cid]["state"] = "main"
    bot.send_message(
        cid,
        f"✨ سلام {users[cid]['name']} خوش اومدی 😎",
        reply_markup=main_kb()
    )
    save_users()

# ---------- start ----------
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    args = message.text.split()

    if len(args) > 1:
        code = args[1]
        if code in links:
            owner = links[code]
            if owner == cid:
                bot.send_message(cid, "❌ نمی‌تونی به خودت پیام بدی")
                return
            users.setdefault(cid, {})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = owner
            bot.send_message(cid, "✏️ پیامت رو بنویس:")
            save_users()
            return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "name"}
        bot.send_message(cid, "👤 اسمت رو وارد کن:")
        save_users()
        return

    main_menu(cid)

# ---------- messages ----------
@bot.message_handler(func=lambda m: True)
def handle(message):
    cid = str(message.chat.id)
    text = message.text
    user = users.get(cid)
    if not user: return

    state = user.get("state")

    if state == "name":
        user["name"] = text.strip()
        user["state"] = "gender"
        bot.send_message(cid, f"✅ اسمت ثبت شد ({user['name']})\n🚻 جنسیتت چیه؟", reply_markup=gender_kb())
        save_users()
        return

    if state == "gender":
        if text not in ["پسر 👦", "دختر 👧"]: return
        user["gender"] = "male" if "پسر" in text else "female"
        user["state"] = "age"
        bot.send_message(cid, "🎂 سنت چنده؟ (13 تا 60)")
        save_users()
        return

    if state == "age":
        if not text.isdigit() or not 13 <= int(text) <= 60:
            bot.send_message(cid, "❌ سن معتبر نیست")
            return
        user["age"] = int(text)
        main_menu(cid)
        return

    if state == "main":
        if text == "🔗 ساخت لینک ناشناس":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code
            links[code] = cid
            bot.send_message(cid, f"🔗 لینک ناشناس تو:\nhttps://t.me/{BOT_USERNAME}?start={code}")
            save_users()
            return

        if text == "🔗 به یه ناشناس وصل کن":
            user["state"] = "choose_pref"
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("پسر 👦", callback_data="search_male"),
                types.InlineKeyboardButton("دختر 👧", callback_data="search_female"),
                types.InlineKeyboardButton("فرقی نداره 👫", callback_data="search_any"),
            )
            bot.send_message(cid, "🎯 جنسیت فرد ناشناس رو انتخاب کن:", reply_markup=kb)
            save_users()
            return

    if state == "chat":
        if text == "❌ پایان چت":
            partner = user.get("partner")
            if partner and partner in users:
                users[partner]["state"] = "main"
                users[partner].pop("partner", None)
                main_menu(partner)
            user.pop("partner", None)
            main_menu(cid)
            return

        partner = user.get("partner")
        if partner:
            bot.send_message(partner, text)
            chats.append({
                "from": cid, "to": partner, "text": text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            save_chats()
        return

    if state == "anon_write":
        anon_pending[cid] = text
        user["state"] = "anon_confirm"
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ ارسال", callback_data="anon_send"),
            types.InlineKeyboardButton("❌ لغو", callback_data="anon_cancel")
        )
        bot.send_message(cid, text, reply_markup=kb)
        return

# ---------- callbacks ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id)
    user = users.get(cid)
    if not user: return

    if call.data.startswith("search_"):
        pref = call.data.replace("search_", "")
        user["state"] = "searching"
        # منطق جستجو...
        waiting[pref].append(cid)
        bot.send_message(cid, "⏳ در حال جستجو...", reply_markup=cancel_search_kb())
        save_users()
        return

    if user["state"] == "anon_confirm":
        if call.data == "anon_send":
            target = user["anon_target"]
            msg = anon_pending.pop(cid)
            bot.send_message(target, f"📩 پیام ناشناس:\n{msg}")
            main_menu(cid)
        else:
            anon_pending.pop(cid, None)
            main_menu(cid)
        return

# --- اجرای نهایی ---
if __name__ == "__main__":
    keep_alive() # سرور کوچک را روشن کن
    print("Bot is starting...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
