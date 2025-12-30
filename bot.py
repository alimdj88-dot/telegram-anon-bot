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

    # بررسی عضویت اجباری
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("عضویت در کانال اعلانات 📢", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو 🔓", callback_data="verify_join"))
        bot.send_message(uid, "✨ مسافر عزیز! برای ورود به تالار اصلی محفل، ابتدا باید در کانال ما حضور داشته باشی. منتظرت هستیم...", reply_markup=btn)
        return

    # منوی ادمین
    if uid == OWNER_ID and text == "📊 آمار و دیتابیس":
        m = sum(1 for u in db["users"].values() if u.get("gender") == "male")
        f = sum(1 for u in db["users"].values() if u.get("gender") == "female")
        stats = f"📜 **آمار محفل:**\n\n👥 کل کاربران: {len(db['users'])}\n👦 شوالیه‌ها: {m}\n👧 بانوها: {f}\n🚫 لیست سیاه: {len(db['banned'])}"
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("📥 دریافت فایل دیتابیس", callback_data="get_db_file"))
        btn.add(types.InlineKeyboardButton("🚫 مدیریت لیست سیاه", callback_data="manage_banned"))
        bot.send_message(uid, stats, reply_markup=btn)
        return

    # هندل کردن /start
    if text and text.startswith("/start"):
        if uid in db["users"] and db["users"][uid].get("state") == "in_chat":
            bot.send_message(uid, "🕯 شما در حال گفتگو هستید. ابتدا ارتباط را قطع کنید.")
            return

        if len(text.split()) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}
                save_db(db)
                bot.send_message(uid, "🕯 **به محفل سایه‌ها خوش آمدی...**\n\nنام مستعار خود را وارد کن:")
                return
            bot.send_message(uid, "🗝 به تالار اصلی خوش آمدی.", reply_markup=main_menu(uid))
            return

        # لینک ناشناس
        code = text.split()[1]
        target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
        if target == uid:
            bot.send_message(uid, "🎭 برای خودت نامه ننویس شیطون!")
            return
        if target:
            db["users"][uid] = db["users"].get(uid, {"state": "main"})
            db["users"][uid].update({"state": "writing_confession", "target": target})
            save_db(db)
            bot.send_message(uid, "🕯 در خلوتگاه او هستی... هر چه در دل داری بنویس.", reply_markup=types.ReplyKeyboardRemove())
            return

    # مراحل ثبت‌نام
    if uid in db["users"] and db["users"][uid].get("state") in ["reg_name", "reg_gender", "reg_age"]:
        state = db["users"][uid]["state"]
        if state == "reg_name":
            db["users"][uid].update({"name": text[:20], "state": "reg_gender"})
            save_db(db)
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه 👦", callback_data="set_m"), types.InlineKeyboardButton("بانو 👧", callback_data="set_f"))
            bot.send_message(uid, "✨ جنسیت خودت رو انتخاب کن:", reply_markup=btn)
            return
        if state == "reg_age":
            if text and text.isdigit():
                db["users"][uid].update({"age": text, "state": "main"})
                save_db(db)
                bot.send_message(uid, "📜 ثبت شد!", reply_markup=main_menu(uid))
            else: bot.send_message(uid, "🎭 فقط عدد بفرست.")
            return

    user = db["users"].get(uid)
    if not user: return

    # پاسخ به پیام ناشناس (رفع باگ ارسال نشدن)
    if message.reply_to_message:
        target_uid = None
        for u_id, u_data in db["users"].items():
            if u_data.get("last_anon_msg_id") == message.reply_to_message.message_id:
                target_uid = u_id
                break
        
        if target_uid:
            try:
                sent_msg = bot.send_message(target_uid, f"💌 **پاسخی جدید در خلوتگاه تو رسید:**\n\n{text}\n\n➖➖➖➖➖➖\n💡 ریپلای کن تا جواب بدی.")
                db["users"][target_uid]["last_anon_msg_id"] = sent_msg.message_id
                save_db(db)
                bot.send_message(uid, "✅ پیامت با موفقیت ارسال شد.")
                return
            except:
                bot.send_message(uid, "🎭 متاسفانه پیام ارسال نشد.")
                return

    # چت دو نفره
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله ❌", callback_data="confirm_end"), types.InlineKeyboardButton("خیر 🕯", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 قطع بشه؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup()
            btn.add(types.InlineKeyboardButton("توهین 🤬", callback_data="report_توهین"), types.InlineKeyboardButton("بی‌خیال 🔙", callback_data="cancel_end"))
            bot.send_message(uid, "🚩 دلیل گزارش؟", reply_markup=btn)
        else:
            chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
            if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
            if text:
                db["chat_history"][chat_id].append(f"[{uid}]: {text}")
                if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
                save_db(db)
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # نوشتن اعتراف
    if user.get("state") == "writing_confession" and text:
        db["users"][uid].update({"state": "confirm_confession", "temp_msg": text})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بفرست 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"📜 بفرستمش؟\n\n{text}", reply_markup=btn)
        return

    # دکمه‌های منو
    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_m"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_f"))
        btn.add(types.InlineKeyboardButton("هر دو 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 دنبال کی میگردی؟", reply_markup=btn)
    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(1111, 9999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینک تو:\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif text == "🎈 ویترین من":
        bot.send_message(uid, f"👤 نام: {user['name']}\n🎭 جنسیت: {user.get('gender')}")
    elif text == "📖 داستان محفل":
        bot.send_message(uid, "🕯 محفل سایه‌ها... جایی برای آزادی.")
    elif text == "📢 طنین مدیریت" and uid == OWNER_ID:
        db["users"][uid]["state"] = "admin_bc"; save_db(db)
        bot.send_message(uid, "📢 پیام همگانی رو بفرست:")
    elif user.get("state") == "admin_bc" and uid == OWNER_ID:
        db["users"][uid]["state"] = "main"; save_db(db)
        for u in db["users"]:
            try: bot.send_message(u, f"📢 **طنین:**\n{text}")
            except: pass
        bot.send_message(uid, "✅ ارسال شد.", reply_markup=main_menu(uid))

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    # تأیید جوین کانال (رفع مشکل دکمه)
    if call.data == "verify_join":
        if check_sub(uid):
            bot.delete_message(uid, call.message.id)
            bot.send_message(uid, "🔓 خوش آمدی!", reply_markup=main_menu(uid))
        else:
            bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)

    # دکمه‌های ادمین (رفع مشکل دکمه BAN و IGNORE)
    elif call.data.startswith("adminban_"):
        target = call.data.split("_")[1]
        if target not in db["banned"]: db["banned"].append(target)
        save_db(db)
        bot.answer_callback_query(call.id, "🚫 مسدود شد.")
        bot.edit_message_text(call.message.text + "\n\n✅ نتیجه: مسدود شد.", OWNER_ID, call.message.id)
    
    elif call.data == "adminignore":
        bot.edit_message_text(call.message.text + "\n\n✅ نتیجه: نادیده گرفته شد.", OWNER_ID, call.message.id)

    elif call.data == "manage_banned" and uid == OWNER_ID:
        if not db["banned"]: bot.answer_callback_query(call.id, "خالی است."); return
        btn = types.InlineKeyboardMarkup()
        for b in db["banned"]: btn.add(types.InlineKeyboardButton(f"🔓 حذف {b}", callback_data=f"unban_{b}"))
        bot.send_message(uid, "🚫 لیست سیاه:", reply_markup=btn)

    elif call.data.startswith("unban_"):
        target = call.data.split("_")[1]
        if target in db["banned"]: db["banned"].remove(target)
        save_db(db)
        bot.edit_message_text(f"✅ {target} آزاد شد.", uid, call.message.id)

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"})
        save_db(db); bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "🕯 سن خودت رو بفرست:")

    elif call.data == "send_conf":
        target = db["users"][uid].get("target")
        msg = db["users"][uid].get("temp_msg")
        try:
            sent_m = bot.send_message(target, f"📬 **راز جدید:**\n\n{msg}\n\n💡 ریپلای کن جواب بدی.")
            db["users"][target]["last_anon_msg_id"] = sent_m.message_id
            db["users"][uid]["state"] = "main"
            save_db(db)
            bot.edit_message_text("✅ ارسال شد.", uid, call.message.id)
            bot.send_message(uid, "🏡 بازگشت به منو", reply_markup=main_menu(uid))
        except: bot.send_message(uid, "❌ خطا در ارسال.")

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        pref_key = "male" if pref == "m" else ("female" if pref == "f" else "any")
        bot.edit_message_text("🔍 جستجو...", uid, call.message.id)
        
        # پاکسازی صف‌های قبلی
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
            
        my_gender = db["users"][uid].get("gender")
        # منطق درست شکار (فقط کسی که با ملاک ما بخوره)
        target_pool = db["queue"]["any"] + db["queue"][my_gender]
        match = next((u for u in target_pool if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key)), None)
        
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 وصل شدی!", reply_markup=chat_menu())
            bot.send_message(match, "💎 وصل شدی!", reply_markup=chat_menu())
        else:
            db["queue"][pref_key].append(uid)
            save_db(db)
            bot.send_message(uid, "🕯 در صف ماندی...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("لغو ❌", callback_data="cancel_search")))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][p].update({"state": "main", "partner": None})
        save_db(db)
        bot.send_message(uid, "قطع شد.", reply_markup=main_menu(uid))
        bot.send_message(p, "طرف مقابل قطع کرد.", reply_markup=main_menu(p))

    elif call.data == "report_":
        reason = call.data.split("_")[1]
        partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = "\n".join(db.get("chat_history", {}).get(chat_id, ["خالی"]))
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("🚫 BAN", callback_data=f"adminban_{partner}"), types.InlineKeyboardButton("✅ IGNORE", callback_data="adminignore"))
        bot.send_message(OWNER_ID, f"🚩 گزارش تخلف\nشاکی: {uid}\nمتهم: {partner}\nدلیل: {reason}\n\nپیام‌ها:\n{history}", reply_markup=btn)
        bot.answer_callback_query(call.id, "ارسال شد.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
