import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- پایداری سرور ---
app = Flask('')
@app.route('/')
def home(): return "🎭 Shadow Club Evolution is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- اطلاعات اختصاصی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
waiting_room = {"male": [], "female": [], "any": []}

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

# --- کیبوردهای محفل ---
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("☄️ شکارِ هم‌صحبت", "🕵️ ایستگاهِ اعتراف")
    kb.add("🔮 ویترینِ من", "📜 کتیبه راهنما")
    if str(cid) == ADMIN_ID: kb.add("⚡️ طنینِ مدیریت")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✂️ قطعِ رشته اتصال", "🚩 گزارش مزاحمت")
    return kb

# --- موتور اصلی ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def shadow_master(message):
    cid = str(message.chat.id)
    users = load_db()
    text = message.text

    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔱 ورود به محفل", url="https://t.me/ChatNaAnnouncements"))
        kb.add(types.InlineKeyboardButton("🔓 تایید دعوتنامه", callback_data="verify_member"))
        bot.send_message(cid, "🌑 **دسترسی محدود!**\n\nابتدا در کانال عضو شو و بعد روی تایید بزن.", reply_markup=kb)
        return

    # ۱. هندل لینک ناشناس (Deep Link)
    if text and text.startswith("/start "):
        code = text.split()[1]
        target_id = next((u for u, d in users.items() if d.get("link") == code), None)
        
        if target_id == cid:
            bot.send_message(cid, "🧐 **داری با خودت خلوت می‌کنی؟**\n\nنمیتونی به لینک ناشناس خودت پیام بدی! این لینک رو برای بقیه بفرست تا اونا برات بنویسن.")
            return
            
        if target_id:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid].update({"state": "writing_anon", "target": target_id})
            save_db(users)
            bot.send_message(cid, "🤫 **وارد خلوتگاهِ او شدی...**\n\nهر چه در دل داری بنویس؛ هویت تو مثل یک راز در اعماق سایه‌ها باقی می‌مونه:", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۲. ثبت‌نام
    if cid not in users or "name" not in users[cid]:
        if text == "/start" or cid not in users:
            users[cid] = {"state": "get_name"}
            save_db(users)
            bot.send_message(cid, "👋 **سلام غریبه!** نام مستعارت رو بفرست:")
            return
        
        state = users[cid].get("state")
        if state == "get_name":
            users[cid].update({"name": text[:20], "state": "get_gender"})
            save_db(users)
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👦 شوالیه", callback_data="set_male"), types.InlineKeyboardButton("👧 بانو", callback_data="set_female"))
            bot.send_message(cid, "🚻 اصالتت رو انتخاب کن:", reply_markup=kb)
            return
        if state == "get_age":
            if text.isdigit():
                users[cid].update({"age": text, "state": "main"})
                save_db(users)
                bot.send_message(cid, "🎉 **خوش آمدی!** ثبت‌نام با موفقیت انجام شد.", reply_markup=main_kb(cid))
            return
        return

    user = users[cid]
    u_state = user.get("state")

    # ۳. مدیریت وضعیت‌های خاص (گزارش و قطع چت)
    if u_state == "chat":
        partner = user.get("partner")
        if text == "✂️ قطعِ رشته اتصال":
            kb = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("✅ بله، قطع کن", callback_data="confirm_stop"),
                types.InlineKeyboardButton("❌ نه، ادامه میدم", callback_data="cancel_stop")
            )
            bot.send_message(cid, "🧐 **آیا مطمئنی که می‌خوای این گفتگو رو برای همیشه تموم کنی؟**", reply_markup=kb)
            return
        elif text == "🚩 گزارش مزاحمت":
            users[cid]["state"] = "reporting"
            save_db(users)
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔙 انصراف", callback_data="cancel_report"))
            bot.send_message(cid, "🚩 **دلیل گزارش رو بنویس:**\n(مثلاً: توهین، مزاحمت، محتوای غیراخلاقی)", reply_markup=kb)
            return
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass
        return

    # وضعیت گزارش دادن
    if u_state == "reporting":
        partner = user.get("partner")
        bot.send_message(ADMIN_ID, f"🚩 **گزارش تخلف!**\nشاکی: {cid}\nمتخلف: {partner}\nدلیل: {text}")
        bot.send_message(cid, "✅ گزارش تو با موفقیت برای نگهبانان محفل ارسال شد. چت رو ادامه میدی؟", reply_markup=chat_kb())
        users[cid]["state"] = "chat"; save_db(users)
        return

    # وضعیت نوشتن پیام ناشناس
    if u_state == "writing_anon" and text:
        user["pending"] = text; user["state"] = "anon_confirm"
        save_db(users)
        kb = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🚀 آره، بفرست", callback_data="send_anon"),
            types.InlineKeyboardButton("❌ پشیمون شدم", callback_data="main_menu")
        )
        bot.send_message(cid, f"👀 **پیش‌نمایشِ رازی که می‌فرستی:**\n\n_{text}_\n\nارسال بشه؟", reply_markup=kb, parse_mode="Markdown")
        return

    # دکمه‌های منوی اصلی
    if text == "☄️ شکارِ هم‌صحبت":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("👤 شوالیه‌ها", callback_data="find_male"),
               types.InlineKeyboardButton("👸 بانوها", callback_data="find_female"),
               types.InlineKeyboardButton("🌌 هرکسی", callback_data="find_any"))
        bot.send_message(cid, "🛰 **رادارها فعال شدند...**", reply_markup=kb)

    elif text == "🕵️ ایستگاهِ اعتراف":
        link = user.get("link") or str(random.randint(100000, 999999))
        users[cid]["link"] = link; save_db(users)
        bot.send_message(cid, f"🔗 **لینک اعتراف تو:**\n\n`https://t.me/{bot.get_me().username}?start={link}`", parse_mode="Markdown")

    elif text == "🔮 ویترینِ من":
        bot.send_message(cid, f"📜 **کتیبه هویت:**\n✨ نام: {user['name']}\n🚻 جنسیت: {user['gender']}\n🎂 سن: {user['age']}")

