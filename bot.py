import telebot
from telebot import types
import json, os, random, datetime, re, time
from flask import Flask
from threading import Thread

# --- سامانه پایداری ربات (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Shadow Chat System is Online and Active."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات و متغیرهای اصلی ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_data.json"

# لیست کلمات ممنوعه برای فیلتر هوشمند
BAD_WORDS = ["مادرجنده", "کص ننت", "کون", "کص", "کیر", "جنده", "ناموس", "بی‌ناموس", "کونی", "لاشی", "خایه", "ساک", "پستون"] 
user_last_msg_time = {}

# --- مدیریت دیتابیس فایل‌محور ---
def get_db():
    if not os.path.exists(DB_PATH): 
        db = {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}, "blocks": {}}
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # اطمینان از وجود تمام کلیدهای دیتابیس
            keys = ["users", "queue", "banned", "chat_history", "anon_msgs", "blocks"]
            for k in keys:
                if k not in data: data[k] = {} if k != "queue" else {"male": [], "female": [], "any": []}
            return data
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}, "blocks": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def is_bad(text):
    if not text: return False
    cleaned = re.sub(r'[\s\.\-\_\*\/\\n\+]+', '', text)
    for w in BAD_WORDS:
        if w in cleaned: return True
    return False

def check_sub(uid):
    if str(uid) == OWNER_ID: return True
    try:
        s = bot.get_chat_member(CHANNEL_ID, int(uid)).status
        return s in ['member', 'administrator', 'creator']
    except: return False

# --- کیبوردهای ربات ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛰 شروع چت ناشناس", "🤫 لینک پیام ناشناس")
    markup.add("👤 پروفایل من", "❓ راهنمای ربات")
    if str(uid) == OWNER_ID:
        markup.add("📢 ارسال همگانی", "📊 مدیریت و آمار")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("❌ قطع چت", "🚩 گزارش تخلف")
    markup.add("🚫 بلاک کردن کاربر")
    return markup

