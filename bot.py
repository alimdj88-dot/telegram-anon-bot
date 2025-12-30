import telebot
from telebot import types
import json, os, random, datetime
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "🕯 قلب محفل سایه‌ها در حال تپیدن است..."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)

DB_PATH = "shadow_data.json"

def get_db():
    if not os.path.exists(DB_PATH): 
        db = {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": [], "chat_history": {}, "anon_msgs": {}}
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "banned" not in data: data["banned"] = []
            if "chat_history" not in data: data["chat_history"] = {}
            if "queue" not in data: data["queue"] = {"male": [], "female": [], "any": []}
            if "anon_msgs" not in data: data["anon_msgs"] = {}
            return data
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": [], "chat_history": {}, "anon_msgs": {}}

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

    # --- بخش مدیریت ریپلای اصلاح شده ---
    if message.reply_to_message:
        target_uid = None
        # پیدا کردن کسی که پیامِ ریپلای شده متعلق به اوست (یعنی کسی که پیام اصلی یا جواب قبلی رو فرستاده)
        for u_id, u_data in db["users"].items():
            if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id:
                target_uid = u_id
                break
        
        if target_uid:
            try:
                bot.send_message(target_uid, "💬 **پاسخی در سایه‌ها:**")
                sent_msg = bot.copy_message(target_uid, uid, message.message_id)
                # آپدیت آیدی پیام جدید برای طرف مقابل تا او هم بتواند ریپلای کند
                db["users"][target_uid]["last_anon_msg_id"] = sent_msg.message_id
                save_db(db)
                bot.send_message(uid, "✅ پیامت با موفقیت در سایه‌ها منتقل شد.")
                return
            except:
                bot.send_message(uid, "🎭 متاسفانه ارتباط در سایه‌ها قطع شده است.")
                return

    if text and text.startswith("/start"):
        if uid in db["users"] and db["users"][uid].get("state") == "in_chat":
            bot.send_message(uid, "🕯 شما در اعماق یک گفتگو هستید. برای بازگشت به تالار، ابتدا رشته اتصال را قطع کنید.")
            return

        if len(text.split()) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}
                save_db(db)
                bot.send_message(uid, "🕯 **به محفل سایه‌ها خوش آمدی، غریبه...**\n\nاینجا جاییه که نقاب‌ها می‌افته و روح‌ها بدون ترس از قضاوت با هم حرف می‌زنن. برای ثبت نام در کتیبه محفل، اسمی مستعار برای خودت انتخاب کن:\n\n👤 **نام مستعارت رو اینجا بنویس:**")
                return
            bot.send_message(uid, "🗝 درهای تالار به روی تو باز است. سایه‌ها منتظر شنیدن صدای تو هستند...", reply_markup=main_menu(uid))
            return

        code = text.split()[1]
        target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
        if target == uid:
            bot.send_message(uid, "🎭 ای شیطون! داری برای خودت نامه می‌نویسی؟ این لینک رو پخش کن تا بقیه برات اعتراف کنن!")
            return
        if target:
            db["users"][uid] = db["users"].get(uid, {"state": "main"})
            db["users"][uid].update({"state": "writing_confession", "target": target})
            save_db(db)
            bot.send_message(uid, "🕯 در خلوتگاه او هستی... هر چه در دل داری بنویس. هویت تو مثل یک رازِ مقدس محفوظ می‌مونه.", reply_markup=types.ReplyKeyboardRemove())
            return

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
            else: bot.send_message(uid, "🎭 مسافر عزیز، سن رو فقط به صورت عدد بفرست.")
            return

    user = db["users"].get(uid)
    if not user: return

    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن ❌", callback_data="confirm_end"), types.InlineKeyboardButton("نه، بمان 🕯", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 آیا مطمئنی می‌خوای این رشته‌ی اتصال رو پاره کنی و به دنیای سایه‌ها برگردی؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=2)
            reasons = ["توهین و بی‌ادبی 🤬", "تبلیغات 📢", "محتوای نامناسب 🔞", "مزاحمت ❌"]
            btns = [types.InlineKeyboardButton(r, callback_data=f"report_{r}") for r in reasons]
            btn.add(*btns)
            btn.add(types.InlineKeyboardButton("بی‌خیال، لغو گزارش 🔙", callback_data="cancel_end"))
            bot.send_message(uid, "🚩 دلیل گزارش رو انتخاب کن تا نگهبان‌ها بررسی کنن:", reply_markup=btn)
        else:
            chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
            if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
            if text:
                db["chat_history"][chat_id].append(f"🆔{uid} | {text}")
                if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
                save_db(db)
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    if user.get("state") == "writing_confession" and text:
        db["users"][uid].update({"state": "confirm_confession", "temp_msg": text})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بفرست بره 🚀", callback_data="send_conf"), types.InlineKeyboardButton("پشیمون شدم ❌", callback_data="cancel_conf"))
        bot.send_message(uid, f"📜 متنت رو با دقت خوندم. بفرستمش برای صاحب راز؟\n\n📝 متن تو:\n{text}", reply_markup=btn)
        return

    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_m"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_f"))
        btn.add(types.InlineKeyboardButton("هر کسی که شد 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 رادارهای محفل رو برای پیدا کردن یک هم‌فرکانس روشن کردم. کی مد نظرته؟", reply_markup=btn)
    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(111111, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینکِ اعترافات ناشناس تو آماده‌ست! بزارش توی بیو تا بقیه برات بنویسن:\n\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif text == "🎈 ویترین من":
        sex = "شوالیه 👦" if user.get("gender") == "male" else "بانو 👧"
        bot.send_message(uid, f"📜 **کتیبه هویت تو در دفتر محفل:**\n\n👤 اسم مستعار: {user['name']}\n🎭 جنسیت: {sex}\n🎂 سن: {user.get('age', 'نامعلوم')}")
    elif text == "📖 داستان محفل":
        bot.send_message(uid, "🕯 محفل سایه‌ها جایی برای گفتگوهای بدون نقابه. اینجا هویت تو مخفیه تا بتونی بلندترین فریادهای دلت رو به گوش بقیه برسونی.")

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    if call.data == "verify_join":
        if check_sub(uid):
            bot.delete_message(uid, call.message.id)
            bot.send_message(uid, "🔓 درهای تالار باز شد! خوش آمدی.", reply_markup=main_menu(uid))
        else: bot.answer_callback_query(call.id, "❌ هنوز عضو کانال نشدی مسافر!", show_alert=True)

    # --- اصلاح دکمه مشاهده برای فعالسازی ریپلای ---
    elif call.data.startswith("view_msg_"):
        sender_id = call.data.split("_")[2]
        msg_text = db["anon_msgs"].get(call.data)
        if msg_text:
            # ذخیره آیدی پیام برای گیرنده، تا وقتی روی این پیام ریپلای میکند ربات بشناسد
            db["users"][uid]["last_anon_msg_id"] = call.message.id
            save_db(db)
            
            bot.edit_message_text(f"📬 **یه رازِ ناشناس:**\n\n{msg_text}\n\n➖➖➖➖➖➖\n💡 برای جواب دادن، روی همین پیام ریپلای کن.", uid, call.message.id)
            bot.send_message(sender_id, "👁‍🗨 قاصدک تو به مقصد رسید و توسط صاحب راز رویت شد.")
        else:
            bot.answer_callback_query(call.id, "🎭 این راز قدیمی شده است.")

    elif call.data == "send_conf":
        target = db["users"][uid].get("target"); msg = db["users"][uid].get("temp_msg")
        try:
            msg_id_key = f"view_msg_{uid}_{random.randint(1000,9999)}"
            db["anon_msgs"][msg_id_key] = msg
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👁 مشاهده پیام", callback_data=msg_id_key))
            bot.send_message(target, "📬 **یک پیام ناشناس جدید در سایه‌ها منتظر توست...**", reply_markup=btn)
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.edit_message_text("✅ قاصدک تو به مقصد رسید!", uid, call.message.id)
            bot.send_message(uid, "🏡 بازگشت به منو", reply_markup=main_menu(uid))
        except: bot.send_message(uid, "🎭 نشد برسونم...")

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"})
        save_db(db); bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "🕯 حالا سن خودت رو به عدد برای کتیبه بفرست:")

    elif call.data == "cancel_conf":
        db["users"][uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("❌ منصرف شدی.", uid, call.message.id)
        bot.send_message(uid, "🏡", reply_markup=main_menu(uid))

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        pref_key = "male" if pref == "m" else ("female" if pref == "f" else "any")
        bot.edit_message_text("🔍 در حال جستجوی یک روح سرگردان...", uid, call.message.id)
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        
        my_gender = db["users"][uid].get("gender")
        target_pool = db["queue"]["any"] + db["queue"][my_gender]
        match = next((u for u in target_pool if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key)), None)
        
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 وصل شدی! گپ رو شروع کن.", reply_markup=chat_menu())
            bot.send_message(match, "💎 وصل شدی! گپ رو شروع کن.", reply_markup=chat_menu())
        else:
            db["queue"][pref_key].append(uid)
            save_db(db)
            bot.send_message(uid, "🕯 کسی پیدا نشد، در صف ماندی...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("لغو جستجو ❌", callback_data="cancel_search")))

    elif call.data == "cancel_search":
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        save_db(db)
        bot.edit_message_text("❌ لغو شد.", uid, call.message.id)
        bot.send_message(uid, "🏡", reply_markup=main_menu(uid))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None})
        db["users"][p].update({"state": "main", "partner": None})
        save_db(db)
        bot.send_message(uid, "رشته اتصال پاره شد.", reply_markup=main_menu(uid))
        bot.send_message(p, "طرف مقابل چت رو تموم کرد.", reply_markup=main_menu(p))

    elif call.data == "cancel_end":
        bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "🕯 به گفتگو ادامه بده.")

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
