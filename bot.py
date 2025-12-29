import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- سامانه پایداری ---
app = Flask('')
@app.route('/')
def home(): return "💎 High-End UI Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اختصاصی شما ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
# لیست انتظار برای شکار هم‌صحبت (در حافظه موقت برای سرعت بالا)
waiting_room = {"male": [], "female": [], "any": []}

def load_db():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return {}
    return {}

def save_db(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_member(user_id):
    if str(user_id) == ADMIN_ID: return True
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

# --- طراحی ویژوال کیبوردها ---
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔥 شکارِ هم‌صحبت", "🎭 ایستگاهِ ناشناس")
    kb.add("💎 ویترینِ من", "📜 راهنمایِ سفر")
    if str(cid) == ADMIN_ID:
        kb.add("📢 طنینِ همگانی")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✂️ پایانِ قصه", "🚩 گزارشِ مزاحمت")
    return kb

# --- مدیریت پیام‌ها و منطق UI ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def main_controller(message):
    cid = str(message.chat.id)
    users = load_db()
    text = message.text

    # ۱. قفل فوق امنیتی جوین اجباری
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📢 اطلاع رسانی|چت ناشناس", url=f"https://t.me/ChatNaAnnouncements"))
        kb.add(types.InlineKeyboardButton("✅ عضویتم را تایید کن", callback_data="verify_member"))
        bot.send_message(cid, "👋 **سلام مسافر گرامی!**\n\nبرای دسترسی به امکانات پیشرفته و دنیای ناشناس، ابتدا باید در کانال رسمی ما عضو شوید.\n\n✨ **سپس دکمه تایید را لمس کنید:**", reply_markup=kb, parse_mode="Markdown")
        return

    # ۲. هندل لینک ناشناس (Deep Link)
    if text and text.startswith("/start "):
        code = text.split()[1]
        target_id = next((u for u, d in users.items() if d.get("link") == code), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid].update({"state": "writing_anon", "target": target_id})
            save_db(users)
            bot.send_message(cid, "🤫 **وارد ایستگاه اعتراف شدی!**\n\nپیام تو کاملاً ناشناس ارسال میشه. هر چی دوست داری بنویس و بفرست:", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۳. ورود و ثبت نام با UI جدید
    if cid not in users or "name" not in users[cid]:
        if text == "/start" or cid not in users:
            users[cid] = {"state": "get_name"}
            save_db(users)
            bot.send_message(cid, "✨ **خوش آمدید!**\n\nبرای شروع این ماجراجویی، یک **نام مستعار** جذاب برای خودت انتخاب کن و بفرست:")
            return

        u_state = users[cid].get("state")
        if u_state == "get_name":
            users[cid].update({"name": text[:20], "state": "get_gender"})
            save_db(users)
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.add("👦 شوالیه (آقا)", "👧 بانو (خانم)")
            bot.send_message(cid, f"✅ عالیه **{text}** عزیز!\n\nحالا جنسیت خودت رو مشخص کن:", reply_markup=kb)
        elif u_state == "get_gender":
            gender = "male" if "شوالیه" in text else "female"
            users[cid].update({"gender": gender, "state": "get_age"})
            save_db(users)
            bot.send_message(cid, "🎂 **چند سالته؟**\n(لطفاً سن خودت رو به عدد انگلیسی یا فارسی بفرست)", reply_markup=types.ReplyKeyboardRemove())
        elif u_state == "get_age" and text.isdigit():
            users[cid].update({"age": text, "state": "main"})
            save_db(users)
            bot.send_message(cid, "🎉 **شناسنامه تو با موفقیت صادر شد!**\n\nحالا می‌تونی وارد دنیای ناشناس بشی.", reply_markup=main_kb(cid))
        return

    # ۴. هندل منوی اصلی
    user = users[cid]
    if user["state"] == "main":
        if text == "🔥 شکارِ هم‌صحبت":
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(types.InlineKeyboardButton("👦 گپ با آقایان", callback_data="find_male"),
                   types.InlineKeyboardButton("👧 گپ با خانم‌ها", callback_data="find_female"))
            kb.add(types.InlineKeyboardButton("🌈 فرقی نمی‌کند", callback_data="find_any"))
            bot.send_message(cid, "🛰 **رادارهای جستجو فعال شدند...**\n\nدوست داری با چه کسی هم‌کلام شوی؟", reply_markup=kb)

        elif text == "🎭 ایستگاهِ ناشناس":
            link = user.get("link") or str(random.randint(100000, 999999))
            users[cid]["link"] = link; save_db(users)
            bot.send_message(cid, f"🔗 **لینک اختصاصی تو آماده است!**\n\nاین لینک را در بیو یا استوری خود قرار بده تا دیگران بتوانند به تو پیام ناشناس بدهند:\n\n`https://t.me/{bot.get_me().username}?start={link}`", parse_mode="Markdown")

        elif text == "💎 ویترینِ من":
            g_icon = "👦" if user['gender'] == 'male' else "👧"
            bot.send_message(cid, f"👤 **پروفایل کاربری شما:**\n\n🆔 آیدی: `{cid}`\n✨ نام: {user['name']}\n🚻 جنسیت: {g_icon}\n🎂 سن: {user['age']}\n\n_وضعیت: آنلاین و آماده گفتگو_", parse_mode="Markdown")

        elif text == "📢 طنینِ همگانی" and cid == ADMIN_ID:
            users[cid]["state"] = "broad_wait"; save_db(users)
            bot.send_message(cid, "📝 **پیام مورد نظر را ارسال کنید:**\n(متن، عکس یا فایل فرقی نمی‌کند)")

    # ۵. منطق چت فعال (بدون باگ)
    elif user["state"] == "chat":
        partner = user.get("partner")
        if text == "✂️ پایانِ قصه":
            users[cid]["state"] = "main"; users[partner]["state"] = "main"
            save_db(users)
            bot.send_message(cid, "🔚 **مکالمه پایان یافت.**", reply_markup=main_kb(cid))
            bot.send_message(partner, "⚠️ **هم‌صحبت شما چت را ترک کرد.**", reply_markup=main_kb(partner))
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

    # ۶. منطق پیام ناشناس
    elif user["state"] == "writing_anon" and text:
        user["pending"] = text; user["state"] = "confirm_anon"
        save_db(users)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 شلیک (ارسال نهایی)", callback_data="send_anon"), 
                                              types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_anon"))
        bot.send_message(cid, f"📝 **پیش‌نمایش پیام:**\n\n_{text}_\n\nآیا از ارسال مطمئن هستی؟", reply_markup=kb, parse_mode="Markdown")

# --- مدیریت کلیک‌های شیشه‌ای (Callback) ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    cid = str(call.message.chat.id)
    users = load_db()

    if call.data == "verify_member":
        if is_member(cid):
            bot.delete_message(cid, call.message.id)
            bot.send_message(cid, "✅ **عضویت تایید شد!** خوش آمدید.", reply_markup=main_kb(cid))
            # رفرش کردن استیت به منو
            if cid in users: users[cid]["state"] = "main"; save_db(users)
        else:
            bot.answer_callback_query(call.id, "❌ هنوز در کانال عضو نشده‌اید!", show_alert=True)

    elif call.data.startswith("find_"):
        pref = call.data.split("_")[1]
        my_gender = users[cid].get("gender")
        
        # حذف از لیست‌های احتمالی قبلی
        for key in waiting_room:
            if cid in waiting_room[key]: waiting_room[key].remove(cid)

        # پیدا کردن جفت
        match = None
        target_list = waiting_room["any"] if pref == "any" else waiting_room[pref]
        
        if target_list:
            match = target_list.pop(0)
            users[cid].update({"state": "chat", "partner": match})
            users[match].update({"state": "chat", "partner": cid})
            save_db(users)
            bot.edit_message_text("💎 **هم‌صحبت پیدا شد!**\nهمین حالا گفتگو را شروع کنید.", cid, call.message.id)
            bot.send_message(cid, "💬 برای امنیت، اطلاعات شخصی ندهید.", reply_markup=chat_kb())
            bot.send_message(match, "💎 **یک نفر آماده گفتگو با شماست!**", reply_markup=chat_kb())
        else:
            waiting_room[my_gender if pref != "any" else "any"].append(cid)
            bot.edit_message_text("🔍 **در جستجوی غریبه‌ای خوش‌سخن...**\nکمی صبور باشید.", cid, call.message.id)

    elif call.data == "send_anon":
        target = users[cid].get("target")
        msg = users[cid].get("pending")
        bot.send_message(target, f"📬 **یک پیام ناشناس جدید داری:**\n\n_{msg}_", parse_mode="Markdown")
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✅ **پیام شما با موفقیت و در امنیت کامل ارسال شد.**", cid, call.message.id)
        bot.send_message(cid, "🏡 بازگشت به منوی اصلی", reply_markup=main_kb(cid))

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
