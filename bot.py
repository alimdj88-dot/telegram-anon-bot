import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- سامانه پایداری محفل ---
app = Flask('')
@app.route('/')
def home(): return "قلب محفل با قدرت می‌تپد"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- پیکربندی اصلی ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_USERNAME = "@ChatNaAnnouncements"
shadow_bot = telebot.TeleBot(API_TOKEN)

DATA_PATH = "users_db.json"
waiting_room = {"male": [], "female": [], "any": []}

def load_shadow_data():
    if not os.path.exists(DATA_PATH): return {}
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        try: return json.load(file)
        except: return {}

def save_shadow_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def check_subscription(user_id):
    if str(user_id) == OWNER_ID: return True
    try:
        member = shadow_bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return member in ['member', 'administrator', 'creator']
    except: return False

# --- کیبوردهای محفل ---
def get_main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛰 شکار هم‌صحبت", "🤫 ایستگاه اعتراف")
    markup.add("🎈 ویترین من", "📖 داستان محفل")
    if str(uid) == OWNER_ID: markup.add("📢 طنین مدیریت")
    return markup

def get_chat_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✂️ قطع ارتباط", "🚩 گزارش تخلف")
    return markup

# --- موتور اصلی ---
@shadow_bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def core_processor(message):
    uid = str(message.chat.id)
    db = load_shadow_data()
    msg_text = message.text

    if not check_subscription(message.chat.id):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("ورود به کانال محفل", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        btn.add(types.InlineKeyboardButton("عضو شدم 🔓", callback_data="verify_sub"))
        shadow_bot.send_message(uid, "سلام! واسه ورود به محفل، اول باید توی کانال ما عضو بشی.", reply_markup=btn)
        return

    # لینک ناشناس
    if msg_text and msg_text.startswith("/start "):
        secret_code = msg_text.split()[1]
        target_uid = next((u for u, d in db.items() if d.get("link") == secret_code), None)
        if target_uid == uid:
            shadow_bot.send_message(uid, "به خودت که نمی‌تونی پیام ناشناس بدی رفیق!")
            return
        if target_uid:
            db[uid] = db.get(uid, {"state": "main"})
            db[uid].update({"state": "writing_anonymous", "target_recipient": target_uid})
            save_shadow_data(db)
            shadow_bot.send_message(uid, "در خلوتگاه او هستی... بنویس تا من ناشناس بهش برسونم.", reply_markup=types.ReplyKeyboardRemove())
            return

    # ثبت‌نام
    if uid not in db or "name" not in db[uid] or db[uid].get("state") in ["set_name", "set_gender", "set_age"]:
        if uid not in db: db[uid] = {"state": "set_name"}
        if db[uid]["state"] == "set_name":
            if msg_text == "/start": shadow_bot.send_message(uid, "سلام! یه اسم مستعار جذاب برام بفرست:")
            else:
                db[uid].update({"name": msg_text[:20], "state": "set_gender"})
                save_shadow_data(db)
                btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه (آقا) 👦", callback_data="gender_male"), types.InlineKeyboardButton("بانو (خانم) 👧", callback_data="gender_female"))
                shadow_bot.send_message(uid, f"خوشبختم {msg_text} جان! حالا بگو شوالیه‌ای یا بانو؟", reply_markup=btn)
            return
        if db[uid]["state"] == "set_age":
            if msg_text and msg_text.isdigit():
                db[uid].update({"age": msg_text, "state": "main"})
                save_shadow_data(db)
                shadow_bot.send_message(uid, "ثبت نامت تموم شد! بریم واسه گپ زدن؟", reply_markup=get_main_keyboard(uid))
            else: shadow_bot.send_message(uid, "سن رو فقط به عدد بفرست.")
            return
        return

    user_info = db[uid]

    # ریپلای ناشناس
    if message.reply_to_message and "کد راز:" in (message.reply_to_message.text or ""):
        try:
            original_sender = message.reply_to_message.text.split("کد راز:")[1].strip()
            shadow_bot.send_message(original_sender, f"💌 صاحبِ راز به پیام تو جواب داد:\n\n{msg_text}")
            shadow_bot.send_message(uid, "✅ جوابت ناشناس ارسال شد.")
        except: shadow_bot.send_message(uid, "نشد برسونم.")
        return

    # طنین مدیریت
    if msg_text == "📢 طنین مدیریت" and uid == OWNER_ID:
        db[uid]["state"] = "broadcast_mode"
        save_shadow_data(db)
        shadow_bot.send_message(uid, "پیامی که می‌خوای به کل محفل برسه رو بنویس:", reply_markup=types.ReplyKeyboardRemove())
        return
    if user_info.get("state") == "broadcast_mode" and uid == OWNER_ID:
        db[uid]["state"] = "main"
        save_shadow_data(db)
        for user_id in db:
            try: shadow_bot.send_message(user_id, f"📢 **طنین مدیریت:**\n\n{msg_text}")
            except: pass
        shadow_bot.send_message(uid, "ارسال شد!", reply_markup=get_main_keyboard(uid))
        return

    # ویترین من (اصلاح شده)
    if msg_text == "🎈 ویترین من":
        gender_str = "آقا 👦" if user_info.get("gender") == "male" else "خانم 👧"
        shadow_bot.send_message(uid, f"📜 **کتیبه هویت تو:**\n\n👤 اسم: {user_info.get('name')}\n🎭 جنسیت: {gender_str}\n🎂 سن: {user_info.get('age')}\n\nهمه چی درسته؟")

    # چت و گزارش
    if user_info.get("state") == "active_chat":
        partner_id = user_info.get("partner_id")
        if msg_text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آره، قطع کن", callback_data="quit_yes"), types.InlineKeyboardButton("نه، پشیمون شدم", callback_data="quit_no"))
            shadow_bot.send_message(uid, "مطمئنی می‌خوای گپ رو تموم کنی؟", reply_markup=btn)
        elif msg_text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=1)
            reasons = ["توهین 🤬", "تبلیغات 📢", "نامناسب 🔞", "مزاحمت ❌", "لغو گزارش 🔙"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r}"))
            shadow_bot.send_message(uid, "دلیل گزارش رو انتخاب کن:", reply_markup=btn)
        else:
            try: shadow_bot.copy_message(partner_id, uid, message.message_id)
            except: pass
        return

    # شکار هم‌صحبت
    if msg_text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="find_male"), types.InlineKeyboardButton("بانوها 👧", callback_data="find_female"))
        btn.add(types.InlineKeyboardButton("هر کی که شد 🌈", callback_data="find_any"))
        shadow_bot.send_message(uid, "دنبال چه هم‌صحبتی می‌گردی؟", reply_markup=btn)

