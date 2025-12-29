import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- پایداری سرور ---
app = Flask('')
@app.route('/')
def home(): return "🤖 Database Integrated & Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091"  # آیدی عددی خودت
CHANNEL_ID = "@ChatNaAnnouncements" 
CHANNEL_NAME = "اطلاع رسانی|چت ناشناس"
bot = telebot.TeleBot(TOKEN)

# فایل‌های دیتابیس شما
USERS_FILE = "users.json"
CHATS_FILE = "chats.json"

# بارگذاری داده‌ها از فایل
def load_db(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

# ذخیره داده‌ها در فایل
def save_db(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- کیبوردهای جذاب (بدون تغییر متن) ---
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔥 شکارِ هم‌صحبت", "🎭 ایستگاهِ ناشناس")
    kb.add("💎 ویترینِ من", "📜 راهنمایِ سفر")
    if str(cid) == str(ADMIN_ID): kb.add("📢 طنینِ همگانی")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✂️ پایانِ قصه", "🚩 گزارشِ مزاحمت")
    return kb

def is_member(user_id):
    if str(user_id) == str(ADMIN_ID): return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

# --- مدیریت پیام‌ها ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation'])
def main_controller(message):
    cid = str(message.chat.id)
    users = load_db(USERS_FILE)
    chats = load_db(CHATS_FILE)

    # ۱. چک کردن عضویت
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        kb.add(types.InlineKeyboardButton("🚀 عضو شدم! بازش کن", callback_data="verify"))
        bot.send_message(cid, "⛔️ **دسترسی محدود شده است!**\nبرای عبور، ابتدا در کانال ما عضو شو و دکمه تایید رو بزن. ✨", reply_markup=kb)
        return

    # ۲. تشخیص لینک ناشناس (Deep Linking)
    if message.text and message.text.startswith("/start "):
        code = message.text.split()[1]
        target_id = next((u for u, d in users.items() if d.get("link") == code), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "anon_writing"
            users[cid]["target"] = target_id
            save_db(USERS_FILE, users)
            bot.send_message(cid, "🤫 **هیسسس!** هر چی تو دلت هست بنویس تا مخفیانه براش بفرستم:", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۳. فرآیند ثبت‌نام (ذخیره در users.json)
    if cid not in users or "name" not in users[cid]:
        if cid not in users: users[cid] = {"state": "get_name"}
        
        if users[cid]["state"] == "get_name" and message.text:
            users[cid].update({"name": message.text[:15], "state": "get_gender"})
            save_db(USERS_FILE, users)
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True).add("شوالیه (آقا) 👦", "بانو (خانم) 👧")
            bot.send_message(cid, "✅ حالا اصالتت رو انتخاب کن:", reply_markup=kb)
        elif users[cid]["state"] == "get_gender" and message.text:
            users[cid].update({"gender": "male" if "شوالیه" in message.text else "female", "state": "get_age"})
            save_db(USERS_FILE, users)
            bot.send_message(cid, "🎂 چند سالته؟ (فقط عدد)", reply_markup=types.ReplyKeyboardRemove())
        elif users[cid]["state"] == "get_age" and message.text and message.text.isdigit():
            users[cid].update({"age": message.text, "state": "main"})
            save_db(USERS_FILE, users)
            bot.send_message(cid, "🎉 خوش اومدی!", reply_markup=main_kb(cid))
        return

    user_data = users[cid]
    
    # ۴. پیام همگانی ادمین
    if user_data.get("state") == "broad_wait" and cid == str(ADMIN_ID):
        user_data["temp_msg"] = message.message_id
        user_data["state"] = "broad_confirm"
        save_db(USERS_FILE, users)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 بله، بفرست", callback_data="bc_yes"), types.InlineKeyboardButton("❌ لغو", callback_data="bc_no"))
        bot.send_message(cid, "⚠️ از ارسال این پیام برای همه مطمئنی؟", reply_markup=kb)
        return

    # ۵. منوی اصلی
    if user_data["state"] == "main":
        if message.text == "🔥 شکارِ هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقایان 👦", callback_data="f_male"), types.InlineKeyboardButton("خانم‌ها 👧", callback_data="f_female"))
            bot.send_message(cid, "🛰 در حال جستجو...", reply_markup=kb)
        elif message.text == "🎭 ایستگاهِ ناشناس":
            link = user_data.get("link") or str(random.randint(100000, 999999))
            users[cid]["link"] = link; save_db(USERS_FILE, users)
            bot.send_message(cid, f"🎁 لینک تو:\n`https://t.me/{bot.get_me().username}?start={link}`", parse_mode="Markdown")
        elif message.text == "💎 ویترینِ من":
            bot.send_message(cid, f"📝 **اطلاعات تو:**\n👤 نام: {user_data['name']}\n🚻 جنسیت: {user_data['gender']}\n🎂 سن: {user_data['age']}")
        elif message.text == "📢 طنینِ همگانی" and cid == str(ADMIN_ID):
            users[cid]["state"] = "broad_wait"; save_db(USERS_FILE, users)
            bot.send_message(cid, "📝 پیام رو بفرست:")

    # ۶. نوشتن پیام ناشناس
    elif user_data["state"] == "anon_writing":
        users[cid]["pending"] = message.text
        users[cid]["state"] = "anon_confirm"
        save_db(USERS_FILE, users)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال", callback_data="send_anon"), types.InlineKeyboardButton("❌ لغو", callback_data="cancel"))
        bot.send_message(cid, "📝 ارسال بشه؟", reply_markup=kb)

    # ۷. چت دو نفره (استفاده از chats.json)
    elif user_data["state"] == "chat":
        partner = user_data.get("partner")
        if message.text == "✂️ پایانِ قصه":
            # منطق قطع چت
            users[cid]["state"] = "main"; users[partner]["state"] = "main"
            save_db(USERS_FILE, users)
            bot.send_message(cid, "🔚 قطع شد.", reply_markup=main_kb(cid))
            bot.send_message(partner, "⚠️ طرف مقابل قطع کرد.", reply_markup=main_kb(partner))
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

# --- مدیریت دکمه‌های شیشه‌ای ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    cid = str(call.message.chat.id)
    users = load_db(USERS_FILE)
    
    if call.data == "bc_yes":
        msg_id = users[cid].get("temp_msg")
        for u in users:
            try: bot.copy_message(u, cid, msg_id)
            except: pass
        users[cid]["state"] = "main"; save_db(USERS_FILE, users)
        bot.edit_message_text("✅ ارسال شد.", cid, call.message.id)

    elif call.data == "send_anon":
        target = users[cid].get("target")
        msg = users[cid].get("pending")
        bot.send_message(target, f"📬 پیام ناشناس:\n\n{msg}")
        users[cid]["state"] = "main"; save_db(USERS_FILE, users)
        bot.edit_message_text("✅ فرستاده شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی", reply_markup=main_kb(cid))

    elif call.data == "verify":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ تایید شد!")
            bot.delete_message(cid, call.message.id)
        else:
            bot.answer_callback_query(call.id, "❌ عضو نشدی!", show_alert=True)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
