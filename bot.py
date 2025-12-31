import telebot
from telebot import types
import json, os, random, datetime, re, time
from flask import Flask
from threading import Thread

# --- سامانه پایداری و میزبانی ---
app = Flask('')
@app.route('/')
def home(): return "Shadow Chat Bot is active."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات و دیتابیس ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_data.json"

BAD_WORDS = ["مادرجنده", "کص ننت", "کون", "کص", "کیر", "جنده", "ناموس", "بی‌ناموس", "کونی", "جنده‌خونه", "لاشی", "خایه"] 
user_last_msg_time = {}

def get_db():
    if not os.path.exists(DB_PATH): 
        db = {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}, "blocks": {}}
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "blocks" not in data: data["blocks"] = {}
            if "chat_history" not in data: data["chat_history"] = {}
            if "anon_msgs" not in data: data["anon_msgs"] = {}
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

# --- کیبوردهای اختصاصی ---
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

# --- پردازشگر اصلی پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    
    # ۱. فیلتر مسدودیت
    if uid in db.get("banned", {}):
        expire = db["banned"][uid]['end']
        if expire == "perm" or datetime.datetime.now() < datetime.datetime.fromisoformat(expire):
            bot.send_message(uid, "🚫 **دسترسی شما قطع شده است!**\nحساب کاربری شما به دلیل رعایت نکردن قوانین مسدود می‌باشد.")
            return

    # ۲. عضویت اجباری
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("عضویت در کانال خبررسانی 📢", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        bot.send_message(uid, "👋 **خوش آمدی همسفر!**\nبرای استفاده از قابلیت‌های چت و پیام ناشناس، ابتدا در کانال ما عضو شو و سپس مجدد تلاش کن:", reply_markup=btn)
        return

    # ۳. ضد اسپم هوشمند
    now = time.time()
    if uid in user_last_msg_time and now - user_last_msg_time[uid] < 0.8:
        bot.send_message(uid, "⚠️ **آرام‌تر!** ربات برای پردازش دقیق نیاز به زمان دارد. لطفاً پیام‌ها را پشت سر هم ارسال نکنید.")
        return
    user_last_msg_time[uid] = now

    user = db["users"].get(uid)

    # ۴. رفع باگ بن موقت (اولویت ادمین برای جلوگیری از قفل شدن)
    if uid == OWNER_ID and user and user.get("state") == "waiting_ban_time":
        if message.text and message.text.isdigit():
            target = user.get("temp_target")
            expire = (datetime.datetime.now() + datetime.timedelta(minutes=int(message.text))).isoformat()
            db["banned"][target] = {"end": expire, "reason": "تخلف گزارش شده"}
            db["users"][uid]["state"] = "main"
            save_db(db)
            bot.send_message(uid, f"✅ کاربر {target} برای {message.text} دقیقه مسدود شد.", reply_markup=main_menu(uid))
            try: bot.send_message(target, f"⏳ حساب شما برای {message.text} دقیقه مسدود شد.")
            except: pass
            return
        elif message.text: # اگر دکمه زد یا متن فرستاد و عدد نبود
            db["users"][uid]["state"] = "main"; save_db(db)

    # ۵. استارت و ورودی‌های لینک پیام ناشناس
    if message.text and message.text.startswith("/start"):
        args = message.text.split()
        if len(args) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}
                save_db(db)
                bot.send_message(uid, "✨ **سلام! به ایستگاه ناشناس خوش آمدی.**\nابتدا یک نام مستعار (حداکثر ۲۰ حرف) برای خودت انتخاب و ارسال کن:")
                return
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.send_message(uid, "💎 **به خانه خوش آمدی!**\nاز منوی زیر یکی از گزینه‌ها را برای شروع انتخاب کن:", reply_markup=main_menu(uid))
            return
        else:
            code = args[1]
            target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
            if target == uid: bot.send_message(uid, "🙄 شما نمی‌توانید برای خودتان پیام ناشناس ارسال کنید!"); return
            if target:
                db["users"][uid] = db["users"].get(uid, {"state": "main"})
                db["users"][uid].update({"state": "writing_confession", "target": target})
                save_db(db)
                bot.send_message(uid, "📝 **در حال آماده‌سازی پیام برای یک ناشناس...**\nهر چه در دل داری بنویس، هویت تو مخفی می‌ماند:", reply_markup=types.ReplyKeyboardRemove())
                return

    if not user: return

    # ۶. سیستم ریپلای ناشناس (با رفع باگ تاییدیه)
    if message.reply_to_message:
        target_uid = next((u_id for u_id, u_data in db["users"].items() if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            db["users"][uid].update({"state": "writing_confession", "target": target_uid, "temp_msg": message.text})
            save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال قطعی 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
            bot.send_message(uid, f"✅ **پیش‌نمایش پاسخ شما:**\n\n{message.text}\n\nآیا از ارسال آن اطمینان دارید؟", reply_markup=btn)
            return

    # ۷. مراحل ثبت‌نام
    if user["state"] == "reg_name":
        db["users"][uid].update({"name": message.text[:20], "state": "reg_gender"})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="set_m"), types.InlineKeyboardButton("خانم 👧", callback_data="set_f"))
        bot.send_message(uid, f"✨ **بسیار عالی، {message.text}!**\nحالا جنسیت خودت رو مشخص کن:", reply_markup=btn)
        return
    elif user["state"] == "reg_age":
        if message.text and message.text.isdigit():
            db["users"][uid].update({"age": message.text, "state": "main"})
            save_db(db)
            bot.send_message(uid, "🎉 **تبریک! پروفایل تو تکمیل شد.**", reply_markup=main_menu(uid))
        return

    # ۸. مدیریت چت زنده
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        if message.text == "🚫 بلاک کردن کاربر":
            if uid not in db["blocks"]: db["blocks"][uid] = []
            db["blocks"][uid].append(partner)
            db["users"][uid].update({"state": "main", "partner": None}); db["users"][partner].update({"state": "main", "partner": None})
            save_db(db); bot.send_message(uid, "🚫 کاربر بلاک شد.", reply_markup=main_menu(uid)); bot.send_message(partner, "⚠️ ارتباط قطع شد.", reply_markup=main_menu(partner))
            return
        elif message.text == "❌ قطع چت":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله 🔚", callback_data="confirm_end"), types.InlineKeyboardButton("خیر 🔙", callback_data="cancel_end"))
            bot.send_message(uid, "🤔 مطمئنی؟", reply_markup=btn); return
        elif message.text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup()
            for r in ["فحش ناموسی 🤬", "تبلیغات", "مزاحمت"]: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r[:5]}"))
            bot.send_message(uid, "🚩 علت گزارش:", reply_markup=btn); return
        
        if message.text and is_bad(message.text):
            bot.delete_message(uid, message.message_id)
            bot.send_message(uid, "⚠️ پیام شما حاوی کلمات نامناسب بود.")
            return

        if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
        db["chat_history"][chat_id].append({"u": uid, "val": message.text if message.text else "رسانه"})
        if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
        save_db(db)

        try: bot.copy_message(partner, uid, message.message_id)
        except: pass
        return

    # ۹. منوی اصلی
    if message.text == "🛰 شروع چت ناشناس":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="hunt_m"), types.InlineKeyboardButton("خانم 👧", callback_data="hunt_f")).add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 **دنبال چه هم‌صحبتی می‌گردی؟**", reply_markup=btn)
    elif message.text == "🤫 لینک پیام ناشناس":
        link = user.get("link") or str(random.randint(100000, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🤫 **لینک اختصاصی تو ساخته شد!**\n`https://t.me/{bot.get_me().username}?start={link}`")
    elif message.text == "👤 پروفایل من":
        sex = "آقا 👦" if user.get("gender")=="male" else "خانم 👧"
        bot.send_message(uid, f"👤 **مشخصات شما:**\n🏷 نام: {user['name']}\n👫 جنسیت: {sex}\n🆔 آیدی: `{uid}`")
    elif message.text == "❓ راهنمای ربات":
        bot.send_message(uid, "🛠 **راهنما:**\n۱. چت ناشناس: وصل شدن به افراد تصادفی\n۲. لینک ناشناس: دریافت پیام در صندوق مخفی")
    elif message.text == "📊 مدیریت و آمار" and uid == OWNER_ID:
        stats = f"📊 آمار:\n👥 کاربران: {len(db['users'])}\n⏳ در صف: {len(db['queue']['any'])}"
        bot.send_message(uid, stats, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 دریافت دیتابیس", callback_data="get_db_file")))
    elif message.text == "📢 ارسال همگانی" and uid == OWNER_ID:
        db["users"][uid]["state"] = "admin_bc"; save_db(db)
        bot.send_message(uid, "📝 متن اطلاعیه را بفرستید:", reply_markup=types.ReplyKeyboardRemove())
    elif user.get("state") == "admin_bc" and uid == OWNER_ID:
        db["users"][uid]["state"] = "main"; save_db(db)
        for u in db["users"]:
            try: bot.send_message(u, f"📢 **اطلاعیه:**\n\n{message.text}")
            except: pass
        bot.send_message(uid, "✅ ارسال شد.", reply_markup=main_menu(uid))

    # ۱۰. وضعیت نوشتن پیام ناشناس اولیه
    elif user.get("state") == "writing_confession" and message.text:
        db["users"][uid].update({"temp_msg": message.text}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال قطعی 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"✅ **پیش‌نمایش پیام:**\n\n{message.text}\n\nارسال شود؟", reply_markup=btn)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    if call.data == "send_conf":
        u_data = db["users"].get(uid); target = u_data.get("target"); msg = u_data.get("temp_msg")
        if target and msg:
            mkey = f"v_{uid}_{random.randint(100,999)}"
            db["anon_msgs"][mkey] = {"m": msg, "f": uid}; save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 مشاهده پیام", callback_data=mkey))
            bot.send_message(target, "📬 **یک پیام ناشناس جدید داری!**", reply_markup=btn)
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.edit_message_text("✅ **پیام تو با موفقیت ارسال شد.**", uid, call.message.id)
            bot.send_message(uid, "🏡 بازگشت به منوی اصلی", reply_markup=main_menu(uid))

    elif call.data == "cancel_conf":
        db["users"][uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("❌ **ارسال پیام لغو شد.**", uid, call.message.id)
        bot.send_message(uid, "🏡 بازگشت به منوی اصلی", reply_markup=main_menu(uid))

    elif call.data.startswith("v_"):
        data = db["anon_msgs"].get(call.data)
        if data:
            bot.edit_message_text(f"📩 **پیام ناشناس رسیده:**\n\n{data['m']}\n\n💡 برای پاسخ کافیست ریپلای کنید.", uid, call.message.id)
            db["users"][uid]["last_anon_msg_id"] = call.message.id; save_db(db)
            try: bot.send_message(data['f'], "🔔 ناشناس پیام شما را مشاهده کرد.")
            except: pass

    elif call.data.startswith("adm_p_"):
        target = call.data.split("_")[2]
        db["banned"][target] = {"end": "perm"}; save_db(db)
        bot.edit_message_text(f"✅ کاربر {target} دائمی مسدود شد.", uid, call.message.id)

    elif call.data.startswith("adm_t_"):
        target = call.data.split("_")[2]
        db["users"][uid].update({"state": "waiting_ban_time", "temp_target": target}); save_db(db)
        bot.send_message(uid, f"⏳ زمان بن (دقیقه) برای `{target}`:")

    elif call.data.startswith("rep_"):
        reason = call.data.split("_")[1]; partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = db["chat_history"].get(chat_id, [])
        report = f"🚩 گزارش تخلف\nدلیل: {reason}\nمتهم: `{partner}`\n📜 تاریخچه:\n"
        for h in history: report += f"{'[متهم]' if h['u']==partner else '[شاکی]'}: {h['val']}\n"
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("TEMP BAN ⏳", callback_data=f"adm_t_{partner}"), types.InlineKeyboardButton("PERM BAN 🚫", callback_data=f"adm_p_{partner}"))
        bot.send_message(OWNER_ID, report, reply_markup=btn)
        bot.edit_message_text("✅ گزارش ارسال شد.", uid, call.message.id)

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None}); db["users"][p].update({"state": "main", "partner": None}); save_db(db)
        bot.send_message(uid, "👋 چت قطع شد.", reply_markup=main_menu(uid)); bot.send_message(p, "⚠️ چت قطع شد.", reply_markup=main_menu(p))

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]; pref_key = "male" if pref=="m" else ("female" if pref=="f" else "any")
        bot.edit_message_text("🔍 **در حال جستجو...**", uid, call.message.id)
        my_g = db["users"][uid].get("gender"); target_pool = db["queue"]["any"] + db["queue"][my_g]
        match = next((u for u in target_pool if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key) and u not in db["blocks"].get(uid, [])), None)
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match}); db["users"][match].update({"state": "in_chat", "partner": uid}); save_db(db)
            bot.send_message(uid, "💎 متصل شدی!", reply_markup=chat_menu()); bot.send_message(match, "💎 متصل شدی!", reply_markup=chat_menu())
        else:
            if uid not in db["queue"][pref_key]: db["queue"][pref_key].append(uid); save_db(db)
            bot.send_message(uid, "⌛️ در صف انتظار...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("انصراف ❌", callback_data="cancel_search")))

    elif call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(OWNER_ID, f)

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
