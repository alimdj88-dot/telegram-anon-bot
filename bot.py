import telebot
from telebot import types
import json, os, random
from flask import Flask
from threading import Thread

# --- تنظیمات سرور ---
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is Online & Safe!"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run).start()

# --- تنظیمات اصلی ---
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
ADMIN_ID = "8013245091" # آیدی عددی خودت
BOT_USERNAME = "Chatnashenas_IriBot"
bot = telebot.TeleBot(TOKEN)

# آیدی کانال‌ها (ربات باید در این‌ها ادمین باشد)
CHANNELS = ["@ChatNaAnnouncements"]

USERS_FILE = "users.json"
BLACKLIST_FILE = "blacklist.json"
users = {}
waiting = {"male": [], "female": []}
blacklist = []
anon_pending = {}

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

# --- تابع بررسی عضویت ---
def is_member(user_id):
    if str(user_id) == str(ADMIN_ID): return True # ادمین نیاز به جوین ندارد
    for channel in CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['left', 'kicked']: return False
        except: continue
    return True

# --- کیبوردهای ثابت (بدون تغییر) ---
def main_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🚀 پیدا کردن هم‌صحبت", "🔗 لینک ناشناس من")
    kb.add("👤 پروفایل من", "ℹ️ راهنما")
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
    
    if cid in blacklist:
        bot.send_message(cid, "🚫 **دسترسی شما مسدود شده است.**")
        return

    # دروازه جوین اجباری
    if not is_member(message.chat.id):
        kb = types.InlineKeyboardMarkup(row_width=1)
        for i, ch in enumerate(CHANNELS, 1):
            kb.add(types.InlineKeyboardButton(f"📢 عضویت در کانال {i}", url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("✅ عضو شدم! (تایید)", callback_data="check_membership"))
        
        bot.send_message(cid, "💎 **خوش اومدی!**\n\nواسه استفاده از ربات و حمایت از ما، اول تو کانال‌های زیر عضو شو و بعد دکمه تایید رو بزن:", reply_markup=kb)
        return

    # --- بقیه کدهای قبلی (بدون هیچ تغییری در متن یا عملکرد) ---
    args = message.text.split()
    if len(args) > 1:
        target_id = next((uid for uid, udata in users.items() if udata.get("link") == args[1]), None)
        if target_id and target_id != cid:
            users.setdefault(cid, {"state": "main"})
            users[cid]["state"] = "anon_write"
            users[cid]["anon_target"] = target_id
            bot.send_message(cid, "🤫 **هیسسسس!**\n\nداری یه پیام ناشناس می‌فرستی. هر چی تو دلت هست رو بنویس:", reply_markup=types.ReplyKeyboardRemove())
            return

    if cid not in users or "name" not in users[cid]:
        users[cid] = {"state": "get_name"}
        bot.send_message(cid, "🌟 **سلام! به دنیای بزرگ چت ناشناس خوش اومدی.**\n\n✨ واسه قدم اول، بگو دوست داری چی **صدات کنم؟**")
        save_users()
    else:
        name = users[cid].get("name", "دوست من")
        bot.send_message(cid, f"😍 **{name} جان، خیلی خوش برگشتی!**", reply_markup=main_kb())

# --- مدیریت پیام‌ها و کال‌بک‌ها (بخش‌های اصلی ربات) ---
@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    cid = str(call.message.chat.id); user = users.get(cid)
    if not user: return

    if call.data == "check_membership":
        if is_member(cid):
            bot.answer_callback_query(call.id, "✅ تایید شد!")
            bot.delete_message(cid, call.message.id)
            start(call.message) # هدایت به شروع مجدد بعد از جوین
        else:
            bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)

    # تمام کال‌بک‌های قبلی (s_, report, adm_ban, rep_, confirm_end و ...) در اینجا عیناً تکرار می‌شوند
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
                    bot.send_message(cid, "💎 **ایول! یه هم‌صحبت عالی پیدا کردم.**", reply_markup=chat_kb())
                    bot.send_message(pid, "💎 **ایول! یه هم‌صحبت عالی پیدا کردم.**", reply_markup=chat_kb())
                    found = True; break
        if not found:
            waiting[user['gender']].append(cid)
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ لغو جستجو", callback_data="cancel_search"))
            bot.send_message(cid, "🔍 **در حال اسکن کردن کهکشانِ کاربران...**", reply_markup=kb, parse_mode="Markdown")

    if call.data == "cancel_search":
        for g in waiting:
            if cid in waiting[g]: waiting[g].remove(cid)
        user["state"] = "main"
        bot.edit_message_text("📥 جستجو لغو شد.", cid, call.message.id)
        bot.send_message(cid, "🏡 منوی اصلی:", reply_markup=main_kb())

    if call.data == "report_confirm":
        p_id = user.get("partner")
        if p_id:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚫 بن", callback_data=f"adm_ban_{p_id}"), types.InlineKeyboardButton("✅ رد", callback_data="adm_ignore"))
            bot.send_message(ADMIN_ID, f"🚨 گزارش آیدی: `{p_id}`", reply_markup=kb)
            bot.send_message(cid, "✅ گزارش شد."); bot.send_message(p_id, "⚠️ قطع شد.")
            users[p_id].update({"partner": None, "state": "main"}); user.update({"partner": None, "state": "main"})
            bot.send_message(cid, "🏡 منو", reply_markup=main_kb()); bot.send_message(p_id, "🏡 منو", reply_markup=main_kb())

    if call.data.startswith("adm_ban_"):
        target = call.data.replace("adm_ban_", "")
        blacklist.append(target); save_blacklist()
        bot.edit_message_text(f"✅ {target} بن شد.", cid, call.message.id)

    if call.data == "send_anon_final":
        target = user.get("anon_target")
        msg = anon_pending.pop(cid, "")
        if target:
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📩 پاسخ", callback_data=f"rep_{cid}"))
            bot.send_message(target, f"📬 **پیام ناشناس:**\n\n_{msg}_", reply_markup=kb, parse_mode="Markdown")
            bot.send_message(cid, "✅ ارسال شد.", reply_markup=main_kb())
        user["state"] = "main"

    if call.data.startswith("rep_"):
        user.update({"state": "anon_write", "anon_target": call.data.replace("rep_", "")})
        bot.send_message(cid, "✍️ پاسخت رو بنویس:")

    if call.data == "confirm_end":
        p_id = user.get("partner")
        if p_id: 
            users[p_id].update({"partner": None, "state": "main"})
            bot.send_message(p_id, "⚠️ قطع شد.", reply_markup=main_kb())
        user.update({"partner": None, "state": "main"})
        bot.send_message(cid, "🔚 قطع شد.", reply_markup=main_kb())

