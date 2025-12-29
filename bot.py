import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- پایداری سرور ---
app = Flask('')
@app.route('/')
def home(): return "🎭 Shadow Club is Fully Operational!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- اطلاعات اختصاصی (تایید شده) ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" 
CHANNEL_ID = "@ChatNaAnnouncements"
bot = telebot.TeleBot(TOKEN)

USERS_FILE = "users.json"
# لیست انتظار واقعی (In-Memory برای سرعت)
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

# --- طراحی کیبوردهای مدرن ---
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

# --- هندلر اصلی پیام‌ها ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
def master_engine(message):
    cid = str(message.chat.id)
    users = load_db()
    text = message.text

    # ۱. بررسی عضویت اجباری
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔱 ورود به محفل", url="https://t.me/ChatNaAnnouncements"))
        kb.add(types.InlineKeyboardButton("🔓 تایید دعوتنامه", callback_data="verify_member"))
        bot.send_message(cid, "🌑 **ایست! قبل از ورود به محفل باید هویتت تایید بشه.**\n\nلطفاً در کانال ما عضو شو و بعد روی دکمه زیر بزن:", reply_markup=kb, parse_mode="Markdown")
        return

    # ۲. تشخیص لینک ناشناس (Deep Link) - در اولویت مطلق
    if text and text.startswith("/start "):
        code = text.split()[1]
        target_id = next((u for u, d in users.items() if d.get("link") == code), None)
        if target_id and target_id != cid:
            users[cid] = users.get(cid, {"state": "main"})
            users[cid].update({"state": "writing_anon", "target": target_id})
            save_db(users)
            bot.send_message(cid, "🤫 **به ایستگاه اعتراف خوش اومدی!**\n\nحرفت رو بنویس تا مثل یک رازِ ابدی، ناشناس به گوشش برسونم:", reply_markup=types.ReplyKeyboardRemove())
            return

    # ۳. منطق ثبت‌نام (بدون قفل شدن در مرحله سن)
    if cid not in users or "name" not in users[cid] or users[cid].get("state") in ["get_name", "get_gender", "get_age"]:
        if cid not in users: users[cid] = {"state": "get_name"}
        state = users[cid].get("state")

        if text == "/start" and state == "get_name":
            bot.send_message(cid, "👋 **سلام مسافرِ شب!**\n\nبرای اینکه وارد محفل ما بشی، اول بگو دوست داری با چه اسمی بشناسمت؟")
            return

        if state == "get_name" and text:
            users[cid].update({"name": text[:20], "state": "get_gender"})
            save_db(users)
            kb = types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("👦 شوالیه", callback_data="set_male"),
                types.InlineKeyboardButton("👧 بانو", callback_data="set_female")
            )
            bot.send_message(cid, f"✅ عالیه **{text}** جان! حالا بگو از کدوم قبیله‌ای؟", reply_markup=kb)
            return

        if state == "get_age" and text:
            if text.isdigit() and 10 < int(text) < 90:
                users[cid].update({"age": text, "state": "main"})
                save_db(users)
                bot.send_message(cid, "🎉 **خوش اومدی! شناسنامه‌ت صادر شد.**\n\nحالا آماده‌ای که در محفلِ سایه‌ها گشت بزنی. از دکمه‌های زیر استفاده کن:", reply_markup=main_kb(cid))
            else:
                bot.send_message(cid, "⚠️ **ای وای!** سن رو باید به عدد انگلیسی یا فارسی بفرستی (مثلاً 20).")
            return
        
        if state == "get_gender":
            bot.send_message(cid, "⚠️ لطفاً یکی از گزینه‌های بالا رو برای تعیین اصالتت انتخاب کن!")
            return

    # ۴. عملیات کاربران تایید شده
    user = users[cid]
    u_state = user.get("state")

    # --- مدیریت چت زنده ---
    if u_state == "chat":
        partner = user.get("partner")
        if text == "✂️ قطعِ رشته اتصال":
            users[cid]["state"] = "main"; users[partner]["state"] = "main"
            save_db(users)
            bot.send_message(cid, "🔚 **رشته اتصال پاره شد.** برگشتیم به ایستگاه مرکزی.", reply_markup=main_kb(cid))
            bot.send_message(partner, "⚠️ **هم‌صحبت تو رشته اتصال رو قطع کرد...**", reply_markup=main_kb(partner))
        elif partner:
            try: bot.copy_message(partner, cid, message.message_id)
            except: pass
        return

    # --- مدیریت پیام همگانی ادمین ---
    if u_state == "broad_wait" and cid == ADMIN_ID:
        user["temp_msg"] = message.message_id; user["state"] = "broad_confirm"
        save_db(users)
        bot.send_message(cid, "🧐 **از طنین‌انداز شدن این پیام در کل محفل مطمئنی؟**", reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔥 بله، شلیک کن", callback_data="bc_yes"),
            types.InlineKeyboardButton("❌ نه، لغو کن", callback_data="main_menu")
        ))
        return

    # --- مدیریت ارسال ناشناس ---
    if u_state == "writing_anon" and text:
        user["pending"] = text; user["state"] = "anon_confirm"
        save_db(users)
        bot.send_message(cid, f"👀 **آماده‌ای این اعتراف رو بفرستی؟**\n\n_{text}_", reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🚀 آره، بفرست بره", callback_data="send_anon"),
            types.InlineKeyboardButton("❌ پشیمون شدم", callback_data="main_menu")
        ), parse_mode="Markdown")
        return

    # --- دکمه‌های منوی اصلی ---
    if text == "☄️ شکارِ هم‌صحبت":
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("👤 شوالیه‌ها", callback_data="find_male"),
               types.InlineKeyboardButton("👸 بانوها", callback_data="find_female"),
               types.InlineKeyboardButton("🌌 هرکسی (تقدیر)", callback_data="find_any"))
        bot.send_message(cid, "🛰 **در حال جستجوی فرکانس‌ها...**\nدنبال چه هم‌صحبتی می‌گردی؟", reply_markup=kb)

    elif text == "🕵️ ایستگاهِ اعتراف":
        link = user.get("link") or str(random.randint(100000, 999999))
        users[cid]["link"] = link; save_db(users)
        bot.send_message(cid, f"🔗 **لینک اعتراف تو ساخته شد!**\n\nاین لینک رو پخش کن تا بقیه بیان و ناشناس بهت اعتراف کنن:\n\n`https://t.me/{bot.get_me().username}?start={link}`", parse_mode="Markdown")

    elif text == "🔮 ویترینِ من":
        icon = "⚔️" if user.get('gender') == 'male' else "🌹"
        bot.send_message(cid, f"📜 **کتیبه هویت شما:**\n\n👤 نام: {user['name']}\n🚻 اصالت: {icon}\n🎂 تجربه (سن): {user['age']}\n\n_وضعیت: آنلاین_")

    elif text == "📜 کتیبه راهنما":
        bot.send_message(cid, "📖 **قوانین محفل سایه‌ها:**\n\n۱. احترام به هم‌صحبت الزامیه.\n۲. پیام‌های ناشناس کاملاً مخفی می‌مونن.\n۳. با دکمه شکار، غریبه‌ها رو پیدا کن.", reply_markup=main_kb(cid))

    elif text == "⚡️ طنینِ مدیریت" and cid == ADMIN_ID:
        users[cid]["state"] = "broad_wait"; save_db(users)
        bot.send_message(cid, "🖋 **پیام مدیریت را بنویس:**")

