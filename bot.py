import telebot
from telebot import types
import json
import os
import random
import datetime
import re
import requests
import time
from flask import Flask
from threading import Thread

# --- سامانه پایداری ربات (Anti-Sleep) ---
app = Flask('')
@app.route('/')
def home():
    return "Shadow Bot Status: Online & Secured"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- تنظیمات اصلی و توکن‌ها ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091"
CHANNEL_ID = "@ChatNaAnnouncements"
HF_TOKEN = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk" # توکن هوش مصنوعی شما

bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_data.json"

# لیست سیاه کلمات (برای سرعت بیشتر قبل از ارسال به هوش مصنوعی)
BAD_WORDS = ["مادرجنده", "کص ننت", "کون", "کص", "کیر", "جنده", "ناموس", "بی‌ناموس", "کونی", "جنده‌خونه", "لاشی", "خایه", "ساک", "پستون", "کصکش", "دیوث"]

# --- توابع مدیریت دیتابیس ---
def get_db():
    if not os.path.exists(DB_PATH):
        db = {
            "users": {}, 
            "queue": {"male": [], "female": [], "any": []}, 
            "banned": {}, 
            "chat_history": {}, 
            "blocks": {}
        }
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # اطمینان از وجود کلیدهای اصلی
            for key in ["users", "queue", "banned", "chat_history", "blocks"]:
                if key not in data:
                    data[key] = {} if key != "queue" else {"male": [], "female": [], "any": []}
            return data
        except:
            return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "blocks": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

# --- سیستم هوش مصنوعی و تشخیص محتوا ---
def check_toxicity_ai(text):
    if not text or len(text) < 2: return 0
    API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": text}, timeout=10)
        output = response.json()
        if isinstance(output, list) and len(output) > 0:
            # بررسی نتایج مدل برای برچسب toxic
            for item in output[0]:
                if item['label'] == 'toxic':
                    return item['score']
    except Exception as e:
        print(f"AI Error: {e}")
        return 0
    return 0

def is_content_dangerous(message):
    if message.text:
        # ۱. بررسی متنی با لیست سیاه
        cleaned_text = re.sub(r'[\s\.\-\_\*\/\\n\+]+', '', message.text)
        if any(word in cleaned_text for word in BAD_WORDS):
            return True
        # ۲. بررسی با هوش مصنوعی Hugging Face
        ai_score = check_toxicity_ai(message.text)
        if ai_score > 0.85:
            return True
    return False

def check_subscription(uid):
    if str(uid) == OWNER_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, int(uid)).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

# --- طراحی کیبوردهای حرفه‌ای ---
def get_main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🛰 شروع چت ناشناس")
    btn2 = types.KeyboardButton("🤫 لینک پیام ناشناس")
    btn3 = types.KeyboardButton("👤 پروفایل من")
    btn4 = types.KeyboardButton("❓ راهنمای ربات")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    if str(uid) == OWNER_ID:
        markup.add(types.KeyboardButton("📊 مدیریت و آمار"), types.KeyboardButton("📢 ارسال همگانی"))
    return markup

def get_chat_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("❌ قطع چت"), types.KeyboardButton("🚩 گزارش تخلف"))
    markup.add(types.KeyboardButton("🚫 بلاک کردن کاربر"))
    return markup

