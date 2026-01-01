import telebot
from telebot import types
import json
import os
import re
import requests
import datetime
import time
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

# وب‌سرور برای زنده نگه داشتن ربات در سرورهای رایگان
app = Flask('')
@app.route('/')
def status(): return "Shadow Titan v13.1: Full Systems Operational"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# ==========================================
# 2. کلاس مدیریت دیتابیس و داده‌های حجیم
# ==========================================
class DatabaseManager:
    def __init__(self):
        self.files = {
            "users": "db_users.json",
            "bans": "db_bans.json",
            "blocks": "db_blocks.json",  # جدید: بلاک لیست کاربران
            "queue": "db_queue.json",
            "reports": "db_reports.json",
            "config": "db_config.json"
        }
        self.lock = threading.Lock()
        self._init_files()

    def _init_files(self):
        with self.lock:
            defaults = {
                "users": {"users": {}},
                "bans": {"blacklist": {}},
                "blocks": {"blocks": {}},  # هر کاربر: لیست uidهایی که بلاک کرده
                "queue": {"male": [], "female": [], "any": []},
                "reports": {"archive": []},
                "config": {"stats": {"chats": 0, "ai_detections": 0, "users": 0}, "settings": {"maintenance": False}}
            }
            for key, path in self.files.items():
                if not os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(defaults[key], f, indent=4)

    def read(self, key):
        with self.lock:
            try:
                with open(self.files[key], "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return defaults.get(key, {})  # بازگشت به پیش‌فرض اگر خطا

    def write(self, key, data):
        with self.lock:
            with open(self.files[key], "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 3. هسته اصلی ربات (Shadow Sovereign Engine)
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        # تنظیمات پایه
        self.token = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
        self.owner = "8013245091"
        self.channel = "@ChatNaAnnouncements"
        self.hf_token = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk"
        
        # راه‌اندازی ملزومات
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.db = DatabaseManager()
        self.anti_spam = {}
        
        # ثبت تمام رویدادها
        self.register_actions()
        logger.info("Bot Engine Started Successfully.")

    # ------------------------------------------
    # لایه تحلیل محتوا (AI & Security)
    # ------------------------------------------
    def ai_toxic_scan(self, text):
        """تحلیل عمیق متن توسط مدل هوش مصنوعی Toxic-BERT برای محتوای سمی"""
        if not text or len(text.strip()) < 2: return 0.0
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        try:
            response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                if isinstance(res_data, list) and res_data[0]:
                    for label in res_data[0]:
                        if label['label'] == 'toxic': return label['score']
        except Exception as e:
            logger.error(f"AI Toxic Connection Error: {e}")
        return 0.0

    def ai_nsfw_scan(self, text):
        """تشخیص محتوای +18 (NSFW) با مدل NSFW Text Classifier"""
        if not text or len(text.strip()) < 2: return 0.0
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        url = "https://api-inference.huggingface.co/models/michellejieli/nsfw_text_classifier"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        try:
            response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                if isinstance(res_data, list) and res_data[0]:
                    for label in res_data[0]:
                        if label['label'] == 'nsfw': return label['score']
        except Exception as e:
            logger.error(f"AI NSFW Connection Error: {e}")
        return 0.0

    # ------------------------------------------
    # سیستم‌های کیبورد (UI/UX Layer)
    # ------------------------------------------
    def get_kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("🎡 گردونه شانس روزانه", "🏆 برترین‌ها")
        markup.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if str(uid) == self.owner:
            markup.add("📊 پنل مدیریت مرکزی", "📢 ارسال همگانی")
        return markup

    def get_kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def get_kb_gender(self):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("آقا 👦", callback_data="reg_sex_m"),
                   types.InlineKeyboardButton("خانم 👧", callback_data="reg_sex_f"))
        return markup

    def get_kb_settings(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✏️ تغییر نام", "🔢 تغییر سن")
        markup.add("⚧ تغییر جنسیت", "🔙 بازگشت به منو")
        return markup

    def get_kb_admin(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📈 آمار کاربران", "🚫 بلاک کاربر")
        markup.add("✅ آنبلاک کاربر", "🛠 نگهداری سیستم")
        markup.add("🔙 بازگشت به منو")
        return markup

    # ------------------------------------------
    # لایه پردازش پیام‌ها و وضعیت‌ها
    # ------------------------------------------
    def register_actions(self):
        
        @self.bot.message_handler(commands=['start'])
        def welcome(message):
            uid = str(message.chat.id)
            db_u = self.db.read("users")
            
            if uid not in db_u["users"]:
                db_u["users"][uid] = {
                    "state": "STEP_NAME", "name": "نامشخص", "sex": "نامشخص",
                    "age": 0, "warns": 0, "ban_count": 0, "partner": None,
                    "score": 10, "last_spin": "", "level": 1, "blocks": []  # لیست بلاک‌های کاربر
                }
                self.db.write("users", db_u)
                self.bot.send_message(uid, "👋 <b>به ربات بزرگ چت ناشناس شادو خوش آمدید!</b>\n\nبرای شروع، لطفاً <b>نام مستعار</b> خود را بفرستید:", reply_markup=types.ReplyKeyboardRemove())
            else:
                self.bot.send_message(uid, "شما عضو هستید. از منوی زیر استفاده کنید:", reply_markup=self.get_kb_main(uid))

        @self.bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def central_logic(message):
            uid = str(message.chat.id)
            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            
            # 1. فیلتر مسدودیت
            if uid in db_b["blacklist"]:
                self.bot.send_message(uid, "🚫 حساب شما مسدود است."); return
            
            # 2. فیلتر عضویت
            try:
                if str(uid) != self.owner:
                    s = self.bot.get_chat_member(self.channel, uid).status
                    if s not in ['member', 'administrator', 'creator']:
                        self.bot.send_message(uid, f"❌ عضویت در کانال الزامی است:\n{self.channel}"); return
            except: pass

            # 3. مدیریت وضعیت‌های ثبت‌نام و تنظیمات
            user = db_u["users"].get(uid)
            if not user: return

            if user["state"] == "STEP_NAME":
                if message.text and (self.ai_toxic_scan(message.text) > 0.7 or self.ai_nsfw_scan(message.text) > 0.7):
                    self.bot.send_message(uid, "❌ نام نامناسب رد شد. نام دیگری بفرستید:"); return
                user["name"] = message.text[:20]; user["state"] = "STEP_SEX"
                self.db.write("users", db_u)
                self.bot.send_message(uid, f"خوش آمدی <b>{user['name']}</b>. جنسیت خودت رو انتخاب کن:", reply_markup=self.get_kb_gender()); return

            if user["state"] == "STEP_SEX":
                # فقط کال‌بک مدیریت می‌کند
                return

            if user["state"] == "STEP_AGE":
                if not message.text.isdigit() or not (12 <= int(message.text) <= 99):
                    self.bot.send_message(uid, "❌ سن باید عددی بین ۱۲ تا ۹۹ باشد:"); return
                user["age"] = int(message.text); user["state"] = "IDLE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ پروفایل شما با موفقیت تایید شد!", reply_markup=self.get_kb_main(uid)); return

            if user["state"] == "SET_NAME":
                if message.text and (self.ai_toxic_scan(message.text) > 0.7 or self.ai_nsfw_scan(message.text) > 0.7):
                    self.bot.send_message(uid, "❌ نام نامناسب رد شد. نام دیگری بفرستید:"); return
                user["name"] = message.text[:20]; user["state"] = "IDLE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ نام تغییر یافت.", reply_markup=self.get_kb_main(uid)); return

            if user["state"] == "SET_AGE":
                if not message.text.isdigit() or not (12 <= int(message.text) <= 99):
                    self.bot.send_message(uid, "❌ سن باید عددی بین ۱۲ تا ۹۹ باشد:"); return
                user["age"] = int(message.text); user["state"] = "IDLE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ سن تغییر یافت.", reply_markup=self.get_kb_main(uid)); return

            if user["state"] == "ADMIN_BAN":
                if not message.text.isdigit(): 
                    self.bot.send_message(uid, "❌ آیدی عددی وارد کنید:"); return
                target = message.text
                db_b["blacklist"][target] = {"reason": "Admin Ban", "date": str(datetime.datetime.now())}
                self.db.write("bans", db_b)
                self.bot.send_message(uid, f"✅ کاربر {target} بلاک شد.")
                user["state"] = "IDLE"; self.db.write("users", db_u)
                try: self.bot.send_message(target, "🚫 شما توسط ادمین بلاک شدید.")
                except: pass
                return

            if user["state"] == "ADMIN_UNBAN":
                if not message.text.isdigit(): 
                    self.bot.send_message(uid, "❌ آیدی عددی وارد کنید:"); return
                target = message.text
                if target in db_b["blacklist"]:
                    del db_b["blacklist"][target]
                    self.db.write("bans", db_b)
                    self.bot.send_message(uid, f"✅ کاربر {target} آنبلاک شد.")
                    try: self.bot.send_message(target, "✅ شما توسط ادمین آنبلاک شدید.")
                    except: pass
                else:
                    self.bot.send_message(uid, "❌ کاربر یافت نشد.")
                user["state"] = "IDLE"; self.db.write("users", db_u)
                return

            if user["state"] == "ADMIN_BROADCAST":
                db_c = self.db.read("config")
                db_c["stats"]["broadcast"] = message.text
                self.db.write("config", db_c)
                self.bot.send_message(uid, "📢 پیام برای ارسال همگانی ذخیره شد. برای تایید /send_broadcast بزنید.")
                user["state"] = "IDLE"; self.db.write("users", db_u)
                return

            # 4. موتور چت فعال (Live Chat Core)
            if user.get("partner"):
                pid = user["partner"]
                
                # مدیریت دکمه‌های حین چت
                if message.text == "🔚 پایان گفتگو":
                    m = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله 🔚", callback_data="chat_end_y"), types.InlineKeyboardButton("خیر 🔙", callback_data="chat_end_n"))
                    self.bot.send_message(uid, "❓ آیا از قطع این گفتگو اطمینان دارید؟", reply_markup=m); return

                if message.text == "🚩 گزارش تخلف":
                    user["state"] = "REPORT"; self.db.write("users", db_u)
                    self.bot.send_message(uid, "📝 دلیل گزارش را بنویسید (حداکثر ۲۰۰ حرف):"); return

                if message.text == "🚫 بلاک و خروج":
                    self.block_user(uid, pid)
                    self.end_chat(uid, pid, "بلاک و خروج توسط کاربر")
                    return

                if message.text == "👥 درخواست آیدی":
                    m = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله، آیدی بده ✅", callback_data=f"id_share_y_{uid}"), types.InlineKeyboardButton("خیر ❌", callback_data="id_share_n"))
                    self.bot.send_message(pid, "❓ هم‌صحبت درخواست آیدی شما را دارد. موافقید؟", reply_markup=m)
                    self.bot.send_message(uid, "📩 درخواست ارسال شد. منتظر تایید باشید."); return

                # آنالیز هوش مصنوعی پیام‌های متنی
                if message.text:
                    toxic_score = self.ai_toxic_scan(message.text)
                    nsfw_score = self.ai_nsfw_scan(message.text)
                    if toxic_score > 0.85 or nsfw_score > 0.85:
                        self.bot.delete_message(uid, message.message_id)
                        user["warns"] += 1; self.db.write("users", db_u)
                        db_c = self.db.read("config")
                        db_c["stats"]["ai_detections"] += 1
                        self.db.write("config", db_c)
                        if user["warns"] >= 3:
                            self.auto_ban_user(uid, pid)
                            return
                        self.bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3! محتوای نامناسب (سمی: {toxic_score:.2f}, +18: {nsfw_score:.2f}) ممنوع است."); return

                # انتقال پیام به هم‌صحبت
                try:
                    self.bot.copy_message(pid, uid, message.message_id)
                except: pass
                return

            if user["state"] == "REPORT":
                if len(message.text) > 200:
                    self.bot.send_message(uid, "❌ متن طولانی است. دوباره بنویسید:"); return
                db_r = self.db.read("reports")
                db_r["archive"].append({"from": uid, "target": user["partner"], "reason": message.text, "date": str(datetime.datetime.now())})
                self.db.write("reports", db_r)
                self.bot.send_message(uid, "✅ گزارش ثبت شد و به ادمین ارسال می‌گردد.")
                try: self.bot.send_message(self.owner, f"🚩 گزارش جدید از {uid} علیه {user['partner']}: {message.text}")
                except: pass
                user["state"] = "IDLE"; self.db.write("users", db_u)
                return

            # 5. مدیریت دکمه‌های منوی اصلی و تنظیمات
            self.handle_main_menu(message, uid, user, db_u)

    def handle_main_menu(self, message, uid, user, db_u):
        if message.text == "🛰 شروع چت ناشناس":
            m = types.InlineKeyboardMarkup(row_width=2)
            m.add(types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                  types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                  types.InlineKeyboardButton("فرقی نمی‌کند 🌈", callback_data="find_any"))
            self.bot.send_message(uid, "🔍 دنبال چه کسی هستی؟", reply_markup=m)

        elif message.text == "👤 پروفایل من":
            msg = (f"👤 <b>اطلاعات کاربری:</b>\n\n🏷 نام: {user['name']}\n⚧ جنسیت: {user['sex']}\n"
                   f"🔢 سن: {user['age']}\n🏆 امتیاز: {user['score']}\n⚠️ اخطارها: {user['warns']}\n📈 سطح: {user['level']}")
            self.bot.send_message(uid, msg)

        elif message.text == "🎡 گردونه شانس روزانه":
            today = str(datetime.date.today())
            if user["last_spin"] == today:
                self.bot.send_message(uid, "❌ شما امروز شانس خود را امتحان کرده‌اید!"); return
            win = random.choice([5, 10, 20, -5, 0])
            user["score"] += win; user["last_spin"] = today
            if user["score"] >= 100 * user["level"]: user["level"] += 1
            self.db.write("users", db_u)
            self.bot.send_message(uid, f"🎡 گردونه چرخید و شما **{win}** امتیاز گرفتید! سطح فعلی: {user['level']}")

        elif message.text == "🏆 برترین‌ها":
            top_users = sorted(db_u["users"].items(), key=lambda x: x[1]["score"], reverse=True)[:10]
            msg = "🏆 <b>برترین کاربران بر اساس امتیاز:</b>\n\n"
            for i, (u, data) in enumerate(top_users, 1):
                msg += f"{i}. {data['name']} - امتیاز: {data['score']}\n"
            self.bot.send_message(uid, msg)

        elif message.text == "❓ راهنما و قوانین":
            guide = ("📜 <b>راهنما و قوانین:</b>\n\n"
                     "۱. ثبت‌نام: نام، جنسیت، سن.\n"
                     "۲. چت ناشناس: انتخاب جنسیت و جستجو.\n"
                     "۳. قوانین: بدون فحاشی، محتوای +18، اسپم. اخطارها منجر به بن می‌شود.\n"
                     "۴. گزارش: برای تخلفات استفاده کنید.\n"
                     "۵. بلاک: هم‌صحبت را بلاک کنید تا match نشود.\n"
                     "۶. گردونه: روزانه امتیاز بگیرید.\n"
                     "پشتیبانی: @admin")
            self.bot.send_message(uid, guide)

        elif message.text == "⚙ تنظیمات":
            self.bot.send_message(uid, "⚙ <b>تنظیمات:</b>", reply_markup=self.get_kb_settings())

        elif message.text == "✏️ تغییر نام":
            user["state"] = "SET_NAME"; self.db.write("users", db_u)
            self.bot.send_message(uid, "✏️ نام جدید را وارد کنید:")

        elif message.text == "🔢 تغییر سن":
            user["state"] = "SET_AGE"; self.db.write("users", db_u)
            self.bot.send_message(uid, "🔢 سن جدید را وارد کنید:")

        elif message.text == "⚧ تغییر جنسیت":
            self.bot.send_message(uid, "⚧ جنسیت جدید را انتخاب کنید:", reply_markup=self.get_kb_gender())

        elif message.text == "🔙 بازگشت به منو":
            user["state"] = "IDLE"; self.db.write("users", db_u)
            self.bot.send_message(uid, "🔙 بازگشت به منو اصلی.", reply_markup=self.get_kb_main(uid))

        elif message.text == "📊 پنل مدیریت مرکزی" and uid == self.owner:
            self.bot.send_message(uid, "📊 <b>پنل ادمین:</b>", reply_markup=self.get_kb_admin())

        elif message.text == "📈 آمار کاربران" and uid == self.owner:
            db_c = self.db.read("config")
            total = len(db_u["users"])
            db_c["stats"]["users"] = total
            self.db.write("config", db_c)
            msg = f"📈 <b>آمار:</b>\nکاربران: {total}\nچت‌ها: {db_c['stats']['chats']}\nتشخیص AI: {db_c['stats']['ai_detections']}"
            self.bot.send_message(uid, msg)

        elif message.text == "🚫 بلاک کاربر" and uid == self.owner:
            user["state"] = "ADMIN_BAN"; self.db.write("users", db_u)
            self.bot.send_message(uid, "🚫 آیدی کاربر را وارد کنید:")

        elif message.text == "✅ آنبلاک کاربر" and uid == self.owner:
            user["state"] = "ADMIN_UNBAN"; self.db.write("users", db_u)
            self.bot.send_message(uid, "✅ آیدی کاربر را وارد کنید:")

        elif message.text == "🛠 نگهداری سیستم" and uid == self.owner:
            db_c = self.db.read("config")
            db_c["settings"]["maintenance"] = not db_c["settings"]["maintenance"]
            self.db.write("config", db_c)
            status = "فعال" if db_c["settings"]["maintenance"] else "غیرفعال"
            self.bot.send_message(uid, f"🛠 حالت نگهداری: {status}")

        elif message.text == "📢 ارسال همگانی" and uid == self.owner:
            user["state"] = "ADMIN_BROADCAST"; self.db.write("users", db_u)
            self.bot.send_message(uid, "📢 متن پیام همگانی را وارد کنید:")

    # ------------------------------------------
    # بخش مدیریت رویدادهای کلیکی (Callbacks)
    # ------------------------------------------
    def init_callbacks(self):
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            uid = str(call.from_user.id)  # اصلاح: استفاده از call.from_user.id
            db_u = self.db.read("users")
            db_q = self.db.read("queue")
            db_b = self.db.read("blocks")
            user = db_u["users"].get(uid, {})
            
            if call.data.startswith("reg_sex_"):
                sex = "آقا" if "m" in call.data else "خانم"
                user["sex"] = sex
                if user["state"] == "STEP_SEX":
                    user["state"] = "STEP_AGE"
                    self.bot.edit_message_text("🔢 حالا <b>سن</b> خود را وارد کنید:", call.message.chat.id, call.message.id)
                else:
                    self.bot.answer_callback_query(call.id, "⚧ جنسیت تغییر یافت.")
                self.db.write("users", db_u)

            elif call.data.startswith("find_"):
                self.bot.edit_message_text("🔍 در حال جستجوی هم‌صحبت...", call.message.chat.id, call.message.id)
                pref = call.data.split("_")[1]  # m, f, any
                queue_key = pref if pref != "any" else "any"
                if uid not in db_q[queue_key]: db_q[queue_key].append(uid)
                self.db.write("queue", db_q)
                
                # منطق matching پیشرفته
                potential_queues = [queue_key]
                if pref == "any": potential_queues = ["male", "female", "any"]
                
                found = False
                for q_key in potential_queues:
                    pots = [p for p in db_q[q_key] if p != uid and p not in user.get("blocks", []) and uid not in db_u["users"].get(p, {}).get("blocks", [])]
                    if pots:
                        partner = pots[0]
                        db_q[q_key].remove(partner)
                        if uid in db_q[queue_key]: db_q[queue_key].remove(uid)
                        user["partner"] = partner
                        db_u["users"][partner]["partner"] = uid
                        db_c = self.db.read("config")
                        db_c["stats"]["chats"] += 1
                        self.db.write("config", db_c)
                        self.db.write("users", db_u)
                        self.db.write("queue", db_q)
                        self.bot.send_message(uid, "💎 متصل شدید! چت را شروع کنید.", reply_markup=self.get_kb_chatting())
                        self.bot.send_message(partner, "💎 متصل شدید! چت را شروع کنید.", reply_markup=self.get_kb_chatting())
                        found = True
                        break
                
                if not found:
                    self.bot.send_message(uid, "⏳ در صف انتظار هستید. منتظر بمانید یا دوباره جستجو کنید.")

            elif call.data == "chat_end_y":
                pid = user["partner"]
                self.end_chat(uid, pid, "پایان توسط کاربر")

            elif call.data == "chat_end_n":
                self.bot.answer_callback_query(call.id, "🔙 بازگشت به چت.")

            elif call.data.startswith("id_share_y_"):
                sharer = call.data.split("_")[3]
                self.bot.answer_callback_query(call.id, "✅ آیدی ارسال شد.")
                try:
                    self.bot.send_message(sharer, f"👥 آیدی هم‌صحبت: @{call.from_user.username or call.from_user.id}")
                except: pass

            elif call.data == "id_share_n":
                self.bot.answer_callback_query(call.id, "❌ درخواست رد شد.")

    def end_chat(self, uid, pid, reason):
        db_u = self.db.read("users")
        db_u["users"][uid]["partner"] = None
        db_u["users"][pid]["partner"] = None
        self.db.write("users", db_u)
        self.bot.send_message(uid, f"👋 چت پایان یافت ({reason}).", reply_markup=self.get_kb_main(uid))
        self.bot.send_message(pid, f"⚠️ هم‌صحبت چت را ترک کرد ({reason}).", reply_markup=self.get_kb_main(pid))

    def block_user(self, uid, target):
        db_u = self.db.read("users")
        if target not in db_u["users"][uid]["blocks"]:
            db_u["users"][uid]["blocks"].append(target)
            self.db.write("users", db_u)
        self.bot.send_message(uid, "🚫 کاربر بلاک شد و دیگر match نخواهد شد.")

    def auto_ban_user(self, uid, pid=None):
        db_u = self.db.read("users")
        db_b = self.db.read("bans")
        db_b["blacklist"][uid] = {"reason": "AI Content Policy Violation", "date": str(datetime.datetime.now())}
        db_u["users"][uid]["partner"] = None
        if pid: db_u["users"][pid]["partner"] = None
        self.db.write("users", db_u)
        self.db.write("bans", db_b)
        self.bot.send_message(uid, "🚫 شما به دلیل نقض مکرر قوانین مسدود شدید.")
        if pid: self.bot.send_message(pid, "⚠️ هم‌صحبت به دلیل تخلف مسدود شد.", reply_markup=self.get_kb_main(pid))

    def run(self):
        self.init_callbacks()
        print("--- Shadow Titan v13.1 Running ---")
        self.bot.infinity_polling()

# ==========================================
# 4. نقطه ورود نهایی (Main Entry)
# ==========================================
if __name__ == "__main__":
    Thread(target=run_web_server).start()
    titan = ShadowTitanBot()
    titan.run()
