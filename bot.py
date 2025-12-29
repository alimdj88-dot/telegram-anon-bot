import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- تنظیمات سرور ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is Online!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" # آیدی عددی خودت را اینجا بزن
BOT_USERNAME = "Chatnashenas_IriBot"
CHANNELS = ["@ChatNaAnnouncements"] 
bot = telebot.TeleBot(TOKEN)

# --- متغیرهای سیستمی (بسیار مهم) ---
USERS_FILE = "users.json"
waiting = {"male": [], "female": []} # تعریف صف انتظار برای جلوگیری از خطا
users = {}

# --- مدیریت داده‌ها ---
def load_data():
    global users
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except: users = {}

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# --- بررسی عضویت ---
def is_member(user_id):
    if str(user_id) == str(ADMIN_ID): return True
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        except: continue
    return True

# --- کیبوردهای اصلی ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 پیدا کردن هم‌صحبت", "🔗 لینک ناشناس من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    if str(ADMIN_ID) != "YOUR_CHAT_ID": # دکمه ادمین فقط برای شما
         kb.add("📢 ارسال پیام همگانی")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# --- شروع ربات ---
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    
    # جوین اجباری
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            kb.add(types.InlineKeyboardButton(f"📢 عضویت در کانال {i}", url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ عضو شدم! (تایید نهایی)", callback_data="check_membership"))
        bot.send_message(cid, "💎 **خوش اومدی!**\n\nواسه استفاده از ربات، اول تو کانال‌های زیر عضو شو و بعد روی تایید بزن:", reply_markup=kb)
        return

    # لینک ناشناس
    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسسس!**\n\nداری یه پیام ناشناس می‌فرستی. بنویس تا مخفیانه برسونم:", reply_markup=types.ReplyKeyboardRemove())
            save_users()
            return

    # ثبت نام
    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 **سلام! به دنیای بزرگ چت ناشناس خوش اومدی.**\n\n✨ واسه قدم اول، بگو چی **صدات کنم؟**")
        save_users()
    else:
        name = users[cid].get("name", "دوست من")
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 **{name} جان، خیلی خوش برگشتی!**", reply_markup=main_kb())

# --- بخش ادمین (ارسال همگانی) ---
@bot.message_handler(func=lambda m: m.text == "📢 ارسال پیام همگانی")
def admin_broadcast(message):
    if str(message.chat.id) == str(ADMIN_ID):
        users[str(ADMIN_ID)]["state"] = "broadcasting"
        bot.send_message(ADMIN_ID, "📝 پیام یا مدیای خودت رو بفرست تا برای همه اعضا ارسال بشه:")

# --- مدیریت پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id); load_data()
    user = users.get(cid)
    if not user: return
    text = message.text

    # ارسال همگانی ادمین
    if user.get("state") == "broadcasting" and str(cid) == str(ADMIN_ID):
        count = 0
        for uid in users:
            try:
                bot.copy_message(uid, cid, message.message_id)
                count += 1
            except: pass
        user["state"] = "main"
        bot.send_message(ADMIN_ID, f"✅ پیام شما به {count} نفر ارسال شد.", reply_markup=main_kb())
        return

    # ثبت نام
    if user["state"] == "get_name" and text:
        user["name"] = text[:15]; user["state"] = "get_gender"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("آقا هستم 👦", "خانم هستم 👧")
        bot.send_message(cid, f"✅ خوشبختم {user['name']}! جنسیتت چیه؟", reply_markup=kb); save_users(); return
    
    if user["state"] == "get_gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "get_age"
        bot.send_message(cid, "🎂 **چند سالته؟** (عدد بفرست)"); save_users(); return

    if user["state"] == "get_age" and text:
        if text.isdigit():
            user["age"] = int(text); user["state"] = "main"
            bot.send_message(cid, "🎉 **ثبت‌نامت تموم شد!**", reply_markup=main_kb()); save_users(); return

    # منوی اصلی
    if user["state"] == "main":
        if text == "🚀 پیدا کردن هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("آقا 👦", callback_data="s_male"),
                types.InlineKeyboardButton("خانم 👧", callback_data="s_female"),
                types.InlineKeyboardButton("🌈 واسم فرقی نمی‌کنه", callback_data="s_any"))
            bot.send_message(cid, "🛰 **سیگنال‌های یابنده فعال شد!**\n\nدنبال کی می‌گردی؟", reply_markup=kb)
        elif text == "🔗 لینک ناشناس من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_users()
            bot.send_message(cid, f"🎁 **لینک ناشناس تو:**\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
        elif text == "👤 پروفایل من":
            icon = "👦" if user.get('gender') == 'male' else "👧"
            bot.send_message(cid, f"📝 **پروفایل تو:**\n\n👤 نام: {user.get('name')}\n🚻 جنسیت: {icon}\n🎂 سن: {user.get('age')}")
        elif text == "ℹ️ راهنما":
            bot.send_message(cid, "📖 **راهنما:**\n1- چت ناشناس: وصل شدن به غریبه‌ها\n2- لینک ناشناس: دریافت پیام مخفی")

    # چت فعال
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله", callback_data="confirm_end"), types.InlineKeyboardButton("❌ خیر", callback_data="cancel_end"))
            bot.send_message(cid, "⚠️ مطمئنی؟", reply_markup=kb)
        elif text == "🚩 گزارش تخلف":
            kb = types.InlineKeyboardMarkup(row_width=1).add(
                types.InlineKeyboardButton("🤬 فحاشی", callback_data="rep_insult"),
                types.InlineKeyboardButton("🔞 محتوای جنسی", callback_data="rep_18"),
                types.InlineKeyboardButton("⚖️ مزاحمت", callback_data="rep_spam"))
            bot.send_message(cid, "❓ دلیل گزارش چیه؟", reply_markup=kb)
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

    # ارسال ناشناس
    if user["state"] == "anon_write" and text:
        anon_pending[cid] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال", callback_data="send_anon_final"), types.InlineKeyboardButton("❌ لغو", callback_data="cancel_anon"))
        bot.send_message(cid, f"📝 پیامت:\n_{text}_\nارسال بشه؟", reply_markup=kb, parse_mode="Markdown")

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
                    bot.send_message(cid, "💎 **ایول! یکی رو پیدا کردم.**", reply_markup=chat_kb())
                    bot.send_message(pid, "💎 **ایول! یکی رو پیدا کردم.**", reply_markup=chat_kb())
                    found = True; break
        if not found:
            waiting[user.get('gender', 'male')].append(cid)
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ لغو جستجو", callback_data="cancel_search"))
            bot.send_message(cid, "🔍 **در حال اسکن کردن کهکشانِ کاربران...**", reply_markup=kb)

    if call.data == "cancel_search":
        for g in waiting:
            if cid in waiting[g]: waiting[g].remove(cid)
        user["state"] = "main"; bot.edit_message_text("📥 جستجو لغو شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی:", reply_markup=main_kb())

    if call.data.startswith("rep_"):
        bot.send_message(ADMIN_ID, f"🚨 **گزارش تخلف**\nآیدی: `{user.get('partner')}`\nعلت: {call.data}")
        bot.answer_callback_query(call.id, "✅ گزارش ارسال شد.", show_alert=True)

    if call.data == "send_anon_final":
        target = user.get("anon_target")
        msg = anon_pending.pop(cid, "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 پاسخ", callback_data=f"rep_anon_{cid}"))
            bot.send_message(target, f"📬 **پیام ناشناس:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "✅ ارسال شد.", reply_markup=main_kb())
        user["state"] = "main"; save_users()

    if call.data == "confirm_end":
        p_id = user.get("partner")
        if p_id: 
            users[p_id].update({"partner": None, "state": "main"})
            bot.send_message(p_id, "⚠️ طرف مقابل چت رو ترک کرد.", reply_markup=main_kb())
        user.update({"partner": None, "state": "main"})
        bot.send_message(cid, "🔚 قطع شد.", reply_markup=main_kb()); save_users()

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.infinity_polling()
