import telebot
from telebot import types
import json
import os
import re
import requests
import datetime
import time
import logging
import random
from flask import Flask
from threading import Thread

# ==========================================
# ۱. پیکربندی سیستم لاگ‌گیری و مانیتورینگ
# ==========================================
logging.basicConfig(
    filename='system_core.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask('')
@app.route('/')
def live_monitor():
    return "<h1>Shadow Sovereign Engine v10.0</h1><p>Status: Extreme Performance</p>"

def run_flask_app():
    app.run(host='0.0.0.0', port=8080)

def start_server():
    server_thread = Thread(target=run_flask_app)
    server_thread.daemon = True
    server_thread.start()

# ==========================================
# ۲. متغیرهای حیاتی و پیکربندی توکن‌ها
# ==========================================
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091"
CHANNEL_ID = "@ChatNaAnnouncements"
HF_TOKEN = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk"

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML")

# فایل‌های دیتابیس برای مدیریت کلان‌داده
FILE_USERS = "db_users_main.json"
FILE_BLACKLIST = "db_blacklist_core.json"
FILE_REPORTS = "db_violation_archive.json"
FILE_CONFIG = "db_system_config.json"
FILE_QUEUE = "db_matchmaking_queue.json"

# ==========================================
# ۳. لایه مدیریت داده (Data Access Layer)
# ==========================================
def initialize_all_databases():
    """تضمین سلامت و وجود تمامی فایل‌های دیتابیس"""
    db_templates = {
        FILE_USERS: {"users": {}},
        FILE_BLACKLIST: {"banned": {}},
        FILE_REPORTS: {"all_reports": []},
        FILE_CONFIG: {"stats": {"total_chats": 0, "ai_blocks": 0}, "settings": {"maintenance": False}},
        FILE_QUEUE: {"male": [], "female": [], "any": []}
    }
    for file_path, template in db_templates.items():
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=4)
            logger.info(f"Database {file_path} created successfully.")

