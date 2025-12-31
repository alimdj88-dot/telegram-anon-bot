import telebot
from telebot import types
import json, os, random, datetime, re
from flask import Flask
from threading import Thread

# --- قلب تپنده محفل ---
app = Flask('')
@app.route('/')
def home(): return "🕯 محفل سایه‌ها با نظارت کامل بیدار است..."
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات ---
API_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
OWNER_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(API_TOKEN)
DB_PATH = "shadow_data.json"

# لیست کلمات ممنوعه (حتماً کلمات مورد نظرت را اینجا اضافه کن)
BAD_WORDS = ["فحش1", "بی‌ناموس", "خواهر"] 

def get_db():
    if not os.path.exists(DB_PATH): 
        db = {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}}
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if "banned" not in data or isinstance(data["banned"], list): data["banned"] = {}
            if "chat_history" not in data: data["chat_history"] = {}
            return data
        except: return {"users": {}, "queue": {"male": [], "female": [], "any": []}, "banned": {}, "chat_history": {}, "anon_msgs": {}}

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def clean_text(text):
    if not text: return ""
    # حذف تمام فاصله، نقطه، ستاره و نویزها برای پیدا کردن فحش
    return re.sub(r'[.\s\-_*+]+', '', text)

def is_bad(text):
    cleaned = clean_text(text)
    for w in BAD_WORDS:
        if w in cleaned and w != "": return True
    return False

def check_sub(uid):
    if str(uid) == OWNER_ID: return True
    try:
        s = bot.get_chat_member(CHANNEL_ID, int(uid)).status
        return s in ['member', 'administrator', 'creator']
    except: return False

def is_banned(uid, db):
    if uid in db["banned"]:
        info = db["banned"][uid]
        if info['end'] == "perm": return True
        expire = datetime.datetime.fromisoformat(info['end'])
        if datetime.datetime.now() < expire: return True
        else:
            del db["banned"][uid]; save_db(db)
    return False

