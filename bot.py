import telebot
from telebot import types
import json, os, random
from datetime import datetime
from flask import Flask
from threading import Thread
import time

# --- تنظیمات سرور برای بیدار ماندن در رندر ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is Online!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# توکن و تنظیمات اصلی
TOKEN = "8213706320:AAEdPVVuC6NdVcIWJah4jq218CriKS3qV2I"
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

# فایل‌های ذخیره‌سازی
USERS_FILE = "users.json"
CHATS_FILE = "chats.json"

users = {}
links = {}
waiting = {"male": [], "female": []}
anon_pending = {}
chats = []

def load_data():
    global users, chats
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except: users = {}
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                chats = json.load(f)
        except: chats = []

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_chats():
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)

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

# ---------- دستورات اصلی ----------
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    args = message.text.split()
    
    # مدیریت لینک ناشناس
    if len(args) > 1:
        code = args[1]
        if code in links:
            owner = links[code]
            if owner == cid:
                bot.send_message(cid, "⚠️ شما نمی‌توانید به لینک ناشناس خودتان پیام بدهید!")
                return
            users.setdefault(cid, {"name": message.from_user.first_name})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = owner
            bot.send_message(cid, "✉️ پیامت رو بنویس تا به صورت کاملاً ناشناس برای طرف مقابل ارسال بشه:")
            save_users()
            return

    if cid not in users or "gender" not in users[cid]:
        users[cid] = {"state": "name"}
        bot.send_message(cid, "🌱 خوش اومدی! برای شروع لطفاً اسمت رو وارد کن:")
        save_users()
        return
    
    users[cid]["state"] = "main"
    bot.send_message(cid, "🌟 به دنیای چت ناشناس خوش اومدی!", reply_markup=main_kb())

# ---------- مدیریت پیام‌ها ----------
@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id)
    user = users.get(cid)
    if not user: return
    text = message.text

    # ثبت‌نام
    if user["state"] == "name" and text:
        user["name"] = text.strip()
        user["state"] = "gender"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("آقا 👦", "خانم 👧")
        bot.send_message(cid, f"✅ خوشبختم {text}! حالا جنسیتت رو انتخاب کن:", reply_markup=kb)
        return

    if user["state"] == "gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "age"
        bot.send_message(cid, "🎂 چند سالته؟ (عدد وارد کن)")
        return

    if user["state"] == "age" and text:
        if text.isdigit():
            user["age"] = int(text)
            user["state"] = "main"
            bot.send_message(cid, "✅ پروفایل شما با موفقیت ساخته شد.", reply_markup=main_kb())
            save_users()
        return

    # منوی اصلی
    if user["state"] == "main" and text:
        if text == "🚀 شروع چت ناشناس":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="search_male"),
                   types.InlineKeyboardButton("خانم 👧", callback_data="search_female"))
            kb.add(types.InlineKeyboardButton("فرقی نمی‌کنه 👫", callback_data="search_any"))
            bot.send_message(cid, "🎯 قصد داری با چه کسی هم‌صحبت بشی؟", reply_markup=kb)
        
        elif text == "🔗 لینک اختصاصی من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code
            links[code] = cid
            bot.send_message(cid, f"🔗 لینک ناشناس همیشگی تو:\n\n`https://t.me/{BOT_USERNAME}?start={code}`\n\nاین لینک رو پخش کن تا بقیه بتونن بهت پیام بدن.", parse_mode="Markdown")
            save_users()

        elif text == "👤 پروفایل من":
            g = "آقا 👦" if user['gender'] == 'male' else "خانم 👧"
            bot.send_message(cid, f"📝 **اطلاعات شما:**\n\n👤 نام: {user['name']}\n🎂 سن: {user['age']}\n🚻 جنسیت: {g}", parse_mode="Markdown")

        elif text == "ℹ️ راهنما":
            help_text = (
                "📘 **راهنمای استفاده از ربات:**\n\n"
                "1️⃣ **چت ناشناس:** با زدن این دکمه، سیستم شما را به یک فرد ناشناس وصل می‌کند. شما می‌توانید متن، عکس و ویس بفرستید.\n\n"
                "2️⃣ **لینک ناشناس:** لینکی مخصوص به شماست. هر کسی روی آن بزند می‌تواند برای شما پیام بفرستد بدون اینکه بفهمید او کیست.\n\n"
                "3️⃣ **امنیت:** هویت شما کاملاً مخفی می‌ماند. اگر کسی مزاحمت ایجاد کرد، از دکمه '🚩 گزارش تخلف' استفاده کنید.\n\n"
                "4️⃣ **پایان چت:** برای قطع مکالمه دکمه '🔚 قطع مکالمه' را بزنید."
            )
            bot.send_message(cid, help_text, parse_mode="Markdown")

    # چت ناشناس فعال
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("✅ بله قطع کن", callback_data="confirm_end"),
                   types.InlineKeyboardButton("❌ خیر ادامه بده", callback_data="cancel_end"))
            bot.send_message(cid, "⚠️ مطمئنی می‌خوای مکالمه رو قطع کنی؟", reply_markup=kb)
            return
        
        if text == "🚩 گزارش تخلف":
            if partner:
                bot.send_message(partner, "🚩 شما گزارش شدید و مکالمه پایان یافت.")
                bot.send_message(cid, "✅ گزارش شما ثبت و مکالمه قطع شد.")
                users[partner]["partner"] = users[cid]["partner"] = None
                users[partner]["state"] = users[cid]["state"] = "main"
                bot.send_message(partner, "🌟 منوی اصلی", reply_markup=main_kb())
                bot.send_message(cid, "🌟 منوی اصلی", reply_markup=main_kb())
            return

        if partner:
            if message.content_type == 'text': bot.send_message(partner, f"👤: {text}")
            elif message.content_type == 'photo': bot.send_photo(partner, message.photo[-1].file_id, caption="🖼️")
            elif message.content_type == 'voice': bot.send_voice(partner, message.voice.file_id)
            elif message.content_type == 'video': bot.send_video(partner, message.video.file_id)
            elif message.content_type == 'sticker': bot.send_sticker(partner, message.sticker.file_id)

    # نوشتن پیام ناشناس (لینک)
    if user["state"] == "anon_write" and text:
        anon_pending[cid] = text
        user["state"] = "anon_confirm"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("✅ تایید و ارسال", callback_data="anon_send"),
               types.InlineKeyboardButton("❌ لغو", callback_data="anon_cancel"))
        bot.send_message(cid, f"💬 متن پیام شما:\n\n_{text}_\n\nآیا ارسال بشه؟", reply_markup=kb, parse_mode="Markdown")