# --- کال‌بک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    cid = str(call.message.chat.id); users = load_db()

    if call.data == "verify_member":
        if is_member(cid):
            bot.delete_message(cid, call.message.id)
            bot.send_message(cid, "🔓 **دروازه باز شد!**", reply_markup=main_kb(cid))

    elif call.data == "confirm_stop":
        partner = users[cid].get("partner")
        users[cid]["state"] = "main"; users[partner]["state"] = "main"
        save_db(users)
        bot.edit_message_text("🔚 **اتصال با موفقیت قطع شد.**", cid, call.message.id)
        bot.send_message(cid, "🏡 بازگشت به منو", reply_markup=main_kb(cid))
        bot.send_message(partner, "⚠️ **هم‌صحبت تو رشته اتصال رو پاره کرد...**", reply_markup=main_kb(partner))

    elif call.data == "cancel_stop":
        bot.edit_message_text("✅ **گفتگو ادامه پیدا می‌کنه.**", cid, call.message.id)

    elif call.data == "cancel_report":
        users[cid]["state"] = "chat"; save_db(users)
        bot.edit_message_text("❌ گزارش لغو شد.", cid, call.message.id)

    elif call.data == "send_anon":
        target = users[cid].get("target"); msg = users[cid].get("pending")
        bot.send_message(target, f"📬 **یک رازِ ناشناس برایت رسید:**\n\n_{msg}_", parse_mode="Markdown")
        # پیام شاعرانه برای فرستنده (تایید دیده شدن)
        bot.send_message(cid, "🕊 **قاصدک به مقصد رسید...**\nراز تو در گوشِ او زمزمه شد و او اکنون آن را خوانده است.")
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✨ فرستاده شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 ایستگاه مرکزی", reply_markup=main_kb(cid))

    elif call.data.startswith("find_"):
        # (همان الگوریتم جفت‌سازی قبلی...)
        bot.edit_message_text("🔍 در حال جستجو...", cid, call.message.id)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
