import telebot
from telebot import types
import json
import os
import re
import requests
import datetime
import logging
import random
import threading
from flask import Flask
from threading import Thread

# ==========================================
# 1. سیستم مدیریت لاگ و مانیتورینگ پیشرفته
# ==========================================
logging.basicConfig(
    filename='bot_internal_core.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger("ShadowTitan")

# وب‌سرور برای زنده نگه داشتن ربات
app = Flask('')
@app.route('/')
def status(): return "Shadow Titan v16.0: Full Systems Operational - All Features Fixed"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# ==========================================
# 2. کلاس مدیریت دیتابیس
# ==========================================
class DatabaseManager:
    def __init__(self):
        self.files = {
            "users": "db_users.json",
            "bans": "db_bans.json",
            "queue": "db_queue.json",
            "messages": "db_messages.json",
            "reports": "db_reports.json",
            "config": "db_config.json"
        }
        self.lock = threading.Lock()
        self._init_files()

    def _init_files(self):
        with self.lock:
            defaults = {
                "users": {"users": {}},
                "bans": {"blacklist": {}, "temp_bans": {}},  # temp_bans: {uid: timestamp_end}
                "queue": {"general": []},
                "messages": {"inbox": {}},
                "reports": {"pending": []},
                "config": {
                    "stats": {"chats": 0, "ai_detections": 0},
                    "settings": {"maintenance": False},
                    "broadcast": {"text": None}
                }
            }
            for key, path in self.files.items():
                if not os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(defaults[key], f, indent=4, ensure_ascii=False)

    def read(self, key):
        with self.lock:
            try:
                with open(self.files[key], "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"DB Read Error {key}: {e}")
                return {}

    def write(self, key, data):
        with self.lock:
            try:
                with open(self.files[key], "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"DB Write Error {key}: {e}")

# ==========================================
# 3. هسته اصلی ربات
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        self.token = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
        self.owner_id = "8013245091"
        self.support_username = "@its_alimo"
        self.channel = "@ChatNaAnnouncements"
        self.hf_token = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk"
        
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.db = DatabaseManager()
        
        try:
            self.bot_username = self.bot.get_me().username
        except:
            self.bot_username = "ShadowTitanBot"
        
        self.register_actions()
        logger.info("Bot Engine Started Successfully - v16.0")

    # ------------------------------------------
    # لایه هوش مصنوعی
    # ------------------------------------------
    def ai_toxic_scan(self, text):
        if not text or len(text.strip()) < 2: return 0.0
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        try:
            response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    for item in data[0]:
                        if item['label'] == 'toxic':
                            return item['score']
        except Exception as e:
            logger.error(f"AI Toxic Error: {e}")
        return 0.0

    def ai_nsfw_scan(self, text):
        if not text or len(text.strip()) < 2: return 0.0
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        url = "https://api-inference.huggingface.co/models/michellejieli/nsfw_text_classifier"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        try:
            response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    for item in data[0]:
                        if item['label'] == 'nsfw':
                            return item['score']
        except Exception as e:
            logger.error(f"AI NSFW Error: {e}")
        return 0.0

    # ------------------------------------------
    # کیبوردها
    # ------------------------------------------
    def get_kb_main(self, uid):
        db_u = self.db.read("users")
        is_vip = db_u["users"].get(uid, {}).get("vip", False)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس روزانه")
        markup.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if str(uid) == self.owner_id:
            markup.add("📊 پنل مدیریت")
        return markup

    def get_kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def get_kb_search_cancel(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❌ لغو جستجو")
        return markup

    def get_kb_admin(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛠 حالت تعمیر و نگهداری")
        markup.add("🎖 گیفت VIP", "❌ حذف VIP")
        markup.add("📋 لیست VIP ها", "🔙 بازگشت")
        return markup

    def get_kb_report_reasons(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
                   types.InlineKeyboardButton("محتوای +18", callback_data="rep_nsfw"))
        markup.add(types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
                   types.InlineKeyboardButton("آزار", callback_data="rep_harass"))
        markup.add(types.InlineKeyboardButton("لغو گزارش ❌", callback_data="rep_cancel"))
        return markup

    # ------------------------------------------
    # هندلرها
    # ------------------------------------------
    def register_actions(self):
        @self.bot.message_handler(commands=['start'])
        def welcome(message):
            uid = str(message.chat.id)
            payload = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
            
            db_c = self.db.read("config")
            db_u = self.db.read("users")
            
            is_vip = db_u["users"].get(uid, {}).get("vip", False)
            is_admin = str(uid) == self.owner_id
            
            if db_c["settings"]["maintenance"] and not (is_vip or is_admin):
                self.bot.send_message(uid, "🔧 <b>ربات در حال تعمیر و نگهداری است!</b>\n\n"
                                          "فقط کاربران 🎖 VIP و مدیران می‌توانند استفاده کنند.\n"
                                          "به زودی برمی‌گردیم 🌟\n"
                                          "پشتیبانی: @its_alimo")
                return
            
            # لینک ناشناس
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    self.bot.send_message(uid, "❌ نمی‌توانید به خودتان پیام بفرستید.")
                    return
                if uid not in db_u["users"]:
                    db_u["users"][uid] = {"state": "STEP_NAME", "name": "نامشخص", "sex": "نامشخص", "age": 0,
                                           "warns": 0, "partner": None, "vip": False, "blocks": [], "anon_target": target}
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "برای ارسال پیام ناشناس، ابتدا نام مستعار وارد کنید:")
                else:
                    db_u["users"][uid]["state"] = "ANON_SENDING"
                    db_u["users"][uid]["anon_target"] = target
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "✉️ پیام ناشناس خود را بنویسید (فقط متن):")
                return
            
            # ثبت‌نام
            if uid not in db_u["users"]:
                db_u["users"][uid] = {"state": "STEP_NAME", "name": "نامشخص", "sex": "نامشخص", "age": 0,
                                      "warns": 0, "partner": None, "vip": False, "blocks": [], "last_spin": ""}
                self.db.write("users", db_u)
                self.bot.send_message(uid, "👋 خوش آمدید!\nلطفاً <b>نام مستعار</b> وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
            else:
                self.bot.send_message(uid, "خوش برگشتی 🌟", reply_markup=self.get_kb_main(uid))

        @self.bot.message_handler(commands=['send_broadcast'])
        def broadcast_cmd(message):
            if str(message.chat.id) != self.owner_id: return
            db_c = self.db.read("config")
            text = db_c["broadcast"]["text"]
            if not text:
                self.bot.send_message(message.chat.id, "❌ متنی ذخیره نشده.")
                return
            db_u = self.db.read("users")
            sent = 0
            for u in db_u["users"]:
                try:
                    self.bot.send_message(u, text)
                    sent += 1
                except: pass
            self.bot.send_message(message.chat.id, f"✅ ارسال به {sent} کاربر.")
            db_c["broadcast"]["text"] = None
            self.db.write("config", db_c)

        @self.bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def central_logic(message):
            uid = str(message.chat.id)
            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")
            
            # بن چک
            if uid in db_b["blacklist"]:
                self.bot.send_message(uid, "🚫 بن دائم هستید.")
                return
            if uid in db_b["temp_bans"] and db_b["temp_bans"][uid] > datetime.datetime.now().timestamp():
                self.bot.send_message(uid, "🚫 بن موقت هستید.")
                return
            
            # تعمیر چک
            if db_c["settings"]["maintenance"]:
                is_vip = db_u["users"].get(uid, {}).get("vip", False)
                if not (is_vip or str(uid) == self.owner_id):
                    self.bot.send_message(uid, "🔧 ربات در تعمیر است.")
                    return
            
            # عضویت کانال
            try:
                if uid != self.owner_id:
                    status = self.bot.get_chat_member(self.channel, uid).status
                    if status not in ['member', 'administrator', 'creator']:
                        self.bot.send_message(uid, f"❌ عضو کانال شوید:\n{self.channel}")
                        return
            except: pass
            
            user = db_u["users"].get(uid)
            if not user: return
            
            # ثبت‌نام مراحل
            if user["state"] == "STEP_NAME":
                if self.ai_toxic_scan(message.text) > 0.7 or self.ai_nsfw_scan(message.text) > 0.7:
                    self.bot.send_message(uid, "❌ نام نامناسب.")
                    return
                user["name"] = message.text[:20]
                user["state"] = "STEP_SEX"
                self.db.write("users", db_u)
                self.bot.send_message(uid, f"خوش آمدی {user['name']}!\nجنسیت:", reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("آقا 👦", callback_data="sex_m"),
                    types.InlineKeyboardButton("خانم 👧", callback_data="sex_f")))
                return
            
            if user["state"] == "STEP_AGE":
                if not message.text.isdigit() or not 12 <= int(message.text) <= 99:
                    self.bot.send_message(uid, "❌ سن ۱۲-۹۹")
                    return
                user["age"] = int(message.text)
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ ثبت‌نام کامل!", reply_markup=self.get_kb_main(uid))
                return
            
            # حالت‌های خاص
            if user["state"] == "SET_NAME":
                user["name"] = message.text[:20]
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ نام تغییر کرد.", reply_markup=self.get_kb_main(uid))
                return
            
            if user["state"] == "SET_AGE":
                if message.text.isdigit() and 12 <= int(message.text) <= 99:
                    user["age"] = int(message.text)
                    user["state"] = "IDLE"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "✅ سن تغییر کرد.", reply_markup=self.get_kb_main(uid))
                return
            
            # پیام ناشناس
            if user["state"] == "ANON_SENDING":
                if message.content_type != "text":
                    self.bot.send_message(uid, "❌ فقط متن.")
                    return
                target = user["anon_target"]
                db_m = self.db.read("messages")
                if target not in db_m["inbox"]:
                    db_m["inbox"][target] = []
                db_m["inbox"][target].append({"text": message.text, "from": uid, "seen": False, "time": datetime.datetime.now().strftime("%H:%M %d/%m")})
                self.db.write("messages", db_m)
                self.bot.send_message(uid, "✅ پیام ارسال شد.")
                try:
                    self.bot.send_message(target, "📩 پیام ناشناس جدید! به «پیام‌های ناشناس» بروید.")
                except: pass
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                return
            
            if user["state"] == "ANON_REPLYING":
                target_from = user["anon_reply_from"]
                self.bot.send_message(target_from, f"📩 پاسخ ناشناس:\n{message.text}")
                self.bot.send_message(uid, "✅ پاسخ ارسال شد.")
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                return
            
            # چت فعال
            if user.get("partner"):
                pid = user["partner"]
                
                if message.text == "❌ لغو جستجو":
                    return  # اگر در جستجو بود
                
                if message.text == "🔚 پایان گفتگو":
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("بله", callback_data="end_yes"), types.InlineKeyboardButton("خیر", callback_data="end_no"))
                    self.bot.send_message(uid, "مطمئنید؟", reply_markup=markup)
                    return
                
                if message.text == "🚩 گزارش تخلف":
                    self.bot.send_message(uid, "دلیل گزارش را انتخاب کنید:", reply_markup=self.get_kb_report_reasons())
                    user["report_target"] = pid
                    self.db.write("users", db_u)
                    return
                
                if message.text == "🚫 بلاک و خروج":
                    self.block_user(uid, pid)
                    self.end_chat(uid, pid, "بلاک شد")
                    return
                
                if message.text == "👥 درخواست آیدی":
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("بله ✅", callback_data=f"id_yes_{uid}"),
                               types.InlineKeyboardButton("خیر ❌", callback_data="id_no"))
                    self.bot.send_message(pid, "درخواست آیدی. موافقید؟", reply_markup=markup)
                    self.bot.send_message(uid, "درخواست ارسال شد.")
                    return
                
                # AI چک
                if message.text:
                    toxic = self.ai_toxic_scan(message.text)
                    nsfw = self.ai_nsfw_scan(message.text)
                    if toxic > 0.85 or nsfw > 0.85:
                        try: self.bot.delete_message(uid, message.message_id)
                        except: pass
                        user["warns"] += 1
                        self.db.write("users", db_u)
                        if user["warns"] >= 3:
                            self.ban_user(uid, reason="AI Violation")
                            self.end_chat(uid, pid, "بن شد")
                            return
                        self.bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3")
                        return
                
                try:
                    self.bot.copy_message(pid, uid, message.message_id)
                except: pass
                return
            
            # لغو جستجو
            if message.text == "❌ لغو جستجو":
                db_q = self.db.read("queue")
                if uid in db_q["general"]:
                    db_q["general"].remove(uid)
                    self.db.write("queue", db_q)
                self.bot.send_message(uid, "جستجو لغو شد.", reply_markup=self.get_kb_main(uid))
                return
            
            # منو اصلی
            self.handle_main_menu(message, uid, user, db_u, db_c)

        self.init_callbacks()

    def handle_main_menu(self, message, uid, user, db_u, db_c):
        text = message.text
        
        if text == "🛰 شروع چت ناشناس":
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(types.InlineKeyboardButton("آقا", callback_data="find_m"),
                       types.InlineKeyboardButton("خانم", callback_data="find_f"),
                       types.InlineKeyboardButton("هرکی", callback_data="find_any"))
            self.bot.send_message(uid, "جستجو برای:", reply_markup=markup)
        
        elif text == "👤 پروفایل من":
            rank = "🎖 VIP" if user.get("vip", False) else "عادی"
            self.bot.send_message(uid, f"👤 پروفایل:\n\nنام: {user['name']}\nجنسیت: {user['sex']}\nسن: {user['age']}\nرنک: {rank}\nاخطار: {user['warns']}")
        
        elif text == "📩 لینک ناشناس من":
            link = f"https://t.me/{self.bot_username}?start=msg_{uid}"
            self.bot.send_message(uid, f"لینک ناشناس:\n{link}")
        
        elif text == "📥 پیام‌های ناشناس":
            db_m = self.db.read("messages")
            inbox = db_m["inbox"].get(uid, [])
            if not inbox:
                self.bot.send_message(uid, "هیچ پیامی ندارید.")
                return
            markup = types.InlineKeyboardMarkup()
            msg_text = "<b>پیام‌های ناشناس:</b>\n\n"
            for i, m in enumerate(inbox):
                msg_text += f"{i+1}. {m['text']}\n<i>{m['time']}</i>\n\n"
                markup.add(types.InlineKeyboardButton(f"پاسخ {i+1}", callback_data=f"reply_{i}"))
            self.bot.send_message(uid, msg_text, reply_markup=markup)
            # دیده شدن
            updated = False
            for m in inbox:
                if not m["seen"]:
                    m["seen"] = True
                    updated = True
                    try:
                        self.bot.send_message(m["from"], "✅ پیام دیده شد.")
                    except: pass
            if updated:
                self.db.write("messages", db_m)
        
        elif text == "🎡 گردونه شانس روزانه":
            today = str(datetime.date.today())
            if user.get("last_spin") == today:
                self.bot.send_message(uid, "امروز چرخاندید!")
                return
            user["last_spin"] = today
            if random.random() < 0.05:
                user["vip"] = True
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🎉 تبریک! VIP شدید! 🎖")
            else:
                self.bot.send_message(uid, "پوچ! دفعه بعد 🌟")
            self.db.write("users", db_u)
        
        elif text == "❓ راهنما و قوانین":
            self.bot.send_message(uid, "راهنما:\n- چت ناشناس\n- قوانین: بدون فحش و +18\n- گزارش = اخطار → بن\nپشتیبانی: @its_alimo")
        
        elif text == "⚙ تنظیمات":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت", "🔙 منو")
            self.bot.send_message(uid, "تنظیمات:", reply_markup=markup)
        
        elif text in ["✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت"]:
            if text == "✏️ تغییر نام":
                user["state"] = "SET_NAME"
                self.bot.send_message(uid, "نام جدید:")
            elif text == "🔢 تغییر سن":
                user["state"] = "SET_AGE"
                self.bot.send_message(uid, "سن جدید:")
            elif text == "⚧ تغییر جنسیت":
                self.bot.send_message(uid, "جنسیت:", reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("آقا", callback_data="sex_m"),
                    types.InlineKeyboardButton("خانم", callback_data="sex_f")))
            self.db.write("users", db_u)
        
        elif text == "🔙 منو" or text == "🔙 بازگشت":
            self.bot.send_message(uid, "منو اصلی", reply_markup=self.get_kb_main(uid))
        
        # ادمین
        if str(uid) == self.owner_id:
            if text == "📊 پنل مدیریت":
                self.bot.send_message(uid, "پنل ادمین:", reply_markup=self.get_kb_admin())
            
            elif text == "🛠 حالت تعمیر و نگهداری":
                db_c["settings"]["maintenance"] = not db_c["settings"]["maintenance"]
                self.db.write("config", db_c)
                status = "فعال" if db_c["settings"]["maintenance"] else "غیرفعال"
                self.bot.send_message(uid, f"تعمیر: {status}")
            
            elif text == "🎖 گیفت VIP":
                user["state"] = "GIFT_VIP"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "آیدی عددی برای گیفت VIP:")
            
            elif text == "❌ حذف VIP":
                user["state"] = "REMOVE_VIP"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "آیدی عددی برای حذف VIP:")
            
            elif text == "📋 لیست VIP ها":
                vips = [u for u, d in db_u["users"].items() if d.get("vip")]
                msg = "VIP ها:\n" + "\n".join(vips[:50]) if vips else "هیچکس"
                self.bot.send_message(uid, msg)
            
            # حالت‌های گیفت/حذف
            if user.get("state") == "GIFT_VIP" and message.text.isdigit():
                target = message.text
                if target in db_u["users"]:
                    db_u["users"][target]["vip"] = True
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "گیفت شد.")
                    try: self.bot.send_message(target, "VIP شدید!")
                    except: pass
                user["state"] = "IDLE"
                self.db.write("users", db_u)
            
            if user.get("state") == "REMOVE_VIP" and message.text.isdigit():
                target = message.text
                if target in db_u["users"]:
                    db_u["users"][target]["vip"] = False
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "حذف شد.")
                user["state"] = "IDLE"
                self.db.write("users", db_u)
            
            if text == "📢 ارسال همگانی":
                user["state"] = "BROADCAST"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "متن همگانی را بفرستید:")
            
            if user.get("state") == "BROADCAST":
                db_c["broadcast"]["text"] = message.text
                self.db.write("config", db_c)
                self.bot.send_message(uid, "ذخیره شد. با /send_broadcast ارسال کنید.")
                user["state"] = "IDLE"
                self.db.write("users", db_u)

    # ------------------------------------------
    # کال‌بک‌ها
    # ------------------------------------------
    def init_callbacks(self):
        @self.bot.callback_query_handler(func=lambda call: True)
        def callbacks(call):
            uid = str(call.from_user.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            if not user: return
            
            if call.data.startswith("sex_"):
                user["sex"] = "آقا" if call.data == "sex_m" else "خانم"
                if user["state"] in ["STEP_SEX", ""]:
                    user["state"] = "STEP_AGE"
                    self.bot.send_message(uid, "سن وارد کنید:")
                self.db.write("users", db_u)
            
            elif call.data.startswith("find_"):
                pref = call.data[5:]
                self.bot.edit_message_text("در حال جستجو... (لغو با دکمه زیر)", call.message.chat.id, call.message.message_id)
                self.bot.send_message(uid, "برای لغو جستجو دکمه زیر را بزنید:", reply_markup=self.get_kb_search_cancel())
                
                db_q = self.db.read("queue")
                if uid not in db_q["general"]:
                    db_q["general"].append(uid)
                self.db.write("queue", db_q)
                
                pots = [p for p in db_q["general"] if p != uid]
                pots = [p for p in pots if uid not in db_u["users"][p].get("blocks", []) and p not in user.get("blocks", [])]
                
                if pots:
                    partner = random.choice(pots)
                    db_q["general"].remove(uid)
                    db_q["general"].remove(partner)
                    self.db.write("queue", db_q)
                    
                    user["partner"] = partner
                    db_u["users"][partner]["partner"] = uid
                    self.db.write("users", db_u)
                    
                    self.bot.send_message(uid, "متصل شدید!", reply_markup=self.get_kb_chatting())
                    self.bot.send_message(partner, "متصل شدید!", reply_markup=self.get_kb_chatting())
                # اگر نه، در صف می‌ماند
            
            elif call.data == "end_yes":
                pid = user["partner"]
                self.end_chat(uid, pid, "ترک کرد")
            
            elif call.data.startswith("id_yes_"):
                target = call.data[7:]
                username = call.from_user.username or "ندارد"
                self.bot.send_message(target, f"آیدی: @{username}")
            
            elif call.data.startswith("reply_"):
                i = int(call.data[6:])
                db_m = self.db.read("messages")
                msg = db_m["inbox"][uid][i]
                user["state"] = "ANON_REPLYING"
                user["anon_reply_from"] = msg["from"]
                self.db.write("users", db_u)
                self.bot.send_message(uid, "پاسخ بنویسید:")
            
            # گزارش
            elif call.data.startswith("rep_"):
                if call.data == "rep_cancel":
                    self.bot.answer_callback_query(call.id, "لغو شد")
                    return
                reasons = {"rep_insult": "فحاشی", "rep_nsfw": "+18", "rep_spam": "اسپم", "rep_harass": "آزار"}
                reason = reasons[call.data]
                target = user["report_target"]
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                markup.add(types.InlineKeyboardButton("Ignore", callback_data=f"adm_ignore_{target}_{uid}"),
                           types.InlineKeyboardButton("Permanent Ban", callback_data=f"adm_ban_perm_{target}"))
                markup.add(types.InlineKeyboardButton("Temp Ban", callback_data=f"adm_ban_temp_{target}"),
                           types.InlineKeyboardButton("Warning 1", callback_data=f"adm_warn1_{target}"),
                           types.InlineKeyboardButton("Warning 2", callback_data=f"adm_warn2_{target}"))
                
                report_msg = f"🚩 گزارش:\nشاکی: {uid}\nمتهم: {target}\nدلیل: {reason}"
                sent = self.bot.send_message(self.owner_id, report_msg, reply_markup=markup)
                # ذخیره report id برای temp ban
                db_r = self.db.read("reports")
                db_r["pending"].append({"msg_id": sent.message_id, "target": target})
                self.db.write("reports", db_r)
                
                self.bot.answer_callback_query(call.id, "گزارش ارسال شد")
            
            # ادمین گزارش
            elif call.data.startswith("adm_"):
                if uid != self.owner_id: return
                parts = call.data.split("_")
                action = parts[1]
                target = parts[2]
                
                if action == "ignore":
                    self.bot.edit_message_text("گزارش ignore شد", self.owner_id, call.message.message_id)
                
                elif action == "ban" and parts[2] == "perm":
                    self.ban_user(target, "دائم")
                    self.bot.edit_message_text("بن دائم اعمال شد", self.owner_id, call.message.message_id)
                
                elif action == "ban" and parts[2] == "temp":
                    self.bot.send_message(self.owner_id, "دقیقه بن موقت را وارد کنید:")
                    # ذخیره برای هندل بعدی
                    user["state"] = f"TEMP_BAN_{target}_{call.message.message_id}"
                    self.db.write("users", db_u)
                
                elif action.startswith("warn"):
                    warns = 1 if action == "warn1" else 2
                    if target in db_u["users"]:
                        db_u["users"][target]["warns"] += warns
                        self.db.write("users", db_u)
                        try: self.bot.send_message(target, f"اخطار {warns} دریافت کردید")
                        except: pass
                    self.bot.edit_message_text(f"{warns} اخطار اعمال شد", self.owner_id, call.message.message_id)

    def ban_user(self, uid, reason=""):
        db_b = self.db.read("bans")
        db_b["blacklist"][uid] = reason
        self.db.write("bans", db_b)
        try: self.bot.send_message(uid, "🚫 بن شدید.")
        except: pass

    def end_chat(self, uid, pid, msg):
        db_u = self.db.read("users")
        db_u["users"][uid]["partner"] = None
        db_u["users"][pid]["partner"] = None
        self.db.write("users", db_u)
        self.bot.send_message(uid, "چت پایان یافت.", reply_markup=self.get_kb_main(uid))
        self.bot.send_message(pid, f"هم‌صحبت {msg}.", reply_markup=self.get_kb_main(pid))

    def block_user(self, uid, target):
        db_u = self.db.read("users")
        if target not in db_u["users"][uid]["blocks"]:
            db_u["users"][uid]["blocks"].append(target)
        self.db.write("users", db_u)

    def run(self):
        print("Shadow Titan v16.0 - All Bugs Fixed")
        self.bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_web_server).start()
    bot = ShadowTitanBot()
    bot.run()
