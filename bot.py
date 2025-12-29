import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- تنظیمات پایداری ---
app = Flask('')
@app.route('/')
def home(): return "💎 VIP System is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- اطلاعات شما (ثبت شده) ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"

def load_db():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
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

# --- کیبوردهای مدرن ---
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔥 شکارِ هم‌صحبت", "🎭 ایستگاهِ ناشناس")
    kb.add("💎 ویترینِ من", "📜 راهنمایِ سفر")
    if str(cid) == ADMIN_ID: kb.add("📢 طنینِ همگانی")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✂️ پایانِ قصه", "🚩 گزارشِ مزاحمت")
    return kb

# --- مدیریت پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def main_engine(message):
    cid = str(message.chat.id)
    users = load_db()
    text = message.text

    # ۱. قفل جوین اجباری
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/ChatNaAnnouncements"))
        kb.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="verify_member"))
        bot.send_message(cid, "👋 **خوش آمدید!**\n\nبرای استفاده از ربات چت ناشناس، ابتدا در کانال ما عضو شوید و سپس دکمه تایید را بزنید.", reply_markup=kb, parse_mode="Markdown")
        return

    # ۲. هندل کردن لینک ناشناس (Deep Link)
    if text and text.startswith("/start "):
        code = text.split()[1]
        target_id = next((u for u, d in users.items() if d.get("link") == code), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid].update({"state": "writing_anon", "target": target_id})
            save_db(users)
            bot.send_message(cid, "🤫 **وارد ایستگاه اعتراف شدی!**\n\nهر چه در دل داری بنویس تا مخفیانه برای طرف مقابل ارسال کنم:", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۳. ثبت‌نام اولیه (اگر کاربر جدید باشد یا ناقص)
    if cid not in users or "name" not in users[cid] or users[cid].get("state") in ["get_name", "get_gender", "get_age"]:
        if cid not in users: users[cid] = {"state": "get_name"}
        
        state = users[cid].get("state")

        if text == "/start":
            bot.send_message(cid, "🌟 **سلام مسافر!** برای شروع، یک نام مستعار جذاب بفرست:")
            users[cid]["state"] = "get_name"
            save_db(users)
            return

        if state == "get_name" and text:
            users[cid].update({"name": text[:20], "state": "get_gender"})
            save_db(users)
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("👦 شوالیه (آقا)", callback_data="set_male"),
                   types.InlineKeyboardButton("👧 بانو (خانم)", callback_data="set_female"))
            bot.send_message(cid, f"✅ عالیه **{text}** جان! حالا جنسیتت رو انتخاب کن:", reply_markup=kb)
            return

        if state == "get_age" and text:
            if text.isdigit() and 10 < int(text) < 90:
                users[cid].update({"age": text, "state": "main"})
                save_db(users)
                bot.send_message(cid, "🎉 **شناسنامه تو صادر شد!** به دنیای ناشناس خوش آمدی.", reply_markup=main_kb(cid))
            else:
                bot.send_message(cid, "⚠️ لطفاً سن خود را به عدد (مثلاً 20) وارد کنید.")
            return
        
        # اگر در حال ثبت‌نام است و متن بی ربط فرستاد
        if state == "get_gender":
            bot.send_message(cid, "⚠️ لطفاً از دکمه‌های بالا جنسیت خود را انتخاب کنید.")
            return

    # ۴. عملیات کاربر ثبت‌نام شده (Main States)
    user = users[cid]
    u_state = user.get("state")

    # --- بخش چت فعال ---
    if u_state == "chat":
        partner = user.get("partner")
        if text == "✂️ پایانِ قصه":
            users[cid]["state"] = "main"; users[partner]["state"] = "main"
            save_db(users)
            bot.send_message(cid, "🔚 **قصه به پایان رسید.**", reply_markup=main_kb(cid))
            bot.send_message(partner, "⚠️ **هم‌صحبت شما چت را ترک کرد.**", reply_markup=main_kb(partner))
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass
        return

    # --- بخش پیام همگانی (ادمین) ---
    if u_state == "broad_wait" and cid == ADMIN_ID:
        user["temp_msg"] = message.message_id
        user["state"] = "broad_confirm"
        save_db(users)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال همگانی", callback_data="bc_yes"), types.InlineKeyboardButton("❌ لغو", callback_data="main_menu"))
        bot.send_message(cid, "⚠️ **آیا از ارسال این پیام برای تمام کاربران مطمئن هستید؟**", reply_markup=kb)
        return

    # --- بخش نوشتن پیام ناشناس ---
    if u_state == "writing_anon" and text:
        user["pending"] = text; user["state"] = "anon_confirm"
        save_db(users)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 بفرست بره", callback_data="send_anon"), types.InlineKeyboardButton("❌ انصراف", callback_data="main_menu"))
        bot.send_message(cid, f"📝 **پیش‌نمایش پیام شما:**\n\n_{text}_\n\nارسال شود؟", reply_markup=kb, parse_mode="Markdown")
        return

    # --- دکمه‌های منوی اصلی ---
    if text == "🔥 شکارِ هم‌صحبت":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("👦 آقایان", callback_data="f_male"),
               types.InlineKeyboardButton("👧 خانم‌ها", callback_data="f_female"),
               types.InlineKeyboardButton("🌈 هرکسی", callback_data="f_any"))
        bot.send_message(cid, "🛰 **رادارهای جستجو فعال شدند...**\nدنبال چه هم‌صحبتی می‌گردی؟", reply_markup=kb)

    elif text == "🎭 ایستگاهِ ناشناس":
        link = user.get("link") or str(random.randint(100000, 999999))
        users[cid]["link"] = link; save_db(users)
        bot.send_message(cid, f"🔗 **لینک اعتراف اختصاصی شما:**\n\n`https://t.me/{bot.get_me().username}?start={link}`", parse_mode="Markdown")

    elif text == "💎 ویترینِ من":
        icon = "👦" if user['gender'] == 'male' else "👧"
        bot.send_message(cid, f"👤 **مشخصات شما در سیستم:**\n\n✨ نام: {user['name']}\n🚻 جنسیت: {icon}\n🎂 سن: {user['age']}\n\n_وضعیت: آماده گفتگو_")

    elif text == "📢 طنینِ همگانی" and cid == ADMIN_ID:
        users[cid]["state"] = "broad_wait"; save_db(users)
        bot.send_message(cid, "📝 **پیام خود را بفرستید:**")

