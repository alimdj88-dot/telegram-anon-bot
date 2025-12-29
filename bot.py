import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- سامانه پایداری ---
app = Flask('')
@app.route('/')
def home(): return "💎 VIP Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- اطلاعات شما ---
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

# --- هندلر اصلی ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def main_controller(message):
    cid = str(message.chat.id)
    users = load_db()
    text = message.text

    # ۱. چک کردن عضویت
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📢 عضویت در کانال", url="https://t.me/ChatNaAnnouncements"))
        kb.add(types.InlineKeyboardButton("✅ تایید عضویت", callback_data="verify_member"))
        bot.send_message(cid, "⚠️ **دسترسی محدود!**\n\nبرای استفاده، ابتدا در کانال عضو شده و سپس دکمه تایید را بزنید.", reply_markup=kb, parse_mode="Markdown")
        return

    # ۲. لینک ناشناس
    if text and text.startswith("/start "):
        code = text.split()[1]
        target_id = next((u for u, d in users.items() if d.get("link") == code), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid].update({"state": "writing_anon", "target": target_id})
            save_db(users)
            bot.send_message(cid, "🤫 **وارد ایستگاه اعتراف شدی!** هر چه می‌خواهی بنویس:", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۳. ثبت‌نام گام به گام (بدون گیر کردن در جنسیت)
    if cid not in users or "name" not in users[cid]:
        if text == "/start" or cid not in users:
            users[cid] = {"state": "get_name"}
            save_db(users)
            bot.send_message(cid, "🌟 **سلام!** اسمی که دوست داری باهاش شناخته بشی رو بفرست:")
            return
        
        state = users[cid].get("state")
        if state == "get_name":
            users[cid].update({"name": text[:20], "state": "get_gender"})
            save_db(users)
            # استفاده از دکمه شیشه‌ای برای جنسیت (حل قطعی باگ)
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("👦 شوالیه (آقا)", callback_data="set_male"),
                   types.InlineKeyboardButton("👧 بانو (خانم)", callback_data="set_female"))
            bot.send_message(cid, f"✅ خوش‌بختم **{text}** جان!\nحالا جنسیتت رو انتخاب کن:", reply_markup=kb, parse_mode="Markdown")
        
        elif state == "get_age":
            if text.isdigit():
                users[cid].update({"age": text, "state": "main"})
                save_db(users)
                bot.send_message(cid, "🎉 **شناسنامه تو صادر شد!**", reply_markup=main_kb(cid))
            else:
                bot.send_message(cid, "⚠️ لطفاً سن رو به عدد بفرست.")
        return

    # ۴. منوی اصلی و ویژگی‌های جدید
    user = users[cid]
    if user["state"] == "main":
        if text == "🔥 شکارِ هم‌صحبت":
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(types.InlineKeyboardButton("👦 آقایان", callback_data="f_male"),
                   types.InlineKeyboardButton("👧 خانم‌ها", callback_data="f_female"),
                   types.InlineKeyboardButton("🌈 هرکسی", callback_data="f_any"))
            bot.send_message(cid, "🛰 **در حال اسکن فرکانس‌ها...**\nدنبال چه کسی می‌گردی؟", reply_markup=kb)

        elif text == "🎭 ایستگاهِ ناشناس":
            link = user.get("link") or str(random.randint(100000, 999999))
            users[cid]["link"] = link; save_db(users)
            bot.send_message(cid, f"🔗 **لینک اعتراف تو:**\n`https://t.me/{bot.get_me().username}?start={link}`", parse_mode="Markdown")

        elif text == "💎 ویترینِ من":
            icon = "👦" if user['gender'] == 'male' else "👧"
            bot.send_message(cid, f"👤 **پروفایل شما:**\n✨ نام: {user['name']}\n🚻 جنسیت: {icon}\n🎂 سن: {user['age']}")

        elif text == "📢 طنینِ همگانی" and cid == ADMIN_ID:
            users[cid]["state"] = "broad_wait"; save_db(users)
            bot.send_message(cid, "📝 پیام همگانی رو بفرست:")

    # ۵. چت و پیام ناشناس (مثل قبل)
    elif user["state"] == "chat":
        partner = user.get("partner")
        if text == "✂️ پایانِ قصه":
            users[cid]["state"] = "main"; users[partner]["state"] = "main"
            save_db(users)
            bot.send_message(cid, "🔚 قطع شد.", reply_markup=main_kb(cid))
            bot.send_message(partner, "⚠️ هم‌صحبت قطع کرد.", reply_markup=main_kb(partner))
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

    elif user["state"] == "broad_wait" and cid == ADMIN_ID:
        user["temp_msg"] = message.message_id
        user["state"] = "broad_confirm"
        save_db(users)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال شود", callback_data="bc_yes"), types.InlineKeyboardButton("❌ لغو", callback_data="main_menu"))
        bot.send_message(cid, "⚠️ مطمئنی؟", reply_markup=kb)

    elif user["state"] == "writing_anon" and text:
        user["pending"] = text; user["state"] = "anon_confirm"
        save_db(users)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال نهایی", callback_data="send_anon"))
        bot.send_message(cid, f"📝 **پیش‌نمایش:**\n_{text}_\n\nارسال بشه؟", reply_markup=kb, parse_mode="Markdown")

# --- مدیریت کال‌بک‌ها (حل باگ جنسیت) ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    cid = str(call.message.chat.id)
    users = load_db()

    if call.data == "verify_member":
        if is_member(cid):
            bot.delete_message(cid, call.message.id)
            bot.send_message(cid, "✅ تایید شد!", reply_markup=main_kb(cid))
        else: bot.answer_callback_query(call.id, "❌ عضو نشدی!", show_alert=True)

    elif call.data in ["set_male", "set_female"]:
        gender = "male" if call.data == "set_male" else "female"
        users[cid].update({"gender": gender, "state": "get_age"})
        save_db(users)
        bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🎂 **عالیه! حالا سن خودت رو به عدد بفرست:**")

    elif call.data == "bc_yes":
        mid = users[cid].get("temp_msg")
        for u in users:
            try: bot.copy_message(u, cid, mid)
            except: pass
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✅ ارسال شد.", cid, call.message.id)

    elif call.data == "send_anon":
        target = users[cid].get("target")
        msg = users[cid].get("pending")
        bot.send_message(target, f"📬 پیام ناشناس جدید:\n\n{msg}")
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✅ فرستاده شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 منو:", reply_markup=main_kb(cid))

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
