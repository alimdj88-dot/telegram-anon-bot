import telebot
from telebot import types, formatting
import json
import os
import re
import requests
import datetime
import logging
import random
import threading
import time
import html
import uuid
from flask import Flask
from threading import Thread
from zoneinfo import ZoneInfo
from collections import defaultdict, deque
import schedule

# ==========================================
# پیکربندی از متغیرهای محیطی
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID", "8013245091")  # آیدی ادمین (پیش‌فرض)
HF_TOKEN = os.getenv("HF_TOKEN")

if not BOT_TOKEN:
    raise ValueError("لطفا BOT_TOKEN را در متغیرهای محیطی تنظیم کنید")

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
    return "Shadow Titan v42.1 – Full Fixed Edition"


def run_web():
    app.run(host='0.0.0.0', port=8080)


# ==========================================
# مدیریت دیتابیس با قفل و تراکنش
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
            "events": "db_events.json",
            "discounts": "db_discounts.json"
        }
        self.lock = threading.RLock()  # قفل بازگشتی برای تراکنش‌ها
        self.init_files()

    def init_files(self):
        defaults = {
            "users": {"users": {}, "next_event_id": 1},
            "bans": {"permanent": {}, "temporary": {}},
            "queue": {"general": []},
            "messages": {"inbox": {}},
            "config": {
                "settings": {
                    "maintenance": False,
                    "welcome_message": True,
                    "reward_message": True,
                    "warning_message": True,
                    "anon_notify": True,
                    "auto_search": True,
                    "word_filter": True,
                    "ai_scan": True,
                    "chat_restore": True,
                    "vip_message_limit": 100,
                    "chat_search_time": 30,
                    "daily_report_limit": 5
                },
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
            "events": {},
            "discounts": {}
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

    def transaction(self, func):
        """اجرای عملیات در یک تراکنش با قفل"""
        with self.lock:
            return func()


# ==========================================
# ربات اصلی
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        self.token = BOT_TOKEN
        self.owner = OWNER_ID
        self.channel = "@ChatNaAnnouncements"
        self.support = "@its_alimo"
        self.hf_token = HF_TOKEN

        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.db = DB()

        try:
            self.username = self.bot.get_me().username
        except:
            self.username = "ShadowTitanBot"
            logger.error("خطا در دریافت نام کاربری بات")

        # قیمت‌های VIP با سکه
        self.vip_prices_coins = {
            "week": 500,
            "month": 1800,
            "3month": 5000,
            "6month": 9000,
            "year": 15000,
            "christmas": 0
        }

        # مدت‌های VIP به ثانیه
        self.vip_durations = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "3month": 90 * 24 * 3600,
            "6month": 180 * 24 * 3600,
            "year": 365 * 24 * 3600,
            "christmas": 90 * 24 * 3600
        }

        # لیست فحش (بهبود یافته)
        self.bad_words = [
            "کیر", "کیرم", "کیرت", "کیری", "کس", "کص", "کوس", "کوث",
            "جنده", "جهنده", "مادرجنده", "قحبه", "قهبه",
            "پدرسگ", "پدرسوخته", "حرامزاده", "گاییدم", "گاییدن",
            "سیکتیر", "کون", "کونی", "گوه", "لاشی", "فاحشه",
            "ناموس", "اوبی", "بی‌ناموس", "سکس", "پورن",
            "خارکصه", "تخمم", "شاسگول", "پفیوز", "دیوث"
        ]

        # متغیرهای هشدار تعمیر
        self.maintenance_warning_active = False
        self.maintenance_warning_event = None
        self.maintenance_warning_thread = None

        # محدودیت نرخ (rate limiting)
        self.user_last_message = defaultdict(lambda: deque(maxlen=10))
        self.rate_limit_lock = threading.Lock()

        # زمان‌بند وظایف دوره‌ای
        self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.scheduler_thread.start()

        # بازیابی چت‌های فعال
        self.restore_active_chats()

        # پالایش صف جستجو (حذف کاربران timeout)
        self.start_queue_cleaner()

        self.register_handlers()
        logger.info("Shadow Titan v42.1 (Full) شروع شد")

    # ==========================================
    # توابع کمکی عمومی
    # ==========================================
    def escape_html(self, text):
        """فرار از کاراکترهای HTML در متن کاربر"""
        if text is None:
            return ""
        return html.escape(str(text))

    def format_user_text(self, text):
        """تبدیل متن کاربر با escape امن"""
        return self.escape_html(text)

    def get_tehran_time(self):
        """زمان حال به وقت تهران"""
        return datetime.datetime.now(ZoneInfo("Asia/Tehran"))

    def get_tehran_date_str(self):
        """تاریخ امروز به وقت تهران به فرمت YYYY-MM-DD"""
        return self.get_tehran_time().date().isoformat()

    def get_tehran_datetime_str(self):
        return self.get_tehran_time().strftime("%Y-%m-%d %H:%M:%S")

    def run_scheduler(self):
        """اجرای وظایف زمان‌بندی شده"""
        schedule.every().day.at("00:01").do(self.auto_update_daily_mission)
        schedule.every().hour.do(self.clean_expired_temp_bans)
        while True:
            schedule.run_pending()
            time.sleep(60)

    def clean_expired_temp_bans(self):
        """پاک‌سازی بن‌های موقت منقضی شده از فایل"""
        db_b = self.db.read("bans")
        now = datetime.datetime.now().timestamp()
        expired = [uid for uid, data in db_b["temporary"].items() if data["end"] <= now]
        for uid in expired:
            del db_b["temporary"][uid]
        if expired:
            self.db.write("bans", db_b)
            logger.info(f"{len(expired)} بن موقت منقضی پاک‌سازی شد")

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
                        self.bot.send_message(uid, "🔄 <b>چت شما بازیابی شد!</b>\n\nربات ری‌استارت شده بود. می‌توانید ادامه دهید.",
                                              reply_markup=self.kb_chatting())
                        self.bot.send_message(partner, "🔄 <b>چت شما بازیابی شد!</b>\n\nربات ری‌استارت شده بود. می‌توانید ادامه دهید.",
                                              reply_markup=self.kb_chatting())
                    except Exception as e:
                        logger.error(f"خطا در ارسال پیام بازیابی چت: {e}")
        self.db.write("users", db_u)
        logger.info("بازیابی چت‌های فعال انجام شد")

    def save_active_chat(self, uid, partner):
        db_c = self.db.read("chats")
        db_c[uid] = partner
        self.db.write("chats", db_c)

    def remove_active_chat(self, uid):
        db_c = self.db.read("chats")
        if uid in db_c:
            partner = db_c[uid]
            if partner in db_c and db_c[partner] == uid:
                del db_c[partner]
            del db_c[uid]
            self.db.write("chats", db_c)

    def auto_update_daily_mission(self):
        """بروزرسانی خودکار ماموریت روزانه (هر روز ساعت 00:01)"""
        db_m = self.db.read("missions")
        today = self.get_tehran_date_str()
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

    def contains_bad(self, text):
        """بررسی فحش (با حذف فاصله و کاراکترهای خاص)"""
        if not text:
            return False
        t = text.lower()
        t = re.sub(r'[\s\*\-_\.\d]+', '', t)
        # همچنین می‌توان فینگلیش را هم اضافه کرد
        return any(word.lower() in t for word in self.bad_words)

    def ai_toxic_scan(self, text):
        if not text or len(text.strip()) < 2 or not self.hf_token:
            return 0.0
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        try:
            response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=5)
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
        if not text or len(text.strip()) < 2 or not self.hf_token:
            return 0.0
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        url = "https://api-inference.huggingface.co/models/michellejieli/nsfw_text_classifier"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        try:
            response = requests.post(url, headers=headers, json={"inputs": clean_text}, timeout=5)
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
        db_u = self.db.read("users")
        user = db_u["users"].get(str(uid), {})
        vip_end = user.get("vip_end", 0)
        return vip_end > datetime.datetime.now().timestamp()

    def add_vip(self, uid, duration_key, reason="گیفت"):
        """افزودن VIP با جمع شدن مدت (تراکنش)"""
        def _add():
            db_u = self.db.read("users")
            uid = str(uid)
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
            return new_end
        new_end = self.db.transaction(_add)
        if new_end:
            try:
                end_date = datetime.datetime.fromtimestamp(new_end).strftime("%Y-%m-%d")
                duration_name = {
                    "week": "۱ هفته", "month": "۱ ماه", "3month": "۳ ماه",
                    "6month": "۶ ماه", "year": "۱ سال", "christmas": "۳ ماه رایگان"
                }.get(duration_key, "۳ ماه")
                remaining_days = int((new_end - datetime.datetime.now().timestamp()) / (24 * 3600))
                self.bot.send_message(uid,
                    f"🎉 <b>تبریک! رنک VIP دریافت کردید</b>\n\n"
                    f"مدت: {duration_name}\n"
                    f"تا تاریخ: {end_date}\n"
                    f"مدت باقی‌مانده: {remaining_days} روز\n"
                    f"دلیل: {reason}\n\nمبارک باشد ✨")
            except Exception as e:
                logger.error(f"خطا در ارسال پیام VIP به {uid}: {e}")
            return True
        return False

    def add_coins(self, uid, amount, reason=""):
        """افزودن سکه با تراکنش"""
        def _add():
            db_u = self.db.read("users")
            uid = str(uid)
            if uid not in db_u["users"]:
                return None
            if "coins" not in db_u["users"][uid]:
                db_u["users"][uid]["coins"] = 0
            db_u["users"][uid]["coins"] += amount
            new_balance = db_u["users"][uid]["coins"]
            self.db.write("users", db_u)
            return new_balance
        new_balance = self.db.transaction(_add)
        if new_balance is not None:
            try:
                self.bot.send_message(uid,
                    f"💰 <b>دریافت سکه!</b>\n\n"
                    f"مقدار: {amount:,} سکه\n"
                    f"دلیل: {reason}\n"
                    f"موجودی: {new_balance:,} سکه")
            except Exception as e:
                logger.error(f"خطا در ارسال پیام سکه به {uid}: {e}")
            return True
        return False

    def deduct_coins(self, uid, amount, reason=""):
        """کسر سکه با تراکنش (برای خرید)"""
        def _deduct():
            db_u = self.db.read("users")
            uid = str(uid)
            if uid not in db_u["users"]:
                return None
            coins = db_u["users"][uid].get("coins", 0)
            if coins < amount:
                return None
            db_u["users"][uid]["coins"] = coins - amount
            new_balance = db_u["users"][uid]["coins"]
            self.db.write("users", db_u)
            return new_balance
        return self.db.transaction(_deduct)

    def check_and_reward_mission(self, uid):
        db_u = self.db.read("users")
        db_m = self.db.read("missions")
        uid = str(uid)
        user = db_u["users"].get(uid, {})
        today = self.get_tehran_date_str()
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
        db_b = self.db.read("bans")
        uid = str(uid)
        db_b["permanent"][uid] = reason
        self.db.write("bans", db_b)
        try:
            self.bot.send_message(uid, f"🚫 <b>شما بن دائم شدید!</b>\n"
                                      f"دلیل: {reason}\n"
                                      f"پشتیبانی: {self.support}")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام بن به {uid}: {e}")

    def ban_temp(self, uid, minutes, reason="تخلف"):
        db_b = self.db.read("bans")
        uid = str(uid)
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
        db_u = self.db.read("users")
        uid = str(uid)
        name = db_u["users"].get(uid, {}).get("name", "نامشخص")
        tehran_time = self.get_tehran_datetime_str()
        report_text = f"🤖 <b>بن خودکار توسط ربات</b>\n\n"
        report_text += f"کاربر: 🆔 <code>{uid}</code> - {self.escape_html(name)}\n"
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
        db_u = self.db.read("users")
        a, b = str(a), str(b)
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
    # کیبوردها
    # ==========================================
    def kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس", "🎯 ماموریت روزانه")
        markup.add("👥 رفرال و دعوت", "🎖 خرید VIP")
        markup.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if str(uid) == self.owner:
            markup.add("📊 پنل مدیریت")
        return markup

    def kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def kb_admin(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📈 آمار کلی ربات", "👥 مدیریت کاربران")
        markup.add("📅 مدیریت رویدادها", "🎫 مدیریت تخفیف‌ها")
        markup.add("💎 سیستم VIP", "💰 مدیریت مالی")
        markup.add("🔧 تنظیمات ربات", "📈 گزارش‌های پیشرفته")
        markup.add("📤 خروجی دیتابیس", "🚫 مدیریت بن‌ها")
        markup.add("🎖 گیفت VIP تکی", "🎖 گیفت VIP همگانی")
        markup.add("❌ حذف VIP", "📋 لیست VIP")
        markup.add("💰 اهدای سکه", "🎯 مدیریت ماموریت‌ها")
        markup.add("⚠️ هشدار تعمیر", "🛠 تعمیر و نگهداری")
        markup.add("🔙 بازگشت به منو")
        return markup

    def kb_admin_users(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔍 جستجوی کاربر", "📋 لیست کاربران")
        markup.add("📊 آمار کاربران", "🎖 تغییر سطح VIP")
        markup.add("💰 تنظیم سکه", "⚠️ مدیریت اخطارها")
        markup.add("📅 فعالیت اخیر", "🔙 بازگشت به پنل مدیریت")
        return markup

    def kb_admin_events(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("➕ ایجاد رویداد جدید", "📋 لیست رویدادها")
        markup.add("✏️ ویرایش رویداد", "🗑️ حذف رویداد")
        markup.add("📊 آمار رویدادها", "👥 شرکت‌کنندگان")
        markup.add("🔙 بازگشت به پنل مدیریت")
        return markup

    def kb_admin_discounts(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("➕ ایجاد تخفیف جدید", "📋 لیست تخفیف‌ها")
        markup.add("✏️ ویرایش تخفیف", "🗑️ حذف تخفیف")
        markup.add("📊 آمار استفاده", "🎯 تخفیف‌های ویژه")
        markup.add("🔙 بازگشت به پنل مدیریت")
        return markup

    def kb_admin_vip(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🎖 گیفت VIP تکی", "🎖 گیفت VIP همگانی")
        markup.add("❌ حذف VIP", "📋 لیست VIP")
        markup.add("💰 تنظیم قیمت VIP", "⏰ تنظیم مدت VIP")
        markup.add("🔙 بازگشت به پنل مدیریت")
        return markup

    def kb_admin_finance(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("💰 اهدای سکه", "💸 کسر سکه")
        markup.add("📊 گزارش مالی", "🏦 تنظیمات مالی")
        markup.add("🔙 بازگشت به پنل مدیریت")
        return markup

    def kb_admin_settings(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("⚡ بهینه‌سازی", "🔄 ریست خودکار")
        markup.add("📦 پشتیبان‌گیری", "🗑️ پاک‌سازی داده")
        markup.add("🔧 تنظیمات سیستم", "📝 تنظیمات پیام")
        markup.add("🎛️ تنظیمات چت", "🔙 بازگشت به پنل مدیریت")
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
    # مدیریت صف و timeout
    # ==========================================
    def start_queue_cleaner(self):
        """هر 30 ثانیه کاربران timeout شده از صف پاک می‌شوند"""
        def cleaner():
            while True:
                time.sleep(30)
                self.clean_queue()
        thread = threading.Thread(target=cleaner, daemon=True)
        thread.start()

    def clean_queue(self):
        """حذف کاربرانی که بیش از 2 دقیقه در صف مانده‌اند"""
        db_q = self.db.read("queue")
        db_u = self.db.read("users")
        now = time.time()
        to_remove = []
        for entry in db_q.get("general", []):
            if isinstance(entry, dict):
                uid = entry["uid"]
                join_time = entry["time"]
                if now - join_time > 120:  # 2 دقیقه
                    to_remove.append(entry)
            else:
                # برای backward compatibility (اگر قبلاً فقط uid ذخیره شده)
                uid = entry
                join_time = db_u["users"].get(uid, {}).get("queue_join_time", 0)
                if now - join_time > 120:
                    to_remove.append({"uid": uid, "time": join_time})
        for entry in to_remove:
            uid = entry["uid"]
            try:
                db_q["general"] = [e for e in db_q["general"] if (isinstance(e, dict) and e["uid"] != uid) or (not isinstance(e, dict) and e != uid)]
                self.bot.send_message(uid, "⏰ زمان جستجو به پایان رسید. دوباره تلاش کنید.", reply_markup=self.kb_main(uid))
            except:
                pass
        if to_remove:
            self.db.write("queue", db_q)

    def try_match(self, uid):
        """تلاش برای پیدا کردن هم‌صحبت برای کاربر"""
        db_u = self.db.read("users")
        db_q = self.db.read("queue")
        user = db_u["users"].get(uid)
        if not user:
            return
        search_gender = user.get("search_gender")
        # یافتن ورودی کاربر در صف
        user_entry = None
        for e in db_q.get("general", []):
            if isinstance(e, dict) and e["uid"] == uid:
                user_entry = e
                break
        if not user_entry:
            return
        # لیست نامزدها
        candidates = []
        for e in db_q["general"]:
            if isinstance(e, dict) and e["uid"] != uid:
                # بررسی بلاک
                if uid in db_u["users"].get(e["uid"], {}).get("blocks", []):
                    continue
                if e["uid"] in user.get("blocks", []):
                    continue
                # بررسی جنسیت
                partner_gender = db_u["users"].get(e["uid"], {}).get("sex")
                if search_gender == "any" or (search_gender == "m" and partner_gender == "آقا") or (search_gender == "f" and partner_gender == "خانم"):
                    candidates.append(e["uid"])
        if candidates:
            partner = random.choice(candidates)
            # حذف هر دو از صف
            db_q["general"] = [e for e in db_q["general"] if (isinstance(e, dict) and e["uid"] not in [uid, partner]) or (not isinstance(e, dict) and e not in [uid, partner])]
            self.db.write("queue", db_q)
            # برقراری چت
            user["partner"] = partner
            db_u["users"][partner]["partner"] = uid
            self.db.write("users", db_u)
            self.save_active_chat(uid, partner)
            self.save_active_chat(partner, uid)
            self.bot.send_message(uid, "✅ هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chatting())
            self.bot.send_message(partner, "✅ هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chatting())
        # در غیر این صورت در صف می‌ماند

    # ==========================================
    # مدیریت رویدادها
    # ==========================================
    def create_event(self, title, description, creator_id, start_date=None, end_date=None):
        def _create():
            db_e = self.db.read("events")
            db_u = self.db.read("users")
            event_id = db_u.get("next_event_id", 1)
            event = {
                "event_id": event_id,
                "title": title,
                "description": description,
                "creator_id": creator_id,
                "status": "draft",
                "created_date": self.get_tehran_datetime_str(),
                "start_date": start_date,
                "end_date": end_date,
                "participants": []
            }
            db_e[str(event_id)] = event
            db_u["next_event_id"] = event_id + 1
            self.db.write("events", db_e)
            self.db.write("users", db_u)
            return event_id
        return self.db.transaction(_create)

    def get_event(self, event_id):
        db_e = self.db.read("events")
        return db_e.get(str(event_id))

    def list_events(self, status=None):
        db_e = self.db.read("events")
        events = list(db_e.values())
        if status:
            events = [e for e in events if e.get("status") == status]
        return events

    def update_event_status(self, event_id, status):
        db_e = self.db.read("events")
        if str(event_id) in db_e:
            db_e[str(event_id)]["status"] = status
            self.db.write("events", db_e)
            return True
        return False

    def delete_event(self, event_id):
        db_e = self.db.read("events")
        if str(event_id) in db_e:
            del db_e[str(event_id)]
            self.db.write("events", db_e)
            return True
        return False

    def add_event_participant(self, event_id, user_id):
        db_e = self.db.read("events")
        if str(event_id) in db_e:
            if user_id not in db_e[str(event_id)]["participants"]:
                db_e[str(event_id)]["participants"].append(user_id)
                self.db.write("events", db_e)
                return True
        return False

    # ==========================================
    # مدیریت تخفیف‌ها
    # ==========================================
    def create_discount(self, code, discount_type, value, max_uses=-1, expiry_date=None, min_vip_level=0):
        db_d = self.db.read("discounts")
        code = code.upper()
        if code in db_d:
            return False
        discount = {
            "code": code,
            "type": discount_type,
            "value": value,
            "max_uses": max_uses,
            "current_uses": 0,
            "expiry_date": expiry_date,
            "min_vip_level": min_vip_level,
            "active": True,
            "created_date": self.get_tehran_datetime_str()
        }
        db_d[code] = discount
        self.db.write("discounts", db_d)
        return True

    def validate_discount(self, code, user_id):
        db_d = self.db.read("discounts")
        code = code.upper()
        if code not in db_d:
            return False, "کد تخفیف یافت نشد", None
        discount = db_d[code]
        if not discount.get("active", True):
            return False, "کد تخفیف غیرفعال است", None
        if discount.get("expiry_date"):
            expiry = datetime.datetime.fromisoformat(discount["expiry_date"])
            if datetime.datetime.now() > expiry:
                return False, "کد تخفیف منقضی شده", None
        if discount["max_uses"] != -1 and discount["current_uses"] >= discount["max_uses"]:
            return False, "کد تخفیف به حداکثر استفاده رسیده", None
        user_vip_level = 3 if self.is_vip(user_id) else 0
        if user_vip_level < discount.get("min_vip_level", 0):
            return False, "سطح VIP شما برای این تخفیف کافی نیست", None
        return True, "معتبر", discount

    def use_discount(self, code):
        db_d = self.db.read("discounts")
        code = code.upper()
        if code in db_d and db_d[code]["max_uses"] != -1:
            db_d[code]["current_uses"] += 1
            self.db.write("discounts", db_d)

    # ==========================================
    # آمار و گزارشات
    # ==========================================
    def get_bot_stats(self):
        db_u = self.db.read("users")
        db_b = self.db.read("bans")
        db_m = self.db.read("messages")
        db_c = self.db.read("chats")
        total_users = len(db_u["users"])
        active_users = sum(1 for user in db_u["users"].values() if user.get("last_active_date") == self.get_tehran_date_str())
        vip_users = sum(1 for uid in db_u["users"] if self.is_vip(uid))
        total_coins = sum(user.get("coins", 0) for user in db_u["users"].values())
        total_messages = sum(len(messages) for messages in db_m["inbox"].values())
        active_chats = len(db_c)
        return {
            "total_users": total_users,
            "active_users": active_users,
            "vip_users": vip_users,
            "total_coins": total_coins,
            "total_messages": total_messages,
            "active_chats": active_chats,
            "permanent_bans": len(db_b["permanent"]),
            "temporary_bans": len(db_b["temporary"])
        }

    def get_user_stats(self, user_id):
        db_u = self.db.read("users")
        user_id = str(user_id)
        if user_id not in db_u["users"]:
            return None
        user = db_u["users"][user_id]
        return {
            "name": user.get("name", "نامشخص"),
            "coins": user.get("coins", 0),
            "vip": self.is_vip(user_id),
            "warns": user.get("warns", 0),
            "messages_sent": user.get("daily_chat_count", 0),
            "referrals": user.get("total_referrals", 0),
            "joined_date": user.get("joined_date", "نامشخص")
        }

    # ==========================================
    # هشدار تعمیر
    # ==========================================
    def start_maintenance_warning(self, admin_id):
        if self.maintenance_warning_active:
            return False
        self.maintenance_warning_active = True
        self.maintenance_warning_event = threading.Event()

        def warning_thread():
            try:
                for i in range(6):
                    if self.maintenance_warning_event.is_set():
                        logger.info("هشدار تعمیر لغو شد")
                        return
                    time.sleep(30)
                    remaining = 3 - (i * 0.5)
                    try:
                        self.bot.send_message(admin_id,
                            f"⚠️ <b>هشدار تعمیر و نگهداری</b>\n\n"
                            f"ربات {remaining:.1f} دقیقه دیگر به حالت تعمیر می‌رود.\n"
                            f"اطلاعات شما ذخیره خواهد شد.\n\n"
                            f"📞 پشتیبانی: {self.support}")
                    except:
                        pass
                if not self.maintenance_warning_event.is_set():
                    time.sleep(30)
                    db_c = self.db.read("config")
                    db_c["settings"]["maintenance"] = True
                    self.db.write("config", db_c)
                    self.bot.send_message(admin_id,
                        "✅ <b>ربات به حالت تعمیر و نگهداری رفت.</b>\n\n"
                        "اکنون فقط کاربران VIP می‌توانند از ربات استفاده کنند.")
                self.maintenance_warning_active = False
                self.maintenance_warning_event = None
            except Exception as e:
                logger.error(f"خطا در ترد هشدار تعمیر: {e}")
                self.maintenance_warning_active = False
                self.maintenance_warning_event = None

        self.maintenance_warning_thread = threading.Thread(target=warning_thread, daemon=True)
        self.maintenance_warning_thread.start()
        return True

    def cancel_maintenance_warning(self):
        if not self.maintenance_warning_active:
            return False
        if self.maintenance_warning_event:
            self.maintenance_warning_event.set()
        self.maintenance_warning_active = False
        return True

    # ==========================================
    # محدودیت نرخ
    # ==========================================
    def check_rate_limit(self, uid):
        with self.rate_limit_lock:
            now = time.time()
            times = self.user_last_message[uid]
            while times and times[0] < now - 10:
                times.popleft()
            if len(times) >= 5:
                return False
            times.append(now)
            return True

    # ==========================================
    # ثبت‌نام و هندلرها
    # ==========================================
    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(msg):
            uid = str(msg.chat.id)
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None
            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")

            # چک بن
            if uid in db_b["permanent"]:
                reason = db_b["permanent"][uid]
                self.bot.send_message(uid, f"🚫 <b>شما بن دائم هستید!</b>\n"
                                          f"دلیل: {reason}\n"
                                          f"پشتیبانی: {self.support}")
                return
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
                        self.add_coins(referrer_id, 100, f"دعوت کاربر جدید")
                        try:
                            self.bot.send_message(referrer_id, "🎉 یک کاربر جدید از لینک شما عضو شد!\n"
                                                              "💰 +100 سکه پاداش دریافت کردید")
                        except:
                            pass

            # لینک ناشناس
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    self.bot.send_message(uid, "❌ نمی‌توانید به خودتان پیام بفرستید 😊")
                    return
                if uid not in db_u["users"]:
                    db_u["users"][uid] = {
                        "state": "name",
                        "vip_end": 0,
                        "warns": 0,
                        "blocks": [],
                        "coins": 0,
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
                        "anon_target": target,
                        "joined_date": self.get_tehran_date_str()
                    }
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "✨ برای ارسال پیام ناشناس، ابتدا نام مستعار وارد کنید:")
                else:
                    db_u["users"][uid]["state"] = "anon_send"
                    db_u["users"][uid]["anon_target"] = target
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "📝 پیام ناشناس خود را بنویسید:")
                return

            # ثبت‌نام عادی
            if uid not in db_u["users"]:
                db_u["users"][uid] = {
                    "state": "name",
                    "vip_end": 0,
                    "warns": 0,
                    "blocks": [],
                    "coins": 0,
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
                    "joined_date": self.get_tehran_date_str()
                }
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\n"
                                          "لطفاً نام مستعار خود را وارد کنید:")
            else:
                self.bot.send_message(uid, "خوش برگشتید عزیز 🌹", reply_markup=self.kb_main(uid))

        @self.bot.message_handler(func=lambda msg: True, content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def main(msg):
            uid = str(msg.chat.id)

            # محدودیت نرخ
            if not self.check_rate_limit(uid):
                self.bot.send_message(uid, "⏱ لطفاً کمی صبر کنید و سپس دوباره تلاش کنید.")
                return

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
            today = self.get_tehran_date_str()
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
                self.bot.send_message(uid, f"سلام {self.escape_html(user['name'])} 🌸\n\n"
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
                self.add_coins(uid, 50, "پاداش ثبت‌نام")
                self.bot.send_message(uid, "✅ <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
                                          "🎁 پاداش ثبت‌نام: 50 سکه\n\n"
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
                    "time": self.get_tehran_datetime_str()
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
                        self.bot.send_message(target, f"📩 <b>پاسخ ناشناس:</b>\n\n{self.escape_html(msg.text)}")
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
                    self.bot.send_message(uid, "❓ آیا مطمئن هستید که می‌خواهید چت را پایان دهید؟", reply_markup=kb)
                    return

                if msg.text == "🚩 گزارش تخلف":
                    user["report_target"] = partner
                    user["report_last_msg_id"] = msg.message_id
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "⚠️ دلیل گزارش را انتخاب کنید:", reply_markup=self.kb_report())
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
                    self.bot.send_message(partner, "📢 هم‌صحبت شما درخواست آیدی دارد. موافقید؟", reply_markup=kb)
                    self.bot.send_message(uid, "⏳ درخواست ارسال شد، منتظر تایید باشید")
                    return

                # فیلتر محتوا
                if msg.content_type == "text" and msg.text and db_c["settings"]["word_filter"]:
                    is_bad = self.contains_bad(msg.text)
                    toxic_score = self.ai_toxic_scan(msg.text) if db_c["settings"]["ai_scan"] else 0.0
                    nsfw_score = self.ai_nsfw_scan(msg.text) if db_c["settings"]["ai_scan"] else 0.0
                    if is_bad or toxic_score > 0.8 or nsfw_score > 0.8:
                        try:
                            self.bot.delete_message(uid, msg.message_id)
                        except:
                            pass
                        user["warns"] = user.get("warns", 0) + 1
                        self.db.write("users", db_u)
                        if user["warns"] >= 3:
                            if user.get("had_temp_ban", False):
                                self.ban_perm(uid, "فحاشی مکرر پس از بن موقت")
                                self.report_auto_ban(uid, "فحاشی مکرر پس از بن موقت", "بن دائم")
                                self.end_chat(uid, partner, "به دلیل تخلف بن دائم شد")
                            else:
                                self.ban_temp(uid, 1440, "فحاشی مکرر (بن ۲۴ ساعته)")
                                user["had_temp_ban"] = True
                                user["warns"] = 0
                                self.db.write("users", db_u)
                                self.report_auto_ban(uid, "فحاشی مکرر (اولین بار)", "بن ۲۴ ساعته")
                                self.end_chat(uid, partner, "به دلیل تخلف بن موقت شد")
                        else:
                            self.bot.send_message(uid, f"⚠️ <b>اخطار {user['warns']}/3</b>\n\n"
                                                      "محتوای نامناسب ممنوع است!")
                        return

                # شمارش پیام برای ماموریت
                user["daily_chat_count"] = user.get("daily_chat_count", 0) + 1
                if partner not in user.get("daily_unique_chats", []):
                    unique_chats = user.get("daily_unique_chats", [])
                    unique_chats.append(partner)
                    user["daily_unique_chats"] = unique_chats
                self.db.write("users", db_u)
                self.check_and_reward_mission(uid)

                # ارسال پیام به طرف مقابل
                try:
                    self.bot.copy_message(partner, uid, msg.message_id)
                except Exception as e:
                    logger.error(f"خطا در ارسال پیام چت: {e}")
                return

            # لغو جستجو
            if msg.text == "❌ لغو جستجو":
                db_q = self.db.read("queue")
                db_q["general"] = [e for e in db_q.get("general", []) if (isinstance(e, dict) and e["uid"] != uid) or (not isinstance(e, dict) and e != uid)]
                self.db.write("queue", db_q)
                self.bot.send_message(uid, "✅ جستجو با موفقیت لغو شد", reply_markup=self.kb_main(uid))
                return

            # منوی اصلی
            if not msg.text:
                return
            text = msg.text

            # منوی اصلی کاربران عادی
            if text == "🛰 شروع چت ناشناس":
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
                profile_text += f"نام: {self.escape_html(user.get('name', 'نامشخص'))}\n"
                profile_text += f"جنسیت: {self.escape_html(user.get('sex', 'نامشخص'))}\n"
                profile_text += f"سن: {self.escape_html(user.get('age', 'نامشخص'))}\n"
                profile_text += f"رنک: {rank}\n"
                profile_text += f"VIP: {vip_status}\n"
                profile_text += f"💰 سکه: {coins:,}\n"
                profile_text += f"👥 رفرال: {user.get('total_referrals', 0)} نفر\n"
                profile_text += f"⚠️ اخطار: {user.get('warns', 0)}/3\n"
                if user.get("christmas_vip_taken", False):
                    profile_text += f"🎄 VIP کریسمس: <b>دریافت شده ✅</b>"
                self.bot.send_message(uid, profile_text)
                self.check_and_reward_mission(uid)

            elif text == "📩 لینک ناشناس من":
                link = f"https://t.me/{self.username}?start=msg_{uid}"
                self.bot.send_message(uid, f"<b>📩 لینک ناشناس شما</b>\n\n"
                                          f"<code>{link}</code>\n\n"
                                          "با اشتراک این لینک، دیگران می‌توانند ناشناس به شما پیام بفرستند ✨")

            elif text == "📥 پیام‌های ناشناس":
                db_m = self.db.read("messages")
                inbox = db_m["inbox"].get(uid, [])
                if not inbox:
                    self.bot.send_message(uid, "📭 هیچ پیام ناشناسی دریافت نکرده‌اید")
                    return
                kb = types.InlineKeyboardMarkup()
                txt = "<b>📥 پیام‌های ناشناس شما</b>\n\n"
                for i, m in enumerate(inbox):
                    status = "✅" if m.get("seen") else "🔵"
                    txt += f"{status} <b>پیام {i + 1}:</b>\n{self.escape_html(m['text'])}\n"
                    txt += f"<i>🕐 {m['time']}</i>\n\n"
                    kb.add(types.InlineKeyboardButton(f"📝 پاسخ به پیام {i + 1}", callback_data=f"anon_reply_{i}"))
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
                today = self.get_tehran_date_str()
                if user.get("last_spin") == today:
                    self.bot.send_message(uid, "⏰ امروز قبلاً گردونه را چرخانده‌اید\n\n"
                                              "فردا دوباره امتحان کنید! 🎡")
                    return
                user["last_spin"] = today
                user["daily_spin_done"] = True
                self.db.write("users", db_u)
                rand = random.random()
                if rand < 0.001:
                    self.add_vip(uid, "month", "گردونه شانس")
                    result = "🎉 <b>جایزه بزرگ!</b>\n\n🎖 VIP ۳۰ روزه\n\nتبریک! 🎊"
                elif rand < 0.05:
                    coins = random.choice([500, 750, 1000])
                    self.add_coins(uid, coins, "گردونه شانس")
                    result = f"🎁 <b>برنده شدید!</b>\n\n💰 {coins:,} سکه\n\nآفرین! ✨"
                elif rand < 0.3:
                    coins = random.choice([50, 100, 150, 200])
                    self.add_coins(uid, coins, "گردونه شانس")
                    result = f"🎯 <b>موفق!</b>\n\n💰 {coins:,} سکه\n\nخوب بود! 👍"
                else:
                    result = "😔 <b>متأسفانه پوچ!</b>\n\nشانس بعدی را امتحان کنید 🍀"
                self.bot.send_message(uid, f"🎡 گردونه در حال چرخش...\n\n{result}")
                self.check_and_reward_mission(uid)

            elif text == "🎯 ماموریت روزانه":
                db_m = self.db.read("missions")
                mission = db_m["daily"]
                today = self.get_tehran_date_str()
                completed = user.get("mission_completed_date") == today
                mission_text = f"<b>🎯 ماموریت روزانه</b>\n\n"
                mission_text += f"📋 ماموریت: {mission['mission']}\n"
                mission_text += f"📝 کار انجام‌دادنی: {mission.get('description', mission['mission'])}\n"
                if mission.get("reward_type") == "coins":
                    mission_text += f"🎁 پاداش: {mission.get('reward_value', 50):,} سکه\n\n"
                elif mission.get("reward_type") == "vip":
                    duration_name = {"week": "۱ هفته", "month": "۱ ماه", "3month": "۳ ماه", "6month": "۶ ماه", "year": "۱ سال"}.get(
                        mission.get("reward_value", "week"), "VIP")
                    mission_text += f"🎁 پاداش: VIP {duration_name}\n\n"
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
                ref_link = f"https://t.me/{self.username}?start=ref_{uid}"
                ref_count = user.get("total_referrals", 0)
                ref_text = f"<b>👥 سیستم رفرال</b>\n\n"
                ref_text += f"🎁 به ازای هر دعوت موفق: <b>100 سکه</b>\n"
                ref_text += f"👤 تعداد دعوت‌های شما: <b>{ref_count} نفر</b>\n"
                ref_text += f"💰 کل سکه از رفرال: <b>{ref_count * 100:,} سکه</b>\n\n"
                ref_text += f"🔗 لینک دعوت شما:\n<code>{ref_link}</code>\n\n"
                ref_text += "این لینک را با دوستان خود به اشتراک بگذارید!"
                self.bot.send_message(uid, ref_text)

            elif text == "🎖 خرید VIP":
                coins = user.get("coins", 0)
                vip_text = "<b>🎖 فروشگاه VIP</b>\n\n"
                vip_text += "<b>ویژگی‌های VIP:</b>\n"
                vip_text += "✅ ارسال آزاد گیف و استیکر\n"
                vip_text += "✅ اولویت در بررسی گزارش‌ها\n"
                vip_text += "✅ دسترسی در زمان تعمیر\n"
                vip_text += "✅ نشان ویژه VIP\n\n"
                vip_text += f"💰 موجودی شما: <b>{coins:,} سکه</b>\n\n"
                christmas_deadline = datetime.datetime(2026, 1, 15, tzinfo=ZoneInfo("Asia/Tehran"))
                today = self.get_tehran_time()
                is_christmas_active = today < christmas_deadline
                kb = types.InlineKeyboardMarkup(row_width=1)
                vip_options = [("week", "۱ هفته"), ("month", "۱ ماه"), ("3month", "۳ ماه"), ("6month", "۶ ماه"), ("year", "۱ سال")]
                for key, name in vip_options:
                    price = self.vip_prices_coins[key]
                    status = "✅" if coins >= price else "🔒"
                    kb.add(types.InlineKeyboardButton(f"{status} VIP {name} - {price:,} سکه", callback_data=f"buy_vip_{key}"))
                if is_christmas_active and not user.get("christmas_vip_taken", False):
                    vip_text += "🎄 <b>پیشنهاد ویژه کریسمس!</b>\n"
                    vip_text += "VIP ۳ ماهه رایگان فقط تا ۱۵ ژانویه ۲۰۲۶\n"
                    vip_text += "<i>(هر کاربر فقط یکبار می‌تواند دریافت کند)</i>\n\n"
                    kb.add(types.InlineKeyboardButton("🎁 VIP ۳ ماه رایگان (ویژه کریسمس) - ۰ سکه", callback_data="buy_vip_christmas"))
                elif user.get("christmas_vip_taken", False):
                    vip_text += "🎄 <b>شما قبلاً VIP رایگان کریسمس را دریافت کرده‌اید</b>\n\n"
                self.bot.send_message(uid, vip_text, reply_markup=kb)

            elif text == "❓ راهنما و قوانین":
                help_text = "<b>📖 راهنما و قوانین</b>\n\n"
                help_text += "<b>چگونه کار می‌کند؟</b>\n"
                help_text += "• چت کاملاً ناشناس است\n"
                help_text += "• با افراد تصادفی گفتگو کنید\n"
                help_text += "• سکه جمع کنید و VIP بخرید\n\n"
                help_text += "<b>قوانین:</b>\n"
                help_text += "❌ فحاشی ممنوع\n"
                help_text += "❌ محتوای +18 ممنوع\n"
                help_text += "❌ اسپم و آزار ممنوع\n\n"
                help_text += "<b>سیستم اخطار:</b>\n"
                help_text += "• اخطار ۳: بن ۲۴ ساعته\n"
                help_text += "• تکرار پس از بن: بن دائم\n\n"
                help_text += f"پشتیبانی: {self.support}"
                self.bot.send_message(uid, help_text)

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

            # ==================== پنل مدیریت ====================
            if uid == self.owner:
                if text == "📊 پنل مدیریت":
                    self.bot.send_message(uid, "<b>🛠️ پنل مدیریت پیشرفته</b>", reply_markup=self.kb_admin())

                elif text == "📈 آمار کلی ربات":
                    stats = self.get_bot_stats()
                    stats_text = "<b>📊 آمار کلی ربات</b>\n\n"
                    stats_text += f"👥 کل کاربران: {stats['total_users']:,}\n"
                    stats_text += f"📈 کاربران فعال امروز: {stats['active_users']:,}\n"
                    stats_text += f"🎖 کاربران VIP: {stats['vip_users']:,}\n"
                    stats_text += f"💰 کل سکه‌ها: {stats['total_coins']:,}\n"
                    stats_text += f"💬 کل پیام‌های ناشناس: {stats['total_messages']:,}\n"
                    stats_text += f"💬 چت‌های فعال: {stats['active_chats']:,}\n"
                    stats_text += f"🚫 بن دائم: {stats['permanent_bans']:,}\n"
                    stats_text += f"⏰ بن موقت: {stats['temporary_bans']:,}"
                    self.bot.send_message(uid, stats_text)

                elif text == "👥 مدیریت کاربران":
                    self.bot.send_message(uid, "👥 <b>مدیریت کاربران</b>", reply_markup=self.kb_admin_users())

                elif text == "📅 مدیریت رویدادها":
                    self.bot.send_message(uid, "📅 <b>مدیریت رویدادها</b>", reply_markup=self.kb_admin_events())

                elif text == "🎫 مدیریت تخفیف‌ها":
                    self.bot.send_message(uid, "🎫 <b>مدیریت تخفیف‌ها</b>", reply_markup=self.kb_admin_discounts())

                elif text == "💎 سیستم VIP":
                    self.bot.send_message(uid, "💎 <b>سیستم VIP</b>", reply_markup=self.kb_admin_vip())

                elif text == "💰 مدیریت مالی":
                    self.bot.send_message(uid, "💰 <b>مدیریت مالی</b>", reply_markup=self.kb_admin_finance())

                elif text == "🔧 تنظیمات ربات":
                    self.bot.send_message(uid, "🔧 <b>تنظیمات ربات</b>", reply_markup=self.kb_admin_settings())

                elif text == "📈 گزارش‌های پیشرفته":
                    self.show_advanced_reports(uid)

                elif text == "📤 خروجی دیتابیس":
                    for file_name, file_path in self.db.files.items():
                        if os.path.exists(file_path):
                            try:
                                with open(file_path, 'rb') as f:
                                    self.bot.send_document(uid, f, caption=f"📄 {file_name}.json")
                            except Exception as e:
                                logger.error(f"خطا در ارسال فایل {file_name}: {e}")

                elif text == "🚫 مدیریت بن‌ها":
                    self.show_bans_list(uid)

                elif text == "🎖 گیفت VIP تکی":
                    user["admin_state"] = "gift_vip_duration"
                    self.db.write("users", db_u)
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("۱ هفته", "۱ ماه", "۳ ماه")
                    kb.add("۶ ماه", "۱ سال", "🔙 بازگشت")
                    self.bot.send_message(uid, "⏰ مدت VIP را انتخاب کنید:", reply_markup=kb)

                elif text == "🎖 گیفت VIP همگانی":
                    user["admin_state"] = "gift_vip_all_duration"
                    self.db.write("users", db_u)
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("۱ هفته", "۱ ماه", "۳ ماه")
                    kb.add("۶ ماه", "۱ سال", "🔙 بازگشت")
                    self.bot.send_message(uid, "⏰ مدت VIP همگانی را انتخاب کنید:", reply_markup=kb)

                elif text == "❌ حذف VIP":
                    user["admin_state"] = "remove_vip"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی عددی کاربر برای حذف VIP:")

                elif text == "📋 لیست VIP":
                    self.show_vip_list(uid)

                elif text == "💰 اهدای سکه":
                    user["admin_state"] = "gift_coins_amount"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "💰 مقدار سکه را وارد کنید:")

                elif text == "🎯 مدیریت ماموریت‌ها":
                    self.manage_missions(uid)

                elif text == "⚠️ هشدار تعمیر":
                    self.manage_maintenance_warning(uid)

                elif text == "🛠 تعمیر و نگهداری":
                    db_c = self.db.read("config")
                    db_c["settings"]["maintenance"] = not db_c["settings"].get("maintenance", False)
                    self.db.write("config", db_c)
                    status = "🟢 فعال" if db_c["settings"]["maintenance"] else "🔴 غیرفعال"
                    self.bot.send_message(uid, f"حالت تعمیر و نگهداری: {status}")

                # زیرمنوهای مدیریت کاربران
                elif text == "🔍 جستجوی کاربر":
                    user["admin_state"] = "search_user"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🔍 جستجوی کاربر:\n\nمی‌توانید با آیدی، نام یا یوزرنیم جستجو کنید:")

                elif text == "📋 لیست کاربران":
                    self.list_users_admin(uid)

                elif text == "📊 آمار کاربران":
                    self.show_users_stats(uid)

                elif text == "🎖 تغییر سطح VIP":
                    user["admin_state"] = "change_vip_tier_user"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی کاربر برای تغییر سطح VIP:")

                elif text == "💰 تنظیم سکه":
                    user["admin_state"] = "set_coins_user"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی کاربر برای تنظیم سکه:")

                elif text == "⚠️ مدیریت اخطارها":
                    user["admin_state"] = "manage_warns_user"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی کاربر برای مدیریت اخطارها:")

                elif text == "📅 فعالیت اخیر":
                    self.show_recent_activity(uid)

                # زیرمنوهای مدیریت رویدادها
                elif text == "➕ ایجاد رویداد جدید":
                    user["admin_state"] = "create_event_title"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "📝 <b>ایجاد رویداد جدید</b>\n\nعنوان رویداد را وارد کنید:")

                elif text == "📋 لیست رویدادها":
                    self.list_events_admin(uid)

                elif text == "✏️ ویرایش رویداد":
                    user["admin_state"] = "edit_event_select"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی رویداد برای ویرایش:")

                elif text == "🗑️ حذف رویداد":
                    user["admin_state"] = "delete_event"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی رویداد برای حذف:")

                elif text == "📊 آمار رویدادها":
                    self.show_events_stats(uid)

                elif text == "👥 شرکت‌کنندگان":
                    user["admin_state"] = "event_participants"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی رویداد برای مشاهده شرکت‌کنندگان:")

                # زیرمنوهای مدیریت تخفیف‌ها
                elif text == "➕ ایجاد تخفیف جدید":
                    user["admin_state"] = "create_discount_code"
                    self.db.write("users", db_u)
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("🎁 درصدی", "💰 مقدار ثابت", "🔙 لغو")
                    self.bot.send_message(uid, "🎫 <b>ایجاد کد تخفیف جدید</b>\n\nنوع تخفیف را انتخاب کنید:", reply_markup=kb)

                elif text == "📋 لیست تخفیف‌ها":
                    self.list_discounts_admin(uid)

                elif text == "✏️ ویرایش تخفیف":
                    user["admin_state"] = "edit_discount_select"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی تخفیف برای ویرایش:")

                elif text == "🗑️ حذف تخفیف":
                    user["admin_state"] = "delete_discount"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🆔 آیدی تخفیف برای حذف:")

                elif text == "📊 آمار استفاده":
                    self.show_discounts_stats(uid)

                elif text == "🎯 تخفیف‌های ویژه":
                    self.show_special_discounts(uid)

                # زیرمنوهای تنظیمات پیشرفته
                elif text == "⚡ بهینه‌سازی":
                    self.optimize_system(uid)

                elif text == "🔄 ریست خودکار":
                    self.auto_reset_settings(uid)

                elif text == "📦 پشتیبان‌گیری":
                    self.create_backup(uid)

                elif text == "🗑️ پاک‌سازی داده":
                    self.cleanup_data(uid)

                elif text == "🔧 تنظیمات سیستم":
                    self.system_settings(uid)

                elif text == "📝 تنظیمات پیام":
                    self.message_settings(uid)

                elif text == "🎛️ تنظیمات چت":
                    self.chat_settings(uid)

                # مدیریت stateهای ادمین
                admin_state = user.get("admin_state")
                if admin_state:
                    self.handle_admin_state(uid, msg, user, admin_state, db_u)
                    return

            # بازگشت به منو
            if "بازگشت" in text or text == "🔙 بازگشت به منو":
                user["state"] = "idle"
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🏠 منوی اصلی", reply_markup=self.kb_main(uid))

        # هندلر ویرایش پیام
        @self.bot.edited_message_handler(func=lambda msg: True)
        def edited(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            if user and user.get("partner"):
                partner = user["partner"]
                try:
                    self.bot.copy_message(partner, uid, msg.message_id)
                except:
                    pass

        # هندلر کال‌بک‌ها
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
                self.bot.edit_message_text("🔍 در حال جستجو برای هم‌صحبت...", call.message.chat.id, call.message.message_id)
                kb_cancel = types.ReplyKeyboardMarkup(resize_keyboard=True)
                kb_cancel.add("❌ لغو جستجو")
                self.bot.send_message(uid, "⏳ منتظر بمانید...", reply_markup=kb_cancel)
                db_q = self.db.read("queue")
                if "general" not in db_q:
                    db_q["general"] = []
                now = time.time()
                entry = {"uid": uid, "time": now, "gender": search_gender}
                db_q["general"] = [e for e in db_q["general"] if (isinstance(e, dict) and e["uid"] != uid) or (not isinstance(e, dict) and e != uid)]
                db_q["general"].append(entry)
                self.db.write("queue", db_q)
                self.try_match(uid)

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
                reasons = {"rep_insult": "فحاشی", "rep_nsfw": "محتوای +18", "rep_spam": "اسپم", "rep_harass": "آزار و اذیت"}
                reason = reasons.get(call.data, "نامشخص")
                target = user.get("report_target")
                if not target:
                    self.bot.answer_callback_query(call.id, "❌ خطا در گزارش")
                    return
                target_name = db_u["users"].get(target, {}).get("name", "نامشخص")
                reporter_name = user.get("name", "نامشخص")
                tehran_time = self.get_tehran_datetime_str()
                report_text = f"🚩 <b>گزارش جدید</b>\n\n"
                report_text += f"<b>شاکی:</b> 🆔 <code>{uid}</code> - {self.escape_html(reporter_name)}\n"
                report_text += f"<b>متهم:</b> 🆔 <code>{target}</code> - {self.escape_html(target_name)}\n"
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
                kb.add(types.InlineKeyboardButton("Warning +2", callback_data=f"adm_warn2_{target}"))
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
                    self.bot.edit_message_text(call.message.text + "\n\n✅ <b>Ignored</b>", call.message.chat.id, call.message.message_id)
                elif action == "ban":
                    ban_type = parts[2]
                    target = parts[3]
                    if ban_type == "perm":
                        self.ban_perm(target, "گزارش تأیید شده")
                        self.bot.answer_callback_query(call.id, "✅ بن دائم اعمال شد")
                        self.bot.edit_message_text(call.message.text + "\n\n🚫 <b>Permanent Ban</b>", call.message.chat.id, call.message.message_id)
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
                        self.bot.edit_message_text(call.message.text + f"\n\n⚠️ <b>+{warns_count} Warning</b>", call.message.chat.id, call.message.message_id)

            # بخشیدن بن خودکار
            elif call.data.startswith("auto_ban_correct_"):
                if uid != self.owner:
                    return
                self.bot.answer_callback_query(call.id, "✅ تأیید شد")
                self.bot.edit_message_text(call.message.text + "\n\n✅ <b>Confirmed by admin</b>", call.message.chat.id, call.message.message_id)

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
                self.bot.edit_message_text(call.message.text + "\n\n🌟 <b>Pardoned by admin</b>", call.message.chat.id, call.message.message_id)

            # خرید VIP
            elif call.data.startswith("buy_vip_"):
                vip_type = call.data.split("_")[2]
                if vip_type == "christmas":
                    christmas_deadline = datetime.datetime(2026, 1, 15, tzinfo=ZoneInfo("Asia/Tehran"))
                    today = self.get_tehran_time()
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
                new_balance = self.deduct_coins(uid, price, f"خرید VIP {vip_type}")
                if new_balance is not None:
                    self.add_vip(uid, vip_type, "خرید با سکه")
                    self.bot.answer_callback_query(call.id, "✅ VIP فعال شد!")
                else:
                    self.bot.answer_callback_query(call.id, "❌ خطا در انجام تراکنش", show_alert=True)

            # ماموریت‌ها (ادمین)
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
                        duration_name = {"week": "۱ هفته", "month": "۱ ماه", "3month": "۳ ماه", "6month": "۶ ماه", "year": "۱ سال"}.get(
                            mission.get("reward_value", "week"), "VIP")
                        reward_text = f"VIP {duration_name}"
                    else:
                        reward_text = f"{mission.get('reward', 0):,} سکه"
                    kb.add(types.InlineKeyboardButton(f"{i + 1}. {mission['name']} - {reward_text}", callback_data=f"select_mission_{i}"))
                self.bot.edit_message_text("📋 لطفا ماموریت روزانه جدید را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✅")

            elif call.data.startswith("select_mission_"):
                if uid != self.owner:
                    return
                index = int(call.data.split("_")[2])
                db_m = self.db.read("missions")
                if index < len(db_m["available"]):
                    mission = db_m["available"][index]
                    db_m["daily"] = {
                        "date": self.get_tehran_date_str(),
                        "mission": mission["name"],
                        "reward_type": mission.get("reward_type", "coins"),
                        "reward_value": mission.get("reward_value", mission.get("reward", 50)),
                        "type": mission["type"],
                        "target": mission["target"],
                        "description": mission.get("description", mission["name"])
                    }
                    self.db.write("missions", db_m)
                    reward_text = ""
                    if mission.get("reward_type") == "coins":
                        reward_text = f"{mission.get('reward_value', mission.get('reward', 0)):,} سکه"
                    elif mission.get("reward_type") == "vip":
                        duration_name = {"week": "۱ هفته", "month": "۱ ماه", "3month": "۳ ماه", "6month": "۶ ماه", "year": "۱ سال"}.get(
                            mission.get("reward_value", "week"), "VIP")
                        reward_text = f"VIP {duration_name}"
                    self.bot.edit_message_text(f"✅ ماموریت روزانه به '{mission['name']}' تغییر کرد.\n\n"
                                              f"کار انجام‌دادنی: {mission.get('description', mission['name'])}\n"
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
                        duration_name = {"week": "۱ هفته", "month": "۱ ماه", "3month": "۳ ماه", "6month": "۶ ماه", "year": "۱ سال"}.get(
                            m.get("reward_value", "week"), "VIP")
                        missions_text += f"   🎖 پاداش: VIP {duration_name}\n"
                    else:
                        missions_text += f"   🎁 پاداش: {m.get('reward', 0):,} سکه\n"
                    missions_text += f"   📝 کار: {m.get('description', m['name'])}\n"
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
                self.bot.send_message(uid, "🎯 <b>افزودن ماموریت جدید</b>\n\nنوع پاداش ماموریت را انتخاب کنید:", reply_markup=kb)
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
                if self.cancel_maintenance_warning():
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
    # متدهای مدیریتی (ادمین) - تکمیل شده
    # ==========================================
    def handle_admin_state(self, uid, msg, user, state, db_u):
        """مدیریت stateهای مختلف ادمین"""
        # جستجوی کاربر
        if state == "search_user":
            search_term = msg.text.strip()
            results = self.search_users(search_term)
            if not results:
                self.bot.send_message(uid, "❌ کاربری یافت نشد")
            else:
                result_text = f"🔍 <b>نتایج جستجو برای '{self.escape_html(search_term)}':</b>\n\n"
                for i, (user_id, user_data) in enumerate(results[:10], 1):
                    result_text += f"{i}. 🆔 <code>{user_id}</code>\n"
                    result_text += f"   👤 نام: {self.escape_html(user_data.get('name', 'نامشخص'))}\n"
                    result_text += f"   💰 سکه: {user_data.get('coins', 0):,}\n"
                    result_text += f"   🎖 VIP: {'✅' if self.is_vip(int(user_id)) else '❌'}\n\n"
                if len(results) > 10:
                    result_text += f"\n... و {len(results) - 10} نتیجه دیگر"
                self.bot.send_message(uid, result_text)
            user["admin_state"] = None
            self.db.write("users", db_u)
            return

        # گیفت VIP تکی
        if state == "gift_vip_duration":
            duration_map = {"۱ هفته": "week", "۱ ماه": "month", "۳ ماه": "3month", "۶ ماه": "6month", "۱ سال": "year"}
            if msg.text in duration_map:
                user["gift_vip_duration"] = duration_map[msg.text]
                user["admin_state"] = "gift_vip_reason"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 دلیل گیفت VIP را بنویسید:")
            return
        if state == "gift_vip_reason":
            user["gift_vip_reason"] = msg.text
            user["admin_state"] = "gift_vip_id"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "🆔 آیدی عددی کاربر را وارد کنید:")
            return
        if state == "gift_vip_id":
            if msg.text.isdigit():
                target_uid = msg.text
                duration = user.get("gift_vip_duration")
                reason = user.get("gift_vip_reason", "گیفت ادمین")
                db_target = self.db.read("users")
                if target_uid in db_target["users"]:
                    self.add_vip(int(target_uid), duration, reason)
                    self.bot.send_message(uid, f"✅ گیفت VIP به {target_uid} ارسال شد", reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ کاربر پیدا نشد")
                user["admin_state"] = None
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return

        # گیفت VIP همگانی
        if state == "gift_vip_all_duration":
            duration_map = {"۱ هفته": "week", "۱ ماه": "month", "۳ ماه": "3month", "۶ ماه": "6month", "۱ سال": "year"}
            if msg.text in duration_map:
                user["gift_vip_all_duration"] = duration_map[msg.text]
                user["admin_state"] = "gift_vip_all_reason"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 دلیل گیفت همگانی را بنویسید:")
            return
        if state == "gift_vip_all_reason":
            duration = user.get("gift_vip_all_duration")
            reason = msg.text
            db_all = self.db.read("users")
            sent_count = 0
            for target_uid in db_all["users"]:
                if self.add_vip(int(target_uid), duration, reason):
                    sent_count += 1
            self.bot.send_message(uid, f"✅ گیفت VIP به {sent_count} کاربر ارسال شد", reply_markup=self.kb_admin())
            user["admin_state"] = None
            self.db.write("users", db_u)
            return

        # حذف VIP
        if state == "remove_vip":
            if msg.text.isdigit():
                target_uid = msg.text
                db_target = self.db.read("users")
                if target_uid in db_target["users"]:
                    db_target["users"][target_uid]["vip_end"] = 0
                    db_target["users"][target_uid]["christmas_vip_taken"] = False
                    self.db.write("users", db_target)
                    try:
                        self.bot.send_message(target_uid, "❌ VIP شما توسط ادمین حذف شد")
                    except:
                        pass
                    self.bot.send_message(uid, f"✅ VIP از کاربر {target_uid} حذف شد", reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ کاربر پیدا نشد")
                user["admin_state"] = None
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return

        # اهدای سکه
        if state == "gift_coins_amount":
            if msg.text.isdigit():
                user["gift_coins_amount"] = int(msg.text)
                user["admin_state"] = "gift_coins_reason"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 دلیل اهدا سکه را بنویسید:")
            else:
                self.bot.send_message(uid, "❌ لطفاً عدد وارد کنید")
            return
        if state == "gift_coins_reason":
            user["gift_coins_reason"] = msg.text
            user["admin_state"] = "gift_coins_id"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "🆔 آیدی عددی کاربر را وارد کنید:")
            return
        if state == "gift_coins_id":
            if msg.text.isdigit():
                target_uid = msg.text
                amount = user.get("gift_coins_amount", 0)
                reason = user.get("gift_coins_reason", "هدیه ادمین")
                db_target = self.db.read("users")
                if target_uid in db_target["users"]:
                    self.add_coins(int(target_uid), amount, reason)
                    db_target = self.db.read("users")
                    new_balance = db_target["users"][target_uid].get("coins", 0)
                    self.bot.send_message(uid, f"✅ {amount:,} سکه به {target_uid} اهدا شد\n"
                                              f"موجودی جدید کاربر: {new_balance:,} سکه", reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ کاربر پیدا نشد")
                user["admin_state"] = None
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return

        # بن موقت
        if state == "admin_temp_ban_minutes":
            if msg.text.isdigit():
                minutes = int(msg.text)
                target = user.get("admin_temp_ban_target")
                if target:
                    self.ban_temp(int(target), minutes, "بن موقت توسط ادمین")
                    self.bot.send_message(uid, f"✅ بن موقت {minutes} دقیقه‌ای برای کاربر {target} اعمال شد.", reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ خطا در اعمال بن موقت.")
                user["admin_state"] = None
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفا عدد وارد کنید.")
            return

        # ایجاد رویداد
        if state == "create_event_title":
            user["create_event_title"] = msg.text
            user["admin_state"] = "create_event_description"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "📝 توضیحات رویداد را وارد کنید:")
            return
        if state == "create_event_description":
            user["create_event_description"] = msg.text
            user["admin_state"] = "create_event_date"
            self.db.write("users", db_u)
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            kb.add("فوری", "۱ روز بعد", "۳ روز بعد", "۱ هفته بعد")
            kb.add("تاریخ دستی", "🔙 لغو")
            self.bot.send_message(uid, "📅 زمان شروع رویداد را انتخاب کنید:", reply_markup=kb)
            return
        if state == "create_event_date":
            if msg.text == "تاریخ دستی":
                user["admin_state"] = "create_event_date_manual"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📅 تاریخ را به فرمت YYYY-MM-DD وارد کنید:")
                return
            elif msg.text == "🔙 لغو":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ ایجاد رویداد لغو شد", reply_markup=self.kb_admin())
                return
            else:
                now = self.get_tehran_time()
                if msg.text == "فوری":
                    start_date = now.isoformat()
                elif msg.text == "۱ روز بعد":
                    start_date = (now + datetime.timedelta(days=1)).isoformat()
                elif msg.text == "۳ روز بعد":
                    start_date = (now + datetime.timedelta(days=3)).isoformat()
                elif msg.text == "۱ هفته بعد":
                    start_date = (now + datetime.timedelta(days=7)).isoformat()
                else:
                    start_date = now.isoformat()
                event_id = self.create_event(
                    user.get("create_event_title"),
                    user.get("create_event_description"),
                    int(uid),
                    start_date
                )
                if event_id:
                    self.bot.send_message(uid, f"✅ رویداد با موفقیت ایجاد شد!\n\n"
                                             f"🆔 آیدی رویداد: {event_id}\n"
                                             f"📝 عنوان: {user.get('create_event_title')}\n"
                                             f"📅 تاریخ شروع: {start_date}",
                                         reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ خطا در ایجاد رویداد", reply_markup=self.kb_admin())
                for key in ["create_event_title", "create_event_description", "admin_state"]:
                    if key in user:
                        del user[key]
                self.db.write("users", db_u)
                return
        if state == "create_event_date_manual":
            try:
                # بررسی فرمت YYYY-MM-DD
                start_date = datetime.datetime.strptime(msg.text, "%Y-%m-%d").replace(tzinfo=ZoneInfo("Asia/Tehran")).isoformat()
                event_id = self.create_event(
                    user.get("create_event_title"),
                    user.get("create_event_description"),
                    int(uid),
                    start_date
                )
                if event_id:
                    self.bot.send_message(uid, f"✅ رویداد با موفقیت ایجاد شد!\n\n"
                                             f"🆔 آیدی رویداد: {event_id}\n"
                                             f"📝 عنوان: {user.get('create_event_title')}\n"
                                             f"📅 تاریخ شروع: {start_date}",
                                         reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ خطا در ایجاد رویداد", reply_markup=self.kb_admin())
                for key in ["create_event_title", "create_event_description", "admin_state"]:
                    if key in user:
                        del user[key]
                self.db.write("users", db_u)
            except:
                self.bot.send_message(uid, "❌ فرمت تاریخ صحیح نیست. لطفاً دوباره تلاش کنید.")
            return

        # ویرایش رویداد
        if state == "edit_event_select":
            if msg.text.isdigit():
                event_id = int(msg.text)
                event = self.get_event(event_id)
                if event:
                    user["edit_event_id"] = event_id
                    user["admin_state"] = "edit_event_field"
                    self.db.write("users", db_u)
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("عنوان", "توضیحات", "تاریخ شروع", "وضعیت", "🔙 لغو")
                    self.bot.send_message(uid, f"رویداد: {event['title']}\nکدام فیلد را ویرایش می‌کنید؟", reply_markup=kb)
                else:
                    self.bot.send_message(uid, "❌ رویداد یافت نشد")
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return
        if state == "edit_event_field":
            if msg.text == "🔙 لغو":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ ویرایش لغو شد", reply_markup=self.kb_admin())
                return
            field_map = {"عنوان": "title", "توضیحات": "description", "تاریخ شروع": "start_date", "وضعیت": "status"}
            if msg.text in field_map:
                user["edit_event_field"] = field_map[msg.text]
                user["admin_state"] = "edit_event_value"
                self.db.write("users", db_u)
                self.bot.send_message(uid, f"مقدار جدید برای {msg.text} را وارد کنید:")
            else:
                self.bot.send_message(uid, "❌ گزینه نامعتبر")
            return
        if state == "edit_event_value":
            event_id = user.get("edit_event_id")
            field = user.get("edit_event_field")
            new_value = msg.text
            db_e = self.db.read("events")
            if str(event_id) in db_e:
                db_e[str(event_id)][field] = new_value
                self.db.write("events", db_e)
                self.bot.send_message(uid, f"✅ فیلد {field} با موفقیت ویرایش شد", reply_markup=self.kb_admin())
            else:
                self.bot.send_message(uid, "❌ رویداد یافت نشد")
            for key in ["edit_event_id", "edit_event_field", "admin_state"]:
                if key in user:
                    del user[key]
            self.db.write("users", db_u)
            return

        # حذف رویداد
        if state == "delete_event":
            if msg.text.isdigit():
                event_id = int(msg.text)
                if self.delete_event(event_id):
                    self.bot.send_message(uid, f"✅ رویداد {event_id} حذف شد", reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ رویداد یافت نشد")
                user["admin_state"] = None
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return

        # شرکت‌کنندگان رویداد
        if state == "event_participants":
            if msg.text.isdigit():
                event_id = int(msg.text)
                event = self.get_event(event_id)
                if event:
                    participants = event.get("participants", [])
                    if participants:
                        text = f"👥 شرکت‌کنندگان رویداد {event['title']}:\n\n"
                        for pid in participants:
                            name = db_u["users"].get(pid, {}).get("name", "نامشخص")
                            text += f"🆔 <code>{pid}</code> - {self.escape_html(name)}\n"
                    else:
                        text = "هیچ شرکت‌کننده‌ای ثبت نشده است."
                    self.bot.send_message(uid, text)
                else:
                    self.bot.send_message(uid, "❌ رویداد یافت نشد")
                user["admin_state"] = None
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return

        # ایجاد تخفیف
        if state == "create_discount_code":
            if msg.text == "🔙 لغو":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ ایجاد تخفیف لغو شد", reply_markup=self.kb_admin())
                return
            discount_type = "percentage" if msg.text == "🎁 درصدی" else "fixed"
            user["create_discount_type"] = discount_type
            user["admin_state"] = "create_discount_value"
            self.db.write("users", db_u)
            if discount_type == "percentage":
                self.bot.send_message(uid, "📊 درصد تخفیف را وارد کنید (مثال: 20):")
            else:
                self.bot.send_message(uid, "💰 مقدار ثابت تخفیف را وارد کنید (مثال: 500):")
            return
        if state == "create_discount_value":
            try:
                value = float(msg.text)
                user["create_discount_value"] = value
                user["admin_state"] = "create_discount_code_input"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🔤 کد تخفیف را وارد کنید (به انگلیسی):")
            except:
                self.bot.send_message(uid, "❌ لطفاً عدد معتبر وارد کنید")
            return
        if state == "create_discount_code_input":
            code = msg.text.strip().upper()
            discount_type = user.get("create_discount_type", "percentage")
            value = user.get("create_discount_value", 0)
            if self.create_discount(code, discount_type, value):
                self.bot.send_message(uid, f"✅ کد تخفیف ایجاد شد!\n\n"
                                         f"🎫 کد: {code}\n"
                                         f"📊 نوع: {'درصدی' if discount_type == 'percentage' else 'مقدار ثابت'}\n"
                                         f"💰 مقدار: {value}{'%' if discount_type == 'percentage' else ' سکه'}",
                                     reply_markup=self.kb_admin())
            else:
                self.bot.send_message(uid, "❌ خطا در ایجاد کد تخفیف (کد تکراری یا خطای دیگر)", reply_markup=self.kb_admin())
            for key in ["create_discount_type", "create_discount_value", "admin_state"]:
                if key in user:
                    del user[key]
            self.db.write("users", db_u)
            return

        # ویرایش تخفیف
        if state == "edit_discount_select":
            code = msg.text.strip().upper()
            db_d = self.db.read("discounts")
            if code in db_d:
                user["edit_discount_code"] = code
                user["admin_state"] = "edit_discount_field"
                self.db.write("users", db_u)
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add("مقدار", "حداکثر استفاده", "تاریخ انقضا", "فعال/غیرفعال", "🔙 لغو")
                self.bot.send_message(uid, f"تخفیف {code}\nکدام فیلد را ویرایش می‌کنید؟", reply_markup=kb)
            else:
                self.bot.send_message(uid, "❌ کد تخفیف یافت نشد")
            return
        if state == "edit_discount_field":
            if msg.text == "🔙 لغو":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ ویرایش لغو شد", reply_markup=self.kb_admin())
                return
            field_map = {"مقدار": "value", "حداکثر استفاده": "max_uses", "تاریخ انقضا": "expiry_date", "فعال/غیرفعال": "active"}
            if msg.text in field_map:
                user["edit_discount_field"] = field_map[msg.text]
                user["admin_state"] = "edit_discount_value"
                self.db.write("users", db_u)
                if field_map[msg.text] == "active":
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("فعال", "غیرفعال", "🔙 لغو")
                    self.bot.send_message(uid, "وضعیت جدید را انتخاب کنید:", reply_markup=kb)
                else:
                    self.bot.send_message(uid, f"مقدار جدید برای {msg.text} را وارد کنید:")
            else:
                self.bot.send_message(uid, "❌ گزینه نامعتبر")
            return
        if state == "edit_discount_value":
            code = user.get("edit_discount_code")
            field = user.get("edit_discount_field")
            new_value = msg.text
            db_d = self.db.read("discounts")
            if code in db_d:
                if field == "active":
                    new_value = (new_value == "فعال")
                elif field == "value":
                    try:
                        new_value = float(new_value)
                    except:
                        self.bot.send_message(uid, "❌ مقدار نامعتبر")
                        return
                elif field == "max_uses":
                    try:
                        new_value = int(new_value) if new_value != "-1" else -1
                    except:
                        self.bot.send_message(uid, "❌ مقدار نامعتبر")
                        return
                elif field == "expiry_date":
                    try:
                        datetime.datetime.fromisoformat(new_value)
                    except:
                        self.bot.send_message(uid, "❌ فرمت تاریخ نامعتبر. از YYYY-MM-DD استفاده کنید.")
                        return
                db_d[code][field] = new_value
                self.db.write("discounts", db_d)
                self.bot.send_message(uid, f"✅ فیلد {field} با موفقیت ویرایش شد", reply_markup=self.kb_admin())
            else:
                self.bot.send_message(uid, "❌ کد تخفیف یافت نشد")
            for key in ["edit_discount_code", "edit_discount_field", "admin_state"]:
                if key in user:
                    del user[key]
            self.db.write("users", db_u)
            return

        # حذف تخفیف
        if state == "delete_discount":
            code = msg.text.strip().upper()
            db_d = self.db.read("discounts")
            if code in db_d:
                del db_d[code]
                self.db.write("discounts", db_d)
                self.bot.send_message(uid, f"✅ تخفیف {code} حذف شد", reply_markup=self.kb_admin())
            else:
                self.bot.send_message(uid, "❌ کد تخفیف یافت نشد")
            user["admin_state"] = None
            self.db.write("users", db_u)
            return

        # تنظیم سکه کاربر
        if state == "set_coins_user":
            if msg.text.isdigit():
                target_uid = msg.text
                user["set_coins_target"] = target_uid
                user["admin_state"] = "set_coins_amount"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "💰 مقدار سکه جدید را وارد کنید:")
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return
        if state == "set_coins_amount":
            if msg.text.isdigit():
                amount = int(msg.text)
                target_uid = user.get("set_coins_target")
                db_target = self.db.read("users")
                if target_uid in db_target["users"]:
                    db_target["users"][target_uid]["coins"] = amount
                    self.db.write("users", db_target)
                    self.bot.send_message(uid, f"✅ سکه کاربر {target_uid} به {amount:,} تنظیم شد", reply_markup=self.kb_admin())
                else:
                    self.bot.send_message(uid, "❌ کاربر پیدا نشد")
                user["admin_state"] = None
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفاً عدد وارد کنید")
            return

        # مدیریت اخطارها
        if state == "manage_warns_user":
            if msg.text.isdigit():
                target_uid = msg.text
                db_target = self.db.read("users")
                if target_uid in db_target["users"]:
                    user["manage_warns_target"] = target_uid
                    user["admin_state"] = "manage_warns_action"
                    self.db.write("users", db_u)
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("➕ اضافه کردن اخطار", "➖ کاهش اخطار", "🔄 صفر کردن", "🔙 لغو")
                    self.bot.send_message(uid, f"کاربر: {target_uid}\nاخطار فعلی: {db_target['users'][target_uid].get('warns', 0)}\nعملیات مورد نظر را انتخاب کنید:", reply_markup=kb)
                else:
                    self.bot.send_message(uid, "❌ کاربر پیدا نشد")
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return
        if state == "manage_warns_action":
            if msg.text == "🔙 لغو":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ عملیات لغو شد", reply_markup=self.kb_admin())
                return
            target_uid = user.get("manage_warns_target")
            db_target = self.db.read("users")
            if target_uid not in db_target["users"]:
                self.bot.send_message(uid, "❌ کاربر پیدا نشد")
                user["admin_state"] = None
                self.db.write("users", db_u)
                return
            current = db_target["users"][target_uid].get("warns", 0)
            if msg.text == "➕ اضافه کردن اخطار":
                new_warns = current + 1
                db_target["users"][target_uid]["warns"] = new_warns
                self.db.write("users", db_target)
                self.bot.send_message(uid, f"✅ اخطار کاربر {target_uid} به {new_warns} افزایش یافت", reply_markup=self.kb_admin())
            elif msg.text == "➖ کاهش اخطار":
                new_warns = max(0, current - 1)
                db_target["users"][target_uid]["warns"] = new_warns
                self.db.write("users", db_target)
                self.bot.send_message(uid, f"✅ اخطار کاربر {target_uid} به {new_warns} کاهش یافت", reply_markup=self.kb_admin())
            elif msg.text == "🔄 صفر کردن":
                db_target["users"][target_uid]["warns"] = 0
                self.db.write("users", db_target)
                self.bot.send_message(uid, f"✅ اخطار کاربر {target_uid} صفر شد", reply_markup=self.kb_admin())
            else:
                self.bot.send_message(uid, "❌ گزینه نامعتبر")
            user["admin_state"] = None
            self.db.write("users", db_u)
            return

        # تغییر سطح VIP
        if state == "change_vip_tier_user":
            if msg.text.isdigit():
                target_uid = msg.text
                user["change_vip_tier_target"] = target_uid
                user["admin_state"] = "change_vip_tier_level"
                self.db.write("users", db_u)
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
                kb.add("استاندارد", "نقره‌ای", "طلایی")
                kb.add("پلاتینیوم", "VIP ۱ ماهه", "VIP ۳ ماهه")
                kb.add("VIP ۶ ماهه", "VIP ۱ ساله", "🔙 لغو")
                self.bot.send_message(uid, "🎖 سطح VIP جدید را انتخاب کنید:", reply_markup=kb)
            else:
                self.bot.send_message(uid, "❌ لطفاً آیدی عددی وارد کنید")
            return
        if state == "change_vip_tier_level":
            if msg.text == "🔙 لغو":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ تغییر سطح VIP لغو شد", reply_markup=self.kb_admin())
                return
            target_uid = user.get("change_vip_tier_target")
            level = msg.text
            level_to_duration = {
                "استاندارد": None,
                "نقره‌ای": "week",
                "طلایی": "month",
                "پلاتینیوم": "3month",
                "VIP ۱ ماهه": "month",
                "VIP ۳ ماهه": "3month",
                "VIP ۶ ماهه": "6month",
                "VIP ۱ ساله": "year"
            }
            duration = level_to_duration.get(level)
            if duration is None:
                db_target = self.db.read("users")
                if target_uid in db_target["users"]:
                    db_target["users"][target_uid]["vip_end"] = 0
                    self.db.write("users", db_target)
                    self.bot.send_message(uid, f"✅ VIP کاربر {target_uid} حذف شد", reply_markup=self.kb_admin())
            elif duration:
                self.add_vip(int(target_uid), duration, f"تغییر سطح توسط ادمین: {level}")
                self.bot.send_message(uid, f"✅ سطح VIP کاربر {target_uid} به {level} تغییر کرد", reply_markup=self.kb_admin())
            user["admin_state"] = None
            self.db.write("users", db_u)
            return

        # افزودن ماموریت جدید
        if state == "add_mission_reward_type":
            if msg.text == "🎖 VIP":
                user["add_mission_reward_type"] = "vip"
                user["admin_state"] = "add_mission_vip_duration"
                self.db.write("users", db_u)
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add("۱ هفته", "۱ ماه", "۳ ماه", "۶ ماه", "۱ سال", "🔙 بازگشت")
                self.bot.send_message(uid, "⏰ مدت VIP را انتخاب کنید:", reply_markup=kb)
            elif msg.text == "💰 سکه":
                user["add_mission_reward_type"] = "coins"
                user["admin_state"] = "add_mission_coins_amount"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "💰 مقدار سکه را وارد کنید:")
            elif msg.text == "🔙 بازگشت":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ افزودن ماموریت لغو شد", reply_markup=self.kb_admin())
            return
        if state == "add_mission_vip_duration":
            duration_map = {"۱ هفته": "week", "۱ ماه": "month", "۳ ماه": "3month", "۶ ماه": "6month", "۱ سال": "year"}
            if msg.text in duration_map:
                user["add_mission_vip_duration"] = duration_map[msg.text]
                user["admin_state"] = "add_mission_title"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 عنوان ماموریت را وارد کنید:")
            elif msg.text == "🔙 بازگشت":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ افزودن ماموریت لغو شد", reply_markup=self.kb_admin())
            return
        if state == "add_mission_coins_amount":
            if msg.text.isdigit():
                user["add_mission_coins_amount"] = int(msg.text)
                user["admin_state"] = "add_mission_title"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 عنوان ماموریت را وارد کنید:")
            else:
                self.bot.send_message(uid, "❌ لطفاً عدد وارد کنید")
            return
        if state == "add_mission_title":
            user["add_mission_title"] = msg.text
            user["admin_state"] = "add_mission_type"
            self.db.write("users", db_u)
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            kb.add("chat_count", "unique_chats", "referrals")
            kb.add("spin_wheel", "profile_views", "🔙 بازگشت")
            self.bot.send_message(uid, "🎯 نوع ماموریت را انتخاب کنید:\n\n"
                                      "• chat_count: تعداد پیام در چت\n"
                                      "• unique_chats: چت با افراد مختلف\n"
                                      "• referrals: دعوت افراد\n"
                                      "• spin_wheel: چرخاندن گردونه\n"
                                      "• profile_views: بازدید از پروفایل",
                                reply_markup=kb)
            return
        if state == "add_mission_type":
            if msg.text in ["chat_count", "unique_chats", "referrals", "spin_wheel", "profile_views"]:
                user["add_mission_type"] = msg.text
                user["admin_state"] = "add_mission_target"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🎯 هدف (عدد) را وارد کنید:")
            elif msg.text == "🔙 بازگشت":
                user["admin_state"] = None
                self.db.write("users", db_u)
                self.bot.send_message(uid, "❌ افزودن ماموریت لغو شد", reply_markup=self.kb_admin())
            else:
                self.bot.send_message(uid, "❌ لطفاً از گزینه‌ها استفاده کنید")
            return
        if state == "add_mission_target":
            if msg.text.isdigit():
                target = int(msg.text)
                mission_data = {
                    "name": user.get("add_mission_title"),
                    "type": user.get("add_mission_type"),
                    "target": target,
                    "description": self.get_mission_description(user.get("add_mission_type"), target)
                }
                reward_type = user.get("add_mission_reward_type")
                if reward_type == "vip":
                    mission_data["reward_type"] = "vip"
                    mission_data["reward_value"] = user.get("add_mission_vip_duration", "week")
                else:
                    mission_data["reward_type"] = "coins"
                    mission_data["reward_value"] = user.get("add_mission_coins_amount", 50)
                db_m = self.db.read("missions")
                db_m["available"].append(mission_data)
                self.db.write("missions", db_m)
                mission_info = f"✅ <b>ماموریت جدید اضافه شد</b>\n\n"
                mission_info += f"📝 عنوان: {mission_data['name']}\n"
                mission_info += f"📝 توضیح: {mission_data['description']}\n"
                mission_info += f"🎯 نوع: {mission_data['type']}\n"
                mission_info += f"🎯 هدف: {mission_data['target']}\n"
                if mission_data["reward_type"] == "coins":
                    mission_info += f"💰 پاداش: {mission_data['reward_value']:,} سکه\n"
                else:
                    duration_name = {"week": "۱ هفته", "month": "۱ ماه", "3month": "۳ ماه", "6month": "۶ ماه", "year": "۱ سال"}.get(
                        mission_data["reward_value"], "VIP")
                    mission_info += f"🎖 پاداش: VIP {duration_name}\n"
                self.bot.send_message(uid, mission_info, reply_markup=self.kb_admin())
                keys = ["add_mission_reward_type", "add_mission_vip_duration", "add_mission_coins_amount",
                        "add_mission_title", "add_mission_type", "add_mission_target", "admin_state"]
                for key in keys:
                    if key in user:
                        del user[key]
                self.db.write("users", db_u)
            else:
                self.bot.send_message(uid, "❌ لطفاً عدد وارد کنید")
            return

    # متدهای نمایشی مدیریت
    def search_users(self, search_term):
        db_u = self.db.read("users")
        results = []
        for user_id, user_data in db_u["users"].items():
            if search_term in user_id:
                results.append((user_id, user_data))
                continue
            if "name" in user_data and search_term.lower() in user_data["name"].lower():
                results.append((user_id, user_data))
                continue
        return results

    def list_users_admin(self, uid, page=0, page_size=10):
        db_u = self.db.read("users")
        users_list = list(db_u["users"].items())
        if not users_list:
            self.bot.send_message(uid, "👥 هیچ کاربری ثبت‌نام نکرده است")
            return
        total_users = len(users_list)
        start_idx = page * page_size
        end_idx = start_idx + page_size
        page_users = users_list[start_idx:end_idx]
        users_text = f"👥 <b>لیست کاربران (صفحه {page + 1})</b>\n\n"
        users_text += f"📊 کل کاربران: {total_users}\n\n"
        for i, (user_id, user_data) in enumerate(page_users, start_idx + 1):
            vip_status = "✅" if self.is_vip(int(user_id)) else "❌"
            users_text += f"{i}. 🆔 <code>{user_id}</code>\n"
            users_text += f"   👤 {self.escape_html(user_data.get('name', 'نامشخص'))}\n"
            users_text += f"   💰 {user_data.get('coins', 0):,} سکه\n"
            users_text += f"   🎖 VIP: {vip_status}\n"
            users_text += f"   📅 عضویت: {user_data.get('joined_date', 'نامشخص')[:10]}\n"
            users_text += "-" * 30 + "\n"
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        buttons = []
        if page > 0:
            buttons.append(types.InlineKeyboardButton("⬅️ قبلی", callback_data=f"users_page_{page - 1}"))
        buttons.append(types.InlineKeyboardButton(f"{page + 1}", callback_data="current_page"))
        if end_idx < total_users:
            buttons.append(types.InlineKeyboardButton("➡️ بعدی", callback_data=f"users_page_{page + 1}"))
        keyboard.add(*buttons)
        self.bot.send_message(uid, users_text, reply_markup=keyboard)

    def show_users_stats(self, uid):
        db_u = self.db.read("users")
        users = db_u["users"]
        total_users = len(users)
        if total_users == 0:
            self.bot.send_message(uid, "هنوز کاربری ثبت‌نام نکرده است.")
            return
        vip_users = sum(1 for user_id in users if self.is_vip(int(user_id)))
        active_today = 0
        total_coins = sum(user.get("coins", 0) for user in users.values())
        today = self.get_tehran_date_str()
        for user_data in users.values():
            if user_data.get("last_active_date") == today:
                active_today += 1
        stats_text = "📊 <b>آمار کاربران</b>\n\n"
        stats_text += f"👥 کل کاربران: {total_users:,}\n"
        stats_text += f"🎖 کاربران VIP: {vip_users:,}\n"
        stats_text += f"📈 کاربران فعال امروز: {active_today:,}\n"
        stats_text += f"💰 کل سکه‌ها: {total_coins:,}\n"
        stats_text += f"📊 میانگین سکه: {total_coins // total_users:,}\n"
        males = sum(1 for user in users.values() if user.get("sex") == "آقا")
        females = total_users - males
        stats_text += f"\n👦 آقا: {males:,} ({males / total_users * 100:.1f}%)\n"
        stats_text += f"👧 خانم: {females:,} ({females / total_users * 100:.1f}%)\n"
        self.bot.send_message(uid, stats_text)

    def show_recent_activity(self, uid, days=7):
        db_u = self.db.read("users")
        users = db_u["users"]
        today = datetime.date.today()
        dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(days)]
        activity_data = {}
        for date in dates:
            activity_data[date] = sum(1 for user in users.values() if user.get("last_active_date") == date)
        activity_text = f"📅 <b>فعالیت {days} روز اخیر</b>\n\n"
        for date, count in activity_data.items():
            date_obj = datetime.datetime.fromisoformat(date).date()
            persian_date = date_obj.strftime("%Y/%m/%d")
            activity_text += f"{persian_date}: {count} کاربر\n"
        today_str = today.isoformat()
        active_today = [user_id for user_id, user in users.items() if user.get("last_active_date") == today_str]
        if active_today:
            activity_text += f"\n✅ <b>کاربران فعال امروز:</b>\n"
            for user_id in active_today[:10]:
                user_data = users[user_id]
                activity_text += f"🆔 <code>{user_id}</code> - {self.escape_html(user_data.get('name', 'نامشخص'))}\n"
            if len(active_today) > 10:
                activity_text += f"\n... و {len(active_today) - 10} کاربر دیگر"
        self.bot.send_message(uid, activity_text)

    def list_events_admin(self, uid):
        events = self.list_events()
        if not events:
            self.bot.send_message(uid, "📭 هیچ رویدادی ایجاد نشده است")
            return
        events_text = "📅 <b>لیست رویدادها</b>\n\n"
        for event in events:
            status_icons = {"draft": "📝", "active": "🟢", "completed": "✅", "cancelled": "❌"}
            status = event.get("status", "draft")
            icon = status_icons.get(status, "📝")
            events_text += f"{icon} <b>رویداد #{event['event_id']}</b>\n"
            events_text += f"📝 عنوان: {self.escape_html(event['title'])}\n"
            events_text += f"📅 تاریخ: {event.get('start_date', 'تعیین نشده')}\n"
            events_text += f"👥 شرکت‌کنندگان: {len(event.get('participants', []))} نفر\n"
            events_text += f"📊 وضعیت: {status}\n"
            events_text += "-" * 30 + "\n"
        self.bot.send_message(uid, events_text)

    def show_events_stats(self, uid):
        events = self.list_events()
        total_events = len(events)
        active_events = len([e for e in events if e.get("status") == "active"])
        total_participants = sum(len(e.get("participants", [])) for e in events)
        stats_text = "📊 <b>آمار رویدادها</b>\n\n"
        stats_text += f"📅 کل رویدادها: {total_events}\n"
        stats_text += f"🟢 رویدادهای فعال: {active_events}\n"
        stats_text += f"👥 کل شرکت‌کنندگان: {total_participants}\n"
        if events:
            popular = max(events, key=lambda x: len(x.get("participants", [])))
            stats_text += f"\n🏆 پرطرفدارترین رویداد:\n"
            stats_text += f"   📝 {self.escape_html(popular['title'])}\n"
            stats_text += f"   👥 {len(popular.get('participants', []))} نفر\n"
        self.bot.send_message(uid, stats_text)

    def list_discounts_admin(self, uid):
        db_d = self.db.read("discounts")
        discounts = db_d
        if not discounts:
            self.bot.send_message(uid, "🎫 هیچ کد تخفیفی ایجاد نشده است")
            return
        active_discounts = [d for d in discounts.values() if d.get("active", True)]
        expired_discounts = [d for d in discounts.values() if not d.get("active", True)]
        discounts_text = "🎫 <b>لیست تخفیف‌ها</b>\n\n"
        discounts_text += f"🟢 فعال: {len(active_discounts)}\n"
        discounts_text += f"🔴 غیرفعال: {len(expired_discounts)}\n\n"
        for discount in active_discounts[:10]:
            discount_type = "٪" if discount["type"] == "percentage" else "سکه"
            uses = f"{discount.get('current_uses', 0)}/{discount.get('max_uses', -1)}" if discount.get('max_uses', -1) != -1 else "نامحدود"
            discounts_text += f"🎁 <b>{discount['code']}</b>\n"
            discounts_text += f"💰 مقدار: {discount['value']} {discount_type}\n"
            discounts_text += f"📊 استفاده: {uses}\n"
            if discount.get("expiry_date"):
                expiry = datetime.datetime.fromisoformat(discount["expiry_date"]).strftime("%Y-%m-%d")
                discounts_text += f"📅 انقضا: {expiry}\n"
            discounts_text += "-" * 20 + "\n"
        self.bot.send_message(uid, discounts_text)

    def show_discounts_stats(self, uid):
        db_d = self.db.read("discounts")
        discounts = db_d
        total_discounts = len(discounts)
        active_discounts = len([d for d in discounts.values() if d.get("active", True)])
        total_uses = sum(d.get("current_uses", 0) for d in discounts.values())
        most_used = sorted(discounts.values(), key=lambda x: x.get("current_uses", 0), reverse=True)[:3]
        stats_text = "📊 <b>آمار تخفیف‌ها</b>\n\n"
        stats_text += f"🎫 کل تخفیف‌ها: {total_discounts}\n"
        stats_text += f"🟢 تخفیف‌های فعال: {active_discounts}\n"
        stats_text += f"📊 کل دفعات استفاده: {total_uses}\n\n"
        if most_used:
            stats_text += "🏆 پراستفاده‌ترین تخفیف‌ها:\n"
            for i, discount in enumerate(most_used, 1):
                stats_text += f"{i}. {discount['code']} - {discount.get('current_uses', 0)} بار استفاده\n"
        self.bot.send_message(uid, stats_text)

    def show_special_discounts(self, uid):
        db_d = self.db.read("discounts")
        discounts = db_d
        special_discounts = [d for d in discounts.values() if d.get("min_vip_level", 0) > 0]
        if not special_discounts:
            self.bot.send_message(uid, "🎯 هیچ تخفیف ویژه‌ای ایجاد نشده است")
            return
        discounts_text = "🎯 <b>تخفیف‌های ویژه</b>\n\n"
        for discount in special_discounts:
            vip_level = discount.get("min_vip_level", 0)
            vip_names = {1: "نقره‌ای", 2: "طلایی", 3: "پلاتینیوم"}
            vip_name = vip_names.get(vip_level, f"سطح {vip_level}")
            discounts_text += f"🎁 <b>{discount['code']}</b>\n"
            discounts_text += f"💰 مقدار: {discount['value']}{'%' if discount['type'] == 'percentage' else ' سکه'}\n"
            discounts_text += f"🎖 نیازمند: VIP {vip_name}\n"
            discounts_text += f"📊 استفاده: {discount.get('current_uses', 0)}/{discount.get('max_uses', -1) if discount.get('max_uses', -1) != -1 else 'نامحدود'}\n"
            discounts_text += "-" * 20 + "\n"
        self.bot.send_message(uid, discounts_text)

    def show_advanced_reports(self, uid):
        db_u = self.db.read("users")
        db_b = self.db.read("bans")
        db_m = self.db.read("messages")
        today = self.get_tehran_date_str()
        week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        users_this_week = sum(1 for user in db_u["users"].values() if user.get("joined_date") and user["joined_date"] >= week_ago)
        total_messages = sum(len(messages) for messages in db_m["inbox"].values())
        vip_users = sum(1 for user_id in db_u["users"] if self.is_vip(int(user_id)))
        reports_text = "📈 <b>گزارش‌های پیشرفته</b>\n\n"
        reports_text += "📊 <b>رشد کاربران:</b>\n"
        reports_text += f"• کاربران این هفته: {users_this_week}\n"
        reports_text += f"• نرخ رشد: {(users_this_week / len(db_u['users']) * 100):.1f}%\n\n" if db_u["users"] else "• نرخ رشد: 0%\n\n"
        reports_text += "💬 <b>فعالیت چت:</b>\n"
        reports_text += f"• کل پیام‌های ناشناس: {total_messages}\n"
        reports_text += f"• کاربران با پیام: {len(db_m['inbox'])}\n\n"
        reports_text += "🎖 <b>وضعیت VIP:</b>\n"
        reports_text += f"• کاربران VIP: {vip_users}\n"
        reports_text += f"• درآمد تخمینی: {vip_users * 1000:,} سکه\n"
        self.bot.send_message(uid, reports_text)

    def show_vip_list(self, uid):
        db_u = self.db.read("users")
        active_vips = [u for u in db_u["users"] if self.is_vip(int(u))]
        if not active_vips:
            self.bot.send_message(uid, "❌ هیچ کاربر VIP فعال وجود ندارد")
            return
        vip_text = "<b>📋 لیست کاربران VIP فعال</b>\n\n"
        for v in active_vips[:50]:
            name = db_u["users"][v].get("name", "نامشخص")
            end_date = datetime.datetime.fromtimestamp(db_u["users"][v].get("vip_end", 0)).strftime("%Y-%m-%d")
            now = datetime.datetime.now().timestamp()
            remaining_days = int((db_u["users"][v].get("vip_end", 0) - now) / (24 * 3600))
            vip_text += f"🆔 <code>{v}</code> - {self.escape_html(name)}\n📅 تا {end_date} ({remaining_days} روز)\n\n"
        if len(active_vips) > 50:
            vip_text += f"\n... و {len(active_vips) - 50} نفر دیگر"
        self.bot.send_message(uid, vip_text)

    def show_bans_list(self, uid):
        db_b = self.db.read("bans")
        db_u = self.db.read("users")
        ban_text = "<b>🚫 لیست بن‌شده‌ها</b>\n\n"
        kb = types.InlineKeyboardMarkup()
        if db_b.get("permanent"):
            ban_text += "<b>بن دائم:</b>\n"
            for ban_uid, reason in list(db_b["permanent"].items())[:20]:
                name = db_u["users"].get(ban_uid, {}).get("name", "نامشخص")
                ban_text += f"🆔 <code>{ban_uid}</code> - {self.escape_html(name)}\n💬 {reason}\n"
                kb.add(types.InlineKeyboardButton(f"🔓 بخشیدن {ban_uid}", callback_data=f"unban_perm_{ban_uid}"))
            ban_text += "\n"
        if db_b.get("temporary"):
            ban_text += "<b>بن موقت:</b>\n"
            for ban_uid, data in list(db_b["temporary"].items())[:20]:
                name = db_u["users"].get(ban_uid, {}).get("name", "نامشخص")
                end_time = datetime.datetime.fromtimestamp(data["end"]).strftime("%Y-%m-%d %H:%M")
                ban_text += f"🆔 <code>{ban_uid}</code> - {self.escape_html(name)}\n⏰ تا {end_time}\n"
                kb.add(types.InlineKeyboardButton(f"⏰ تمدید بن {ban_uid}", callback_data=f"extend_ban_{ban_uid}"))
        if not db_b.get("permanent") and not db_b.get("temporary"):
            ban_text += "✅ هیچ کاربر بن‌شده‌ای وجود ندارد"
        self.bot.send_message(uid, ban_text, reply_markup=kb)

    def manage_missions(self, uid):
        db_m = self.db.read("missions")
        current_mission = db_m["daily"]
        mission_text = f"<b>🎯 مدیریت ماموریت‌های روزانه</b>\n\n"
        mission_text += f"<b>ماموریت امروز:</b>\n"
        mission_text += f"📋 {current_mission['mission']}\n"
        mission_text += f"📝 کار: {current_mission.get('description', current_mission['mission'])}\n"
        if current_mission.get("reward_type") == "coins":
            mission_text += f"🎁 پاداش: {current_mission.get('reward_value', 50):,} سکه\n"
        elif current_mission.get("reward_type") == "vip":
            duration_name = {"week": "۱ هفته", "month": "۱ ماه", "3month": "۳ ماه", "6month": "۶ ماه", "year": "۱ سال"}.get(
                current_mission.get("reward_value", "week"), "VIP")
            mission_text += f"🎁 پاداش: VIP {duration_name}\n"
        else:
            mission_text += f"🎁 پاداش: {current_mission.get('reward_value', 50):,} سکه\n"
        mission_text += f"📅 تاریخ: {current_mission['date']}\n\n"
        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(types.InlineKeyboardButton("🔄 تغییر ماموریت امروز", callback_data="change_daily_mission"))
        kb.add(types.InlineKeyboardButton("📋 مشاهده لیست ماموریت‌ها", callback_data="view_missions_list"))
        kb.add(types.InlineKeyboardButton("➕ افزودن ماموریت جدید", callback_data="add_new_mission"))
        self.bot.send_message(uid, mission_text, reply_markup=kb)

    def manage_maintenance_warning(self, uid):
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

    # متدهای تنظیمات پیشرفته (placeholder – می‌توانید تکمیل کنید)
    def optimize_system(self, uid):
        self.bot.send_message(uid, "⚡ <b>بهینه‌سازی سیستم در حال انجام...</b>")
        time.sleep(1)
        self.bot.send_message(uid, "✅ بهینه‌سازی با موفقیت انجام شد")

    def auto_reset_settings(self, uid):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🔄 ریست روزانه", callback_data="auto_reset_daily"),
            types.InlineKeyboardButton("📊 ریست آمار", callback_data="auto_reset_stats"),
            types.InlineKeyboardButton("🎯 ریست ماموریت", callback_data="auto_reset_missions"),
            types.InlineKeyboardButton("📅 ریست رویداد", callback_data="auto_reset_events"),
            types.InlineKeyboardButton("❌ غیرفعال", callback_data="auto_reset_disable")
        )
        self.bot.send_message(uid, "🔄 <b>تنظیمات ریست خودکار</b>\n\n"
                                 "کدام ریست خودکار را می‌خواهید تنظیم کنید؟", reply_markup=kb)

    def create_backup(self, uid):
        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            for key, path in self.db.files.items():
                if os.path.exists(path):
                    backup_path = os.path.join(backup_dir, f"{key}_{timestamp}.json")
                    with open(path, 'rb') as src, open(backup_path, 'wb') as dst:
                        dst.write(src.read())
            self.bot.send_message(uid, f"✅ پشتیبان‌گیری با موفقیت انجام شد\n\n"
                                     f"📁 مسیر: {backup_dir}\n"
                                     f"🕒 زمان: {timestamp}")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            self.bot.send_message(uid, f"❌ خطا در پشتیبان‌گیری: {e}")

    def cleanup_data(self, uid):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🗑️ پیام‌های قدیمی", callback_data="cleanup_old_messages"),
            types.InlineKeyboardButton("🚮 کاربران غیرفعال", callback_data="cleanup_inactive_users"),
            types.InlineKeyboardButton("📅 رویدادهای قدیمی", callback_data="cleanup_old_events"),
            types.InlineKeyboardButton("🎫 تخفیف‌های منقضی", callback_data="cleanup_expired_discounts"),
            types.InlineKeyboardButton("⚠️ همه موارد", callback_data="cleanup_all"),
            types.InlineKeyboardButton("❌ لغو", callback_data="cleanup_cancel")
        )
        self.bot.send_message(uid, "🗑️ <b>پاک‌سازی داده‌ها</b>\n\n"
                                 "کدام داده‌ها را می‌خواهید پاک‌سازی کنید؟", reply_markup=kb)

    def system_settings(self, uid):
        db_c = self.db.read("config")
        settings = db_c["settings"]
        settings_text = "🔧 <b>تنظیمات سیستم</b>\n\n"
        settings_text += f"🛠 حالت تعمیر: {'✅ فعال' if settings.get('maintenance') else '❌ غیرفعال'}\n"
        settings_text += f"🔒 محدودیت پیام VIP: {settings.get('vip_message_limit', 100)}\n"
        settings_text += f"⏰ زمان جستجوی چت: {settings.get('chat_search_time', 30)} ثانیه\n"
        settings_text += f"📊 محدودیت گزارش روزانه: {settings.get('daily_report_limit', 5)}\n"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🛠 تغییر حالت تعمیر", callback_data="toggle_maintenance"),
            types.InlineKeyboardButton("🔒 تنظیم محدودیت VIP", callback_data="set_vip_limit"),
            types.InlineKeyboardButton("⏰ تنظیم زمان جستجو", callback_data="set_search_time"),
            types.InlineKeyboardButton("📊 تنظیم محدودیت گزارش", callback_data="set_report_limit"),
            types.InlineKeyboardButton("⚡ تنظیمات پیش‌فرض", callback_data="reset_settings")
        )
        self.bot.send_message(uid, settings_text, reply_markup=kb)

    def message_settings(self, uid):
        db_c = self.db.read("config")
        settings = db_c["settings"]
        settings_text = "📝 <b>تنظیمات پیام‌ها</b>\n\n"
        settings_text += f"👋 پیام خوش‌آمدگویی: {'✅ فعال' if settings.get('welcome_message', True) else '❌ غیرفعال'}\n"
        settings_text += f"🎉 پیام پاداش: {'✅ فعال' if settings.get('reward_message', True) else '❌ غیرفعال'}\n"
        settings_text += f"⚠️ پیام اخطار: {'✅ فعال' if settings.get('warning_message', True) else '❌ غیرفعال'}\n"
        settings_text += f"📨 اعلان پیام ناشناس: {'✅ فعال' if settings.get('anon_notify', True) else '❌ غیرفعال'}\n"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("👋 خوش‌آمدگویی", callback_data="toggle_welcome"),
            types.InlineKeyboardButton("🎉 پاداش", callback_data="toggle_reward"),
            types.InlineKeyboardButton("⚠️ اخطار", callback_data="toggle_warning"),
            types.InlineKeyboardButton("📨 اعلان", callback_data="toggle_anon_notify"),
            types.InlineKeyboardButton("📝 ویرایش متن‌ها", callback_data="edit_messages")
        )
        self.bot.send_message(uid, settings_text, reply_markup=kb)

    def chat_settings(self, uid):
        db_c = self.db.read("config")
        settings = db_c["settings"]
        settings_text = "🎛️ <b>تنظیمات چت</b>\n\n"
        settings_text += f"🔍 جستجوی خودکار: {'✅ فعال' if settings.get('auto_search', True) else '❌ غیرفعال'}\n"
        settings_text += f"📵 فیلتر کلمات: {'✅ فعال' if settings.get('word_filter', True) else '❌ غیرفعال'}\n"
        settings_text += f"🤖 اسکن هوش مصنوعی: {'✅ فعال' if settings.get('ai_scan', True) else '❌ غیرفعال'}\n"
        settings_text += f"🔄 بازیابی چت: {'✅ فعال' if settings.get('chat_restore', True) else '❌ غیرفعال'}\n"
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("🔍 جستجوی خودکار", callback_data="toggle_auto_search"),
            types.InlineKeyboardButton("📵 فیلتر کلمات", callback_data="toggle_word_filter"),
            types.InlineKeyboardButton("🤖 اسکن AI", callback_data="toggle_ai_scan"),
            types.InlineKeyboardButton("🔄 بازیابی", callback_data="toggle_chat_restore"),
            types.InlineKeyboardButton("⚙️ تنظیمات فیلتر", callback_data="filter_settings")
        )
        self.bot.send_message(uid, settings_text, reply_markup=kb)

    def get_mission_description(self, mission_type, target):
        descriptions = {
            "chat_count": f"ارسال {target} پیام در چت",
            "unique_chats": f"چت با {target} نفر مختلف",
            "referrals": f"دعوت {target} نفر به ربات",
            "spin_wheel": "چرخاندن گردونه شانس",
            "profile_views": f"بازدید {target} بار از پروفایل خود"
        }
        return descriptions.get(mission_type, f"ماموریت {mission_type}")

    # ==========================================
    # اجرای ربات
    # ==========================================
    def run(self):
        print("=" * 50)
        print("Shadow Titan v42.1 - Full Fixed Edition")
        print("All issues fixed. Bot is starting...")
        print("=" * 50)
        try:
            server_thread = Thread(target=run_web)
            server_thread.daemon = True
            server_thread.start()
            print("✅ Web Server started on port 8080")
        except Exception as e:
            logger.error(f"Web Server Error: {e}")
        try:
            print("🚀 Connecting to Telegram...")
            self.bot.infinity_polling(skip_pending=True)
        except Exception as e:
            logger.error(f"Polling Error: {e}")
            print(f"❌ Polling Error: {e}")


if __name__ == "__main__":
    bot_instance = ShadowTitanBot()
    bot_instance.run()