# --- هندلرهای پیام ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def main_handler(message):
    uid = str(message.chat.id)
    db = get_db()
    
    # بررسی مسدود بودن
    if uid in db["banned"]:
        ban_data = db["banned"][uid]
        if ban_data['end'] == "perm":
            bot.send_message(uid, "🚫 **دسترسی شما برای همیشه قطع شده است.**\nعلت: نقض مکرر قوانین چت.")
            return
        else:
            expire_dt = datetime.datetime.fromisoformat(ban_data['end'])
            if datetime.datetime.now() < expire_dt:
                bot.send_message(uid, f"🚫 **حساب شما مسدود است.**\nزمان آزادی: `{ban_data['end']}`\nعلت: فحاشی یا گزارش‌های مکرر.")
                return
            else:
                del db["banned"][uid] # زمان بن تمام شده
                save_db(db)

    # کاربر جدید
    if uid not in db["users"]:
        db["users"][uid] = {"name": "ناشناس", "state": "start", "warns": 0, "ban_count": 0, "gender": "unknown", "link": str(random.randint(100000, 999999))}
        save_db(db)

    user = db["users"][uid]

    # شروع ربات
    if message.text and message.text.startswith("/start"):
        bot.send_message(uid, "👋 **به بزرگترین چت ناشناس خوش آمدی!**\n\nلطفاً یک نام مستعار برای خودت انتخاب کن:", reply_markup=types.ReplyKeyboardRemove())
        user["state"] = "set_name"
        save_db(db)
        return

    # تنظیم نام
    if user["state"] == "set_name":
        user["name"] = message.text[:15]
        user["state"] = "main"
        save_db(db)
        bot.send_message(uid, f"✅ نام مستعار شما با موفقیت به **{user['name']}** تغییر یافت.", reply_markup=get_main_keyboard(uid))
        return

    # مدیریت چت فعال
    if user["state"] == "in_chat":
        partner_id = user.get("partner")
        
        # دکمه‌های کنترلی
        if message.text == "❌ قطع چت":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("بله، قطع کن ✅", callback_data="end_yes"), types.InlineKeyboardButton("نه، ادامه بده 🔙", callback_data="end_no"))
            bot.send_message(uid, "⚠️ آیا مطمئنی می‌خواهی گفتگو را قطع کنی؟", reply_markup=markup)
            return

        # سیستم تشخیص فحاشی هوشمند
        if is_content_dangerous(message):
            bot.delete_message(uid, message.message_id)
            user["warns"] += 1
            save_db(db)
            
            # اخطار ۳: گزارش به ادمین
            if user["warns"] == 3:
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(
                    types.InlineKeyboardButton("🤖 تصمیم هوشمند", callback_data=f"ai_dec_{uid}"),
                    types.InlineKeyboardButton("⏳ بن موقت", callback_data=f"man_t_{uid}"),
                    types.InlineKeyboardButton("🚫 بن دائم", callback_data=f"man_p_{uid}")
                )
                bot.send_message(OWNER_ID, f"🚩 **گزارش ۳ اخطار!**\n\n👤 کاربر: {user['name']}\n🆔 آیدی: `{uid}`\n📝 آخرین پیام: {message.text if message.text else 'رسانه'}", reply_markup=markup)
                bot.send_message(uid, f"⚠️ **اخطار {user['warns']}/3!** رعایت ادب الزامی است. در صورت تکرار خودکار مسدود می‌شوید.")
            
            # بن پله‌ای بعد از ۳ اخطار
            elif user["warns"] > 3:
                user["ban_count"] += 1
                ban_minutes = 0
                ban_label = ""
                
                if user["ban_count"] == 1:
                    ban_minutes = 120; ban_label = "۲ ساعت"
                elif user["ban_count"] == 2:
                    ban_minutes = 1440; ban_label = "۲۴ ساعت"
                else:
                    ban_minutes = -1; ban_label = "دائم"
                
                if ban_minutes != -1:
                    expire = (datetime.datetime.now() + datetime.timedelta(minutes=ban_minutes)).isoformat()
                else:
                    expire = "perm"
                
                db["banned"][uid] = {"end": expire, "reason": "فحاشی خودکار"}
                
                # آزاد کردن هر دو نفر
                db["users"][partner_id]["state"] = "main"
                db["users"][partner_id]["partner"] = None
                user["state"] = "main"
                user["partner"] = None
                save_db(db)
                
                bot.send_message(uid, f"🚫 به دلیل تکرار فحاشی، شما برای **{ban_label}** مسدود شدید.")
                bot.send_message(partner_id, "⚠️ چت به دلیل تخلف کاربر مقابل به پایان رسید.", reply_markup=get_main_keyboard(partner_id))
                
                # گزارش بن به شما
                btn_unban = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔓 آنبن (بخشش)", callback_data=f"unban_{uid}"))
                bot.send_message(OWNER_ID, f"🤖 **سیستم بن خودکار:**\n\n👤 کاربر: `{uid}`\n⏳ مدت: {ban_label}\n📌 دلیل: فحاشی مکرر", reply_markup=btn_unban)
                return
            else:
                bot.send_message(uid, f"⚠️ کلام نامناسب! اخطار {user['warns']}/3.")
            return

        # کپی پیام برای پارتنر
        try:
            bot.copy_message(partner_id, uid, message.message_id)
        except:
            pass
        return

    # منوی اصلی
    if message.text == "🛰 شروع چت ناشناس":
        if not check_subscription(uid):
            bot.send_message(uid, f"❌ برای استفاده ابتدا باید در کانال ما عضو شوی:\n\n{CHANNEL_ID}")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("آقا 👦", callback_data="h_m"), types.InlineKeyboardButton("خانم 👧", callback_data="h_f"))
        markup.add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="h_a"))
        bot.send_message(uid, "🔍 مایل هستی با چه کسی چت کنی؟", reply_markup=markup)

    elif message.text == "👤 پروفایل من":
        bot.send_message(uid, f"👤 **مشخصات شما:**\n\n🏷 نام: {user['name']}\n🆔 آیدی: `{uid}`\n⚠️ تعداد اخطار: {user['warns']}\n🚫 تعداد بن‌های قبلی: {user['ban_count']}")

    elif message.text == "🤫 لینک پیام ناشناس":
        link = f"https://t.me/{bot.get_me().username}?start={user['link']}"
        bot.send_message(uid, f"🤫 **لینک اختصاصی شما رسید!**\n\nاین لینک را در بیو یا استوری قرار دهید:\n`{link}`")

