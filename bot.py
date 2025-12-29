import telebot
from telebot import types
import json, os, random
from datetime import datetime
from flask import Flask
from threading import Thread
import time

# --- تنظیمات سرور برای پایداری ---
app = Flask('')
@app.route('/')
def home(): return "✅ ChatNashenas Pro is Running!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- تنظیمات اصلی ربات ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091"  # <--- حتماً آیدی عددی خودت رو اینجا بزن
BOT_NAME = "چت ناشناس"
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
BLACKLIST_FILE = "blacklist.json"

users = {}
waiting = {"male": [], "female": []}
blacklist = []
anon_pending = {}

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
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=2)

# --- طراحی کیبوردهای UI ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 پیدا کردن هم‌صحبت", "🔗 لینک ناشناس من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# --- شروع و ثبت‌نام ---
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    
    if cid in blacklist:
        bot.send_message(cid, "🚫 **دسترسی شما به دلیل نقض قوانین مسدود شده است.**", parse_mode="Markdown")
        return

    # بررسی لینک ناشناس
    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id:
            if target_id == cid:
                bot.send_message(cid, "😅 شوخی می‌کنی؟ نمی‌تونی به خودت پیام ناشناس بدی!")
                return
            users.setdefault(cid, {"state": "main"})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسسس!**\n\nداری یه پیام ناشناس می‌فرستی. هر چی تو دلت هست رو اینجا بنویس تا من بدون اینکه اسمت رو بگم به طرف برسونم:", reply_markup=types.ReplyKeyboardRemove())
            return

    # سیستم هوشمند ثبت‌نام و خوش‌آمدگویی
    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, f"🌟 **سلام! به دنیای بزرگ {BOT_NAME} خوش اومدی.**\n\nاینجا می‌تونی دوستای جدید پیدا کنی یا لینک ناشناس بگیری.\n\n✨ واسه قدم اول، بگو دوست داری چی **صدات کنم؟** (اسمت رو بفرست)")
        save_users()
    else:
        name = users[cid].get("name", "دوست من")
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 **{name} جان، خیلی خوش برگشتی!**\n\nامروز قراره با کی گپ بزنیم؟ از منوی زیر انتخاب کن:", reply_markup=main_kb())

@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id)
    if cid in blacklist: return
    user = users.get(cid)
    if not user: return
    text = message.text

    # --- فرآیند ثبت‌نام ---
    if user["state"] == "get_name" and text:
        user["name"] = text[:15]; user["state"] = "get_gender"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("آقا هستم 👦", "خانم هستم 👧")
        bot.send_message(cid, f"✅ خوشبختم **{user['name']}** عزیز!\nحالا واسه اینکه هم‌صحبت بهتری پیدا کنیم، جنسیتت رو انتخاب کن:", reply_markup=kb, parse_mode="Markdown")
        return

    if user["state"] == "get_gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "get_age"
        bot.send_message(cid, "🎂 **چند سالته؟** (لطفاً عدد سن‌ت رو بفرست تا با هم‌سن‌های خودت چت کنی)", reply_markup=types.ReplyKeyboardRemove())
        return

    if user["state"] == "get_age" and text:
        if text.isdigit():
            user["age"] = int(text); user["state"] = "main"
            bot.send_message(cid, f"🎉 **ایول! ثبت‌نامت تموم شد.**\nحالا با خیال راحت برو تو دنیای چت ناشناس!", reply_markup=main_kb())
            save_users()
        return

    # --- منوی اصلی ---
    if user["state"] == "main":
        if text == "🚀 پیدا کردن هم‌صحبت":
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="s_male"),
                   types.InlineKeyboardButton("خانم 👧", callback_data="s_female"))
            kb.add(types.InlineKeyboardButton("🌈 واسم فرقی نمی‌کنه", callback_data="s_any"))
            bot.send_message(cid, "🛰 **سیگنال‌های یابنده فعال شد!**\n\nدنبال هم‌صحبت با چه جنسیتی می‌گردی؟", reply_markup=kb, parse_mode="Markdown")
        
        elif text == "🔗 لینک ناشناس من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_users()
            bot.send_message(cid, f"🎁 **لینک اختصاصی و همیشگی تو آماده شد!**\n\nاین لینک رو کپی کن و بذار توی بیو اینستات یا تلگرامت تا بقیه بتونن بهت پیام ناشناس بدن:\n\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")

        elif text == "👤 پروفایل من":
            icon = "👦" if user['gender'] == 'male' else "👧"
            bot.send_message(cid, f"📝 **مشخصات کاربری تو:**\n\n👤 نام: {user['name']}\n🚻 جنسیت: {icon}\n🎂 سن: {user['age']}\n⭐ امتیاز: 5/5", parse_mode="Markdown")

        elif text == "ℹ️ راهنما":
            bot.send_message(cid, "📖 **چطوری با من کار کنی؟**\n\n1️⃣ با دکمه پیدا کردن هم‌صحبت، به صورت اتفاقی به یک نفر وصل میشی.\n2️⃣ لینک ناشناس رو به بقیه بده تا حرفای دلشون رو بهت بزنن.\n3️⃣ امنیت اینجا اولویته، اگه کسی اذیت کرد سریع گزارش بده!")

    # --- چت فعال ---
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله، قطع کن", callback_data="confirm_end"), types.InlineKeyboardButton("❌ ادامه گپ", callback_data="cancel_end"))
            bot.send_message(cid, "⚠️ **مطمئنی می‌خوای این مکالمه جذاب رو قطع کنی؟**", reply_markup=kb, parse_mode="Markdown")
        elif text == "🚩 گزارش تخلف":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚩 تایید و ارسال گزارش", callback_data="report_confirm"))
            bot.send_message(cid, "‼️ **آیا این کاربر قوانین رو نقض کرده؟**\n(گزارش شما مستقیم برای مدیریت ارسال میشه)", reply_markup=kb, parse_mode="Markdown")
        elif partner:
            try:
                if message.content_type == 'text': bot.send_message(partner, f"💬: {text}")
                elif message.content_type == 'photo': bot.send_photo(partner, message.photo[-1].file_id)
                elif message.content_type == 'voice': bot.send_voice(partner, message.voice.file_id)
                elif message.content_type == 'sticker': bot.send_sticker(partner, message.sticker.file_id)
            except: pass

    # --- فرآیند ارسال پیام ناشناس ---
    if user["state"] == "anon_write" and text:
        anon_pending[cid] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال نهایی", callback_data="send_anon_final"), types.InlineKeyboardButton("❌ لغو", callback_data="cancel_anon"))
        bot.send_message(cid, f"📝 **پیش‌نمایش پیام تو:**\n\n_{text}_\n\nآیا از ارسالش مطمئنی؟", reply_markup=kb, parse_mode="Markdown")

