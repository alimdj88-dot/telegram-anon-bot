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

    # مدیریت داده‌ها برای ادمین
    if uid == OWNER_ID and text == "📊 آمار و دیتابیس":
        males = sum(1 for u in db["users"].values() if u.get("gender") == "male")
        females = sum(1 for u in db["users"].values() if u.get("gender") == "female")
        stats = f"📜 **وضعیت فعلی محفل:**\n\n👥 کل اعضا: {len(db['users'])}\n👦 شوالیه‌ها: {males}\n👧 بانوها: {females}\n🚫 لیست سیاه: {len(db['banned'])}"
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 دریافت فایل دیتابیس", callback_data="get_db_file"))
        bot.send_message(uid, stats, reply_markup=btn)
        return

    if text and text.startswith("/start "):
        code = text.split()[1]
        target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
        if target and target != uid:
            db["users"][uid] = db["users"].get(uid, {"state": "main"})
            db["users"][uid].update({"state": "writing_confession", "target": target})
            save_db(db)
            bot.send_message(uid, "🕯 در خلوتگاه او هستی... بنویس تا من به گوشش برسانم.", reply_markup=types.ReplyKeyboardRemove())
            return

    if uid not in db["users"] or "name" not in db["users"][uid] or db["users"][uid].get("state") in ["reg_name", "reg_gender", "reg_age"]:
        if uid not in db["users"]: db["users"][uid] = {"state": "reg_name"}
        state = db["users"][uid]["state"]
        if state == "reg_name":
            if text == "/start": bot.send_message(uid, "🕯 به محفل سایه‌ها خوش آمدی... نامی مستعار انتخاب کن:")
            else:
                db["users"][uid].update({"name": text[:20], "state": "reg_gender"})
                save_db(db)
                btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👦 شوالیه", callback_data="set_m"), types.InlineKeyboardButton("👧 بانو", callback_data="set_f"))
                bot.send_message(uid, "✨ خوش‌آمدی. جنسیتت رو مشخص کن:", reply_markup=btn)
            return
        if state == "reg_age":
            if text and text.isdigit():
                db["users"][uid].update({"age": text, "state": "main"})
                save_db(db)
                bot.send_message(uid, "📜 ثبت شد! بریم برای شروع؟", reply_markup=main_menu(uid))
            else: bot.send_message(uid, "🎭 فقط عدد بفرست.")
            return
        return

    user = db["users"][uid]
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله", callback_data="confirm_end"), types.InlineKeyboardButton("خیر", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 از قطع اتصال مطمئنی؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=1)
            reasons = ["توهین 🤬", "تبلیغات 📢", "نامناسب 🔞", "لغو 🔙"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"report_{r}"))
            bot.send_message(uid, "🚩 دلیل گزارش رو انتخاب کن:", reply_markup=btn)
        else:
            # ذخیره چت برای نظارت در صورت گزارش
            chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
            if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
            if text:
                db["chat_history"][chat_id].append(f"{db['users'][uid]['name']}: {text}")
                if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
                save_db(db)
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    if user.get("state") == "writing_confession" and text:
        db["users"][uid].update({"state": "confirm_confession", "temp_msg": text})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بفرست بره 🚀", callback_data="send_conf"), types.InlineKeyboardButton("لغو ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"📝 متن تو:\n{text}\n\nبفرستمش؟", reply_markup=btn)
        return

    if message.reply_to_message:
        for u_id, u_data in db["users"].items():
            if u_data.get("last_anon_msg_id") == message.reply_to_message.message_id:
                bot.send_message(u_id, f"💌 جواب ناشناس:\n\n{text}")
                bot.send_message(uid, "✅ ارسال شد.")
                return

    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("👦 شوالیه", callback_data="hunt_m"), types.InlineKeyboardButton("👧 بانو", callback_data="hunt_f"), types.InlineKeyboardButton("🌈 هر دو", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 دنبال کی می‌گردی؟", reply_markup=btn)
    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(111111, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینک ناشناس تو:\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif text == "🎈 ویترین من":
        bot.send_message(uid, f"👤 نام: {user['name']}\n🎂 سن: {user.get('age')}")
    elif text == "📢 طنین مدیریت" and uid == OWNER_ID:
        db["users"][uid]["state"] = "admin_bc"
        save_db(db)
        bot.send_message(uid, "📢 پیام همگانی رو بنویس:")

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    if call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(uid, f)

    elif call.data.startswith("report_"):
        reason = call.data.replace("report_", "")
        if "لغو" in reason: bot.edit_message_text("لغو شد.", uid, call.message.id)
        else:
            partner = db["users"][uid].get("partner")
            chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
            history = "\n".join(db["chat_history"].get(chat_id, ["پیام متنی یافت نشد"]))
            report_text = f"🚩 **گزارش جدید**\n\n👤 شاکی: `{uid}`\n👤 متهم: `{partner}`\n📂 دلیل: {reason}\n\n📝 **آخرین پیام‌ها:**\n{history}"
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚫 BAN", callback_data=f"adminban_{partner}"), types.InlineKeyboardButton("✅ رد گزارش", callback_data="adminignore"))
            bot.send_message(OWNER_ID, report_text, reply_markup=btn)
            bot.edit_message_text("✅ گزارش ارسال شد.", uid, call.message.id)

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        chat_id = f"{min(uid, p)}_{max(uid, p)}"
        if chat_id in db["chat_history"]: del db["chat_history"][chat_id]
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][p].update({"state": "main", "partner": None})
        save_db(db)
        bot.send_message(uid, "اتصال قطع شد.", reply_markup=main_menu(uid))
        bot.send_message(p, "هم‌صحبت چت رو بست.", reply_markup=main_menu(p))

    elif call.data.startswith("adminban_"):
        target = call.data.split("_")[1]
        if target not in db["banned"]: db["banned"].append(target)
        save_db(db)
        bot.answer_callback_query(call.id, "مسدود شد.")
        bot.send_message(target, "🚫 شما مسدود شدید.")

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        pref_key = "male" if pref == "m" else ("female" if pref == "f" else "any")
        bot.edit_message_text("🔍 در حال جستجو...", uid, call.message.id)
        target_pool = db["queue"][pref_key] if pref_key != "any" else (db["queue"]["male"] + db["queue"]["female"])
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
            my_sex = db["users"][uid].get("gender")
            db["queue"][my_sex if pref_key == "any" else pref_key].append(uid)
            save_db(db)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
