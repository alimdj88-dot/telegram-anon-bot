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
def status(): return "Shadow Titan v15.0: Full Systems Operational"

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
                "bans": {"blacklist": {}, "temp_bans": {}},
                "queue": {"general": []},
                "messages": {"inbox": {}},
                "reports": {"pending": [], "archive": []},
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
            except:
                return {}

    def write(self, key, data):
        with self.lock:
            with open(self.files[key], "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

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
        logger.info("Bot Engine Started Successfully.")

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
    def get_kb_main(self, uid, is_vip=False):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس روزانه")
        markup.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if str(uid) == self.owner_id:
            markup.add("📊 پنل مدیریت", "📢 ارسال همگانی")
        return markup

    def get_kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def get_kb_admin(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛠 حالت تعمیر و نگهداری", "🎖 گیفت VIP")
        markup.add("❌ حذف VIP", "📋 لیست VIP ها")
        markup.add("🔙 بازگشت به منو")
        return markup

    def get_kb_report_reasons(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("فحاشی", callback_data="report_reason_insult"),
                   types.InlineKeyboardButton("محتوای +18", callback_data="report_reason_nsfw"))
        markup.add(types.InlineKeyboardButton("اسپم", callback_data="report_reason_spam"),
                   types.InlineKeyboardButton("آزار و اذیت", callback_data="report_reason_harass"))
        markup.add(types.InlineKeyboardButton("لغو گزارش", callback_data="report_cancel"))
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
            maintenance = db_c["settings"]["maintenance"]
            
            db_u = self.db.read("users")
            is_vip = db_u["users"].get(uid, {}).get("vip", False)
            is_admin = str(uid) == self.owner_id
            
            if maintenance and not (is_vip or is_admin):
                self.bot.send_message(uid, "🔧 <b>ربات در حال تعمیر و نگهداری است</b>\n\n"
                                          "در حال حاضر فقط کاربران VIP و مدیران می‌توانند از ربات استفاده کنند.\n"
                                          "به زودی برمی‌گردیم! 🌟")
                return
            
            # ادامه کد /start قبلی (لینک ناشناس و ثبت‌نام)
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    self.bot.send_message(uid, "❌ نمی‌توانید به خودتان پیام ناشناس بفرستید.")
                    return
                
                if uid not in db_u["users"]:
                    db_u["users"][uid] = {
                        "state": "STEP_NAME", "name": "نامشخص", "sex": "نامشخص", "age": 0,
                        "warns": 0, "partner": None, "vip": False, "blocks": [], "anon_target": target
                    }
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "👋 برای ارسال پیام ناشناس ابتدا نام مستعار خود را وارد کنید:")
                else:
                    user = db_u["users"][uid]
                    user["state"] = "ANON_SENDING"
                    user["anon_target"] = target
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "✉️ پیام ناشناس خود را بنویسید:")
                return
            
            if uid not in db_u["users"]:
                db_u["users"][uid] = {
                    "state": "STEP_NAME", "name": "نامشخص", "sex": "نامشخص", "age": 0,
                    "warns": 0, "partner": None, "vip": False, "blocks": []
                }
                self.db.write("users", db_u)
                self.bot.send_message(uid, "👋 به ربات چت ناشناس شادو خوش آمدید!\n\nلطفاً <b>نام مستعار</b> خود را بفرستید:")
            else:
                self.bot.send_message(uid, "خوش برگشتی! 🌟", reply_markup=self.get_kb_main(uid, db_u["users"][uid].get("vip", False)))

        @self.bot.message_handler(commands=['send_broadcast'])
        def send_broadcast_cmd(message):
            if str(message.chat.id) != self.owner_id:
                return
            db_c = self.db.read("config")
            text = db_c["broadcast"]["text"]
            if not text:
                self.bot.send_message(message.chat.id, "❌ پیامی برای ارسال ذخیره نشده.")
                return
            
            db_u = self.db.read("users")
            sent = 0
            for uid in db_u["users"]:
                try:
                    self.bot.send_message(uid, text)
                    sent += 1
                except:
                    pass
            self.bot.send_message(message.chat.id, f"✅ پیام همگانی به {sent} کاربر ارسال شد.")
            db_c["broadcast"]["text"] = None
            self.db.write("config", db_c)

        @self.bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def central_logic(message):
            uid = str(message.chat.id)
            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")
            
            # چک بن دائم یا موقت
            if uid in db_b["blacklist"] or (uid in db_b["temp_bans"] and db_b["temp_bans"][uid] > datetime.datetime.now().timestamp()):
                self.bot.send_message(uid, "🚫 حساب شما مسدود است.")
                return
            
            # چک تعمیر
            if db_c["settings"]["maintenance"]:
                is_vip = db_u["users"].get(uid, {}).get("vip", False)
                if not (is_vip or str(uid) == self.owner_id):
                    self.bot.send_message(uid, "🔧 ربات در حال تعمیر و نگهداری است.")
                    return
            
            # چک عضویت کانال
            try:
                if uid != self.owner_id:
                    status = self.bot.get_chat_member(self.channel, uid).status
                    if status not in ['member', 'administrator', 'creator']:
                        self.bot.send_message(uid, f"❌ برای استفاده باید در کانال عضو شوید:\n{self.channel}")
                        return
            except: pass
            
            user = db_u["users"].get(uid)
            if not user: return
            
            # ادامه منطق قبلی (ثبت‌نام، چت، گزارش و غیره)
            # ... (کدهای قبلی برای ثبت‌نام، چت، پیام ناشناس و غیره را اینجا نگه دارید)
            
            if user.get("partner"):
                pid = user["partner"]
                
                if message.text == "🚩 گزارش تخلف":
                    self.bot.send_message(uid, "دلیل گزارش را انتخاب کنید:", reply_markup=self.get_kb_report_reasons())
                    user["pending_report"] = {"target": pid, "last_message_id": message.message_id}
                    self.db.write("users", db_u)
                    return
                
                # ... سایر قسمت‌های چت
                
            self.handle_main_menu(message, uid, user, db_u)

        self.init_callbacks()

    def handle_main_menu(self, message, uid, user, db_u):
        text = message.text
        
        if text == "🛰 شروع چت ناشناس":
            # کد جستجو قبلی
            pass
        
        elif text == "👤 پروفایل من":
            rank = "🎖 VIP" if user.get("vip", False) else "کاربر عادی"
            self.bot.send_message(uid, f"👤 <b>پروفایل شما:</b>\n\n"
                                      f"🏷 نام: {user['name']}\n"
                                      f"⚧ جنسیت: {user['sex']}\n"
                                      f"🔢 سن: {user['age']}\n"
                                      f"🏅 رنک: {rank}\n"
                                      f"⚠️ اخطار: {user['warns']}")
        
        elif text == "🎡 گردونه شانس روزانه":
            today = str(datetime.date.today())
            if user.get("last_spin") == today:
                self.bot.send_message(uid, "❌ امروز قبلاً چرخوندید!")
                return
            if random.random() < 0.05:  # 5%
                user["vip"] = True
                user["last_spin"] = today
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🎉 تبریک! شما رنک VIP گرفتید! 🎖")
            else:
                user["last_spin"] = today
                self.db.write("users", db_u)
                self.bot.send_message(uid, "💨 گردونه چرخید... پوچ! بهتر شانس بعدی 🌟")
        
        elif text == "📊 پنل مدیریت" and str(uid) == self.owner_id:
            self.bot.send_message(uid, "📊 پنل مدیریت:", reply_markup=self.get_kb_admin())
        
        elif text == "🛠 حالت تعمیر و نگهداری" and str(uid) == self.owner_id:
            db_c = self.db.read("config")
            db_c["settings"]["maintenance"] = not db_c["settings"]["maintenance"]
            self.db.write("config", db_c)
            status = "فعال 🟢" if db_c["settings"]["maintenance"] else "غیرفعال 🔴"
            self.bot.send_message(uid, f"حالت تعمیر: {status}")
        
        elif text == "🎖 گیفت VIP" and str(uid) == self.owner_id:
            user["state"] = "ADMIN_GIFT_VIP"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "آیدی عددی کاربر را وارد کنید:")
        
        elif text == "❌ حذف VIP" and str(uid) == self.owner_id:
            user["state"] = "ADMIN_REVOKE_VIP"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "آیدی عددی کاربر را وارد کنید:")
        
        elif text == "📋 لیست VIP ها" and str(uid) == self.owner_id:
            vips = [u for u, data in db_u["users"].items() if data.get("vip")]
            if not vips:
                self.bot.send_message(uid, "هیچ کاربر VIP وجود ندارد.")
            else:
                msg = "🎖 لیست کاربران VIP:\n\n"
                for v in vips[:50]:  # محدود به 50
                    name = db_u["users"][v]["name"]
                    msg += f"{v} - {name}\n"
                self.bot.send_message(uid, msg)

        # هندل حالت‌های ادمین
        if user.get("state") == "ADMIN_GIFT_VIP":
            if message.text.isdigit():
                target = message.text
                if target in db_u["users"]:
                    db_u["users"][target]["vip"] = True
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, f"✅ VIP به {target} گیفت شد.")
                    try: self.bot.send_message(target, "🎉 تبریک! شما رنک VIP دریافت کردید! 🎖")
                    except: pass
                user["state"] = "IDLE"
                self.db.write("users", db_u)
        
        # مشابه برای revoke و غیره

    # ------------------------------------------
    # کال‌بک‌ها (شامل مدیریت گزارش)
    # ------------------------------------------
    def init_callbacks(self):
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            uid = str(call.from_user.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            
            if call.data.startswith("report_reason_"):
                if call.data == "report_cancel":
                    self.bot.answer_callback_query(call.id, "گزارش لغو شد.")
                    return
                reason = {
                    "insult": "فحاشی",
                    "nsfw": "محتوای +18",
                    "spam": "اسپم",
                    "harass": "آزار و اذیت"
                }[call.data.split("_")[2]]
                
                target = user["pending_report"]["target"]
                # ذخیره گزارش موقت و ارسال به ادمین با گزینه‌ها
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Ignore", callback_data=f"admin_ignore_{target}_{uid}"))
                markup.add(types.InlineKeyboardButton("Permanent Ban", callback_data=f"admin_ban_perm_{target}"))
                markup.add(types.InlineKeyboardButton("Temp Ban", callback_data=f"admin_ban_temp_{target}"))
                markup.add(types.InlineKeyboardButton("Warning 1", callback_data=f"admin_warn_1_{target}"))
                markup.add(types.InlineKeyboardButton("Warning 2", callback_data=f"admin_warn_2_{target}"))
                
                msg = f"🚩 گزارش جدید:\nشاکی: {uid}\nمتهم: {target}\nدلیل: {reason}"
                self.bot.send_message(self.owner_id, msg, reply_markup=markup)
                self.bot.answer_callback_query(call.id, "گزارش ارسال شد.")
            
            # هندل گزینه‌های ادمین برای گزارش
            elif call.data.startswith("admin_"):
                # پیاده‌سازی بن، اخطار و غیره

    def run(self):
        print("--- Shadow Titan v15.0 Running ---")
        self.bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_web_server).start()
    bot = ShadowTitanBot()
    bot.run()