# --- مدیریت Callback Query ها ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); user = users.get(cid)
    if not user: return

    # منطق جستجوی جذاب
    if call.data.startswith("s_"):
        pref = call.data.replace("s_", "")
        user.update({"search_pref": pref, "state": "searching"})
        
        # حذف پیام قبلی برای خلوت شدن صفحه
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
                    bot.send_message(cid, "💎 **ایول! یه هم‌صحبت عالی پیدا کردم.**\nالان به هم وصل شدید. شروع کن به گپ زدن! 👇", reply_markup=chat_kb())
                    bot.send_message(pid, "💎 **ایول! یه هم‌صحبت عالی پیدا کردم.**\nالان به هم وصل شدید. شروع کن به گپ زدن! 👇", reply_markup=chat_kb())
                    found = True; break
        
        if not found:
            waiting[user['gender']].append(cid)
            search_text = (
                "🔍 **در حال اسکن کردن کهکشانِ کاربران...**\n\n"
                "توی صفِ انتظار قرارت دادم. دارم می‌گردم تا یه هم‌صحبتِ خوش‌انرژی برات پیدا کنم. صبور باش... ✨"
            )
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ لغو جستجو و بازگشت", callback_data="cancel_search"))
            bot.send_message(cid, search_text, reply_markup=kb, parse_mode="Markdown")

    if call.data == "cancel_search":
        for g in waiting:
            if cid in waiting[g]: waiting[g].remove(cid)
        user["state"] = "main"
        bot.edit_message_text("📥 **جستجو لغو شد.**\nبرگشتیم به منوی اصلی. هر وقت دوست داشتی دوباره بگرد!", cid, call.message.id, parse_mode="Markdown")
        bot.send_message(cid, "🏡 منوی اصلی فعال شد:", reply_markup=main_kb())

    # گزارش و پنل ادمین
    if call.data == "report_confirm":
        p_id = user.get("partner")
        if p_id:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🚫 مسدود سازی (Ban)", callback_data=f"adm_ban_{p_id}"),
                   types.InlineKeyboardButton("✅ صرف نظر", callback_data="adm_ignore"))
            bot.send_message(ADMIN_ID, f"🚨 **گزارش تخلف**\n\nمتخلف: `{p_id}`\nنام: {users[p_id]['name']}\nگزارش‌دهنده: `{cid}`", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "✅ گزارش شما با موفقیت برای مدیریت ارسال و چت قطع شد.")
            bot.send_message(p_id, "⚠️ مکالمه به دلیل گزارش تخلف توسط طرف مقابل پایان یافت.")
            users[p_id].update({"partner": None, "state": "main"}); user.update({"partner": None, "state": "main"})
            bot.send_message(cid, "🏡 منو اصلی", reply_markup=main_kb()); bot.send_message(p_id, "🏡 منو اصلی", reply_markup=main_kb())

    if call.data.startswith("adm_ban_"):
        target = call.data.replace("adm_ban_", "")
        if target not in blacklist:
            blacklist.append(target); save_blacklist()
            bot.send_message(target, "❌ **شما توسط ادمین از ربات اخراج شدید.**")
            bot.edit_message_text(f"✅ کاربر {target} بن شد.", cid, call.message.id)

    if call.data == "adm_ignore":
        bot.edit_message_text("✅ گزارش رد شد.", cid, call.message.id)

    # پیام ناشناس
    if call.data == "send_anon_final":
        target = user.get("anon_target")
        msg = anon_pending.pop(cid, "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 پاسخ به این پیام", callback_data=f"rep_{cid}"))
            bot.send_message(target, f"📬 **یه پیام ناشناسِ جدید داری:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "✅ پیامت با موفقیت و کاملاً مخفیانه ارسال شد.", reply_markup=main_kb())
        user["state"] = "main"

    if call.data.startswith("rep_"):
        user.update({"state": "anon_write", "anon_target": call.data.replace("rep_", "")})
        bot.send_message(cid, "✍️ **پاسخت رو بنویس:**")

    if call.data == "confirm_end":
        p_id = user.get("partner")
        if p_id: 
            users[p_id].update({"partner": None, "state": "main"})
            bot.send_message(p_id, "⚠️ **طرف مقابل چت رو ترک کرد.**", reply_markup=main_kb())
        user.update({"partner": None, "state": "main"})
        bot.send_message(cid, "🔚 **مکالمه تموم شد.**", reply_markup=main_kb())

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.remove_webhook()
    bot.infinity_polling()
