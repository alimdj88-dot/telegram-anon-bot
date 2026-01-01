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

# --- سامانه پایداری و سرور داخلی ---
app = Flask('')
@app.route('/')
def home():
    return "Shadow Ultimate AI Bot: System Status [ONLINE]"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- پیکربندی امنیتی و کلیدها ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091"
CHANNEL_ID = "@ChatNaAnnouncements"
HF_TOKEN = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk"

bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_full_data.json"

# --- مدیریت دیتابیس پیشرفته ---
def load_data():
    if not os.path.exists(DB_PATH):
        initial_structure = {
            "users": {},
            "queue": {"male": [], "female": [], "any": []},
            "banned_list": {},
            "global_blocks": {}, # برای بلاک دوطرفه
            "reports_archive": []
        }
        save_data(initial_structure)
        return initial_structure
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned_list": {}, "global_blocks": {}, "reports_archive": []}

def save_data(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- موتور هوش مصنوعی (Hugging Face Interface) ---
def get_ai_score(text):
    """تحلیل محتوا توسط هوش مصنوعی با قابلیت تشخیص لحن سمی"""
    if not text or len(text.strip()) < 1: return 0
    API_URL = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        # پاکسازی کاراکترهای مخفی برای دور زدن فیلتر
        clean_text = re.sub(r'[^\w\s]', '', text)
        response = requests.post(API_URL, headers=headers, json={"inputs": clean_text}, timeout=10)
        output = response.json()
        if isinstance(output, list) and len(output) > 0:
            for item in output[0]:
                if item['label'] == 'toxic':
                    return item['score']
    except Exception as e:
        print(f"AI Connection Error: {e}")
        return 0
    return 0

# --- توابع کمکی سیستم ---
def is_member(user_id):
    if str(user_id) == OWNER_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def get_time_diff(expiry_time):
    now = datetime.datetime.now()
    exp = datetime.datetime.fromisoformat(expiry_time)
    diff = exp - now
    if diff.total_seconds() <= 0: return None
    hours, remainder = divmod(int(diff.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours} ساعت و {minutes} دقیقه"

# --- طراحی کیبوردهای داینامیک ---
def main_markup(user_id):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🛰 شروع چت ناشناس", "👤 پروفایل و آمار")
    m.add("🤫 لینک ناشناس من", "❓ راهنما و قوانین")
    if str(user_id) == OWNER_ID:
        m.add("📊 پنل مدیریت مرکزی", "📢 ارسال پیام همگانی")
    return m

def in_chat_markup():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
    m.add("🚫 بلاک کردن هم‌صحبت")
    return m

def report_inline():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        types.InlineKeyboardButton("فحاشی شدید 🤬", callback_data="report_toxic"),
        types.InlineKeyboardButton("مزاحمت و بلاک ⛔️", callback_data="report_spam"),
        types.InlineKeyboardButton("محتوای جنسی 🔞", callback_data="report_nsfw"),
        types.InlineKeyboardButton("تبلیغات 📢", callback_data="report_ads"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="report_cancel")
    )
    return m

# --- هسته مرکزی پردازش پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def central_handler(message):
    uid = str(message.chat.id)
    db = load_data()
    
    # ۱. چک کردن بن سیستم
    if uid in db["banned_list"]:
        b_data = db["banned_list"][uid]
        if b_data['end'] == "perm":
            bot.send_message(uid, "🚫 **دسترسی شما به صورت دائمی قطع شده است.**\n\nدلیل: نقض مکرر قوانین و تایید هوش مصنوعی.")
            return
        
        remaining = get_time_diff(b_data['end'])
        if remaining:
            bot.send_message(uid, f"🚫 **شما در حال حاضر مسدود هستید.**\n\nزمان باقی‌مانده: {remaining}\nعلت: رفتار نامناسب")
            return
        else:
            del db["banned_list"][uid]
            save_data(db)

    # ۲. ثبت نام و مدیریت وضعیت کاربر
    if uid not in db["users"]:
        db["users"][uid] = {
            "name": "بدون نام",
            "state": "setting_name",
            "warns": 0,
            "ban_count": 0,
            "partner": None,
            "gender": "unknown",
            "joined_at": str(datetime.date.today())
        }
        save_data(db)
        bot.send_message(uid, "👋 خوش آمدی! برای شروع چت، یک **نام مستعار** برای خودت بفرست (نام نباید حاوی توهین باشد):")
        return

    user = db["users"][uid]

    # بخش تنظیم نام با نظارت هوش مصنوعی
    if user["state"] == "setting_name":
        if get_ai_score(message.text) > 0.65:
            bot.send_message(uid, "❌ این نام توسط هوش مصنوعی تایید نشد. نام مودبانه‌تری انتخاب کنید:")
            return
        user["name"] = message.text[:20]
        user["state"] = "main_menu"
        save_data(db)
        bot.send_message(uid, f"✅ نام شما با موفقیت ثبت شد: **{user['name']}**", reply_markup=main_markup(uid))
        return

    # ۳. مدیریت چت فعال
    if user["state"] == "chatting":
        partner_id = user["partner"]
        
        # دکمه‌های کنترلی داخل چت
        if message.text == "🔚 پایان گفتگو":
            m = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("بله 🔚", callback_data="confirm_end"),
                types.InlineKeyboardButton("خیر 🔙", callback_data="cancel_end")
            )
            bot.send_message(uid, "❓ آیا از اتمام چت اطمینان دارید؟", reply_markup=m)
            return

        if message.text == "🚩 گزارش تخلف":
            bot.send_message(uid, "لطفاً نوع تخلف هم‌صحبت را انتخاب کنید:", reply_markup=report_inline())
            return
            
        if message.text == "🚫 بلاک کردن هم‌صحبت":
            # اضافه کردن به لیست سیاه دوطرفه
            if uid not in db["global_blocks"]: db["global_blocks"][uid] = []
            db["global_blocks"][uid].append(partner_id)
            save_data(db)
            bot.send_message(uid, "✅ کاربر بلاک شد. دیگر هرگز در چت به او وصل نخواهید شد.")
            # پایان چت اجباری
            user["state"] = "main_menu"; user["partner"] = None
            db["users"][partner_id]["state"] = "main_menu"; db["users"][partner_id]["partner"] = None
            save_data(db)
            bot.send_message(uid, "چت پایان یافت.", reply_markup=main_markup(uid))
            bot.send_message(partner_id, "⚠️ طرف مقابل چت را ترک و شما را بلاک کرد.", reply_markup=main_markup(partner_id))
            return

        # ۴. فیلترینگ هوشمند پیام‌ها (AI Guard)
        if message.text:
            ai_score = get_ai_score(message.text)
            if ai_score > 0.82: # آستانه حساسیت هوش مصنوعی
                bot.delete_message(uid, message.message_id)
                user["warns"] += 1
                save_data(db)
                
                # سیستم پله‌ای اخطار و بن
                if user["warns"] == 3:
                    # گزارش به ادمین در اخطار سوم
                    m = types.InlineKeyboardMarkup(row_width=2)
                    m.add(
                        types.InlineKeyboardButton("🤖 تصمیم AI", callback_data=f"ai_logic_{uid}"),
                        types.InlineKeyboardButton("⏳ بن ۲۴ ساعته", callback_data=f"ban_24_{uid}"),
                        types.InlineKeyboardButton("🚫 بن دائمی", callback_data=f"ban_perm_{uid}"),
                        types.InlineKeyboardButton("✅ بخشش", callback_data=f"forgive_{uid}")
                    )
                    bot.send_message(OWNER_ID, f"🚨 **تخلف سطح ۳ شناسایی شد!**\n\n👤 نام: {user['name']}\n🆔 آیدی: `{uid}`\n📜 پیام: {message.text}\n📈 امتیاز سمیت: {ai_score:.2f}", reply_markup=m)
                    bot.send_message(uid, "⚠️ **اخطار ۳ از ۳!** پیام شما حاوی توهین بود. تکرار بعدی منجر به مسدودیت خودکار می‌شود.")
                
                elif user["warns"] > 3:
                    user["ban_count"] += 1
                    # تعیین مدت بن بر اساس تعداد دفعات
                    if user["ban_count"] == 1:
                        duration = 120; label = "۲ ساعت"
                    elif user["ban_count"] == 2:
                        duration = 1440; label = "۲۴ ساعت"
                    else:
                        duration = -1; label = "دائمی"
                    
                    expiry = (datetime.datetime.now() + datetime.timedelta(minutes=duration)).isoformat() if duration != -1 else "perm"
                    db["banned_list"][uid] = {"end": expiry, "by": "Auto-AI"}
                    
                    # ریست کردن وضعیت‌ها
                    user["state"] = "main_menu"; user["partner"] = None
                    db["users"][partner_id]["state"] = "main_menu"; db["users"][partner_id]["partner"] = None
                    save_data(db)
                    
                    bot.send_message(uid, f"🚫 به دلیل عدم توجه به اخطارهای هوش مصنوعی، شما برای **{label}** مسدود شدید.")
                    bot.send_message(partner_id, "⚠️ هم‌صحبت شما به دلیل نقض قوانین بن شد.", reply_markup=main_markup(partner_id))
                    return
                else:
                    bot.send_message(uid, f"⚠️ کلام نامناسب! اخطار {user['warns']}/3. پیام شما حذف شد.")
                return

        # ارسال پیام به طرف مقابل در صورت نبود تخلف
        try:
            bot.copy_message(partner_id, uid, message.message_id)
        except Exception:
            pass
        return

    # ۵. منوی اصلی
    if message.text == "🛰 شروع چت ناشناس":
        if not is_member(uid):
            bot.send_message(uid, f"❌ برای استفاده از ربات باید در کانال ما عضو باشید:\n{CHANNEL_ID}")
            return
        m = types.InlineKeyboardMarkup(row_width=2)
        m.add(types.InlineKeyboardButton("آقا 👦", callback_data="find_m"), types.InlineKeyboardButton("خانم 👧", callback_data="find_f"))
        m.add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="find_any"))
        bot.send_message(uid, "🔍 مایل هستید با چه کسی چت کنید؟", reply_markup=m)

    elif message.text == "👤 پروفایل و آمار":
        bot.send_message(uid, f"👤 **پروفایل شما:**\n\n🏷 نام: {user['name']}\n🆔 آیدی: `{uid}`\n⚠️ تعداد اخطارها: {user['warns']}\n🚫 تعداد کل مسدودیت‌ها: {user['ban_count']}\n📅 تاریخ عضویت: {user['joined_at']}")