# --- پردازشگر اصلی متن و رسانه ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    
    # ۱. بررسی وضعیت مسدودیت (Ban System)
    if uid in db.get("banned", {}):
        expire_str = db["banned"][uid]['end']
        if expire_str == "perm":
            bot.send_message(uid, "🚫 **دسترسی شما به صورت دائمی قطع شده است.**")
            return
        elif datetime.datetime.now() < datetime.datetime.fromisoformat(expire_str):
            bot.send_message(uid, f"🚫 **حساب شما موقتاً مسدود است.**\nپایان مسدودیت: {expire_str}")
            return

    # ۲. هندلر ادمین برای بن موقت (رفع باگ قفل شدن وضعیت)
    user = db["users"].get(uid)
    if uid == OWNER_ID and user and user.get("state") == "waiting_ban_time":
        if message.text and message.text.isdigit():
            target = user.get("temp_target")
            expire = (datetime.datetime.now() + datetime.timedelta(minutes=int(message.text))).isoformat()
            db["banned"][target] = {"end": expire}
            db["users"][uid]["state"] = "main"
            save_db(db)
            bot.send_message(uid, f"✅ کاربر {target} برای {message.text} دقیقه بن شد.", reply_markup=main_menu(uid))
            try: bot.send_message(target, f"⏳ حساب شما به دلیل تخلف برای {message.text} دقیقه مسدود شد.")
            except: pass
            return
        else:
            db["users"][uid]["state"] = "main"; save_db(db)

    # ۳. بررسی عضویت اجباری (Join Channel)
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("عضویت در کانال خبررسانی 📢", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        bot.send_message(uid, "👋 **خوش آمدی!**\nبرای استفاده از امکانات ربات چت ناشناس، ابتدا باید در کانال زیر عضو شوید:", reply_markup=btn)
        return

    # ۴. سیستم ضد اسپم (Anti-Spam)
    now = time.time()
    if uid in user_last_msg_time and now - user_last_msg_time[uid] < 0.7:
        bot.send_message(uid, "⚠️ لطفاً پیام‌ها را با سرعت کمتری ارسال کنید.")
        return
    user_last_msg_time[uid] = now

    # ۵. دستور شروع و ورودی‌های لینک (Start & Registration)
    if message.text and message.text.startswith("/start"):
        # بررسی ثبت‌نام ناقص
        if uid not in db["users"] or "gender" not in db["users"][uid]:
            db["users"][uid] = {"state": "reg_name"}
            save_db(db)
            bot.send_message(uid, "✨ **به ربات چت ناشناس خوش آمدی!**\nبرای شروع، یک نام مستعار برای خودت وارد کن:")
            return
        
        args = message.text.split()
        if len(args) > 1: # ورود با لینک ناشناس
            code = args[1]
            target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
            if target == uid: bot.send_message(uid, "🙄 شما نمی‌توانید به خودتان پیام ناشناس بدهید."); return
            if target:
                db["users"][uid].update({"state": "writing_confession", "target": target})
                save_db(db)
                bot.send_message(uid, "📝 **در حال ارسال پیام ناشناس...**\nپیام خود را بنویسید (هویت شما کاملاً مخفی می‌ماند):", reply_markup=types.ReplyKeyboardRemove())
                return
        
        bot.send_message(uid, "💎 **منوی اصلی**\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=main_menu(uid))
        return

    if not user: return

    # ۶. سیستم ریپلای ناشناس با تاییدیه (Reply System)
    if message.reply_to_message and user.get("state") == "main":
        target_uid = next((u_id for u_id, u_data in db["users"].items() if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            db["users"][uid].update({"state": "writing_confession", "target": target_uid, "temp_msg": message.text})
            save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال قطعی 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
            bot.send_message(uid, f"✅ **پیش‌نمایش پاسخ:**\n\n{message.text}\n\nآیا از ارسال این پاسخ اطمینان دارید؟", reply_markup=btn)
            return

    # ۷. فرآیند ثبت‌نام گام‌به‌گام
    if user["state"] == "reg_name":
        db["users"][uid].update({"name": message.text[:20], "state": "reg_gender"})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="set_m"), types.InlineKeyboardButton("خانم 👧", callback_data="set_f"))
        bot.send_message(uid, f"✨ **خوشبختم {message.text}!**\nحالا جنسیت خودت رو انتخاب کن:", reply_markup=btn)
        return
    elif user["state"] == "reg_age":
        if message.text and message.text.isdigit() and 10 < int(message.text) < 90:
            db["users"][uid].update({"age": message.text, "state": "main"})
            save_db(db)
            bot.send_message(uid, "🎉 **تبریک! پروفایل شما تکمیل شد.**", reply_markup=main_menu(uid))
        else:
            bot.send_message(uid, "❌ لطفاً سن خود را به عدد (بین ۱۱ تا ۸۹) وارد کنید.")
        return

    # ۸. مدیریت چت همزمان (Live Chat)
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        
        if message.text == "🚫 بلاک کردن کاربر":
            if uid not in db["blocks"]: db["blocks"][uid] = []
            db["blocks"][uid].append(partner)
            db["users"][uid].update({"state": "main", "partner": None}); db["users"][partner].update({"state": "main", "partner": None})
            save_db(db)
            bot.send_message(uid, "🚫 کاربر بلاک شد و چت پایان یافت.", reply_markup=main_menu(uid))
            bot.send_message(partner, "⚠️ طرف مقابل چت را ترک کرد و شما را بلاک کرد.", reply_markup=main_menu(partner))
            return
            
        elif message.text == "❌ قطع چت":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن 🔚", callback_data="confirm_end"), types.InlineKeyboardButton("خیر، ادامه بده 🔙", callback_data="cancel_end"))
            bot.send_message(uid, "🤔 **آیا از اتمام چت مطمئن هستید؟**", reply_markup=btn)
            return

        elif message.text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup()
            for r in ["فحش ناموسی 🤬", "تبلیغات", "مزاحمت یا درخواست بد"]: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r[:5]}"))
            bot.send_message(uid, "🚩 **علت گزارش خود را انتخاب کنید:**", reply_markup=btn)
            return

        # فیلتر محتوا
        if message.text and is_bad(message.text):
            bot.delete_message(uid, message.message_id)
            bot.send_message(uid, "⚠️ پیام شما به دلیل استفاده از کلمات نامناسب حذف شد.")
            return

        # ذخیره تاریخچه برای گزارش
        if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
        db["chat_history"][chat_id].append({"u": uid, "t": message.text if message.text else "رسانه"})
        if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
        save_db(db)

        try: bot.copy_message(partner, uid, message.message_id)
        except: pass
        return

    # ۹. دکمه‌های منوی اصلی
    if message.text == "🛰 شروع چت ناشناس":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="hunt_m"), types.InlineKeyboardButton("خانم 👧", callback_data="hunt_f")).add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 **مایل هستید به چه کسی متصل شوید؟**", reply_markup=btn)
    
    elif message.text == "🤫 لینک پیام ناشناس":
        link = user.get("link") or str(random.randint(100000, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🤫 **لینک اختصاصی شما ساخته شد!**\nآن را در بیو اینستاگرام یا کانال خود قرار دهید:\n\n`https://t.me/{bot.get_me().username}?start={link}`")
    
    elif message.text == "👤 پروفایل من":
        sex = "آقا 👦" if user.get("gender")=="male" else "خانم 👧"
        bot.send_message(uid, f"👤 **مشخصات شما:**\n\n🏷 نام: {user['name']}\n👫 جنسیت: {sex}\n🎂 سن: {user.get('age', 'ثبت نشده')}\n🆔 آیدی: `{uid}`")
    
    elif message.text == "❓ راهنمای ربات":
        bot.send_message(uid, "❓ **راهنمای سریع:**\n\n۱. **چت ناشناس:** شما را به صورت تصادفی به یک نفر وصل می‌کند.\n۲. **لینک ناشناس:** دیگران می‌توانند بدون فاش شدن هویتشان به شما پیام دهند.")

    # ۱۰. بخش مدیریت (Admin Panel)
    if uid == OWNER_ID:
        if message.text == "📊 مدیریت و آمار":
            stats = f"📊 **آمار کل ربات:**\n\n👥 تعداد کاربران: {len(db['users'])}\n🚫 تعداد مسدودین: {len(db['banned'])}\n⏳ کاربران در صف: {len(db['queue']['any'])}"
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 دریافت فایل دیتابیس", callback_data="get_db_file"))
            bot.send_message(uid, stats, reply_markup=btn)
        elif message.text == "📢 ارسال همگانی":
            db["users"][uid]["state"] = "admin_bc"; save_db(db)
            bot.send_message(uid, "📝 متن اطلاعیه را بفرستید (برای لغو کلمه 'لغو' را بفرستید):", reply_markup=types.ReplyKeyboardRemove())
        elif user.get("state") == "admin_bc":
            if message.text == "لغو":
                db["users"][uid]["state"] = "main"; save_db(db)
                bot.send_message(uid, "❌ ارسال لغو شد.", reply_markup=main_menu(uid))
            else:
                db["users"][uid]["state"] = "main"; save_db(db)
                for u in db["users"]:
                    try: bot.send_message(u, f"📢 **اطلاعیه از طرف مدیریت:**\n\n{message.text}")
                    except: pass
                bot.send_message(uid, "✅ پیام با موفقیت برای همه ارسال شد.", reply_markup=main_menu(uid))

    # ۱۱. وضعیت نوشتن پیام ناشناس (Confession State)
    elif user.get("state") == "writing_confession" and message.text:
        db["users"][uid].update({"temp_msg": message.text}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال قطعی 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"✅ **پیش‌نمایش پیام شما:**\n\n{message.text}\n\nآیا ارسال شود؟", reply_markup=btn)

# --- مدیریت دکمه‌های شیشه‌ای (Callbacks) ---
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    # تنظیم جنسیت در ثبت‌نام
    if call.data == "set_m":
        db["users"][uid].update({"gender": "male", "state": "reg_age"}); save_db(db)
        bot.edit_message_text("✨ نام کاربری شما تایید شد. حالا **سن** خود را وارد کنید:", uid, call.message.id)
    elif call.data == "set_f":
        db["users"][uid].update({"gender": "female", "state": "reg_age"}); save_db(db)
        bot.edit_message_text("✨ نام کاربری شما تایید شد. حالا **سن** خود را وارد کنید:", uid, call.message.id)
    
    # تایید ارسال پیام ناشناس
    elif call.data == "send_conf":
        u_data = db["users"].get(uid); target = u_data.get("target"); msg = u_data.get("temp_msg")
        if target and msg:
            m_key = f"v_{uid}_{random.randint(1000,9999)}"
            db["anon_msgs"][m_key] = {"from": uid, "msg": msg}; save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 مشاهده پیام ناشناس", callback_data=m_key))
            bot.send_message(target, "📬 **یک پیام ناشناس جدید دریافت کردید!**", reply_markup=btn)
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.edit_message_text("✅ پیام شما با موفقیت ارسال شد.", uid, call.message.id)
            bot.send_message(uid, "🏡 برگشت به منوی اصلی", reply_markup=main_menu(uid))

    elif call.data == "cancel_conf":
        db["users"][uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("❌ ارسال پیام لغو شد.", uid, call.message.id)
        bot.send_message(uid, "🏡 برگشت به منوی اصلی", reply_markup=main_menu(uid))

    # مشاهده پیام ناشناس
    elif call.data.startswith("v_"):
        data = db["anon_msgs"].get(call.data)
        if data:
            bot.edit_message_text(f"📩 **پیام ناشناس رسیده:**\n\n{data['msg']}\n\n💡 برای پاسخ دادن کافیست روی همین پیام **ریپلای** کنید.", uid, call.message.id)
            db["users"][uid]["last_anon_msg_id"] = call.message.id; save_db(db)
            try: bot.send_message(data['from'], "🔔 پیام شما توسط مخاطب خوانده شد.")
            except: pass

    # عملیات مدیریتی بن
    elif call.data.startswith("adm_p_"):
        target = call.data.split("_")[2]
        db["banned"][target] = {"end": "perm"}; save_db(db)
        bot.edit_message_text(f"✅ کاربر {target} به صورت دائمی مسدود شد.", uid, call.message.id)

    elif call.data.startswith("adm_t_"):
        target = call.data.split("_")[2]
        db["users"][uid].update({"state": "waiting_ban_time", "temp_target": target}); save_db(db)
        bot.send_message(uid, f"⏳ مدت زمان مسدودیت برای `{target}` را به **دقیقه** وارد کنید:")

    # گزارش تخلف
    elif call.data.startswith("rep_"):
        reason = call.data.split("_")[1]; partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = db["chat_history"].get(chat_id, [])
        report_text = f"🚩 **گزارش تخلف جدید**\n\nدلیل: {reason}\nشاکی: `{uid}`\nمتهم: `{partner}`\n\n📜 **۱۰ پیام آخر:**\n"
        for h in history: report_text += f"{'متهم' if h['u']==partner else 'شاکی'}: {h['t']}\n"
        
        btn = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("TEMP BAN ⏳", callback_data=f"adm_t_{partner}"),
            types.InlineKeyboardButton("PERM BAN 🚫", callback_data=f"adm_p_{partner}")
        )
        bot.send_message(OWNER_ID, report_text, reply_markup=btn)
        bot.edit_message_text("✅ گزارش شما برای مدیریت ارسال شد.", uid, call.message.id)

    # قطع چت
    elif call.data == "confirm_end":
        partner = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][partner].update({"state": "main", "partner": None})
        save_db(db)
        bot.send_message(uid, "👋 چت پایان یافت.", reply_markup=main_menu(uid))
        bot.send_message(partner, "⚠️ طرف مقابل چت را ترک کرد.", reply_markup=main_menu(partner))

    # سیستم جستجو و اتصال (Matchmaking Logic)
    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        pref_key = "male" if pref=="m" else ("female" if pref=="f" else "any")
        bot.edit_message_text("🔍 **در حال جستجوی هم‌صحبت...**", uid, call.message.id)
        
        my_gender = db["users"][uid].get("gender")
        potential_matches = []
        
        # ترکیب صف‌ها برای یافتن بهترین مورد
        search_pool = db["queue"]["any"] + db["queue"][my_gender]
        for p_uid in search_pool:
            if p_uid == uid or p_uid in db["blocks"].get(uid, []): continue
            p_user = db["users"][p_uid]
            # بررسی تطابق جنسیت دو طرفه
            if pref_key == "any" or p_user["gender"] == pref_key:
                potential_matches.append(p_uid)
        
        if potential_matches:
            match = potential_matches[0]
            # حذف از تمام صف‌ها
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 **متصل شدید!**\nهم‌اکنون می‌توانید گفتگو کنید.", reply_markup=chat_menu())
            bot.send_message(match, "💎 **متصل شدید!**\nهم‌اکنون می‌توانید گفتگو کنید.", reply_markup=chat_menu())
        else:
            if uid not in db["queue"][pref_key]:
                db["queue"][pref_key].append(uid)
                save_db(db)
            bot.send_message(uid, "⌛️ **کسی در صف نبود.**\nبه محض یافتن هم‌صحبت، به شما اطلاع می‌دهیم...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("انصراف از صف ❌", callback_data="cancel_search")))

    elif call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(OWNER_ID, f)

# --- اجرای نهایی ربات ---
if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
