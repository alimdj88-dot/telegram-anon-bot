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
import time
from flask import Flask
from threading import Thread
from zoneinfo import ZoneInfo
import math

# ==========================================
# سیستم لاگ و وب‌سرور
# ==========================================
logging.basicConfig(
    filename='shadow_titan.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("ShadowTitan")

app = Flask(__name__)
@app.route('/')
def home():
    return "Shadow Titan v42.0 – Ultimate Edition"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# ==========================================
# مدیریت دیتابیس
# ==========================================
class DB:
    def __init__(self):
        self.files = {
            "users": "db_users.json",
            "bans": "db_bans.json",
            "queue": "db_queue.json",
            "messages": "db_messages.json",
            "config": "db_config.json",
            "missions": "db_missions.json",
            "chats": "db_chats.json",
            "settings": "db_settings.json",  # فایل جدید برای تنظیمات
            "templates": "db_templates.json",  # فایل جدید برای قالب‌ها
            "reports": "db_reports.json"  # فایل جدید برای گزارش‌ها
        }
        self.lock = threading.Lock()
        self.init_files()

    def init_files(self):
        defaults = {
            "users": {"users": {}},
            "bans": {"permanent": {}, "temporary": {}},
            "queue": {"general": []},
            "messages": {"inbox": {}},
            "config": {
                "settings": {"maintenance": False},
                "broadcast": {"text": None}
            },
            "missions": {
                "daily": {
                    "date": "",
                    "mission": "ارسال 5 پیام در چت",
                    "reward_type": "coins",
                    "reward_value": 50,
                    "type": "chat_count",
                    "target": 5,
                    "description": "ارسال 5 پیام در چت"
                },
                "available": [
                    {"name": "ارسال 5 پیام در چت", "reward_type": "coins", "reward_value": 50, "type": "chat_count", "target": 5, "description": "ارسال 5 پیام در چت"},
                    {"name": "ارسال 10 پیام در چت", "reward_type": "coins", "reward_value": 100, "type": "chat_count", "target": 10, "description": "ارسال 10 پیام در چت"},
                    {"name": "چت با 3 نفر مختلف", "reward_type": "coins", "reward_value": 80, "type": "unique_chats", "target": 3, "description": "چت با 3 نفر مختلف"},
                    {"name": "چت با 5 نفر مختلف", "reward_type": "coins", "reward_value": 150, "type": "unique_chats", "target": 5, "description": "چت با 5 نفر مختلف"},
                    {"name": "دعوت 2 نفر", "reward_type": "vip", "reward_value": "week", "type": "referrals", "target": 2, "description": "دعوت 2 نفر به ربات"},
                    {"name": "دعوت 5 نفر", "reward_type": "vip", "reward_value": "month", "type": "referrals", "target": 5, "description": "دعوت 5 نفر به ربات"},
                    {"name": "چرخاندن گردونه", "reward_type": "coins", "reward_value": 30, "type": "spin_wheel", "target": 1, "description": "چرخاندن گردونه شانس"},
                    {"name": "بازدید از پروفایل 3 بار", "reward_type": "coins", "reward_value": 40, "type": "profile_views", "target": 3, "description": "بازدید 3 بار از پروفایل خود"}
                ]
            },
            "chats": {},
            "settings": {  # تنظیمات پویا
                "bot_settings": {
                    "welcome_bonus": 50,
                    "referral_bonus": 100,
                    "spin_wheel_cooldown": 24,  # ساعت
                    "max_warnings": 3,
                    "temp_ban_duration": 1440,  # دقیقه
                    "daily_reset_hour": 0,  # ساعت 00:00
                    "auto_backup": True,
                    "backup_interval_hours": 24,
                    "max_messages_per_user": 1000,
                    "chat_timeout_minutes": 30
                },
                "vip_prices": {
                    "week": 500,
                    "month": 1800,
                    "3month": 5000,
                    "6month": 9000,
                    "year": 15000
                },
                "wheel_rewards": [
                    {"type": "vip", "value": "month", "probability": 0.001, "name": "VIP 30 روزه"},
                    {"type": "coins", "value": 1000, "probability": 0.049, "name": "1000 سکه"},
                    {"type": "coins", "value": 500, "probability": 0.05, "name": "500 سکه"},
                    {"type": "coins", "value": 200, "probability": 0.1, "name": "200 سکه"},
                    {"type": "coins", "value": 100, "probability": 0.2, "name": "100 سکه"},
                    {"type": "nothing", "value": 0, "probability": 0.6, "name": "پوچ"}
                ],
                "features": {
                    "chat_enabled": True,
                    "anonymous_messages": True,
                    "spin_wheel_enabled": True,
                    "missions_enabled": True,
                    "referral_system": True,
                    "vip_system": True,
                    "ai_filter": True,
                    "bad_words_filter": True
                },
                "messages": {
                    "welcome_message": "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\nلطفاً نام مستعار خود را وارد کنید:",
                    "rules_message": "📖 <b>راهنما و قوانین</b>\n\n<b>چگونه کار می‌کند؟</b>\n• چت کاملاً ناشناس است\n• با افراد تصادفی گفتگو کنید\n• سکه جمع کنید و VIP بخرید\n\n<b>قوانین:</b>\n❌ فحاشی ممنوع\n❌ محتوای +18 ممنوع\n❌ اسپم و آزار ممنوع\n\n<b>سیستم اخطار:</b>\n• اخطار ۳: بن ۲۴ ساعته\n• تکرار پس از بن: بن دائم",
                    "vip_features": "✅ <b>ویژگی‌های VIP:</b>\n✅ ارسال آزاد گیف و استیکر\n✅ اولویت در بررسی گزارش‌ها\n✅ دسترسی در زمان تعمیر\n✅ نشان ویژه VIP"
                }
            },
            "templates": {
                "broadcast_templates": [
                    {"name": "خوش‌آمدگویی عمومی", "text": "👋 سلام به ربات خوش آمدید!"},
                    {"name": "اعلان VIP", "text": "🎖 کاربران VIP عزیز، امتیازات ویژه شما فعال است!"},
                    {"name": "اعلان ماموریت", "text": "🎯 ماموریت جدید امروز آماده است!"}
                ],
                "button_templates": {
                    "main_menu": ["🛰 شروع چت ناشناس", "👤 پروفایل من", "📩 لینک ناشناس من", "📥 پیام‌های ناشناس", "🎡 گردونه شانس", "🎯 ماموریت روزانه", "👥 رفرال و دعوت", "🎖 خرید VIP", "❓ راهنما و قوانین", "⚙ تنظیمات"],
                    "chat_menu": ["🔚 پایان گفتگو", "🚩 گزارش تخلف", "🚫 بلاک و خروج", "👥 درخواست آیدی"]
                }
            },
            "reports": {
                "daily_stats": {},
                "user_activity": {},
                "financial_reports": {}
            }
        }
        with self.lock:
            for key, path in self.files.items():
                if not os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(defaults.get(key, {}), f, ensure_ascii=False, indent=4)

    def read(self, key):
        with self.lock:
            try:
                with open(self.files[key], "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"خطا در خواندن {key}: {e}")
                return {}

    def write(self, key, data):
        with self.lock:
            try:
                with open(self.files[key], "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"خطا در نوشتن {key}: {e}")

# ==========================================
# ربات اصلی با پنل مدیریت پیشرفته
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        self.token = "8213706320:AAFnu2EgXqRf05dPuJE_RU0AlQcXQkNdRZI"
        self.owner = "8013245091"
        self.channel = "@ChatNaAnnouncements"
        self.support = "@its_alimo"
        self.hf_token = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk"

        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.db = DB()

        try:
            self.username = self.bot.get_me().username
        except:
            self.username = "ShadowTitanBot"
            logger.error("خطا در دریافت نام کاربری بات")

        # بارگیری تنظیمات پویا
        self.settings = self.db.read("settings")
        self.vip_prices_coins = self.settings.get("vip_prices", {
            "week": 500, "month": 1800, "3month": 5000, 
            "6month": 9000, "year": 15000, "christmas": 0
        })

        # مدت‌های VIP به ثانیه
        self.vip_durations = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "3month": 90 * 24 * 3600,
            "6month": 180 * 24 * 3600,
            "year": 365 * 24 * 3600,
            "christmas": 90 * 24 * 3600
        }

        # لیست فحش
        self.bad_words = [
            "کیر", "کیرم", "کیرت", "کیری", "کس", "کص", "کوس", "کوث",
            "جنده", "جهنده", "مادرجنده", "قحبه", "قهبه",
            "پدرسگ", "پدرسوخته", "حرامزاده", "گاییدم", "گاییدن",
            "سیکتیر", "کون", "کونی", "گوه", "لاشی", "فاحشه",
            "ناموس", "اوبی", "بی‌ناموس", "سکس", "پورن",
            "خارکصه", "تخمم", "شاسگول", "پفیوز", "دیوث"
        ]

        # متغیرهای مدیریت
        self.maintenance_warning_active = False
        self.maintenance_warning_event = None
        self.maintenance_warning_thread = None
        self.auto_backup_thread = None
        self.daily_reset_thread = None
        
        # شروع سیستم‌های خودکار
        self.start_auto_systems()
        
        # بازیابی چت‌های فعال
        self.restore_active_chats()
        
        # بروزرسانی خودکار ماموریت روزانه
        self.auto_update_daily_mission()
        
        self.register_handlers()
        logger.info("Shadow Titan v42.0 Advanced شروع شد")

    def start_auto_systems(self):
        """شروع سیستم‌های خودکار"""
        # سیستم پشتیبان‌گیری خودکار
        if self.settings.get("bot_settings", {}).get("auto_backup", True):
            self.start_auto_backup()
        
        # سیستم ریست روزانه خودکار
        self.start_daily_reset()
        
        logger.info("سیستم‌های خودکار شروع شدند")

    def start_auto_backup(self):
        """شروع پشتیبان‌گیری خودکار"""
        def backup_task():
            interval = self.settings.get("bot_settings", {}).get("backup_interval_hours", 24) * 3600
            while True:
                time.sleep(interval)
                self.create_backup()
        
        self.auto_backup_thread = threading.Thread(target=backup_task, daemon=True)
        self.auto_backup_thread.start()

    def start_daily_reset(self):
        """شروع ریست روزانه خودکار"""
        def reset_task():
            while True:
                now = datetime.datetime.now()
                reset_hour = self.settings.get("bot_settings", {}).get("daily_reset_hour", 0)
                
                # محاسبه زمان تا ریست بعدی
                target_time = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
                if now >= target_time:
                    target_time += datetime.timedelta(days=1)
                
                wait_seconds = (target_time - now).total_seconds()
                time.sleep(wait_seconds)
                
                # انجام ریست
                self.perform_daily_reset()
        
        self.daily_reset_thread = threading.Thread(target=reset_task, daemon=True)
        self.daily_reset_thread.start()

    def create_backup(self):
        """ایجاد پشتیبان از دیتابیس"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            for key, path in self.db.files.items():
                if os.path.exists(path):
                    backup_path = os.path.join(backup_dir, f"{key}_{timestamp}.json")
                    with open(path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            logger.info(f"پشتیبان‌گیری انجام شد: {timestamp}")
            
            # حذف پشتیبان‌های قدیمی (نگه‌داری 7 روز آخر)
            self.clean_old_backups(backup_dir, days=7)
            
        except Exception as e:
            logger.error(f"خطا در پشتیبان‌گیری: {e}")

    def clean_old_backups(self, backup_dir, days=7):
        """پاک کردن پشتیبان‌های قدیمی"""
        try:
            cutoff_time = time.time() - (days * 24 * 3600)
            for filename in os.listdir(backup_dir):
                filepath = os.path.join(backup_dir, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    logger.info(f"پشتیبان قدیمی حذف شد: {filename}")
        except Exception as e:
            logger.error(f"خطا در پاک کردن پشتیبان‌های قدیمی: {e}")

    def perform_daily_reset(self):
        """انجام ریست روزانه"""
        try:
            db_u = self.db.read("users")
            today = str(datetime.date.today())
            
            for uid, user in db_u["users"].items():
                user["daily_chat_count"] = 0
                user["daily_unique_chats"] = []
                user["daily_spin_done"] = False
                user["daily_profile_views"] = 0
                user["last_active_date"] = today
                
                # ریست اخطارها برای کاربرانی که بن موقت داشتند و مدت آن گذشته
                if user.get("had_temp_ban", False):
                    last_ban = self.check_last_ban_time(uid)
                    if last_ban and (datetime.datetime.now().timestamp() - last_ban) > 30*24*3600:  # 30 روز
                        user["warns"] = 0
                        user["had_temp_ban"] = False
            
            self.db.write("users", db_u)
            logger.info("ریست روزانه انجام شد")
            
            # بروزرسانی ماموریت روزانه
            self.auto_update_daily_mission()
            
        except Exception as e:
            logger.error(f"خطا در ریست روزانه: {e}")

    def check_last_ban_time(self, uid):
        """بررسی زمان آخرین بن"""
        db_b = self.db.read("bans")
        if uid in db_b.get("temporary", {}):
            return db_b["temporary"][uid].get("end", 0)
        return None

    def restore_active_chats(self):
        """بازیابی چت‌های فعال از دیتابیس"""
        db_c = self.db.read("chats")
        db_u = self.db.read("users")
        
        for uid, partner in db_c.items():
            if uid in db_u["users"] and partner in db_u["users"]:
                if db_u["users"][uid].get("state") == "idle":
                    db_u["users"][uid]["partner"] = partner
                    db_u["users"][partner]["partner"] = uid
                    logger.info(f"چت بازیابی شد: {uid} <-> {partner}")
                    
                    try:
                        self.bot.send_message(uid, "🔄 <b>چت شما بازیابی شد!</b>\n\n"
                                                  "ربات ری‌استارت شده بود. می‌توانید ادامه دهید.", 
                                              reply_markup=self.kb_chatting())
                        self.bot.send_message(partner, "🔄 <b>چت شما بازیابی شد!</b>\n\n"
                                                      "ربات ری‌استارت شده بود. می‌توانید ادامه دهید.", 
                                              reply_markup=self.kb_chatting())
                    except Exception as e:
                        logger.error(f"خطا در ارسال پیام بازیابی چت: {e}")
        
        self.db.write("users", db_u)
        logger.info("بازیابی چت‌های فعال انجام شد")

    def save_active_chat(self, uid, partner):
        """ذخیره چت فعال در دیتابیس"""
        db_c = self.db.read("chats")
        db_c[uid] = partner
        self.db.write("chats", db_c)

    def remove_active_chat(self, uid):
        """حذف چت فعال از دیتابیس"""
        db_c = self.db.read("chats")
        if uid in db_c:
            partner = db_c[uid]
            if partner in db_c and db_c[partner] == uid:
                del db_c[partner]
            del db_c[uid]
            self.db.write("chats", db_c)

    def auto_update_daily_mission(self):
        """بروزرسانی خودکار ماموریت روزانه"""
        db_m = self.db.read("missions")
        today = str(datetime.date.today())
        
        if db_m["daily"]["date"] != today:
            mission = random.choice(db_m["available"])
            db_m["daily"] = {
                "date": today,
                "mission": mission["name"],
                "reward_type": mission["reward_type"],
                "reward_value": mission["reward_value"],
                "type": mission["type"],
                "target": mission["target"],
                "description": mission.get("description", mission["name"])
            }
            self.db.write("missions", db_m)
            logger.info(f"ماموریت روزانه بروز شد: {mission['name']}")

    # ==========================================
    # 🔧 سیستم مدیریت پیشرفته
    # ==========================================

    def update_settings(self, key, value):
        """بروزرسانی تنظیمات پویا"""
        settings = self.db.read("settings")
        
        # اعمال تغییر به صورت بازگشتی
        def recursive_update(d, keys, val):
            if len(keys) == 1:
                d[keys[0]] = val
            else:
                if keys[0] not in d:
                    d[keys[0]] = {}
                recursive_update(d[keys[0]], keys[1:], val)
        
        keys = key.split('.')
        recursive_update(settings, keys, value)
        
        self.db.write("settings", settings)
        self.settings = settings  # بروزرسانی کش
        
        # اعمال تغییرات در زمان اجرا
        if key == "vip_prices":
            self.vip_prices_coins = settings.get("vip_prices", {})
        elif key == "bot_settings.welcome_bonus":
            logger.info(f"پاداش خوش‌آمدگویی به {value} سکه تغییر یافت")
        
        return True

    def get_statistics(self, period="daily"):
        """دریافت آمار پیشرفته"""
        db_u = self.db.read("users")
        db_b = self.db.read("bans")
        db_c = self.db.read("chats")
        
        stats = {
            "total_users": len(db_u["users"]),
            "active_today": sum(1 for u in db_u["users"].values() 
                              if u.get("last_active_date") == str(datetime.date.today())),
            "male_users": sum(1 for u in db_u["users"].values() if u.get("sex") == "آقا"),
            "female_users": sum(1 for u in db_u["users"].values() if u.get("sex") == "خانم"),
            "vip_users": sum(1 for uid in db_u["users"] if self.is_vip(uid)),
            "total_coins": sum(u.get("coins", 0) for u in db_u["users"].values()),
            "permanent_bans": len(db_b.get("permanent", {})),
            "temporary_bans": len(db_b.get("temporary", {})),
            "active_chats": len(db_c),
            "queue_size": len(self.db.read("queue").get("general", []))
        }
        
        # محاسبه رشد
        if period == "weekly":
            # در اینجا می‌توانید آمار هفتگی را محاسبه کنید
            pass
        
        return stats

    def search_users(self, query, search_type="id"):
        """جستجوی پیشرفته کاربران"""
        db_u = self.db.read("users")
        results = []
        
        for uid, user in db_u["users"].items():
            if search_type == "id" and query in uid:
                results.append((uid, user))
            elif search_type == "name" and query.lower() in user.get("name", "").lower():
                results.append((uid, user))
            elif search_type == "age" and str(user.get("age", "")) == query:
                results.append((uid, user))
            elif search_type == "vip" and self.is_vip(uid) == (query.lower() == "true"):
                results.append((uid, user))
        
        return results

    def send_targeted_broadcast(self, user_ids, message):
        """ارسال پیام هدفمند"""
        success = 0
        failed = 0
        
        for uid in user_ids:
            try:
                self.bot.send_message(uid, message)
                success += 1
                time.sleep(0.1)  # جلوگیری از محدودیت تلگرام
            except Exception as e:
                logger.error(f"خطا در ارسال به {uid}: {e}")
                failed += 1
        
        return success, failed

    def manage_bad_words(self, action, word=None):
        """مدیریت لیست کلمات فحش"""
        if action == "add" and word:
            if word not in self.bad_words:
                self.bad_words.append(word)
                return True
        elif action == "remove" and word:
            if word in self.bad_words:
                self.bad_words.remove(word)
                return True
        elif action == "list":
            return self.bad_words
        
        return False

    def contains_bad(self, text):
        """بررسی فحش"""
        if not text:
            return False
        t = text.lower()
        t = re.sub(r'[\s\*\-_\.\d]+', '', t)
        return any(word.lower() in t for word in self.bad_words)

    def ai_toxic_scan(self, text):
        """اسکن هوش مصنوعی برای محتوای مسموم"""
        if not text or len(text.strip()) < 2:
            return 0.0
        
        # اگر فیلتر AI غیرفعال است
        if not self.settings.get("features", {}).get("ai_filter", True):
            return 0.0
            
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
            logger.error(f"خطا در AI toxic scan: {e}")
        return 0.0

    def ai_nsfw_scan(self, text):
        """اسکن هوش مصنوعی برای محتوای +18"""
        if not text or len(text.strip()) < 2:
            return 0.0
        
        # اگر فیلتر AI غیرفعال است
        if not self.settings.get("features", {}).get("ai_filter", True):
            return 0.0
            
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
            logger.error(f"خطا در AI NSFW scan: {e}")
        return 0.0

    def is_vip(self, uid):
        """بررسی VIP بودن"""
        db_u = self.db.read("users")
        user = db_u["users"].get(uid, {})
        vip_end = user.get("vip_end", 0)
        return vip_end > datetime.datetime.now().timestamp()

    def add_vip(self, uid, duration_key, reason="گیفت"):
        """افزودن VIP - مدت VIP ها جمع می‌شود"""
        db_u = self.db.read("users")
        if uid not in db_u["users"]:
            return False
        
        now = datetime.datetime.now().timestamp()
        current_end = db_u["users"][uid].get("vip_end", 0)
        
        if current_end < now:
            new_end = now + self.vip_durations[duration_key]
        else:
            new_end = current_end + self.vip_durations[duration_key]
        
        db_u["users"][uid]["vip_end"] = new_end
        
        if duration_key == "christmas":
            db_u["users"][uid]["christmas_vip_taken"] = True
        
        self.db.write("users", db_u)
        
        try:
            end_date = datetime.datetime.fromtimestamp(new_end).strftime("%Y-%m-%d")
            duration_name = {
                "week": "۱ هفته",
                "month": "۱ ماه",
                "3month": "۳ ماه",
                "6month": "۶ ماه",
                "year": "۱ سال",
                "christmas": "۳ ماه رایگان"
            }.get(duration_key, "۳ ماه")
            
            remaining_days = int((new_end - now) / (24 * 3600))
            
            self.bot.send_message(uid, f"🎉 <b>تبریک! رنک VIP دریافت کردید</b>\n\n"
                                       f"مدت: {duration_name}\n"
                                       f"تا تاریخ: {end_date}\n"
                                       f"مدت باقی‌مانده: {remaining_days} روز\n"
                                       f"دلیل: {reason}\n\nمبارک باشد ✨")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام VIP به {uid}: {e}")
        return True

    def add_coins(self, uid, amount, reason=""):
        """افزودن سکه"""
        db_u = self.db.read("users")
        if uid not in db_u["users"]:
            return False
        
        if "coins" not in db_u["users"][uid]:
            db_u["users"][uid]["coins"] = 0
        
        db_u["users"][uid]["coins"] += amount
        self.db.write("users", db_u)
        
        try:
            self.bot.send_message(uid, f"💰 <b>دریافت سکه!</b>\n\n"
                                       f"مقدار: {amount:,} سکه\n"
                                       f"دلیل: {reason}\n"
                                       f"موجودی: {db_u['users'][uid]['coins']:,} سکه")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام سکه به {uid}: {e}")
        
        return True

    def check_and_reward_mission(self, uid):
        """بررسی و پاداش ماموریت روزانه"""
        db_u = self.db.read("users")
        db_m = self.db.read("missions")
        user = db_u["users"].get(uid, {})
        
        today = str(datetime.date.today())
        if user.get("mission_completed_date") == today:
            return False
        
        mission = db_m["daily"]
        mission_type = mission["type"]
        target = mission["target"]
        
        completed = False
        if mission_type == "chat_count":
            if user.get("daily_chat_count", 0) >= target:
                completed = True
        elif mission_type == "unique_chats":
            if len(user.get("daily_unique_chats", [])) >= target:
                completed = True
        elif mission_type == "referrals":
            if user.get("total_referrals", 0) >= target:
                completed = True
        elif mission_type == "spin_wheel":
            if user.get("daily_spin_done", False):
                completed = True
        elif mission_type == "profile_views":
            if user.get("daily_profile_views", 0) >= target:
                completed = True
        
        if completed:
            reward_type = mission.get("reward_type", "coins")
            reward_value = mission.get("reward_value", 50)
            
            if reward_type == "coins":
                self.add_coins(uid, reward_value, f"ماموریت روزانه: {mission['mission']}")
            elif reward_type == "vip":
                self.add_vip(uid, reward_value, f"ماموریت روزانه: {mission['mission']}")
            
            user["mission_completed_date"] = today
            self.db.write("users", db_u)
            return True
        
        return False

    def ban_perm(self, uid, reason="تخلف"):
        """بن دائم"""
        db_b = self.db.read("bans")
        db_b["permanent"][uid] = reason
        self.db.write("bans", db_b)
        try:
            self.bot.send_message(uid, f"🚫 <b>شما بن دائم شدید!</b>\n"
                                      f"دلیل: {reason}\n"
                                      f"پشتیبانی: {self.support}")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام بن به {uid}: {e}")

    def ban_temp(self, uid, minutes, reason="تخلف"):
        """بن موقت"""
        db_b = self.db.read("bans")
        end_time = datetime.datetime.now().timestamp() + minutes * 60
        db_b["temporary"][uid] = {"end": end_time, "reason": reason}
        self.db.write("bans", db_b)
        
        try:
            remaining_hours = minutes // 60
            remaining_minutes = minutes % 60
            time_text = ""
            if remaining_hours > 0:
                time_text += f"{remaining_hours} ساعت"
            if remaining_minutes > 0:
                if time_text:
                    time_text += " و "
                time_text += f"{remaining_minutes} دقیقه"
            
            self.bot.send_message(uid, f"🚫 <b>بن موقت {time_text}</b>\n"
                                      f"دلیل: {reason}\n"
                                      f"پشتیبانی: {self.support}")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام بن موقت به {uid}: {e}")

    def report_auto_ban(self, uid, reason, ban_type):
        """گزارش بن خودکار به ادمین"""
        db_u = self.db.read("users")
        name = db_u["users"].get(uid, {}).get("name", "نامشخص")
        tehran_time = datetime.datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")
        
        report_text = f"🤖 <b>بن خودکار توسط ربات</b>\n\n"
        report_text += f"کاربر: 🆔 <code>{uid}</code> - {name}\n"
        report_text += f"تاریخ (ایران): {tehran_time}\n"
        report_text += f"نوع بن: {ban_type}\n"
        report_text += f"دلیل: {reason}\n\n"
        report_text += "آیا تصمیم ربات درست بود؟"

        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ درست بود", callback_data=f"auto_ban_correct_{uid}"),
            types.InlineKeyboardButton("❌ اشتباه بود (بخشیدن)", callback_data=f"auto_ban_pardon_{uid}")
        )

        try:
            self.bot.send_message(self.owner, report_text, reply_markup=kb)
        except Exception as e:
            logger.error(f"خطا در ارسال گزارش بن خودکار: {e}")

    def end_chat(self, a, b, msg="به دلیل تخلف از چت خارج شد"):
        """پایان چت"""
        db_u = self.db.read("users")
        if a in db_u["users"]:
            db_u["users"][a]["partner"] = None
        if b in db_u["users"]:
            db_u["users"][b]["partner"] = None
        self.db.write("users", db_u)
        
        self.remove_active_chat(a)
        self.remove_active_chat(b)
        
        try:
            self.bot.send_message(a, "چت با موفقیت پایان یافت 🌙", reply_markup=self.kb_main(a))
        except:
            pass
        try:
            self.bot.send_message(b, f"هم‌صحبت شما {msg} 🌙", reply_markup=self.kb_main(b))
        except:
            pass

    # ==========================================
    # 🎛 کیبوردها
    # ==========================================

    def kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = self.settings.get("templates", {}).get("button_templates", {}).get("main_menu", [
            "🛰 شروع چت ناشناس", "👤 پروفایل من",
            "📩 لینک ناشناس من", "📥 پیام‌های ناشناس",
            "🎡 گردونه شانس", "🎯 ماموریت روزانه",
            "👥 رفرال و دعوت", "🎖 خرید VIP",
            "❓ راهنما و قوانین", "⚙ تنظیمات"
        ])
        
        # اضافه کردن دکمه‌ها به صورت ردیفی
        for i in range(0, len(buttons), 2):
            row = buttons[i:i+2]
            markup.add(*row)
        
        if uid == self.owner:
            markup.add("📊 پنل مدیریت")
        return markup

    def kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = self.settings.get("templates", {}).get("button_templates", {}).get("chat_menu", [
            "🔚 پایان گفتگو", "🚩 گزارش تخلف",
            "🚫 بلاک و خروج", "👥 درخواست آیدی"
        ])
        
        for i in range(0, len(buttons), 2):
            row = buttons[i:i+2]
            markup.add(*row)
        
        return markup

    def kb_admin(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📈 آمار پیشرفته", "🔍 جستجوی کاربران")
        markup.add("⚙️ تنظیمات پویا", "📢 ارسال هدفمند")
        markup.add("🛠 مدیریت قابلیت‌ها", "🗣 مدیریت فحش")
        markup.add("📊 گزارش‌گیری", "🔄 مدیریت خودکار")
        markup.add("🎭 مدیریت قالب‌ها", "💾 پشتیبان‌گیری")
        markup.add("📋 لیست VIP", "💰 مدیریت اقتصادی")
        markup.add("🎯 مدیریت ماموریت‌ها", "🚫 مدیریت بن‌ها")
        markup.add("⚠️ هشدار تعمیر", "🔙 بازگشت به منو")
        return markup

    def kb_admin_settings(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💰 قیمت VIP", callback_data="admin_vip_prices"),
            types.InlineKeyboardButton("🎡 گردونه", callback_data="admin_wheel_settings")
        )
        markup.add(
            types.InlineKeyboardButton("🎁 پاداش‌ها", callback_data="admin_rewards"),
            types.InlineKeyboardButton("📝 پیام‌ها", callback_data="admin_messages")
        )
        markup.add(
            types.InlineKeyboardButton("⚙ تنظیمات اصلی", callback_data="admin_main_settings"),
            types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
        )
        return markup

    def kb_report(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
            types.InlineKeyboardButton("+18", callback_data="rep_nsfw")
        )
        markup.add(
            types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
            types.InlineKeyboardButton("آزار", callback_data="rep_harass")
        )
        markup.add(types.InlineKeyboardButton("لغو ❌", callback_data="rep_cancel"))
        return markup

    # ==========================================
    # 🎪 سیستم‌های مدیریتی
    # ==========================================

    def start_maintenance_warning(self, admin_id):
        """شروع هشدار تعمیر و نگهداری"""
        if self.maintenance_warning_active:
            return
        
        self.maintenance_warning_active = True
        self.maintenance_warning_event = threading.Event()
        
        def warning_thread():
            try:
                for i in range(6):
                    if self.maintenance_warning_event.is_set():
                        logger.info("هشدار تعمیر توسط ادمین لغو شد")
                        return
                    
                    time.sleep(30)
                    remaining = 3 - (i * 0.5)
                    
                    try:
                        self.bot.send_message(
                            admin_id,
                            f"⚠️ <b>هشدار تعمیر و نگهداری</b>\n\n"
                            f"ربات {remaining:.1f} دقیقه دیگر به حالت تعمیر می‌رود.\n"
                            f"اطلاعات شما ذخیره خواهد شد.\n\n"
                            f"📞 پشتیبانی: {self.support}\n\n"
                            f"برای لغو روی '⛔ لغو هشدار' کلیک کنید."
                        )
                    except:
                        pass
                
                if not self.maintenance_warning_event.is_set():
                    time.sleep(30)
                    db_c = self.db.read("config")
                    db_c["settings"]["maintenance"] = True
                    self.db.write("config", db_c)
                    
                    self.bot.send_message(
                        admin_id,
                        "✅ <b>ربات به حالت تعمیر و نگهداری رفت.</b>\n\n"
                        "اکنون فقط کاربران VIP می‌توانند از ربات استفاده کنند."
                    )
                
                self.maintenance_warning_active = False
                self.maintenance_warning_event = None
                
            except Exception as e:
                logger.error(f"خطا در ترد هشدار تعمیر: {e}")
                self.maintenance_warning_active = False
                self.maintenance_warning_event = None
        
        self.maintenance_warning_thread = threading.Thread(target=warning_thread)
        self.maintenance_warning_thread.daemon = True
        self.maintenance_warning_thread.start()
        
        return True

    def cancel_maintenance_warning(self, admin_id):
        """لغو هشدار تعمیر"""
        if not self.maintenance_warning_active:
            return False
        
        if self.maintenance_warning_event:
            self.maintenance_warning_event.set()
        
        self.maintenance_warning_active = False
        self.send_maintenance_cancel_notification()
        
        return True

    def send_maintenance_cancel_notification(self):
        """ارسال پیام لغو هشدار به کاربران"""
        db_u = self.db.read("users")
        users_to_notify = []
        
        for uid, user_data in db_u["users"].items():
            if self.is_vip(uid):
                users_to_notify.append(uid)
        
        for uid in users_to_notify[:50]:
            try:
                self.bot.send_message(
                    uid,
                    "📢 <b>اطلاعیه مهم</b>\n\n"
                    "هشدار تعمیر و نگهداری ربات لغو شد.\n"
                    "ربات به حالت عادی بازگشته و می‌توانید از آن استفاده کنید.\n\n"
                    "با تشکر از صبر و شکیبایی شما 🌹"
                )
            except Exception as e:
                logger.error(f"خطا در ارسال پیام لغو به {uid}: {e}")
        
        logger.info(f"پیام لغو هشدار به {len(users_to_notify[:50])} کاربر ارسال شد")

    def get_mission_description(self, mission_type, target):
        """دریافت توضیح ماموریت بر اساس نوع"""
        descriptions = {
            "chat_count": f"ارسال {target} پیام در چت",
            "unique_chats": f"چت با {target} نفر مختلف",
            "referrals": f"دعوت {target} نفر به ربات",
            "spin_wheel": "چرخاندن گردونه شانس",
            "profile_views": f"بازدید {target} بار از پروفایل خود"
        }
        return descriptions.get(mission_type, f"ماموریت {mission_type}")

    # ==========================================
    # 📝 هندلرها
    # ==========================================

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(msg):
            uid = str(msg.chat.id)
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None

            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")

            # چک بن دائم
            if uid in db_b["permanent"]:
                reason = db_b["permanent"][uid]
                self.bot.send_message(uid, f"🚫 <b>شما بن دائم هستید!</b>\n"
                                          f"دلیل: {reason}\n"
                                          f"پشتیبانی: {self.support}")
                return

            # چک بن موقت
            if uid in db_b["temporary"]:
                temp_data = db_b["temporary"][uid]
                end = temp_data["end"]
                if datetime.datetime.now().timestamp() < end:
                    rem = int((end - datetime.datetime.now().timestamp()) / 60)
                    hours = rem // 60
                    minutes = rem % 60
                    time_text = ""
                    if hours > 0:
                        time_text += f"{hours} ساعت"
                    if minutes > 0:
                        if time_text:
                            time_text += " و "
                        time_text += f"{minutes} دقیقه"
                    
                    self.bot.send_message(uid, f"🚫 <b>بن موقت هستید!</b>\n"
                                              f"زمان باقی‌مانده: {time_text}\n"
                                              f"پشتیبانی: {self.support}")
                    return
                else:
                    del db_b["temporary"][uid]
                    self.db.write("bans", db_b)

            # چک تعمیر
            if db_c["settings"]["maintenance"] and not self.is_vip(uid) and uid != self.owner:
                self.bot.send_message(uid, "🔧 <b>ربات در حال تعمیر و نگهداری است</b>\n\n"
                                          f"فقط کاربران VIP دسترسی دارند 🌟\n"
                                          f"پشتیبانی: {self.support}")
                return

            # رفرال
            if payload and payload.startswith("ref_"):
                referrer_id = payload[4:]
                if referrer_id != uid and uid not in db_u["users"]:
                    if referrer_id in db_u["users"]:
                        db_u["users"][referrer_id]["total_referrals"] = db_u["users"][referrer_id].get("total_referrals", 0) + 1
                        db_u["users"][referrer_id]["referral_list"] = db_u["users"][referrer_id].get("referral_list", [])
                        db_u["users"][referrer_id]["referral_list"].append(uid)
                        self.db.write("users", db_u)
                        
                        referral_bonus = self.settings.get("bot_settings", {}).get("referral_bonus", 100)
                        self.add_coins(referrer_id, referral_bonus, f"دعوت کاربر جدید")
                        try:
                            self.bot.send_message(referrer_id, f"🎉 یک کاربر جدید از لینک شما عضو شد!\n"
                                                              f"💰 +{referral_bonus} سکه پاداش دریافت کردید")
                        except:
                            pass

            # لینک ناشناس
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    self.bot.send_message(uid, "❌ نمی‌توانید به خودتان پیام بفرستید 😊")
                    return
                
                if uid not in db_u["users"]:
                    welcome_bonus = self.settings.get("bot_settings", {}).get("welcome_bonus", 50)
                    db_u["users"][uid] = {
                        "state": "name",
                        "vip_end": 0,
                        "warns": 0,
                        "blocks": [],
                        "coins": welcome_bonus,
                        "total_referrals": 0,
                        "referral_list": [],
                        "daily_chat_count": 0,
                        "daily_unique_chats": [],
                        "daily_spin_done": False,
                        "daily_profile_views": 0,
                        "mission_completed_date": "",
                        "last_spin": "",
                        "christmas_vip_taken": False,
                        "had_temp_ban": False,
                        "anon_target": target
                    }
                    self.db.write("users", db_u)
                    welcome_msg = self.settings.get("messages", {}).get("welcome_message", 
                        "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\nلطفاً نام مستعار خود را وارد کنید:")
                    self.bot.send_message(uid, welcome_msg)
                else:
                    db_u["users"][uid]["state"] = "anon_send"
                    db_u["users"][uid]["anon_target"] = target
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "📝 پیام ناشناس خود را بنویسید:")
                return

            # ثبت‌نام عادی
            if uid not in db_u["users"]:
                welcome_bonus = self.settings.get("bot_settings", {}).get("welcome_bonus", 50)
                db_u["users"][uid] = {
                    "state": "name",
                    "vip_end": 0,
                    "warns": 0,
                    "blocks": [],
                    "coins": welcome_bonus,
                    "total_referrals": 0,
                    "referral_list": [],
                    "daily_chat_count": 0,
                    "daily_unique_chats": [],
                    "daily_spin_done": False,
                    "daily_profile_views": 0,
                    "mission_completed_date": "",
                    "last_spin": "",
                    "christmas_vip_taken": False,
                    "had_temp_ban": False
                }
                self.db.write("users", db_u)
                welcome_msg = self.settings.get("messages", {}).get("welcome_message", 
                    "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\nلطفاً نام مستعار خود را وارد کنید:")
                self.bot.send_message(uid, welcome_msg)
            else:
                self.bot.send_message(uid, "خوش برگشتید عزیز 🌹", reply_markup=self.kb_main(uid))

        @self.bot.message_handler(func=lambda msg: True, content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def main(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")

            # چک بن
            if uid in db_b["permanent"]:
                return
            if uid in db_b["temporary"] and datetime.datetime.now().timestamp() < db_b["temporary"][uid]["end"]:
                return

            # چک تعمیر
            if db_c["settings"]["maintenance"] and not self.is_vip(uid) and uid != self.owner:
                return

            # چک عضویت کانال
            try:
                if uid != self.owner:
                    status = self.bot.get_chat_member(self.channel, uid).status
                    if status not in ['member', 'administrator', 'creator']:
                        self.bot.send_message(uid, f"❌ برای استفاده از ربات باید در کانال عضو شوید:\n{self.channel}")
                        return
            except:
                pass

            user = db_u["users"].get(uid)
            if not user:
                return

            # ریست روزانه
            today = str(datetime.date.today())
            if user.get("last_active_date") != today:
                user["daily_chat_count"] = 0
                user["daily_unique_chats"] = []
                user["daily_spin_done"] = False
                user["daily_profile_views"] = 0
                user["last_active_date"] = today
                self.db.write("users", db_u)

            # مرحله نام
            if user.get("state") == "name":
                if msg.content_type != "text":
                    self.bot.send_message(uid, "❌ لطفاً فقط متن وارد کنید")
                    return
                if self.contains_bad(msg.text):
                    self.bot.send_message(uid, "❌ نام شامل کلمات نامناسب است")
                    return
                user["name"] = msg.text[:20]
                user["state"] = "sex"
                self.db.write("users", db_u)
                
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("آقا 👦", callback_data="sex_m"),
                    types.InlineKeyboardButton("خانم 👧", callback_data="sex_f")
                )
                self.bot.send_message(uid, f"سلام {user['name']} 🌸\n\n"
                                          "جنسیت خود را انتخاب کنید:", reply_markup=kb)
                return

            # مرحله سن
            if user.get("state") == "age":
                if msg.content_type != "text" or not msg.text.isdigit():
                    self.bot.send_message(uid, "❌ لطفاً فقط عدد وارد کنید")
                    return
                age = int(msg.text)
                if not 12 <= age <= 99:
                    self.bot.send_message(uid, "❌ سن باید بین ۱۲ تا ۹۹ باشد")
                    return
                
                user["age"] = age
                user["state"] = "idle"
                self.db.write("users", db_u)
                
                # پاداش ثبت‌نام
                welcome_bonus = self.settings.get("bot_settings", {}).get("welcome_bonus", 50)
                self.add_coins(uid, welcome_bonus, "پاداش ثبت‌نام")
                
                self.bot.send_message(uid, f"✅ <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
                                          f"🎁 پاداش ثبت‌نام: {welcome_bonus} سکه\n\n"
                                          "حالا از ربات لذت ببرید!", 
                                          reply_markup=self.kb_main(uid))
                return

            # پیام ناشناس ارسال
            if user.get("state") == "anon_send":
                if msg.content_type != "text":
                    self.bot.send_message(uid, "❌ فقط متن مجاز است")
                    return
                
                target = user.get("anon_target")
                if not target:
                    self.bot.send_message(uid, "❌ خطا در ارسال پیام")
                    return
                
                db_m = self.db.read("messages")
                if target not in db_m["inbox"]:
                    db_m["inbox"][target] = []
                
                db_m["inbox"][target].append({
                    "text": msg.text,
                    "from": uid,
                    "seen": False,
                    "time": datetime.datetime.now().strftime("%H:%M %d/%m")
                })
                self.db.write("messages", db_m)
                
                self.bot.send_message(uid, "✅ پیام ناشناس با موفقیت ارسال شد")
                try:
                    self.bot.send_message(target, "📩 یک پیام ناشناس جدید دریافت کردید!")
                except:
                    pass
                
                user["state"] = "idle"
                self.db.write("users", db_u)
                return

            # پاسخ به پیام ناشناس
            if user.get("state") == "anon_reply":
                if msg.content_type != "text":
                    self.bot.send_message(uid, "❌ فقط متن مجاز است")
                    return
                
                target = user.get("anon_reply_target")
                if target:
                    try:
                        self.bot.send_message(target, f"📩 <b>پاسخ ناشناس:</b>\n\n{msg.text}")
                        self.bot.send_message(uid, "✅ پاسخ ارسال شد")
                    except:
                        self.bot.send_message(uid, "❌ خطا در ارسال پاسخ")
                
                user["state"] = "idle"
                self.db.write("users", db_u)
                return

            # تغییرات پروفایل
            if user.get("state") == "change_name":
                if msg.content_type != "text":
                    self.bot.send_message(uid, "❌ فقط متن مجاز است")
                    return
                if self.contains_bad(msg.text):
                    self.bot.send_message(uid, "❌ نام شامل کلمات نامناسب است")
                    return
                user["name"] = msg.text[:20]
                user["state"] = "idle"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ نام با موفقیت تغییر کرد", reply_markup=self.kb_main(uid))
                return

            if user.get("state") == "change_age":
                if msg.content_type != "text" or not msg.text.isdigit():
                    self.bot.send_message(uid, "❌ فقط عدد وارد کنید")
                    return
                age = int(msg.text)
                if not 12 <= age <= 99:
                    self.bot.send_message(uid, "❌ سن باید بین ۱۲ تا ۹۹ باشد")
                    return
                user["age"] = age
                user["state"] = "idle"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ سن با موفقیت تغییر کرد", reply_markup=self.kb_main(uid))
                return

            # چت فعال
            if user.get("partner"):
                partner = user["partner"]

                if msg.text == "🔚 پایان گفتگو":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(
                        types.InlineKeyboardButton("✅ بله، پایان بده", callback_data="end_yes"),
                        types.InlineKeyboardButton("❌ خیر، ادامه بده", callback_data="end_no")
                    )
                    self.bot.send_message(uid, "❓ آیا مطمئن هستید که می‌خواهید چت را پایان دهید؟", 
                                        reply_markup=kb)
                    return

                if msg.text == "🚩 گزارش تخلف":
                    user["report_target"] = partner
                    user["report_last_msg_id"] = msg.message_id
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "⚠️ دلیل گزارش را انتخاب کنید:", 
                                        reply_markup=self.kb_report())
                    return

                if msg.text == "🚫 بلاک و خروج":
                    blocks = user.get("blocks", [])
                    if partner not in blocks:
                        blocks.append(partner)
                    user["blocks"] = blocks
                    self.db.write("users", db_u)
                    self.end_chat(uid, partner, "شما را بلاک کرد")
                    return

                if msg.text == "👥 درخواست آیدی":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(
                        types.InlineKeyboardButton("✅ بله", callback_data=f"id_share_yes_{uid}"),
                        types.InlineKeyboardButton("❌ خیر", callback_data="id_share_no")
                    )
                    self.bot.send_message(partner, "📢 هم‌صحبت شما درخواست آیدی دارد. موافقید؟", 
                                        reply_markup=kb)
                    self.bot.send_message(uid, "⏳ درخواست ارسال شد، منتظر تایید باشید")
                    return

                # فیلتر فحش + AI
                if msg.content_type == "text" and msg.text:
                    # چک فعال بودن فیلترها
                    bad_words_enabled = self.settings.get("features", {}).get("bad_words_filter", True)
                    ai_enabled = self.settings.get("features", {}).get("ai_filter", True)
                    
                    is_bad = self.contains_bad(msg.text) if bad_words_enabled else False
                    toxic_score = self.ai_toxic_scan(msg.text) if ai_enabled else 0.0
                    nsfw_score = self.ai_nsfw_scan(msg.text) if ai_enabled else 0.0
                    
                    toxic_threshold = 0.8
                    nsfw_threshold = 0.8
                    
                    if is_bad or toxic_score > toxic_threshold or nsfw_score > nsfw_threshold:
                        try:
                            self.bot.delete_message(uid, msg.message_id)
                        except:
                            pass
                        
                        user["warns"] = user.get("warns", 0) + 1
                        self.db.write("users", db_u)

                        max_warnings = self.settings.get("bot_settings", {}).get("max_warnings", 3)
                        temp_ban_duration = self.settings.get("bot_settings", {}).get("temp_ban_duration", 1440)
                        
                        if user["warns"] >= max_warnings:
                            if user.get("had_temp_ban", False):
                                self.ban_perm(uid, "فحاشی مکرر پس از بن موقت")
                                self.report_auto_ban(uid, "فحاشی مکرر پس از بن موقت", "بن دائم")
                                self.end_chat(uid, partner, "به دلیل تخلف بن دائم شد")
                            else:
                                self.ban_temp(uid, temp_ban_duration, "فحاشی مکرر")
                                user["had_temp_ban"] = True
                                user["warns"] = 0
                                self.db.write("users", db_u)
                                self.report_auto_ban(uid, "فحاشی مکرر (اولین بار)", f"بن {temp_ban_duration} دقیقه‌ای")
                                self.end_chat(uid, partner, "به دلیل تخلف بن موقت شد")
                        else:
                            self.bot.send_message(uid, f"⚠️ <b>اخطار {user['warns']}/{max_warnings}</b>\n\n"
                                                      "محتوای نامناسب ممنوع است!")
                        return

                # شمارش پیام برای ماموریت
                user["daily_chat_count"] = user.get("daily_chat_count", 0) + 1
                if partner not in user.get("daily_unique_chats", []):
                    unique_chats = user.get("daily_unique_chats", [])
                    unique_chats.append(partner)
                    user["daily_unique_chats"] = unique_chats
                self.db.write("users", db_u)

                # بررسی ماموریت
                self.check_and_reward_mission(uid)

                # ارسال پیام
                try:
                    self.bot.copy_message(partner, uid, msg.message_id)
                except Exception as e:
                    logger.error(f"خطا در ارسال پیام چت: {e}")
                return

            # لغو جستجو
            if msg.text == "❌ لغو جستجو":
                db_q = self.db.read("queue")
                if uid in db_q.get("general", []):
                    db_q["general"].remove(uid)
                    self.db.write("queue", db_q)
                self.bot.send_message(uid, "✅ جستجو با موفقیت لغو شد", reply_markup=self.kb_main(uid))
                return

            # منوی اصلی
            if not msg.text:
                return

            text = msg.text

            if text == "🛰 شروع چت ناشناس":
                # چک فعال بودن چت
                if not self.settings.get("features", {}).get("chat_enabled", True):
                    self.bot.send_message(uid, "❌ سرویس چت موقتاً غیرفعال است")
                    return
                    
                kb = types.InlineKeyboardMarkup(row_width=3)
                kb.add(
                    types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                    types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                    types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any")
                )
                self.bot.send_message(uid, "🔍 دنبال چه کسی می‌گردید؟", reply_markup=kb)

            elif text == "👤 پروفایل من":
                db_u = self.db.read("users")
                user = db_u["users"].get(uid)
                
                if not user:
                    return
                
                user["daily_profile_views"] = user.get("daily_profile_views", 0) + 1
                self.db.write("users", db_u)
                
                rank = "🎖 VIP" if self.is_vip(uid) else "⭐ عادی"
                vip_end = user.get("vip_end", 0)
                
                if vip_end > 0:
                    vip_status = f"تا {datetime.datetime.fromtimestamp(vip_end).strftime('%Y-%m-%d')}"
                    now = datetime.datetime.now().timestamp()
                    remaining_days = int((vip_end - now) / (24 * 3600))
                    if remaining_days > 0:
                        vip_status += f" ({remaining_days} روز)"
                else:
                    vip_status = "ندارید"
                
                coins = user.get("coins", 0)
                
                profile_text = f"<b>👤 پروفایل شما</b>\n\n"
                profile_text += f"نام: {user.get('name', 'نامشخص')}\n"
                profile_text += f"جنسیت: {user.get('sex', 'نامشخص')}\n"
                profile_text += f"سن: {user.get('age', 'نامشخص')}\n"
                profile_text += f"رنک: {rank}\n"
                profile_text += f"VIP: {vip_status}\n"
                profile_text += f"💰 سکه: {coins:,}\n"
                profile_text += f"👥 رفرال: {user.get('total_referrals', 0)} نفر\n"
                profile_text += f"⚠️ اخطار: {user.get('warns', 0)}/{self.settings.get('bot_settings', {}).get('max_warnings', 3)}\n"
                
                if user.get("christmas_vip_taken", False):
                    profile_text += f"🎄 VIP کریسمس: <b>دریافت شده ✅</b>"
                
                self.bot.send_message(uid, profile_text)
                self.check_and_reward_mission(uid)

            elif text == "📩 لینک ناشناس من":
                if not self.settings.get("features", {}).get("anonymous_messages", True):
                    self.bot.send_message(uid, "❌ سرویس پیام ناشناس موقتاً غیرفعال است")
                    return
                    
                link = f"https://t.me/{self.username}?start=msg_{uid}"
                self.bot.send_message(uid, f"<b>📩 لینک ناشناس شما</b>\n\n"
                                          f"<code>{link}</code>\n\n"
                                          "با اشتراک این لینک، دیگران می‌توانند ناشناس به شما پیام بفرستند ✨")

            elif text == "📥 پیام‌های ناشناس":
                if not self.settings.get("features", {}).get("anonymous_messages", True):
                    self.bot.send_message(uid, "❌ سرویس پیام ناشناس موقتاً غیرفعال است")
                    return
                    
                db_m = self.db.read("messages")
                inbox = db_m["inbox"].get(uid, [])
                
                if not inbox:
                    self.bot.send_message(uid, "📭 هیچ پیام ناشناسی دریافت نکرده‌اید")
                    return
                
                kb = types.InlineKeyboardMarkup()
                txt = "<b>📥 پیام‌های ناشناس شما</b>\n\n"
                
                for i, m in enumerate(inbox):
                    status = "✅" if m.get("seen") else "🔵"
                    txt += f"{status} <b>پیام {i+1}:</b>\n{m['text']}\n"
                    txt += f"<i>🕐 {m['time']}</i>\n\n"
                    kb.add(types.InlineKeyboardButton(f"📝 پاسخ به پیام {i+1}", 
                                                     callback_data=f"anon_reply_{i}"))
                
                self.bot.send_message(uid, txt, reply_markup=kb)
                
                updated = False
                for m in inbox:
                    if not m.get("seen"):
                        m["seen"] = True
                        updated = True
                        try:
                            self.bot.send_message(m["from"], "✅ پیام شما دیده شد")
                        except:
                            pass
                
                if updated:
                    self.db.write("messages", db_m)

            elif text == "🎡 گردونه شانس":
                if not self.settings.get("features", {}).get("spin_wheel_enabled", True):
                    self.bot.send_message(uid, "❌ گردونه شانس موقتاً غیرفعال است")
                    return
                    
                today = str(datetime.date.today())
                if user.get("last_spin") == today:
                    self.bot.send_message(uid, "⏰ امروز قبلاً گردونه را چرخانده‌اید\n\n"
                                              "فردا دوباره امتحان کنید! 🎡")
                    return
                
                user["last_spin"] = today
                user["daily_spin_done"] = True
                self.db.write("users", db_u)
                
                # استفاده از تنظیمات پویا برای گردونه
                wheel_rewards = self.settings.get("wheel_rewards", [])
                rand = random.random()
                cumulative = 0
                result_reward = None
                
                for reward in wheel_rewards:
                    cumulative += reward.get("probability", 0)
                    if rand <= cumulative:
                        result_reward = reward
                        break
                
                if result_reward:
                    reward_type = result_reward.get("type")
                    reward_value = result_reward.get("value")
                    reward_name = result_reward.get("name", "جایزه")
                    
                    if reward_type == "vip":
                        self.add_vip(uid, reward_value, "گردونه شانس")
                        result = f"🎉 <b>جایزه بزرگ!</b>\n\n🎖 {reward_name}\n\nتبریک! 🎊"
                    elif reward_type == "coins":
                        self.add_coins(uid, reward_value, "گردونه شانس")
                        result = f"🎁 <b>برنده شدید!</b>\n\n💰 {reward_name}\n\nآفرین! ✨"
                    else:
                        result = "😔 <b>متأسفانه پوچ!</b>\n\nشانس بعدی را امتحان کنید 🍀"
                else:
                    result = "😔 <b>متأسفانه پوچ!</b>\n\nشانس بعدی را امتحان کنید 🍀"
                
                self.bot.send_message(uid, f"🎡 گردونه در حال چرخش...\n\n{result}")
                self.check_and_reward_mission(uid)

            elif text == "🎯 ماموریت روزانه":
                if not self.settings.get("features", {}).get("missions_enabled", True):
                    self.bot.send_message(uid, "❌ سیستم ماموریت‌ها موقتاً غیرفعال است")
                    return
                    
                db_m = self.db.read("missions")
                mission = db_m["daily"]
                
                today = str(datetime.date.today())
                completed = user.get("mission_completed_date") == today
                
                mission_description = mission.get("description", self.get_mission_description(mission['type'], mission['target']))
                
                mission_text = f"<b>🎯 ماموریت روزانه</b>\n\n"
                mission_text += f"📋 ماموریت: {mission['mission']}\n"
                mission_text += f"📝 کار انجام‌دادنی: {mission_description}\n"
                
                if mission.get("reward_type") == "coins":
                    mission_text += f"🎁 پاداش: {mission.get('reward_value', mission.get('reward', 0)):,} سکه\n\n"
                elif mission.get("reward_type") == "vip":
                    duration_name = {
                        "week": "۱ هفته",
                        "month": "۱ ماه",
                        "3month": "۳ ماه",
                        "6month": "۶ ماه",
                        "year": "۱ سال"
                    }.get(mission.get("reward_value", "week"), "VIP")
                    mission_text += f"🎁 پاداش: VIP {duration_name}\n\n"
                else:
                    mission_text += f"🎁 پاداش: {mission.get('reward', 0):,} سکه\n\n"
                
                if completed:
                    mission_text += "✅ <b>تکمیل شده!</b>\n\nفردا ماموریت جدید منتظر شماست 🌟"
                else:
                    mission_type = mission['type']
                    target = mission['target']
                    
                    if mission_type == "chat_count":
                        current = user.get("daily_chat_count", 0)
                        mission_text += f"پیشرفت: {current}/{target} پیام\n"
                    elif mission_type == "unique_chats":
                        current = len(user.get("daily_unique_chats", []))
                        mission_text += f"پیشرفت: {current}/{target} چت\n"
                    elif mission_type == "referrals":
                        current = user.get("total_referrals", 0)
                        mission_text += f"پیشرفت: {current}/{target} نفر\n"
                    elif mission_type == "spin_wheel":
                        current = 1 if user.get("daily_spin_done") else 0
                        mission_text += f"پیشرفت: {'✅' if current else '❌'}\n"
                    elif mission_type == "profile_views":
                        current = user.get("daily_profile_views", 0)
                        mission_text += f"پیشرفت: {current}/{target} بار\n"
                    
                    progress = min(100, int((current / target) * 100)) if target > 0 else 0
                    mission_text += f"\n📊 {progress}% تکمیل شده"
                
                self.bot.send_message(uid, mission_text)

            elif text == "👥 رفرال و دعوت":
                if not self.settings.get("features", {}).get("referral_system", True):
                    self.bot.send_message(uid, "❌ سیستم رفرال موقتاً غیرفعال است")
                    return
                    
                ref_link = f"https://t.me/{self.username}?start=ref_{uid}"
                ref_count = user.get("total_referrals", 0)
                referral_bonus = self.settings.get("bot_settings", {}).get("referral_bonus", 100)
                
                ref_text = f"<b>👥 سیستم رفرال</b>\n\n"
                ref_text += f"🎁 به ازای هر دعوت موفق: <b>{referral_bonus} سکه</b>\n"
                ref_text += f"👤 تعداد دعوت‌های شما: <b>{ref_count} نفر</b>\n"
                ref_text += f"💰 کل سکه از رفرال: <b>{ref_count * referral_bonus:,} سکه</b>\n\n"
                ref_text += f"🔗 لینک دعوت شما:\n<code>{ref_link}</code>\n\n"
                ref_text += "این لینک را با دوستان خود به اشتراک بگذارید!"
                
                self.bot.send_message(uid, ref_text)

            elif text == "🎖 خرید VIP":
                if not self.settings.get("features", {}).get("vip_system", True):
                    self.bot.send_message(uid, "❌ سیستم VIP موقتاً غیرفعال است")
                    return
                    
                coins = user.get("coins", 0)
                
                vip_text = "<b>🎖 فروشگاه VIP</b>\n\n"
                vip_text += self.settings.get("messages", {}).get("vip_features", 
                    "✅ <b>ویژگی‌های VIP:</b>\n✅ ارسال آزاد گیف و استیکر\n✅ اولویت در بررسی گزارش‌ها\n✅ دسترسی در زمان تعمیر\n✅ نشان ویژه VIP")
                vip_text += f"\n\n💰 موجودی شما: <b>{coins:,} سکه</b>\n\n"
                
                christmas_deadline = datetime.datetime(2026, 1, 15)
                today = datetime.datetime.now()
                is_christmas_active = today < christmas_deadline
                
                kb = types.InlineKeyboardMarkup(row_width=1)
                
                vip_options = [
                    ("week", "۱ هفته"),
                    ("month", "۱ ماه"),
                    ("3month", "۳ ماه"),
                    ("6month", "۶ ماه"),
                    ("year", "۱ سال")
                ]
                
                for key, name in vip_options:
                    price = self.vip_prices_coins[key]
                    status = "✅" if coins >= price else "🔒"
                    kb.add(types.InlineKeyboardButton(
                        f"{status} VIP {name} - {price:,} سکه",
                        callback_data=f"buy_vip_{key}"
                    ))
                
                if is_christmas_active and not user.get("christmas_vip_taken", False):
                    vip_text += "🎄 <b>پیشنهاد ویژه کریسمس!</b>\n"
                    vip_text += "VIP ۳ ماهه رایگان فقط تا ۱۵ ژانویه ۲۰۲۶\n"
                    vip_text += "<i>(هر کاربر فقط یکبار می‌تواند دریافت کند)</i>\n\n"
                    
                    kb.add(types.InlineKeyboardButton(
                        f"🎁 VIP ۳ ماه رایگان (ویژه کریسمس) - ۰ سکه",
                        callback_data="buy_vip_christmas"
                    ))
                elif user.get("christmas_vip_taken", False):
                    vip_text += "🎄 <b>شما قبلاً VIP رایگان کریسمس را دریافت کرده‌اید</b>\n\n"
                
                self.bot.send_message(uid, vip_text, reply_markup=kb)

            elif text == "❓ راهنما و قوانین":
                rules_msg = self.settings.get("messages", {}).get("rules_message", 
                    "<b>📖 راهنما و قوانین</b>\n\n<b>چگونه کار می‌کند؟</b>\n• چت کاملاً ناشناس است\n• با افراد تصادفی گفتگو کنید\n• سکه جمع کنید و VIP بخرید\n\n<b>قوانین:</b>\n❌ فحاشی ممنوع\n❌ محتوای +18 ممنوع\n❌ اسپم و آزار ممنوع\n\n<b>سیستم اخطار:</b>\n• اخطار ۳: بن ۲۴ ساعته\n• تکرار پس از بن: بن دائم")
                self.bot.send_message(uid, rules_msg + f"\n\nپشتیبانی: {self.support}")

            elif text == "⚙ تنظیمات":
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add("✏️ تغییر نام", "🔢 تغییر سن")
                kb.add("⚧ تغییر جنسیت", "🔙 بازگشت به منو")
                self.bot.send_message(uid, "⚙️ تنظیمات پروفایل:", reply_markup=kb)

            elif text == "✏️ تغییر نام":
                user["state"] = "change_name"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✏️ نام جدید را وارد کنید:")

            elif text == "🔢 تغییر سن":
                user["state"] = "change_age"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🔢 سن جدید را وارد کنید (۱۲-۹۹):")

            elif text == "⚧ تغییر جنسیت":
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("آقا 👦", callback_data="change_sex_m"),
                    types.InlineKeyboardButton("خانم 👧", callback_data="change_sex_f")
                )
                self.bot.send_message(uid, "⚧ جنسیت جدید را انتخاب کنید:", reply_markup=kb)

            # پنل مدیریت پیشرفته
            if uid == self.owner:
                if text == "📊 پنل مدیریت":
                    self.bot.send_message(uid, "<b>📊 پنل مدیریت پیشرفته</b>\n\n"
                                              "با استفاده از این پنل می‌توانید تمامی تنظیمات ربات را کنترل کنید.", 
                                        reply_markup=self.kb_admin())

                elif text == "📈 آمار پیشرفته":
                    stats = self.get_statistics()
                    
                    stats_text = f"<b>📊 آمار پیشرفته ربات</b>\n\n"
                    stats_text += f"👥 کل کاربران: {stats['total_users']:,}\n"
                    stats_text += f"📅 کاربران فعال امروز: {stats['active_today']:,}\n"
                    stats_text += f"👦 کاربران مرد: {stats['male_users']:,}\n"
                    stats_text += f"👧 کاربران زن: {stats['female_users']:,}\n"
                    stats_text += f"🎖 کاربران VIP: {stats['vip_users']:,}\n"
                    stats_text += f"💰 کل سکه‌ها: {stats['total_coins']:,}\n"
                    stats_text += f"🚫 بن دائم: {stats['permanent_bans']:,}\n"
                    stats_text += f"⏰ بن موقت: {stats['temporary_bans']:,}\n"
                    stats_text += f"💬 چت‌های فعال: {stats['active_chats']:,}\n"
                    stats_text += f"⏳ کاربران در صف: {stats['queue_size']:,}"
                    
                    self.bot.send_message(uid, stats_text)

                elif text == "🔍 جستجوی کاربران":
                    user["admin_state"] = "admin_search_type"
                    self.db.write("users", db_u)
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("🆔 با آیدی", callback_data="search_id"),
                        types.InlineKeyboardButton("📝 با نام", callback_data="search_name")
                    )
                    kb.add(
                        types.InlineKeyboardButton("🔢 با سن", callback_data="search_age"),
                        types.InlineKeyboardButton("🎖 وضعیت VIP", callback_data="search_vip")
                    )
                    self.bot.send_message(uid, "🔍 نوع جستجو را انتخاب کنید:", reply_markup=kb)

                elif text == "⚙️ تنظیمات پویا":
                    self.bot.send_message(uid, "⚙️ <b>تنظیمات پویا</b>\n\n"
                                              "از طریق این منو می‌توانید تمامی تنظیمات ربات را تغییر دهید:", 
                                        reply_markup=self.kb_admin_settings())

                elif text == "📢 ارسال هدفمند":
                    user["admin_state"] = "admin_broadcast_type"
                    self.db.write("users", db_u)
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("👥 همه کاربران", callback_data="broadcast_all"),
                        types.InlineKeyboardButton("🎖 فقط VIP", callback_data="broadcast_vip")
                    )
                    kb.add(
                        types.InlineKeyboardButton("👦 فقط آقایان", callback_data="broadcast_male"),
                        types.InlineKeyboardButton("👧 فقط خانم‌ها", callback_data="broadcast_female")
                    )
                    self.bot.send_message(uid, "🎯 گروه هدف را انتخاب کنید:", reply_markup=kb)

                elif text == "🛠 مدیریت قابلیت‌ها":
                    features = self.settings.get("features", {})
                    
                    features_text = "<b>🛠 مدیریت قابلیت‌ها</b>\n\n"
                    features_text += "✅ = فعال\n❌ = غیرفعال\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    
                    feature_list = [
                        ("chat_enabled", "چت ناشناس"),
                        ("anonymous_messages", "پیام ناشناس"),
                        ("spin_wheel_enabled", "گردونه شانس"),
                        ("missions_enabled", "ماموریت‌ها"),
                        ("referral_system", "سیستم رفرال"),
                        ("vip_system", "سیستم VIP"),
                        ("ai_filter", "فیلتر AI"),
                        ("bad_words_filter", "فیلتر فحش")
                    ]
                    
                    for key, name in feature_list:
                        status = "✅" if features.get(key, True) else "❌"
                        features_text += f"{status} {name}\n"
                        kb.add(types.InlineKeyboardButton(
                            f"{'❌ غیرفعال' if features.get(key, True) else '✅ فعال'} {name}",
                            callback_data=f"toggle_feature_{key}"
                        ))
                    
                    self.bot.send_message(uid, features_text, reply_markup=kb)

                elif text == "🗣 مدیریت فحش":
                    user["admin_state"] = "admin_bad_words_action"
                    self.db.write("users", db_u)
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("📋 مشاهده لیست", callback_data="bad_words_list"),
                        types.InlineKeyboardButton("➕ اضافه کردن", callback_data="bad_words_add")
                    )
                    kb.add(
                        types.InlineKeyboardButton("➖ حذف کردن", callback_data="bad_words_remove"),
                        types.InlineKeyboardButton("📊 آمار", callback_data="bad_words_stats")
                    )
                    self.bot.send_message(uid, "🗣 <b>مدیریت کلمات فحش</b>\n\n"
                                              "تعداد کلمات فعلی: " + str(len(self.bad_words)), 
                                        reply_markup=kb)

                elif text == "📊 گزارش‌گیری":
                    user["admin_state"] = "admin_reports_type"
                    self.db.write("users", db_u)
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("📅 روزانه", callback_data="report_daily"),
                        types.InlineKeyboardButton("📆 هفتگی", callback_data="report_weekly")
                    )
                    kb.add(
                        types.InlineKeyboardButton("📈 ماهانه", callback_data="report_monthly"),
                        types.InlineKeyboardButton("💰 مالی", callback_data="report_financial")
                    )
                    self.bot.send_message(uid, "📊 <b>گزارش‌گیری</b>\n\n"
                                              "نوع گزارش مورد نظر را انتخاب کنید:", 
                                        reply_markup=kb)

                elif text == "🔄 مدیریت خودکار":
                    auto_settings = self.settings.get("bot_settings", {})
                    
                    auto_text = "<b>🔄 مدیریت سیستم‌های خودکار</b>\n\n"
                    auto_text += f"🔄 ریست روزانه: ساعت {auto_settings.get('daily_reset_hour', 0)}:00\n"
                    auto_text += f"💾 پشتیبان‌گیری خودکار: {'✅ فعال' if auto_settings.get('auto_backup', True) else '❌ غیرفعال'}\n"
                    auto_text += f"⏰ فاصله پشتیبان‌گیری: هر {auto_settings.get('backup_interval_hours', 24)} ساعت\n"
                    auto_text += f"💬 محدودیت پیام: {auto_settings.get('max_messages_per_user', 1000)} پیام\n"
                    auto_text += f"⏳ تایم‌اوت چت: {auto_settings.get('chat_timeout_minutes', 30)} دقیقه\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("🕐 تغییر ساعت ریست", callback_data="change_reset_hour"),
                        types.InlineKeyboardButton("💾 تنظیم پشتیبان", callback_data="configure_backup")
                    )
                    kb.add(
                        types.InlineKeyboardButton("📝 تغییر محدودیت‌ها", callback_data="change_limits"),
                        types.InlineKeyboardButton("🔄 ریست دستی", callback_data="manual_reset")
                    )
                    
                    self.bot.send_message(uid, auto_text, reply_markup=kb)

                elif text == "🎭 مدیریت قالب‌ها":
                    templates = self.db.read("templates")
                    
                    templates_text = "<b>🎭 مدیریت قالب‌ها</b>\n\n"
                    templates_text += f"📢 قالب‌های پیام: {len(templates.get('broadcast_templates', []))}\n"
                    templates_text += f"🎛 قالب‌های دکمه: {len(templates.get('button_templates', {}))}\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("📝 مدیریت پیام‌ها", callback_data="manage_message_templates"),
                        types.InlineKeyboardButton("🎛 مدیریت دکمه‌ها", callback_data="manage_button_templates")
                    )
                    kb.add(
                        types.InlineKeyboardButton("➕ افزودن قالب جدید", callback_data="add_new_template"),
                        types.InlineKeyboardButton("📋 مشاهده همه", callback_data="view_all_templates")
                    )
                    
                    self.bot.send_message(uid, templates_text, reply_markup=kb)

                elif text == "💾 پشتیبان‌گیری":
                    self.create_backup()
                    self.bot.send_message(uid, "✅ پشتیبان‌گیری انجام شد.\n"
                                              "فایل‌ها در پوشه backups ذخیره شدند.")

                elif text == "📋 لیست VIP":
                    active_vips = [u for u in db_u["users"] if self.is_vip(u)]
                    
                    if not active_vips:
                        self.bot.send_message(uid, "❌ هیچ کاربر VIP فعال وجود ندارد")
                    else:
                        vip_text = "<b>📋 لیست کاربران VIP فعال</b>\n\n"
                        for v in active_vips[:30]:
                            name = db_u["users"][v].get("name", "نامشخص")
                            end_date = datetime.datetime.fromtimestamp(
                                db_u["users"][v].get("vip_end", 0)
                            ).strftime("%Y-%m-%d")
                            
                            now = datetime.datetime.now().timestamp()
                            remaining_days = int((db_u["users"][v].get("vip_end", 0) - now) / (24 * 3600))
                            
                            vip_text += f"🆔 <code>{v}</code> - {name}\n📅 تا {end_date} ({remaining_days} روز)\n\n"
                        
                        if len(active_vips) > 30:
                            vip_text += f"\n... و {len(active_vips) - 30} نفر دیگر"
                        
                        self.bot.send_message(uid, vip_text)

                elif text == "💰 مدیریت اقتصادی":
                    economic_text = "<b>💰 مدیریت اقتصادی ربات</b>\n\n"
                    economic_text += f"💰 کل سکه‌ها: {sum(u.get('coins', 0) for u in db_u['users'].values()):,}\n"
                    economic_text += f"🎖 قیمت VIP هفته: {self.vip_prices_coins.get('week', 500):,} سکه\n"
                    economic_text += f"🎖 قیمت VIP ماه: {self.vip_prices_coins.get('month', 1800):,} سکه\n"
                    economic_text += f"🎁 پاداش ثبت‌نام: {self.settings.get('bot_settings', {}).get('welcome_bonus', 50):,} سکه\n"
                    economic_text += f"👥 پاداش رفرال: {self.settings.get('bot_settings', {}).get('referral_bonus', 100):,} سکه\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("💰 تغییر قیمت VIP", callback_data="change_vip_prices"),
                        types.InlineKeyboardButton("🎁 تغییر پاداش‌ها", callback_data="change_rewards")
                    )
                    kb.add(
                        types.InlineKeyboardButton("📈 گزارش مالی", callback_data="financial_report"),
                        types.InlineKeyboardButton("💸 تخفیف ویژه", callback_data="special_discount")
                    )
                    
                    self.bot.send_message(uid, economic_text, reply_markup=kb)

                elif text == "🎯 مدیریت ماموریت‌ها":
                    db_m = self.db.read("missions")
                    current_mission = db_m["daily"]
                    
                    mission_text = f"<b>🎯 مدیریت ماموریت‌های روزانه</b>\n\n"
                    mission_text += f"<b>ماموریت امروز:</b>\n"
                    mission_text += f"📋 {current_mission['mission']}\n"
                    mission_text += f"📝 کار: {current_mission.get('description', self.get_mission_description(current_mission['type'], current_mission['target']))}\n"
                    
                    if current_mission.get("reward_type") == "coins":
                        mission_text += f"🎁 پاداش: {current_mission.get('reward_value', current_mission.get('reward', 0)):,} سکه\n"
                    elif current_mission.get("reward_type") == "vip":
                        duration_name = {
                            "week": "۱ هفته",
                            "month": "۱ ماه",
                            "3month": "۳ ماه",
                            "6month": "۶ ماه",
                            "year": "۱ سال"
                        }.get(current_mission.get("reward_value", "week"), "VIP")
                        mission_text += f"🎁 پاداش: VIP {duration_name}\n"
                    else:
                        mission_text += f"🎁 پاداش: {current_mission.get('reward', 0):,} سکه\n"
                    
                    mission_text += f"📅 تاریخ: {current_mission['date']}\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=1)
                    kb.add(types.InlineKeyboardButton("🔄 تغییر ماموریت امروز", 
                                                     callback_data="change_daily_mission"))
                    kb.add(types.InlineKeyboardButton("📋 مشاهده لیست ماموریت‌ها", 
                                                     callback_data="view_missions_list"))
                    kb.add(types.InlineKeyboardButton("➕ افزودن ماموریت جدید", 
                                                     callback_data="add_new_mission"))
                    kb.add(types.InlineKeyboardButton("📊 آمار ماموریت‌ها", 
                                                     callback_data="mission_stats"))
                    
                    self.bot.send_message(uid, mission_text, reply_markup=kb)

                elif text == "🚫 مدیریت بن‌ها":
                    db_b = self.db.read("bans")
                    ban_text = "<b>🚫 مدیریت بن‌ها</b>\n\n"
                    
                    if db_b.get("permanent"):
                        ban_text += "<b>بن دائم:</b>\n"
                        for ban_uid, reason in list(db_b["permanent"].items())[:10]:
                            name = db_u["users"].get(ban_uid, {}).get("name", "نامشخص")
                            ban_text += f"🆔 <code>{ban_uid}</code> - {name}\n💬 {reason}\n"
                    else:
                        ban_text += "✅ هیچ بن دائم‌ای وجود ندارد\n"
                    
                    ban_text += "\n"
                    
                    if db_b.get("temporary"):
                        ban_text += "<b>بن موقت:</b>\n"
                        for ban_uid, data in list(db_b["temporary"].items())[:10]:
                            name = db_u["users"].get(ban_uid, {}).get("name", "نامشخص")
                            end_time = datetime.datetime.fromtimestamp(data["end"]).strftime("%Y-%m-%d %H:%M")
                            ban_text += f"🆔 <code>{ban_uid}</code> - {name}\n⏰ تا {end_time}\n"
                    else:
                        ban_text += "✅ هیچ بن موقتی وجود ندارد"
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("🔍 جستجوی بن‌ها", callback_data="search_bans"),
                        types.InlineKeyboardButton("📋 گزارش بن‌ها", callback_data="ban_report")
                    )
                    kb.add(
                        types.InlineKeyboardButton("⚙ تنظیمات بن", callback_data="ban_settings"),
                        types.InlineKeyboardButton("🔄 ریست اخطارها", callback_data="reset_warnings")
                    )
                    
                    self.bot.send_message(uid, ban_text, reply_markup=kb)

                elif text == "⚠️ هشدار تعمیر":
                    if self.maintenance_warning_active:
                        kb = types.InlineKeyboardMarkup()
                        kb.add(
                            types.InlineKeyboardButton("⛔ لغو هشدار", callback_data="cancel_maintenance_warning"),
                            types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_no")
                        )
                        self.bot.send_message(uid, "⚠️ <b>هشدار تعمیر در حال اجراست!</b>\n\n"
                                                  "آیا می‌خواهید هشدار را لغو کنید؟", 
                                            reply_markup=kb)
                    else:
                        kb = types.InlineKeyboardMarkup()
                        kb.add(
                            types.InlineKeyboardButton("✅ بله، شروع کن", callback_data="start_maintenance_warning"),
                            types.InlineKeyboardButton("❌ خیر، لغو کن", callback_data="cancel_maintenance")
                        )
                        self.bot.send_message(uid, "⚠️ <b>هشدار تعمیر و نگهداری</b>\n\n"
                                                  "با شروع هشدار:\n"
                                                  "• هر 30 ثانیه پیام هشدار ارسال می‌شود\n"
                                                  "• بعد از 3 دقیقه ربات به حالت تعمیر می‌رود\n"
                                                  "• کاربران VIP همچنان دسترسی خواهند داشت\n\n"
                                                  "آیا مطمئن هستید؟", 
                                            reply_markup=kb)

                # مدیریت state های ادمین پیشرفته
                admin_state = user.get("admin_state")
                
                # Stateهای جستجو
                if admin_state == "admin_search_type":
                    if text == "آیدی":
                        user["admin_state"] = "admin_search_id"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "🆔 آیدی کاربر را وارد کنید:")
                    elif text == "نام":
                        user["admin_state"] = "admin_search_name"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 نام کاربر را وارد کنید:")
                    elif text == "سن":
                        user["admin_state"] = "admin_search_age"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "🔢 سن مورد نظر را وارد کنید:")
                    elif text == "VIP":
                        user["admin_state"] = "admin_search_vip"
                        self.db.write("users", db_u)
                        
                        kb = types.InlineKeyboardMarkup(row_width=2)
                        kb.add(
                            types.InlineKeyboardButton("✅ VIP ها", callback_data="search_vip_true"),
                            types.InlineKeyboardButton("❌ غیر VIP", callback_data="search_vip_false")
                        )
                        self.bot.send_message(uid, "🎖 وضعیت VIP را انتخاب کنید:", reply_markup=kb)
                
                elif admin_state == "admin_search_id":
                    results = self.search_users(text, "id")
                    self.display_search_results(uid, results, f"نتایج جستجو برای آیدی: {text}")
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                elif admin_state == "admin_search_name":
                    results = self.search_users(text, "name")
                    self.display_search_results(uid, results, f"نتایج جستجو برای نام: {text}")
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                elif admin_state == "admin_search_age":
                    results = self.search_users(text, "age")
                    self.display_search_results(uid, results, f"نتایج جستجو برای سن: {text}")
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                # Stateهای ارسال هدفمند
                elif admin_state == "admin_broadcast_type":
                    if text == "همه کاربران":
                        user["broadcast_target"] = "all"
                        user["admin_state"] = "admin_broadcast_message"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 متن پیام همگانی را وارد کنید:")
                    elif text == "فقط VIP":
                        user["broadcast_target"] = "vip"
                        user["admin_state"] = "admin_broadcast_message"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 متن پیام برای کاربران VIP را وارد کنید:")
                    elif text == "فقط آقایان":
                        user["broadcast_target"] = "male"
                        user["admin_state"] = "admin_broadcast_message"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 متن پیام برای آقایان را وارد کنید:")
                    elif text == "فقط خانم‌ها":
                        user["broadcast_target"] = "female"
                        user["admin_state"] = "admin_broadcast_message"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 متن پیام برای خانم‌ها را وارد کنید:")
                
                elif admin_state == "admin_broadcast_message":
                    target_type = user.get("broadcast_target", "all")
                    db_u_all = self.db.read("users")
                    
                    # انتخاب کاربران بر اساس نوع
                    if target_type == "all":
                        user_ids = list(db_u_all["users"].keys())
                        target_name = "همه کاربران"
                    elif target_type == "vip":
                        user_ids = [uid_key for uid_key in db_u_all["users"] if self.is_vip(uid_key)]
                        target_name = "کاربران VIP"
                    elif target_type == "male":
                        user_ids = [uid_key for uid_key, u in db_u_all["users"].items() if u.get("sex") == "آقا"]
                        target_name = "آقایان"
                    elif target_type == "female":
                        user_ids = [uid_key for uid_key, u in db_u_all["users"].items() if u.get("sex") == "خانم"]
                        target_name = "خانم‌ها"
                    else:
                        user_ids = []
                        target_name = "نامشخص"
                    
                    # تأیید ارسال
                    kb = types.InlineKeyboardMarkup()
                    kb.add(
                        types.InlineKeyboardButton("✅ تأیید و ارسال", callback_data=f"confirm_broadcast_{target_type}"),
                        types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_broadcast")
                    )
                    
                    preview_text = f"📢 <b>پیش‌نمایش پیام همگانی</b>\n\n"
                    preview_text += f"🎯 گروه هدف: {target_name}\n"
                    preview_text += f"👥 تعداد کاربران: {len(user_ids):,} نفر\n\n"
                    preview_text += f"📝 متن پیام:\n{text}\n\n"
                    preview_text += "آیا از ارسال این پیام اطمینان دارید؟"
                    
                    user["broadcast_message"] = text
                    self.db.write("users", db_u)
                    
                    self.bot.send_message(uid, preview_text, reply_markup=kb)
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                # Stateهای مدیریت فحش
                elif admin_state == "admin_bad_words_action":
                    if text == "مشاهده لیست":
                        bad_words_list = self.manage_bad_words("list")
                        words_text = "<b>📋 لیست کلمات فحش</b>\n\n"
                        words_text += f"تعداد: {len(bad_words_list)} کلمه\n\n"
                        
                        # نمایش کلمات در گروه‌های 10 تایی
                        for i in range(0, len(bad_words_list), 10):
                            chunk = bad_words_list[i:i+10]
                            words_text += f"{', '.join(chunk)}\n\n"
                        
                        self.bot.send_message(uid, words_text)
                        user["admin_state"] = None
                        self.db.write("users", db_u)
                    
                    elif text == "اضافه کردن":
                        user["admin_state"] = "admin_bad_words_add"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "➕ کلمه جدید را وارد کنید:")
                    
                    elif text == "حذف کردن":
                        user["admin_state"] = "admin_bad_words_remove"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "➖ کلمه مورد نظر برای حذف را وارد کنید:")
                    
                    elif text == "آمار":
                        bad_words_list = self.manage_bad_words("list")
                        stats_text = "<b>📊 آمار کلمات فحش</b>\n\n"
                        stats_text += f"📊 تعداد کل کلمات: {len(bad_words_list)}\n"
                        stats_text += f"📈 بیشترین استفاده: در حال پیگیری...\n"
                        stats_text += f"🔄 آخرین بروزرسانی: همین الان\n\n"
                        
                        kb = types.InlineKeyboardMarkup()
                        kb.add(types.InlineKeyboardButton("📥 خروجی CSV", callback_data="export_bad_words"))
                        
                        self.bot.send_message(uid, stats_text, reply_markup=kb)
                        user["admin_state"] = None
                        self.db.write("users", db_u)
                
                elif admin_state == "admin_bad_words_add":
                    if self.manage_bad_words("add", text):
                        self.bot.send_message(uid, f"✅ کلمه '{text}' به لیست اضافه شد")
                    else:
                        self.bot.send_message(uid, f"⚠️ کلمه '{text}' از قبل در لیست وجود دارد")
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                elif admin_state == "admin_bad_words_remove":
                    if self.manage_bad_words("remove", text):
                        self.bot.send_message(uid, f"✅ کلمه '{text}' از لیست حذف شد")
                    else:
                        self.bot.send_message(uid, f"❌ کلمه '{text}' در لیست وجود ندارد")
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                # Stateهای گزارش‌گیری
                elif admin_state == "admin_reports_type":
                    if text == "روزانه":
                        self.generate_daily_report(uid)
                    elif text == "هفتگی":
                        self.generate_weekly_report(uid)
                    elif text == "ماهانه":
                        self.generate_monthly_report(uid)
                    elif text == "مالی":
                        self.generate_financial_report(uid)
                    
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                # Stateهای قدیمی (برای سازگاری)
                elif admin_state == "gift_vip_duration":
                    duration_map = {
                        "۱ هفته": "week",
                        "۱ ماه": "month",
                        "۳ ماه": "3month",
                        "۶ ماه": "6month",
                        "۱ سال": "year"
                    }
                    
                    if text in duration_map:
                        user["gift_vip_duration"] = duration_map[text]
                        user["admin_state"] = "gift_vip_reason"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 دلیل گیفت VIP را بنویسید:")
                    return

                elif admin_state == "gift_vip_reason":
                    user["gift_vip_reason"] = msg.text
                    user["admin_state"] = "gift_vip_id"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی عددی کاربر را وارد کنید:")
                    return

                elif admin_state == "gift_vip_id":
                    if msg.text.isdigit():
                        target_uid = msg.text
                        duration = user.get("gift_vip_duration")
                        reason = user.get("gift_vip_reason", "گیفت ادمین")
                        
                        if target_uid in db_u["users"]:
                            success = self.add_vip(target_uid, duration, reason)
                            if success:
                                self.bot.send_message(uid, f"✅ گیفت VIP به {target_uid} ارسال شد", 
                                                    reply_markup=self.kb_admin())
                            else:
                                self.bot.send_message(uid, "❌ خطا در ارسال گیفت")
                        else:
                            self.bot.send_message(uid, "❌ کاربر پیدا نشد")
                        
                        user["admin_state"] = None
                        self.db.write("users", db_u)
                    return

                elif admin_state == "gift_coins_amount":
                    if msg.text.isdigit():
                        user["gift_coins_amount"] = int(msg.text)
                        user["admin_state"] = "gift_coins_reason"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 دلیل اهدا سکه را بنویسید:")
                    else:
                        self.bot.send_message(uid, "❌ لطفاً عدد وارد کنید")
                    return

                elif admin_state == "gift_coins_reason":
                    user["gift_coins_reason"] = msg.text
                    user["admin_state"] = "gift_coins_id"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی عددی کاربر را وارد کنید:")
                    return

                elif admin_state == "gift_coins_id":
                    if msg.text.isdigit():
                        target_uid = msg.text
                        amount = user.get("gift_coins_amount", 0)
                        reason = user.get("gift_coins_reason", "هدیه ادمین")
                        
                        if target_uid in db_u["users"]:
                            success = self.add_coins(target_uid, amount, reason)
                            if success:
                                db_u = self.db.read("users")
                                user = db_u["users"].get(uid)
                                self.bot.send_message(uid, f"✅ {amount:,} سکه به {target_uid} اهدا شد\n"
                                                         f"موجودی جدید کاربر: {db_u['users'][target_uid].get('coins', 0):,} سکه", 
                                                    reply_markup=self.kb_admin())
                            else:
                                self.bot.send_message(uid, "❌ خطا در اهدا سکه")
                        else:
                            self.bot.send_message(uid, "❌ کاربر پیدا نشد")
                        
                        user["admin_state"] = None
                        self.db.write("users", db_u)
                    return

            # بازگشت به منو
            if "بازگشت" in text or text == "🔙 بازگشت به منو":
                user["state"] = "idle"
                user["admin_state"] = None
                
                keys_to_delete = [
                    "add_mission_reward_type", "add_mission_vip_duration",
                    "add_mission_coins_amount", "add_mission_title",
                    "add_mission_type", "add_mission_target"
                ]
                for key in keys_to_delete:
                    if key in user:
                        del user[key]
                
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🏠 منوی اصلی", reply_markup=self.kb_main(uid))

        # ==========================================
        # 🔘 کال‌بک‌های پیشرفته
        # ==========================================
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            uid = str(call.from_user.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            
            if not user:
                self.bot.answer_callback_query(call.id, "❌ خطا: کاربر یافت نشد")
                return

            # انتخاب جنسیت
            if call.data.startswith("sex_"):
                user["sex"] = "آقا" if call.data == "sex_m" else "خانم"
                user["state"] = "age"
                self.db.write("users", db_u)
                self.bot.edit_message_text("✅ جنسیت ثبت شد", call.message.chat.id, call.message.message_id)
                self.bot.send_message(uid, "🔢 سن خود را وارد کنید (۱۲-۹۹):")

            # تغییر جنسیت
            elif call.data.startswith("change_sex_"):
                user["sex"] = "آقا" if call.data == "change_sex_m" else "خانم"
                self.db.write("users", db_u)
                self.bot.edit_message_text("✅ جنسیت تغییر کرد", call.message.chat.id, call.message.message_id)
                self.bot.send_message(uid, "✅ جنسیت با موفقیت تغییر کرد", reply_markup=self.kb_main(uid))

            # جستجوی چت
            elif call.data.startswith("find_"):
                search_gender = call.data.split("_")[1]
                user["search_gender"] = search_gender
                self.db.write("users", db_u)

                self.bot.edit_message_text("🔍 در حال جستجو برای هم‌صحبت...", 
                                          call.message.chat.id, call.message.message_id)
                
                kb_cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
                kb_cancel.add("❌ لغو جستجو")
                self.bot.send_message(uid, "⏳ منتظر بمانید...", reply_markup=kb_cancel)

                db_q = self.db.read("queue")
                if "general" not in db_q:
                    db_q["general"] = []
                
                if uid not in db_q["general"]:
                    db_q["general"].append(uid)
                    self.db.write("queue", db_q)

                potential_partners = [p for p in db_q["general"] if p != uid]
                
                potential_partners = [
                    p for p in potential_partners 
                    if uid not in db_u["users"].get(p, {}).get("blocks", []) 
                    and p not in user.get("blocks", [])
                ]

                valid_partners = []
                for p in potential_partners:
                    partner_sex = db_u["users"].get(p, {}).get("sex")
                    if search_gender == "any":
                        valid_partners.append(p)
                    elif search_gender == "m" and partner_sex == "آقا":
                        valid_partners.append(p)
                    elif search_gender == "f" and partner_sex == "خانم":
                        valid_partners.append(p)

                if valid_partners:
                    partner = random.choice(valid_partners)
                    
                    if uid in db_q["general"]:
                        db_q["general"].remove(uid)
                    if partner in db_q["general"]:
                        db_q["general"].remove(partner)
                    self.db.write("queue", db_q)

                    user["partner"] = partner
                    db_u["users"][partner]["partner"] = uid
                    self.db.write("users", db_u)
                    
                    self.save_active_chat(uid, partner)
                    self.save_active_chat(partner, uid)

                    self.bot.send_message(uid, "✅ هم‌صحبت پیدا شد! چت را شروع کنید 💬", 
                                        reply_markup=self.kb_chatting())
                    self.bot.send_message(partner, "✅ هم‌صحبت پیدا شد! چت را شروع کنید 💬", 
                                        reply_markup=self.kb_chatting())

            # پایان چت
            elif call.data == "end_yes":
                partner = user.get("partner")
                if partner:
                    self.end_chat(uid, partner, "پایان داد")
                self.bot.answer_callback_query(call.id, "چت پایان یافت")

            elif call.data == "end_no":
                self.bot.answer_callback_query(call.id, "✅ چت ادامه دارد")

            # اشتراک آیدی
            elif call.data.startswith("id_share_yes_"):
                requester = call.data.split("_")[3]
                username = call.from_user.username or "ندارد"
                user_id = call.from_user.id
                
                share_text = f"<b>👤 اطلاعات هم‌صحبت:</b>\n\n"
                if username != "ندارد":
                    share_text += f"یوزرنیم: @{username}\n"
                share_text += f"آیدی: <code>{user_id}</code>"
                
                self.bot.send_message(requester, share_text)
                self.bot.answer_callback_query(call.id, "✅ اطلاعات ارسال شد")

            elif call.data == "id_share_no":
                self.bot.answer_callback_query(call.id, "❌ درخواست رد شد")

            # پاسخ به پیام ناشناس
            elif call.data.startswith("anon_reply_"):
                msg_index = int(call.data.split("_")[2])
                db_m = self.db.read("messages")
                inbox = db_m["inbox"].get(uid, [])
                
                if msg_index < len(inbox):
                    msg_data = inbox[msg_index]
                    user["state"] = "anon_reply"
                    user["anon_reply_target"] = msg_data["from"]
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "📝 پاسخ خود را بنویسید:")
                    self.bot.answer_callback_query(call.id, "✅ پاسخ دهید")

            # گزارش تخلف
            elif call.data.startswith("rep_"):
                if call.data == "rep_cancel":
                    self.bot.answer_callback_query(call.id, "✅ گزارش لغو شد")
                    return
                
                reasons = {
                    "rep_insult": "فحاشی",
                    "rep_nsfw": "محتوای +18",
                    "rep_spam": "اسپم",
                    "rep_harass": "آزار و اذیت"
                }
                
                reason = reasons.get(call.data, "نامشخص")
                target = user.get("report_target")
                
                if not target:
                    self.bot.answer_callback_query(call.id, "❌ خطا در گزارش")
                    return
                
                target_name = db_u["users"].get(target, {}).get("name", "نامشخص")
                reporter_name = user.get("name", "نامشخص")
                
                tehran_time = datetime.datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-d %H:%M")
                
                report_text = f"🚩 <b>گزارش جدید</b>\n\n"
                report_text += f"<b>شاکی:</b> 🆔 <code>{uid}</code> - {reporter_name}\n"
                report_text += f"<b>متهم:</b> 🆔 <code>{target}</code> - {target_name}\n"
                report_text += f"<b>دلیل:</b> {reason}\n"
                report_text += f"<b>زمان:</b> {tehran_time}\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("Ignore", callback_data=f"adm_ignore_{target}"),
                    types.InlineKeyboardButton("Permanent Ban", callback_data=f"adm_ban_perm_{target}")
                )
                kb.add(
                    types.InlineKeyboardButton("Temp Ban", callback_data=f"adm_ban_temp_{target}"),
                    types.InlineKeyboardButton("Warning +1", callback_data=f"adm_warn1_{target}")
                )
                kb.add(
                    types.InlineKeyboardButton("Warning +2", callback_data=f"adm_warn2_{target}")
                )
                
                try:
                    self.bot.send_message(self.owner, report_text, reply_markup=kb)
                    self.bot.answer_callback_query(call.id, "✅ گزارش ارسال شد")
                except Exception as e:
                    logger.error(f"خطا در ارسال گزارش: {e}")
                    self.bot.answer_callback_query(call.id, "❌ خطا در ارسال گزارش")

            # اقدامات ادمین
            elif call.data.startswith("adm_"):
                if uid != self.owner:
                    self.bot.answer_callback_query(call.id, "❌ فقط ادمین")
                    return
                
                parts = call.data.split("_")
                action = parts[1]
                
                if action == "ignore":
                    self.bot.answer_callback_query(call.id, "✅ Ignored")
                    self.bot.edit_message_text(call.message.text + "\n\n✅ <b>Ignored</b>", 
                                              call.message.chat.id, call.message.message_id)

                elif action == "ban":
                    ban_type = parts[2]
                    target = parts[3]
                    
                    if ban_type == "perm":
                        self.ban_perm(target, "گزارش تأیید شده")
                        self.bot.answer_callback_query(call.id, "✅ بن دائم اعمال شد")
                        self.bot.edit_message_text(call.message.text + "\n\n🚫 <b>Permanent Ban</b>", 
                                                  call.message.chat.id, call.message.message_id)
                    
                    elif ban_type == "temp":
                        user["admin_temp_ban_target"] = target
                        user["admin_state"] = "admin_temp_ban_minutes"
                        self.db.write("users", db_u)
                        self.bot.send_message(self.owner, f"⏰ دقیقه بن موقت برای {target}:")
                        self.bot.answer_callback_query(call.id, "وارد کنید")

                elif action.startswith("warn"):
                    warns_count = 1 if action == "warn1" else 2
                    target = parts[2]
                    
                    if target in db_u["users"]:
                        db_u["users"][target]["warns"] = db_u["users"][target].get("warns", 0) + warns_count
                        self.db.write("users", db_u)
                        
                        try:
                            self.bot.send_message(target, f"⚠️ {warns_count} اخطار از ادمین دریافت کردید!")
                        except:
                            pass
                        
                        self.bot.answer_callback_query(call.id, f"✅ {warns_count} اخطار اعمال شد")
                        self.bot.edit_message_text(call.message.text + f"\n\n⚠️ <b>+{warns_count} Warning</b>", 
                                                  call.message.chat.id, call.message.message_id)

            # بخشیدن بن خودکار
            elif call.data.startswith("auto_ban_correct_"):
                if uid != self.owner:
                    return
                self.bot.answer_callback_query(call.id, "✅ تأیید شد")
                self.bot.edit_message_text(call.message.text + "\n\n✅ <b>Confirmed by admin</b>", 
                                          call.message.chat.id, call.message.message_id)

            elif call.data.startswith("auto_ban_pardon_"):
                if uid != self.owner:
                    return
                
                target = call.data.split("_")[3]
                db_b = self.db.read("bans")
                
                if target in db_b.get("permanent", {}):
                    del db_b["permanent"][target]
                if target in db_b.get("temporary", {}):
                    del db_b["temporary"][target]
                self.db.write("bans", db_b)
                
                if target in db_u["users"]:
                    db_u["users"][target]["warns"] = 0
                    db_u["users"][target]["had_temp_ban"] = False
                    self.db.write("users", db_u)
                
                try:
                    self.bot.send_message(target, "🌟 حساب شما توسط ادمین از بن خارج شد")
                except:
                    pass
                
                self.bot.answer_callback_query(call.id, "✅ بخشیده شد")
                self.bot.edit_message_text(call.message.text + "\n\n🌟 <b>Pardoned by admin</b>", 
                                          call.message.chat.id, call.message.message_id)

            # بخشیدن بن دائم
            elif call.data.startswith("unban_perm_"):
                if uid != self.owner:
                    return
                
                target = call.data.split("_")[2]
                db_b = self.db.read("bans")
                
                if target in db_b.get("permanent", {}):
                    del db_b["permanent"][target]
                    self.db.write("bans", db_b)
                    
                    try:
                        self.bot.send_message(target, "🌟 حساب شما از بن دائم خارج شد")
                    except:
                        pass
                    
                    self.bot.answer_callback_query(call.id, "✅ بخشیده شد")

            # خرید VIP با سکه
            elif call.data.startswith("buy_vip_"):
                vip_type = call.data.split("_")[2]
                
                if vip_type == "christmas":
                    christmas_deadline = datetime.datetime(2026, 1, 15)
                    today = datetime.datetime.now()
                    
                    if today >= christmas_deadline:
                        self.bot.answer_callback_query(call.id, "❌ مهلت دریافت VIP رایگان کریسمس به پایان رسیده!", show_alert=True)
                        return
                    
                    if user.get("christmas_vip_taken", False):
                        self.bot.answer_callback_query(call.id, "❌ شما قبلاً VIP رایگان کریسمس را دریافت کرده‌اید! هر کاربر فقط یکبار می‌تواند دریافت کند.", show_alert=True)
                        return
                    
                    self.add_vip(uid, "christmas", "هدیه کریسمس")
                    self.bot.answer_callback_query(call.id, "✅ VIP رایگان کریسمس فعال شد!")
                    return
                
                price = self.vip_prices_coins.get(vip_type, 0)
                coins = user.get("coins", 0)
                
                if coins < price:
                    self.bot.answer_callback_query(call.id, f"❌ سکه کافی ندارید! نیاز: {price:,}", show_alert=True)
                    return
                
                user["coins"] = coins - price
                self.db.write("users", db_u)
                
                reason_map = {
                    "week": "خرید با سکه",
                    "month": "خرید با سکه", 
                    "3month": "خرید با سکه",
                    "6month": "خرید با سکه",
                    "year": "خرید با سکه"
                }
                
                self.add_vip(uid, vip_type, reason_map.get(vip_type, "خرید با سکه"))
                self.bot.answer_callback_query(call.id, "✅ VIP فعال شد!")

            # مدیریت ماموریت‌ها
            elif call.data == "change_daily_mission":
                if uid != self.owner:
                    return
                
                db_m = self.db.read("missions")
                kb = types.InlineKeyboardMarkup(row_width=1)
                
                for i, mission in enumerate(db_m["available"]):
                    reward_text = ""
                    if mission.get("reward_type") == "coins":
                        reward_text = f"{mission.get('reward_value', mission.get('reward', 0)):,} سکه"
                    elif mission.get("reward_type") == "vip":
                        duration_name = {
                            "week": "۱ هفته",
                            "month": "۱ ماه",
                            "3month": "۳ ماه",
                            "6month": "۶ ماه",
                            "year": "۱ سال"
                        }.get(mission.get("reward_value", "week"), "VIP")
                        reward_text = f"VIP {duration_name}"
                    else:
                        reward_text = f"{mission.get('reward', 0):,} سکه"
                    
                    kb.add(types.InlineKeyboardButton(
                        f"{i+1}. {mission['name']} - {reward_text}",
                        callback_data=f"select_mission_{i}"
                    ))
                
                self.bot.edit_message_text("📋 لطفا ماموریت روزانه جدید را انتخاب کنید:", 
                                          call.message.chat.id, call.message.message_id, 
                                          reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data.startswith("select_mission_"):
                if uid != self.owner:
                    return
                
                index = int(call.data.split("_")[2])
                db_m = self.db.read("missions")
                
                if index < len(db_m["available"]):
                    mission = db_m["available"][index]
                    db_m["daily"] = {
                        "date": str(datetime.date.today()),
                        "mission": mission["name"],
                        "reward_type": mission.get("reward_type", "coins"),
                        "reward_value": mission.get("reward_value", mission.get("reward", 50)),
                        "type": mission["type"],
                        "target": mission["target"],
                        "description": mission.get("description", self.get_mission_description(mission["type"], mission["target"]))
                    }
                    self.db.write("missions", db_m)
                    
                    reward_text = ""
                    if mission.get("reward_type") == "coins":
                        reward_text = f"{mission.get('reward_value', mission.get('reward', 0)):,} سکه"
                    elif mission.get("reward_type") == "vip":
                        duration_name = {
                            "week": "۱ هفته",
                            "month": "۱ ماه",
                            "3month": "۳ ماه",
                            "6month": "۶ ماه",
                            "year": "۱ سال"
                        }.get(mission.get("reward_value", "week"), "VIP")
                        reward_text = f"VIP {duration_name}"
                    
                    self.bot.edit_message_text(f"✅ ماموریت روزانه به '{mission['name']}' تغییر کرد.\n\n"
                                              f"کار انجام‌دادنی: {mission.get('description', self.get_mission_description(mission['type'], mission['target']))}\n"
                                              f"پاداش: {reward_text}", 
                                              call.message.chat.id, call.message.message_id)
                    self.bot.answer_callback_query(call.id, "✅")

            elif call.data == "view_missions_list":
                if uid != self.owner:
                    return
                
                db_m = self.db.read("missions")
                missions_text = "<b>📋 لیست کامل ماموریت‌ها</b>\n\n"
                
                for i, m in enumerate(db_m["available"], 1):
                    missions_text += f"<b>{i}. {m['name']}</b>\n"
                    
                    if m.get("reward_type") == "coins":
                        missions_text += f"   🎁 پاداش: {m.get('reward_value', m.get('reward', 0)):,} سکه\n"
                    elif m.get("reward_type") == "vip":
                        duration_name = {
                            "week": "۱ هفته",
                            "month": "۱ ماه",
                            "3month": "۳ ماه",
                            "6month": "۶ ماه",
                            "year": "۱ سال"
                        }.get(m.get("reward_value", "week"), "VIP")
                        missions_text += f"   🎖 پاداش: VIP {duration_name}\n"
                    else:
                        missions_text += f"   🎁 پاداش: {m.get('reward', 0):,} سکه\n"
                    
                    missions_text += f"   📝 کار: {m.get('description', self.get_mission_description(m['type'], m['target']))}\n"
                    missions_text += f"   🎯 نوع: {m['type']}\n"
                    missions_text += f"   🎯 هدف: {m['target']}\n\n"
                
                self.bot.send_message(uid, missions_text)
                self.bot.answer_callback_query(call.id, "✅ لیست ارسال شد")

            elif call.data == "add_new_mission":
                if uid != self.owner:
                    return
                
                user["admin_state"] = "add_mission_reward_type"
                self.db.write("users", db_u)
                
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add("🎖 VIP", "💰 سکه", "🔙 بازگشت")
                
                self.bot.send_message(uid, "🎯 <b>افزودن ماموریت جدید</b>\n\n"
                                          "نوع پاداش ماموریت را انتخاب کنید:", 
                                    reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data.startswith("extend_ban_"):
                if uid != self.owner:
                    return
                
                target = call.data.split("_")[2]
                user["admin_temp_ban_target"] = target
                user["admin_state"] = "admin_temp_ban_minutes"
                self.db.write("users", db_u)
                
                self.bot.send_message(uid, f"⏰ تعداد دقیقه برای تمدید بن کاربر {target}:")
                self.bot.answer_callback_query(call.id, "✅")

            # مدیریت هشدار تعمیر
            elif call.data == "start_maintenance_warning":
                if uid != self.owner:
                    return
                
                self.start_maintenance_warning(uid)
                self.bot.edit_message_text("⚠️ <b>هشدار تعمیر فعال شد!</b>\n\n"
                                          "هر 30 ثانیه پیام هشدار ارسال می‌شود.\n"
                                          "بعد از 3 دقیقه ربات به حالت تعمیر می‌رود.\n\n"
                                          "برای لغو روی '⚠️ هشدار تعمیر' کلیک کنید.", 
                                          call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅ هشدار فعال شد")

            elif call.data == "cancel_maintenance":
                if uid != self.owner:
                    return
                
                self.bot.edit_message_text("❌ <b>هشدار تعمیر لغو شد</b>\n\n"
                                          "ربات به حالت عادی ادامه می‌دهد.", 
                                          call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅ لغو شد")

            elif call.data == "cancel_maintenance_warning":
                if uid != self.owner:
                    return
                
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("✅ بله، لغو کن و عذرخواهی کن", callback_data="confirm_cancel_warning"),
                    types.InlineKeyboardButton("❌ خیر، ادامه بده", callback_data="continue_warning")
                )
                
                self.bot.edit_message_text("⚠️ <b>لغو هشدار تعمیر</b>\n\n"
                                          "آیا مطمئن هستید که می‌خواهید هشدار را لغو کنید؟\n\n"
                                          "اگر لغو کنید:\n"
                                          "• پیام عذرخواهی به کاربران ارسال می‌شود\n"
                                          "• هشدارها متوقف می‌شوند\n"
                                          "• ربات به حالت تعمیر نمی‌رود", 
                                          call.message.chat.id, call.message.message_id, 
                                          reply_markup=kb)
                self.bot.answer_callback_query(call.id, "⚠️")

            elif call.data == "confirm_cancel_warning":
                if uid != self.owner:
                    return
                
                if self.cancel_maintenance_warning(uid):
                    self.bot.edit_message_text("✅ <b>هشدار تعمیر لغو شد</b>\n\n"
                                              "پیام عذرخواهی به کاربران ارسال شد.\n"
                                              "ربات به حالت عادی ادامه می‌دهد.", 
                                              call.message.chat.id, call.message.message_id)
                    self.bot.answer_callback_query(call.id, "✅ لغو شد و عذرخواهی ارسال شد")
                else:
                    self.bot.answer_callback_query(call.id, "❌ هشداری فعال نیست")

            elif call.data == "continue_warning":
                if uid != self.owner:
                    return
                
                self.bot.edit_message_text("⚠️ <b>هشدار تعمیر ادامه دارد</b>\n\n"
                                          "هشدارها همچنان ارسال می‌شوند.\n"
                                          "بعد از 3 دقیقه ربات به حالت تعمیر می‌رود.", 
                                          call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅ ادامه دارد")

            elif call.data == "cancel_no":
                if uid != self.owner:
                    return
                self.bot.answer_callback_query(call.id, "✅")

            # ==========================================
            # 🔘 کال‌بک‌های مدیریت پیشرفته
            # ==========================================

            # تنظیمات پویا
            elif call.data == "admin_vip_prices":
                if uid != self.owner:
                    return
                
                vip_prices = self.vip_prices_coins
                prices_text = "<b>💰 تنظیمات قیمت VIP</b>\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                
                for vip_type, price in vip_prices.items():
                    if vip_type != "christmas":  # VIP کریسمس رایگان است
                        prices_text += f"🎖 VIP {vip_type}: {price:,} سکه\n"
                        kb.add(types.InlineKeyboardButton(
                            f"تغییر {vip_type}",
                            callback_data=f"change_vip_price_{vip_type}"
                        ))
                
                self.bot.edit_message_text(prices_text, call.message.chat.id, call.message.message_id, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data.startswith("change_vip_price_"):
                if uid != self.owner:
                    return
                
                vip_type = call.data.split("_")[3]
                user["admin_change_vip_type"] = vip_type
                user["admin_state"] = "admin_change_vip_price"
                self.db.write("users", db_u)
                
                self.bot.send_message(uid, f"💰 قیمت جدید برای VIP {vip_type} را وارد کنید (سکه):")
                self.bot.answer_callback_query(call.id, "💰")

            elif call.data == "admin_wheel_settings":
                if uid != self.owner:
                    return
                
                wheel_settings = self.settings.get("wheel_rewards", [])
                wheel_text = "<b>🎡 تنظیمات گردونه شانس</b>\n\n"
                
                total_prob = sum(r.get("probability", 0) for r in wheel_settings)
                wheel_text += f"📊 مجموع احتمالات: {total_prob:.3f}\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                
                for i, reward in enumerate(wheel_settings):
                    wheel_text += f"{i+1}. {reward.get('name')} - {reward.get('probability')*100:.1f}%\n"
                    kb.add(types.InlineKeyboardButton(
                        f"تغییر {i+1}",
                        callback_data=f"change_wheel_reward_{i}"
                    ))
                
                self.bot.edit_message_text(wheel_text, call.message.chat.id, call.message.message_id, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data.startswith("change_wheel_reward_"):
                if uid != self.owner:
                    return
                
                reward_index = int(call.data.split("_")[3])
                wheel_settings = self.settings.get("wheel_rewards", [])
                
                if reward_index < len(wheel_settings):
                    reward = wheel_settings[reward_index]
                    reward_text = f"🎯 <b>تغییر جایزه گردونه</b>\n\n"
                    reward_text += f"جایزه فعلی: {reward.get('name')}\n"
                    reward_text += f"نوع: {reward.get('type')}\n"
                    reward_text += f"مقدار: {reward.get('value')}\n"
                    reward_text += f"احتمال: {reward.get('probability')*100:.1f}%\n\n"
                    
                    user["admin_wheel_index"] = reward_index
                    user["admin_state"] = "admin_change_wheel_reward"
                    self.db.write("users", db_u)
                    
                    kb = types.InlineKeyboardMarkup(row_width=3)
                    kb.add(
                        types.InlineKeyboardButton("تغییر نام", callback_data=f"wheel_change_name_{reward_index}"),
                        types.InlineKeyboardButton("تغییر مقدار", callback_data=f"wheel_change_value_{reward_index}"),
                        types.InlineKeyboardButton("تغییر احتمال", callback_data=f"wheel_change_prob_{reward_index}")
                    )
                    
                    self.bot.send_message(uid, reward_text, reply_markup=kb)
                
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data.startswith("wheel_change_prob_"):
                if uid != self.owner:
                    return
                
                reward_index = int(call.data.split("_")[3])
                user["admin_wheel_index"] = reward_index
                user["admin_state"] = "admin_change_wheel_probability"
                self.db.write("users", db_u)
                
                self.bot.send_message(uid, "📊 احتمال جدید را وارد کنید (مثلاً 0.1 برای 10%):")
                self.bot.answer_callback_query(call.id, "📊")

            # مدیریت قابلیت‌ها
            elif call.data.startswith("toggle_feature_"):
                if uid != self.owner:
                    return
                
                feature_key = call.data.split("_")[2]
                features = self.settings.get("features", {})
                current_state = features.get(feature_key, True)
                
                # تغییر وضعیت
                features[feature_key] = not current_state
                self.update_settings("features", features)
                
                feature_names = {
                    "chat_enabled": "چت ناشناس",
                    "anonymous_messages": "پیام ناشناس",
                    "spin_wheel_enabled": "گردونه شانس",
                    "missions_enabled": "ماموریت‌ها",
                    "referral_system": "سیستم رفرال",
                    "vip_system": "سیستم VIP",
                    "ai_filter": "فیلتر AI",
                    "bad_words_filter": "فیلتر فحش"
                }
                
                new_state = "✅ فعال" if not current_state else "❌ غیرفعال"
                self.bot.answer_callback_query(call.id, f"{feature_names.get(feature_key, feature_key)} {new_state} شد")
                
                # بروزرسانی پیام
                features = self.settings.get("features", {})
                features_text = "<b>🛠 مدیریت قابلیت‌ها</b>\n\n"
                features_text += "✅ = فعال\n❌ = غیرفعال\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                
                for key, name in [
                    ("chat_enabled", "چت ناشناس"),
                    ("anonymous_messages", "پیام ناشناس"),
                    ("spin_wheel_enabled", "گردونه شانس"),
                    ("missions_enabled", "ماموریت‌ها"),
                    ("referral_system", "سیستم رفرال"),
                    ("vip_system", "سیستم VIP"),
                    ("ai_filter", "فیلتر AI"),
                    ("bad_words_filter", "فیلتر فحش")
                ]:
                    status = "✅" if features.get(key, True) else "❌"
                    features_text += f"{status} {name}\n"
                    kb.add(types.InlineKeyboardButton(
                        f"{'❌ غیرفعال' if features.get(key, True) else '✅ فعال'} {name}",
                        callback_data=f"toggle_feature_{key}"
                    ))
                
                self.bot.edit_message_text(features_text, call.message.chat.id, call.message.message_id, reply_markup=kb)

            # ارسال هدفمند
            elif call.data.startswith("confirm_broadcast_"):
                if uid != self.owner:
                    return
                
                target_type = call.data.split("_")[2]
                db_u_all = self.db.read("users")
                
                # انتخاب کاربران بر اساس نوع
                if target_type == "all":
                    user_ids = list(db_u_all["users"].keys())
                    target_name = "همه کاربران"
                elif target_type == "vip":
                    user_ids = [uid_key for uid_key in db_u_all["users"] if self.is_vip(uid_key)]
                    target_name = "کاربران VIP"
                elif target_type == "male":
                    user_ids = [uid_key for uid_key, u in db_u_all["users"].items() if u.get("sex") == "آقا"]
                    target_name = "آقایان"
                elif target_type == "female":
                    user_ids = [uid_key for uid_key, u in db_u_all["users"].items() if u.get("sex") == "خانم"]
                    target_name = "خانم‌ها"
                else:
                    user_ids = []
                    target_name = "نامشخص"
                
                message = user.get("broadcast_message", "پیام تست")
                
                # ارسال پیام
                success, failed = self.send_targeted_broadcast(user_ids, message)
                
                result_text = f"📢 <b>نتیجه ارسال پیام همگانی</b>\n\n"
                result_text += f"🎯 گروه هدف: {target_name}\n"
                result_text += f"👥 تعداد کل: {len(user_ids):,} کاربر\n"
                result_text += f"✅ ارسال موفق: {success:,} کاربر\n"
                result_text += f"❌ ارسال ناموفق: {failed:,} کاربر\n\n"
                
                if failed > 0:
                    result_text += "کاربران ناموفق احتمالاً ربات را بلاک کرده‌اند یا حسابشان حذف شده."
                
                self.bot.send_message(uid, result_text, reply_markup=self.kb_admin())
                self.bot.answer_callback_query(call.id, "✅ ارسال انجام شد")

            elif call.data == "cancel_broadcast":
                if uid != self.owner:
                    return
                
                self.bot.send_message(uid, "❌ ارسال پیام همگانی لغو شد", reply_markup=self.kb_admin())
                self.bot.answer_callback_query(call.id, "❌ لغو شد")

            # جستجوی کاربران
            elif call.data == "search_id":
                user["admin_state"] = "admin_search_id"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🆔 آیدی کاربر را وارد کنید:")
                self.bot.answer_callback_query(call.id, "🔍")

            elif call.data == "search_name":
                user["admin_state"] = "admin_search_name"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 نام کاربر را وارد کنید:")
                self.bot.answer_callback_query(call.id, "🔍")

            elif call.data == "search_age":
                user["admin_state"] = "admin_search_age"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🔢 سن مورد نظر را وارد کنید:")
                self.bot.answer_callback_query(call.id, "🔍")

            elif call.data == "search_vip_true":
                results = self.search_users("true", "vip")
                self.display_search_results(uid, results, "نتایج جستجو برای کاربران VIP")
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data == "search_vip_false":
                results = self.search_users("false", "vip")
                self.display_search_results(uid, results, "نتایج جستجو برای کاربران غیر VIP")
                self.bot.answer_callback_query(call.id, "✅")

            # مدیریت فحش
            elif call.data == "bad_words_list":
                bad_words_list = self.manage_bad_words("list")
                words_text = "<b>📋 لیست کلمات فحش</b>\n\n"
                words_text += f"تعداد: {len(bad_words_list)} کلمه\n\n"
                
                for i in range(0, len(bad_words_list), 10):
                    chunk = bad_words_list[i:i+10]
                    words_text += f"{', '.join(chunk)}\n\n"
                
                self.bot.send_message(uid, words_text)
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data == "bad_words_add":
                user["admin_state"] = "admin_bad_words_add"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "➕ کلمه جدید را وارد کنید:")
                self.bot.answer_callback_query(call.id, "➕")

            elif call.data == "bad_words_remove":
                user["admin_state"] = "admin_bad_words_remove"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "➖ کلمه مورد نظر برای حذف را وارد کنید:")
                self.bot.answer_callback_query(call.id, "➖")

            elif call.data == "bad_words_stats":
                bad_words_list = self.manage_bad_words("list")
                stats_text = "<b>📊 آمار کلمات فحش</b>\n\n"
                stats_text += f"📊 تعداد کل کلمات: {len(bad_words_list)}\n"
                stats_text += f"📈 بیشترین استفاده: در حال پیگیری...\n"
                stats_text += f"🔄 آخرین بروزرسانی: همین الان\n\n"
                
                self.bot.send_message(uid, stats_text)
                self.bot.answer_callback_query(call.id, "📊")

            # گزارش‌گیری
            elif call.data == "report_daily":
                self.generate_daily_report(uid)
                self.bot.answer_callback_query(call.id, "📅")

            elif call.data == "report_weekly":
                self.generate_weekly_report(uid)
                self.bot.answer_callback_query(call.id, "📆")

            elif call.data == "report_monthly":
                self.generate_monthly_report(uid)
                self.bot.answer_callback_query(call.id, "📈")

            elif call.data == "report_financial":
                self.generate_financial_report(uid)
                self.bot.answer_callback_query(call.id, "💰")

            # مدیریت خودکار
            elif call.data == "change_reset_hour":
                user["admin_state"] = "admin_change_reset_hour"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🕐 ساعت جدید ریست روزانه را وارد کنید (0-23):")
                self.bot.answer_callback_query(call.id, "🕐")

            elif call.data == "configure_backup":
                auto_settings = self.settings.get("bot_settings", {})
                
                backup_text = "<b>💾 تنظیمات پشتیبان‌گیری خودکار</b>\n\n"
                backup_text += f"وضعیت فعلی: {'✅ فعال' if auto_settings.get('auto_backup', True) else '❌ غیرفعال'}\n"
                backup_text += f"فاصله فعلی: هر {auto_settings.get('backup_interval_hours', 24)} ساعت\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("🔄 فعال/غیرفعال", callback_data="toggle_auto_backup"),
                    types.InlineKeyboardButton("⏰ تغییر فاصله", callback_data="change_backup_interval")
                )
                
                self.bot.send_message(uid, backup_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "💾")

            elif call.data == "toggle_auto_backup":
                auto_settings = self.settings.get("bot_settings", {})
                current_state = auto_settings.get("auto_backup", True)
                auto_settings["auto_backup"] = not current_state
                
                self.update_settings("bot_settings", auto_settings)
                
                new_state = "✅ فعال" if not current_state else "❌ غیرفعال"
                self.bot.answer_callback_query(call.id, f"پشتیبان‌گیری خودکار {new_state} شد")
                
                # راه‌اندازی مجدد سیستم پشتیبان‌گیری در صورت فعال شدن
                if not current_state and self.auto_backup_thread is None:
                    self.start_auto_backup()

            elif call.data == "change_backup_interval":
                user["admin_state"] = "admin_change_backup_interval"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "⏰ فاصله جدید پشتیبان‌گیری را وارد کنید (ساعت):")
                self.bot.answer_callback_query(call.id, "⏰")

            elif call.data == "change_limits":
                auto_settings = self.settings.get("bot_settings", {})
                
                limits_text = "<b>📝 تنظیمات محدودیت‌ها</b>\n\n"
                limits_text += f"💬 محدودیت پیام هر کاربر: {auto_settings.get('max_messages_per_user', 1000)} پیام\n"
                limits_text += f"⏳ تایم‌اوت چت: {auto_settings.get('chat_timeout_minutes', 30)} دقیقه\n"
                limits_text += f"⚠️ حداکثر اخطار: {auto_settings.get('max_warnings', 3)}\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("💬 تغییر محدودیت پیام", callback_data="change_msg_limit"),
                    types.InlineKeyboardButton("⏳ تغییر تایم‌اوت", callback_data="change_chat_timeout")
                )
                kb.add(
                    types.InlineKeyboardButton("⚠️ تغییر اخطارها", callback_data="change_warnings_limit"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
                )
                
                self.bot.send_message(uid, limits_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "📝")

            elif call.data == "change_msg_limit":
                user["admin_state"] = "admin_change_msg_limit"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "💬 محدودیت جدید پیام هر کاربر را وارد کنید:")
                self.bot.answer_callback_query(call.id, "💬")

            elif call.data == "change_chat_timeout":
                user["admin_state"] = "admin_change_chat_timeout"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "⏳ تایم‌اوت جدید چت را وارد کنید (دقیقه):")
                self.bot.answer_callback_query(call.id, "⏳")

            elif call.data == "change_warnings_limit":
                user["admin_state"] = "admin_change_warnings_limit"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "⚠️ حداکثر اخطار جدید را وارد کنید:")
                self.bot.answer_callback_query(call.id, "⚠️")

            elif call.data == "manual_reset":
                self.perform_daily_reset()
                self.bot.send_message(uid, "✅ ریست روزانه دستی انجام شد")
                self.bot.answer_callback_query(call.id, "✅")

            # مدیریت قالب‌ها
            elif call.data == "manage_message_templates":
                templates = self.db.read("templates")
                broadcast_templates = templates.get("broadcast_templates", [])
                
                templates_text = "<b>📝 مدیریت قالب‌های پیام</b>\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                
                for i, template in enumerate(broadcast_templates):
                    templates_text += f"{i+1}. {template.get('name')}\n"
                    kb.add(types.InlineKeyboardButton(
                        f"✏️ {template.get('name')[:15]}",
                        callback_data=f"edit_template_{i}"
                    ))
                
                kb.add(types.InlineKeyboardButton("➕ افزودن قالب جدید", callback_data="add_template"))
                
                self.bot.send_message(uid, templates_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "📝")

            elif call.data.startswith("edit_template_"):
                template_index = int(call.data.split("_")[2])
                templates = self.db.read("templates")
                broadcast_templates = templates.get("broadcast_templates", [])
                
                if template_index < len(broadcast_templates):
                    template = broadcast_templates[template_index]
                    
                    template_text = f"<b>✏️ ویرایش قالب پیام</b>\n\n"
                    template_text += f"📝 نام: {template.get('name')}\n"
                    template_text += f"📄 متن:\n{template.get('text')}\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("✏️ تغییر نام", callback_data=f"change_template_name_{template_index}"),
                        types.InlineKeyboardButton("📝 تغییر متن", callback_data=f"change_template_text_{template_index}")
                    )
                    kb.add(
                        types.InlineKeyboardButton("🗑 حذف قالب", callback_data=f"delete_template_{template_index}"),
                        types.InlineKeyboardButton("🔙 بازگشت", callback_data="manage_message_templates")
                    )
                    
                    self.bot.send_message(uid, template_text, reply_markup=kb)
                
                self.bot.answer_callback_query(call.id, "✏️")

            elif call.data == "add_template":
                user["admin_state"] = "admin_add_template_name"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 نام قالب جدید را وارد کنید:")
                self.bot.answer_callback_query(call.id, "➕")

            elif call.data == "manage_button_templates":
                templates = self.db.read("templates")
                button_templates = templates.get("button_templates", {})
                
                templates_text = "<b>🎛 مدیریت قالب‌های دکمه</b>\n\n"
                templates_text += f"📋 تعداد منوها: {len(button_templates)}\n\n"
                
                for menu_name, buttons in button_templates.items():
                    templates_text += f"📌 {menu_name}: {len(buttons)} دکمه\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("✏️ منوی اصلی", callback_data="edit_main_menu"),
                    types.InlineKeyboardButton("✏️ منوی چت", callback_data="edit_chat_menu")
                )
                kb.add(
                    types.InlineKeyboardButton("➕ منوی جدید", callback_data="add_button_menu"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
                )
                
                self.bot.send_message(uid, templates_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "🎛")

            elif call.data == "edit_main_menu":
                templates = self.db.read("templates")
                main_menu = templates.get("button_templates", {}).get("main_menu", [])
                
                menu_text = "<b>✏️ ویرایش منوی اصلی</b>\n\n"
                menu_text += "دکمه‌های فعلی:\n"
                
                for i, button in enumerate(main_menu, 1):
                    menu_text += f"{i}. {button}\n"
                
                user["admin_state"] = "admin_edit_main_menu"
                self.db.write("users", db_u)
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("➕ افزودن دکمه", callback_data="add_main_menu_button"),
                    types.InlineKeyboardButton("➖ حذف دکمه", callback_data="remove_main_menu_button")
                )
                kb.add(
                    types.InlineKeyboardButton("🔄 بازنشانی", callback_data="reset_main_menu"),
                    types.InlineKeyboardButton("💾 ذخیره", callback_data="save_main_menu")
                )
                
                self.bot.send_message(uid, menu_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✏️")

            # مدیریت اقتصادی
            elif call.data == "change_vip_prices":
                vip_prices = self.vip_prices_coins
                prices_text = "<b>💰 تغییر قیمت VIP</b>\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                
                for vip_type, price in vip_prices.items():
                    if vip_type != "christmas":
                        prices_text += f"🎖 VIP {vip_type}: {price:,} سکه\n"
                        kb.add(types.InlineKeyboardButton(
                            f"تغییر {vip_type}",
                            callback_data=f"change_vip_price_{vip_type}"
                        ))
                
                self.bot.send_message(uid, prices_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "💰")

            elif call.data == "change_rewards":
                bot_settings = self.settings.get("bot_settings", {})
                
                rewards_text = "<b>🎁 تغییر پاداش‌ها</b>\n\n"
                rewards_text += f"🎁 پاداش ثبت‌نام: {bot_settings.get('welcome_bonus', 50):,} سکه\n"
                rewards_text += f"👥 پاداش رفرال: {bot_settings.get('referral_bonus', 100):,} سکه\n"
                rewards_text += f"⚠️ اخطار قبل از بن: {bot_settings.get('max_warnings', 3)}\n"
                rewards_text += f"⏰ مدت بن موقت: {bot_settings.get('temp_ban_duration', 1440)} دقیقه\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("🎁 تغییر پاداش ثبت‌نام", callback_data="change_welcome_bonus"),
                    types.InlineKeyboardButton("👥 تغییر پاداش رفرال", callback_data="change_referral_bonus")
                )
                kb.add(
                    types.InlineKeyboardButton("⚠️ تغییر اخطارها", callback_data="change_warnings_limit"),
                    types.InlineKeyboardButton("⏰ تغییر مدت بن", callback_data="change_ban_duration")
                )
                
                self.bot.send_message(uid, rewards_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "🎁")

            elif call.data == "change_welcome_bonus":
                user["admin_state"] = "admin_change_welcome_bonus"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🎁 پاداش جدید ثبت‌نام را وارد کنید (سکه):")
                self.bot.answer_callback_query(call.id, "🎁")

            elif call.data == "change_referral_bonus":
                user["admin_state"] = "admin_change_referral_bonus"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "👥 پاداش جدید رفرال را وارد کنید (سکه):")
                self.bot.answer_callback_query(call.id, "👥")

            elif call.data == "change_ban_duration":
                user["admin_state"] = "admin_change_ban_duration"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "⏰ مدت جدید بن موقت را وارد کنید (دقیقه):")
                self.bot.answer_callback_query(call.id, "⏰")

            elif call.data == "financial_report":
                self.generate_financial_report(uid)
                self.bot.answer_callback_query(call.id, "💰")

            elif call.data == "special_discount":
                user["admin_state"] = "admin_special_discount"
                self.db.write("users", db_u)
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("🎖 تخفیف VIP", callback_data="vip_discount"),
                    types.InlineKeyboardButton("💰 تخفیف سکه", callback_data="coins_discount")
                )
                kb.add(
                    types.InlineKeyboardButton("⏰ تخفیف محدود", callback_data="time_discount"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
                )
                
                self.bot.send_message(uid, "💸 <b>تخفیف ویژه</b>\n\n"
                                          "نوع تخفیف مورد نظر را انتخاب کنید:", 
                                    reply_markup=kb)
                self.bot.answer_callback_query(call.id, "💸")

            elif call.data == "vip_discount":
                user["admin_state"] = "admin_vip_discount_type"
                self.db.write("users", db_u)
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("۱ هفته", callback_data="discount_week"),
                    types.InlineKeyboardButton("۱ ماه", callback_data="discount_month")
                )
                kb.add(
                    types.InlineKeyboardButton("۳ ماه", callback_data="discount_3month"),
                    types.InlineKeyboardButton("۶ ماه", callback_data="discount_6month")
                )
                kb.add(
                    types.InlineKeyboardButton("۱ سال", callback_data="discount_year"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="special_discount")
                )
                
                self.bot.send_message(uid, "🎖 <b>تخفیف VIP</b>\n\n"
                                          "مدت VIP مورد نظر برای تخفیف را انتخاب کنید:", 
                                    reply_markup=kb)
                self.bot.answer_callback_query(call.id, "🎖")

            elif call.data.startswith("discount_"):
                vip_type = call.data.split("_")[1]
                user["discount_vip_type"] = vip_type
                user["admin_state"] = "admin_vip_discount_percent"
                self.db.write("users", db_u)
                
                self.bot.send_message(uid, f"🎖 درصد تخفیف برای VIP {vip_type} را وارد کنید (مثلاً 20 برای 20%):")
                self.bot.answer_callback_query(call.id, "🎖")

            elif call.data == "mission_stats":
                self.generate_mission_stats(uid)
                self.bot.answer_callback_query(call.id, "📊")

            elif call.data == "ban_report":
                self.generate_ban_report(uid)
                self.bot.answer_callback_query(call.id, "📋")

            elif call.data == "ban_settings":
                bot_settings = self.settings.get("bot_settings", {})
                
                ban_text = "<b>⚙ تنظیمات سیستم بن</b>\n\n"
                ban_text += f"⚠️ اخطار قبل از بن: {bot_settings.get('max_warnings', 3)}\n"
                ban_text += f"⏰ مدت بن موقت: {bot_settings.get('temp_ban_duration', 1440)} دقیقه\n"
                ban_text += f"🔁 بن دائم پس از: {bot_settings.get('perm_ban_after_temp', 2)} بن موقت\n\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("⚠️ تغییر اخطارها", callback_data="change_warnings_limit"),
                    types.InlineKeyboardButton("⏰ تغییر مدت بن", callback_data="change_ban_duration")
                )
                kb.add(
                    types.InlineKeyboardButton("🔁 تنظیم بن دائم", callback_data="set_perm_ban_rule"),
                    types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back")
                )
                
                self.bot.send_message(uid, ban_text, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "⚙")

            elif call.data == "set_perm_ban_rule":
                user["admin_state"] = "admin_set_perm_ban_rule"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🔁 پس از چند بن موقت، بن دائم اعمال شود؟")
                self.bot.answer_callback_query(call.id, "🔁")

            elif call.data == "reset_warnings":
                db_u_all = self.db.read("users")
                reset_count = 0
                
                for user_id, user_data in db_u_all["users"].items():
                    if user_data.get("warns", 0) > 0:
                        user_data["warns"] = 0
                        reset_count += 1
                
                self.db.write("users", db_u_all)
                self.bot.send_message(uid, f"✅ اخطارهای {reset_count} کاربر ریست شد")
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data == "admin_back":
                self.bot.send_message(uid, "🔙 بازگشت به پنل مدیریت", reply_markup=self.kb_admin())
                self.bot.answer_callback_query(call.id, "🔙")

    # ==========================================
    # 📊 توابع کمکی
    # ==========================================

    def display_search_results(self, uid, results, title):
        """نمایش نتایج جستجو"""
        if not results:
            self.bot.send_message(uid, f"❌ هیچ نتیجه‌ای برای '{title}' پیدا نشد")
            return
        
        results_text = f"<b>{title}</b>\n\n"
        results_text += f"🔍 تعداد نتایج: {len(results)}\n\n"
        
        for i, (user_id, user_data) in enumerate(results[:20], 1):
            vip_status = "🎖 VIP" if self.is_vip(user_id) else "⭐ عادی"
            results_text += f"{i}. 🆔 <code>{user_id}</code>\n"
            results_text += f"   📝 نام: {user_data.get('name', 'نامشخص')}\n"
            results_text += f"   ⚧ جنسیت: {user_data.get('sex', 'نامشخص')}\n"
            results_text += f"   🔢 سن: {user_data.get('age', 'نامشخص')}\n"
            results_text += f"   🎖 وضعیت: {vip_status}\n"
            results_text += f"   💰 سکه: {user_data.get('coins', 0):,}\n"
            results_text += f"   ⚠️ اخطار: {user_data.get('warns', 0)}\n\n"
        
        if len(results) > 20:
            results_text += f"\n... و {len(results) - 20} نتیجه دیگر"
        
        self.bot.send_message(uid, results_text)

    def generate_daily_report(self, uid):
        """تولید گزارش روزانه"""
        stats = self.get_statistics("daily")
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        report_text = f"<b>📅 گزارش روزانه - {today}</b>\n\n"
        report_text += f"👥 کل کاربران: {stats['total_users']:,}\n"
        report_text += f"📅 کاربران فعال امروز: {stats['active_today']:,}\n"
        report_text += f"🎖 کاربران VIP: {stats['vip_users']:,}\n"
        report_text += f"💰 کل سکه‌ها: {stats['total_coins']:,}\n"
        report_text += f"💬 چت‌های فعال: {stats['active_chats']:,}\n"
        report_text += f"⏳ کاربران در صف: {stats['queue_size']:,}\n"
        report_text += f"🚫 بن دائم: {stats['permanent_bans']:,}\n"
        report_text += f"⏰ بن موقت: {stats['temporary_bans']:,}\n\n"
        
        # محاسبه رشد
        yesterday_stats = self.get_yesterday_stats()
        if yesterday_stats:
            user_growth = stats['total_users'] - yesterday_stats.get('total_users', 0)
            vip_growth = stats['vip_users'] - yesterday_stats.get('vip_users', 0)
            
            report_text += f"<b>📈 رشد روزانه:</b>\n"
            report_text += f"👥 کاربران: {'+' if user_growth > 0 else ''}{user_growth}\n"
            report_text += f"🎖 VIP: {'+' if vip_growth > 0 else ''}{vip_growth}\n"
        
        self.bot.send_message(uid, report_text)

    def generate_weekly_report(self, uid):
        """تولید گزارش هفتگی"""
        # این تابع را می‌توانید بر اساس نیاز توسعه دهید
        self.bot.send_message(uid, "📆 <b>گزارش هفتگی</b>\n\n"
                                  "این قابلیت در حال توسعه است...")

    def generate_monthly_report(self, uid):
        """تولید گزارش ماهانه"""
        # این تابع را می‌توانید بر اساس نیاز توسعه دهید
        self.bot.send_message(uid, "📈 <b>گزارش ماهانه</b>\n\n"
                                  "این قابلیت در حال توسعه است...")

    def generate_financial_report(self, uid):
        """تولید گزارش مالی"""
        db_u = self.db.read("users")
        
        total_coins = sum(u.get("coins", 0) for u in db_u["users"].values())
        total_vip_sales = 0
        
        # تخمین فروش VIP بر اساس موجودی کاربران
        for user_id, user_data in db_u["users"].items():
            if self.is_vip(user_id):
                # یک تخمین ساده - می‌توانید سیستم دقیق‌تری پیاده‌سازی کنید
                vip_sales = user_data.get("vip_purchases", 0)
                total_vip_sales += vip_sales
        
        report_text = "<b>💰 گزارش مالی ربات</b>\n\n"
        report_text += f"💰 کل سکه‌های در گردش: {total_coins:,}\n"
        report_text += f"🎖 تخمین فروش VIP: {total_vip_sales:,} سکه\n"
        report_text += f"💵 ارزش تقریبی: {total_coins / 1000:.2f} دلار\n\n"
        report_text += "<i>نکته: این اعداد تقریبی هستند.</i>"
        
        self.bot.send_message(uid, report_text)

    def generate_mission_stats(self, uid):
        """تولید آمار ماموریت‌ها"""
        db_u = self.db.read("users")
        db_m = self.db.read("missions")
        
        completed_today = 0
        total_users = len(db_u["users"])
        
        for user_data in db_u["users"].values():
            if user_data.get("mission_completed_date") == str(datetime.date.today()):
                completed_today += 1
        
        stats_text = "<b>📊 آمار ماموریت‌ها</b>\n\n"
        stats_text += f"📅 ماموریت امروز: {db_m['daily']['mission']}\n"
        stats_text += f"✅ تکمیل شده امروز: {completed_today}/{total_users} کاربر\n"
        stats_text += f"📈 درصد مشارکت: {(completed_today/total_users*100) if total_users > 0 else 0:.1f}%\n"
        stats_text += f"📋 تعداد ماموریت‌ها: {len(db_m['available'])}\n\n"
        
        # محبوب‌ترین ماموریت‌ها
        stats_text += "<b>🎯 محبوب‌ترین ماموریت‌ها:</b>\n"
        
        mission_stats = {}
        for user_data in db_u["users"].values():
            completed_missions = user_data.get("completed_missions", [])
            for mission in completed_missions:
                mission_stats[mission] = mission_stats.get(mission, 0) + 1
        
        sorted_missions = sorted(mission_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        
        for mission_name, count in sorted_missions:
            stats_text += f"• {mission_name}: {count} بار\n"
        
        self.bot.send_message(uid, stats_text)

    def generate_ban_report(self, uid):
        """تولید گزارش بن‌ها"""
        db_b = self.db.read("bans")
        
        report_text = "<b>🚫 گزارش سیستم بن</b>\n\n"
        report_text += f"🚫 بن دائم: {len(db_b.get('permanent', {}))} کاربر\n"
        report_text += f"⏰ بن موقت: {len(db_b.get('temporary', {}))} کاربر\n\n"
        
        # دلایل رایج بن
        ban_reasons = {}
        for ban_data in db_b.get("permanent", {}).values():
            if isinstance(ban_data, dict):
                reason = ban_data.get("reason", "نامشخص")
            else:
                reason = ban_data
            ban_reasons[reason] = ban_reasons.get(reason, 0) + 1
        
        for ban_data in db_b.get("temporary", {}).values():
            reason = ban_data.get("reason", "نامشخص")
            ban_reasons[reason] = ban_reasons.get(reason, 0) + 1
        
        if ban_reasons:
            report_text += "<b>📊 دلایل رایج بن:</b>\n"
            sorted_reasons = sorted(ban_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for reason, count in sorted_reasons:
                report_text += f"• {reason}: {count} بار\n"
        
        self.bot.send_message(uid, report_text)

    def get_yesterday_stats(self):
        """دریافت آمار دیروز (برای مقایسه)"""
        # این تابع را می‌توانید بر اساس نیاز توسعه دهید
        # می‌توانید آمار روزانه را در دیتابیس ذخیره کنید
        return None

    def run(self):
        """اجرای ربات"""
        print("=" * 50)
        print("Shadow Titan v42.0 - Advanced Edition")
        print("🤖 با پنل مدیریت پیشرفته")
        print("=" * 50)
        
        try:
            server_thread = Thread(target=run_web)
            server_thread.daemon = True
            server_thread.start()
            print("✅ وب‌سرور روی پورت 8080 راه‌اندازی شد")
        except Exception as e:
            logger.error(f"خطای وب‌سرور: {e}")

        try:
            print("🚀 در حال اتصال به تلگرام...")
            self.bot.infinity_polling(skip_pending=True)
        except Exception as e:
            logger.error(f"خطای پولینگ: {e}")
            print(f"❌ خطای پولینگ: {e}")

if __name__ == "__main__":
    bot_instance = ShadowTitanBot()
    bot_instance.run()
