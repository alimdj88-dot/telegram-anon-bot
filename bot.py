import telebot
from telebot import types
import json, os, random, datetime, re, time
from flask import Flask
from threading import Thread

# --- ایجاد سرور برای جلوگیری از غیرفعال شدن ---
app = Flask('')
@app.route('/')
def home(): return "Robot is Online and Protecting Data"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات ربات ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_data.json"

# لیست سیاه کلمات (تقویت شده با کلمات ناموسی)
BAD_WORDS = ["مادرجنده", "کص ننت", "کون", "کص", "کیر", "جنده", "ناموس", "بی‌ناموس"] 

# دیکشنری برای کنترل اسپم
user_last_msg_time = {}

def get_db():
    if not os.path.exists(DB_PATH): 
        db = {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}}
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "banned" not in data: data["banned"] = {}
            if "chat_history" not in data: data["chat_history"] = {}
            return data
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def clean_text(text):
    if not text: return ""
    return re.sub(r'[.\s\-_*+]+', '', text)

def is_bad(text):
    cleaned = clean_text(text)
    for w in BAD_WORDS:
        if w in cleaned and w != "": return True
    return False

def check_sub(uid):
    if str(uid) == OWNER_ID: return True
    try:
        s = bot.get_chat_member(CHANNEL_ID, int(uid)).status
        return s in ['member', 'administrator', 'creator']
    except: return False

def is_banned(uid, db):
    if uid in db["banned"]:
        info = db["banned"][uid]
        if info['end'] == "perm": return True
        expire = datetime.datetime.fromisoformat(info['end'])
        if datetime.datetime.now() < expire: return True
        else:
            del db["banned"][uid]; save_db(db)
    return False

# --- کیبوردهای اصلی ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛰 شروع چت ناشناس", "🤫 لینک پیام ناشناس")
    markup.add("👤 پروفایل من", "❓ راهنمای ربات")
    if str(uid) == OWNER_ID: markup.add("📢 ارسال همگانی", "📊 مدیریت و آمار")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("❌ قطع چت", "🚩 گزارش تخلف")
    return markup

