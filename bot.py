import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- سرور ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is Fixed & Powerfull!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091"  # آیدی عددی خودت
BOT_USERNAME = "Chatnashenas_IriBot"
CHANNELS = ["@ChatNaAnnouncements"] 
bot = telebot.TeleBot(TOKEN)

# دیتابیس ساده
USERS_FILE = "users.json"
users = {}
waiting = {"male": [], "female": []}
broadcast_msg = {} # برای ذخیره موقت پیام همگانی

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
            status = bot.get_chat_member(ch, user_id).status
            if status in ['left', 'kicked']: return False
        except: continue
    return True

# کیبوردها
def main_kb(cid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 پیدا کردن هم‌صحبت", "🔗 لینک ناشناس من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
    if str(cid) == str(ADMIN_ID):
        kb.add("📢 ارسال پیام همگانی")
    return kb

def chat_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 قطع مکالمه", "🚩 گزارش تخلف")
    return kb

# --- شروع ---
@bot.message_handler(commands=["start"])
def start(message):
    cid = str(message.chat.id)
    load_data()
    
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            kb.add(types.InlineKeyboardButton(f"📢 عضویت در کانال {i}", url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ عضو شدم! (تایید)", callback_data="check_membership"))
        bot.send_message(cid, "💎 **خوش اومدی!**\n\nواسه استفاده، اول عضو کانال‌ها شو:", reply_markup=kb)
        return

    # مدیریت لینک ناشناس (بدون تکرار استارت)
    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسسس!**\n\nداری پیام ناشناس می‌فرستی. هر چی تو دلت هست رو بنویس:", reply_markup=types.ReplyKeyboardRemove())
            save_users()
            return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 **سلام! به چت ناشناس خوش اومدی.**\n\n✨ واسه قدم اول، اسمت چیه؟")
        save_users()
    else:
        name = users[cid].get("name", "عزیز")
        users[cid]["state"] = "main"
        bot.send_message(cid, f"😍 **{name} جان، خوش برگشتی!**", reply_markup=main_kb(cid))

# --- هندل کردن تمام پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'audio', 'video', 'voice', 'sticker', 'video_note', 'animation'])
def handle_all(message):
    cid = str(message.chat.id); load_data()
    user = users.get(cid)
    if not user: return
    text = message.text

    # ارسال همگانی (توسط ادمین)
    if user.get("state") == "broad_wait" and str(cid) == str(ADMIN_ID):
        broadcast_msg[cid] = message.message_id
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله بفرست", callback_data="bc_confirm"), types.InlineKeyboardButton("❌ لغو", callback_data="bc_cancel"))
        bot.send_message(cid, "❓ آیا مطمئنی که این پیام برای تمام کاربران ارسال شود؟", reply_markup=kb)
        return

    # ثبت نام
    if user["state"] == "get_name" and text:
        user["name"] = text[:15]; user["state"] = "get_gender"; save_users()
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("آقا هستم 👦", "خانم هستم 👧")
        bot.send_message(cid, "✅ جنسیتت چیه؟", reply_markup=kb)
        return
    if user["state"] == "get_gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "get_age"; save_users()
        bot.send_message(cid, "🎂 چند سالته؟ (فقط عدد)", reply_markup=types.ReplyKeyboardRemove())
        return
    if user["state"] == "get_age" and text:
        if text.isdigit():
            user["age"] = int(text); user["state"] = "main"; save_users()
            bot.send_message(cid, "🎉 ثبت‌نام تکمیل شد!", reply_markup=main_kb(cid))
        return

    # منوی اصلی
    if user["state"] == "main":
        if text == "🚀 پیدا کردن هم‌صحبت":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("آقا 👦", callback_data="s_male"), types.InlineKeyboardButton("خانم 👧", callback_data="s_female"), types.InlineKeyboardButton("🌈 فرقی نمی‌کنه", callback_data="s_any"))
            bot.send_message(cid, "🛰 **سیگنال‌های یابنده فعال شد!**\n\nدنبال کی می‌گردی؟", reply_markup=kb)
        elif text == "🔗 لینک ناشناس من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_users()
            bot.send_message(cid, f"🎁 **لینک تو:**\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
        elif text == "👤 پروفایل من":
            icon = "👦" if user.get('gender') == 'male' else "👧"
            bot.send_message(cid, f"👤 نام: {user.get('name')}\n🚻 جنسیت: {icon}\n🎂 سن: {user.get('age')}")
        elif text == "📢 ارسال پیام همگانی" and str(cid) == str(ADMIN_ID):
            user["state"] = "broad_wait"
            bot.send_message(cid, "📝 پیام (متن، عکس و...) را بفرست تا تاییدیه ارسال صادر شود:")
        elif text == "ℹ️ راهنما":
            bot.send_message(cid, "📖 راهنما:\n- هم‌صحبت: چت با غریبه\n- لینک ناشناس: دریافت پیام مخفی")

    # چت دو نفره (ارسال تمام فرمت‌ها)
    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله", callback_data="confirm_end"), types.InlineKeyboardButton("❌ خیر", callback_data="main_menu"))
            bot.send_message(cid, "⚠️ مطمئنی می‌خوای قطع کنی؟", reply_markup=kb)
        elif text == "🚩 گزارش تخلف":
            kb = types.InlineKeyboardMarkup(row_width=1).add(types.InlineKeyboardButton("🤬 فحاشی", callback_data="r_insult"), types.InlineKeyboardButton("🔞 محتوای جنسی", callback_data="r_18"), types.InlineKeyboardButton("⚖️ مزاحمت", callback_data="r_spam"))
            bot.send_message(cid, "❓ علت گزارش چیه؟", reply_markup=kb)
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: bot.send_message(cid, "❌ ارسال نشد.")

    # نوشتن پیام ناشناس
    if user["state"] == "anon_write" and text:
        user["anon_pending"] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال", callback_data="bc_send_anon"), types.InlineKeyboardButton("❌ لغو", callback_data="main_menu"))
        bot.send_message(cid, f"📝 ارسال بشه؟\n\n_{text}_", reply_markup=kb, parse_mode="Markdown")

# --- کال‌بک‌ها ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); load_data(); user = users.get(cid)
    if not user: return

    # تایید جوین
    if call.data == "check_membership":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ تایید شد!")
            bot.delete_message(cid, call.message.id)
            start(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)

    # جستجو
    if call.data.startswith("s_"):
        pref = call.data.replace("s_", "")
        user.update({"search_pref": pref, "state": "searching"})
        bot.delete_message(cid, call.message.id)
        search_list = ["male", "female"] if pref == "any" else [pref]
        for g in search_list:
            if waiting[g]:
                pid = waiting[g].pop(0)
                if pid != cid:
                    p = users[pid]
                    user.update({"partner": pid, "state": "chat"})
                    p.update({"partner": cid, "state": "chat"})
                    bot.send_message(cid, "💎 **وصل شدی!**", reply_markup=chat_kb())
                    bot.send_message(pid, "💎 **وصل شدی!**", reply_markup=chat_kb())
                    save_users(); return
        waiting[user.get('gender', 'male')].append(cid)
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ لغو جستجو", callback_data="main_menu"))
        bot.send_message(cid, "🔍 **در حال اسکن کردن کهکشانِ کاربران...**", reply_markup=kb)

    # قطع چت
    if call.data == "confirm_end":
        pid = user.get("partner")
        if pid: 
            users[pid].update({"partner": None, "state": "main"})
            bot.send_message(pid, "⚠️ طرف مقابل چت رو قطع کرد.", reply_markup=main_kb(pid))
        user.update({"partner": None, "state": "main"})
        save_users(); bot.edit_message_text("🔚 مکالمه تمام شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی:", reply_markup=main_kb(cid))

    # گزارش
    if call.data.startswith("r_"):
        bot.send_message(ADMIN_ID, f"🚨 گزارش آیدی `{user.get('partner')}` به علت: {call.data}")
        bot.answer_callback_query(call.id, "✅ گزارش شد.", show_alert=True)

    # ارسال همگانی تایید شده
    if call.data == "bc_confirm":
        mid = broadcast_msg.pop(cid, None)
        count = 0
        for uid in users:
            try: bot.copy_message(uid, cid, mid); count += 1
            except: pass
        user["state"] = "main"; bot.edit_message_text(f"✅ برای {count} نفر ارسال شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 منو:", reply_markup=main_kb(cid))

    if call.data == "bc_cancel":
        user["state"] = "main"; bot.edit_message_text("❌ لغو شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 منو:", reply_markup=main_kb(cid))

    # ارسال پیام ناشناس
    if call.data == "bc_send_anon":
        target = user.get("anon_target")
        msg = user.pop("anon_pending", "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 پاسخ", callback_data=f"rep_{cid}"))
            bot.send_message(target, f"📬 **پیام ناشناس جدید:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "🚀 ارسال شد.", reply_markup=main_kb(cid))
        user["state"] = "main"; save_users()

    if call.data == "main_menu":
        user["state"] = "main"; bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی:", reply_markup=main_kb(cid))

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.infinity_polling()