def fetch_db(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return {}

def commit_db(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error writing to {path}: {e}")

# ==========================================
# ۴. موتور تحلیل محتوای سمی (AI Toxic Guard)
# ==========================================
def ai_security_scan(text_content):
    """آنالیز پیام توسط هوش مصنوعی برای حفظ سلامت محیط چت"""
    if not text_content or len(text_content.strip()) < 1:
        return 0.0
    
    # حذف نویزها برای دقت بالاتر در تشخیص فارسی و انگلیسی
    processed_text = re.sub(r'[\.\-\_\/\+\=\(\)\]\[]', ' ', text_content)
    
    api_endpoint = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    request_headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        req = requests.post(api_endpoint, headers=request_headers, json={"inputs": processed_text}, timeout=12)
        if req.status_code == 200:
            analysis_results = req.json()
            if isinstance(analysis_results, list) and len(analysis_results) > 0:
                for metric in analysis_results[0]:
                    if metric['label'] == 'toxic':
                        return metric['score']
        return 0.0
    except Exception as err:
        logger.warning(f"AI Guard Connection Warning: {err}")
        return 0.0

# ==========================================
# ۵. سیستم مدیریت وضعیت و کیبوردها
# ==========================================
def get_main_keyboard(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
    kb.add("🤫 لینک ناشناس", "💰 کیف پول و سکه")
    kb.add("❓ راهنما و پشتیبانی", "🏆 برترین‌های هفته")
    if str(user_id) == OWNER_ID:
        kb.add("📊 کنترل پنل مدیریت", "📢 ارسال همگانی")
    return kb

def get_chatting_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 پایان چت", "🚩 گزارش تخلف")
    kb.add("🚫 بلاک و خروج", "👥 اشتراک آیدی")
    return kb

def get_gender_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("آقا 👦", callback_data="reg_sex_m"),
        types.InlineKeyboardButton("خانم 👧", callback_data="reg_sex_f")
    )
    return kb

# ==========================================
# ۶. توابع کمکی و امنیتی
# ==========================================
def check_join_condition(uid):
    if str(uid) == OWNER_ID: return True
    try:
        member = bot.get_chat_member(CHANNEL_ID, uid)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

def calculate_ban_expiry(uid):
    blacklist = fetch_db(FILE_BLACKLIST)
    if str(uid) in blacklist["banned"]:
        info = blacklist["banned"][str(uid)]
        if info['end'] == "permanent": return "perm", "همیشگی"
        
        target_date = datetime.datetime.fromisoformat(info['end'])
        if datetime.datetime.now() < target_date:
            diff = target_date - datetime.datetime.now()
            h, r = divmod(int(diff.total_seconds()), 3600)
            m = r // 60
            return "temp", f"{h} ساعت و {m} دقیقه"
        else:
            del blacklist["banned"][str(uid)]
            commit_db(FILE_BLACKLIST, blacklist)
    return "free", None

def apply_step_ban(uid):
    users_db = fetch_db(FILE_USERS)
    bans_db = fetch_db(FILE_BLACKLIST)
    u_id = str(uid)
    
    users_db["users"][u_id]["ban_count"] += 1
    count = users_db["users"][u_id]["ban_count"]
    
    if count == 1: dur = 120; label = "۲ ساعت"
    elif count == 2: dur = 1440; label = "۲۴ ساعت"
    else: dur = -1; label = "دائمی"
    
    expiry = (datetime.datetime.now() + datetime.timedelta(minutes=dur)).isoformat() if dur != -1 else "permanent"
    bans_db["banned"][u_id] = {"end": expiry, "reason": "AI Content Violation", "at": str(datetime.datetime.now())}
    
    commit_db(FILE_USERS, users_db)
    commit_db(FILE_BLACKLIST, bans_db)
    return label

# ==========================================
# ۷. هسته پردازش منطقی پیام‌ها (Core Processor)
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note', 'document'])
def central_handler(message):
    uid = str(message.chat.id)
    initialize_all_databases()
    
    # الف) فیلتر بن و محدودیت دسترسی
    ban_status, time_msg = calculate_ban_expiry(uid)
    if ban_status != "free":
        bot.send_message(uid, f"🚫 <b>دسترسی شما معلق شده است.</b>\nزمان باقی‌مانده: <code>{time_msg}</code>"); return

    # ب) بررسی عضویت اجباری
    if not check_join_condition(uid):
        bot.send_message(uid, f"❌ برای استفاده از خدمات، ابتدا در کانال ما عضو شوید:\n{CHANNEL_ID}"); return

    users_db = fetch_db(FILE_USERS)

    # ج) مدیریت ثبت‌نام (Registration State Machine)
    if uid not in users_db["users"]:
        users_db["users"][uid] = {"state": "REGISTER_NAME", "warns": 0, "ban_count": 0, "partner": None, "coins": 10}
        commit_db(FILE_USERS, users_db)
        bot.send_message(uid, "👋 <b>به ربات شادو خوش آمدید!</b>\n\nبرای شروع، یک <b>نام مستعار</b> برای خود ارسال کنید:", reply_markup=types.ReplyKeyboardRemove())
        return

    curr_user = users_db["users"][uid]

    # پردازش مراحل ثبت نام
    if curr_user["state"] == "REGISTER_NAME":
        if ai_security_scan(message.text) > 0.65:
            bot.send_message(uid, "❌ این نام از نظر اخلاقی تایید نشد. نام دیگری بفرستید:"); return
        curr_user["name"] = message.text[:20]
        curr_user["state"] = "REGISTER_SEX"
        commit_db(FILE_USERS, users_db)
        bot.send_message(uid, f"خوش آمدی <b>{curr_user['name']}</b> عزیز. جنسیت خود را مشخص کن:", reply_markup=get_gender_keyboard())
        return

    if curr_user["state"] == "REGISTER_AGE":
        if not message.text.isdigit() or not (12 <= int(message.text) <= 90):
            bot.send_message(uid, "❌ سن باید عددی بین ۱۲ تا ۹۰ باشد. مجدداً وارد کنید:"); return
        curr_user["age"] = int(message.text)
        curr_user["state"] = "IDLE"
        commit_db(FILE_USERS, users_db)
        bot.send_message(uid, "🎉 <b>پروفایل شما تکمیل شد!</b>", reply_markup=get_main_keyboard(uid))
        return

    # د) موتور چت زنده (Live Transmission)
    if curr_user.get("partner"):
        partner_id = curr_user["partner"]
        
        # دکمه‌های کنترلی حین چت
        if message.text == "🔚 پایان چت":
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله 🔚", callback_data="chat_stop_confirm"), types.InlineKeyboardButton("خیر 🔙", callback_data="chat_stop_cancel"))
            bot.send_message(uid, "🤔 آیا مایل به قطع چت هستید؟", reply_markup=markup); return
        
        if message.text == "🚩 گزارش تخلف":
            markup = types.InlineKeyboardMarkup(row_width=2).add(
                types.InlineKeyboardButton("فحاشی 🤬", callback_data="rep_insult"),
                types.InlineKeyboardButton("محتوای جنسی 🔞", callback_data="rep_nsfw"),
                types.InlineKeyboardButton("مزاحمت ⛔️", callback_data="rep_harass"),
                types.InlineKeyboardButton("انصراف ❌", callback_data="rep_none")
            )
            bot.send_message(uid, "دلیل گزارش شما چیست؟", reply_markup=markup); return

        # آنتی‌توهین لحظه‌ای (AI Monitoring)
        if message.text:
            score = ai_security_scan(message.text)
            if score > 0.85:
                bot.delete_message(uid, message.message_id)
                curr_user["warns"] += 1
                commit_db(FILE_USERS, users_db)
                
                if curr_user["warns"] >= 3:
                    lbl = apply_step_ban(uid)
                    users_db = fetch_db(FILE_USERS) # Refresh data
                    users_db["users"][partner_id]["partner"] = None
                    curr_user["partner"] = None
                    commit_db(FILE_USERS, users_db)
                    bot.send_message(uid, f"🚫 شما به دلیل تکرار فحاشی برای <b>{lbl}</b> مسدود شدید.")
                    bot.send_message(partner_id, "⚠️ چت به دلیل بن شدن طرف مقابل پایان یافت.", reply_markup=get_main_keyboard(partner_id))
                    return
                else:
                    bot.send_message(uid, f"⚠️ <b>هشدار!</b> (اخطار {curr_user['warns']}/3)\nارسال الفاظ نامناسب ممنوع است."); return

        # انتقال امن محتوا
        try:
            bot.copy_message(partner_id, uid, message.message_id)
        except Exception as e:
            logger.error(f"Forward failed from {uid} to {partner_id}: {e}")
        return

    # ه) مدیریت منوی اصلی
    if message.text == "🛰 شروع چت ناشناس":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("آقا 👦", callback_data="hunt_m"), types.InlineKeyboardButton("خانم 👧", callback_data="hunt_f"), types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="hunt_any"))
        bot.send_message(uid, "🔍 مایل هستید با چه جنسیتی چت کنید؟", reply_markup=markup)
    
    elif message.text == "👤 پروفایل من":
        bot.send_message(uid, f"👤 <b>اطلاعات پروفایل:</b>\n\n🏷 نام: {curr_user.get('name')}\n⚧ جنسیت: {curr_user.get('gender', 'نامشخص')}\n🔢 سن: {curr_user.get('age', 'نامشخص')}\n⚠️ اخطارها: {curr_user['warns']}\n🚫 سابقه بن: {curr_user['ban_count']}\n💰 سکه: {curr_user['coins']}")

    elif message.text == "📊 کنترل پنل مدیریت" and uid == OWNER_ID:
        config = fetch_db(FILE_CONFIG)
        bot.send_message(uid, f"⚙ <b>پنل مدیریت مرکزی:</b>\n\nکل کاربران: {len(users_db['users'])}\nچت‌های انجام شده: {config['stats']['total_chats']}\nتشخیص‌های AI: {config['stats']['ai_blocks']}")