# ---------- کال‌بک‌ها ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id)
    user = users.get(cid)
    if not user: return

    if call.data.startswith("search_"):
        pref = call.data.replace("search_", "")
        user.update({"search_pref": pref, "state": "searching"})
        found = False
        search_list = ["male", "female"] if pref == "any" else [pref]
        
        for g in search_list:
            for pid in waiting[g]:
                if pid != cid:
                    p = users.get(pid)
                    if p and abs(int(user['age']) - int(p['age'])) <= 10:
                        user["partner"], p["partner"] = pid, cid
                        user["state"] = p["state"] = "chat"
                        waiting[g].remove(pid)
                        bot.send_message(cid, "🎉 متصل شدی! حالا شروع کنید:", reply_markup=end_chat_kb())
                        bot.send_message(pid, "🎉 متصل شدی! حالا شروع کنید:", reply_markup=end_chat_kb())
                        found = True; break
            if found: break
        
        if not found:
            if cid not in waiting[user['gender']]: waiting[user['gender']].append(cid)
            bot.edit_message_text("⏳ در حال یافتن هم‌صحبت مناسب...", cid, call.message.id)

    if call.data == "anon_send":
        target = user.get("anon_target")
        msg = anon_pending.pop(cid, "...")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📩 پاسخ به این پیام", callback_data=f"rep_{cid}"))
        bot.send_message(target, f"🔔 یک پیام ناشناس جدید داری:\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
        bot.send_message(cid, "✅ پیام شما با موفقیت ارسال شد.")
        user["state"] = "main"
        bot.send_message(cid, "🌟 منوی اصلی", reply_markup=main_kb())

    if call.data == "confirm_end":
        p = user.get("partner")
        if p:
            users[p].update({"partner": None, "state": "main"})
            bot.send_message(p, "⚠️ مکالمه پایان یافت.", reply_markup=main_kb())
        user.update({"partner": None, "state": "main"})
        bot.send_message(cid, "✅ مکالمه پایان یافت.", reply_markup=main_kb())

    if call.data.startswith("rep_"):
        user.update({"state": "anon_write", "anon_target": call.data.replace("rep_", "")})
        bot.send_message(cid, "✍️ پاسخت رو بنویس:")

if __name__ == "__main__":
    load_data()
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling()
