import telebot
from telebot import types
import json, os, random
from datetime import datetime
from flask import Flask
from threading import Thread
import time

# --- تنظیمات سرور ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is Managed & Online!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAHMvegMz-NkQUbM7Zt4EnH4ZenpPORuJK4"
ADMIN_ID = "8013245091"  # <--- آیدی عددی خودت رو اینجا بذار
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
CHATS_FILE = "chats.json"
BLACKLIST_FILE = "blacklist.json"

users = {}
links = {}
waiting = {"male": [], "female": []}
blacklist = []
anon_pending = {}

# ---------- بارگذاری داده‌ها ----------
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
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=2)

# ---------- کیبوردها ----------
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 شروع چت ناشناس", "🔗 لینک اختصاصی من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    return kb

def end_chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# ---------- شروع ربات ----------
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    if cid in blacklist:
        bot.send_message(cid, "❌ شما به دلیل نقض قوانین مسدود شده‌اید.")
        return

    load_data()
    args = message.text.split()
    
    if len(args) > 1:
        code = args[1]
        if code in links:
            owner = links[code]
            if owner == cid:
                bot.send_message(cid, "⚠️ نمی‌توانی به خودت پیام ناشناس بدهی!")
                return
            users.setdefault(cid, {"name": message.from_user.first_name})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = owner
            bot.send_message(cid, "✉️ پیامت رو بنویس تا ناشناس ارسال بشه:")
            return

    if cid not in users or "gender" not in users[cid]:
        users[cid] = {"state": "name"}
        bot.send_message(cid, "🌱 سلام! خوش اومدی. اسمت رو وارد کن:")
        save_users()
        return
    
    users[cid]["state"] = "main"
    bot.send_message(cid, "🌟 منوی اصلی فعال شد.", reply_markup=main_kb())

# ---------- مدیریت پیام‌ها ----------
@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id)
    if cid in blacklist: return
    user = users.get(cid)
    if not user: return

    # ثبت‌نام (مشابه قبل...)
    if user["state"] == "name" and message.text:
        user["name"] = message.text.strip(); user["state"] = "gender"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("آقا 👦", "خانم 👧")
        bot.send_message(cid, "✅ جنسیتت رو انتخاب کن:", reply_markup=kb); return

    if user["state"] == "gender" and message.text:
        user["gender"] = "male" if "آقا" in message.text else "female"
        user["state"] = "age"; bot.send_message(cid, "🎂 چند سالته؟"); return

    if user["state"] == "age" and message.text:
        if message.text.isdigit():
            user["age"] = int(message.text); user["state"] = "main"
            bot.send_message(cid, "✅ خوش آمدی!", reply_markup=main_kb()); save_users(); return

    # چت فعال
    if user["state"] == "chat":
        partner = user.get("partner")
        if message.text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("✅ بله قطع کن", callback_data="confirm_end"),
                   types.InlineKeyboardButton("❌ خیر ادامه بده", callback_data="cancel_end"))
            bot.send_message(cid, "⚠️ مطمئنی می‌خوای مکالمه رو قطع کنی؟", reply_markup=kb)
            return
        
        if message.text == "🚩 گزارش تخلف":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("✅ بله، گزارش بده", callback_data="ask_report_reason"),
                   types.InlineKeyboardButton("❌ پشیمان شدم", callback_data="cancel_report"))
            bot.send_message(cid, "❓ آیا واقعاً قصد دارید این کاربر را گزارش کنید؟", reply_markup=kb)
            return

        if partner:
            if message.content_type == 'text': bot.send_message(partner, f"👤: {message.text}")
            elif message.content_type == 'photo': bot.send_photo(partner, message.photo[-1].file_id)
            elif message.content_type == 'voice': bot.send_voice(partner, message.voice.file_id)
            # ... بقیه مدیاها ...

    # منوی اصلی و لینک ناشناس (مشابه قبل...)
    if user["state"] == "main" and message.text:
        if message.text == "🚀 شروع چت ناشناس":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="search_male"),
                   types.InlineKeyboardButton("خانم 👧", callback_data="search_female"))
            kb.add(types.InlineKeyboardButton("فرقی نمی‌کنه 👫", callback_data="search_any"))
            bot.send_message(cid, "🎯 با کی چت کنیم؟", reply_markup=kb)
        elif message.text == "🔗 لینک اختصاصی من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; links[code] = cid
            bot.send_message(cid, f"🔗 لینک تو:\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
            save_users()
        elif message.text == "ℹ️ راهنما":
            bot.send_message(cid, "📘 این ربات برای چت ناشناس است. قوانین را رعایت کنید.")

# ---------- کال‌بک‌ها ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id)
    user = users.get(cid)
    if not user: return

    # شروع جستجو
    if call.data.startswith("search_"):
        user.update({"search_pref": call.data.replace("search_", ""), "state": "searching"})
        # منطق Matching (مشابه قبل...)
        bot.send_message(cid, "⏳ در حال جستجو...")

    # تایید گزارش و انتخاب دلیل
    if call.data == "ask_report_reason":
        kb = types.InlineKeyboardMarkup()
        reasons = [("توهین و فحاشی 🤬", "r_insult"), ("محتوای نامناسب 🔞", "r_18"), 
                   ("تبلیغات و اسپم 📢", "r_spam"), ("مزاحمت شدید ❌", "r_harras")]
        for text, data in reasons:
            kb.add(types.InlineKeyboardButton(text, callback_data=data))
        bot.edit_message_text("📍 دلیل گزارش خود را انتخاب کنید:", cid, call.message.id, reply_markup=kb)

    # ارسال گزارش نهایی به ادمین
    if call.data.startswith("r_"):
        reason = call.data
        partner_id = user.get("partner")
        if partner_id:
            # ارسال به ادمین
            admin_text = f"🚨 **گزارش جدید**\n\nمتخلف: `{partner_id}`\nدلیل: {reason}\nگزارش دهنده: `{cid}`"
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🚫 بن کردن متخلف", callback_data=f"admin_ban_{partner_id}"))
            bot.send_message(ADMIN_ID, admin_text, reply_markup=kb, parse_mode="Markdown")
            
            # قطع چت
            bot.send_message(partner_id, "🚩 شما گزارش شدید و مکالمه پایان یافت.")
            bot.send_message(cid, "✅ گزارش شما ارسال شد و چت قطع گردید.")
            users[partner_id]["partner"] = user["partner"] = None
            users[partner_id]["state"] = user["state"] = "main"
            bot.send_message(partner_id, "🌟 منوی اصلی", reply_markup=main_kb())
            bot.send_message(cid, "🌟 منوی اصلی", reply_markup=main_kb())

    # دکمه بن کردن توسط ادمین
    if call.data.startswith("admin_ban_") and str(cid) == str(ADMIN_ID):
        target = call.data.replace("admin_ban_", "")
        if target not in blacklist:
            blacklist.append(target)
            save_blacklist()
            bot.send_message(target, "❌ شما توسط ادمین مسدود شدید.")
            bot.answer_callback_query(call.id, "✅ کاربر با موفقیت بن شد.")

    if call.data == "confirm_end":
        # قطع چت (مشابه قبل...)
        bot.send_message(cid, "🔚 چت قطع شد.", reply_markup=main_kb())

if __name__ == "__main__":
    load_data()
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling()
