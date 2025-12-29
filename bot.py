import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- زیرساخت ---
app = Flask('')
@app.route('/')
def home(): return "🤖 System Fixed & Ready!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091"  # آیدی عددی خودت
CHANNEL_ID = "@ChatNaAnnouncements"
CHANNEL_NAME = "اطلاع رسانی|چت ناشناس"
bot = telebot.TeleBot(TOKEN)

# فایل‌ها
USERS_FILE = "users.json"
BLACKLIST_FILE = "blacklist.json"
users = {}; blacklist = []; waiting = {"male": [], "female": []}

def load_data():
    global users, blacklist
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f: users = json.load(f)
        except: users = {}
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f: blacklist = json.load(f)
        except: blacklist = []

def save_all():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=4)

def is_member(user_id):
    if str(user_id) == str(ADMIN_ID): return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

# کیبوردها (بدون تغییر متن)
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔥 شکارِ هم‌صحبت", "🎭 ایستگاهِ ناشناس")
    kb.add("💎 ویترینِ من", "📜 راهنمایِ سفر")
    if str(cid) == str(ADMIN_ID): kb.add("📢 طنینِ همگانی")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✂️ پایانِ قصه", "🚩 گزارشِ مزاحمت")
    return kb

# --- شروع سیستم ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def gatekeeper(message):
    cid = str(message.chat.id); load_data()
    
    if cid in blacklist:
        bot.send_message(cid, "❌ **شما به دلیل نقض قوانین از دسترسی به ربات محروم شده‌اید.**")
        return

    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=f"https://t.me/{CHANNEL_ID[1:]}"))
        kb.add(types.InlineKeyboardButton("🚀 عضو شدم! بازش کن", callback_data="check_and_start"))
        bot.send_message(cid, "⛔️ **دسترسی محدود شده است!**\n\nبرای عبور از این دروازه و ورود به دنیای چت ناشناس، ابتدا باید در کانال اطلاع‌رسانی ما عضو شوی. پس از عضویت، دکمه تایید را لمس کن تا مسیر برایت باز شود. ✨", reply_markup=kb)
        return

    if message.text and message.text.startswith("/start"):
        process_start(message); return

    user = users.get(cid)
    if not user: return
    text = message.text

    # ارسال همگانی ادمین (تاییدیه)
    if user.get("state") == "broad_wait" and cid == str(ADMIN_ID):
        user["temp_msg_id"] = message.message_id
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🚀 بله، منتشر کن", callback_data="admin_bc_send"),
            types.InlineKeyboardButton("❌ لغو ارسال", callback_data="main_menu")
        )
        bot.send_message(cid, "⚠️ **آیا از پخش این پیام برای تمام اعضا اطمینان داری؟**", reply_markup=kb)
        return

    # ثبت‌نام
    if user["state"] == "get_name" and text:
        user.update({"name": text[:15], "state": "get_gender"}); save_all()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("شوالیه (آقا) 👦", "بانو (خانم) 👧")
        bot.send_message(cid, "✅ عالیه! حالا بگو با چه هویتی وارد میشی؟", reply_markup=kb); return
    
    if user["state"] == "get_gender" and text:
        user.update({"gender": "male" if "شوالیه" in text else "female", "state": "get_age"}); save_all()
        bot.send_message(cid, "🎂 **چند سالته؟** (فقط عدد بفرست)", reply_markup=types.ReplyKeyboardRemove()); return

    if user["state"] == "get_age" and text:
        if text.isdigit():
            user.update({"age": int(text), "state": "main"}); save_all()
            bot.send_message(cid, "🎉 **تبریک! شناسنامه تو صادر شد.**", reply_markup=main_kb(cid)); return

    # منوی اصلی
    if user["state"] == "main":
        if text == "🔥 شکارِ هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقایان 👦", callback_data="f_male"), types.InlineKeyboardButton("خانم‌ها 👧", callback_data="f_female"), types.InlineKeyboardButton("هرکسی 🌈", callback_data="f_any"))
            bot.send_message(cid, "🛰 **سیگنال‌ها در حال اسکن...**\nدنبال چه هم‌صحبتی می‌گردی؟", reply_markup=kb)
        elif text == "🎭 ایستگاهِ ناشناس":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_all()
            bot.send_message(cid, f"🎁 **لینک اختصاصی تو ساخته شد!**\n\n`https://t.me/{bot.get_me().username}?start={code}`", parse_mode="Markdown")
        elif text == "👤 ویترینِ من":
            icon = "👦" if user.get('gender') == 'male' else "👧"
            bot.send_message(cid, f"📝 **اطلاعاتِ تو:**\n👤 نام: {user.get('name')}\n🚻 جنسیت: {icon}\n🎂 سن: {user.get('age')}")
        elif text == "📜 راهنمایِ سفر":
            bot.send_message(cid, "📖 خیلی ساده‌ست:\n۱- با شکار هم‌صحبت، به یک غریبه وصل میشی.\n۲- با ایستگاه ناشناس، لینک خودت رو می‌گیری.")
        elif text == "📢 طنینِ همگانی" and cid == str(ADMIN_ID):
            user["state"] = "broad_wait"
            bot.send_message(cid, "📝 پیام خودت رو بفرست تا آماده انتشار بشه:")

    # چت فعال
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "✂️ پایانِ قصه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ قطع کن", callback_data="c_stop"), types.InlineKeyboardButton("❌ ادامه", callback_data="main_menu"))
            bot.send_message(cid, "⚠️ واقعاً می‌خوای این مکالمه رو تموم کنی؟", reply_markup=kb)
        elif text == "🚩 گزارشِ مزاحمت":
            kb = types.InlineKeyboardMarkup(row_width=1).add(
                types.InlineKeyboardButton("🤬 فحاشی", callback_data="r_insult"),
                types.InlineKeyboardButton("🔞 غیراخلاقی", callback_data="r_18")
            )
            bot.send_message(cid, "🔍 علت گزارش چیه؟", reply_markup=kb)
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

    # نوشتن ناشناس
    if user["state"] == "writing_anon" and text:
        user["pending_msg"] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال", callback_data="send_final"), types.InlineKeyboardButton("❌ لغو", callback_data="main_menu"))
        bot.send_message(cid, f"📝 **متنِ آماده شده:**\n\n_{text}_\n\nآیا از ارسال این اعتراف مطمئنی؟", reply_markup=kb, parse_mode="Markdown")