# --- کیبوردها ---
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
    
    if is_banned(uid, db):
        bot.send_message(uid, "🚫 شما به دلیل نقض قوانین از حضور در محفل سایه‌ها مسدود شده‌اید.")
        return

    if not check_sub(uid):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("عضویت در کانال اعلانات 📢", url="https://t.me/ChatNaAnnouncements"))
        btn.add(types.InlineKeyboardButton("عضو شدم، باز کن درو 🔓", callback_data="verify_join"))
        bot.send_message(uid, "✨ مسافر عزیز! برای ورود به تالار اصلی محفل، ابتدا باید در کانال ما حضور داشته باشی...", reply_markup=btn)
        return

    # فیلتر فحش
    if message.text and is_bad(message.text):
        bot.delete_message(uid, message.message_id)
        bot.send_message(uid, "⚠️ کلام شما حاوی واژگان نامناسب بود و فیلتر شد. لطفا ادب محفل را رعایت کن.")
        bot.send_message(OWNER_ID, f"🤖 **گزارش هوش مصنوعی:**\nکاربر: `{uid}`\nمتن: {message.text}")
        return

    # --- پنل مدیریت عددی بن ---
    if uid == OWNER_ID and db["users"].get(uid, {}).get("state") == "waiting_ban_time":
        target = db["users"][uid]["temp_target"]
        reason = db["users"][uid]["temp_reason"]
        if message.text.isdigit():
            expire = (datetime.datetime.now() + datetime.timedelta(minutes=int(message.text))).isoformat()
            db["banned"][target] = {"end": expire, "reason": reason}
            db["users"][uid]["state"] = "main"; save_db(db)
            bot.send_message(OWNER_ID, f"✅ کاربر {target} برای {message.text} دقیقه مسدود شد.", reply_markup=main_menu(uid))
            bot.send_message(target, f"⏳ شما به دلیل '{reason}' به مدت {message.text} دقیقه مسدود شدید.")
        else: bot.send_message(uid, "❌ لطفاً فقط عدد (به دقیقه) بفرستید.")
        return

    if uid == OWNER_ID and message.text == "📊 آمار و دیتابیس":
        m = sum(1 for u in db["users"].values() if u.get("gender") == "male")
        f = sum(1 for u in db["users"].values() if u.get("gender") == "female")
        stats = f"📜 **کتیبه آمار اهالی محفل:**\n\n👥 ساکنان: {len(db['users'])}\n👦 شوالیه‌ها: {m}\n👧 بانوها: {f}\n🚫 مطرودین: {len(db['banned'])}"
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("📥 دریافت JSON", callback_data="get_db_file"))
        btn.add(types.InlineKeyboardButton("🚫 مدیریت لیست سیاه", callback_data="manage_banned"))
        bot.send_message(uid, stats, reply_markup=btn); return

    if message.text and message.text.startswith("/start"):
        if uid in db["users"] and db["users"][uid].get("state") == "in_chat":
            bot.send_message(uid, "🕯 شما در اعماق یک گفتگو هستید. ابتدا رشته اتصال را قطع کنید."); return
        if len(message.text.split()) == 1:
            if uid not in db["users"] or "name" not in db["users"][uid]:
                db["users"][uid] = {"state": "reg_name"}; save_db(db)
                bot.send_message(uid, "🕯 **به محفل سایه‌ها خوش آمدی، غریبه...**\n\nنام مستعارت رو اینجا بنویس:"); return
            bot.send_message(uid, "🗝 درهای تالار به روی تو باز است.", reply_markup=main_menu(uid)); return
        code = message.text.split()[1]
        target = next((u for u, d in db["users"].items() if d.get("link") == code), None)
        if target:
            db["users"][uid] = db["users"].get(uid, {"state": "main"})
            db["users"][uid].update({"state": "writing_confession", "target": target}); save_db(db)
            bot.send_message(uid, "🕯 در خلوتگاه او هستی... هر چه در دل داری بنویس.", reply_markup=types.ReplyKeyboardRemove()); return

    user = db["users"].get(uid)
    if not user: return

    # --- چت زنده و ذخیره مدارک ---
    if user.get("state") == "in_chat":
        partner = user.get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        if chat_id not in db["chat_history"]: db["chat_history"][chat_id] = []
        msg_log = {"u": uid, "type": message.content_type, "val": message.text if message.text else (message.json.get(message.content_type).get('file_id') if isinstance(message.json.get(message.content_type), dict) else message.json.get(message.content_type)[-1].get('file_id'))}
        db["chat_history"][chat_id].append(msg_log)
        if len(db["chat_history"][chat_id]) > 10: db["chat_history"][chat_id].pop(0)
        save_db(db)

        if message.text == "✂️ قطع ارتباط":
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، قطع کن ❌", callback_data="confirm_end"), types.InlineKeyboardButton("نه، بمان 🕯", callback_data="cancel_end"))
            bot.send_message(uid, "🕯 آیا مطمئنی می‌خوای این رشته‌ی اتصال رو پاره کنی؟", reply_markup=btn)
        elif message.text == "🚩 گزارش تخلف":
            btn = types.InlineKeyboardMarkup(row_width=2)
            reasons = ["فحش ناموسی 🤬", "محتوای 🔞", "تبلیغات 📢", "مزاحمت ❌", "سایر موارد 👤"]
            for r in reasons: btn.add(types.InlineKeyboardButton(r, callback_data=f"rep_{r}"))
            bot.send_message(uid, "🚩 دلیل گزارش رو انتخاب کن:", reply_markup=btn)
        else:
            try: bot.copy_message(partner, uid, message.message_id)
            except: pass
        return

    # --- پاسخ به ناشناس ---
    if message.reply_to_message:
        target_uid = next((u_id for u_id, u_data in db["users"].items() if u_id != uid and u_data.get("last_anon_msg_id") == message.reply_to_message.message_id), None)
        if target_uid:
            bot.send_message(target_uid, "💬 **پاسخی در سایه‌ها:**")
            sent = bot.copy_message(target_uid, uid, message.message_id)
            db["users"][target_uid]["last_anon_msg_id"] = sent.message_id; save_db(db)
            bot.send_message(uid, "✅ پیامت منتقل شد.")
            return

    # --- ثبت نام و دکمه‌ها ---
    if user["state"] == "reg_name":
        db["users"][uid].update({"name": message.text[:20], "state": "reg_gender"}); save_db(db)
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه (آقا) 👦", callback_data="set_m"), types.InlineKeyboardButton("بانو (خانم) 👧", callback_data="set_f"))
        bot.send_message(uid, f"✨ خوش‌آمدی {message.text}. حالا بگو شوالیه‌ای یا بانو؟", reply_markup=btn)
    elif user["state"] == "reg_age" and message.text.isdigit():
        db["users"][uid].update({"age": message.text, "state": "main"}); save_db(db)
        bot.send_message(uid, "📜 نامت در کتیبه محفل ثبت شد.", reply_markup=main_menu(uid))

    if message.text == "🛰 شکار هم‌صحبت":
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("شوالیه‌ها 👦", callback_data="hunt_m"), types.InlineKeyboardButton("بانوها 👧", callback_data="hunt_f")).add(types.InlineKeyboardButton("هر کسی 🌈", callback_data="hunt_a"))
        bot.send_message(uid, "🔍 رادارهای محفل روشن شد. کی مد نظرته؟", reply_markup=btn)
    elif message.text == "🤫 ایستگاه اعتراف":
        link = user.get("link") or str(random.randint(111111, 999999))
        db["users"][uid]["link"] = link; save_db(db)
        bot.send_message(uid, f"🎭 لینک اعترافات تو:\nhttps://t.me/{bot.get_me().username}?start={link}")
    elif message.text == "🎈 ویترین من":
        sex = "شوالیه 👦" if user.get("gender") == "male" else "بانو 👧"
        bot.send_message(uid, f"📜 **کتیبه هویت تو:**\n👤 نام: {user['name']}\n🎭 جنسیت: {sex}\n🎂 سن: {user.get('age', '؟')}")
    elif message.text == "📖 داستان محفل":
        bot.send_message(uid, "🕯 محفل سایه‌ها جایی برای گفتگوهای بدون نقابه. اینجا هویت تو مخفیه تا بتونی بلندترین فریادهای دلت رو به گوش بقیه برسونی.")

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = str(call.message.chat.id); db = get_db()
    
    if call.data == "verify_join":
        if check_sub(uid): bot.edit_message_text("🔓 درها باز شد!", uid, call.message.id); bot.send_message(uid, "خوش آمدی.", reply_markup=main_menu(uid))
        else: bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)

    elif call.data.startswith("view_msg_"):
        sid = call.data.split("_")[2]
        msg = db["anon_msgs"].get(call.data)
        if msg:
            bot.edit_message_text(f"📬 **راز ناشناس:**\n\n{msg}\n\n➖➖\n💡 برای جواب ریپلای کن.", uid, call.message.id)
            db["users"][uid]["last_anon_msg_id"] = call.message.id; save_db(db)
            try: bot.send_message(sid, "👁‍🗨 پیام تو رویت شد.")
            except: pass

    elif call.data.startswith("rep_"):
        reason = call.data.split("_")[1]; partner = db["users"][uid].get("partner")
        chat_id = f"{min(uid, partner)}_{max(uid, partner)}"
        history = db["chat_history"].get(chat_id, [])
        report_text = f"🚩 **گزارش تخلف**\nدلیل: {reason}\nمتهم: `{partner}`\n\n📜 **آخرین پیام‌ها:**\n"
        for h in history:
            if h['type'] == 'text': report_text += f"👤 {h['u']}: {h['val']}\n"
        
        btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚫 بن دائم", callback_data=f"adminban_p_{partner}_{reason}"), types.InlineKeyboardButton("⏳ بن موقت", callback_data=f"adminban_t_{partner}_{reason}"))
        bot.send_message(OWNER_ID, report_text, reply_markup=btn)
        for h in history: 
            if h['type'] != 'text': bot.copy_message(OWNER_ID, h['u'], call.message.message_id) # ارسال مدیاها
        bot.edit_message_text("✅ گزارش شد.", uid, call.message.id)

    elif call.data.startswith("adminban_t_"):
        _, _, target, reason = call.data.split("_")
        db["users"][OWNER_ID].update({"state": "waiting_ban_time", "temp_target": target, "temp_reason": reason}); save_db(db)
        bot.send_message(OWNER_ID, f"⏳ مدت زمان مسدودیت برای `{target}` را به **دقیقه** وارد کنید:", reply_markup=types.ReplyKeyboardRemove())

    elif call.data.startswith("adminban_p_"):
        _, _, target, reason = call.data.split("_")
        db["banned"][target] = {"end": "perm", "reason": reason}; save_db(db)
        bot.send_message(OWNER_ID, f"✅ {target} دائم بن شد."); bot.send_message(target, "🚫 شما برای همیشه مسدود شدید.")

    elif call.data == "manage_banned":
        if not db["banned"]: bot.answer_callback_query(call.id, "لیست خالی است."); return
        for tid, info in db["banned"].items():
            name = db["users"].get(tid, {}).get("name", "نامعلوم")
            txt = f"👤 {name} ({tid})\nدلیل: {info['reason']}\nپایان: {info['end']}"
            btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔓 بخشش", callback_data=f"unban_{tid}"))
            bot.send_message(OWNER_ID, txt, reply_markup=btn)

    elif call.data.startswith("unban_"):
        tid = call.data.split("_")[1]
        if tid in db["banned"]: del db["banned"][tid]; save_db(db)
        bot.edit_message_text("✅ بخشیده شد.", uid, call.message.id)

    elif call.data == "get_db_file":
        with open(DB_PATH, "rb") as f: bot.send_document(OWNER_ID, f)

    elif call.data.startswith("set_"):
        db["users"][uid].update({"gender": "male" if "m" in call.data else "female", "state": "reg_age"}); save_db(db)
        bot.delete_message(uid, call.message.id); bot.send_message(uid, "🕯 حالا سن خودت رو بفرست:")

    elif call.data.startswith("hunt_"):
        pref = call.data.split("_")[1]; pref_key = "male" if pref=="m" else ("female" if pref=="f" else "any")
        bot.edit_message_text("🔍 در حال جستجو...", uid, call.message.id)
        for k in ["male", "female", "any"]:
            if uid in db["queue"][k]: db["queue"][k].remove(uid)
        my_g = db["users"][uid].get("gender")
        target_pool = db["queue"]["any"] + db["queue"][my_g]
        match = next((u for u in target_pool if u != uid and (pref_key == "any" or db["users"][u]["gender"] == pref_key)), None)
        if match:
            for k in ["male", "female", "any"]:
                if match in db["queue"][k]: db["queue"][k].remove(match)
            db["users"][uid].update({"state": "in_chat", "partner": match}); db["users"][match].update({"state": "in_chat", "partner": uid}); save_db(db)
            bot.send_message(uid, "💎 وصل شدی!", reply_markup=chat_menu()); bot.send_message(match, "💎 وصل شدی!", reply_markup=chat_menu())
        else:
            db["queue"][pref_key].append(uid); save_db(db)
            bot.send_message(uid, "🕯 در صف ماندی...", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("لغو ❌", callback_data="cancel_search")))

    elif call.data == "confirm_end":
        p = db["users"][uid].get("partner")
        db["users"][uid].update({"state": "main", "partner": None}); db["users"][p].update({"state": "main", "partner": None}); save_db(db)
        bot.send_message(uid, "رشته پاره شد.", reply_markup=main_menu(uid)); bot.send_message(p, "طرف مقابل قطع کرد.", reply_markup=main_menu(p))

if __name__ == "__main__":
    keep_alive(); bot.infinity_polling()
