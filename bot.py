import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- زنده نگه داشتن سرور ---
app = Flask('')
@app.route('/')
def home(): return "محفل با عشق در حال اجراست"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(TOKEN)

DB_FILE = "users.json"
waiting_list = {"male": [], "female": [], "any": []}

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
    markup.add("✂️ خداحافظی", "🚩 گزارش تخلف")
    return markup

# --- موتور هوشمند ربات ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    text = message.text

    # ۱. قفل کانال
    if not check_join(message.chat.id):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("بزن بریم توی کانال", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو", callback_data="check_membership"))
        bot.send_message(uid, "سلام رفیق! خوش اومدی به جمع ما. واسه اینکه بتونیم گپ بزنیم، اول یه سر به کانالمون بزن و عضو شو، بعد بیا اینجا دکمه رو بزن تا قفل ربات برات باز بشه.", reply_markup=btn)
        return

    # ۲. سیستم لینک ناشناس (اولویت بالا)
    if text and text.startswith("/start "):
        code = text.split()[1]
        target = next((u for u, d in db.items() if d.get("link") == code), None)
        if target == uid:
            bot.send_message(uid, "ای شیطون! داری به لینک خودت پیام میدی؟ نمیشه که! این لینک رو بفرست واسه دوستات تا اونا برات حرفای قشنگ بنویسن.")
            return
        if target:
            db[uid] = db.get(uid, {"state": "main"})
            db[uid].update({"state": "typing_anon", "send_to": target})
            save_db(db)
            bot.send_message(uid, "الان در خلوتگاه طرف مقابل هستی. هر چی دوست داری بنویس و بفرست، خیالت تخت که هیچوقت نمیفهمه کی بودی!", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۳. ثبت‌نام گام‌به‌گام (اصلاح شده)
    if uid not in db or "name" not in db[uid] or db[uid].get("state") in ["ask_name", "ask_gender", "ask_age"]:
        if uid not in db: db[uid] = {"state": "ask_name"}
        state = db[uid].get("state")

        if state == "ask_name":
            if text == "/start":
                bot.send_message(uid, "سلام سلام! خیلی خوشحالم که اینجایی. واسه شروع، یه اسم باحال واسه خودت انتخاب کن و برام بفرست:")
            else:
                db[uid].update({"name": text[:20], "state": "ask_gender"})
                save_db(db)
                btn = types.InlineKeyboardMarkup()
                btn.add(types.InlineKeyboardButton("آقا هستم 👦", callback_data="sex_male"), types.InlineKeyboardButton("خانم هستم 👧", callback_data="sex_female"))
                bot.send_message(uid, f"به‌به، چه اسم قشنگی! خوشبختم {text} جان. حالا بگو شوالیه محفلی یا بانوی محفل؟", reply_markup=btn)
            return

        if state == "ask_age":
            if text and text.isdigit():
                db[uid].update({"age": text, "state": "main"})
                save_db(db)
                bot.send_message(uid, "ایول! ثبت نامت تموم شد رفیق. حالا وقتشه که بترکونی و هم‌صحبت پیدا کنی!", reply_markup=main_menu(uid))
            else:
                bot.send_message(uid, "قربونت برم، سن رو باید فقط به عدد بفرستی (مثلاً 20). دوباره تلاش کن:")
            return
        return

    user = db[uid]
    state = user.get("state")

    # منطق چت فعال
    if state == "in_chat":
        partner = user.get("partner")
        if text == "✂️ خداحافظی":
            btn = types.InlineKeyboardMarkup()
            btn.add(types.InlineKeyboardButton("آره، تمومش کن", callback_data="end_yes"), types.InlineKeyboardButton("نه، پشیمون شدم", callback_data="end_no"))
            bot.send_message(uid, "مطمئنی میخوای این گپ قشنگ رو تموم کنی؟", reply_markup=btn)
        elif text == "🚩 گزارش تخلف":
            db[uid]["state"] = "waiting_report"
            save_db(db)
            bot.send_message(uid, "ای بابا، کسی اذیتت کرده؟ دلیل گزارش رو بنویس تا من به بزرگترای محفل بگم. اگه هم منصرف شدی بنویس لغو:", reply_markup=types.ReplyKeyboardRemove())
        else:
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # دریافت گزارش
    if state == "waiting_report":
        if text and "لغو" in text:
            db[uid]["state"] = "in_chat"
            save_db(db); bot.send_message(uid, "حله، برگشتیم به چت. حواست به خودت باشه!", reply_markup=chat_menu())
        else:
            bot.send_message(ADMIN_ID, f"🚩 گزارش جدید!\nشاکی: {uid}\nمتهم: {user.get('partner')}\nدلیل: {text}")
            db[uid]["state"] = "in_chat"; save_db(db)
            bot.send_message(uid, "گزارشت رسید به دستم. نگهبانای محفل حواسشون هست. میتونی به چت ادامه بدی.", reply_markup=chat_menu())
        return

    # نوشتن پیام ناشناس
    if state == "typing_anon" and text:
        user["temp_msg"] = text; user["state"] = "confirm_anon"
        save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بفرست بره 🚀", callback_data="go_anon"), types.InlineKeyboardButton("منصرف شدم ❌", callback_data="cancel_anon"))
        bot.send_message(uid, f"متنت رو خوندم، خیلی باحاله! بفرستمش واسه طرف؟\n\nمتن تو: {text}", reply_markup=btn)
        return

    # دکمه‌های منو
    if text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("آقایون 👦", callback_data="hunt_male"), types.InlineKeyboardButton("خانم‌ها 👧", callback_data="hunt_female"))
        btn.add(types.InlineKeyboardButton("هر کی که شد 🌈", callback_data="hunt_any"))
        bot.send_message(uid, "رادارهام رو روشن کردم! دوست داری با کی گپ بزنی؟", reply_markup=btn)

    elif text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(11111, 99999))
        db[uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"اینم از لینک اختصاصی تو! بزارش توی بیو یا استوری تا بقیه بیان و ناشناس بهت اعتراف کنن:\n\nhttps://t.me/{bot.get_me().username}?start={link}")

    elif text == "🎈 ویترین من":
        sex = "آقا" if user.get("gender") == "male" else "خانم"
        bot.send_message(uid, f"مشخصات تو توی دفتر محفل اینجوری ثبت شده:\n\nاسم: {user['name']}\nجنسیت: {sex}\nسن: {user.get('age', 'نامعلوم')} سال\n\nهمه چی ردیفه؟")

    elif text == "📢 طنین مدیریت" and uid == ADMIN_ID:
        db[uid]["state"] = "admin_bc"; save_db(db)
        bot.send_message(uid, "پیامی که میخوای به گوش همه برسه رو بنویس:")

    elif state == "admin_bc" and uid == ADMIN_ID:
        count = 0
        for user_id in db:
            try:
                bot.send_message(user_id, "📢 پیام ویژه از مدیریت محفل:\n\n" + text)
                count += 1
            except: pass
        db[uid]["state"] = "main"; save_db(db)
        bot.send_message(uid, f"طنین با موفقیت برای {count} نفر فرستاده شد!")

