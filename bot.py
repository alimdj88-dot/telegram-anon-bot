import telebot
from telebot import types
import json
import os
import random
import datetime
import re
import requests
import time
import logging
from flask import Flask
from threading import Thread

# ==========================================
# ۱. پیکربندی سیستم لاگ‌گیری (Logging System)
# ==========================================
logging.basicConfig(
    filename='bot_activity.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# ۲. سامانه پایداری و مانیتورینگ
# ==========================================
app = Flask('')

@app.route('/')
def status_page():
    return "<h1>Shadow Titan Engine v8.0: Ultra-Performance Mode</h1><p>Status: Healthy</p>"

def run_flask_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive_init():
    t = Thread(target=run_flask_server)
    t.start()
    logger.info("Keep-alive server started.")

# ==========================================
# ۳. پارامترهای اصلی و توکن‌ها
# ==========================================
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091"
CHANNEL_ID = "@ChatNaAnnouncements"
HF_TOKEN = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk"

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

DB_USERS = "users_registry.json"
DB_BANS = "blacklist_system.json"
DB_REPORTS = "violation_archive.json"
DB_STATS = "global_stats.json"

# ==========================================
# ۴. مدیریت زیرساخت دیتابیس (JSON-DB Engine)
# ==========================================
def db_initialization():
    """ایجاد فایل‌های دیتابیس در صورت عدم وجود"""
    files = {
        DB_USERS: {"users": {}},
        DB_BANS: {"banned": {}},
        DB_REPORTS: {"reports": []},
        DB_STATS: {"total_chats": 0, "total_users": 0, "ai_detections": 0, "queue": {"male": [], "female": [], "any": []}}
    }
    for file_path, default_data in files.items():
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=4)
    logger.info("Database files checked/initialized.")

def get_db(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# ۵. موتور هوش مصنوعی (AI Content Analysis)
# ==========================================
def ai_content_filter(text):
    """آنالیز عمیق توسط مدل Toxic-BERT جهت تشخیص فحاشی و محتوای سمی"""
    if not text or len(text.strip()) < 1:
        return 0.0
    
    url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        # پاکسازی متون از کاراکترهای مخفی و نویزها
        clean_text = re.sub(r'[^\w\s]', ' ', text)
        response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=12)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                for score_box in data[0]:
                    if score_box['label'] == 'toxic':
                        return score_box['score']
        return 0.0
    except Exception as e:
        logger.error(f"AI API Connection Failed: {e}")
        return 0.0

# ==========================================
# ۶. مدیریت امنیت و محدودسازی (Ban Logic)
# ==========================================
def check_ban_status(user_id):
    """بررسی اینکه آیا کاربر در لیست سیاه است یا خیر"""
    db_bans = get_db(DB_BANS)
    uid = str(user_id)
    
    if uid in db_bans["banned"]:
        ban_info = db_bans["banned"][uid]
        if ban_info['end'] == "perm":
            return "permanent", None
        
        expiry = datetime.datetime.fromisoformat(ban_info['end'])
        if datetime.datetime.now() < expiry:
            diff = expiry - datetime.datetime.now()
            hours, remainder = divmod(int(diff.total_seconds()), 3600)
            minutes = remainder // 60
            return "temporary", f"{hours} ساعت و {minutes} دقیقه"
        else:
            del db_bans["banned"][uid]
            save_db(DB_BANS, db_bans)
    return "active", None

def execute_tiered_ban(user_id, reason="AI Violation"):
    """سیستم بن پله‌ای: ۲ ساعت -> ۲۴ ساعت -> دائم"""
    db_users = get_db(DB_USERS)
    db_bans = get_db(DB_BANS)
    uid = str(user_id)
    
    user = db_users["users"][uid]
    user["ban_count"] += 1
    
    if user["ban_count"] == 1:
        duration = 120; label = "۲ ساعت"
    elif user["ban_count"] == 2:
        duration = 1440; label = "۲۴ ساعت"
    else:
        duration = -1; label = "دائمی"
        
    expiry = (datetime.datetime.now() + datetime.timedelta(minutes=duration)).isoformat() if duration != -1 else "perm"
    db_bans["banned"][uid] = {
        "end": expiry,
        "reason": reason,
        "timestamp": str(datetime.datetime.now())
    }
    
    save_db(DB_USERS, db_users)
    save_db(DB_BANS, db_bans)
    return label

