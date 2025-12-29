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
def home(): return "✅ Bot is Pro & Active!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# توکن و تنظیمات اصلی
TOKEN = "8213706320:AAGP3JUbxByGEMMl1dbntBqR3O4dq9hS6cQ"
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

# ---------- بارگذاری و ذخیره داده‌ها ----------
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

# ---------- شروع ربات ----------
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    args = message.text.split()
    
    if len(args) > 1:
        code = args[1]
        if code in links:
            owner = links[code]
            if owner == cid:
                bot.send_message(cid, "⚠️ نمی‌تونی به خودت پیام بدی!")
                return
            users.setdefault(cid, {"name": message.from_user.first_name})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = owner
            bot.send_message(cid, "✉️ پیامت رو بنویس:")
            return

    if cid not in users or "gender" not in users[cid]:
        users[cid] = {"state": "name"}
        bot.send_message(cid, "🌱 خوش اومدی! اسمت رو وارد کن:")
        save_users()
        return
    
    users[cid]["state"] = "main"
    bot.send_message(cid, "🌟 به منوی اصلی برگشتی.", reply_markup=main_kb())

# ---------- مدیریت چت (ارسال مدیا و متن) ----------
@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all_messages(message):
    cid = str(message.chat.id)
    user = users.get(cid)
    if not user: return
    state = user.get("state")

    # ثبت نام
    if state == "name" and message.text:
        user["name"] = message.text.strip()
        user["state"] = "gender"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("آقا 👦", "خانم 👧")
        bot.send_message(cid, "✅ جنسیتت؟", reply_markup=kb)
        return

    if state == "gender" and message.text:
        user["gender"] = "male" if "آقا" in message.text else "female"
        user["state"] = "age"
        bot.send_message(cid, "🎂 سنت؟ (فقط عدد)")
        return

    if state == "age" and message.text:
        if message.text.isdigit():
            user["age"] = int(message.text)
            user["state"] = "main"
            bot.send_message(cid, "✅ ثبت نام تکمیل شد!", reply_markup=main_kb())
            save_users()
        return

    # منوی اصلی
    if state == "main" and message.text:
        if message.text == "🚀 شروع چت ناشناس":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="search_male"),
                   types.InlineKeyboardButton("خانم 👧", callback_data="search_female"))
            kb.add(types.InlineKeyboardButton("فرقی نمی‌کنه 👫", callback_data="search_any"))
            bot.send_message(cid, "🎯 با کی چت کنیم؟", reply_markup=kb)
        elif message.text == "🔗 لینک اختصاصی من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code
            links[code] = cid
            bot.send_message(cid, f"🔗 لینک تو:\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
            save_users()
        elif message.text == "👤 پروفایل من":
            bot.send_message(cid, f"👤 نام: {user['name']}\n🎂 سن: {user.get('age')}\n🚻 جنسیت: {user['gender']}")

    # انتقال پیام‌ها در چت فعال (متن، عکس، ویس و...)
    if state == "chat":
        partner = user.get("partner")
        if message.text == "🔚 قطع مکالمه":
            end_chat_request(cid)
            return
        if message.text == "🚩 گزارش تخلف":
            report_user(cid)
            return
        
        if partner:
            # ارسال انواع مختلف فایل
            if message.content_type == 'text':
                bot.send_message(partner, f"👤: {message.text}")
            elif message.content_type == 'photo':
                bot.send_photo(partner, message.photo[-1].file_id, caption="🖼️ عکس فرستاد")
            elif message.content_type == 'voice':
                bot.send_voice(partner, message.voice.file_id)
            elif message.content_type == 'video':
                bot.send_video(partner, message.video.file_id)
            elif message.content_type == 'sticker':
                bot.send_sticker(partner, message.sticker.file_id)

def end_chat_request(cid):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ بله", callback_data="confirm_end"),
           types.InlineKeyboardButton("❌ خیر", callback_data="cancel_end"))
    bot.send_message(cid, "❓ مطمئنی می‌خوای قطع کنی؟", reply_markup=kb)

def report_user(cid):
    partner = users[cid].get("partner")
    if partner:
        bot.send_message(partner, "🚩 شما گزارش شدید و مکالمه قطع شد.")
        bot.send_message(cid, "✅ گزارش ثبت و مکالمه قطع شد.")
        # قطع چت برای هر دو
        users[partner]["partner"] = users[cid]["partner"] = None
        users[partner]["state"] = users[cid]["state"] = "main"
        bot.send_message(partner, "🌟 منوی اصلی", reply_markup=main_kb())
        bot.send_message(cid, "🌟 منوی اصلی", reply_markup=main_kb())

# ---------- مدیریت کلیک‌ها ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id)
    user = users.get(cid)
    if not user: return

    if call.data.startswith("search_"):
        pref = call.data.replace("search_", "")
        user["search_pref"] = pref
        user["state"] = "searching"
        
        search_in = ["male", "female"] if pref == "any" else [pref]
        found = False
        for g in search_in:
            for pid in waiting[g]:
                if pid != cid:
                    partner = users.get(pid)
                    # فیلتر سنی: اختلاف سن کمتر از 7 سال
                    if partner and abs(int(user.get('age',0)) - int(partner.get('age',0))) <= 7:
                        if partner.get("search_pref") == "any" or partner.get("search_pref") == user.get("gender"):
                            user["partner"], partner["partner"] = pid, cid
                            user["state"] = partner["state"] = "chat"
                            waiting[g].remove(pid)
                            bot.send_message(cid, "🎉 وصل شدی! (می‌تونی عکس و ویس هم بفرستی)", reply_markup=end_chat_kb())
                            bot.send_message(pid, "🎉 وصل شدی! (می‌تونی عکس و ویس هم بفرستی)", reply_markup=end_chat_kb())
                            found = True; break
            if found: break
        
        if not found:
            my_gender = user.get("gender")
            if cid not in waiting[my_gender]: waiting[my_gender].append(cid)
            bot.edit_message_text("⏳ در صف انتظار...", cid, call.message.id)

    if call.data == "confirm_end":
        partner = user.get("partner")
        if partner:
            users[partner]["partner"] = None
            users[partner]["state"] = "main"
            bot.send_message(partner, "⚠️ مکالمه تمام شد.", reply_markup=main_kb())
        user["partner"] = None
        user["state"] = "main"
        bot.send_message(cid, "✅ تمام شد.", reply_markup=main_kb())

# اجرا
if __name__ == "__main__":
    load_data()
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling()
