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
            for key in ["banned", "chat_history"]:
                if key not in data: data[key] = [] if key == "banned" else {}
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

    # مدیریت ادمین
    if uid == OWNER_ID and text == "📊 آمار و دیتابیس":
        m = sum(1 for u in db["users"].values() if u.get("gender") == "male")
        f = sum(1 for u in db["users"].values() if u.get("gender") == "female")
        stats = f"📜 **وضعیت اهالی محفل سایه‌ها:**\n\n👥 کل کاربران: {len(db['users'])}\n👦 شوالیه‌ها: {m}\n👧 بانوها: {f}\n🚫 لیست سیاه: {len(db['banned'])}"
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("📥 دریافت دیتابیس", callback_data="get_db_file"))
        btn.add(types.InlineKeyboardButton("🚫 مدیریت لیست سیاه", callback_data="manage_banned"))
        bot.send_message(uid, stats, reply_markup=btn)
        return

    # سیستم استارت و ثبت‌نام
    if text and text.startswith("/start"):
        if uid in db["users"] and db["users"][uid].get("state") == "in_chat":
            bot.send_message(uid, "🕯 شما در میان یک گفتگو هستید. ابتدا با دکمه قطع ارتباط، به تالار بازگردید.")
            return

        if len(text.split()) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}
                save_db(db)
                bot.send_message(uid, "🕯 **به محفل سایه‌ها خوش آمدی، مسافر...**\n\nاینجا جاییه که نقاب‌ها می‌افته و روح‌ها بدون ترس از قضاوت با هم حرف می‌زنن. برای ورود به تالار، باید اسمی برای خودت انتخاب کنی.\n\n👤 **یک نام مستعار برای خودت بنویس:**")
                return
            else:
                bot.send_message(uid, "🗝 به تالار اصلی خوش آمدی. سایه‌ها منتظر شنیدن صدای تو هستند...", reply_markup=main_menu(uid))
                return

        # لینک ناشناس
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

    # هندل کردن مراحل ثبت نام
    if uid in db["users"] and db["users"][uid].get("state") in ["reg_name", "reg_gender", "reg_age"]:
        state = db["users"][uid]["state"]
        if state == "reg_name":
            db["users"][uid].update({"name": text[:20], "state": "reg_gender"})
            save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه (آقا) 👦", callback_data="set_m"), types.InlineKeyboardButton("بانو (خانم) 👧", callback_data="set_f"))
            bot.send_message(uid, f"✨ خوش‌آمدی {text}. حالا بگو در این محفل شوالیه‌ای یا بانو؟", reply_markup=btn)
            return
        if state == "reg_age":
            if text and text.isdigit():
                db["users"][uid].update({"age": text, "state": "main"})
                save_db(db)
                bot.send_message(uid, "📜 نامت در کتیبه محفل ثبت شد. حالا وقتشه هم‌فرکانس خودت رو پیدا کنی!", reply_markup=main_menu(uid))
            else: bot.send_message(uid, "🎭 سن رو فقط به صورت عدد بفرست.")
            return

    user = db["users"].get(uid)
    if not user: return

    # بخش اعتراف (تأیید پیام)
    if user.get("state") == "writing_confession" and text:
        db["users"][uid].update({"state": "confirm_confession", "temp_msg": text})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بفرست بره 🚀", callback_data="send_conf"), types.InlineKeyboardButton("پشیمون شدم ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"📜 متنت رو با دقت خوندم. بفرستمش برای صاحب راز؟\n\n📝 متن تو:\n{text}", reply_markup=btn)
        return

    # سیستم چت دو نفره
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن ❌", callback_data="confirm_end"), types.InlineKeyboardButton("نه، بمان 🕯", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 آیا مطمئنی می‌خوای این رشته‌ی اتصال رو پاره کنی؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=1)
            reasons = ["توهین و بی‌ادبی 🤬", "تبلیغات مزاحم 📢", "محتوای نامناسب 🔞", "مزاحمت ❌", "لغو گزارش 🔙"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"report_{r}"))
            bot.send_message(uid, "🚩 دلیل گزارش رو انتخاب کن تا نگهبان‌ها بررسی کنن:", reply_markup=btn)
        else:
            chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
            if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
            if text:
                db["chat_history"][chat_id].append(f"ID:{uid} | {text}")
                if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
                save_db(db)
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # پاسخ به پیام ناشناس (ریپلای)
    if message.reply_to_message:
        target_uid = next((u for u, d in db["users"].items() if d.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            try:
                sent_msg = bot.send_message(target_uid, f"💌 **پاسخی جدید در خلوتگاه تو طنین‌انداز شد:**\n\n{text}\n\n➖➖➖➖➖➖\n💡 می‌تونی با ریپلای کردن، ادامه بدی.")
                db["users"][target_uid]["last_anon_msg_id"] = sent_msg.message_id
                save_db(db); bot.send_message(uid, "✅ پیامت منتقل شد.")
            except: bot.send_message(uid, "🎭 ارتباط قطع شده...")
            return

    # منوی اصلی
    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_m"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_f"))
        btn.add(types.InlineKeyboardButton("هر کسی که شد 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 دنبال چه کسی می‌گردی؟ رادارهای محفل رو روشن کردم...", reply_markup=btn)
    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(111111, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینکِ اعترافات ناشناس تو آماده‌ست! بزارش توی بیو تا بقیه برات بنویسن:\n\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif text == "🎈 ویترین من":
        sex = "شوالیه 👦" if user.get("gender") == "male" else "بانو 👧"
        bot.send_message(uid, f"📜 **کتیبه هویت تو:**\n\n👤 نام مستعار: {user['name']}\n🎭 جنسیت: {sex}\n🎂 سن: {user.get('age', 'نامعلوم')}")
    elif text == "📖 داستان محفل":
        bot.send_message(uid, "🕯 محفل سایه‌ها جایی برای گفتگوهای بدون نقابه. اینجا هویت تو مخفیه تا بتونی بلندترین فریادهای دلت رو به گوش بقیه برسونی.")
    elif text == "📢 طنین مدیریت" and uid == OWNER_ID:
        db["users"][uid]["state"] = "admin_bc"; save_db(db)
        bot.send_message(uid, "📢 پیامی که می‌خوای در کل تالار پخش بشه رو بنویس:")
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
        for b_id in db["banned"]: btn.add(types.InlineKeyboardButton(f"🔓 بخشش {b_id}", callback_data=f"unban_{b_id}"))
        bot.send_message(uid, "🚫 لیست سیاه محفل:", reply_markup=btn)

    elif call.data.startswith("unban_"):
        target = call.data.split("_")[1]
        if target in db["banned"]: db["banned"].remove(target); save_db(db)
        bot.edit_message_text(f"✅ {target} به محفل برگشت.", uid, call.message.id)

    elif call.data == "get_db_file" and uid == OWNER_ID:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f: bot.send_document(uid, f, caption="📂 دیتابیس کامل محفل.")

    elif call.data == "verify_join":
        if check_sub(uid): bot.delete_message(uid, call.message.id); bot.send_message(uid, "🔓 خوش آمدی مسافر.", reply_markup=main_menu(uid))

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"})
        save_db(db); bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "🕯 حالا سن خودت رو به عدد بفرست:")

    elif call.data == "send_conf":
        target = db["users"][uid].get("target"); msg = db["users"][uid].get("temp_msg")
        try:
            sent_msg = bot.send_message(target, f"📬 **یه رازِ ناشناس برای تو رسید:**\n\n{msg}\n\n➖➖➖➖➖➖\n💡 برای جواب دادن، ریپلای کن.")
            db["users"][target]["last_anon_msg_id"] = sent_msg.message_id
            save_db(db); db["users"][uid]["state"] = "main"; save_db(db)
            bot.edit_message_text("✅ قاصدک تو به مقصد رسید!", uid, call.message.id)
            bot.send_message(uid, "🏡 بازگشت به منوی اصلی", reply_markup=main_menu(uid))
        except: bot.send_message(uid, "🎭 ارسال نشد.")

    elif call.data == "cancel_conf":
        db["users"][uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("❌ منصرف شدی. پیام پاک شد.", uid, call.message.id)
        bot.send_message(uid, "🏡 منوی اصلی", reply_markup=main_menu(uid))

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        pref_key = "male" if pref == "m" else ("female" if pref == "f" else "any")
        bot.edit_message_text("🔍 در حال جستجوی روحی سرگردان در اعماق محفل...", uid, call.message.id)
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        
        # پیدا کردن کسی که دنبال جنسیت من میگرده
        my_gender = db["users"][uid].get("gender")
        target_pool = db["queue"][my_gender] + db["queue"]["any"]
        match = next((u for u in target_pool if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key)), None)
        
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید.", reply_markup=chat_menu())
            bot.send_message(match, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید.", reply_markup=chat_menu())
        else:
            db["queue"][pref_key].append(uid)
            save_db(db)
            bot.send_message(uid, "🕯 کسی پیدا نشد، در صف انتظار ماندی...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("لغو جستجو ❌", callback_data="cancel_search")))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        chat_id = f"{min(uid, p)}_{max(uid, p)}"
        if chat_id in db.get("chat_history", {}): del db["chat_history"][chat_id]
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][p].update({"state": "main", "partner": None})
        save_db(db); bot.send_message(uid, "رشته اتصال پاره شد.", reply_markup=main_menu(uid)); bot.send_message(p, "هم‌صحبت تو چت رو تموم کرد.", reply_markup=main_menu(p))

    elif call.data.startswith("report_"):
        reason = call.data.replace("report_", "")
        partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = "\n".join(db.get("chat_history", {}).get(chat_id, ["تاریخچه‌ای نیست."]))
        bot.send_message(OWNER_ID, f"🚩 **گزارش**\nشاکی: `{uid}`\nمتهم: `{partner}`\nدلیل: {reason}\n\n📝 **پیام‌ها:**\n{history}", 
                         reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚫 BAN", callback_data=f"adminban_{partner}")))
        bot.edit_message_text("✅ گزارش ارسال شد.", uid, call.message.id)

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
