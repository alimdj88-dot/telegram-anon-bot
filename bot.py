import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- پایداری سیستم ---
app = Flask('')
@app.route('/')
def home(): return "🎭 The Shadow Club is Open!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- تنظیمات اختصاصی شما ---
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

# --- کیبوردهای سینمایی ---
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

# --- موتور اصلی ربات ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def shadow_engine(message):
    cid = str(message.chat.id)
    users = load_db()
    text = message.text

    # ۱. قفل ورود (عضویت اجباری)
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔱 ورود به محفل", url="https://t.me/ChatNaAnnouncements"))
        kb.add(types.InlineKeyboardButton("🔓 تایید دعوتنامه", callback_data="verify_member"))
        bot.send_message(cid, "🌑 **به دنیای سایه‌ها خوش آمدی...**\n\nبرای عبور از درگاه و شروع گفتگوهای پنهان، ابتدا باید در کانال ما عضو شوی تا هویتت تایید شود.", reply_markup=kb, parse_mode="Markdown")
        return

    # ۲. هندل لینک ناشناس (Deep Link) - اصلاح شده
    if text and text.startswith("/start "):
        code = text.split()[1]
        target_id = next((u for u, d in users.items() if d.get("link") == code), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid].update({"state": "writing_anon", "target": target_id})
            save_db(users)
            bot.send_message(cid, "🤫 **هیسسس! الان در ایستگاه اعترافی.**\n\nطرف مقابل هرگز نمی‌فهمه این حرف از طرف کیه. هر چی تو دلت سنگینی می‌کنه رو اینجا بنویس و بفرست:", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۳. ثبت‌نام با روح و احساس
    if cid not in users or "name" not in users[cid]:
        if text == "/start" or cid not in users:
            users[cid] = {"state": "get_name"}
            save_db(users)
            bot.send_message(cid, "👋 **سلام غریبه دوست‌داشتنی!**\n\nمن اینجام تا راه رو برات باز کنم. اول بگو دوست داری با چه اسمی صدات کنم؟ (یه اسم مستعارِ خفن بفرست)")
            return
        
        state = users[cid].get("state")
        if state == "get_name":
            users[cid].update({"name": text[:20], "state": "get_gender"})
            save_db(users)
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("👦 شوالیه", callback_data="set_male"), types.InlineKeyboardButton("👧 بانو", callback_data="set_female"))
            bot.send_message(cid, f"✅ چه اسم قشنگی، **{text}**!\n\nحالا بگو از کدوم قبیله‌ای؟", reply_markup=kb)
            return
        if state == "get_age":
            if text.isdigit() and 10 < int(text) < 90:
                users[cid].update({"age": text, "state": "main"})
                save_db(users)
                bot.send_message(cid, "🎉 **تبریک! هویت تو ثبت شد.**\nحالا بال‌هات رو باز کن و وارد دنیای ناشناس شو...", reply_markup=main_kb(cid))
            else:
                bot.send_message(cid, "⚠️ ای وای! سن رو باید به عدد بفرستی (مثلاً 20).")
            return
        return

    user = users[cid]
    u_state = user.get("state")

    # منوی اصلی و دکمه‌ها
    if text == "☄️ شکارِ هم‌صحبت":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("👤 شوالیه‌ها", callback_data="find_male"),
               types.InlineKeyboardButton("👸 بانوها", callback_data="find_female"),
               types.InlineKeyboardButton("🌌 تقدیر و شانس (هرکسی)", callback_data="find_any"))
        bot.send_message(cid, "🛰 **رادارها در حال اسکن فرکانس‌ها...**\nدنبال چه جور هم‌صحبتی می‌گردی؟", reply_markup=kb)

    elif text == "🕵️ ایستگاهِ اعتراف":
        link = user.get("link") or str(random.randint(100000, 999999))
        users[cid]["link"] = link; save_db(users)
        bot.send_message(cid, f"🔗 **تله‌ی اعتراف تو آماده‌ست!**\n\nاین لینک رو بزار تو بیو یا استوری تا بقیه بیان و ناشناس بهت اعتراف کنن:\n\n`https://t.me/{bot.get_me().username}?start={link}`", parse_mode="Markdown")

    elif text == "🔮 ویترینِ من":
        icon = "⚔️" if user['gender'] == 'male' else "🌹"
        bot.send_message(cid, f"📜 **کتیبه هویت شما:**\n\n👤 نام: {user['name']}\n🚻 اصالت: {icon}\n🎂 تجربه (سن): {user['age']}\n\n_وضعیت: آماده برای ماجراجویی_")

    elif text == "📜 کتیبه راهنما":
        bot.send_message(cid, "💡 **چطور در دنیای سایه‌ها دوام بیاوریم؟**\n\n۱. با شکار، به یک غریبه رندوم وصل میشی.\n۲. پیام‌های ایستگاه اعتراف کاملاً مخفیه.\n۳. اگه کسی مزاحم شد، از دکمه گزارش استفاده کن.", reply_markup=main_kb(cid))

    elif text == "⚡️ طنینِ مدیریت" and cid == ADMIN_ID:
        users[cid]["state"] = "broad_wait"; save_db(users)
        bot.send_message(cid, "🖋 **پیام مدیریت را بنویس تا در کل محفل طنین‌انداز شود:**")

    # منطق چت و پیام همگانی (در ادامه با متون اصلاح شده...)
    elif u_state == "chat":
        partner = user.get("partner")
        if text == "✂️ قطعِ رشته اتصال":
            users[cid]["state"] = "main"; users[partner]["state"] = "main"
            save_db(users)
            bot.send_message(cid, "🔚 **رشته اتصال پاره شد.** برگشتیم به منوی اصلی.", reply_markup=main_kb(cid))
            bot.send_message(partner, "⚠️ **هم‌صحبت تو رشته اتصال رو قطع کرد...**", reply_markup=main_kb(partner))
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass

    elif u_state == "broad_wait" and cid == ADMIN_ID:
        user["temp_msg"] = message.message_id; user["state"] = "broad_confirm"
        save_db(users)
        bot.send_message(cid, "🧐 **آیا از طنین‌انداز شدن این پیام در کل دنیا مطمئنی؟**", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔥 بله، شلیک کن", callback_data="bc_yes"), types.InlineKeyboardButton("❌ نه، لغو کن", callback_data="main_menu")))

    elif u_state == "writing_anon" and text:
        user["pending"] = text; user["state"] = "anon_confirm"
        save_db(users)
        bot.send_message(cid, f"👀 **آماده‌ای که این اعتراف رو بفرستی؟**\n\n_{text}_", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 آره، بفرست", callback_data="send_anon")), parse_mode="Markdown")

# --- مدیریت کلیک‌ها (Callback) ---
@bot.callback_query_handler(func=lambda c: True)
def callback_handler(call):
    cid = str(call.message.chat.id); users = load_db()

    if call.data == "verify_member":
        if is_member(cid):
            bot.delete_message(cid, call.message.id)
            bot.send_message(cid, "🔓 **دروازه باز شد! خوش آمدی.**", reply_markup=main_kb(cid))
            if cid not in users: users[cid] = {"state": "get_name"}; save_db(users)

    elif call.data in ["set_male", "set_female"]:
        users[cid].update({"gender": "male" if "male" in call.data else "female", "state": "get_age"})
        save_db(users); bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🎂 **خیلی هم عالی!** حالا سن خودت رو بگو تا سفرمون رو شروع کنیم:")

    elif call.data.startswith("find_"):
        pref = call.data.split("_")[1]
        my_gender = users[cid].get("gender")
        # الگوریتم صف انتظار فعال
        target_gender = "female" if pref == "female" else "male" if pref == "male" else "any"
        match = None
        for uid in (waiting_room[target_gender] if target_gender != "any" else waiting_room["male"] + waiting_room["female"]):
            if uid != cid: match = uid; break
        
        if match:
            for g in ["male", "female", "any"]:
                if match in waiting_room[g]: waiting_room[g].remove(match)
            users[cid].update({"state": "chat", "partner": match})
            users[match].update({"state": "chat", "partner": cid})
            save_db(users)
            bot.send_message(cid, "💎 **فرکانس‌ها هماهنگ شد! وصل شدی.**", reply_markup=chat_kb())
            bot.send_message(match, "💎 **فرکانس‌ها هماهنگ شد! وصل شدی.**", reply_markup=chat_kb())
        else:
            waiting_room[my_gender].append(cid)
            bot.edit_message_text("🔍 **در حال جستجوی غریبه‌ای در اعماق سایه‌ها...** صبور باش.", cid, call.message.id)

    elif call.data == "bc_yes":
        mid = users[cid].get("temp_msg")
        for u in users:
            try:
                bot.send_message(u, "📢 **[ اطلاعیه رسمی محفل سایه‌ها ]**\n" + "—"*15)
                bot.copy_message(u, cid, mid)
            except: pass
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✨ پیام با موفقیت در کل دنیا طنین‌انداز شد.", cid, call.message.id)

    elif call.data == "send_anon":
        target = users[cid].get("target"); msg = users[cid].get("pending")
        bot.send_message(target, f"📬 **یک اعترافِ ناشناس از اعماق سایه‌ها رسید:**\n\n_{msg}_", parse_mode="Markdown")
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✅ اعتراف با موفقیت به مقصد رسید.", cid, call.message.id)
        bot.send_message(cid, "🏡 بازگشت به ایستگاه مرکزی", reply_markup=main_kb(cid))

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
