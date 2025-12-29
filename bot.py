import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- سرور برای زنده نگه داشتن ---
app = Flask('')
@app.route('/')
def home(): return "✅ Database & Chat Log System is Active!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091"  # آیدی عددی خودت
BOT_USERNAME = "Chatnashenas_IriBot"
CHANNELS = ["@ChatNaAnnouncements"] 
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
BLACKLIST_FILE = "blacklist.json"
LOG_FILE = "chats_log.txt"

users = {}
waiting = {"male": [], "female": []}
blacklist = []
anon_pending = {}

# --- توابع مدیریت داده (اصلاح شده) ---
def load_data():
    global users, blacklist
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except: users = {}
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                blacklist = json.load(f)
        except: blacklist = []

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=4)

def log_chat(from_id, to_id, message_text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{from_id} -> {to_id}]: {message_text}\n")

# --- بررسی عضویت ---
def is_member(user_id):
    if str(user_id) == str(ADMIN_ID): return True
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        except: continue
    return True

# --- کیبوردها ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 پیدا کردن هم‌صحبت", "🔗 لینک ناشناس من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# --- شروع و هندل استارت ---
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    
    if cid in blacklist:
        bot.send_message(cid, "🚫 **دسترسی شما مسدود شده است.**")
        return

    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            kb.add(types.InlineKeyboardButton(f"📢 عضویت در کانال {i}", url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ عضو شدم! (تایید)", callback_data="check_membership"))
        bot.send_message(cid, "💎 **خوش اومدی!**\n\nواسه استفاده از ربات، اول تو کانال‌های زیر عضو شو:", reply_markup=kb)
        return

    # لینک ناشناس
    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسسس!**\n\nداری یه پیام ناشناس می‌فرستی. بنویس تا برسونم:", reply_markup=types.ReplyKeyboardRemove())
            save_users()
            return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 **سلام! به دنیای بزرگ چت ناشناس خوش اومدی.**\n\n✨ واسه قدم اول، اسمت چیه؟")
        save_users()
    else:
        name = users[cid].get("name", "دوست")
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 **{name} جان، خیلی خوش برگشتی!**", reply_markup=main_kb())
        save_users()

@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id)
    load_data()
    if cid in blacklist or not is_member(cid): return
    user = users.get(cid)
    if not user: return
    text = message.text

    # --- فرآیند ثبت نام و ذخیره در فایل ---
    if user["state"] == "get_name" and text:
        user["name"] = text[:15]
        user["state"] = "get_gender"
        save_users()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("آقا هستم 👦", "خانم هستم 👧")
        bot.send_message(cid, f"✅ خوشبختم {user['name']}! جنسیتت چیه؟", reply_markup=kb)
        return

    if user["state"] == "get_gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "get_age"
        save_users()
        bot.send_message(cid, "🎂 **چند سالته؟** (فقط عدد)", reply_markup=types.ReplyKeyboardRemove())
        return

    if user["state"] == "get_age" and text:
        if text.isdigit():
            user["age"] = int(text)
            user["state"] = "main"
            save_users()
            bot.send_message(cid, "🎉 **ثبت‌نامت با موفقیت ذخیره شد!**", reply_markup=main_kb())
        return

    # --- چت فعال و لاگ‌گیری ---
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله", callback_data="confirm_end"), types.InlineKeyboardButton("❌ خیر", callback_data="cancel_end"))
            bot.send_message(cid, "⚠️ مطمئنی؟", reply_markup=kb)
            return
        if partner:
            if message.content_type == 'text':
                log_chat(cid, partner, text)
                bot.send_message(partner, f"💬: {text}")
            elif message.content_type == 'photo':
                bot.send_photo(partner, message.photo[-1].file_id)
            elif message.content_type == 'voice':
                bot.send_voice(partner, message.voice.file_id)

    # --- منوی اصلی ---
    if user["state"] == "main":
        if text == "🚀 پیدا کردن هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="s_male"), types.InlineKeyboardButton("خانم 👧", callback_data="s_female"), types.InlineKeyboardButton("🌈 فرقی نمی‌کنه", callback_data="s_any"))
            bot.send_message(cid, "🛰 دنبال کی می‌گردی؟", reply_markup=kb)
        elif text == "🔗 لینک ناشناس من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code
            save_users()
            bot.send_message(cid, f"🎁 **لینک تو:**\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
        elif text == "👤 پروفایل من":
            bot.send_message(cid, f"👤 نام: {user['name']}\n🎂 سن: {user['age']}")

    # --- ارسال پیام ناشناس ---
    if user["state"] == "anon_write" and text:
        anon_pending[cid] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال", callback_data="send_anon_final"), types.InlineKeyboardButton("❌ لغو", callback_data="cancel_anon"))
        bot.send_message(cid, f"📝 ارسال بشه؟\n_{text}_", reply_markup=kb, parse_mode="Markdown")

# --- کال‌بک‌ها (بخش‌های اصلی) ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); load_data(); user = users.get(cid)
    if not user: return

    if call.data == "check_membership":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ تایید شد!")
            bot.delete_message(cid, call.message.id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ عضو نشدی!", show_alert=True)

    if call.data.startswith("s_"):
        pref = call.data.replace("s_", "")
        user.update({"search_pref": pref, "state": "searching"})
        save_users()
        try: bot.delete_message(cid, call.message.id)
        except: pass
        found = False
        search_list = ["male", "female"] if pref == "any" else [pref]
        for g in search_list:
            if waiting[g]:
                pid = waiting[g].pop(0)
                if pid != cid:
                    p = users[pid]
                    user.update({"partner": pid, "state": "chat"})
                    p.update({"partner": cid, "state": "chat"})
                    save_users()
                    bot.send_message(cid, "💎 **وصل شدی!**", reply_markup=chat_kb())
                    bot.send_message(pid, "💎 **وصل شدی!**", reply_markup=chat_kb())
                    found = True; break
        if not found:
            waiting[user['gender']].append(cid)
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ لغو جستجو", callback_data="cancel_search"))
            bot.send_message(cid, "🔍 در حال اسکن کردن کاربران...", reply_markup=kb)

    if call.data == "confirm_end":
        p_id = user.get("partner")
        if p_id: 
            users[p_id].update({"partner": None, "state": "main"})
            bot.send_message(p_id, "⚠️ طرف مقابل قطع کرد.", reply_markup=main_kb())
        user.update({"partner": None, "state": "main"})
        save_users()
        bot.send_message(cid, "🔚 قطع شد.", reply_markup=main_kb())

    if call.data == "send_anon_final":
        target = user.get("anon_target")
        msg = anon_pending.pop(cid, "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 پاسخ", callback_data=f"rep_{cid}"))
            bot.send_message(target, f"📬 **پیام ناشناس:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "✅ ارسال شد.", reply_markup=main_kb())
        user["state"] = "main"; save_users()

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.infinity_polling()