# --- مدیریت دکمه‌های شیشه‌ای (Callbacks) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_logic(call):
    uid = str(call.message.chat.id)
    db = get_db()
    
    # جستجوی هم‌صحبت
    if call.data.startswith("h_"):
        bot.edit_message_text("🔍 در حال جستجوی هم‌صحبت... لطفاً کمی منتظر بمان.", uid, call.message.id)
        potential = [u_id for u_id in db["queue"]["any"] if u_id != uid]
        
        if potential:
            partner = potential[0]
            db["queue"]["any"].remove(partner)
            db["users"][uid].update({"state": "in_chat", "partner": partner})
            db["users"][partner].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 **هم‌صحبت پیدا شد!**\nمی‌توانی چت را شروع کنی.", reply_markup=get_chat_keyboard())
            bot.send_message(partner, "💎 **هم‌صحبت پیدا شد!**\nمی‌توانی چت را شروع کنی.", reply_markup=get_chat_keyboard())
        else:
            if uid not in db["queue"]["any"]:
                db["queue"]["any"].append(uid)
                save_db(db)
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("انصراف ❌", callback_data="c_search"))
            bot.send_message(uid, "⌛️ در صف انتظار هستید...", reply_markup=markup)

    elif call.data == "c_search":
        if uid in db["queue"]["any"]: db["queue"]["any"].remove(uid)
        save_db(db)
        bot.edit_message_text("❌ جستجو لغو شد.", uid, call.message.id)

    # تصمیم هوشمند ربات
    elif call.data.startswith("ai_dec_"):
        target = call.data.split("_")[2]
        t_user = db["users"].get(target)
        if t_user["ban_count"] > 0:
            db["banned"][target] = {"end": "perm", "reason": "AI Decision (Repeat Offender)"}
            msg = "🚫 کاربر به دلیل سابقه قبلی دائمی بن شد."
        else:
            exp = (datetime.datetime.now() + datetime.timedelta(hours=12)).isoformat()
            db["banned"][target] = {"end": exp, "reason": "AI Decision (First Offense)"}
            msg = "⏳ کاربر برای ۱۲ ساعت بن شد."
        save_db(db)
        bot.send_message(OWNER_ID, f"🤖 **نتیجه تصمیم هوشمند:**\n{msg}")

    # آنبن کردن
    elif call.data.startswith("unban_"):
        target = call.data.split("_")[1]
        if target in db["banned"]: del db["banned"][target]
        if target in db["users"]: 
            db["users"][target]["warns"] = 0
            db["users"][target]["ban_count"] = 0
        save_db(db)
        bot.send_message(OWNER_ID, f"✅ کاربر `{target}` بخشیده شد و اخطارهایش صفر شد.")

    elif call.data == "end_yes":
        partner = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][partner].update({"state": "main", "partner": None})
        save_db(db)
        bot.send_message(uid, "🔚 چت به پایان رسید.", reply_markup=get_main_keyboard(uid))
        bot.send_message(partner, "🔚 طرف مقابل چت را ترک کرد.", reply_markup=get_main_keyboard(partner))

# --- اجرای ربات ---
if __name__ == "__main__":
    print("Shadow Chat Bot is starting...")
    keep_alive()
    bot.infinity_polling()