# ==========================================
# ۷. سیستم‌های کیبورد (UI/UX Design)
# ==========================================
def kb_main(user_id):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
    m.add("🤫 لینک ناشناس من", "🏆 برترین‌ها")
    m.add("❓ راهنما", "⚙ تنظیمات")
    if str(user_id) == OWNER_ID:
        m.add("📊 پنل مدیریت مرکزی", "📢 ارسال همگانی")
    return m

def kb_chat_live():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
    m.add("🚫 بلاک کاربر", "👥 ارسال آیدی")
    return m

def kb_inline_gender():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("آقا 👦", callback_data="set_sex_m"),
          types.InlineKeyboardButton("خانم 👧", callback_data="set_sex_f"))
    return m

def kb_inline_confirm_rules():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("قوانین را می‌پذیرم ✅", callback_data="rules_accept"))
    return m

def kb_admin_actions(target_id):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("🔓 آنبن", callback_data=f"adm_unban_{target_id}"),
          types.InlineKeyboardButton("🚫 بن دائم", callback_data=f"adm_pban_{target_id}"))
    return m

# ==========================================
# ۸. پردازشگر ثبت‌نام (Step-by-Step Registration)
# ==========================================
def handle_registration(message, db_users, uid):
    user = db_users["users"][uid]
    
    if user["state"] == "REG_NAME":
        if ai_content_filter(message.text) > 0.6:
            bot.send_message(uid, "❌ این نام توسط هوش مصنوعی رد شد. نام مودبانه‌ای بفرستید:"); return
        user["name"] = message.text[:20]
        user["state"] = "REG_SEX"
        save_db(DB_USERS, db_users)
        bot.send_message(uid, f"خوش آمدی <b>{user['name']}</b>. جنسیت خود را انتخاب کن:", reply_markup=kb_inline_gender())
    
    elif user["state"] == "REG_AGE":
        if not message.text.isdigit() or not (12 <= int(message.text) <= 90):
            bot.send_message(uid, "❌ سن نامعتبر است (۱۲ تا ۹۰). دوباره بفرستید:"); return
        user["age"] = message.text
        user["state"] = "REG_RULES"
        save_db(DB_USERS, db_users)
        bot.send_message(uid, "📜 <b>قوانین ربات:</b>\n۱. فحاشی ممنوع\n۲. ارسال محتوای جنسی ممنوع\n۳. مزاحمت ممنوع\n\nآیا تایید می‌کنید؟", reply_markup=kb_inline_confirm_rules())

