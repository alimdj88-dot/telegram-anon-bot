import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- زنده نگه داشتن محفل ---
app = Flask('')
@app.route('/')
def home(): return "قلب محفل با قدرت می‌تپد"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(TOKEN)

DB_FILE = "users.json"
# صف انتظار واقعی برای وصل کردن آدم‌ها
waiting_queue = {"male": [], "female": [], "any": []}

def get_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except: return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def check_join(uid):
    if str(uid) == ADMIN_ID: return True
    try:
        s = bot.get_chat_member(CHANNEL_ID, uid).status
        return s in ['member', 'administrator', 'creator']
    except: return False

# --- کیبوردهای رفاقتی ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🛰 شکار هم‌صحبت", "🤫 ایستگاه اعتراف")
    markup.add("🎈 ویترین من", "📚 راهنمای سفر")
    if str(uid) == ADMIN_ID: markup.add("📢 طنین مدیریت")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✂️ قطع ارتباط", "🚩 گزارش تخلف")
    return markup

# --- موتور هوشمند ربات ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def master_logic(message):
    uid = str(message.chat.id)
    db = get_db()
    text = message.text

    if not check_join(message.chat.id):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("بزن بریم توی کانال", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو", callback_data="check_membership"))
        bot.send_message(uid, "سلام رفیق! خوش اومدی. واسه اینکه بتونیم گپ بزنیم، اول یه سر به کانالمون بزن و عضو شو، بعد بیا اینجا دکمه رو بزن.", reply_markup=btn)
        return

    # لینک ناشناس
    if text and text.startswith("/start "):
        code = text.split()[1]
        target = next((u for u, d in db.items() if d.get("link") == code), None)
        if target == uid:
            bot.send_message(uid, "ای شیطون! به لینک خودت پیام میدی؟ اینو بفرست واسه بقیه!")
            return
        if target:
            db[uid] = db.get(uid, {"state": "main"})
            db[uid].update({"state": "typing_anon", "send_to": target})
            save_db(db)
            bot.send_message(uid, "در خلوتگاه او هستی... هر چه دلت می‌خواهد بنویس، هویتت پیش من امن است.", reply_markup=types.ReplyKeyboardRemove())
            return

    # ثبت‌نام
    if uid not in db or "name" not in db[uid] or db[uid].get("state") in ["ask_name", "ask_gender", "ask_age"]:
        if uid not in db: db[uid] = {"state": "ask_name"}
        state = db[uid].get("state")
        if state == "ask_name":
            if text == "/start": bot.send_message(uid, "سلام! واسه شروع یه اسم مستعار جذاب برام بفرست:")
            else:
                db[uid].update({"name": text[:20], "state": "ask_gender"})
                save_db(db)
                btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه (آقا) 👦", callback_data="sex_male"), types.InlineKeyboardButton("بانو (خانم) 👧", callback_data="sex_female"))
                bot.send_message(uid, f"خوشبختم {text} جان! حالا بگو شوالیه محفلی یا بانو؟", reply_markup=btn)
            return
        if state == "ask_age":
            if text and text.isdigit():
                db[uid].update({"age": text, "state": "main"})
                save_db(db)
                bot.send_message(uid, "ثبت‌نامت تموم شد رفیق! حالا وقتشه بترکونی.", reply_markup=main_menu(uid))
            else: bot.send_message(uid, "عدد بفرست قربونت برم!")
            return
        return

    user = db[uid]
    
    # چت زنده
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آره، قطع کن", callback_data="end_yes"), types.InlineKeyboardButton("نه، ادامه میدم", callback_data="end_no"))
            bot.send_message(uid, "مطمئنی می‌خوای این رشته اتصال رو پاره کنی؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=1)
            reasons = ["توهین و بی‌ادبی 🤬", "تبلیغات مزاحم 📢", "محتوای نامناسب 🔞", "ایجاد مزاحمت ❌", "لغو گزارش 🔙"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r}"))
            bot.send_message(uid, "چی شده رفیق؟ کی اذیتت کرده؟ دلیل رو انتخاب کن:", reply_markup=btn)
        else:
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # منوی اصلی
    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_male"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_female"))
        btn.add(types.InlineKeyboardButton("هر کی که شد 🌈", callback_data="hunt_any"))
        bot.send_message(uid, "رادارهام رو روشن کردم! دنبال چه هم‌صحبتی می‌گردی؟", reply_markup=btn)
    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(11111, 99999))
        db[uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"لینک ناشناس تو آماده‌ست! بزارش توی بیو:\n\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif text == "🎈 ویترین من":
        bot.send_message(uid, f"مشخصات تو در دفتر محفل:\n\nاسم: {user['name']}\nسن: {user['age']}\nوضعیت: آماده ماجراجویی")

# --- مدیریت کلیک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def calls(call):
    uid = str(call.message.chat.id); db = get_db()

    if call.data == "check_membership":
        if check_join(uid):
            bot.delete_message(uid, call.message.id)
            bot.send_message(uid, "🔓 درها باز شد! خوش آمدی.", reply_markup=main_menu(uid))

    elif call.data.startswith("sex_"):
        db[uid].update({"gender": "male" if "male" in call.data else "female", "state": "ask_age"})
        save_db(db); bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "حالا سن قشنگت رو به عدد بفرست:")

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        my_gender = db[uid].get("gender")
        bot.edit_message_text("🔍 در حال جستجوی غریبه‌ای در اعماق محفل... صبور باش.", uid, call.message.id)
        
        # جفت‌سازی واقعی
        target_sex = "female" if pref == "female" else "male" if pref == "male" else "any"
        possible_match = None
        
        for g in (["female"] if target_sex=="female" else ["male"] if target_sex=="male" else ["male", "female", "any"]):
            if waiting_queue[g] and waiting_queue[g][0] != uid:
                possible_match = waiting_queue[g].pop(0)
                break
        
        if possible_match:
            db[uid].update({"state": "in_chat", "partner": possible_match})
            db[possible_match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید. گپ رو شروع کن!", reply_markup=chat_menu())
            bot.send_message(possible_match, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید. گپ رو شروع کن!", reply_markup=chat_menu())
        else:
            waiting_queue[my_gender if pref == "any" else pref].append(uid)

    elif call.data.startswith("rep_"):
        reason = call.data.replace("rep_", "")
        if "لغو" in reason:
            bot.edit_message_text("بی‌خیال شدیم! به گپ زدن ادامه بده.", uid, call.message.id)
        else:
            partner = db[uid].get("partner")
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("مسدود کردن متخلف ⛔️", callback_data=f"ban_{partner}"))
            bot.send_message(ADMIN_ID, f"🚩 گزارش تخلف!\nشاکی: {uid}\nمتخلف: {partner}\nدلیل: {reason}", reply_markup=btn)
            bot.edit_message_text("گزارشت رسید به دستم. نگهبانای محفل حواسشون هست.", uid, call.message.id)

    elif call.data == "end_yes":
        p = db[uid].get("partner")
        db[uid]["state"] = "main"; db[p]["state"] = "main"
        save_db(db)
        bot.send_message(uid, "رشته اتصال پاره شد. امیدوارم بهت خوش گذشته باشه.", reply_markup=main_menu(uid))
        bot.send_message(p, "هم‌صحبتت چت رو تموم کرد. بریم واسه بعدی؟", reply_markup=main_menu(p))

    elif call.data == "end_no":
        bot.edit_message_text("ایول که موندی! به گپ زدن ادامه بده.", uid, call.message.id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
