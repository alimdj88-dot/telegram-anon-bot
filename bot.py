import telebot
from telebot import types
import json, os, random, datetime
from flask import Flask
from threading import Thread

# --- زیرساخت پایداری ---
app = Flask('')
@app.route('/')
def home(): return "🤖 ChatNashenas Engine is Ready!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- پیکربندی اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091"  # آیدی عددی خودت را اینجا بگذار
BOT_USERNAME = "Chatnashenas_IriBot"
CHANNELS = ["@ChatNaAnnouncements"] # آیدی کانال‌هایت
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
users = {}
waiting = {"male": [], "female": []}

def load_data():
    global users
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        except: users = {}

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def is_member(user_id):
    if str(user_id) == str(ADMIN_ID): return True
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        except: continue
    return True

# --- طراحی دکمه‌های جدید و جذاب ---
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔥 شکار هم‌صحبت", "🎭 ایستگاه پیام ناشناس")
    kb.add("💎 ویترین من (پروفایل)", "📜 دفترچه راهنما")
    if str(cid) == str(ADMIN_ID):
        kb.add("📢 طنین همگانی (پیام به همه)")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✂️ پایان این قصه (قطع)", "⛔️ گزارش این غریبه")
    return kb

# --- شروع و منطق لینک ناشناس ---
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id); load_data()
    
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            kb.add(types.InlineKeyboardButton(f"🔗 عضویت در پایگاه {i}", url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ وارد شدم! بازش کن", callback_data="verify_join"))
        bot.send_message(cid, "💎 خوش اومدی رفیق!\nبرای اینکه بتونیم با هم پیش بریم، باید اول در پایگاه‌های زیر عضو بشی و بعد دکمه تایید رو بزنی:", reply_markup=kb)
        return

    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "anon_writing"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 هیسسس! الان در امن‌ترین جای ممکنی.\nهر چی تو دلت سنگینی می‌کنه رو اینجا بنویس تا بدون اینکه هویتت فاش بشه، به گوش طرف مقابل برسونم:", reply_markup=types.ReplyKeyboardRemove())
            save_users(); return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 سلام مسافر کهکشان ناشناس!\nبرای اینکه بقیه بدونن با کی حرف می‌زنن، بگو دوست داری چه اسمی برات ثبت کنم؟"); save_users()
    else:
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 {users[cid]['name']} جان، خوش برگشتی به خونه!\nامروز قراره کدوم غریبه رو غافلگیر کنی؟", reply_markup=main_kb(cid))

# --- هندل کردن تمام پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def handle_all(message):
    cid = str(message.chat.id); load_data(); user = users.get(cid)
    if not user: return
    text = message.text

    # ثبت نام
    if user["state"] == "get_name" and text:
        user.update({"name": text[:15], "state": "get_gender"}); save_users()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("شوالیه (آقا) 👦", "بانو (خانم) 👧")
        bot.send_message(cid, "✅ عالیه! حالا بگو از کدوم دسته هستی؟", reply_markup=kb); return
    
    if user["state"] == "get_gender" and text:
        user.update({"gender": "male" if "شوالیه" in text else "female", "state": "get_age"}); save_users()
        bot.send_message(cid, "🎂 و در نهایت، سن خودت رو به عدد برام بفرست:", reply_markup=types.ReplyKeyboardRemove()); return

    if user["state"] == "get_age" and text:
        if text.isdigit():
            user.update({"age": int(text), "state": "main"}); save_users()
            bot.send_message(cid, "🎉 تبریک! حالا تو رسماً عضوی از مایی.", reply_markup=main_kb(cid)); return

    # ارسال همگانی ادمین
    if user.get("state") == "broad_wait" and cid == str(ADMIN_ID):
        user["temp_msg"] = message.message_id
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 بله، منتشر کن!", callback_data="bc_confirm"), types.InlineKeyboardButton("❌ لغو ارسال", callback_data="main_menu"))
        bot.send_message(cid, "⚠️ آیا از پخش این پیام برای تمام اعضا اطمینان داری؟", reply_markup=kb); return

    # منوی اصلی
    if user["state"] == "main":
        if text == "🔥 شکار هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("پسرها 👦", callback_data="find_male"),
                types.InlineKeyboardButton("دخترها 👧", callback_data="find_female"),
                types.InlineKeyboardButton("هر کسی باشه 🌈", callback_data="find_any"))
            bot.send_message(cid, "🛰 رادارهای یابنده فعال شدند!\nدنبال چه جور هم‌صحبتی می‌گردی؟", reply_markup=kb)
        elif text == "🎭 ایستگاه پیام ناشناس":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_users()
            bot.send_message(cid, f"🎁 اینم از کلید گنجینه تو!\nاین لینک رو پخش کن تا بقیه بتونن بهت پیام ناشناس بدن:\n\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
        elif text == "💎 ویترین من (پروفایل)":
            icon = "👦" if user.get('gender') == 'male' else "👧"
            bot.send_message(cid, f"📝 شناسنامه تو در ربات:\n\n👤 نام مستعار: {user.get('name')}\n🚻 اصالت: {icon}\n🎂 تجربه (سن): {user.get('age')}")
        elif text == "📜 دفترچه راهنما":
            bot.send_message(cid, "📖 خیلی ساده‌ست:\n۱- با شکار هم‌صحبت، به یک غریبه وصل میشی.\n۲- با ایستگاه ناشناس، لینک خودت رو می‌گیری.")
        elif text == "📢 طنین همگانی (پیام به همه)" and cid == str(ADMIN_ID):
            user["state"] = "broad_wait"
            bot.send_message(cid, "📝 پیام یا مدیای خودت رو بفرست تا آماده ارسال بشه:")

    # چت دو نفره
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "✂️ پایان این قصه (قطع)":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله، تمام", callback_data="confirm_stop"), types.InlineKeyboardButton("❌ نه، ادامه", callback_data="cancel_action"))
            bot.send_message(cid, "⚠️ آیا واقعاً می‌خوای این مکالمه رو به پایان برسونی؟", reply_markup=kb)
        elif text == "⛔️ گزارش این غریبه":
            kb = types.InlineKeyboardMarkup(row_width=1).add(
                types.InlineKeyboardButton("🤬 توهین و فحاشی", callback_data="rpt_insult"),
                types.InlineKeyboardButton("🔞 محتوای غیراخلاقی", callback_data="rpt_adult"),
                types.InlineKeyboardButton("⚖️ مزاحمت و تبلیغات", callback_data="rpt_spam"))
            bot.send_message(cid, "🔍 علت گزارش این شخص چیه؟", reply_markup=kb)
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

    # پیام ناشناس
    if user["state"] == "anon_writing" and text:
        user["anon_pending"] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال نهایی", callback_data="send_anon_final"), types.InlineKeyboardButton("❌ لغو و بازگشت", callback_data="main_menu"))
        bot.send_message(cid, f"📝 پیامی که آماده کردی:\n\n_{text}_\n\nآیا از ارسال این اعتراف مطمئنی؟", reply_markup=kb, parse_mode="Markdown")

# --- مدیریت کلیک‌ها (Callback Query) ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); load_data(); user = users.get(cid)
    if not user: return

    # تایید جوین
    if call.data == "verify_join":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ خوش آمدی مسافر!")
            bot.delete_message(cid, call.message.id); start(call.message)
        else: bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی رفیق!", show_alert=True)

    # جستجوی هم‌صحبت
    if call.data.startswith("find_"):
        pref = call.data.split("_")[1]
        user.update({"search_pref": pref, "state": "searching"})
        bot.delete_message(cid, call.message.id)
        search_list = ["male", "female"] if pref == "any" else [pref]
        for g in search_list:
            if waiting[g]:
                pid = waiting[g].pop(0)
                if pid != cid:
                    p = users[pid]
                    user.update({"partner": pid, "state": "chat"})
                    p.update({"partner": cid, "state": "chat"})
                    bot.send_message(cid, "💎 یکی رو پیدا کردم! حالا می‌تونی با خیال راحت گپ بزنی.", reply_markup=chat_kb())
                    bot.send_message(pid, "💎 یکی رو پیدا کردم! حالا می‌تونی با خیال راحت گپ بزنی.", reply_markup=chat_kb())
                    save_users(); return
        waiting[user.get('gender', 'male')].append(cid)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ لغو جستجو", callback_data="main_menu"))
        bot.send_message(cid, "🔍 در حال اسکن کردن کهکشانِ کاربران...\nصبور باش، به زودی یکی رو پیدا می‌کنم!", reply_markup=kb)

    # ارسال ناشناس و اعلان سین زدن
    if call.data == "send_anon_final":
        target = user.get("anon_target"); msg = user.pop("anon_pending", "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 پاسخ دادن", callback_data=f"ans_{cid}"))
            sent = bot.send_message(target, f"📬 یه پیام ناشناسِ جدید داری:\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            user["last_mid"] = sent.message_id
            bot.edit_message_text("✅ پیامت با موفقیت و در سکوت کامل تحویل داده شد!", cid, call.message.id)
        user["state"] = "main"; bot.send_message(cid, "🏡 بازگشت به منوی اصلی", reply_markup=main_kb(cid)); save_users()

    if call.data.startswith("ans_"):
        sender_id = call.data.split("_")[1]
        user.update({"state": "anon_writing", "anon_target": sender_id})
        bot.send_message(cid, "✍️ پاسخت رو با خیال راحت بنویس:", reply_markup=types.ReplyKeyboardRemove())
        try: bot.send_message(sender_id, "👁‍🗨 پیامی که فرستاده بودی، توسط طرف مقابل خونده شد!", reply_to_message_id=users[sender_id].get("last_mid"))
        except: pass

    # گزارش ادمین
    if call.data.startswith("rpt_"):
        reason = call.data.split("_")[1]; p_id = user.get("partner")
        report_text = f"🚨 گزارش تخلف\n\n👤 شاکی: `{cid}`\n🚫 متهم: `{p_id}`\n⚖️ دلیل: {reason}"
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⛔️ مسدود سازی متهم", callback_data=f"ban_{p_id}"), types.InlineKeyboardButton("🗑 رد گزارش", callback_data="del_msg"))
        bot.send_message(ADMIN_ID, report_text, reply_markup=kb, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "✅ گزارش با موفقیت ثبت شد.", show_alert=True)

    # عملیات ادمین
    if call.data == "bc_confirm":
        mid = user.pop("temp_msg", None); count = 0
        for uid in users:
            try: bot.copy_message(uid, cid, mid); count += 1
            except: pass
        user["state"] = "main"; bot.edit_message_text(f"✅ طنین پیام تو به گوش {count} نفر رسید.", cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی فعال شد.", reply_markup=main_kb(cid))

    if call.data == "confirm_stop":
        pid = user.get("partner")
        if pid: 
            users[pid].update({"partner": None, "state": "main"})
            bot.send_message(pid, "⚠️ متاسفانه طرف مقابل چت رو ترک کرد.", reply_markup=main_kb(pid))
        user.update({"partner": None, "state": "main"})
        bot.edit_message_text("🔚 این قصه به پایان رسید.", cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی", reply_markup=main_kb(cid)); save_users()

    if call.data == "main_menu":
        user["state"] = "main"; bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🏡 بازگشت به منوی اصلی:", reply_markup=main_kb(cid))

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.infinity_polling()
