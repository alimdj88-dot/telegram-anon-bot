import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- زنده نگه داشتن سرور ---
app = Flask('')
@app.route('/')
def home(): return "✅ ChatNashenas UI FIXED & Running!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- تنظیمات اصلی (آیدی‌های خودت رو اینجا بزن) ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091"  # <-- آیدی عددی خودت
BOT_USERNAME = "Chatnashenas_IriBot"
CHANNELS = ["@ChatNaAnnouncements"] 
bot = telebot.TeleBot(TOKEN)

# فایل‌ها
USERS_FILE = "users.json"
BLACKLIST_FILE = "blacklist.json"
users = {}; blacklist = []; anon_pending = {}

# --- مدیریت داده‌ها ---
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

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=4)

# بررسی عضویت
def is_member(user_id):
    if str(user_id) == str(ADMIN_ID): return True
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        except: continue
    return True

# --- کیبوردهای UI جذاب قبلی ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 پیدا کردن هم‌صحبت", "🔗 لینک ناشناس من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# --- هندل استارت و لینک ناشناس ---
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    
    if cid in blacklist:
        bot.send_message(cid, "🚫 **دسترسی شما مسدود شده است.**")
        return

    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            kb.add(types.InlineKeyboardButton(f"📢 عضویت در کانال {i}", url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ عضو شدم! (تایید)", callback_data="check_membership"))
        bot.send_message(cid, "💎 **خوش اومدی!**\n\nواسه استفاده از ربات، اول تو کانال‌های زیر عضو شو:", reply_markup=kb)
        return

    # حل مشکل لینک ناشناس
    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسسس!**\n\nداری یه پیام ناشناس می‌فرستی. هر چی تو دلت هست رو اینجا بنویس تا من بدون اینکه اسمت رو بگم به طرف برسونم:", reply_markup=types.ReplyKeyboardRemove())
            save_users()
            return

    # ثبت نام یا خوش‌آمدگویی
    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 **سلام! به دنیای بزرگ چت ناشناس خوش اومدی.**\n\n✨ واسه قدم اول، بگو دوست داری چی **صدات کنم؟** (اسمت رو بفرست)")
        save_users()
    else:
        name = users[cid].get("name", "دوست من")
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 **{name} جان، خیلی خوش برگشتی!**\n\nامروز قراره با کی گپ بزنیم؟", reply_markup=main_kb())

@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id); load_data()
    if cid in blacklist or not is_member(cid): return
    user = users.get(cid)
    if not user: return
    text = message.text

    # --- ثبت نام ---
    if user["state"] == "get_name" and text:
        user["name"] = text[:15]; user["state"] = "get_gender"
        save_users()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("آقا هستم 👦", "خانم هستم 👧")
        bot.send_message(cid, f"✅ خوشبختم **{user['name']}** عزیز!\nجنسیتت رو انتخاب کن:", reply_markup=kb, parse_mode="Markdown")
        return
    if user["state"] == "get_gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "get_age"
        save_users()
        bot.send_message(cid, "🎂 **چند سالته؟** (فقط عدد بفرست)", reply_markup=types.ReplyKeyboardRemove())
        return
    if user["state"] == "get_age" and text:
        if text.isdigit():
            user["age"] = int(text); user["state"] = "main"
            save_users()
            bot.send_message(cid, "🎉 **ایول! ثبت‌نامت تموم شد.**", reply_markup=main_kb())
        return

    # --- چت فعال ---
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله", callback_data="confirm_end"), types.InlineKeyboardButton("❌ خیر", callback_data="cancel_end"))
            bot.send_message(cid, "⚠️ **مطمئنی می‌خوای قطع کنی؟**", reply_markup=kb)
            return
        if text == "🚩 گزارش تخلف":
            kb = types.InlineKeyboardMarkup(row_width=1)
            kb.add(types.InlineKeyboardButton("🤬 فحاشی و بی ادبی", callback_data="rep_reason_insult"),
                   types.InlineKeyboardButton("🔞 محتوای نامناسب", callback_data="rep_reason_18"),
                   types.InlineKeyboardButton("⚖️ مزاحمت و تبلیغات", callback_data="rep_reason_spam"))
            bot.send_message(cid, "❓ **علت گزارش چیه؟**", reply_markup=kb)
            return
        if partner:
            try:
                if message.content_type == 'text': bot.send_message(partner, f"💬: {text}")
                elif message.content_type == 'photo': bot.send_photo(partner, message.photo[-1].file_id)
                elif message.content_type == 'voice': bot.send_voice(partner, message.voice.file_id)
                elif message.content_type == 'sticker': bot.send_sticker(partner, message.sticker.file_id)
            except: pass

    # --- منوی اصلی ---
    if user["state"] == "main":
        if text == "🚀 پیدا کردن هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="s_male"), types.InlineKeyboardButton("خانم 👧", callback_data="s_female"), types.InlineKeyboardButton("🌈 واسم فرقی نمی‌کنه", callback_data="s_any"))
            bot.send_message(cid, "🛰 **سیگنال‌های یابنده فعال شد!**\n\nدنبال کی می‌گردی؟", reply_markup=kb)
        elif text == "🔗 لینک ناشناس من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_users()
            bot.send_message(cid, f"🎁 **لینک ناشناس تو:**\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
        elif text == "👤 پروفایل من":
            icon = "👦" if user['gender'] == 'male' else "👧"
            bot.send_message(cid, f"👤 نام: {user['name']}\n🚻 جنسیت: {icon}\n🎂 سن: {user['age']}")
        elif text == "ℹ️ راهنما":
            bot.send_message(cid, "📖 **راهنمای ربات:**\n\n1️⃣ با دکمه **هم‌صحبت**، غریبه‌ها رو پیدا کن.\n2️⃣ با **لینک ناشناس**، بذار بقیه بهت پیام مخفی بدن.")

    # --- ارسال ناشناس ---
    if user["state"] == "anon_write" and text:
        anon_pending[cid] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال نهایی", callback_data="send_anon_final"), types.InlineKeyboardButton("❌ لغو", callback_data="cancel_anon"))
        bot.send_message(cid, f"📝 **پیامت:**\n\n_{text}_\n\nارسال بشه؟", reply_markup=kb, parse_mode="Markdown")

# --- کال‌بک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); load_data(); user = users.get(cid)
    if not user: return

    if call.data == "check_membership":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ تایید شد!")
            bot.delete_message(cid, call.message.id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)

    if call.data.startswith("s_"):
        pref = call.data.replace("s_", "")
        user.update({"search_pref": pref, "state": "searching"})
        save_users()
        try: bot.delete_message(cid, call.message.id)
        except: pass
        found = False
        search_list = ["male", "female"] if pref == "any" else [pref]
        for g in search_list:
            if waiting[g]:
                pid = waiting[g].pop(0)
                if pid != cid:
                    p = users[pid]
                    user.update({"partner": pid, "state": "chat"})
                    p.update({"partner": cid, "state": "chat"})
                    save_users()
                    bot.send_message(cid, "💎 **ایول! یه هم‌صحبت عالی پیدا کردم.**", reply_markup=chat_kb())
                    bot.send_message(pid, "💎 **ایول! یه هم‌صحبت عالی پیدا کردم.**", reply_markup=chat_kb())
                    found = True; break
        if not found:
            waiting[user['gender']].append(cid)
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ لغو جستجو", callback_data="cancel_search"))
            bot.send_message(cid, "🔍 **در حال اسکن کردن کهکشانِ کاربران...**", reply_markup=kb)

    if call.data == "confirm_end":
        p_id = user.get("partner")
        if p_id: 
            users[p_id].update({"partner": None, "state": "main"})
            bot.send_message(p_id, "⚠️ **طرف مقابل چت رو ترک کرد.**", reply_markup=main_kb())
        user.update({"partner": None, "state": "main"})
        save_users(); bot.send_message(cid, "🔚 **مکالمه تموم شد.**", reply_markup=main_kb())

    if call.data.startswith("rep_reason_"):
        reason = call.data.replace("rep_reason_", ""); p_id = user.get("partner")
        if p_id:
            bot.send_message(ADMIN_ID, f"🚨 **گزارش تخلف**\nفرد گزارش شده: `{p_id}`\nعلت: {reason}")
            bot.answer_callback_query(call.id, "✅ گزارش شما برای ادمین ارسال شد.", show_alert=True)
            bot.delete_message(cid, call.message.id)

    if call.data == "send_anon_final":
        target = user.get("anon_target")
        msg = anon_pending.pop(cid, "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 پاسخ", callback_data=f"rep_{cid}"))
            bot.send_message(target, f"📬 **پیام ناشناس:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "✅ **ارسال شد.**", reply_markup=main_kb())
        user["state"] = "main"; save_users()

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.infinity_polling()
