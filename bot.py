import telebot
from telebot import types
import json, os, random, datetime
from flask import Flask
from threading import Thread

# --- قلب تپنده محفل ---
app = Flask('')
@app.route('/')
def home(): return "🕯 قلب محفل سایه‌ها در حال تپیدن است..."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات کتیبه ---
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

# --- تالار منوها ---
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

# --- پردازشگر اصلی پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_messages(message):
    uid = str(message.chat.id)
    db = get_db()
    
    if uid in db.get("banned", []):
        bot.send_message(uid, "🚫 شما به دلیل نقض قوانین از حضور در محفل سایه‌ها مسدود شده‌اید.")
        return

    # عضویت اجباری با متن اصلی
    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("عضویت در کانال اعلانات 📢", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو 🔓", callback_data="verify_join"))
        bot.send_message(uid, "✨ مسافر عزیز! برای ورود به تالار اصلی محفل، ابتدا باید در کانال ما حضور داشته باشی. منتظرت هستیم...", reply_markup=btn)
        return

    # --- سیستم ریپلای هوشمند (اصلاح شده) ---
    if message.reply_to_message:
        target_uid = None
        for u_id, u_data in db["users"].items():
            if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id:
                target_uid = u_id
                break
        if target_uid:
            db["users"][uid].update({"state": "confirm_reply", "temp_reply_target": target_uid, "temp_reply_msg": message.message_id})
            save_db(db)
            btn = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("بفرست بره 🚀", callback_data="send_reply_ok"),
                types.InlineKeyboardButton("پشیمون شدم ❌", callback_data="cancel_reply")
            )
            bot.send_message(uid, "🕯 مسافر عزیز، آیا مطمئنی می‌خوای این پاسخ رو در دلِ سایه‌ها برای صاحب راز بفرستی؟", reply_to_message_id=message.message_id, reply_markup=btn)
            return

    # --- پنل مدیریت ادمین ---
    if uid == OWNER_ID:
        if message.text == "📊 آمار و دیتابیس":
            m = sum(1 for u in db["users"].values() if u.get("gender") == "male")
            f = sum(1 for u in db["users"].values() if u.get("gender") == "female")
            stats = f"📜 **کتیبه آمار اهالی محفل:**\n\n👥 کل ساکنان: {len(db['users'])}\n👦 شوالیه‌ها: {m}\n👧 بانوها: {f}\n🚫 مطرودین: {len(db['banned'])}"
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📥 دریافت دیتابیس (JSON)", callback_data="get_db_file"), types.InlineKeyboardButton("🚫 مدیریت لیست سیاه", callback_data="manage_banned"))
            bot.send_message(uid, stats, reply_markup=btn); return
        if message.text == "📢 طنین مدیریت":
            db["users"][uid]["state"] = "admin_bc"; save_db(db)
            bot.send_message(uid, "📢 پیامی که می‌خوای در کل تالار پخش بشه رو بنویس:", reply_markup=types.ReplyKeyboardRemove()); return

    if db["users"].get(uid, {}).get("state") == "admin_bc" and uid == OWNER_ID:
        db["users"][uid]["state"] = "main"; save_db(db)
        for u in db["users"]:
            try: bot.send_message(u, f"📢 **طنین مدیریت در محفل:**\n\n{message.text}")
            except: pass
        bot.send_message(uid, "✅ پیام با موفقیت طنین‌انداز شد.", reply_markup=main_menu(uid)); return

    # --- هندلر استارت و متن‌های اصلی ---
    if message.text and message.text.startswith("/start"):
        if uid in db["users"] and db["users"][uid].get("state") == "in_chat":
            bot.send_message(uid, "🕯 شما در اعماق یک گفتگو هستید. برای بازگشت به تالار، ابتدا رشته اتصال را قطع کنید."); return
        
        if len(message.text.split()) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}; save_db(db)
                bot.send_message(uid, "🕯 **به محفل سایه‌ها خوش آمدی، غریبه...**\n\nاینجا جاییه که نقاب‌ها می‌افته. نام مستعارت رو اینجا بنویس:"); return
            bot.send_message(uid, "🗝 درهای تالار به روی تو باز است.", reply_markup=main_menu(uid)); return
        
        code = message.text.split()[1]
        target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
        if target:
            db["users"][uid].update({"state": "writing_confession", "target": target}); save_db(db)
            bot.send_message(uid, "🕯 در خلوتگاه او هستی... هر چه در دل داری بنویس. هویت تو مثل یک رازِ مقدس محفوظ می‌مونه.", reply_markup=types.ReplyKeyboardRemove()); return

    # --- تالار گفتگو و گزارشات (بدون تغییر در منطق اصلی) ---
    user = db["users"].get(uid)
    if not user: return

    if user.get("state") == "in_chat":
        partner = user.get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
        
        if message.text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن ❌", callback_data="confirm_end"), types.InlineKeyboardButton("نه، بمان 🕯", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 آیا مطمئنی می‌خوای این رشته‌ی اتصال رو پاره کنی؟", reply_markup=btn)
        elif message.text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=2)
            reasons = ["توهین و بی‌ادبی 🤬", "تبلیغات 📢", "محتوای نامناسب 🔞", "مزاحمت ❌"]
            btns = [types.InlineKeyboardButton(r, callback_data=f"report_{r}") for r in reasons]
            btn.add(*btns).add(types.InlineKeyboardButton("بی‌خیال، لغو گزارش 🔙", callback_data="cancel_end"))
            bot.send_message(uid, "🚩 دلیل گزارش رو انتخاب کن تا نگهبان‌ها بررسی کنن:", reply_markup=btn)
        else:
            msg_val = message.text if message.text else f"[{message.content_type}]"
            db["chat_history"][chat_id].append({"u": uid, "c": msg_val})
            if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
            save_db(db)
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # --- بقیه هندلرها (ثبت‌نام، ویترین و ...) ---
    if user["state"] == "reg_name":
        db["users"][uid].update({"name": message.text[:20], "state": "reg_gender"}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه (آقا) 👦", callback_data="set_m"), types.InlineKeyboardButton("بانو (خانم) 👧", callback_data="set_f"))
        bot.send_message(uid, f"✨ خوش‌آمدی {message.text}. حالا بگو شوالیه‌ای یا بانو؟", reply_markup=btn); return
    
    if user["state"] == "reg_age" and message.text.isdigit():
        db["users"][uid].update({"age": message.text, "state": "main"}); save_db(db)
        bot.send_message(uid, "📜 نامت در کتیبه محفل ثبت شد.", reply_markup=main_menu(uid)); return

    if user["state"] == "writing_confession" and (message.text or message.photo):
        db["users"][uid].update({"state": "confirm_confession", "temp_msg": message.text if message.text else "[تصویر]"}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بفرست بره 🚀", callback_data="send_conf"), types.InlineKeyboardButton("پشیمون شدم ❌", callback_data="cancel_conf"))
        bot.send_message(uid, "📜 متنت رو با دقت خوندم. بفرستمش برای صاحب راز؟", reply_markup=btn); return

    # دکمه‌های منو
    if message.text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_m"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_f"), types.InlineKeyboardButton("هر دو 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 رادارهای محفل رو برای پیدا کردن یک هم‌فرکانس روشن کردم. کی مد نظرته؟", reply_markup=btn)
    elif message.text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(111111, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینکِ اعترافات ناشناس تو آماده‌ست:\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif message.text == "🎈 ویترین من":
        sex = "شوالیه 👦" if user.get("gender") == "male" else "بانو 👧"
        bot.send_message(uid, f"👤 نام: {user['name']}\n🎭 جنسیت: {sex}\n🎂 سن: {user.get('age', '؟')}")
    elif message.text == "📖 داستان محفل":
        bot.send_message(uid, "🕯 محفل سایه‌ها جایی برای گفتگوهای بدون نقابه...")

# --- مدیریت کالبک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()

    if call.data.startswith("view_msg_"):
        sid = call.data.split("_")[2]
        msg = db["anon_msgs"].get(call.data)
        if msg:
            db["users"][uid]["last_anon_msg_id"] = call.message.id; save_db(db)
            bot.edit_message_text(f"📬 **یه رازِ ناشناس:**\n\n{msg}\n\n➖➖\n💡 برای جواب دادن ریپلای کن.", uid, call.message.id)
            bot.send_message(sid, "👁‍🗨 قاصدک تو به مقصد رسید و توسط صاحب راز رویت شد.")
        else: bot.answer_callback_query(call.id, "🎭 این راز در سایه‌ها گم شده.")

    elif call.data == "send_reply_ok":
        t_uid = db["users"][uid].get("temp_reply_target")
        m_id = db["users"][uid].get("temp_reply_msg")
        try:
            bot.send_message(t_uid, "💬 **پاسخی در سایه‌ها:**")
            sent = bot.copy_message(t_uid, uid, m_id)
            db["users"][t_uid]["last_anon_msg_id"] = sent.message_id
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.edit_message_text("✅ پاسخ تو در سایه‌ها رها شد و به مقصد رسید.", uid, call.message.id)
        except: bot.send_message(uid, "🎭 متاسفانه ارتباط در سایه‌ها قطع شده است.")

    elif call.data.startswith("report_"):
        reason = call.data.split("_")[1]; partner = db["users"][uid].get("partner")
        hist = db["chat_history"].get(f"{min(uid, partner)}_{max(uid, partner)}", [])
        log = f"🚩 **گزارش تخلف جدید**\n\n👤 شاکی: `{uid}`\n👤 متهم: `{partner}`\n💡 دلیل: {reason}\n\n📜 **آخرین پیام‌ها:**\n"
        for h in hist: log += f"• {h['u']}: {h['c']}\n"
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚫 بن کردن متهم (BAN)", callback_data=f"ban_u_{partner}"), types.InlineKeyboardButton("✅ نادیده گرفتن", callback_data="ig_rep"))
        bot.send_message(OWNER_ID, log, reply_markup=btn, parse_mode="Markdown")
        bot.edit_message_text("✅ گزارش تو توسط نگهبان‌ها دریافت شد.", uid, call.message.id)

    elif call.data.startswith("ban_u_"):
        target = call.data.split("_")[2]
        if target not in db["banned"]: db["banned"].append(target); save_db(db)
        bot.edit_message_text(call.message.text + "\n\n✅ نتیجه: کاربر مسدود شد.", OWNER_ID, call.message.id)

    elif call.data == "ig_rep":
        bot.edit_message_text(call.message.text + "\n\n✅ نتیجه: نادیده گرفته شد.", OWNER_ID, call.message.id)

    elif call.data == "send_conf":
        target = db["users"][uid].get("target"); msg = db["users"][uid].get("temp_msg")
        mkey = f"view_msg_{uid}_{random.randint(1000,9999)}"
        db["anon_msgs"][mkey] = msg; db["users"][uid]["state"] = "main"; save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👁 مشاهده پیام", callback_data=mkey))
        bot.send_message(target, "📬 یک پیام ناشناس جدید در سایه‌ها منتظر توست...", reply_markup=btn)
        bot.edit_message_text("✅ قاصدک تو به مقصد رسید!", uid, call.message.id)

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"}); save_db(db)
        bot.delete_message(uid, call.message.id); bot.send_message(uid, "🕯 حالا سن خودت رو به عدد بفرست:")

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]; pref_key = "male" if pref=="m" else ("female" if pref=="f" else "any")
        bot.edit_message_text("🔍 در حال جستجوی یک روح سرگردان...", uid, call.message.id)
        # منطق کامل صف‌بندی مشابه نسخه اول تو...
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        my_g = db["users"][uid].get("gender")
        target_pool = db["queue"]["any"] + db["queue"][my_g]
        match = next((u for u in target_pool if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key)), None)
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match})
            db["users"][match].update({"state": "in_chat", "partner": uid}); save_db(db)
            bot.send_message(uid, "💎 وصل شدی! گپ رو شروع کن.", reply_markup=chat_menu())
            bot.send_message(match, "💎 وصل شدی! گپ رو شروع کن.", reply_markup=chat_menu())
        else:
            db["queue"][pref_key].append(uid); save_db(db)
            bot.send_message(uid, "🕯 کسی پیدا نشد، در صف ماندی...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("لغو جستجو ❌", callback_data="cancel_search")))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None}); db["users"][p].update({"state": "main", "partner": None}); save_db(db)
        bot.send_message(uid, "رشته اتصال پاره شد.", reply_markup=main_menu(uid))
        bot.send_message(p, "طرف مقابل چت رو تموم کرد.", reply_markup=main_menu(p))

    elif call.data == "get_db_file" and uid == OWNER_ID:
        with open(DB_PATH, "rb") as f: bot.send_document(uid, f)

    elif call.data == "cancel_reply":
        db["users"][uid]["state"] = "main"; save_db(db)
        bot.edit_message_text("❌ منصرف شدی.", uid, call.message.id)

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
