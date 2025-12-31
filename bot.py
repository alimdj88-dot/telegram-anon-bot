import telebot
from telebot import types
import json, os, random, datetime, re, time
from flask import Flask
from threading import Thread

# --- سامانه پایداری و میزبانی (Anti-Sleep) ---
app = Flask('')
@app.route('/')
def home(): return "Shadow Chat Bot Status: Online and Secure."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات و دیتابیس مرکزی ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_data.json"

# لیست کلمات ممنوعه برای فیلتر هوشمند
BAD_WORDS = ["مادرجنده", "کص ننت", "کون", "کص", "کیر", "جنده", "ناموس", "بی‌ناموس", "کونی", "جنده‌خونه", "لاشی", "خایه", "ساک", "پستون", "کصکش", "دیوث"] 
user_last_msg_time = {}

def get_db():
    if not os.path.exists(DB_PATH): 
        db = {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}, "blocks": {}}
        save_db(db); return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            # اطمینان از سلامت ساختار دیتابیس
            for key in ["blocks", "chat_history", "anon_msgs", "banned"]:
                if key not in data: data[key] = {}
            if "queue" not in data: data["queue"] = {"male": [], "female": [], "any": []}
            return data
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}, "blocks": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def is_bad(text):
    if not text: return False
    cleaned = re.sub(r'[\s\.\-\_\*\/\\n\+]+', '', text)
    for word in BAD_WORDS:
        if word in cleaned: return True
    return False

def check_sub(uid):
    if str(uid) == OWNER_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, int(uid)).status
        return status in ['member', 'administrator', 'creator']
    except: return False

# --- طراحی کیبوردهای گرافیکی (UI) ---
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