@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    
    # ۱. چک کردن بن بودن
    if is_banned(uid, db):
        bot.send_message(uid, "🚫 حساب شما به دلیل نقض قوانین ربات مسدود شده است.")
        return

    # ۲. چک کردن عضویت اجباری
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("عضویت در کانال 📢", url="https://t.me/ChatNaAnnouncements"))
        bot.send_message(uid, "👋 برای استفاده از ربات چت ناشناس، ابتدا در کانال ما عضو شوید:", reply_markup=btn)
        return

    # ۳. سیستم ضد اسپم
    now = time.time()
    if uid in user_last_msg_time and now - user_last_msg_time[uid] < 0.7:
        bot.send_message(uid, "⚠️ سرعت ارسال پیام شما بسیار زیاد است. لطفاً کمی صبر کنید.")
        user_last_msg_time[uid] = now
        return
    user_last_msg_time[uid] = now

    # ۴. فیلتر کلمات زشت
    if message.text and is_bad(message.text):
        bot.delete_message(uid, message.message_id)
        bot.send_message(uid, "⚠️ پیام شما حاوی کلمات غیراخلاقی بود و حذف شد. تکرار باعث مسدودیت می‌شود.")
        bot.send_message(OWNER_ID, f"🚫 **گزارش تخلف خودکار:**\nکاربر: `{uid}`\nمتن: {message.text}")
        return

    # ۵. مدیریت ادمین برای بن عددی
    user_state = db["users"].get(uid, {}).get("state")
    if uid == OWNER_ID and user_state == "waiting_ban_time":
        if message.text.isdigit():
            target = db["users"][uid]["temp_target"]
            expire = (datetime.datetime.now() + datetime.timedelta(minutes=int(message.text))).isoformat()
            db["banned"][target] = {"end": expire, "reason": db["users"][uid]["temp_reason"]}
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.send_message(OWNER_ID, f"✅ کاربر {target} با موفقیت بن شد.", reply_markup=main_menu(uid))
            bot.send_message(target, f"⏳ حساب شما به مدت {message.text} دقیقه مسدود شد.")
            return

    # ۶. دستور استارت و لینک ناشناس
    if message.text and message.text.startswith("/start"):
        if uid in db["users"] and db["users"][uid].get("state") == "in_chat":
            bot.send_message(uid, "🕯 شما در حال چت هستید. ابتدا دکمه قطع چت را بزنید."); return
        
        args = message.text.split()
        if len(args) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}; save_db(db)
                bot.send_message(uid, "سلام! به ربات پیام ناشناس خوش آمدی.\nلطفاً یک نام مستعار برای خودت انتخاب کن:"); return
            bot.send_message(uid, "به منوی اصلی ربات خوش آمدی. از دکمه‌های زیر استفاده کن:", reply_markup=main_menu(uid)); return
        else:
            code = args[1]
            target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
            if target == uid:
                bot.send_message(uid, "❌ شما نمی‌توانید به خودتان پیام ناشناس بفرستید!"); return
            if target:
                db["users"][uid] = db["users"].get(uid, {"state": "main"})
                db["users"][uid].update({"state": "writing_confession", "target": target}); save_db(db)
                bot.send_message(uid, "📝 در حال ارسال پیام ناشناس... هر چه در دل داری بنویس تا به دستش برسانم (هویت تو کاملاً مخفی می‌ماند):", reply_markup=types.ReplyKeyboardRemove()); return

    user = db["users"].get(uid)
    if not user: return

    # ۷. مدیریت چت زنده (دو نفره)
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
        
        # ثبت تاریخچه برای گزارش ادمین
        val = message.text if message.text else (message.json.get(message.content_type).get('file_id') if isinstance(message.json.get(message.content_type), dict) else message.json.get(message.content_type)[-1].get('file_id'))
        db["chat_history"][chat_id].append({"u": uid, "type": message.content_type, "val": val})
        if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
        save_db(db)

        if message.text == "❌ قطع چت":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن", callback_data="confirm_end"), types.InlineKeyboardButton("نه، ادامه بده", callback_data="cancel_end"))
            bot.send_message(uid, "آیا مطمئن هستی که می‌خواهی این چت را تمام کنی؟", reply_markup=btn)
        elif message.text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=2)
            for r in ["فحش ناموسی 🤬", "محتوای 🔞", "مزاحمت", "تبلیغات", "سایر موارد"]: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r}"))
            bot.send_message(uid, "دلیل گزارش تخلف طرف مقابل چیست؟", reply_markup=btn)
        else:
            try: bot.copy_message(partner, uid, message.message_id)
            except: bot.send_message(uid, "⚠️ پیام ارسال نشد. احتمالاً طرف مقابل ربات را متوقف کرده است.")
        return

    # ۸. پاسخ (Reply) به پیام ناشناس
    if message.reply_to_message:
        target_uid = next((u_id for u_id, u_data in db["users"].items() if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            bot.send_message(target_uid, "💬 **یک پاسخ جدید برای پیام ناشناس شما دریافت شد:**")
            sent = bot.copy_message(target_uid, uid, message.message_id)
            db["users"][target_uid]["last_anon_msg_id"] = sent.message_id; save_db(db)
            bot.send_message(uid, "✅ پاسخ شما با موفقیت ارسال شد."); return

    # ۹. مدیریت دکمه‌های منو
    if message.text == "🛰 شروع چت ناشناس":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="hunt_m"), types.InlineKeyboardButton("خانم 👧", callback_data="hunt_f")).add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "دوست داری با چه جنسیتی هم‌کلام شوی؟", reply_markup=btn)
    elif message.text == "🤫 لینک پیام ناشناس":
        link = user.get("link") or str(random.randint(100000, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🔗 لینک اختصاصی شما برای دریافت پیام ناشناس:\nhttps://t.me/{bot.get_me().username}?start={link}\n\nاین لینک را در بیو اینستاگرام یا کانال خود قرار دهید.")
    elif message.text == "👤 پروفایل من":
        sex = "آقا 👦" if user.get("gender") == "male" else "خانم 👧"
        bot.send_message(uid, f"👤 نام: {user['name']}\n🎂 سن: {user.get('age', 'ثبت نشده')}\n👫 جنسیت: {sex}")
    elif message.text == "❓ راهنمای ربات":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("چطور چت کنم؟ 🛠", callback_data="guide_how"))
        btn.add(types.InlineKeyboardButton("سیستم امنیت و فیلتر 🛡", callback_data="guide_security"))
        btn.add(types.InlineKeyboardButton("قوانین ربات ⚖️", callback_data="guide_rules"))
        bot.send_message(uid, "کدام بخش را برایت توضیح دهم؟", reply_markup=btn)
    
    # ۱۰. پنل ادمین
    elif uid == OWNER_ID:
        if message.text == "📢 ارسال همگانی":
            db["users"][uid]["state"] = "admin_bc"; save_db(db)
            bot.send_message(uid, "لطفاً متن پیام تبلیغاتی یا اطلاعیه خود را بفرستید:", reply_markup=types.ReplyKeyboardRemove())
        elif user.get("state") == "admin_bc":
            db["users"][uid]["state"] = "main"; save_db(db)
            count = 0
            for u in db["users"]:
                try: bot.send_message(u, f"📢 **پیام مدیریت ربات:**\n\n{message.text}"); count += 1
                except: pass
            bot.send_message(uid, f"✅ پیام برای {count} نفر با موفقیت ارسال شد.", reply_markup=main_menu(uid))
        elif message.text == "📊 مدیریت و آمار":
            stats = f"📊 **آمار ربات:**\n\nکل کاربران: {len(db['users'])}\nتعداد بن شده‌ها: {len(db['banned'])}"
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 دریافت فایل دیتابیس", callback_data="get_db_file"))
            btn.add(types.InlineKeyboardButton("🚫 مدیریت لیست سیاه", callback_data="manage_banned"))
            bot.send_message(uid, stats, reply_markup=btn)

    # ۱۱. مراحل ثبت‌نام (Name, Gender, Age)
    elif user["state"] == "reg_name":
        db["users"][uid].update({"name": message.text[:20], "state": "reg_gender"}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="set_m"), types.InlineKeyboardButton("خانم 👧", callback_data="set_f"))
        bot.send_message(uid, "جنسیت خود را انتخاب کنید:", reply_markup=btn)
    elif user["state"] == "reg_age" and message.text.isdigit():
        db["users"][uid].update({"age": message.text, "state": "main"}); save_db(db)
        bot.send_message(uid, "خیلی خوش آمدی! ثبت‌نام تو تکمیل شد.", reply_markup=main_menu(uid))
    elif user.get("state") == "writing_confession" and message.text:
        db["users"][uid].update({"state": "main", "temp_msg": message.text}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال پیام 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"متن پیام شما:\n{message.text}\n\nارسال شود؟", reply_markup=btn)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    # بخش راهنما
    if call.data.startswith("guide_"):
        res = ""
        if "how" in call.data: res = "شما می‌توانید با زدن دکمه 'شروع چت'، به طور تصادفی به یک نفر وصل شوید. هویت شما برای او و هویت او برای شما کاملاً مخفی است."
        elif "security" in call.data: res = "ربات مجهز به آنالیزور کلمات زشت و محتوای غیراخلاقی است. ارسال عکس‌های نامناسب یا فحش ناموسی باعث ارسال گزارش مستقیم به ادمین و مسدود شدن دائم حساب شما می‌گردد."
        elif "rules" in call.data: res = "۱. ادب را رعایت کنید.\n۲. از ارسال محتوای +18 خودداری کنید.\n۳. مزاحمت برای کاربران پیگرد دارد."
        bot.edit_message_text(res, uid, call.message.id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بازگشت 🔙", callback_data="back_guide")))

    elif call.data == "back_guide":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("چطور چت کنم؟ 🛠", callback_data="guide_how")).add(types.InlineKeyboardButton("امنیت و فیلتر 🛡", callback_data="guide_security")).add(types.InlineKeyboardButton("قوانین ربات ⚖️", callback_data="guide_rules"))
        bot.edit_message_text("کدام بخش را برایت توضیح دهم؟", uid, call.message.id, reply_markup=btn)

    # بخش گزارش تخلف و مدیریت ادمین
    elif call.data.startswith("rep_"):
        reason = call.data.split("_")[1]; partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = db["chat_history"].get(chat_id, [])
        report = f"🚩 **گزارش تخلف جدید**\nدلیل: {reason}\nخاطی: `{partner}`\n\n📜 **آخرین پیام‌های متنی:**\n"
        for h in history: 
            if h['u'] == partner and h['type'] == 'text': report += f"- {h['val']}\n"
        
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("TEMP BAN ⏳", callback_data=f"adm_t_{partner}"), types.InlineKeyboardButton("PERM BAN 🚫", callback_data=f"adm_p_{partner}"))
        btn.add(types.InlineKeyboardButton("IGNORE ✅", callback_data="adm_ignore"))
        bot.send_message(OWNER_ID, report, reply_markup=btn)
        # ارسال فایل‌های مدیا به ادمین
        for h in history:
            if h['u'] == partner and h['type'] != 'text': bot.copy_message(OWNER_ID, partner, call.message.id)
        bot.edit_message_text("✅ گزارش شما ارسال شد و ادمین‌ها در حال بررسی هستند.", uid, call.message.id)

    elif call.data == "adm_ignore": bot.edit_message_text("✅ این گزارش نادیده گرفته شد.", uid, call.message.id)

    elif call.data.startswith("adm_t_"):
        target = call.data.split("_")[2]
        db["users"][OWNER_ID].update({"state": "waiting_ban_time", "temp_target": target, "temp_reason": "تخلف در چت"}); save_db(db)
        bot.send_message(OWNER_ID, "مدت زمان بن را به **دقیقه** وارد کن (فقط عدد):")

    elif call.data.startswith("adm_p_"):
        target = call.data.split("_")[2]
        db["banned"][target] = {"end": "perm", "reason": "نقض قوانین"}; save_db(db)
        bot.send_message(OWNER_ID, "✅ کاربر دائم بن شد."); bot.send_message(target, "🚫 حساب شما برای همیشه مسدود شد.")

    elif call.data == "manage_banned":
        if not db["banned"]: bot.answer_callback_query(call.id, "لیست سیاه خالی است."); return
        for tid, info in db["banned"].items():
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("UNBAN 🔓", callback_data=f"unban_{tid}"))
            bot.send_message(OWNER_ID, f"کاربر: `{tid}`\nدلیل: {info['reason']}\nپایان: {info['end']}", reply_markup=btn)

    elif call.data.startswith("unban_"):
        tid = call.data.split("_")[1]
        if tid in db["banned"]: del db["banned"][tid]; save_db(db)
        bot.edit_message_text("✅ کاربر بخشیده شد.", uid, call.message.id)

    # جستجوی چت و موارد دیگر
    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]; pref_key = "male" if pref=="m" else ("female" if pref=="f" else "any")
        bot.edit_message_text("🔍 در حال جستجوی هم‌صحبت... لطفاً از ربات خارج نشوید.", uid, call.message.id)
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        my_g = db["users"][uid].get("gender")
        target_pool = db["queue"]["any"] + db["queue"][my_g]
        match = next((u for u in target_pool if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key)), None)
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match}); db["users"][match].update({"state": "in_chat", "partner": uid}); save_db(db)
            bot.send_message(uid, "💎 به یک نفر متصل شدی! می‌توانی چت را شروع کنی.", reply_markup=chat_menu())
            bot.send_message(match, "💎 به یک نفر متصل شدی! می‌توانی چت را شروع کنی.", reply_markup=chat_menu())
        else:
            db["queue"][pref_key].append(uid); save_db(db)
            bot.send_message(uid, "⌛️ کاربری پیدا نشد. شما در صف انتظار هستید، به محض آنلاین شدن نفر جدید، چت به صورت خودکار شروع می‌شود.", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("انصراف از صف ❌", callback_data="cancel_search")))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None}); db["users"][p].update({"state": "main", "partner": None}); save_db(db)
        bot.send_message(uid, "چت قطع شد.", reply_markup=main_menu(uid)); bot.send_message(p, "طرف مقابل چت را قطع کرد.", reply_markup=main_menu(p))

    elif call.data == "send_conf":
        target = db["users"][uid].get("target"); msg = db["users"][uid].get("temp_msg")
        mkey = f"view_msg_{uid}_{random.randint(1000,9999)}"
        db["anon_msgs"][mkey] = msg; db["users"][uid]["state"] = "main"; save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("مشاهده پیام 📥", callback_data=mkey))
        bot.send_message(target, "📬 یک پیام ناشناس جدید داری!", reply_markup=btn)
        bot.edit_message_text("✅ پیام شما با موفقیت ارسال شد.", uid, call.message.id); bot.send_message(uid, "به منوی اصلی برگشتید.", reply_markup=main_menu(uid))

    elif call.data.startswith("view_msg_"):
        msg = db["anon_msgs"].get(call.data)
        if msg:
            bot.edit_message_text(f"📩 پیام ناشناس رسیده:\n\n{msg}\n\n💡 برای پاسخ دادن کافیست روی همین پیام ریپلای کنید.", uid, call.message.id)
            db["users"][uid]["last_anon_msg_id"] = call.message.id; save_db(db)
            try: bot.send_message(call.data.split("_")[2], "👁 پیام شما توسط گیرنده خوانده شد.")
            except: pass

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"}); save_db(db)
        bot.edit_message_text("حالا سن خود را به عدد (مثلاً 20) وارد کن:", uid, call.message.id)

    elif call.data == "cancel_search":
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        save_db(db); bot.edit_message_text("از صف انتظار خارج شدی.", uid, call.message.id); bot.send_message(uid, "منوی اصلی:", reply_markup=main_menu(uid))

    elif call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(OWNER_ID, f)

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