@bot.message_handler(content_types=['text', 'photo', 'voice', 'video', 'sticker'])
def handle_all(message):
    cid = str(message.chat.id)
    if cid in blacklist: return
    if not is_member(cid): return # امنیت مضاعف
    user = users.get(cid)
    if not user: return
    text = message.text

    # ثبت‌نام (عیناً قبلی)
    if user["state"] == "get_name" and text:
        user["name"] = text[:15]; user["state"] = "get_gender"
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("آقا 👦", "خانم 👧")
        bot.send_message(cid, "✅ جنسیتت؟", reply_markup=kb); return
    if user["state"] == "get_gender" and text:
        user["gender"] = "male" if "آقا" in text else "female"
        user["state"] = "get_age"
        bot.send_message(cid, "🎂 سن؟"); return
    if user["state"] == "get_age" and text:
        if text.isdigit():
            user["age"] = int(text); user["state"] = "main"
            bot.send_message(cid, "🎉 خوش اومدی!", reply_markup=main_kb()); save_users(); return

    # منوی اصلی و چت (عیناً قبلی)
    if user["state"] == "main":
        if text == "🚀 پیدا کردن هم‌صحبت": start(message) # فراخوانی اینلاین
        elif text == "🔗 لینک ناشناس من":
            code = user.get("link") or str(random.randint(100000, 999999))
            user["link"] = code; save_users()
            bot.send_message(cid, f"🔗 لینک تو:\n`https://t.me/{BOT_USERNAME}?start={code}`", parse_mode="Markdown")
        elif text == "👤 پروفایل من":
            bot.send_message(cid, f"👤 نام: {user['name']}\n🎂 سن: {user['age']}")

    if user["state"] == "chat":
        partner = user.get("partner")
        if text == "🔚 قطع مکالمه":
            kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ بله", callback_data="confirm_end"), types.InlineKeyboardButton("❌ خیر", callback_data="cancel_end"))
            bot.send_message(cid, "⚠️ قطع کنی؟", reply_markup=kb)
        elif partner:
            try:
                if message.content_type == 'text': bot.send_message(partner, f"💬: {text}")
                elif message.content_type == 'photo': bot.send_photo(partner, message.photo[-1].file_id)
            except: pass

    if user["state"] == "anon_write" and text:
        anon_pending[cid] = text
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🚀 ارسال", callback_data="send_anon_final"), types.InlineKeyboardButton("❌ لغو", callback_data="cancel_anon"))
        bot.send_message(cid, f"📝 ارسال بشه؟\n\n_{text}_", reply_markup=kb, parse_mode="Markdown")

if __name__ == "__main__":
    load_data(); keep_alive()
    bot.remove_webhook()
    bot.infinity_polling()
