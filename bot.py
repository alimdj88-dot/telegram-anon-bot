import telebot
from telebot import types
import json, os, random, datetime
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "قلب محفل در حال تپیدن است..."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)

DB_PATH = "shadow_data.json"

def get_db():
    if not os.path.exists(DB_PATH): 
        db = {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": [], "chat_history": {}}
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "banned" not in data: data["banned"] = []
            if "chat_history" not in data: data["chat_history"] = {}
            if "queue" not in data: data["queue"] = {"male": [], "female": [], "any": []}
            return data
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": [], "chat_history": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def check_sub(uid):
    if str(uid) == OWNER_ID: return True
    try:
        s = bot.get_chat_member(CHANNEL_ID, int(uid)).status
        return s in ['member', 'administrator', 'creator']
    except: return False

def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛰 شکار هم‌صحبت", "🤫 ایستگاه اعتراف")
    markup.add("🎈 ویترین من", "📖 داستان محفل")
    if str(uid) == OWNER_ID: markup.add("📢 طنین مدیریت", "📊 آمار و دیتابیس")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✂️ قطع ارتباط", "🚩 گزارش تخلف")
    return markup

@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    
    if uid in db.get("banned", []):
        bot.send_message(uid, "🚫 شما به دلیل نقض قوانین از حضور در محفل سایه‌ها مسدود شده‌اید.")
        return

    text = message.text
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("عضویت در کانال اعلانات 📢", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو 🔓", callback_data="verify_join"))
        bot.send_message(uid, "✨ مسافر عزیز! برای ورود به تالار اصلی محفل، ابتدا باید در کانال ما حضور داشته باشی. منتظرت هستیم...", reply_markup=btn)
        return

    # مدیریت ویژه ادمین
    if uid == OWNER_ID and text == "📊 آمار و دیتابیس":
        males = sum(1 for u in db["users"].values() if u.get("gender") == "male")
        females = sum(1 for u in db["users"].values() if u.get("gender") == "female")
        stats = f"📜 **آمار اهالی محفل:**\n\n👥 کل کاربران: {len(db['users'])}\n👦 شوالیه‌ها: {males}\n👧 بانوها: {females}\n🚫 مسدود شده‌ها: {len(db['banned'])}"
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("📥 دریافت فایل دیتابیس", callback_data="get_db_file"))
        btn.add(types.InlineKeyboardButton("🚫 مدیریت لیست سیاه", callback_data="manage_banned"))
        bot.send_message(uid, stats, reply_markup=btn)
        return

    # سیستم هندل کردن استارت و لینک‌های ناشناس
    if text and text.startswith("/start"):
        # اگر کاربر وسط چت باشد، اجازه استارت مجدد نده
        if uid in db["users"] and db["users"][uid].get("state") == "in_chat":
            bot.send_message(uid, "🕯 شما در حال حاضر در یک رشته اتصال هستید. ابتدا با دکمه قطع ارتباط، به تالار بازگردید.")
            return

        # اگر استارت معمولی بود و ثبت نام نکرده بود
        if len(text.split()) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}
                save_db(db)
                welcome_text = "🕯 **به محفل سایه‌ها خوش آمدی، غریبه...**\n\nاینجا جاییه که نقاب‌ها می‌افته و روح‌ها بدون ترس از قضاوت با هم حرف می‌زنن. برای ورود به تالار، باید هویت سایه‌ای خودت رو بسازی.\n\n👤 **یک نام مستعار برای کتیبه محفل بنویس:**"
                bot.send_message(uid, welcome_text, parse_mode="Markdown")
                return
            else:
                bot.send_message(uid, "🗝 درهای تالار به روی تو باز است...", reply_markup=main_menu(uid))
                return

        # اگر استارت لینک ناشناس بود
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

    # مراحل ثبت‌نام (اگر در حال ثبت نام باشد)
    if uid in db["users"] and db["users"][uid].get("state") in ["reg_name", "reg_gender", "reg_age"]:
        state = db["users"][uid]["state"]
        if state == "reg_name":
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

    user = db["users"].get(uid)
    if not user: return

    # سیستم چت فعال
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن ❌", callback_data="confirm_end"), types.InlineKeyboardButton("نه، بمان 🕯", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 آیا مطمئنی می‌خوای این رشته‌ی اتصال رو پاره کنی؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=1)
            reasons = ["توهین و بی‌ادبی 🤬", "تبلیغات مزاحم 📢", "محتوای نامناسب 🔞", "مزاحمت ❌", "بی‌خیال، لغو 🔙"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"report_{r}"))
            bot.send_message(uid, "🚩 دلیل گزارش رو انتخاب کن:", reply_markup=btn)
        else:
            chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
            if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
            if text:
                db["chat_history"][chat_id].append(f"[{uid}] {user['name']}: {text}")
                if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
                save_db(db)
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # بقیه منوهای اصلی (شکار، اعتراف و ...)
    if message.reply_to_message:
        target_uid = next((u for u, d in db["users"].items() if d.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            sent_msg = bot.send_message(target_uid, f"💌 **پاسخی جدید در خلوتگاه تو طنین‌انداز شد:**\n\n{text}\n\n➖➖➖➖➖➖\n💡 می‌تونی با ریپلای کردن، ادامه بدی.")
            db["users"][target_uid]["last_anon_msg_id"] = sent_msg.message_id
            save_db(db); bot.send_message(uid, "✅ پیامت منتقل شد.")
            return

    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_m"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_f"))
        btn.add(types.InlineKeyboardButton("هر کسی که شد 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 دنبال چه کسی می‌گردی؟", reply_markup=btn)
    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(111111, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینکِ اعترافات ناشناس تو:\n\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif text == "🎈 ویترین من":
        sex = "شوالیه 👦" if user.get("gender") == "male" else "بانو 👧"
        bot.send_message(uid, f"📜 **ویترین هویت تو:**\n\n👤 نام: {user['name']}\n🎭 جنسیت: {sex}\n🎂 سن: {user.get('age', 'نامعلوم')}")
    elif text == "📖 داستان محفل":
        bot.send_message(uid, "🕯 محفل سایه‌ها جایی برای گفتگوهای بدون نقابه...")
    elif text == "📢 طنین مدیریت" and uid == OWNER_ID:
        db["users"][uid]["state"] = "admin_bc"; save_db(db)
        bot.send_message(uid, "📢 پیام همگانی رو بنویس:")
    elif user.get("state") == "admin_bc" and uid == OWNER_ID:
        db["users"][uid]["state"] = "main"; save_db(db)
        for u in db["users"]:
            try: bot.send_message(u, f"📢 **طنین مدیریت:**\n\n{text}")
            except: pass
        bot.send_message(uid, "✅ طنین‌انداز شد.", reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    if call.data == "manage_banned" and uid == OWNER_ID:
        if not db["banned"]: bot.answer_callback_query(call.id, "لیست سیاه خالی است."); return
        btn = types.InlineKeyboardMarkup()
        for b_id in db["banned"]: btn.add(types.InlineKeyboardButton(f"🔓 حذف {b_id}", callback_data=f"unban_{b_id}"))
        bot.send_message(uid, "🚫 لیست سیاه:", reply_markup=btn)

    elif call.data.startswith("unban_"):
        target = call.data.split("_")[1]
        if target in db["banned"]: db["banned"].remove(target); save_db(db)
        bot.edit_message_text(f"✅ {target} بخشیده شد.", uid, call.message.id)

    elif call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(uid, f)

    elif call.data == "verify_join":
        if check_sub(uid): bot.delete_message(uid, call.message.id); bot.send_message(uid, "🔓 خوش آمدی.", reply_markup=main_menu(uid))

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"})
        save_db(db); bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "🕯 حالا سن خودت رو به عدد بفرست:")

    elif call.data == "send_conf":
        target = db["users"][uid].get("target"); msg = db["users"][uid].get("temp_msg")
        sent_msg = bot.send_message(target, f"📬 **رازِ جدید:**\n\n{msg}\n\n💡 برای جواب، ریپلای کن.")
        db["users"][target]["last_anon_msg_id"] = sent_msg.message_id
        save_db(db); db["users"][uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("✅ ارسال شد.", uid, call.message.id); bot.send_message(uid, "🏡", reply_markup=main_menu(uid))

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        pref_key = "male" if pref == "m" else ("female" if pref == "f" else "any")
        bot.edit_message_text("🔍 در حال جستجو...", uid, call.message.id)
        # پاک کردن کاربر از تمام صف‌های قبلی برای جلوگیری از همپوشانی
        for k in db["queue"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        
        # پیدا کردن هدف بر اساس جنسیت درخواستی
        target_pool = db["queue"]["male"] if pref_key == "male" else (db["queue"]["female"] if pref_key == "female" else (db["queue"]["male"] + db["queue"]["female"]))
        match = next((u for u in target_pool if u != uid), None)
        
        if match:
            for k in db["queue"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 وصل شدید!", reply_markup=chat_menu())
            bot.send_message(match, "💎 وصل شدید!", reply_markup=chat_menu())
        else:
            # کاربر را بر اساس جنسیت خودش در صف انتظار قرار بده
            my_sex = db["users"][uid].get("gender")
            # اگر کاربر به دنبال جنس مخالف است، در صف مخصوص اون جنسیت قرار بگیرد
            db["queue"][pref_key if pref_key != "any" else my_sex].append(uid)
            save_db(db)
            bot.send_message(uid, "🕯 کسی پیدا نشد، در صف انتظار ماندی...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("لغو ❌", callback_data="cancel_search")))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        chat_id = f"{min(uid, p)}_{max(uid, p)}"
        if chat_id in db.get("chat_history", {}): del db["chat_history"][chat_id]
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][p].update({"state": "main", "partner": None})
        save_db(db); bot.send_message(uid, "قطع شد.", reply_markup=main_menu(uid)); bot.send_message(p, "قطع شد.", reply_markup=main_menu(p))

    elif call.data.startswith("report_"):
        reason = call.data.replace("report_", "")
        partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = "\n".join(db.get("chat_history", {}).get(chat_id, ["تاریخچه‌ای یافت نشد."]))
        report_msg = f"🚩 **گزارش تخلف**\n\n👤 شاکی: `{uid}`\n👤 متهم: `{partner}`\n📂 دلیل: {reason}\n\n📝 **۱۰ پیام آخر (با آیدی فرستنده):**\n{history}"
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚫 BAN", callback_data=f"adminban_{partner}"), types.InlineKeyboardButton("✅ نادیده گرفتن", callback_data="adminignore"))
        bot.send_message(OWNER_ID, report_msg, reply_markup=btn)
        bot.edit_message_text("✅ گزارش ارسال شد.", uid, call.message.id)

    elif call.data.startswith("adminban_"):
        target = call.data.split("_")[1]
        if target not in db["banned"]: db["banned"].append(target); save_db(db)
        bot.answer_callback_query(call.id, "بلاک شد.")

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