# --- پردازشگر اصلی تمام پیام‌ها و رسانه‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    
    # ۱. بررسی سیستم مسدودیت
    if uid in db.get("banned", {}):
        expire_str = db["banned"][uid]['end']
        if expire_str == "perm":
            bot.send_message(uid, "🚫 **دسترسی شما به صورت دائمی قطع شده است!**\nشما به دلیل نقض قوانین و گزارش‌های مکرر از استفاده از ربات محروم شده‌اید.")
            return
        elif datetime.datetime.now() < datetime.datetime.fromisoformat(expire_str):
            bot.send_message(uid, f"🚫 **حساب شما به صورت موقت مسدود شده است!**\nزمان بازگشایی: `{expire_str}`\nلطفاً در این مدت قوانین را مطالعه کنید.")
            return

    # ۲. هندلر ادمین برای بن موقت (رفع باگ وضعیت)
    user = db["users"].get(uid)
    if uid == OWNER_ID and user and user.get("state") == "waiting_ban_time":
        if message.text and message.text.isdigit():
            target = user.get("temp_target")
            minutes = int(message.text)
            expire = (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat()
            db["banned"][target] = {"end": expire, "name": db["users"][target].get("name", "نامشخص"), "reason": "تخلف گزارش شده"}
            db["users"][uid]["state"] = "main"
            save_db(db)
            bot.send_message(uid, f"✅ کاربر `{target}` با موفقیت برای {minutes} دقیقه از ربات مسدود شد.", reply_markup=main_menu(uid))
            try: bot.send_message(target, f"⏳ حساب شما به دلیل عدم رعایت قوانین برای {minutes} دقیقه مسدود شد.")
            except: pass
            return
        else:
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.send_message(uid, "❌ مقدار نامعتبر بود. عملیات لغو شد.", reply_markup=main_menu(uid))
            return

    # ۳. عضویت اجباری در کانال
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("عضویت در کانال خبررسانی 📢", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        bot.send_message(uid, "👋 **خوش آمدی همسفر عزیز!**\nبرای استفاده از قابلیت‌های چت ناشناس و لینک‌های اختصاصی، ابتدا باید در کانال ما عضو شوی. پس از عضویت، دوباره ربات را /start کن:", reply_markup=btn)
        return

    # ۴. هندل دستور استارت و ورود با لینک
    if message.text and message.text.startswith("/start"):
        if uid not in db["users"] or "gender" not in db["users"][uid]:
            db["users"][uid] = {"state": "reg_name", "warns": 0}
            save_db(db)
            bot.send_message(uid, "✨ **سلام! به ایستگاه چت ناشناس خوش آمدی.**\nبرای اینکه دوستانت بهتر بشناسنت، ابتدا یک **نام مستعار** برای خودت انتخاب و ارسال کن:")
            return
            
        args = message.text.split()
        if len(args) > 1:
            code = args[1]
            target = next((u_id for u_id, u_data in db["users"].items() if u_data.get("link") == code), None)
            if target == uid:
                bot.send_message(uid, "🙄 **ای شیطون!** نمی‌تونی به خودت پیام ناشناس بدی.")
                return
            if target:
                db["users"][uid].update({"state": "writing_confession", "target": target})
                save_db(db)
                bot.send_message(uid, "📝 **در حال آماده‌سازی پیام برای یک ناشناس...**\nهر چه در دل داری بنویس (هویت تو برای طرف مقابل کاملاً مخفی می‌ماند):", reply_markup=types.ReplyKeyboardRemove())
                return
        
        bot.send_message(uid, "💎 **به خانه خوش آمدی!**\nاز منوی زیر برای شروع چت یا دریافت لینک استفاده کن:", reply_markup=main_menu(uid))
        return

    if not user: return

    # ۵. سیستم پاسخ‌دهی (Reply) به پیام‌های ناشناس با تاییدیه
    if message.reply_to_message and user.get("state") == "main":
        target_uid = next((u_id for u_id, u_data in db["users"].items() if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            db["users"][uid].update({"state": "writing_confession", "target": target_uid, "temp_msg": message.text})
            save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال قطعی 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
            bot.send_message(uid, f"✅ **پیش‌نمایش پاسخ شما:**\n\n{message.text}\n\nآیا از ارسال این پاسخ اطمینان دارید؟", reply_markup=btn)
            return

    # ۶. مدیریت چت زنده و آنتی‌فحش پیشرفته (Media Support)
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        
        if message.text == "🚫 بلاک کردن کاربر":
            if uid not in db["blocks"]: db["blocks"][uid] = []
            db["blocks"][uid].append(partner)
            db["users"][uid].update({"state": "main", "partner": None})
            db["users"][partner].update({"state": "main", "partner": None})
            save_db(db)
            bot.send_message(uid, "🚫 کاربر برای شما بلاک شد و چت پایان یافت.", reply_markup=main_menu(uid))
            bot.send_message(partner, "⚠️ طرف مقابل چت را ترک کرد و شما را بلاک کرد.", reply_markup=main_menu(partner))
            return
        elif message.text == "❌ قطع چت":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن 🔚", callback_data="confirm_end"), types.InlineKeyboardButton("خیر، ادامه 🔙", callback_data="cancel_end"))
            bot.send_message(uid, "🤔 **آیا واقعاً می‌خواهی این گفتگو را تمام کنی؟**", reply_markup=btn); return
        elif message.text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup()
            for reason in ["فحاشی و توهین 🤬", "تبلیغات مزاحم", "درخواست نامربوط"]:
                btn.add(types.InlineKeyboardButton(reason, callback_data=f"rep_{reason[:5]}"))
            bot.send_message(uid, "🚩 **علت گزارش خود را انتخاب کنید:**", reply_markup=btn); return
        
        # آنتی‌فحش و سیستم اخطار هوشمند
        if message.text and is_bad(message.text):
            bot.delete_message(uid, message.message_id)
            db["users"][uid]["warns"] = db["users"][uid].get("warns", 0) + 1
            save_db(db)
            bot.send_message(uid, f"⚠️ **اخطار!** استفاده از کلمات رکیک ممنوع است.\nتعداد اخطارهای شما: `{db['users'][uid]['warns']}/3`")
            if db["users"][uid]["warns"] >= 3:
                btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🤖 تصمیم هوشمند", callback_data=f"ai_decide_{uid}"), types.InlineKeyboardButton("TEMP ⏳", callback_data=f"adm_t_{uid}"), types.InlineKeyboardButton("PERM 🚫", callback_data=f"adm_p_{uid}"))
                bot.send_message(OWNER_ID, f"🚨 **گزارش خودکار سیستم!**\nکاربر `{uid}` ({user.get('name')}) به سقف ۳ اخطار فحاشی رسید.\nچه دستوری صادر می‌کنید؟", reply_markup=btn)
            return

        # ذخیره رسانه‌ها و متون در دیتابیس برای گزارش ادمین
        if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
        msg_type = "MEDIA_FILE" if not message.text else "TEXT"
        db["chat_history"][chat_id].append({"u": uid, "t": message.text if message.text else "رسانه ارسالی", "mid": message.message_id, "type": msg_type})
        if len(db["chat_history"][chat_id]) > 20: db["chat_history"][chat_id].pop(0)
        save_db(db)
        
        try: bot.copy_message(partner, uid, message.message_id)
        except: pass
        return

    # ۷. فرآیند ثبت‌نام گام‌به‌گام (بدون بازنویسی)
    if user["state"] == "reg_name":
        db["users"][uid].update({"name": message.text[:20], "state": "reg_gender"}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="set_m"), types.InlineKeyboardButton("خانم 👧", callback_data="set_f"))
        bot.send_message(uid, f"✨ **بسیار خوشبختم، {message.text}!**\nحالا برای تکمیل پروفایل، جنسیت خودت رو انتخاب کن:", reply_markup=btn)
    elif user["state"] == "reg_age":
        if message.text.isdigit() and 10 < int(message.text) < 90:
            db["users"][uid].update({"age": message.text, "state": "main"}); save_db(db)
            bot.send_message(uid, "🎉 **تبریک! ثبت‌نام شما کامل شد.**\nهم‌اکنون می‌توانید از منوی زیر استفاده کنید:", reply_markup=main_menu(uid))
        else:
            bot.send_message(uid, "❌ لطفاً سن خود را به عدد (بین ۱۰ تا ۹۰) وارد کنید:")

    # ۸. قابلیت‌های منوی اصلی و ادمین
    elif message.text == "🛰 شروع چت ناشناس":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="hunt_m"), types.InlineKeyboardButton("خانم 👧", callback_data="hunt_f")).add(types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 **مایل هستید به چه کسی متصل شوید؟**\nجنسیت مخاطب خود را انتخاب کنید:", reply_markup=btn)
    elif message.text == "🤫 لینک پیام ناشناس":
        link = user.get("link") or str(random.randint(100000, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🤫 **لینک اختصاصی شما آماده شد!**\nآن را در بیو یا استوری خود قرار دهید تا دیگران به شما پیام ناشناس بدهند:\n\n`https://t.me/{bot.get_me().username}?start={link}`")
    elif message.text == "👤 پروفایل من":
        sex = "آقا 👦" if user.get("gender")=="male" else "خانم 👧"
        bot.send_message(uid, f"👤 **مشخصات کاربری شما:**\n\n🏷 نام: {user['name']}\n👫 جنسیت: {sex}\n🎂 سن: {user.get('age')}\n🆔 آیدی عددی: `{uid}`")
    elif message.text == "❓ راهنمای ربات":
        bot.send_message(uid, "📖 **راهنمای سریع:**\n\n۱. **چت ناشناس:** اتصال تصادفی به افراد غریبه.\n۲. **لینک ناشناس:** دریافت پیام‌های مخفی از دوستان.\n۳. **امنیت:** هویت شما در هیچ حالتی فاش نمی‌شود.")

    # پنل مدیریت ادمین
    elif message.text == "📊 مدیریت و آمار" and uid == OWNER_ID:
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 دریافت دیتابیس", callback_data="get_db_file"), types.InlineKeyboardButton("🚫 لیست سیاه کاربران", callback_data="show_blacklist"))
        bot.send_message(uid, f"📊 **آمار کلی Shadow Chat:**\n\n👥 کاربران: {len(db['users'])}\n🚫 کل مسدودین: {len(db['banned'])}\n⏳ در صف انتظار: {len(db['queue']['any'])}", reply_markup=btn)
    elif message.text == "📢 ارسال همگانی" and uid == OWNER_ID:
        db["users"][uid]["state"] = "admin_bc"; save_db(db)
        bot.send_message(uid, "📝 **متن اطلاعیه خود را بفرستید:**\n(برای لغو کلمه 'لغو' را ارسال کنید)", reply_markup=types.ReplyKeyboardRemove())
    elif user.get("state") == "admin_bc" and uid == OWNER_ID:
        if message.text == "لغو":
            db["users"][uid]["state"] = "main"; save_db(db); bot.send_message(uid, "لغو شد.", reply_markup=main_menu(uid)); return
        db["users"][uid]["state"] = "main"; save_db(db)
        for u_id in db["users"]:
            try: bot.send_message(u_id, f"📢 **اطلاعیه جدید مدیریت:**\n\n{message.text}")
            except: pass
        bot.send_message(uid, "✅ ارسال همگانی با موفقیت انجام شد.", reply_markup=main_menu(uid))

    # هندلر ارسال نهایی پیام ناشناس
    elif user.get("state") == "writing_confession" and message.text:
        db["users"][uid].update({"temp_msg": message.text}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ارسال قطعی 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"✅ **پیش‌نمایش نهایی:**\n\n{message.text}\n\nآیا ارسال شود؟", reply_markup=btn)

@bot.callback_query_handler(func=lambda call: True)
def callback_logic(call):
    uid = str(call.message.chat.id); db = get_db()
    
    # دکمه‌های ثبت‌نام
    if call.data == "set_m": db["users"][uid].update({"gender": "male", "state": "reg_age"}); save_db(db); bot.edit_message_text("✨ نام شما تایید شد. حالا **سن** خودت رو وارد کن:", uid, call.message.id)
    elif call.data == "set_f": db["users"][uid].update({"gender": "female", "state": "reg_age"}); save_db(db); bot.edit_message_text("✨ نام شما تایید شد. حالا **سن** خودت رو وارد کن:", uid, call.message.id)
    
    # مدیریت لیست سیاه (Blacklist)
    elif call.data == "show_blacklist":
        text = "🚫 **لیست سیاه ادمین:**\n\n"
        markup = types.InlineKeyboardMarkup()
        for b_id, b_data in db["banned"].items():
            text += f"👤 {b_data.get('name')} | `{b_id}`\n⏰ انقضا: {b_data['end']}\n\n"
            markup.add(types.InlineKeyboardButton(f"🔓 آن‌بن {b_id}", callback_data=f"unban_{b_id}"))
        bot.send_message(uid, text if db["banned"] else "لیست سیاه خالی است.", reply_markup=markup)

    elif call.data.startswith("unban_"):
        target = call.data.split("_")[1]
        if target in db["banned"]: del db["banned"][target]
        save_db(db); bot.send_message(uid, f"✅ کاربر {target} با موفقیت آن‌بن شد.")

    # سیستم گزارش و بازبینی رسانه
    elif call.data.startswith("rep_"):
        partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("TEMP ⏳", callback_data=f"adm_t_{partner}"), types.InlineKeyboardButton("PERM 🚫", callback_data=f"adm_p_{partner}"))
        btn.add(types.InlineKeyboardButton("📥 مشاهده رسانه‌های چت", callback_data=f"view_m_{chat_id}"), types.InlineKeyboardButton("Ignore 🟢", callback_data="ignore_rep"))
        
        # نمایش ۵ پیام آخر چت در گزارش برای ادمین
        history = db["chat_history"].get(chat_id, [])
        log = "\n".join([f"{'او' if x['u']==partner else 'من'}: {x['t']}" for x in history[-10:]])
        bot.send_message(OWNER_ID, f"🚩 **گزارش تخلف جدید**\nمتهم: `{partner}`\nشاکی: `{uid}`\nنام متهم: {db['users'][partner].get('name')}\n\n📜 **آخرین پیام‌ها:**\n{log}", reply_markup=btn)
        bot.edit_message_text("✅ گزارش شما با موفقیت برای مدیریت ارسال شد.", uid, call.message.id)

    elif call.data.startswith("view_m_"):
        cid = call.data.replace("view_m_", ""); history = db["chat_history"].get(cid, [])
        bot.send_message(uid, "📂 **در حال ارسال تمام فایل‌های تبادل شده در این چت...**")
        found = False
        for h in history:
            if h["type"] == "MEDIA_FILE":
                try: bot.copy_message(uid, OWNER_ID, h["mid"]); found = True
                except: pass
        if not found: bot.send_message(uid, "❌ هیچ فایل رسانه‌ای (عکس/فیلم/...) در این چت یافت نشد.")

    elif call.data == "ignore_rep":
        bot.edit_message_text("🟢 این گزارش نادیده گرفته شد.", uid, call.message.id)

    # هوش مصنوعی اخطار
    elif call.data.startswith("ai_decide_"):
        t = call.data.split("_")[2]; action = random.choice(["ban_1h", "forgive"])
        if action == "ban_1h":
            db["banned"][t] = {"end": (datetime.datetime.now() + datetime.timedelta(hours=1)).isoformat(), "name": db["users"][t].get("name")}
            bot.send_message(OWNER_ID, f"🤖 تصمیم هوشمند: کاربر `{t}` برای ۱ ساعت بن شد.")
        else:
            db["users"][t]["warns"] = 0
            bot.send_message(OWNER_ID, f"🤖 تصمیم هوشمند: به کاربر `{t}` یک فرصت دوباره داده شد.")
        save_db(db)

    # چت ناشناس و اتصال
    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]; pref_key = "male" if pref=="m" else ("female" if pref=="f" else "any")
        bot.edit_message_text("🔍 **در حال جستجوی هم‌صحبت مناسب...**", uid, call.message.id)
        
        potential = []
        for q_uid in db["queue"]["any"] + db["queue"]["male"] + db["queue"]["female"]:
            if q_uid == uid or q_uid in db["blocks"].get(uid, []): continue
            if pref_key == "any" or db["users"][q_uid]["gender"] == pref_key: potential.append(q_uid)
        
        if potential:
            match = potential[0]
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid}); save_db(db)
            bot.send_message(uid, "💎 **شکار پیدا شد!**\nهم‌اکنون می‌توانید گفتگو کنید.", reply_markup=chat_menu())
            bot.send_message(match, "💎 **شکار پیدا شد!**\nهم‌اکنون می‌توانید گفتگو کنید.", reply_markup=chat_menu())
        else:
            if uid not in db["queue"][pref_key]: db["queue"][pref_key].append(uid); save_db(db)
            bot.send_message(uid, "⌛️ **فعلاً کسی در صف نیست.**\nبه محض پیدا شدن نفر جدید، به شما خبر می‌دهیم...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("انصراف از صف ❌", callback_data="cancel_search")))

    # عملیات ارسال پیام ناشناس و دکمه‌های ادمین
    elif call.data == "send_conf":
        u_data = db["users"].get(uid); target = u_data.get("target"); msg = u_data.get("temp_msg")
        if target:
            mkey = f"v_{uid}_{random.randint(100,999)}"
            db["anon_msgs"][mkey] = {"m": msg, "f": uid}; save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 مشاهده پیام", callback_data=mkey))
            bot.send_message(target, "📬 **یک پیام ناشناس جدید برای شما ارسال شد!**", reply_markup=btn)
            db["users"][uid]["state"] = "main"; save_db(db); bot.edit_message_text("✅ پیام شما با موفقیت ارسال شد.", uid, call.message.id); bot.send_message(uid, "🏡 منوی اصلی", reply_markup=main_menu(uid))

    elif call.data.startswith("v_"):
        data = db["anon_msgs"].get(call.data)
        if data:
            bot.edit_message_text(f"📩 **پیام دریافتی:**\n\n{data['m']}\n\n💡 برای پاسخ دادن، کافیست روی همین پیام **Reply** کنید.", uid, call.message.id)
            db["users"][uid]["last_anon_msg_id"] = call.message.id; save_db(db)

    elif call.data.startswith("adm_p_"):
        t = call.data.split("_")[2]; db["banned"][t] = {"end": "perm", "name": db["users"][t].get("name")}; save_db(db)
        bot.send_message(uid, f"✅ کاربر `{t}` به صورت دائمی مسدود شد.")

    elif call.data.startswith("adm_t_"):
        t = call.data.split("_")[2]; db["users"][uid].update({"state": "waiting_ban_time", "temp_target": t}); save_db(db)
        bot.send_message(uid, f"⏳ لطفاً مدت زمان مسدودیت برای کاربر `{t}` را به **دقیقه** وارد کنید:")

    elif call.data == "confirm_end":
        partner = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None}); db["users"][partner].update({"state": "main", "partner": None}); save_db(db)
        bot.send_message(uid, "👋 چت با موفقیت پایان یافت.", reply_markup=main_menu(uid))
        bot.send_message(partner, "⚠️ هم‌صحبت شما چت را ترک کرد.", reply_markup=main_menu(partner))

    elif call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(OWNER_ID, f)

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
