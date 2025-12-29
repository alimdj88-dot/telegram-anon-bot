import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- زنده نگه داشتن محفل ---
app = Flask('')
@app.route('/')
def home(): return "قلب محفل با عشق می‌تپد"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(TOKEN)

DB_FILE = "users.json"
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
    markup.add("🎈 ویترین من", "📖 داستان محفل")
    if str(uid) == ADMIN_ID: markup.add("📢 طنین مدیریت")
    return markup

def chat_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✂️ قطع ارتباط", "🚩 گزارش تخلف")
    return markup

# --- موتور هوشمند محفل ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def master_logic(message):
    uid = str(message.chat.id)
    db = get_db()
    text = message.text

    if not check_join(message.chat.id):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("بزن بریم توی کانال", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو", callback_data="check_membership"))
        bot.send_message(uid, "سلام مسافر! واسه اینکه بتونی وارد محفل بشی و از گفتگوهای ناشناس لذت ببری، اول باید توی کانال ما عضو بشی. منتظرتم!", reply_markup=btn)
        return

    # ۱. هندل لینک ناشناس
    if text and text.startswith("/start "):
        code = text.split()[1]
        target = next((u for u, d in db.items() if d.get("link") == code), None)
        if target == uid:
            bot.send_message(uid, "ای شیطون! داری به خودت پیام میدی؟ این لینک رو بفرست واسه بقیه تا اونا برات حرفای قشنگ بنویسن.")
            return
        if target:
            db[uid] = db.get(uid, {"state": "main"})
            db[uid].update({"state": "typing_anon", "send_to": target})
            save_db(db)
            bot.send_message(uid, "الان در خلوتگاهِ او هستی... هر چه در دل داری بنویس، هویتت مثل یک رازِ ابدی پیش من محفوظ می‌مونه.", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۲. ثبت‌نام (بدون باگ)
    if uid not in db or "name" not in db[uid] or db[uid].get("state") in ["ask_name", "ask_gender", "ask_age"]:
        if uid not in db: db[uid] = {"state": "ask_name"}
        state = db[uid].get("state")
        if state == "ask_name":
            if text == "/start": bot.send_message(uid, "سلام! واسه اینکه بتونیم با هم آشنا بشیم، یه اسم مستعار جذاب برام بفرست:")
            else:
                db[uid].update({"name": text[:20], "state": "ask_gender"})
                save_db(db)
                btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه (آقا) 👦", callback_data="sex_male"), types.InlineKeyboardButton("بانو (خانم) 👧", callback_data="sex_female"))
                bot.send_message(uid, f"خوشبختم {text} جان! حالا بگو شوالیه محفلی یا بانویِ شب؟", reply_markup=btn)
            return
        if state == "ask_age":
            if text and text.isdigit():
                db[uid].update({"age": text, "state": "main"})
                save_db(db)
                bot.send_message(uid, "ایول! شناسنامه‌ت توی محفل صادر شد. حالا وقتشه که هم‌صحبت پیدا کنی و خوش بگذرونی!", reply_markup=main_menu(uid))
            else: bot.send_message(uid, "قربونت برم، سن رو فقط به عدد بفرست.")
            return
        return

    user = db[uid]
    
    # ۳. ریپلای به پیام ناشناس
    if message.reply_to_message and "فرستنده:" in (message.reply_to_message.text or ""):
        try:
            target_id = message.reply_to_message.text.split("فرستنده:")[1].strip()
            bot.send_message(target_id, f"💌 **صاحبِ راز به پیام تو جواب داد:**\n\n{text}")
            bot.send_message(uid, "✅ جوابت با موفقیت و به صورت ناشناس براش ارسال شد.")
        except: bot.send_message(uid, "ای وای! نشد جوابت رو برسونم.")
        return

    # ۴. وضعیت‌های چت و گزارش
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        if text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آره، قطع کن", callback_data="end_yes"), types.InlineKeyboardButton("نه، ادامه میدم", callback_data="end_no"))
            bot.send_message(uid, "مطمئنی می‌خوای این رشته اتصال رو پاره کنی و هم‌صحبتت رو تنها بذاری؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=1)
            reasons = ["توهین و بی‌ادبی 🤬", "تبلیغات مزاحم 📢", "محتوای نامناسب 🔞", "ایجاد مزاحمت ❌", "لغو گزارش 🔙"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r}"))
            bot.send_message(uid, "کی خاطرِ عزیزت رو مکدر کرده؟ دلیل گزارش رو انتخاب کن تا نگهبان‌ها برسن:", reply_markup=btn)
        else:
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # ۵. تاییدیه ارسال پیام ناشناس (جدید)
    if user.get("state") == "typing_anon" and text:
        db[uid].update({"state": "confirm_anon", "temp_msg": text})
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آره، بفرست بره 🚀", callback_data="go_anon"), types.InlineKeyboardButton("نه، پشیمون شدم ❌", callback_data="cancel_anon"))
        bot.send_message(uid, f"متنت رو با دقت خوندم! مطمئنی بفرستمش؟\n\n📝 متن تو:\n{text}", reply_markup=btn)
        return

    # ۶. منوی اصلی
    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_male"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_female"))
        btn.add(types.InlineKeyboardButton("هر کی که شد 🌈", callback_data="hunt_any"))
        bot.send_message(uid, "رادارهام رو برای پیدا کردن یک هم‌فرکانس روشن کردم! کی مد نظرته؟", reply_markup=btn)
    
    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(11111, 99999))
        db[uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"لینک ناشناس تو آماده‌ست! بزارش توی بیو یا استوری تا بقیه بیان و ناشناس بهت اعتراف کنن:\n\nhttps://t.me/{bot.get_me().username}?start={link}")

    elif text == "📖 داستان محفل":
        about_text = (
            "🌑 **خوش اومدی به اعماقِ محفلِ سایه‌ها**\n\n"
            "اینجا جایی برای شنیدنِ ناگفته‌هاست. ما این ربات رو ساختیم تا مرزهای هویت رو بشکنیم. "
            "توی محفل ما، فرقی نمی‌کنه کی هستی؛ مهم اینه که چی توی دلت می‌گذره.\n\n"
            "✨ **چیکار می‌تونی بکنی؟**\n"
            "۱- به صورت کاملاً ناشناس با غریبه‌ها گپ بزنی.\n"
            "۲- لینک اختصاصی بگیری و اجازه بدی بقیه بهت اعتراف کنن.\n"
            "۳- رازهایی رو بشنوی که هیچ‌جا گفته نمی‌شه.\n\n"
            "امنیت و ناشناس موندن تو، خط قرمزِ ماست. پس با خیال راحت رها باش و از گفتگو لذت ببر! 🎈"
        )
        bot.send_message(uid, about_text, reply_markup=main_menu(uid))

    elif text == "🎈 ویترین من":
        bot.send_message(uid, f"📜 کتیبه هویت تو در دفتر محفل:\n\n👤 اسم: {user['name']}\n🎂 سن: {user['age']}\nStatus: آماده برای کشف غریبه‌ها")