def process_start(message):
    cid = str(message.chat.id)
    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "writing_anon"; users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسس!**\nداری یه پیام مخفیانه می‌فرستی. هرچی تو دلت هست رو اینجا بنویس:", reply_markup=types.ReplyKeyboardRemove())
            save_all(); return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 **سلام مسافرِ دنیای ناشناس!**\n\nبرای شروع این ماجراجویی، اسمت رو برام بفرست!"); save_all()
    else:
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 **{users[cid]['name']} جان، خوش برگشتی!**", reply_markup=main_kb(cid))

# --- کال‌بک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); load_data(); user = users.get(cid)
    
    if call.data == "check_and_start":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ تایید شد!")
            bot.delete_message(cid, call.message.id)
            fake_msg = call.message; fake_msg.text = "/start"; process_start(fake_msg)
        else: bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی رفیق!", show_alert=True)
        return

    if not user: return

    # بن کردن متهم (توسط ادمین)
    if call.data.startswith("ban_user_"):
        bad_id = call.data.replace("ban_user_", "")
        if bad_id not in blacklist:
            blacklist.append(bad_id); save_all()
            bot.send_message(bad_id, "❌ **شما توسط ادمین از ربات بن شدید.**")
            bot.edit_message_text(f"✅ کاربر {bad_id} با موفقیت بن شد.", cid, call.message.id)
        return

    # ارسال همگانی نهایی
    if call.data == "admin_bc_send":
        mid = user.pop("temp_msg_id", None); count = 0
        for uid in users:
            try: bot.copy_message(uid, cid, mid); count += 1
            except: pass
        bot.edit_message_text(f"✅ پیام به {count} نفر ارسال شد.", cid, call.message.id)
        user["state"] = "main"; save_all(); return

    # بقیه کال‌بک‌ها
    if call.data.startswith("f_"):
        pref = call.data.split("_")[1]; user.update({"state": "searching", "pref": pref})
        bot.delete_message(cid, call.message.id)
        search_target = ["male", "female"] if pref == "any" else [pref]
        for g in search_target:
            if waiting[g]:
                pid = waiting[g].pop(0)
                if pid != cid:
                    p = users[pid]; user.update({"partner": pid, "state": "chat"}); p.update({"partner": cid, "state": "chat"})
                    bot.send_message(cid, "💎 **وصل شدی!**", reply_markup=chat_kb()); bot.send_message(pid, "💎 **وصل شدی!**", reply_markup=chat_kb())
                    save_all(); return
        waiting[user.get('gender', 'male')].append(cid)
        bot.send_message(cid, "🔍 **در حال جستجوی غریبه‌ها...**", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ انصراف", callback_data="main_menu")))

    if call.data == "send_final":
        target = user.get("anon_target"); msg = user.pop("pending_msg", "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 جواب بده", callback_data=f"reply_{cid}"))
            sent = bot.send_message(target, f"📬 **پیام ناشناس:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            user["last_mid"] = sent.message_id
            bot.edit_message_text("✅ ارسال شد.", cid, call.message.id)
        user["state"] = "main"; bot.send_message(cid, "🏡 منو:", reply_markup=main_kb(cid)); save_all()

    if call.data.startswith("r_"):
        reason = call.data.split("_")[1]; p_id = user.get("partner")
        report = f"🚨 **گزارش تخلف**\n👤 شاکی: `{cid}`\n🚫 متهم: `{p_id}`\n⚖️ دلیل: {reason}"
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("⛔️ بن کردن متهم", callback_data=f"ban_user_{p_id}"),
            types.InlineKeyboardButton("🗑 رد گزارش", callback_data="main_menu")
        )
        bot.send_message(ADMIN_ID, report, reply_markup=kb, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "🚩 گزارش ارسال شد.", show_alert=True)

    if call.data == "c_stop":
        pid = user.get("partner")
        if pid: 
            users[pid].update({"partner": None, "state": "main"})
            bot.send_message(pid, "⚠️ طرف مقابل قطع کرد.", reply_markup=main_kb(pid))
        user.update({"partner": None, "state": "main"})
        bot.edit_message_text("🔚 تمام شد.", cid, call.message.id); save_all()
        bot.send_message(cid, "🏡 منو:", reply_markup=main_kb(cid))

    if call.data == "main_menu":
        user["state"] = "main"; bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🏡 **منوی اصلی:**", reply_markup=main_kb(cid))

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.infinity_polling()