# ==========================================
# ۹. هسته مرکزی چت و فیلترینگ (Titan Core)
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def titan_gateway(message):
    uid = str(message.chat.id)
    db_users = get_db(DB_USERS)
    db_stats = get_db(DB_STATS)
    
    # الف) فیلتر بن
    status, time_left = check_ban_status(uid)
    if status != "active":
        msg = "🚫 شما بن دائم هستید." if status == "permanent" else f"🚫 شما مسدود هستید. زمان باقی‌مانده: {time_left}"
        bot.send_message(uid, msg); return

    # ب) فیلتر عضویت
    if str(uid) != OWNER_ID:
        try:
            s = bot.get_chat_member(CHANNEL_ID, uid).status
            if s not in ['member', 'administrator', 'creator']:
                bot.send_message(uid, f"❌ لطفاً ابتدا عضو کانال شوید:\n{CHANNEL_ID}"); return
        except: pass

    # ج) مدیریت ثبت‌نام
    if uid not in db_users["users"]:
        db_users["users"][uid] = {"state": "REG_NAME", "warns": 0, "ban_count": 0, "partner": None}
        save_db(DB_USERS, db_users)
        bot.send_message(uid, "👋 برای شروع، <b>نام مستعار</b> خود را بفرستید:", reply_markup=types.ReplyKeyboardRemove()); return

    user = db_users["users"][uid]
    if user["state"] != "IDLE" and not user.get("partner"):
        handle_registration(message, db_users, uid); return

    # د) منطق چت فعال
    if user.get("partner"):
        pid = user["partner"]
        
        # دکمه‌های کنترلی چت
        if message.text == "🔚 پایان گفتگو":
            m = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله", callback_data="chat_end_y"), types.InlineKeyboardButton("خیر", callback_data="chat_end_n"))
            bot.send_message(uid, "❓ قطع چت؟", reply_markup=m); return

        # آنالیز هوش مصنوعی
        if message.text:
            toxic_score = ai_content_filter(message.text)
            if toxic_score > 0.82:
                bot.delete_message(uid, message.message_id)
                user["warns"] += 1; save_db(DB_USERS, db_users)
                if user["warns"] >= 3:
                    label = execute_tiered_ban(uid, f"Toxic Message: {message.text}")
                    db_users["users"][pid]["partner"] = None; user["partner"] = None; save_db(DB_USERS, db_users)
                    bot.send_message(uid, f"🚫 به دلیل فحاشی برای <b>{label}</b> بن شدید."); bot.send_message(pid, "⚠️ هم‌صحبت بن شد.", reply_markup=kb_main(pid))
                    bot.send_message(OWNER_ID, f"🚨 <b>بن خودکار:</b>\nکاربر: {uid}\nپیام: {message.text}", reply_markup=kb_admin_actions(uid))
                    return
                bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3. فحاشی نکنید!"); return

        # کپی محتوا به پارتنر
        try: bot.copy_message(pid, uid, message.message_id)
        except: pass
        return

    # ه) منوی اصلی
    if message.text == "🛰 شروع چت ناشناس":
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(types.InlineKeyboardButton("آقا 👦", callback_data="hunt_m"), types.InlineKeyboardButton("خانم 👧", callback_data="hunt_f"))
        m.add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="hunt_any"))
        bot.send_message(uid, "دنبال چه کسی هستی؟", reply_markup=m)
    
    elif message.text == "📊 پنل مدیریت مرکزی" and uid == OWNER_ID:
        total = len(db_users["users"])
        bot.send_message(uid, f"📊 <b>آمار کل سیستم:</b>\n\nتعداد کاربران: {total}\nچت‌های فعال: {db_stats['total_chats']}\nتعداد بن‌ها: {len(get_db(DB_BANS)['banned'])}")

# ==========================================
# ۱۰. مدیریت رویدادهای کلیکی (Callbacks)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def titan_callback_handler(call):
    uid = str(call.message.chat.id); db_users = get_db(DB_USERS); db_stats = get_db(DB_STATS)
    
    if call.data.startswith("set_sex_"):
        db_users["users"][uid]["sex"] = "m" if "m" in call.data else "f"
        db_users["users"][uid]["state"] = "REG_AGE"; save_db(DB_USERS, db_users)
        bot.edit_message_text("🔢 حالا <b>سن</b> خود را وارد کن:", uid, call.message.id)

    elif call.data == "rules_accept":
        db_users["users"][uid]["state"] = "IDLE"; save_db(DB_USERS, db_users)
        bot.edit_message_text("✅ تبریک! پروفایل شما فعال شد.", uid, call.message.id)
        bot.send_message(uid, "خوش آمدید!", reply_markup=kb_main(uid))

    elif call.data.startswith("hunt_"):
        bot.edit_message_text("🔍 در صف انتظار...", uid, call.message.id)
        q = db_stats["queue"]["any"]
        if uid not in q: q.append(uid); save_db(DB_STATS, db_stats)
        
        pots = [p for p in q if p != uid]
        if pots:
            p = pots[0]; q.remove(p); q.remove(uid); db_stats["total_chats"] += 1
            db_users["users"][uid]["partner"] = p; db_users["users"][p]["partner"] = uid
            save_db(DB_USERS, db_users); save_db(DB_STATS, db_stats)
            bot.send_message(uid, "💎 وصل شدید!", reply_markup=kb_chat_live())
            bot.send_message(p, "💎 وصل شدید!", reply_markup=kb_chat_live())

    elif call.data == "chat_end_y":
        u = db_users["users"][uid]; pid = u["partner"]
        u["partner"] = None; db_users["users"][pid]["partner"] = None; save_db(DB_USERS, db_users)
        bot.send_message(uid, "👋 چت تمام شد.", reply_markup=kb_main(uid))
        bot.send_message(pid, "⚠️ هم‌صحبت چت را ترک کرد.", reply_markup=kb_main(pid))

# ==========================================
# ۱۱. اجرای نهایی
# ==========================================
if __name__ == "__main__":
    db_initialization()
    keep_alive_init()
    logger.info("Bot is polling...")
    bot.infinity_polling()
