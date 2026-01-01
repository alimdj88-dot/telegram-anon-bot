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
# 1. نظام مدیریت لاگ و مانیتورینگ پیشرفته
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
def status(): return "Shadow Titan v13.0: Full Systems Operational"

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
                "queue": {"male": [], "female": [], "any": []},
                "reports": {"archive": []},
                "config": {"stats": {"chats": 0, "ai_detections": 0}, "settings": {"maintenance": False}}
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
            except: return {}

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
    def ai_scan(self, text):
        """تحلیل عمیق متن توسط مدل هوش مصنوعی Toxic-BERT"""
        if not text or len(text.strip()) < 2: return 0.0
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        try:
            response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                if isinstance(res_data, list):
                    for label in res_data[0]:
                        if label['label'] == 'toxic': return label['score']
        except Exception as e:
            logger.error(f"AI Connection Error: {e}")
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
                    "score": 10, "last_spin": "", "level": 1
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

            # 3. مدیریت وضعیت‌های ثبت‌نام
            user = db_u["users"].get(uid)
            if not user: return

            if user["state"] == "STEP_NAME":
                if self.ai_scan(message.text) > 0.7:
                    self.bot.send_message(uid, "❌ نام نامناسب رد شد. نام دیگری بفرستید:"); return
                user["name"] = message.text[:20]; user["state"] = "STEP_SEX"
                self.db.write("users", db_u)
                self.bot.send_message(uid, f"خوش آمدی <b>{user['name']}</b>. جنسیت خودت رو انتخاب کن:", reply_markup=self.get_kb_gender()); return

            if user["state"] == "STEP_AGE":
                if not message.text.isdigit() or not (12 <= int(message.text) <= 99):
                    self.bot.send_message(uid, "❌ سن باید عددی بین ۱۲ تا ۹۹ باشد:"); return
                user["age"] = int(message.text); user["state"] = "IDLE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ پروفایل شما با موفقیت تایید شد!", reply_markup=self.get_kb_main(uid)); return

            # 4. موتور چت فعال (Live Chat Core)
            if user.get("partner"):
                pid = user["partner"]
                
                # مدیریت دکمه‌های حین چت
                if message.text == "🔚 پایان گفتگو":
                    m = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("بله 🔚", callback_data="chat_end_y"), types.InlineKeyboardButton("خیر 🔙", callback_data="chat_end_n"))
                    self.bot.send_message(uid, "❓ آیا از قطع این گفتگو اطمینان دارید؟", reply_markup=m); return

                # آنالیز هوش مصنوعی پیام‌های متنی
                if message.text:
                    if self.ai_scan(message.text) > 0.85:
                        self.bot.delete_message(uid, message.message_id)
                        user["warns"] += 1; self.db.write("users", db_u)
                        if user["warns"] >= 3:
                            self.auto_ban_user(uid, pid)
                            return
                        self.bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3! فحاشی ممنوع است."); return

                # انتقال پیام به هم‌صحبت
                try:
                    self.bot.copy_message(pid, uid, message.message_id)
                except: pass
                return

            # 5. مدیریت دکمه‌های منوی اصلی
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
                   f"🔢 سن: {user['age']}\n🏆 امتیاز: {user['score']}\n⚠️ اخطارها: {user['warns']}")
            self.bot.send_message(uid, msg)

        elif message.text == "🎡 گردونه شانس روزانه":
            today = str(datetime.date.today())
            if user["last_spin"] == today:
                self.bot.send_message(uid, "❌ شما امروز شانس خود را امتحان کرده‌اید!"); return
            win = random.choice([5, 10, 20, -5, 0])
            user["score"] += win; user["last_spin"] = today; self.db.write("users", db_u)
            self.bot.send_message(uid, f"🎡 گردونه چرخید و شما **{win}** امتیاز گرفتید!")

        elif message.text == "📊 پنل مدیریت مرکزی" and uid == self.owner:
            total = len(db_u["users"])
            self.bot.send_message(uid, f"⚙ <b>آمار کل سیستم:</b>\n\nتعداد کاربران: {total}\nوضعیت سرور: پایدار")

    # ------------------------------------------
    # بخش مدیریت رویدادهای کلیکی (Callbacks)
    # ------------------------------------------
    def auto_ban_user(self, uid, pid):
        db_u = self.db.read("users"); db_b = self.db.read("bans")
        db_b["blacklist"][str(uid)] = {"reason": "AI Content Policy", "date": str(datetime.datetime.now())}
        db_u["users"][str(uid)]["partner"] = None; db_u["users"][str(pid)]["partner"] = None
        self.db.write("users", db_u); self.db.write("bans", db_b)
        self.bot.send_message(uid, "🚫 شما به دلیل نقض مکرر قوانین مسدود شدید.")
        self.bot.send_message(pid, "⚠️ هم‌صحبت به دلیل تخلف مسدود شد.", reply_markup=self.get_kb_main(pid))

    def init_callbacks(self):
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            uid = str(call.message.chat.id)
            db_u = self.db.read("users"); db_q = self.db.read("queue")
            
            if call.data.startswith("reg_sex_"):
                db_u["users"][uid]["sex"] = "آقا" if "m" in call.data else "خانم"
                db_u["users"][uid]["state"] = "STEP_AGE"
                self.db.write("users", db_u)
                self.bot.edit_message_text("🔢 حالا <b>سن</b> خود را وارد کنید:", uid, call.message.id)

            elif call.data.startswith("find_"):
                self.bot.edit_message_text("🔍 در حال جستجوی هم‌صحبت...", uid, call.message.id)
                q = db_q["any"]
                if uid not in q: q.append(uid); self.db.write("queue", db_q)
                
                pots = [p for p in q if p != uid]
                if pots:
                    partner = pots[0]; q.remove(partner); q.remove(uid)
                    db_u["users"][uid]["partner"] = partner; db_u["users"][partner]["partner"] = uid
                    self.db.write("users", db_u); self.db.write("queue", db_q)
                    self.bot.send_message(uid, "💎 متصل شدید! چت را شروع کنید.", reply_markup=self.get_kb_chatting())
                    self.bot.send_message(partner, "💎 متصل شدید! چت را شروع کنید.", reply_markup=self.get_kb_chatting())

            elif call.data == "chat_end_y":
                p_id = db_u["users"][uid]["partner"]
                db_u["users"][uid]["partner"] = None; db_u["users"][p_id]["partner"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "👋 چت پایان یافت.", reply_markup=self.get_kb_main(uid))
                self.bot.send_message(p_id, "⚠️ هم‌صحبت چت را ترک کرد.", reply_markup=self.get_kb_main(p_id))

    def run(self):
        self.init_callbacks()
        print("--- Shadow Titan v13.0 Running ---")
        self.bot.infinity_polling()

# ==========================================
# 4. نقطه ورود نهایی (Main Entry)
# ==========================================
if __name__ == "__main__":
    Thread(target=run_web_server).start()
    titan = ShadowTitanBot()
    titan.run()