# --- مدیریت کال‌بک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    cid = str(call.message.chat.id)
    users = load_db()

    if call.data == "verify_member":
        if is_member(cid):
            bot.delete_message(cid, call.message.id)
            bot.send_message(cid, "✅ **عضویت تایید شد!**", reply_markup=main_kb(cid))
        else: bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)

    elif call.data in ["set_male", "set_female"]:
        users[cid].update({"gender": "male" if "male" in call.data else "female", "state": "get_age"})
        save_db(users)
        bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🎂 **عالی! حالا سن خودت رو به عدد بفرست:**")

    elif call.data.startswith("f_"):
        pref = call.data.split("_")[1]
        # منطق ساده جفت‌سازی (برای نمونه)
        bot.edit_message_text("🔍 **در حال جستجوی هم‌صحبت...**", cid, call.message.id)
        # در اینجا می‌توانید کد جفت‌سازی پیشرفته را اضافه کنید
        users[cid]["state"] = "searching"; save_db(users)

    elif call.data == "bc_yes":
        mid = users[cid].get("temp_msg")
        for u in users:
            try: bot.copy_message(u, cid, mid)
            except: pass
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✅ پیام برای همه ارسال شد.", cid, call.message.id)

    elif call.data == "send_anon":
        target = users[cid].get("target")
        msg = users[cid].get("pending")
        bot.send_message(target, f"📬 **یک پیام ناشناس جدید داری:**\n\n{msg}")
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✅ ارسال شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 بازگشت به منو", reply_markup=main_kb(cid))

    elif call.data == "main_menu":
        users[cid]["state"] = "main"; save_db(users)
        bot.send_message(cid, "🏡 منوی اصلی فعال شد.", reply_markup=main_kb(cid))

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