# --- مدیریت کلیک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def calls(call):
    uid = str(call.message.chat.id); db = get_db()

    if call.data == "go_anon":
        target = db[uid].get("send_to"); msg = db[uid].get("temp_msg")
        try:
            bot.send_message(target, f"📬 **یه رازِ ناشناس برای تو رسید:**\n\n{msg}\n\n➖➖➖➖➖➖\n💡 برای جواب دادن، روی همین پیام ریپلای کن.\n🆔 فرستنده: {uid}")
            bot.edit_message_text("✅ پیامت مثل یک قاصدک رها شد و به دستش رسید. به محض اینکه بخونتش بهت خبر میدم!", uid, call.message.id)
            bot.send_message(uid, "🏡 برگشتیم به منوی اصلی", reply_markup=main_menu(uid))
            # اطلاع‌رسانی به فرستنده (دیده شدن)
            bot.send_message(uid, "🕊 **قاصدکِ تو دیده شد!** پیامت در این لحظه توسط گیرنده باز شد.")
        except: bot.send_message(uid, "ای وای! انگار طرف راهِ ورود قاصدک‌ها رو بسته (بلاک کرده).")
        db[uid]["state"] = "main"; save_db(db)

    elif call.data == "cancel_anon":
        db[uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("❌ منصرف شدی؟ حله، پیام رو پاک کردم.", uid, call.message.id)
        bot.send_message(uid, "برگشتیم به ایستگاه مرکزی", reply_markup=main_menu(uid))

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]
        my_gender = db[uid].get("gender")
        bot.edit_message_text("🔍 در حال جستجوی غریبه‌ای در اعماق محفل... صبور باش رفیق.", uid, call.message.id)
        
        target_list = waiting_queue[pref] if pref != "any" else (waiting_queue["male"] + waiting_queue["female"])
        match = next((u for u in target_list if u != uid), None)
        
        if match:
            for k in waiting_queue: 
                if match in waiting_queue[k]: waiting_queue[k].remove(match)
            db[uid].update({"state": "in_chat", "partner": match})
            db[match].update({"state": "in_chat", "partner": uid})
            save_db(db)
            bot.send_message(uid, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید. با احترام گپ بزنید!", reply_markup=chat_menu())
            bot.send_message(match, "💎 فرکانس‌ها هماهنگ شد! به هم وصل شدید. با احترام گپ بزنید!", reply_markup=chat_menu())
        else:
            waiting_queue[my_gender if pref == "any" else pref].append(uid)

    elif call.data == "end_yes":
        p = db[uid].get("partner")
        db[uid]["state"] = "main"; db[p]["state"] = "main"
        save_db(db)
        bot.send_message(uid, "رشته اتصال پاره شد. امیدوارم هم‌صحبت خوبی بوده باشه!", reply_markup=main_menu(uid))
        bot.send_message(p, "هم‌صحبتت رشته اتصال رو قطع کرد. برو دنبال یه غریبه دیگه!", reply_markup=main_menu(p))

    elif call.data == "end_no":
        bot.edit_message_text("ایول که موندی! به گفتگو ادامه بده.", uid, call.message.id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
