import telebot
from telebot import types
import json, os, random, datetime
from flask import Flask
from threading import Thread

# --- زنده نگه داشتن قلب محفل ---
app = Flask('')
@app.route('/')
def home(): return "قلب محفل در حال تپیدن است..."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات محرمانه ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)

DB_PATH = "shadow_data.json"

def get_db():
    if not os.path.exists(DB_PATH): 
        return {"users": {}, "queue": {"male": [], "female": [], "any": []}}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def check_sub(uid):
    if str(uid) == OWNER_ID: return True
    try:
        s = bot.get_chat_member(CHANNEL_ID, uid).status
        return s in ['member', 'administrator', 'creator']
    except: return False

# --- طراحی فضاهای بصری (Keyboard) ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛰 شکار هم‌صحبت", "🤫 ایستگاه اعتراف")
    markup.add("🎈 ویترین من", "📖 داستان محفل")
    if str(uid) == OWNER_ID: markup.add("📢 طنین مدیریت")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✂️ قطع ارتباط", "🚩 گزارش تخلف")
    return markup

# --- موتور اصلی محفل ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    text = message.text

    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("عضویت در کانال اعلانات 📢", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو 🔓", callback_data="verify_join"))
        bot.send_message(uid, "✨ مسافر عزیز! برای ورود به تالار اصلی محفل، ابتدا باید در کانال ما حضور داشته باشی. منتظرت هستیم...", reply_markup=btn)
        return

    # ۱. هندل کردن استارت و لینک ناشناس
    if text and text.startswith("/start "):
        code = text.split()[1]
        target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
        if target == uid:
            bot.send_message(uid, "🎭 ای شیطون! داری برای خودت نامه می‌نویسی؟ این لینک رو پخش کن تا بقیه برات اعتراف کنن!")
            return
        if target:
            db["users"][uid] = db["users"].get(uid, {"state": "main"})
            db["users"][uid].update({"state": "writing_confession", "target": target})
            save_db(db)
            bot.send_message(uid, "🕯 در خلوتگاه او هستی... هر چه در دل داری بنویس. هویت تو مثل یک رازِ مقدس پیش من محفوظ می‌مونه.", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۲. ثبت‌نام اولیه
    if uid not in db["users"] or "name" not in db["users"][uid] or db["users"][uid].get("state") in ["reg_name", "reg_gender", "reg_age"]:
        if uid not in db["users"]: db["users"][uid] = {"state": "reg_name"}
        state = db["users"][uid]["state"]

        if state == "reg_name":
            if text == "/start": bot.send_message(uid, "🕯 به محفل سایه‌ها خوش آمدی... نامی مستعار برای خودت انتخاب کن:")
            else:
                db["users"][uid].update({"name": text[:20], "state": "reg_gender"})
                save_db(db)
                btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه (آقا) 👦", callback_data="set_m"), types.InlineKeyboardButton("بانو (خانم) 👧", callback_data="set_f"))
                bot.send_message(uid, f"✨ خوش‌آمدی {text} عزیز. حالا بگو در این محفل شوالیه‌ای یا بانو؟", reply_markup=btn)
            return
        if state == "reg_age":
            if text and text.isdigit():
                db["users"][uid].update({"age": text, "state": "main"})
                save_db(db)
                bot.send_message(uid, "📜 نامت در کتیبه محفل ثبت شد. حالا وقتشه هم‌فرکانس خودت رو پیدا کنی!", reply_markup=main_menu(uid))
            else: bot.send_message(uid, "🎭 سن رو فقط به صورت عدد برام بفرست.")
            return
        return

    user = db["users"][uid]

    # ۳. مدیریت چت فعال
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن ❌", callback_data="confirm_end"), types.InlineKeyboardButton("نه، بمان 🕯", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 آیا مطمئنی می‌خوای این رشته‌ی اتصال رو پاره کنی و به دنیای سایه‌ها برگردی؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=1)
            reasons = ["توهین و بی‌ادبی 🤬", "تبلیغات مزاحم 📢", "محتوای نامناسب 🔞", "مزاحمت ❌", "بی‌خیال، لغو گزارش 🔙"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"report_{r}"))
            bot.send_message(uid, "🚩 دلیل گزارش رو انتخاب کن تا نگهبان‌های محفل بررسی کنن:", reply_markup=btn)
        else:
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # ۴. تایید ارسال اعتراف (ناشناس)
    if user.get("state") == "writing_confession" and text:
        db["users"][uid].update({"state": "confirm_confession", "temp_msg": text})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بفرست بره 🚀", callback_data="send_conf"), types.InlineKeyboardButton("پشیمون شدم ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"📜 متنت رو با دقت خوندم. بفرستمش برای صاحب راز؟\n\n📝 متن تو:\n{text}", reply_markup=btn)
        return

    # ۵. ریپلای به اعتراف (ناشناس)
    if message.reply_to_message and "🆔 کد راز:" in (message.reply_to_message.text or ""):
        try:
            original_sender = message.reply_to_message.text.split("🆔 کد راز:")[1].strip()
            bot.send_message(original_sender, f"💌 صاحبِ راز به پیام تو جواب داد:\n\n{text}")
            bot.send_message(uid, "✅ جوابت با موفقیت و به صورت ناشناس به دستش رسید.")
        except: bot.send_message(uid, "🎭 متاسفانه سایه فرستنده گم شده، پیام نرسید.")
        return

    # ۶. منوی اصلی
    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_m"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_f"))
        btn.add(types.InlineKeyboardButton("هر کسی که شد 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 رادارهای محفل رو برای پیدا کردن یک هم‌فرکانس روشن کردم. کی مد نظرته؟", reply_markup=btn)

    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(111111, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینکِ اعترافات ناشناس تو آماده‌ست! بزارش توی بیو:\n\nhttps://t.me/{bot.get_me().username}?start={link}")

    elif text == "🎈 ویترین من":
        sex = "شوالیه 👦" if user.get("gender") == "male" else "بانو 👧"
        bot.send_message(uid, f"📜 **کتیبه هویت تو در دفتر محفل:**\n\n👤 اسم مستعار: {user['name']}\n🎭 جنسیت: {sex}\n🎂 سن: {user.get('age', 'نامعلوم')}\n\nآیا همه چیز در آینه‌ی محفل درسته؟")

    elif text == "📖 داستان محفل":
        bot.send_message(uid, "🕯 محفل سایه‌ها جایی برای گفتگوهای بدون نقابه. اینجا هویت تو مخفیه تا بتونی بلندترین فریادهای دلت رو به صورت ناشناس به گوش بقیه برسونی. ما نگهبان رازهای تو هستیم.")

    elif text == "📢 طنین مدیریت" and uid == OWNER_ID:
        db["users"][uid]["state"] = "admin_bc"
        save_db(db)
        bot.send_message(uid, "📢 پیامی که می‌خوای در کل تالار طنین‌انداز بشه رو بنویس:", reply_markup=types.ReplyKeyboardRemove())

    elif user.get("state") == "admin_bc" and uid == OWNER_ID:
        db["users"][uid]["state"] = "main"; save_db(db)
        for u in db["users"]:
            try: bot.send_message(u, f"📢 **طنین مدیریت در محفل:**\n\n{text}")
            except: pass
        bot.send_message(uid, "✅ پیام با موفقیت طنین‌انداز شد.", reply_markup=main_menu(uid))

# --- مدیریت تعاملات شیشه‌ای ---
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    if call.data == "verify_join":
        if check_sub(uid):
            bot.delete_message(uid, call.message.id)
            bot.send_message(uid, "🔓 درهای تالار باز شد! خوش آمدی.", reply_markup=main_menu(uid))

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"})
        save_db(db); bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "🕯 حالا سن قشنگت رو به عدد برای کتیبه بفرست:")

    elif call.data == "send_conf":
        target = db["users"][uid].get("target"); msg = db["users"][uid].get("temp_msg")
        try:
            bot.send_message(target, f"📬 **یه رازِ ناشناس برای تو رسید:**\n\n{msg}\n\n➖➖➖➖➖➖\n💡 برای جواب دادن، روی همین پیام ریپلای کن.\n🆔 کد راز: {uid}")
            bot.edit_message_text("✅ قاصدک تو به مقصد رسید! هویتت پیش من جاش امنه.", uid, call.message.id)
            bot.send_message(uid, "🏡 بازگشت به ایستگاه مرکزی", reply_markup=main_menu(uid))
        except: bot.send_message(uid, "🎭 نشد برسونم، انگار راه مسدود شده.")
        db["users"][uid]["state"] = "main"; save_db(db)

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        my_gender = db["users"][uid].get("gender")
        pref_key = "male" if pref == "m" else ("female" if pref == "f" else "any")
        
        bot.edit_message_text("🔍 در حال جستجوی روحی سرگردان در اعماق محفل... یکم صبر کن رفیق.", uid, call.message.id)
        
        # لغو جستجوی قبلی اگر وجود داشت
        for k in db["queue"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)

        target_pool = db["queue"][pref_key] if pref_key != "any" else (db["queue"]["male"] + db["queue"]["female"])
        match = next((u for u in target_pool if u != uid), None)
        
        if match:
            for k in db["queue"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید. گپ رو شروع کن!", reply_markup=chat_menu())
            bot.send_message(match, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید. گپ رو شروع کن!", reply_markup=chat_menu())
        else:
            db["queue"][my_gender if pref_key == "any" else pref_key].append(uid)
            save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بی‌خیال، لغو جستجو ❌", callback_data="cancel_search"))
            bot.send_message(uid, "🕯 هنوز کسی پیدا نشده... همونجا بمون، رادارهای من دارن دنبالش می‌گردن.", reply_markup=btn)

    elif call.data == "cancel_search":
        for k in db["queue"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        save_db(db)
        bot.edit_message_text("❌ جستجو لغو شد. برگشتیم به تالار اصلی.", uid, call.message.id)
        bot.send_message(uid, "🏡 منوی اصلی", reply_markup=main_menu(uid))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][p].update({"state": "main", "partner": None})
        save_db(db)
        bot.send_message(uid, "رشته اتصال پاره شد. به امید دیداری دوباره در محفل...", reply_markup=main_menu(uid))
        bot.send_message(p, "هم‌صحبت تو چت رو تموم کرد. بریم برای شکار بعدی؟", reply_markup=main_menu(p))

    elif call.data == "cancel_end":
        bot.edit_message_text("🕯 خوشحالم که موندی! گپ رو ادامه بده.", uid, call.message.id)

    elif call.data.startswith("report_"):
        reason = call.data.replace("report_", "")
        if "لغو" in reason: bot.edit_message_text("🕯 بی‌خیال شدیم! گپ رو ادامه بده.", uid, call.message.id)
        else:
            partner = db["users"][uid].get("partner")
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            report_msg = f"🚩 **گزارش تخلف جدید**\n\n👤 ارسال‌کننده: `{uid}`\n👤 گزارش شده: `{partner}`\n📅 تاریخ: `{now}`\n📂 دلیل: {reason}"
            bot.send_message(OWNER_ID, report_msg, parse_mode="Markdown")
            bot.edit_message_text("✅ گزارش با موفقیت برای نگهبان‌ها ارسال شد. ممنون که به سلامت محفل کمک می‌کنی.", uid, call.message.id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