# --- مدیریت دکمه‌های شیشه‌ای ---
@shadow_bot.callback_query_handler(func=lambda c: True)
def interaction_handler(call):
    uid = str(call.message.chat.id); db = load_shadow_data()
    if call.data.startswith("gender_"):
        db[uid].update({"gender": "male" if "male" in call.data else "female", "state": "set_age"})
        save_shadow_data(db); shadow_bot.delete_message(uid, call.message.id)
        shadow_bot.send_message(uid, "حالا سن قشنگت رو بفرست:")
    elif call.data.startswith("find_"):
        # منطق پیدا کردن هم‌صحبت...
        shadow_bot.edit_message_text("🔍 در حال جستجو... صبور باش.", uid, call.message.id)
    elif call.data.startswith("rep_"):
        if "لغو" in call.data: shadow_bot.edit_message_text("بی‌خیال شدیم!", uid, call.message.id)
        else: shadow_bot.send_message(OWNER_ID, f"🚩 گزارش تخلف از {uid}\nدلیل: {call.data}"); shadow_bot.edit_message_text("گزارش ثبت شد.", uid, call.message.id)
    elif call.data == "quit_yes":
        p_id = db[uid].get("partner_id")
        db[uid].update({"state": "main", "partner_id": None}); db[p_id].update({"state": "main", "partner_id": None}); save_shadow_data(db)
        shadow_bot.send_message(uid, "تموم شد.", reply_markup=get_main_keyboard(uid)); shadow_bot.send_message(p_id, "طرف چت رو بست.", reply_markup=get_main_keyboard(p_id))

if __name__ == "__main__":
    keep_alive()
    shadow_bot.infinity_polling()
