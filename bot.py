import telebot
from telebot import types
import json, os, random, datetime
from flask import Flask
from threading import Thread

# --- تنظیمات سرور و پایداری ---
app = Flask('')
@app.route('/')
def home(): return "✅ System is Professional & Active!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" # آیدی عددی خودت
CHANNELS = ["@ChatNaAnnouncements"] 
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
            if bot.get_chat_member(ch, user_id).status in ['left', 'kicked']: return False
        except: continue
    return True

# --- کیبوردهای جذاب ---
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 پیدا کردن هم‌صحبت", "🔗 لینک ناشناس من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    if str(cid) == str(ADMIN_ID): kb.add("📢 ارسال پیام همگانی")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# --- شروع و تشخیص لینک ناشناس ---
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id); load_data()
    
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            kb.add(types.InlineKeyboardButton(f"📢 عضویت در کانال {i}", url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ عضو شدم! (تایید)", callback_data="check_membership"))
        bot.send_message(cid, "💎 **خوش اومدی!**\n\nواسه استفاده، اول عضو کانال‌ها شو:", reply_markup=kb)
        return

    args = message.text.split()
    if len(args) > 1: # اگر با لینک وارد شده باشد
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسسس! اینجا ایستگاه پیام‌های محرمانه است.**\n\nهر چی تو دلت هست و می‌خوای طرف بدونه رو اینجا بنویس (من اسمت رو لو نمی‌دم!):", reply_markup=types.ReplyKeyboardRemove())
            save_users(); return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 **سلام! خوش اومدی.**\n\nواسه شروع، یه اسم جذاب واسه خودت انتخاب کن:"); save_users()
    else:
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 **{users[cid]['name']} جان، خوش برگشتی!**", reply_markup=main_kb(cid))

# --- مدیریت پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation'])
def handle_all(message):
    cid = str(message.chat.id); load_data(); user = users.get(cid)
    if not user: return

    # ارسال همگانی ادمین
    if user.get("state") == "broad_wait" and cid == str(ADMIN_ID):
        user["temp_msg"] = message.message_id
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 بله، شلیک کن!", callback_data="bc_confirm"), types.InlineKeyboardButton("❌ پشیمون شدم", callback_data="main_menu"))
        bot.send_message(cid, "🎯 **آماده ارسال همگانی هستی؟**", reply_markup=kb); return

    # ثبت نام (خلاصه شده برای فضا)
    if user["state"] == "get_name" and message.text:
        user.update({"name": message.text[:15], "state": "get_gender"}); save_users()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("آقا هستم 👦", "خانم هستم 👧")
        bot.send_message(cid, "✅ جنسیتت؟", reply_markup=kb); return
    
    if user["state"] == "get_gender" and message.text:
        user.update({"gender": "male" if "آقا" in message.text else "female", "state": "get_age"}); save_users()
        bot.send_message(cid, "🎂 چند سالته؟", reply_markup=types.ReplyKeyboardRemove()); return

    if user["state"] == "get_age" and message.text:
        if message.text.isdigit():
            user.update({"age": int(message.text), "state": "main"}); save_users()
            bot.send_message(cid, "🎉 **تبریک! پروفایلت ساخته شد.**", reply_markup=main_kb(cid)); return

    # چت دو نفره
    if user["state"] == "chat":
        partner = user.get("partner")
        if message.text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ آره قطع کن", callback_data="confirm_end"), types.InlineKeyboardButton("❌ نه ادامه بدیم", callback_data="cancel_action"))
            bot.send_message(cid, "⚠️ **واقعاً می‌خوای این گپ رو تموم کنی؟**", reply_markup=kb)
        elif message.text == "🚩 گزارش تخلف":
            kb = types.InlineKeyboardMarkup(row_width=1).add(
                types.InlineKeyboardButton("🤬 توهین و فحاشی", callback_data="rep_fosh"),
                types.InlineKeyboardButton("🔞 محتوای غیراخلاقی", callback_data="rep_18"),
                types.InlineKeyboardButton("⚖️ مزاحمت شدید", callback_data="rep_spam"))
            bot.send_message(cid, "🔍 **دلیل گزارش چیه؟**", reply_markup=kb)
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

    # نوشتن پیام ناشناس (با تاییدیه جذاب)
    if user["state"] == "anon_write" and message.text:
        user["anon_pending"] = message.text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 بفرست بره!", callback_data="confirm_anon_send"), types.InlineKeyboardButton("❌ لغو و پاک کن", callback_data="main_menu"))
        bot.send_message(cid, f"📝 **متن ارسالی تو:**\n\n_{message.text}_\n\nآیا از فرستادن این پیام مطمئنی؟", reply_markup=kb, parse_mode="Markdown")

    # منوی اصلی
    if user["state"] == "main":
        if message.text == "🚀 پیدا کردن هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="s_male"), types.InlineKeyboardButton("خانم 👧", callback_data="s_female"), types.InlineKeyboardButton("🌈 فرقی نمی‌کنه", callback_data="s_any"))
            bot.send_message(cid, "🛰 **در حال اسکن فرکانس‌های اطراف...**\n\nدنبال کی می‌گردی؟", reply_markup=kb)
        elif message.text == "🔗 لینک ناشناس من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_users()
            bot.send_message(cid, f"🎁 **اینم از لینک اختصاصی تو:**\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
        elif message.text == "👤 پروفایل من":
            icon = "👦" if user.get('gender') == 'male' else "👧"
            bot.send_message(cid, f"👤 نام: {user.get('name')}\n🚻 جنسیت: {icon}\n🎂 سن: {user.get('age')}")
        elif message.text == "📢 ارسال پیام همگانی" and cid == str(ADMIN_ID):
            user["state"] = "broad_wait"
            bot.send_message(cid, "📝 پیام مورد نظرت رو بفرست تا برای همه بفرستم:")

# --- کال‌بک‌ها (بخش حساس) ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); load_data(); user = users.get(cid)
    if not user: return

    # تایید ارسال ناشناس و سیستم سین زدن
    if call.data == "confirm_anon_send":
        target = user.get("anon_target"); msg = user.pop("anon_pending", "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 جواب بده", callback_data=f"ans_{cid}"))
            sent = bot.send_message(target, f"📬 **یه پیام ناشناسِ جدید داری:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            # ذخیره آیدی پیام برای سین زدن
            user["last_sent_mid"] = sent.message_id
            bot.edit_message_text("✅ **پیامت با موفقیت و مخفیانه تحویل داده شد!**", cid, call.message.id)
        user["state"] = "main"; bot.send_message(cid, "🏡 بازگشت به منوی اصلی", reply_markup=main_kb(cid)); save_users()

    # وقتی گیرنده روی جواب زدن یا مشاهده پیام کلیک می‌کند
    if call.data.startswith("ans_"):
        sender_id = call.data.split("_")[1]
        user.update({"state": "anon_write", "anon_target": sender_id})
        bot.send_message(cid, "✍️ **پاسخت رو بنویس:**", reply_markup=types.ReplyKeyboardRemove())
        # اعلان سین زدن به فرستنده
        try: bot.send_message(sender_id, "👁‍🗨 **پیام ناشناست توسط طرف مقابل دیده شد!**", reply_to_message_id=users[sender_id].get("last_sent_mid"))
        except: pass

    # گزارش تخلف (پنل شیک ادمین)
    if call.data.startswith("rep_"):
        reason = call.data.split("_")[1]; p_id = user.get("partner")
        time_now = datetime.datetime.now().strftime("%H:%M")
        report_text = (
            "🚨 **گزارش جدید دریافت شد**\n"
            "━━━━━━━━━━━━━━\n"
            f"👤 **شاکی:** `{cid}`\n"
            f"🚫 **متهم:** `{p_id}`\n"
            f"⚖️ **دلیل:** {reason}\n"
            f"⏰ **زمان:** {time_now}\n"
            "━━━━━━━━━━━━━━"
        )
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("⛔️ بن کردن متهم", callback_data=f"ban_{p_id}"),
            types.InlineKeyboardButton("✅ نادیده گرفتن", callback_data="del_msg")
        )
        bot.send_message(ADMIN_ID, report_text, reply_markup=kb, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "🚩 گزارش با موفقیت ثبت شد.", show_alert=True)
        bot.delete_message(cid, call.message.id)

    # دکمه‌های مدیریتی
    if call.data.startswith("ban_"):
        target = call.data.split("_")[1]
        bot.send_message(target, "❌ **شما به دلیل نقض قوانین از ربات مسدود شدید.**")
        bot.edit_message_text(f"✅ کاربر `{target}` با موفقیت بن شد.", cid, call.message.id)

    if call.data == "confirm_end":
        pid = user.get("partner")
        if pid: 
            users[pid].update({"partner": None, "state": "main"})
            bot.send_message(pid, "⚠️ **هم‌صحبتت چت رو ترک کرد.**", reply_markup=main_kb(pid))
        user.update({"partner": None, "state": "main"})
        bot.edit_message_text("🔚 **مکالمه تموم شد. امیدوارم خوش گذشته باشه!**", cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی", reply_markup=main_kb(cid)); save_users()

    if call.data == "check_membership":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
            bot.delete_message(cid, call.message.id); start(call.message)
        else: bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.infinity_polling()