# --- مدیریت کلیک‌های شیشه‌ای ---
@bot.callback_query_handler(func=lambda c: True)
def calls(call):
    uid = str(call.message.chat.id); db = get_db()

    if call.data == "check_membership":
        if check_join(uid):
            bot.delete_message(uid, call.message.id)
            bot.send_message(uid, "ایول! خوش اومدی. حالا میتونی از ربات استفاده کنی.", reply_markup=main_menu(uid))
        else: bot.answer_callback_query(call.id, "هنوز که عضو نشدی ناقلا!", show_alert=True)

    elif call.data.startswith("sex_"):
        gender = "male" if "male" in call.data else "female"
        db[uid].update({"gender": gender, "state": "ask_age"})
        save_db(db); bot.delete_message(uid, call.message.id)
        bot.send_message(uid, "ایول! حالا سن قشنگت رو به عدد برام بفرست:")

    elif call.data == "go_anon":
        target = db[uid].get("send_to"); msg = db[uid].get("temp_msg")
        try:
            bot.send_message(target, f"📬 یه پیام ناشناس جدید برات اومد:\n\n{msg}")
            bot.send_message(uid, "🕊 پیامت مثل یک قاصدک رها شد و به دستش رسید. خیالت راحت!")
        except:
            bot.send_message(uid, "متاسفانه نشد پیامت رو برسونم، انگار طرف ربات رو بلاک کرده.")
        db[uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("پیامت با موفقیت ارسال شد.", uid, call.message.id)
        bot.send_message(uid, "برگشتیم به منوی اصلی رفیق", reply_markup=main_menu(uid))

    elif call.data == "end_yes":
        p = db[uid].get("partner")
        db[uid]["state"] = "main"; db[p]["state"] = "main"
        save_db(db)
        bot.send_message(uid, "چت تموم شد. امیدوارم بهت خوش گذشته باشه!", reply_markup=main_menu(uid))
        bot.send_message(p, "هم‌صحبتت چت رو تموم کرد. اشکال نداره، یکی دیگه رو پیدا کن!", reply_markup=main_menu(p))

    elif call.data == "end_no":
        bot.edit_message_text("ایول که موندی! به گپ زدن ادامه بده.", uid, call.message.id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
