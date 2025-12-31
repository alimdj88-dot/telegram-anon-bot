import telebot
from telebot import types
import json, os, random, datetime, re, time
from flask import Flask
from threading import Thread

# --- سامانه پایداری ربات ---
app = Flask('')
@app.route('/')
def home(): return "Robot is active and monitoring data."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات و متغیرهای اصلی ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_data.json"

BAD_WORDS = ["مادرجنده", "کص ننت", "کون", "کص", "کیر", "جنده", "ناموس", "بی‌ناموس"] 
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
            return data
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}, "blocks": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def is_bad(text):
    if not text: return False
    # حذف تمام فواصل و کاراکترهای مخفی برای جلوگیری از دور زدن فیلتر
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

# --- طراحی کیبوردهای بصری ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛰 شروع چت ناشناس", "🤫 لینک پیام ناشناس")
    markup.add("👤 پروفایل من", "❓ راهنمای ربات")
    if str(uid) == OWNER_ID: markup.add("📢 ارسال همگانی", "📊 مدیریت و آمار")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("❌ قطع چت", "🚩 گزارش تخلف")
    markup.add("🚫 بلاک کردن کاربر")
    return markup

@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    
    # بررسی مسدودیت سراسری
    if uid in db.get("banned", {}):
        expire = db["banned"][uid]['end']
        if expire == "perm" or datetime.datetime.now() < datetime.datetime.fromisoformat(expire):
            bot.send_message(uid, "🚫 **دسترسی شما قطع شده است!**\nحساب کاربری شما به دلیل رعایت نکردن قوانین مسدود می‌باشد.")
            return

    # بررسی عضویت اجباری
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("عضویت در کانال خبررسانی 📢", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        bot.send_message(uid, "👋 **خوش آمدی همسفر!**\nبرای استفاده از قابلیت‌های چت و پیام ناشناس، ابتدا در کانال ما عضو شو و سپس مجدد تلاش کن:", reply_markup=btn)
        return

    # سیستم ضد اسپم هوشمند
    now = time.time()
    if uid in user_last_msg_time and now - user_last_msg_time[uid] < 0.8:
        bot.delete_message(uid, message.message_id)
        bot.send_message(uid, "⚠️ **آرام‌تر!** ربات برای پردازش دقیق نیاز به زمان دارد. لطفاً پیام‌ها را پشت سر هم ارسال نکنید.")
        return
    user_last_msg_time[uid] = now

    # هندلر دستور استارت و ورود با لینک
    if message.text and message.text.startswith("/start"):
        args = message.text.split()
        if len(args) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}
                save_db(db)
                bot.send_message(uid, "✨ **سلام! به ایستگاه ناشناس خوش آمدی.**\nابتدا یک نام مستعار (حداکثر ۲۰ حرف) برای خودت انتخاب و ارسال کن:")
                return
            bot.send_message(uid, "💎 **به منوی اصلی خوش آمدی!**\nچه کاری برایت انجام دهم؟", reply_markup=main_menu(uid))
            return
        else:
            code = args[1]
            target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
            if target == uid: bot.send_message(uid, "🙄 **شوخی می‌کنی؟** شما نمی‌توانید برای خودتان پیام ناشناس ارسال کنید!"); return
            if target:
                db["users"][uid] = db["users"].get(uid, {"state": "main"})
                db["users"][uid].update({"state": "writing_confession", "target": target})
                save_db(db)
                bot.send_message(uid, "📝 **در حال آماده‌سازی پیام برای یک ناشناس...**\nهر چه در دل داری بنویس، هویت تو برای او مثل یک راز باقی می‌ماند:", reply_markup=types.ReplyKeyboardRemove())
                return

    user = db["users"].get(uid)
    if not user: return

    # --- اصلاح شده: لایه اولویت ثبت‌نام ---
    if user["state"] == "reg_name":
        if not message.text or len(message.text) > 20:
            bot.send_message(uid, "❌ **نام نامعتبر!** لطفا فقط یک نام متنی کوتاه ارسال کن.")
            return
        db["users"][uid].update({"name": message.text, "state": "reg_gender"})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="set_m"), types.InlineKeyboardButton("خانم 👧", callback_data="set_f"))
        bot.send_message(uid, f"✨ **بسیار عالی، {message.text}!**\nحالا جنسیت خودت رو مشخص کن تا هم‌صحبت‌های بهتری برات پیدا کنیم:", reply_markup=btn)
        return

    elif user["state"] == "reg_age":
        if message.text and message.text.isdigit() and 10 < int(message.text) < 95:
            db["users"][uid].update({"age": message.text, "state": "main"})
            save_db(db)
            bot.send_message(uid, "🎉 **تبریک! پروفایل تو تکمیل شد.**\nحالا می‌توانی از تمام امکانات ربات استفاده کنی.", reply_markup=main_menu(uid))
        else: bot.send_message(uid, "❌ **سن نامعتبر!** لطفاً سن خود را به صورت عدد (بین ۱۱ تا ۹۴) وارد کنید.")
        return

    # --- لایه مدیریت چت زنده ---
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        
        if message.text == "🚫 بلاک کردن کاربر":
            if uid not in db["blocks"]: db["blocks"][uid] = []
            db["blocks"][uid].append(partner)
            db["users"][uid].update({"state": "main", "partner": None})
            db["users"][partner].update({"state": "main", "partner": None})
            save_db(db)
            bot.send_message(uid, "🚫 **کاربر بلاک شد!**\nاین شخص دیگر هرگز در جستجوها به تو وصل نخواهد شد.", reply_markup=main_menu(uid))
            bot.send_message(partner, "⚠️ **طرف مقابل چت را ترک کرد و ارتباط قطع شد.**", reply_markup=main_menu(partner))
            return
            
        if message.text == "❌ قطع چت":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن 🔚", callback_data="confirm_end"), types.InlineKeyboardButton("خیر، ادامه بده 🔙", callback_data="cancel_end"))
            bot.send_message(uid, "🤔 **مطمئنی می‌خوای این گفتگو رو همین‌جا تموم کنی؟**", reply_markup=btn)
            return

        if message.text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=2)
            reasons = ["فحش ناموسی 🤬", "محتوای غیراخلاقی 🔞", "مزاحمت و توهین", "تبلیغات"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r[:5]}"))
            bot.send_message(uid, "🚩 **چه تخلفی مشاهده کردید؟**\nگزارش شما مستقیماً توسط ادمین بررسی می‌شود.", reply_markup=btn)
            return

        # فیلتر هوشمند کلمات در چت زنده
        if message.text and is_bad(message.text):
            bot.delete_message(uid, message.message_id)
            bot.send_message(uid, "⚠️ **هشدار سیستم امنیت!**\nارسال پیام‌های حاوی کلمات نامناسب مجاز نیست. تکرار باعث مسدودیت شما می‌شود.")
            return

        # ذخیره تاریخچه برای گزارش
        if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
        msg_val = message.text if message.text else "Media/File"
        db["chat_history"][chat_id].append({"u": uid, "val": msg_val})
        if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
        save_db(db)

        try: bot.copy_message(partner, uid, message.message_id)
        except: bot.send_message(uid, "⚠️ **پیام ارسال نشد!**\nارتباط با طرف مقابل قطع شده است.")
        return

    # --- پنل مدیریت اختصاصی ---
    if uid == OWNER_ID:
        if message.text == "📢 ارسال همگانی":
            db["users"][uid]["state"] = "admin_bc"; save_db(db)
            bot.send_message(uid, "📝 **متن اطلاعیه خود را بفرستید:**", reply_markup=types.ReplyKeyboardRemove())
            return
        elif user.get("state") == "admin_bc":
            db["users"][uid]["state"] = "main"; save_db(db)
            count = 0
            for u in db["users"]:
                try: bot.send_message(u, f"📢 **اطلاعیه مهم مدیریت:**\n\n{message.text}"); count += 1
                except: pass
            bot.send_message(uid, f"✅ پیام برای {count} کاربر با موفقیت ارسال شد.", reply_markup=main_menu(uid))
            return
        elif message.text == "📊 مدیریت و آمار":
            stats = f"📊 **وضعیت کلی ربات:**\n\n👥 کل کاربران: {len(db['users'])}\n🚫 تعداد مسدودین: {len(db['banned'])}\n⏳ کاربران در صف: {len(db['queue']['any'])}"
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 دریافت فایل دیتابیس", callback_data="get_db_file"))
            btn.add(types.InlineKeyboardButton("🚫 لیست سیاه", callback_data="manage_banned"))
            bot.send_message(uid, stats, reply_markup=btn)
            return
        elif user.get("state") == "waiting_ban_time":
            if message.text.isdigit():
                target = user["temp_target"]
                expire = (datetime.datetime.now() + datetime.timedelta(minutes=int(message.text))).isoformat()
                db["banned"][target] = {"end": expire, "reason": "تخلف گزارش شده"}
                db["users"][uid]["state"] = "main"; save_db(db)
                bot.send_message(OWNER_ID, f"✅ کاربر {target} برای {message.text} دقیقه بن شد.", reply_markup=main_menu(uid))
                bot.send_message(target, f"⏳ **حساب شما به مدت {message.text} دقیقه مسدود شد.**")
            return

    # --- منوی اصلی و دکمه‌های شیشه‌ای ---
    if message.text == "🛰 شروع چت ناشناس":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="hunt_m"), types.InlineKeyboardButton("خانم 👧", callback_data="hunt_f")).add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 **تمایل داری با چه جنسیتی هم‌کلام شوی؟**", reply_markup=btn)
    
    elif message.text == "🤫 لینک پیام ناشناس":
        link = user.get("link") or str(random.randint(100000, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🤫 **لینک اختصاصی تو ساخته شد!**\nآن را در بیو اینستاگرام یا استوری تلگرام قرار بده تا بقیه بهت پیام ناشناس بدن:\n\n`https://t.me/{bot.get_me().username}?start={link}`")
    
    elif message.text == "👤 پروفایل من":
        sex = "آقا 👦" if user.get("gender")=="male" else "خانم 👧"
        bot.send_message(uid, f"👤 **مشخصات شما در ربات:**\n\n🏷 نام: {user['name']}\n🎂 سن: {user.get('age', 'ثبت نشده')}\n👫 جنسیت: {sex}\n🆔 آیدی عددی: `{uid}`", reply_markup=main_menu(uid))
    
    elif message.text == "❓ راهنمای ربات":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("نحوه کار 🛠", callback_data="guide_how"))
        btn.add(types.InlineKeyboardButton("قوانین و امنیت 🛡", callback_data="guide_sec"))
        bot.send_message(uid, "❓ **کدام بخش را برایت توضیح دهم؟**", reply_markup=btn)

    # پاسخ به پیام ناشناس (Reply Logic)
    if message.reply_to_message:
        target_uid = next((u_id for u_id, u_data in db["users"].items() if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            bot.send_message(target_uid, "💬 **یک پاسخ جدید برای پیام ناشناس شما دریافت شد:**")
            sent = bot.copy_message(target_uid, uid, message.message_id)
            db["users"][target_uid]["last_anon_msg_id"] = sent.message_id; save_db(db)
            bot.send_message(uid, "✅ **پاسخ تو با موفقیت ارسال شد.**")

    # نوشتن پیام ناشناس (State Handling)
    elif user.get("state") == "writing_confession" and message.text:
        db["users"][uid].update({"state": "main", "temp_msg": message.text}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال قطعی 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"✅ **پیش‌نمایش پیام شما:**\n\n{message.text}\n\nآیا از ارسال آن اطمینان دارید؟", reply_markup=btn)

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    # تنظیم جنسیت
    if call.data in ["set_m", "set_f"]:
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"}); save_db(db)
        bot.edit_message_text("🔢 **حالا سن خودت رو به عدد وارد کن (مثلاً 20):**", uid, call.message.id)

    # راهنما
    elif call.data.startswith("guide_"):
        res = "شما می‌توانید به صورت تصادفی با دیگران چت کنید یا لینک اختصاصی خود را منتشر کنید تا پیام ناشناس بگیرید." if "how" in call.data else "هرگونه ایجاد مزاحمت، ارسال محتوای +18 یا توهین باعث مسدود شدن دائم حساب شما می‌شود."
        bot.edit_message_text(res, uid, call.message.id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بازگشت 🔙", callback_data="back_guide")))

    elif call.data == "back_guide":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("نحوه کار 🛠", callback_data="guide_how")).add(types.InlineKeyboardButton("قوانین و امنیت 🛡", callback_data="guide_sec"))
        bot.edit_message_text("❓ بخش مورد نظر را انتخاب کن:", uid, call.message.id, reply_markup=btn)

    # گزارش و مدیریت (اصلاح شده: آیدی متهم در دکمه ذخیره می‌شود)
    elif call.data.startswith("rep_"):
        reason = call.data.split("_")[1]; partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = db["chat_history"].get(chat_id, [])
        report = f"🚩 **گزارش جدید**\nدلیل: {reason}\nشاکی: `{uid}`\nمتهم: `{partner}`\n\n📜 **۱۰ پیام آخر:**\n"
        for h in history: 
            tag = "[متهم]" if h['u'] == partner else "[شاکی]"
            report += f"{tag} ({h['u']}): {h['val']}\n"
        
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("TEMP BAN (دقیقه‌ای) ⏳", callback_data=f"adm_t_{partner}"))
        btn.add(types.InlineKeyboardButton("PERM BAN (دائمی) 🚫", callback_data=f"adm_p_{partner}"))
        btn.add(types.InlineKeyboardButton("IGNORE (نادیده گرفتن) ✅", callback_data="adm_ignore"))
        bot.send_message(OWNER_ID, report, reply_markup=btn)
        bot.edit_message_text("✅ **گزارش شما با موفقیت برای تیم مدیریت ارسال شد.**", uid, call.message.id)

    elif call.data == "adm_ignore": bot.edit_message_text("✅ گزارش نادیده گرفته شد.", uid, call.message.id)

    elif call.data.startswith("adm_t_"):
        target = call.data.split("_")[2]
        db["users"][OWNER_ID].update({"state": "waiting_ban_time", "temp_target": target}); save_db(db)
        bot.send_message(OWNER_ID, f"⏳ مدت زمان مسدودیت کاربر `{target}` را به **دقیقه** وارد کن:")

    elif call.data.startswith("adm_p_"):
        target = call.data.split("_")[2]
        db["banned"][target] = {"end": "perm", "reason": "تخلف شدید"}; save_db(db)
        bot.send_message(OWNER_ID, "✅ کاربر برای همیشه مسدود شد."); bot.send_message(target, "🚫 حساب شما برای همیشه مسدود شد.")

    # جستجوی هم‌صحبت (با لحاظ کردن سیستم بلاک)
    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]; pref_key = "male" if pref=="m" else ("female" if pref=="f" else "any")
        bot.edit_message_text("🔍 **در حال جستجوی هم‌صحبت... لطفاً از این صفحه خارج نشوید.**", uid, call.message.id)
        my_g = db["users"][uid].get("gender")
        target_pool = db["queue"]["any"] + db["queue"][my_g]
        
        match = None
        for u in target_pool:
            if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key):
                # چک کردن سیستم بلاک (مورد ۴)
                if u not in db["blocks"].get(uid, []) and uid not in db["blocks"].get(u, []):
                    match = u; break
        
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
                if uid in db["queue"][k]: db["queue"][k].remove(uid)
            db["users"][uid].update({"state": "in_chat", "partner": match}); db["users"][match].update({"state": "in_chat", "partner": uid}); save_db(db)
            bot.send_message(uid, "💎 **به یک هم‌صحبت متصل شدی!**\nهم‌اکنون می‌توانی چت را شروع کنی.", reply_markup=chat_menu())
            bot.send_message(match, "💎 **به یک هم‌صحبت متصل شدی!**\nهم‌اکنون می‌توانی چت را شروع کنی.", reply_markup=chat_menu())
        else:
            if uid not in db["queue"][pref_key]: db["queue"][pref_key].append(uid); save_db(db)
            bot.send_message(uid, "⌛️ **کاربری پیدا نشد.**\nشما در صف انتظار قرار گرفتید. به محض پیدا شدن نفر جدید، چت به صورت خودکار شروع می‌شود.", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("انصراف از صف ❌", callback_data="cancel_search")))

    elif call.data == "cancel_search":
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        db["users"][uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("🔚 **از صف انتظار خارج شدی.**", uid, call.message.id); bot.send_message(uid, "منوی اصلی:", reply_markup=main_menu(uid))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None}); db["users"][p].update({"state": "main", "partner": None}); save_db(db)
        bot.send_message(uid, "👋 **چت با موفقیت خاتمه یافت.**", reply_markup=main_menu(uid)); bot.send_message(p, "⚠️ **طرف مقابل چت را قطع کرد.**", reply_markup=main_menu(p))

    elif call.data == "send_conf":
        target = db["users"][uid].get("target"); msg = db["users"][uid].get("temp_msg")
        mkey = f"view_msg_{uid}_{random.randint(1000,9999)}"
        db["anon_msgs"][mkey] = msg; save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 مشاهده پیام", callback_data=mkey))
        bot.send_message(target, "📬 **یک پیام ناشناس جدید داری!**", reply_markup=btn)
        bot.edit_message_text("✅ **پیام تو با موفقیت ارسال شد.**", uid, call.message.id); bot.send_message(uid, "🏡 بازگشت به منوی اصلی", reply_markup=main_menu(uid))

    elif call.data.startswith("view_msg_"):
        msg = db["anon_msgs"].get(call.data)
        if msg:
            bot.edit_message_text(f"📩 **پیام ناشناس رسیده:**\n\n{msg}\n\n💡 برای پاسخ دادن کافیست روی همین پیام ریپلای کنید.", uid, call.message.id)
            db["users"][uid]["last_anon_msg_id"] = call.message.id; save_db(db)

    elif call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(OWNER_ID, f)

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
