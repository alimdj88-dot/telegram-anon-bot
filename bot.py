import telebot
from telebot import types
import json, os, random
from datetime import datetime
from flask import Flask
from threading import Thread
import time

# --- تنظیمات سرور برای بیدار ماندن در رندر ---
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is Active and Running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------

# توکن و تنظیمات اصلی
TOKEN = "8213706320:AAGuZ8G0GKepNz4F82ILaoQVOQbZrjwvN-I"
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

# فایل‌های ذخیره‌سازی
USERS_FILE = "users.json"
CHATS_FILE = "chats.json"

users = {}
links = {}
waiting = {"male": [], "female": []}
anon_pending = {}
chats = []

# ---------- بارگذاری و ذخیره داده‌ها ----------
def load_data():
    global users, chats
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except: users = {}
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                chats = json.load(f)
        except: chats = []

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_chats():
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats, f, ensure_ascii=False, indent=2)

# ---------- کیبوردهای حرفه‌ای ----------
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 شروع چت ناشناس", "🔗 لینک اختصاصی من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    return kb

def gender_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("آقا 👦", "خانم 👧")
    return kb

def end_chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔚 قطع مکالمه")
    return kb

def cancel_search_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("❌ انصراف از جستجو")
    return kb

def main_menu(cid):
    users[cid]["state"] = "main"
    welcome_text = (
        f"🌟 **منوی اصلی**\n\n"
        f"خوش اومدی {users[cid].get('name', 'دوست من')}! چه کاری برات انجام بدم؟"
    )
    bot.send_message(cid, welcome_text, reply_markup=main_kb(), parse_mode="Markdown")
    save_users()

# ---------- هندل کردن دستور /start ----------
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    args = message.text.split()

    # اگر کاربر از طریق لینک ناشناس آمده باشد
    if len(args) > 1:
        code = args[1]
        if code in links:
            owner = links[code]
            if owner == cid:
                bot.send_message(cid, "⚠️ شما نمی‌توانید به خودتان پیام ناشناس بفرستید!")
                return
            users.setdefault(cid, {"name": message.from_user.first_name})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = owner
            bot.send_message(cid, "✉️ هر حرفی تو دلت هست رو بنویس تا کاملاً ناشناس براش بفرستم:")
            save_users()
            return

    # ثبت‌نام کاربر جدید
    if cid not in users or "gender" not in users[cid]:
        users[cid] = {"state": "name"}
        bot.send_message(cid, "🌱 سلام! به دنیای چت ناشناس خوش اومدی.\n\nابتدا اسمت رو وارد کن:")
        save_users()
        return

    main_menu(cid)