# --- مدیریت کلیک‌های دکمه شیشه‌ای (Callbacks) ---
@bot.callback_query_handler(func=lambda c: True)
def callback_logic(call):
    cid = str(call.message.chat.id); users = load_db()

    if call.data == "verify_member":
        if is_member(cid):
            bot.delete_message(cid, call.message.id)
            bot.send_message(cid, "🔓 **دروازه باز شد! خوش آمدی.**", reply_markup=main_kb(cid))
            if cid not in users: users[cid] = {"state": "get_name"}; save_db(users)
        else: bot.answer_callback_query(call.id, "❌ هنوز در کانال عضو نشدی!", show_alert=True)

    elif call.data in ["set_male", "set_female"]:
        users[cid].update({"gender": "male" if "male" in call.data else "female", "state": "get_age"})
        save_db(users); bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🎂 **خیلی هم عالی!** حالا سن خودت رو به عدد بفرست:")

    elif call.data.startswith("find_"):
        pref = call.data.split("_")[1]
        my_gender = users[cid].get("gender")
        bot.edit_message_text("🔍 **در حال جستجوی غریبه‌ای در اعماق محفل...**", cid, call.message.id)
        
        # الگوریتم جفت‌سازی واقعی
        target_list = waiting_room["any"] if pref == "any" else waiting_room[pref]
        match = next((uid for uid in target_list if uid != cid), None)
        
        if match:
            for g in ["male", "female", "any"]:
                if match in waiting_room[g]: waiting_room[g].remove(match)
            users[cid].update({"state": "chat", "partner": match})
            users[match].update({"state": "chat", "partner": cid})
            save_db(users)
            bot.send_message(cid, "💎 **فرکانس‌ها هماهنگ شد! به هم وصل شدید.**", reply_markup=chat_kb())
            bot.send_message(match, "💎 **فرکانس‌ها هماهنگ شد! به هم وصل شدید.**", reply_markup=chat_kb())
        else:
            waiting_room[my_gender if pref != "any" else "any"].append(cid)

    elif call.data == "bc_yes":
        mid = users[cid].get("temp_msg")
        for u in users:
            try:
                bot.send_message(u, "📢 **[ اطلاعیه رسمی مدیریت محفل ]**\n" + "—"*15)
                bot.copy_message(u, cid, mid)
            except: pass
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✨ طنین با موفقیت ارسال شد.", cid, call.message.id)

    elif call.data == "send_anon":
        target = users[cid].get("target"); msg = users[cid].get("pending")
        bot.send_message(target, f"📬 **یک اعترافِ ناشناس برای تو رسید:**\n\n_{msg}_", parse_mode="Markdown")
        users[cid]["state"] = "main"; save_db(users)
        bot.edit_message_text("✅ اعتراف با موفقیت به مقصد رسید.", cid, call.message.id)
        bot.send_message(cid, "🏡 بازگشت به ایستگاه مرکزی", reply_markup=main_kb(cid))

    elif call.data == "main_menu":
        users[cid]["state"] = "main"; save_db(users)
        bot.delete_message(cid, call.message.id)
        bot.send_message(cid, "🏡 **ایستگاه مرکزی**", reply_markup=main_kb(cid))

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
