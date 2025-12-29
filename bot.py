import telebot
from telebot import types
import json, os, random
from datetime import datetime
from flask import Flask
from threading import Thread

# --- تنظیمات سرور برای آنلاین ماندن ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------

TOKEN = "8213706320:AAEICB4U73ucmYi9SJwj52wTsq2sPz0N9Q0"
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
CHATS_FILE = "chats.json"

users = {}
links = {}
# لیست انتظار بر اساس جنسیت خود فرد (پسرها در male، دخترها در female)
waiting = {"male": [], "female": []}
anon_pending = {}
chats = []

# ---------- بارگذاری داده‌ها ----------
if os.path.exists(USERS_FILE):
    try:
        users = json.load(open(USERS_FILE, "r", encoding="utf-8"))
    except: users = {}

def save_users():
    json.dump(users, open(USERS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def save_chats():
    json.dump(chats, open(CHATS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---------- کیبوردها ----------
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

def main_menu(cid):
    users[cid]["state"] = "main"
    bot.send_message(cid, f"✨ سلام {users[cid]['name']} خوش اومدی 😎", reply_markup=main_kb())
    save_users()

# ---------- دستور Start ----------
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
            users.setdefault(cid, {"name": message.from_user.first_name})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = owner
            bot.send_message(cid, "✏️ پیامت رو بنویس تا به صورت ناشناس ارسال بشه:")
            save_users()
            return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "name"}
        bot.send_message(cid, "👤 اسمت رو وارد کن:")
        save_users()
        return

    main_menu(cid)

# ---------- مدیریت پیام‌ها ----------
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
            bot.send_message(cid, "❌ سن معتبر نیست (13-60)")
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
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("پسر 👦", callback_data="search_male"),
                types.InlineKeyboardButton("دختر 👧", callback_data="search_female"),
                types.InlineKeyboardButton("فرقی نداره 👫", callback_data="search_any"),
            )
            bot.send_message(cid, "🎯 دوست داری به کی وصل بشی؟", reply_markup=kb)
            return

    if state == "searching" and text == "⛔ لغو جستجو":
        for k in waiting:
            if cid in waiting[k]: waiting[k].remove(cid)
        main_menu(cid)
        return

    if state == "chat":
        if text == "❌ پایان چت":
            partner = user.get("partner")
            if partner and partner in users:
                users[partner]["partner"] = None
                main_menu(partner)
                bot.send_message(partner, "طرف مقابل چت رو تموم کرد ☹️")
            user["partner"] = None
            main_menu(cid)
            return

        partner = user.get("partner")
        if partner:
            bot.send_message(partner, text)

    if state == "anon_write":
        anon_pending[cid] = text
        user["state"] = "anon_confirm"
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ ارسال", callback_data="anon_send"),
            types.InlineKeyboardButton("❌ لغو", callback_data="anon_cancel")
        )
        bot.send_message(cid, f"مطمئنی این پیام ارسال بشه؟\n\n{text}", reply_markup=kb)
        return

# ---------- مدیریت کلیک‌ها (کال‌بک) ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id)
    user = users.get(cid)
    if not user: return

    if call.data.startswith("search_"):
        pref = call.data.replace("search_", "") # چیزی که کاربر میخواد
        user_gender = user.get("gender") # جنسیت خود کاربر
        user["state"] = "searching"
        user["search_pref"] = pref
        
        # پیدا کردن کسی که با خواسته ما جور باشه
        # اگر "فرقی نداره" زدیم، هم تو لیست پسرا میگردیم هم دخترا
        search_in = ["male", "female"] if pref == "any" else [pref]
        
        found = False
        for g in search_in:
            for pid in waiting[g]:
                partner = users.get(pid)
                # طرف مقابل باید دنبال جنسیت ما باشه یا براش فرق نکنه
                if partner and (partner.get("search_pref") == "any" or partner.get("search_pref") == user_gender):
                    # وصل شدن
                    user["partner"] = pid
                    partner["partner"] = cid
                    user["state"] = partner["state"] = "chat"
                    waiting[g].remove(pid)
                    
                    bot.send_message(cid, "🎉 به یه ناشناس وصل شدی! سلام کن...", reply_markup=end_chat_kb())
                    bot.send_message(pid, "🎉 به یه ناشناس وصل شدی! سلام کن...", reply_markup=end_chat_kb())
                    save_users()
                    found = True
                    break
            if found: break

        if not found:
            if cid not in waiting[user_gender]:
                waiting[user_gender].append(cid)
            bot.edit_message_text("⏳ در حال جستجو... هر وقت کسی پیدا بشه وصل میشی.", call.message.chat.id, call.message.message_id)
            bot.send_message(cid, "میتونی جستجو رو لغو کنی:", reply_markup=cancel_search_kb())

    if user["state"] == "anon_confirm":
        if call.data == "anon_send":
            target = user["anon_target"]
            msg = anon_pending.pop(cid, "پیام خالی")
            bot.send_message(target, f"📩 یه پیام ناشناس داری:\n\n{msg}")
            bot.send_message(cid, "✅ ارسال شد!")
            main_menu(cid)
        else:
            main_menu(cid)

# ---------- شروع برنامه ----------
if __name__ == "__main__":
    keep_alive() # بیدار باش!
    print("Bot is running...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