# ---------- مدیریت پیام‌های متنی ----------
@bot.message_handler(func=lambda m: True)
def handle(message):
    cid = str(message.chat.id)
    text = message.text
    user = users.get(cid)
    if not user: return

    state = user.get("state")

    # مراحل تکمیل پروفایل
    if state == "name":
        user["name"] = text.strip()
        user["state"] = "gender"
        bot.send_message(cid, f"✅ خوشبختم {text} عزیز!\nجنسیت خودت رو انتخاب کن:", reply_markup=gender_kb())
        save_users()
        return

    if state == "gender":
        if text not in ["آقا 👦", "خانم 👧"]: return
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "age"
        bot.send_message(cid, "🎂 سن خودت رو وارد کن (عددی بین 13 تا 60):")
        save_users()
        return

    if state == "age":
        if not text.isdigit() or not 13 <= int(text) <= 60:
            bot.send_message(cid, "⚠️ لطفاً یک عدد معتبر بین 13 تا 60 وارد کن:")
            return
        user["age"] = int(text)
        main_menu(cid)
        return

    # مدیریت منوی اصلی
    if state == "main":
        if text == "🚀 شروع چت ناشناس":
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("آقا 👦", callback_data="search_male"),
                types.InlineKeyboardButton("خانم 👧", callback_data="search_female")
            )
            kb.add(types.InlineKeyboardButton("فرقی نمی‌کنه 👫", callback_data="search_any"))
            bot.send_message(cid, "🎯 دوست داری با چه کسی هم‌صحبت بشی؟", reply_markup=kb)
            
        elif text == "🔗 لینک اختصاصی من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code
            links[code] = cid
            link_text = (
                f"🔗 لینک ناشناس اختصاصی شما ساخته شد!\n\n"
                f"این لینک رو توی بیو اینستاگرام یا کانالت بذار تا بقیه بتونن بهت پیام ناشناس بدن:\n\n"
                f"👉 `https://t.me/{BOT_USERNAME}?start={code}`"
            )
            bot.send_message(cid, link_text, parse_mode="Markdown")
            save_users()

        elif text == "👤 پروفایل من":
            gender_icon = "👦" if user['gender'] == 'male' else "👧"
            profile_text = (
                f"📝 **اطلاعات شما:**\n\n"
                f"👤 نام: {user['name']}\n"
                f"🚻 جنسیت: {gender_icon}\n"
                f"🎂 سن: {user['age']}\n"
            )
            bot.send_message(cid, profile_text, parse_mode="Markdown")

    # مدیریت حالت چت فعال
    if state == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            if partner and partner in users:
                users[partner]["partner"] = None
                main_menu(partner)
                bot.send_message(partner, "⚠️ طرف مقابل مکالمه رو قطع کرد.")
            user["partner"] = None
            main_menu(cid)
            return
        
        if partner:
            bot.send_message(partner, f"👤: {text}")
            chats.append({
                "from": cid, "to": partner, "text": text,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_chats()

    # ارسال پیام ناشناس (لینک)
    if state == "anon_write":
        anon_pending[cid] = text
        user["state"] = "anon_confirm"
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ تایید و ارسال", callback_data="anon_send"),
            types.InlineKeyboardButton("❌ لغو", callback_data="anon_cancel")
        )
        bot.send_message(cid, f"💬 پیش‌نمایش پیام شما:\n\n_{text}_\n\nآیا از ارسال مطمئنی؟", reply_markup=kb, parse_mode="Markdown")

# ---------- مدیریت دکمه‌های شیشه‌ای ----------
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id)
    user = users.get(cid)
    if not user: return

    # منطق جستجوی کاربر
    if call.data.startswith("search_"):
        pref = call.data.replace("search_", "")
        user_gender = user.get("gender")
        user["state"] = "searching"
        user["search_pref"] = pref
        search_in = ["male", "female"] if pref == "any" else [pref]
        
        found = False
        for g in search_in:
            for pid in waiting[g]:
                partner = users.get(pid)
                if partner and (partner.get("search_pref") == "any" or partner.get("search_pref") == user_gender):
                    user["partner"], partner["partner"] = pid, cid
                    user["state"] = partner["state"] = "chat"
                    waiting[g].remove(pid)
                    bot.send_message(cid, "🎉 به یک نفر متصل شدی! حالا می‌تونی چت کنی.", reply_markup=end_chat_kb())
                    bot.send_message(pid, "🎉 یک نفر پیدا شد! مکالمه رو شروع کن.", reply_markup=end_chat_kb())
                    save_users()
                    found = True
                    break
            if found: break
        if not found:
            if cid not in waiting[user_gender]: waiting[user_gender].append(cid)
            bot.edit_message_text("⏳ در حال جستجوی هم‌صحبت مناسب... لطفاً صبور باشید.", cid, call.message.id)

    # ارسال نهایی پیام ناشناس لینک
    if call.data == "anon_send":
        target = user["anon_target"]
        msg = anon_pending.pop(cid, "...")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📩 پاسخ به این پیام", callback_data=f"rep_{cid}"))
        bot.send_message(target, f"🔔 یک پیام ناشناس جدید داری:\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
        bot.send_message(cid, "✅ پیام شما با موفقیت و به صورت کاملاً ناشناس ارسال شد.")
        main_menu(cid)

    # پاسخ به پیام ناشناس
    if call.data.startswith("rep_"):
        sender_id = call.data.replace("rep_", "")
        bot.send_message(sender_id, "👀 طرف مقابل پیام شما رو دید و در حال پاسخ دادنه...")
        user["state"] = "anon_write"
        user["anon_target"] = sender_id
        bot.send_message(cid, "✍️ پاسخت رو بنویس تا براش بفرستم:")

# ---------- اجرای نهایی ----------
if __name__ == "__main__":
    load_data()
    keep_alive()
    print("🚀 Bot is starting successfully...")
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