# --- هندلر دکمه‌های شیشه‌ای و منطق تصمیم‌گیری ---
@bot.callback_query_handler(func=lambda call: True)
def callback_manager(call):
    uid = str(call.message.chat.id)
    db = load_data()
    
    # بخش مدیریت ادمین
    if call.data.startswith("ai_logic_"):
        target_id = call.data.split("_")[2]
        t_user = db["users"].get(target_id)
        # تصمیم‌گیری بر اساس تاریخچه
        if t_user["ban_count"] > 0:
            db["banned_list"][target_id] = {"end": "perm"}
            res = "دائمی"
        else:
            db["banned_list"][target_id] = {"end": (datetime.datetime.now() + datetime.timedelta(hours=12)).isoformat()}
            res = "۱۲ ساعته"
        save_data(db)
        bot.edit_message_text(f"✅ تصمیم هوشمند اجرا شد: بن {res}", uid, call.message.id)

    elif call.data.startswith("ban_24_"):
        target_id = call.data.split("_")[2]
        db["banned_list"][target_id] = {"end": (datetime.datetime.now() + datetime.timedelta(hours=24)).isoformat()}
        save_data(db); bot.send_message(uid, "کاربر ۲۴ ساعت بن شد.")

    elif call.data.startswith("forgive_"):
        target_id = call.data.split("_")[2]
        db["users"][target_id]["warns"] = 0; save_data(db)
        bot.send_message(uid, "کاربر بخشیده شد.")
        bot.send_message(target_id, "✅ ادمین شما را بخشید. اخطارهای شما صفر شد.")

    # جستجوی هم‌صحبت
    elif call.data.startswith("find_"):
        bot.edit_message_text("🔍 در حال جستجوی هم‌صحبت مودب برای شما...", uid, call.message.id)
        if uid not in db["queue"]["any"]: db["queue"]["any"].append(uid); save_data(db)
        
        # الگوریتم اتصال (با چک کردن بلاک لیست)
        potential = [q for q in db["queue"]["any"] if q != uid]
        if potential:
            # چک کردن اینکه آیا همدیگر را بلاک کرده‌اند یا نه
            p_id = potential[0]
            if p_id in db["global_blocks"].get(uid, []) or uid in db["global_blocks"].get(p_id, []):
                # اگر بلاک بودند، سراغ نفر بعدی برو (در این کد ساده شده به نفر اول ختم می‌شود)
                pass 
            else:
                db["queue"]["any"].remove(p_id); db["queue"]["any"].remove(uid)
                db["users"][uid].update({"state": "chatting", "partner": p_id})
                db["users"][p_id].update({"state": "chatting", "partner": uid}); save_data(db)
                bot.send_message(uid, "💎 پیدا شد! گفتگو را شروع کنید.", reply_markup=in_chat_markup())
                bot.send_message(p_id, "💎 پیدا شد! گفتگو را شروع کنید.", reply_markup=in_chat_markup())

    elif call.data == "confirm_end":
        partner = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main_menu", "partner": None})
        db["users"][partner].update({"state": "main_menu", "partner": None}); save_data(db)
        bot.send_message(uid, "چت تمام شد.", reply_markup=main_markup(uid))
        bot.send_message(partner, "⚠️ هم‌صحبت چت را ترک کرد.", reply_markup=main_markup(partner))

if __name__ == "__main__":
    print("Shadow Ultimate Bot is Running...")
    keep_alive()
    bot.infinity_polling()