# ==========================================
# ۸. مدیریت رویدادهای کلیکی (Callback Queries)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def query_processor(call):
    uid = str(call.message.chat.id)
    users_db = fetch_db(FILE_USERS)
    queue_db = fetch_db(FILE_QUEUE)
    
    # عملیات ثبت نام
    if call.data.startswith("reg_sex_"):
        gender = "آقا" if "m" in call.data else "خانم"
        users_db["users"][uid]["gender"] = gender
        users_db["users"][uid]["state"] = "REGISTER_AGE"
        commit_db(FILE_USERS, users_db)
        bot.edit_message_text("🔢 بسیار خب، حالا <b>سن</b> خود را به عدد وارد کن:", uid, call.message.id)

    # عملیات جستجو و Matchmaking
    elif call.data.startswith("hunt_"):
        bot.edit_message_text("🔍 در حال جستجوی هم‌صحبت... لطفاً از برنامه خارج نشوید.", uid, call.message.id)
        q_list = queue_db["any"]
        if uid not in q_list:
            q_list.append(uid)
            commit_db(FILE_QUEUE, queue_db)
        
        # الگوریتم تطبیق Titan
        potentials = [p for p in q_list if p != uid]
        if potentials:
            partner = potentials[0]
            q_list.remove(partner); q_list.remove(uid)
            users_db["users"][uid]["partner"] = partner
            users_db["users"][partner]["partner"] = partner # اصلاح منطق اتصال
            # (در نسخه نهایی تمام فیلدها اصلاح شده است)
            users_db["users"][uid]["partner"] = partner
            users_db["users"][partner]["partner"] = uid
            
            commit_db(FILE_QUEUE, queue_db)
            commit_db(FILE_USERS, users_db)
            
            bot.send_message(uid, "💎 <b>متصل شدید!</b>\nمی‌توانید گفتگو را شروع کنید.", reply_markup=get_chatting_keyboard())
            bot.send_message(partner, "💎 <b>متصل شدید!</b>\nمی‌توانید گفتگو را شروع کنید.", reply_markup=get_chatting_keyboard())

    # پایان گفتگو
    elif call.data == "chat_stop_confirm":
        p_id = users_db["users"][uid]["partner"]
        users_db["users"][uid]["partner"] = None
        users_db["users"][p_id]["partner"] = None
        commit_db(FILE_USERS, users_db)
        bot.send_message(uid, "👋 چت پایان یافت.", reply_markup=get_main_keyboard(uid))
        bot.send_message(p_id, "⚠️ هم‌صحبت چت را ترک کرد.", reply_markup=get_main_keyboard(p_id))

# ==========================================
# ۹. نقطه شروع نهایی (Main Entry Point)
# ==========================================
if __name__ == "__main__":
    initialize_all_databases()
    start_server()
    logger.info("Shadow Sovereign Engine Initialized.")
    print("Bot is Polling...")
    bot.infinity_polling()
