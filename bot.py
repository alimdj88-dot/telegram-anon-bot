import telebot
from telebot import types
import json, os, random
from datetime import datetime
from flask import Flask
from threading import Thread
import time

# --- تنظیمات سرور ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is Online & Fully Fixed!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" # <--- آیدی عددی خودت رو اینجا بذار (مثال: 12345678)
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
BLACKLIST_FILE = "blacklist.json"

users = {}
waiting = {"male": [], "female": []}
blacklist = []
anon_pending = {}

# ---------- مدیریت داده‌ها ----------
def load_data():
    global users, blacklist
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except: users = {}
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                blacklist = json.load(f)
        except: blacklist = []

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_blacklist():
    with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=2)

# ---------- طراحی UI (کیبوردها) ----------
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 شروع چت ناشناس", "🔗 لینک من")
    kb.add("👤 پروفایل", "ℹ️ راهنما")
    return kb

def end_chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# ---------- هندلرهای اصلی ----------
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    
    if cid in blacklist:
        bot.send_message(cid, "⛔️ **دسترسی شما به دلیل تخلف مسدود شده است.**", parse_mode="Markdown")
        return

    args = message.text.split()
    if len(args) > 1:
        target_id = None
        for uid, udata in users.items():
            if udata.get("link") == args[1]:
                target_id = uid
                break
        
        if target_id:
            if target_id == cid:
                bot.send_message(cid, "❌ **شوخی میکنی؟ نمیتونی به خودت پیام ناشناس بدی!**", parse_mode="Markdown")
                return
            users.setdefault(cid, {"name": message.from_user.first_name})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **در حال ارسال پیام ناشناس...**\n\nهر چه دل تنگت می‌خواهد بنویس تا به صورت کاملاً مخفی ارسال شود:", reply_markup=types.ReplyKeyboardRemove())
            save_users()
            return

    if cid not in users or "gender" not in users[cid]:
        users[cid] = {"state": "get_name"}
        welcome_text = "👋 **سلام به چت‌باکس خوش اومدی!**\n\n🔸 برای شروع، **نام یا مستعارت** رو بفرست:"
        bot.send_message(cid, welcome_text, parse_mode="Markdown")
        save_users()
        return
    
    users[cid]["state"] = "main"
    bot.send_message(cid, "🏡 **به منوی اصلی خوش اومدی!**", reply_markup=main_kb())

@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id)
    if cid in blacklist: return
    user = users.get(cid)
    if not user: return
    text = message.text

    # --- فرآیند ثبت نام ---
    if user["state"] == "get_name" and text:
        user["name"] = text[:20]
        user["state"] = "get_gender"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        kb.add("آقا 👦", "خانم 👧")
        bot.send_message(cid, f"✅ **خوشبختم {user['name']}!**\nجنسیت خودت رو انتخاب کن:", reply_markup=kb, parse_mode="Markdown")
        return

    if user["state"] == "get_gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "get_age"
        bot.send_message(cid, "🎂 **سن شما؟** (عدد بفرست)", reply_markup=types.ReplyKeyboardRemove())
        return

    if user["state"] == "get_age" and text:
        if text.isdigit():
            user["age"] = int(text)
            user["state"] = "main"
            bot.send_message(cid, "🎉 **پروفایل شما با موفقیت ساخته شد.**", reply_markup=main_kb())
            save_users()
        return

    # --- چت فعال ---
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("✅ بله", callback_data="confirm_end"),
                   types.InlineKeyboardButton("❌ خیر", callback_data="cancel_end"))
            bot.send_message(cid, "❓ **مطمئنی می‌خوای چت رو تموم کنی؟**", reply_markup=kb, parse_mode="Markdown")
            return
        
        if text == "🚩 گزارش تخلف":
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("🚩 تایید و انتخاب دلیل", callback_data="report_confirm"))
            bot.send_message(cid, "⚠️ **آیا این کاربر قانونی را نقض کرده است؟**", reply_markup=kb, parse_mode="Markdown")
            return

        if partner:
            if message.content_type == 'text': bot.send_message(partner, f"💬: {text}")
            elif message.content_type == 'photo': bot.send_photo(partner, message.photo[-1].file_id)
            elif message.content_type == 'voice': bot.send_voice(partner, message.voice.file_id)
            elif message.content_type == 'video': bot.send_video(partner, message.video.file_id)
            elif message.content_type == 'sticker': bot.send_sticker(partner, message.sticker.file_id)

    # --- منوی اصلی ---
    if user["state"] == "main" and text:
        if text == "🚀 شروع چت ناشناس":
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="s_male"),
                   types.InlineKeyboardButton("خانم 👧", callback_data="s_female"))
            kb.add(types.InlineKeyboardButton("🌈 فرقی نمی‌کنه", callback_data="s_any"))
            bot.send_message(cid, "🛰 **دنبال چه کسی می‌گردی؟**", reply_markup=kb, parse_mode="Markdown")
        
        elif text == "🔗 لینک من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code
            bot.send_message(cid, f"🎁 **لینک ناشناس تو:**\n\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
            save_users()

        elif text == "👤 پروفایل":
            gender_icon = "👦" if user['gender'] == 'male' else "👧"
            profile = f"👤 **نام:** {user['name']}\n🎂 **سن:** {user['age']}\n🚻 **جنسیت:** {gender_icon}"
            bot.send_message(cid, profile, parse_mode="Markdown")

        elif text == "ℹ️ راهنما":
            guide = "📖 **راهنما:**\n1- چت ناشناس برای وصل شدن به غریبه‌ها.\n2- لینک من برای دریافت پیام ناشناس."
            bot.send_message(cid, guide, parse_mode="Markdown")

    # --- نوشتن پیام ناشناس ---
    if user["state"] == "anon_write" and text:
        anon_pending[cid] = text
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🚀 ارسال", callback_data="send_anon_final"),
               types.InlineKeyboardButton("❌ لغو", callback_data="cancel_anon"))
        bot.send_message(cid, f"📝 **متن شما:**\n\n_{text}_\n\nآیا ارسال شود؟", reply_markup=kb, parse_mode="Markdown")

# ---------- کال‌بک‌ها ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id)
    user = users.get(cid)
    if not user: return

    # جستجو
    if call.data.startswith("s_"):
        pref = call.data.replace("s_", "")
        user.update({"search_pref": pref, "state": "searching"})
        found = False
        search_list = ["male", "female"] if pref == "any" else [pref]
        for g in search_list:
            if waiting[g]:
                pid = waiting[g].pop(0)
                if pid != cid:
                    p = users[pid]
                    user.update({"partner": pid, "state": "chat"})
                    p.update({"partner": cid, "state": "chat"})
                    bot.send_message(cid, "💎 **وصل شدی!**", reply_markup=end_chat_kb())
                    bot.send_message(pid, "💎 **وصل شدی!**", reply_markup=end_chat_kb())
                    found = True; break
        if not found:
            waiting[user['gender']].append(cid)
            bot.edit_message_text("🔍 **در حال جستجو...**", cid, call.message.id)

    # گزارش تخلف
    if call.data == "report_confirm":
        kb = types.InlineKeyboardMarkup()
        reasons = [("توهین 🤬", "r_insult"), ("محتوای نامناسب 🔞", "r_18"), ("اسپم 📢", "r_spam")]
        for t, d in reasons: kb.add(types.InlineKeyboardButton(t, callback_data=d))
        bot.edit_message_text("📍 دلیل گزارش را انتخاب کنید:", cid, call.message.id, reply_markup=kb)

    if call.data.startswith("r_"):
        partner_id = user.get("partner")
        if partner_id:
            bot.send_message(ADMIN_ID, f"🚨 **گزارش**\nمتخلف: `{partner_id}`\nدلیل: {call.data}\nتوسط: `{cid}`")
            bot.send_message(cid, "✅ گزارش ارسال و چت قطع شد.")
            bot.send_message(partner_id, "⚠️ مکالمه به دلیل گزارش پایان یافت.")
            users[partner_id].update({"partner": None, "state": "main"})
            user.update({"partner": None, "state": "main"})
            bot.send_message(cid, "🏡 منوی اصلی", reply_markup=main_kb())
            bot.send_message(partner_id, "🏡 منوی اصلی", reply_markup=main_kb())

    # ارسال پیام ناشناس (لینک)
    if call.data == "send_anon_final":
        target = user.get("anon_target")
        msg = anon_pending.pop(cid, "")
        if target:
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("📩 پاسخ به این پیام", callback_data=f"rep_{cid}"))
            bot.send_message(target, f"📬 **پیام ناشناس جدید:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "✅ ارسال شد.", reply_markup=main_kb())
        user["state"] = "main"

    # پاسخ به پیام ناشناس
    if call.data.startswith("rep_"):
        sender_id = call.data.replace("rep_", "")
        user.update({"state": "anon_write", "anon_target": sender_id})
        bot.send_message(cid, "✍️ پاسخت رو بنویس:")

    if call.data == "confirm_end":
        p_id = user.get("partner")
        if p_id:
            users[p_id].update({"partner": None, "state": "main"})
            bot.send_message(p_id, "⚠️ چت قطع شد.", reply_markup=main_kb())
        user.update({"partner": None, "state": "main"})
        bot.send_message(cid, "🔚 چت قطع شد.", reply_markup=main_kb())

if __name__ == "__main__":
    load_data()
    keep_alive()
    bot.remove_webhook()
    bot.infinity_polling()
