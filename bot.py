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
from threading import Thread, Lock
from zoneinfo import ZoneInfo
import uuid
import zipfile
import shutil
import io
import base64

# ==========================================
# تنظیمات لاگ و سیستم
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('shadow_titan.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ShadowTitanUltimate")

app = Flask(__name__)

# ==========================================
# مدیریت دیتابیس پیشرفته
# ==========================================
class DatabaseManager:
    def __init__(self):
        self.data_dir = "data"
        self.backup_dir = "backups"
        self.setup_directories()
        
        self.files = {
            "users": f"{self.data_dir}/users.json",
            "bans": f"{self.data_dir}/bans.json",
            "queue": f"{self.data_dir}/queue.json",
            "messages": f"{self.data_dir}/messages.json",
            "config": f"{self.data_dir}/config.json",
            "missions": f"{self.data_dir}/missions.json",
            "chats": f"{self.data_dir}/chats.json",
            "badwords": f"{self.data_dir}/badwords.json",
            "vip_prices": f"{self.data_dir}/vip_prices.json",
            "settings": f"{self.data_dir}/settings.json",
            "stats": f"{self.data_dir}/stats.json",
            "admin_logs": f"{self.data_dir}/admin_logs.json",
            "reports": f"{self.data_dir}/reports.json",
            "transactions": f"{self.data_dir}/transactions.json"
        }
        
        self.locks = {name: Lock() for name in self.files}
        self.init_database()
        self.start_backup_service()
    
    def setup_directories(self):
        """ایجاد پوشه‌های مورد نیاز"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def init_database(self):
        """مقداردهی اولیه دیتابیس"""
        defaults = {
            "users": {
                "users": {},
                "metadata": {"total": 0, "last_update": datetime.datetime.now().isoformat()}
            },
            "bans": {
                "permanent": {},
                "temporary": {},
                "warnings": {}
            },
            "queue": {
                "general": [],
                "vip": [],
                "waiting_time": {}
            },
            "messages": {
                "inbox": {}
            },
            "config": {
                "bot_name": "Shadow Titan Ultimate",
                "version": "4.0.0",
                "admins": ["8013245091"],
                "main_channel": "@ChatNaAnnouncements",
                "support_channel": "@its_alimo",
                "maintenance": {
                    "enabled": False,
                    "message": "ربات در حال تعمیر است",
                    "vip_allowed": True
                }
            },
            "missions": {
                "daily": {
                    "date": "",
                    "name": "ماموریت روزانه",
                    "description": "ارسال 5 پیام در چت",
                    "type": "chat_count",
                    "target": 5,
                    "reward": {"type": "coins", "amount": 50}
                },
                "available": [
                    {"name": "ارسال 5 پیام در چت", "type": "chat_count", "target": 5, "reward": {"type": "coins", "amount": 50}},
                    {"name": "ارسال 10 پیام در چت", "type": "chat_count", "target": 10, "reward": {"type": "coins", "amount": 100}},
                    {"name": "چت با 3 نفر مختلف", "type": "unique_chats", "target": 3, "reward": {"type": "coins", "amount": 80}},
                    {"name": "چت با 5 نفر مختلف", "type": "unique_chats", "target": 5, "reward": {"type": "coins", "amount": 150}},
                    {"name": "دعوت 2 نفر", "type": "referrals", "target": 2, "reward": {"type": "vip", "duration": "week"}},
                    {"name": "دعوت 5 نفر", "type": "referrals", "target": 5, "reward": {"type": "vip", "duration": "month"}}
                ]
            },
            "chats": {},
            "badwords": {
                "words": [
                    "کیر", "کیرم", "کیرت", "کیری", "کس", "کص", "کوس", "کوث",
                    "جنده", "جهنده", "مادرجنده", "قحبه", "قهبه",
                    "پدرسگ", "پدرسوخته", "حرامزاده", "گاییدم", "گاییدن",
                    "سیکتیر", "کون", "کونی", "گوه", "لاشی", "فاحشه",
                    "ناموس", "اوبی", "بی‌ناموس", "سکس", "پورن",
                    "خارکصه", "تچمم", "شاسگول", "پفیوز", "دیوث"
                ],
                "auto_ban": True,
                "warning_threshold": 3
            },
            "vip_prices": {
                "week": 500,
                "month": 1800,
                "3month": 5000,
                "6month": 9000,
                "year": 15000,
                "christmas": 0
            },
            "settings": {
                "security": {
                    "ai_filter": False,
                    "auto_ban": True,
                    "max_warnings": 3,
                    "require_channel": True,
                    "captcha": False
                },
                "features": {
                    "anonymous_chat": True,
                    "wheel": True,
                    "daily_missions": True,
                    "referral": True,
                    "vip": True
                },
                "limits": {
                    "message_length": 1000,
                    "daily_messages": 100,
                    "chat_duration": 7200,
                    "queue_timeout": 300
                }
            },
            "stats": {
                "total_users": 0,
                "active_today": 0,
                "vip_users": 0,
                "total_chats": 0,
                "total_messages": 0,
                "daily_stats": {}
            },
            "admin_logs": [],
            "reports": {
                "pending": [],
                "resolved": []
            },
            "transactions": {
                "vip": [],
                "coins": []
            }
        }
        
        for key, file_path in self.files.items():
            if not os.path.exists(file_path):
                with self.locks[key]:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(defaults.get(key, {}), f, ensure_ascii=False, indent=4)
    
    def read(self, key):
        """خواندن داده"""
        with self.locks[key]:
            try:
                with open(self.files[key], 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"خطا در خواندن {key}: {e}")
                return {}
    
    def write(self, key, data):
        """نوشتن داده"""
        with self.locks[key]:
            try:
                with open(self.files[key], 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                return True
            except Exception as e:
                logger.error(f"خطا در نوشتن {key}: {e}")
                return False
    
    def update(self, key, update_func):
        """بروزرسانی داده"""
        data = self.read(key)
        new_data = update_func(data)
        return self.write(key, new_data)
    
    def backup(self):
        """ایجاد بک‌آپ"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            os.makedirs(backup_path, exist_ok=True)
            
            for key, file_path in self.files.items():
                if os.path.exists(file_path):
                    shutil.copy2(file_path, os.path.join(backup_path, f"{key}.json"))
            
            # فشرده‌سازی
            zip_path = f"{backup_path}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(backup_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), 
                                  os.path.relpath(os.path.join(root, file), backup_path))
            
            shutil.rmtree(backup_path)
            logger.info(f"بک‌آپ ایجاد شد: {zip_path}")
            return True
        except Exception as e:
            logger.error(f"خطا در بک‌آپ: {e}")
            return False
    
    def start_backup_service(self):
        """سرویس بک‌آپ خودکار"""
        def backup_loop():
            while True:
                time.sleep(6 * 3600)  # هر 6 ساعت
                self.backup()
        
        Thread(target=backup_loop, daemon=True).start()

# ==========================================
# کلاس اصلی ربات
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        # بارگیری توکن
        self.token = self.load_token()
        self.db = DatabaseManager()
        
        # اطلاعات ربات
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        
        try:
            self.bot_info = self.bot.get_me()
            self.username = self.bot_info.username
        except:
            self.username = "ShadowTitanBot"
            logger.error("خطا در دریافت اطلاعات بات")
        
        # تنظیمات
        self.config = self.db.read("config")
        self.settings = self.db.read("settings")
        
        # مدیران
        self.owner = self.config.get("admins", ["8013245091"])[0]
        self.admins = self.config.get("admins", [])
        
        # کانال‌ها
        self.channel = self.config.get("main_channel", "@ChatNaAnnouncements")
        self.support = self.config.get("support_channel", "@its_alimo")
        
        # مدت‌های VIP
        self.vip_durations = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "3month": 90 * 24 * 3600,
            "6month": 180 * 24 * 3600,
            "year": 365 * 24 * 3600,
            "christmas": 90 * 24 * 3600
        }
        
        # کلمات ممنوعه
        self.bad_words = self.db.read("badwords")["words"]
        
        # سیستم‌های داخلی
        self.active_chats = {}
        self.search_queue = {}
        self.user_states = {}
        
        # شروع سرویس‌ها
        self.start_services()
        self.register_handlers()
        
        logger.info(f"ربات {self.username} راه‌اندازی شد")
    
    def load_token(self):
        """بارگیری توکن"""
        token = os.getenv("BOT_TOKEN")
        if not token:
            try:
                with open("token.txt", "r") as f:
                    token = f.read().strip()
            except:
                token = "8213706320:AAFnu2EgXqRf05dPuJE_RU0AlQcXQkNdRZI"
        return token
    
    def start_services(self):
        """شروع سرویس‌های جانبی"""
        # سرویس بررسی بن‌های موقت
        Thread(target=self.check_temp_bans, daemon=True).start()
        
        # سرویس بررسی چت‌ها
        Thread(target=self.check_active_chats, daemon=True).start()
        
        # سرویس بروزرسانی آمار
        Thread(target=self.update_stats, daemon=True).start()
        
        # سرویس ماموریت روزانه
        Thread(target=self.daily_mission_updater, daemon=True).start()
        
        # سرویس وب سرور
        Thread(target=self.run_web_server, daemon=True).start()
    
    def run_web_server(self):
        """اجرای وب سرور"""
        @app.route('/')
        def home():
            stats = self.db.read("stats")
            return f"""
            <html>
                <head><title>Shadow Titan Ultimate</title></head>
                <body style="font-family: Arial; padding: 20px;">
                    <h1>🤖 Shadow Titan Ultimate</h1>
                    <p>Version: 4.0.0</p>
                    <p>Users: {stats.get('total_users', 0)}</p>
                    <p>Active Today: {stats.get('active_today', 0)}</p>
                    <p>VIP Users: {stats.get('vip_users', 0)}</p>
                    <p>Status: ✅ Online</p>
                </body>
            </html>
            """
        
        @app.route('/stats')
        def stats_api():
            stats = self.db.read("stats")
            return json.dumps(stats, ensure_ascii=False)
        
        app.run(host='0.0.0.0', port=8080, debug=False)
    
    def check_temp_bans(self):
        """بررسی بن‌های موقت"""
        while True:
            try:
                bans = self.db.read("bans")
                now = time.time()
                updated = False
                
                for user_id, ban_info in list(bans.get("temporary", {}).items()):
                    if ban_info.get("end", 0) < now:
                        del bans["temporary"][user_id]
                        updated = True
                
                if updated:
                    self.db.write("bans", bans)
            except Exception as e:
                logger.error(f"خطا در بررسی بن‌ها: {e}")
            
            time.sleep(60)
    
    def check_active_chats(self):
        """بررسی چت‌های فعال"""
        while True:
            try:
                chats = self.db.read("chats")
                now = time.time()
                updated = False
                
                for chat_id, chat_info in list(chats.items()):
                    if now - chat_info.get("last_activity", 0) > 7200:  # 2 ساعت
                        # پایان چت
                        user1, user2 = chat_info.get("users", [])
                        if user1 and user2:
                            self.end_chat(user1, user2, "پایان خودکار (عدم فعالیت)")
                        del chats[chat_id]
                        updated = True
                
                if updated:
                    self.db.write("chats", chats)
            except Exception as e:
                logger.error(f"خطا در بررسی چت‌ها: {e}")
            
            time.sleep(30)
    
    def update_stats(self):
        """بروزرسانی آمار"""
        while True:
            try:
                users = self.db.read("users")
                stats = self.db.read("stats")
                today = str(datetime.date.today())
                
                # محاسبه آمار
                stats["total_users"] = len(users.get("users", {}))
                
                # کاربران فعال امروز
                active_count = 0
                vip_count = 0
                
                for user_data in users.get("users", {}).values():
                    if user_data.get("last_seen", "").startswith(today):
                        active_count += 1
                    if self.is_vip(user_data.get("vip_end", 0)):
                        vip_count += 1
                
                stats["active_today"] = active_count
                stats["vip_users"] = vip_count
                
                # ذخیره آمار روزانه
                if today not in stats["daily_stats"]:
                    stats["daily_stats"][today] = {
                        "new_users": 0,
                        "active_users": active_count
                    }
                
                self.db.write("stats", stats)
            except Exception as e:
                logger.error(f"خطا در بروزرسانی آمار: {e}")
            
            time.sleep(300)  # هر 5 دقیقه
    
    def daily_mission_updater(self):
        """بروزرسانی ماموریت روزانه"""
        while True:
            now = datetime.datetime.now()
            # بروزرسانی در نیمه شب
            if now.hour == 0 and now.minute < 5:
                self.update_daily_mission()
                time.sleep(300)  # 5 دقیقه منتظر بمان
            time.sleep(60)
    
    def update_daily_mission(self):
        """بروزرسانی ماموریت روزانه"""
        missions = self.db.read("missions")
        today = str(datetime.date.today())
        
        if missions.get("daily", {}).get("date") != today:
            mission = random.choice(missions.get("available", []))
            missions["daily"] = {
                "date": today,
                "name": mission["name"],
                "description": mission.get("description", mission["name"]),
                "type": mission["type"],
                "target": mission["target"],
                "reward": mission["reward"]
            }
            self.db.write("missions", missions)
            logger.info(f"ماموریت روزانه بروزرسانی شد: {mission['name']}")
    
    # ==========================================
    # توابع کمکی
    # ==========================================
    
    def is_vip(self, user_id=None, vip_end=None):
        """بررسی وضعیت VIP"""
        if user_id:
            users = self.db.read("users")
            user = users.get("users", {}).get(str(user_id), {})
            vip_end = user.get("vip_end", 0)
        
        return vip_end > time.time()
    
    def add_coins(self, user_id, amount, reason=""):
        """افزودن سکه"""
        users = self.db.read("users")
        user_id = str(user_id)
        
        if user_id not in users.get("users", {}):
            return False
        
        user = users["users"][user_id]
        user["coins"] = user.get("coins", 0) + amount
        
        # ثبت تراکنش
        transactions = self.db.read("transactions")
        transactions["coins"].append({
            "user_id": user_id,
            "amount": amount,
            "reason": reason,
            "timestamp": time.time()
        })
        
        self.db.write("users", users)
        self.db.write("transactions", transactions)
        
        # اطلاع به کاربر
        try:
            self.bot.send_message(
                user_id,
                f"💰 <b>دریافت سکه!</b>\n\n"
                f"مقدار: {amount:,} سکه\n"
                f"دلیل: {reason}\n"
                f"موجودی جدید: {user['coins']:,} سکه"
            )
        except:
            pass
        
        return True
    
    def add_vip(self, user_id, duration_key, reason=""):
        """افزودن VIP"""
        users = self.db.read("users")
        user_id = str(user_id)
        
        if user_id not in users.get("users", {}):
            return False
        
        user = users["users"][user_id]
        now = time.time()
        current_end = user.get("vip_end", 0)
        
        if current_end < now:
            new_end = now + self.vip_durations.get(duration_key, 0)
        else:
            new_end = current_end + self.vip_durations.get(duration_key, 0)
        
        user["vip_end"] = new_end
        
        if duration_key == "christmas":
            user["christmas_vip_taken"] = True
        
        # ثبت تراکنش
        transactions = self.db.read("transactions")
        transactions["vip"].append({
            "user_id": user_id,
            "duration": duration_key,
            "reason": reason,
            "timestamp": time.time()
        })
        
        self.db.write("users", users)
        self.db.write("transactions", transactions)
        
        # اطلاع به کاربر
        try:
            end_date = datetime.datetime.fromtimestamp(new_end).strftime("%Y/%m/%d")
            duration_name = {
                "week": "۱ هفته",
                "month": "۱ ماه",
                "3month": "۳ ماه",
                "6month": "۶ ماه",
                "year": "۱ سال",
                "christmas": "۳ ماه رایگان"
            }.get(duration_key, duration_key)
            
            remaining = int((new_end - now) / (24 * 3600))
            
            self.bot.send_message(
                user_id,
                f"🎉 <b>دریافت VIP!</b>\n\n"
                f"مدت: {duration_name}\n"
                f"تا تاریخ: {end_date}\n"
                f"باقی‌مانده: {remaining} روز\n"
                f"دلیل: {reason}"
            )
        except:
            pass
        
        return True
    
    def ban_user(self, user_id, duration, reason=""):
        """بن کاربر"""
        bans = self.db.read("bans")
        user_id = str(user_id)
        
        if duration == "permanent":
            bans["permanent"][user_id] = {
                "reason": reason,
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        else:
            minutes = {
                "1h": 60,
                "24h": 1440,
                "7d": 10080
            }.get(duration, 1440)
            
            end_time = time.time() + (minutes * 60)
            bans["temporary"][user_id] = {
                "end": end_time,
                "reason": reason,
                "minutes": minutes
            }
        
        self.db.write("bans", bans)
        
        # پایان چت‌های فعال
        self.end_chat_by_user(user_id)
        
        # اطلاع به کاربر
        try:
            if duration == "permanent":
                msg = f"🚫 <b>بن دائم!</b>\n\nدلیل: {reason}"
            else:
                hours = minutes // 60
                msg = f"🚫 <b>بن موقت {hours} ساعته!</b>\n\nدلیل: {reason}"
            
            self.bot.send_message(user_id, msg)
        except:
            pass
        
        return True
    
    def unban_user(self, user_id):
        """آنبن کاربر"""
        bans = self.db.read("bans")
        user_id = str(user_id)
        
        removed = False
        if user_id in bans.get("permanent", {}):
            del bans["permanent"][user_id]
            removed = True
        if user_id in bans.get("temporary", {}):
            del bans["temporary"][user_id]
            removed = True
        
        if removed:
            self.db.write("bans", bans)
            try:
                self.bot.send_message(user_id, "✅ <b>بن شما لغو شد!</b>\n\nحالا می‌توانید از ربات استفاده کنید.")
            except:
                pass
        
        return removed
    
    def end_chat_by_user(self, user_id):
        """پایان چت توسط کاربر"""
        chats = self.db.read("chats")
        
        for chat_id, chat_info in list(chats.items()):
            if user_id in chat_info.get("users", []):
                users = chat_info["users"]
                other_user = users[1] if users[0] == user_id else users[0]
                self.end_chat(user_id, other_user, "پایان چت")
                return True
        
        return False
    
    def end_chat(self, user1, user2, reason="پایان چت"):
        """پایان چت"""
        chats = self.db.read("chats")
        users_db = self.db.read("users")
        
        # پیدا کردن چت
        chat_id_to_delete = None
        for chat_id, chat_info in chats.items():
            if user1 in chat_info.get("users", []) and user2 in chat_info.get("users", []):
                chat_id_to_delete = chat_id
                break
        
        if chat_id_to_delete:
            del chats[chat_id_to_delete]
            self.db.write("chats", chats)
        
        # بروزرسانی وضعیت کاربران
        user1 = str(user1)
        user2 = str(user2)
        
        if user1 in users_db.get("users", {}):
            users_db["users"][user1]["partner"] = None
            users_db["users"][user1]["state"] = "idle"
        
        if user2 in users_db.get("users", {}):
            users_db["users"][user2]["partner"] = None
            users_db["users"][user2]["state"] = "idle"
        
        self.db.write("users", users_db)
        
        # اطلاع به کاربران
        try:
            self.bot.send_message(user1, f"✅ چت پایان یافت.\nدلیل: {reason}", reply_markup=self.kb_main(user1))
        except:
            pass
        
        try:
            self.bot.send_message(user2, f"✅ چت پایان یافت.\nدلیل: {reason}", reply_markup=self.kb_main(user2))
        except:
            pass
    
    def check_mission_completion(self, user_id):
        """بررسی تکمیل ماموریت روزانه"""
        missions = self.db.read("missions")
        users = self.db.read("users")
        
        user = users.get("users", {}).get(str(user_id), {})
        daily = missions.get("daily", {})
        today = str(datetime.date.today())
        
        # بررسی اگر امروز تکمیل کرده
        if user.get("mission_completed_date") == today:
            return False
        
        mission_type = daily.get("type", "")
        target = daily.get("target", 0)
        completed = False
        
        if mission_type == "chat_count":
            if user.get("daily_chat_count", 0) >= target:
                completed = True
        elif mission_type == "unique_chats":
            if len(user.get("daily_unique_chats", [])) >= target:
                completed = True
        elif mission_type == "referrals":
            if user.get("referrals", 0) >= target:
                completed = True
        
        if completed:
            reward = daily.get("reward", {})
            if reward.get("type") == "coins":
                self.add_coins(user_id, reward.get("amount", 50), "ماموریت روزانه")
            elif reward.get("type") == "vip":
                self.add_vip(user_id, reward.get("duration", "week"), "ماموریت روزانه")
            
            user["mission_completed_date"] = today
            self.db.write("users", users)
            
            return True
        
        return False
    
    # ==========================================
    # کیبوردها
    # ==========================================
    
    def kb_main(self, user_id):
        """کیبورد اصلی"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        # اضافه کردن دکمه پنل مدیریت فقط برای ادمین‌ها
        is_admin = str(user_id) in self.admins
        
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس", "🎯 ماموریت روزانه")
        markup.add("👥 رفرال و دعوت", "🎖 خرید VIP")
        markup.add("❓ راهنما", "⚙ تنظیمات")
        
        if is_admin:
            markup.add("📊 پنل مدیریت")
        
        return markup
    
    def kb_chatting(self):
        """کیبورد حالت چت"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup
    
    def kb_admin(self):
        """کیبورد پنل مدیریت"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📈 آمار کامل", "⚠️ هشدار تعمیر")
        markup.add("🛠 تعمیر و نگهداری", "🎖 گیفت VIP تکی")
        markup.add("🎖 گیفت VIP همگانی", "❌ حذف VIP")
        markup.add("📋 لیست VIP", "💰 اهدای سکه")
        markup.add("🎯 مدیریت ماموریت‌ها", "📁 دانلود دیتابیس")
        markup.add("🚫 لیست بن‌شده‌ها", "🔙 بازگشت به منو")
        markup.add("📝 مدیریت کلمات ممنوعه", "💰 تنظیم قیمت‌های VIP")
        markup.add("⚙️ تنظیمات پیشرفته", "📊 گزارش‌های کاربران")
        return markup
    
    def kb_gender_selection(self):
        """کیبورد انتخاب جنسیت"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("آقا 👦", callback_data="gender_m"),
            types.InlineKeyboardButton("خانم 👧", callback_data="gender_f"),
            types.InlineKeyboardButton("ترجیح می‌دهم نگویم", callback_data="gender_other")
        )
        return markup
    
    def kb_search_preferences(self):
        """کیبورد ترجیحات جستجو"""
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("آقا 👦", callback_data="search_m"),
            types.InlineKeyboardButton("خانم 👧", callback_data="search_f"),
            types.InlineKeyboardButton("هر دو 👥", callback_data="search_any")
        )
        return markup
    
    def kb_report(self):
        """کیبورد گزارش"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("فحاشی", callback_data="report_insult"),
            types.InlineKeyboardButton("+18", callback_data="report_nsfw"),
            types.InlineKeyboardButton("اسپم", callback_data="report_spam"),
            types.InlineKeyboardButton("آزار", callback_data="report_harass"),
            types.InlineKeyboardButton("لغو ❌", callback_data="report_cancel")
        )
        return markup
    
    def kb_vip_purchase(self):
        """کیبورد خرید VIP"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("1 هفته - 500 سکه", callback_data="vip_week"),
            types.InlineKeyboardButton("1 ماه - 1800 سکه", callback_data="vip_month"),
            types.InlineKeyboardButton("3 ماه - 5000 سکه", callback_data="vip_3month"),
            types.InlineKeyboardButton("6 ماه - 9000 سکه", callback_data="vip_6month"),
            types.InlineKeyboardButton("1 سال - 15000 سکه", callback_data="vip_year")
        )
        return markup
    
    # ==========================================
    # هندلرهای اصلی
    # ==========================================
    
    def register_handlers(self):
        """ثبت هندلرهای ربات"""
        
        @self.bot.message_handler(commands=['start'])
        def handle_start(message):
            self.handle_start(message)
        
        @self.bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'voice', 'sticker'])
        def handle_all_messages(message):
            self.handle_all_messages(message)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            self.handle_callback(call)
    
    def handle_start(self, message):
        """مدیریت دستور /start"""
        user_id = str(message.chat.id)
        text = message.text or ""
        
        # بررسی بن
        bans = self.db.read("bans")
        if user_id in bans.get("permanent", {}):
            reason = bans["permanent"][user_id].get("reason", "تخلف")
            self.bot.send_message(user_id, f"🚫 <b>بن دائم!</b>\n\nدلیل: {reason}\nپشتیبانی: {self.support}")
            return
        
        if user_id in bans.get("temporary", {}):
            ban_info = bans["temporary"][user_id]
            end_time = ban_info.get("end", 0)
            if time.time() < end_time:
                remaining = int((end_time - time.time()) / 60)
                hours = remaining // 60
                minutes = remaining % 60
                self.bot.send_message(user_id, f"🚫 <b>بن موقت!</b>\n\nزمان باقی‌مانده: {hours} ساعت و {minutes} دقیقه\nپشتیبانی: {self.support}")
                return
            else:
                del bans["temporary"][user_id]
                self.db.write("bans", bans)
        
        # بررسی حالت تعمیر
        config = self.db.read("config")
        if config.get("maintenance", {}).get("enabled", False):
            if not self.is_vip(user_id) and user_id not in self.admins:
                self.bot.send_message(user_id, config["maintenance"]["message"])
                return
        
        # بررسی عضویت در کانال
        if self.settings.get("security", {}).get("require_channel", True) and user_id not in self.admins:
            try:
                member = self.bot.get_chat_member(self.channel, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{self.channel[1:]}"))
                    markup.add(types.InlineKeyboardButton("بررسی مجدد", callback_data="check_channel"))
                    self.bot.send_message(
                        user_id,
                        f"⚠️ برای استفاده از ربات باید در کانل عضو شوید:\n{self.channel}",
                        reply_markup=markup
                    )
                    return
            except:
                pass
        
        # پردازش لینک دعوت
        if len(text.split()) > 1:
            param = text.split()[1]
            
            if param.startswith("ref_"):
                # سیستم دعوت
                referrer = param[4:]
                if referrer != user_id:
                    users = self.db.read("users")
                    if user_id not in users.get("users", {}) and referrer in users.get("users", {}):
                        # پاداش به دعوت کننده
                        users["users"][referrer]["referrals"] = users["users"][referrer].get("referrals", 0) + 1
                        users["users"][referrer]["referral_list"] = users["users"][referrer].get("referral_list", [])
                        users["users"][referrer]["referral_list"].append(user_id)
                        self.db.write("users", users)
                        
                        # پاداش
                        self.add_coins(referrer, 100, "دعوت دوست")
                        
                        try:
                            self.bot.send_message(referrer, "🎉 یک دوست از لینک شما عضو شد!\n💰 +100 سکه دریافت کردید")
                        except:
                            pass
            
            elif param.startswith("msg_"):
                # پیام ناشناس
                target = param[4:]
                if target != user_id:
                    users = self.db.read("users")
                    if user_id not in users.get("users", {}):
                        users["users"][user_id] = {
                            "state": "name",
                            "vip_end": 0,
                            "coins": 100,
                            "referrals": 0,
                            "warnings": 0,
                            "anon_target": target
                        }
                    else:
                        users["users"][user_id]["anon_target"] = target
                        users["users"][user_id]["state"] = "anon_send"
                    
                    self.db.write("users", users)
                    self.bot.send_message(user_id, "📝 برای ارسال پیام ناشناس، ابتدا نام خود را وارد کنید:")
                    return
        
        # ثبت‌نام یا ورود
        users = self.db.read("users")
        if user_id not in users.get("users", {}):
            # کاربر جدید
            users["users"][user_id] = {
                "state": "name",
                "vip_end": 0,
                "coins": 100,
                "referrals": 0,
                "warnings": 0,
                "daily_chat_count": 0,
                "daily_unique_chats": [],
                "daily_spin": False,
                "mission_completed_date": "",
                "join_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "last_seen": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            self.db.write("users", users)
            
            # بروزرسانی آمار
            stats = self.db.read("stats")
            stats["total_users"] = stats.get("total_users", 0) + 1
            today = str(datetime.date.today())
            if today in stats.get("daily_stats", {}):
                stats["daily_stats"][today]["new_users"] = stats["daily_stats"][today].get("new_users", 0) + 1
            self.db.write("stats", stats)
            
            self.bot.send_message(
                user_id,
                "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\n"
                "🎁 پاداش عضویت: <b>100 سکه</b>\n\n"
                "لطفاً نام مستعار خود را وارد کنید:",
                reply_markup=types.ForceReply()
            )
        else:
            # کاربر قدیمی
            users["users"][user_id]["last_seen"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            self.db.write("users", users)
            
            self.bot.send_message(
                user_id,
                "👋 <b>خوش برگشتید!</b>\n\nچه کاری می‌توانم برای شما انجام دهم؟",
                reply_markup=self.kb_main(user_id)
            )
    
    def handle_all_messages(self, message):
        """مدیریت تمام پیام‌ها"""
        user_id = str(message.chat.id)
        
        # بررسی بن
        bans = self.db.read("bans")
        if user_id in bans.get("permanent", {}):
            return
        
        if user_id in bans.get("temporary", {}):
            if time.time() < bans["temporary"][user_id].get("end", 0):
                return
            else:
                del bans["temporary"][user_id]
                self.db.write("bans", bans)
        
        # بررسی حالت تعمیر
        config = self.db.read("config")
        if config.get("maintenance", {}).get("enabled", False):
            if not self.is_vip(user_id) and user_id not in self.admins:
                return
        
        users = self.db.read("users")
        if user_id not in users.get("users", {}):
            return
        
        user = users["users"][user_id]
        state = user.get("state", "idle")
        
        # بروزرسانی آخرین فعالیت
        user["last_seen"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # ریست روزانه
        today = str(datetime.date.today())
        if user.get("last_active_date") != today:
            user["daily_chat_count"] = 0
            user["daily_unique_chats"] = []
            user["daily_spin"] = False
            user["last_active_date"] = today
        
        # پردازش بر اساس وضعیت
        if state == "name":
            self.handle_registration_name(user_id, message)
        
        elif state == "gender":
            self.handle_registration_gender(user_id, message)
        
        elif state == "age":
            self.handle_registration_age(user_id, message)
        
        elif state == "anon_send":
            self.handle_anon_send(user_id, message)
        
        elif state == "change_name":
            self.handle_change_name(user_id, message)
        
        elif state == "change_age":
            self.handle_change_age(user_id, message)
        
        elif user.get("partner"):
            # حالت چت
            self.handle_chat_message(user_id, message)
        
        else:
            # حالت عادی
            if message.content_type == 'text':
                self.handle_text_command(user_id, message.text)
    
    def handle_registration_name(self, user_id, message):
        """ثبت نام کاربر"""
        if message.content_type != 'text':
            self.bot.send_message(user_id, "❌ لطفاً فقط متن وارد کنید")
            return
        
        name = message.text.strip()
        if len(name) < 2 or len(name) > 20:
            self.bot.send_message(user_id, "❌ نام باید بین ۲ تا ۲۰ حرف باشد")
            return
        
        # بررسی کلمات ممنوعه
        if self.contains_bad_word(name):
            self.bot.send_message(user_id, "❌ نام شامل کلمات نامناسب است")
            return
        
        users = self.db.read("users")
        users["users"][user_id]["name"] = name
        users["users"][user_id]["state"] = "gender"
        self.db.write("users", users)
        
        self.bot.send_message(
            user_id,
            f"✅ نام <b>{name}</b> ثبت شد\n\nلطفاً جنسیت خود را انتخاب کنید:",
            reply_markup=self.kb_gender_selection()
        )
    
    def handle_registration_gender(self, user_id, message):
        """ثبت جنسیت کاربر"""
        if message.content_type != 'text':
            return
        
        users = self.db.read("users")
        gender_map = {"male": "آقا", "female": "خانم", "other": "ترجیح نمی‌دهم بگویم"}
        
        if message.text in gender_map.values():
            users["users"][user_id]["gender"] = message.text
            users["users"][user_id]["state"] = "age"
            self.db.write("users", users)
            
            self.bot.send_message(
                user_id,
                "✅ جنسیت ثبت شد\n\nلطفاً سن خود را وارد کنید (بین ۱۲ تا ۹۹):",
                reply_markup=types.ForceReply()
            )
    
    def handle_registration_age(self, user_id, message):
        """ثبت سن کاربر"""
        if message.content_type != 'text' or not message.text.isdigit():
            self.bot.send_message(user_id, "❌ لطفاً فقط عدد وارد کنید")
            return
        
        age = int(message.text)
        if age < 12 or age > 99:
            self.bot.send_message(user_id, "❌ سن باید بین ۱۲ تا ۹۹ باشد")
            return
        
        users = self.db.read("users")
        users["users"][user_id]["age"] = age
        users["users"][user_id]["state"] = "idle"
        self.db.write("users", users)
        
        # پاداش ثبت‌نام کامل
        self.add_coins(user_id, 50, "تکمیل ثبت‌نام")
        
        self.bot.send_message(
            user_id,
            f"✅ ثبت‌نام با موفقیت تکمیل شد!\n\n"
            f"🎁 پاداش: 50 سکه\n"
            f"💰 موجودی شما: {users['users'][user_id]['coins']} سکه\n\n"
            f"حالا می‌توانید از ربات استفاده کنید!",
            reply_markup=self.kb_main(user_id)
        )
    
    def handle_anon_send(self, user_id, message):
        """ارسال پیام ناشناس"""
        if message.content_type != 'text':
            self.bot.send_message(user_id, "❌ فقط پیام متنی قابل ارسال است")
            return
        
        users = self.db.read("users")
        user = users["users"][user_id]
        target_id = user.get("anon_target")
        
        if not target_id:
            self.bot.send_message(user_id, "❌ خطا در ارسال پیام")
            return
        
        message_text = message.text[:500]  # محدودیت طول
        
        # ذخیره پیام
        messages = self.db.read("messages")
        if target_id not in messages["inbox"]:
            messages["inbox"][target_id] = []
        
        messages["inbox"][target_id].append({
            "text": message_text,
            "from": user_id,
            "time": datetime.datetime.now().strftime("%H:%M %d/%m"),
            "seen": False
        })
        
        # محدود کردن تعداد پیام‌ها
        if len(messages["inbox"][target_id]) > 50:
            messages["inbox"][target_id] = messages["inbox"][target_id][-50:]
        
        self.db.write("messages", messages)
        
        # بروزرسانی وضعیت کاربر
        users["users"][user_id]["state"] = "idle"
        if "anon_target" in users["users"][user_id]:
            del users["users"][user_id]["anon_target"]
        self.db.write("users", users)
        
        # اطلاع به فرستنده
        self.bot.send_message(user_id, "✅ پیام ناشناس شما ارسال شد")
        
        # اطلاع به گیرنده
        try:
            self.bot.send_message(target_id, "📩 یک پیام ناشناس جدید دریافت کردید!")
        except:
            pass
    
    def handle_chat_message(self, user_id, message):
        """مدیریت پیام‌های چت"""
        users = self.db.read("users")
        user = users["users"][user_id]
        partner_id = user.get("partner")
        
        if not partner_id or partner_id not in users.get("users", {}):
            self.bot.send_message(user_id, "⚠️ ارتباط با هم‌صحبت قطع شد", reply_markup=self.kb_main(user_id))
            users["users"][user_id]["partner"] = None
            users["users"][user_id]["state"] = "idle"
            self.db.write("users", users)
            return
        
        partner = users["users"][partner_id]
        
        # دستورات چت
        if message.content_type == 'text':
            text = message.text
            
            if text == "🔚 پایان گفتگو":
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ بله", callback_data=f"end_chat_yes_{partner_id}"),
                    types.InlineKeyboardButton("❌ خیر", callback_data="end_chat_no")
                )
                self.bot.send_message(user_id, "آیا مطمئن هستید که می‌خواهید چت را پایان دهید؟", reply_markup=markup)
                return
            
            elif text == "🚩 گزارش تخلف":
                user["report_target"] = partner_id
                self.db.write("users", users)
                self.bot.send_message(user_id, "لطفاً نوع تخلف را انتخاب کنید:", reply_markup=self.kb_report())
                return
            
            elif text == "🚫 بلاک و خروج":
                # بلاک کردن
                if "blocked_users" not in user:
                    user["blocked_users"] = []
                if partner_id not in user["blocked_users"]:
                    user["blocked_users"].append(partner_id)
                
                self.end_chat(user_id, partner_id, "شما بلاک شدید")
                self.bot.send_message(user_id, "✅ کاربر بلاک شد")
                return
            
            elif text == "👥 درخواست آیدی":
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ موافقم", callback_data=f"share_id_yes_{user_id}"),
                    types.InlineKeyboardButton("❌ مخالفم", callback_data="share_id_no")
                )
                self.bot.send_message(partner_id, "هم‌صحبت شما درخواست اشتراک‌گذاری آیدی دارد. موافقید؟", reply_markup=markup)
                self.bot.send_message(user_id, "درخواست شما ارسال شد...")
                return
            
            # بررسی فحش
            if self.contains_bad_word(text):
                try:
                    self.bot.delete_message(user_id, message.message_id)
                except:
                    pass
                
                user["warnings"] = user.get("warnings", 0) + 1
                self.db.write("users", users)
                
                if user["warnings"] >= 3:
                    self.ban_user(user_id, "24h", "فحاشی مکرر")
                    self.end_chat(user_id, partner_id, "به دلیل تخلف بن شد")
                    self.bot.send_message(user_id, "🚫 به دلیل فحاشی، حساب شما ۲۴ ساعت مسدود شد")
                else:
                    self.bot.send_message(user_id, f"⚠️ اخطار {user['warnings']}/3\nارسال محتوای نامناسب ممنوع است!")
                return
        
        # شمارش پیام برای ماموریت
        user["daily_chat_count"] = user.get("daily_chat_count", 0) + 1
        
        # اضافه کردن به لیست چت‌های منحصر به فرد
        if "daily_unique_chats" not in user:
            user["daily_unique_chats"] = []
        if partner_id not in user["daily_unique_chats"]:
            user["daily_unique_chats"].append(partner_id)
        
        self.db.write("users", users)
        
        # ارسال پیام به هم‌صحبت
        try:
            if message.content_type == 'text':
                self.bot.send_message(partner_id, message.text)
            elif message.content_type == 'photo':
                self.bot.send_photo(partner_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'video':
                self.bot.send_video(partner_id, message.video.file_id, caption=message.caption)
            elif message.content_type == 'voice':
                self.bot.send_voice(partner_id, message.voice.file_id)
            elif message.content_type == 'sticker':
                self.bot.send_sticker(partner_id, message.sticker.file_id)
        except Exception as e:
            logger.error(f"خطا در ارسال پیام: {e}")
            self.bot.send_message(user_id, "⚠️ خطا در ارسال پیام")
        
        # بررسی ماموریت
        self.check_mission_completion(user_id)
    
    def handle_text_command(self, user_id, text):
        """مدیریت دستورات متنی"""
        users = self.db.read("users")
        user = users["users"][user_id]
        
        if text == "🛰 شروع چت ناشناس":
            if user.get("partner"):
                self.bot.send_message(user_id, "⚠️ شما در حال چت هستید!")
                return
            
            self.bot.send_message(
                user_id,
                "🔍 لطفاً جنسیت مورد نظر خود را انتخاب کنید:",
                reply_markup=self.kb_search_preferences()
            )
        
        elif text == "👤 پروفایل من":
            self.show_profile(user_id)
        
        elif text == "📩 لینک ناشناس من":
            link = f"https://t.me/{self.username}?start=msg_{user_id}"
            self.bot.send_message(
                user_id,
                f"🔗 <b>لینک ناشناس شما:</b>\n\n"
                f"<code>{link}</code>\n\n"
                f"با این لینک دیگران می‌توانند به شما پیام ناشناس ارسال کنند."
            )
        
        elif text == "📥 پیام‌های ناشناس":
            self.show_inbox(user_id)
        
        elif text == "🎡 گردونه شانس":
            self.spin_wheel(user_id)
        
        elif text == "🎯 ماموریت روزانه":
            self.show_daily_mission(user_id)
        
        elif text == "👥 رفرال و دعوت":
            self.show_referral_info(user_id)
        
        elif text == "🎖 خرید VIP":
            self.show_vip_store(user_id)
        
        elif text == "❓ راهنما":
            self.show_help(user_id)
        
        elif text == "⚙ تنظیمات":
            self.show_settings(user_id)
        
        elif text == "📊 پنل مدیریت":
            if str(user_id) not in self.admins:
                self.bot.send_message(user_id, "⛔ دسترسی غیرمجاز")
            else:
                self.show_admin_panel(user_id)
        
        else:
            # اگر کاربر ادمین است، دستورات ادمین را بررسی کن
            if str(user_id) in self.admins:
                self.handle_admin_command(user_id, text)
            else:
                self.bot.send_message(user_id, "⚠️ دستور نامعتبر!\nلطفاً از منو استفاده کنید.")
    
    def handle_callback(self, call):
        """مدیریت callback‌ها"""
        user_id = str(call.message.chat.id)
        data = call.data
        
        if data.startswith("gender_"):
            gender = data.split("_")[1]
            gender_map = {"m": "آقا", "f": "خانم", "other": "ترجیح نمی‌دهم بگویم"}
            
            users = self.db.read("users")
            users["users"][user_id]["gender"] = gender_map.get(gender, "ترجیح نمی‌دهم بگویم")
            users["users"][user_id]["state"] = "age"
            self.db.write("users", users)
            
            self.bot.edit_message_text(
                "✅ جنسیت ثبت شد\n\nلطفاً سن خود را وارد کنید (بین ۱۲ تا ۹۹):",
                user_id,
                call.message.message_id
            )
        
        elif data.startswith("search_"):
            preference = data.split("_")[1]
            self.start_chat_search(user_id, preference)
        
        elif data.startswith("end_chat_"):
            action = data.split("_")[2]
            if action == "yes":
                partner_id = data.split("_")[3]
                self.end_chat(user_id, partner_id)
            self.bot.delete_message(user_id, call.message.message_id)
        
        elif data.startswith("report_"):
            report_type = data.split("_")[1]
            if report_type == "cancel":
                self.bot.delete_message(user_id, call.message.message_id)
                return
            
            users = self.db.read("users")
            user = users["users"][user_id]
            target_id = user.get("report_target")
            
            if target_id:
                # ارسال گزارش به ادمین
                report_text = f"⚠️ <b>گزارش تخلف</b>\n\n"
                report_text += f"👤 گزارش‌دهنده: {user.get('name')} ({user_id})\n"
                report_text += f"🎯 گزارش‌شده: {users['users'].get(target_id, {}).get('name', 'ناشناس')} ({target_id})\n"
                report_text += f"📌 نوع: {report_type}\n"
                report_text += f"🕒 زمان: {datetime.datetime.now().strftime('%H:%M %d/%m')}"
                
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("🚫 بن ۲۴h", callback_data=f"admin_ban24_{target_id}"),
                    types.InlineKeyboardButton("⛔ بن دائم", callback_data=f"admin_banperm_{target_id}"),
                    types.InlineKeyboardButton("✅ نادیده", callback_data=f"admin_ignore_{target_id}")
                )
                
                for admin_id in self.admins:
                    try:
                        self.bot.send_message(admin_id, report_text, reply_markup=markup)
                    except:
                        pass
            
            self.bot.edit_message_text(
                "✅ گزارش شما ثبت شد",
                user_id,
                call.message.message_id
            )
        
        elif data.startswith("share_id_"):
            action = data.split("_")[2]
            if action == "yes":
                target_id = data.split("_")[3]
                try:
                    # ارسال آیدی به درخواست کننده
                    self.bot.send_message(
                        target_id,
                        f"✅ هم‌صحبت موافقت کرد!\n\n"
                        f"آیدی: @{call.from_user.username or user_id}"
                    )
                    # اطلاع به اجازه دهنده
                    self.bot.send_message(user_id, "✅ آیدی شما ارسال شد")
                except:
                    pass
            
            self.bot.delete_message(user_id, call.message.message_id)
        
        elif data.startswith("vip_"):
            duration = data.split("_")[1]
            self.purchase_vip(user_id, duration)
        
        elif data == "check_channel":
            try:
                member = self.bot.get_chat_member(self.channel, user_id)
                if member.status in ['member', 'administrator', 'creator']:
                    self.bot.delete_message(user_id, call.message.message_id)
                    self.handle_start(types.Message(
                        message_id=call.message.message_id,
                        chat=types.Chat(id=user_id, type='private'),
                        from_user=call.from_user,
                        date=int(time.time()),
                        content_type='text',
                        text='/start'
                    ))
                else:
                    self.bot.answer_callback_query(call.id, "⚠️ هنوز عضو نشدید!")
            except:
                self.bot.answer_callback_query(call.id, "⚠️ خطا در بررسی عضویت")
        
        elif data.startswith("admin_"):
            # فقط ادمین‌ها
            if str(user_id) not in self.admins:
                self.bot.answer_callback_query(call.id, "⛔ دسترسی غیرمجاز")
                return
            
            action = data.split("_")[1]
            target_id = data.split("_")[2]
            
            if action == "ban24":
                self.ban_user(target_id, "24h", "گزارش کاربر")
                self.bot.answer_callback_query(call.id, f"کاربر {target_id} بن 24h شد")
            
            elif action == "banperm":
                self.ban_user(target_id, "permanent", "گزارش کاربر")
                self.bot.answer_callback_query(call.id, f"کاربر {target_id} بن دائم شد")
            
            elif action == "ignore":
                self.bot.answer_callback_query(call.id, "گزارش نادیده گرفته شد")
            
            self.bot.delete_message(user_id, call.message.message_id)
        
        elif data.startswith("anon_reply_"):
            index = int(data.split("_")[2])
            self.reply_to_anonymous(user_id, index)
        
        elif data.startswith("anon_delete_"):
            index = int(data.split("_")[2])
            self.delete_anonymous(user_id, index)
        
        # پاسخ دادن به همه callback‌ها
        self.bot.answer_callback_query(call.id)
    
    # ==========================================
    # توابع اصلی
    # ==========================================
    
    def contains_bad_word(self, text):
        """بررسی کلمات ممنوعه"""
        if not text:
            return False
        text_lower = text.lower()
        return any(bad_word in text_lower for bad_word in self.bad_words)
    
    def start_chat_search(self, user_id, preference):
        """شروع جستجوی چت"""
        users = self.db.read("users")
        queue = self.db.read("queue")
        
        # بررسی اگر در حال چت هست
        if users["users"][user_id].get("partner"):
            self.bot.send_message(user_id, "⚠️ شما در حال چت هستید!")
            return
        
        # بررسی اگر در صف هست
        if user_id in queue["general"] or user_id in queue["vip"]:
            self.bot.send_message(user_id, "⏳ شما در صف انتظار هستید!")
            return
        
        # تعیین صف بر اساس VIP
        queue_type = "vip" if self.is_vip(user_id) else "general"
        
        # اضافه به صف
        queue[queue_type].append(user_id)
        queue["waiting_time"][user_id] = time.time()
        
        # ذخیره ترجیحات
        users["users"][user_id]["search_pref"] = preference
        users["users"][user_id]["state"] = "searching"
        
        self.db.write("queue", queue)
        self.db.write("users", users)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ لغو جستجو", callback_data="cancel_search"))
        
        self.bot.send_message(
            user_id,
            f"🔍 در حال جستجوی هم‌صحبت...\n\n"
            f"صف: {'⭐ VIP' if queue_type == 'vip' else '👤 عمومی'}\n"
            f"ترجیح: {'آقا 👦' if preference == 'm' else 'خانم 👧' if preference == 'f' else 'هر دو 👥'}",
            reply_markup=markup
        )
        
        # شروع جستجو
        Thread(target=self.search_for_partner, args=(user_id, queue_type, preference), daemon=True).start()
    
    def search_for_partner(self, user_id, queue_type, preference):
        """جستجوی هم‌صحبت"""
        start_time = time.time()
        max_wait = 300  # 5 دقیقه
        
        while time.time() - start_time < max_wait:
            time.sleep(5)  # هر 5 ثانیه بررسی
            
            queue = self.db.read("queue")
            users = self.db.read("users")
            
            # بررسی اگر کاربر از صف خارج شده
            if user_id not in queue[queue_type]:
                return
            
            # جستجو در صف‌ها (اولویت با VIP)
            search_queues = ["vip", "general"] if queue_type == "vip" else ["general", "vip"]
            
            for q_type in search_queues:
                for candidate_id in queue[q_type]:
                    if candidate_id == user_id:
                        continue
                    
                    candidate = users["users"].get(candidate_id, {})
                    if not candidate:
                        continue
                    
                    # بررسی تطابق ترجیحات
                    candidate_pref = candidate.get("search_pref", "any")
                    user_gender = users["users"][user_id].get("gender", "")
                    candidate_gender = candidate.get("gender", "")
                    
                    compatible = False
                    
                    if preference == "any" or candidate_gender in ["", "ترجیح نمی‌دهم بگویم"]:
                        compatible = True
                    elif preference == "m" and candidate_gender == "آقا":
                        compatible = True
                    elif preference == "f" and candidate_gender == "خانم":
                        compatible = True
                    
                    if candidate_pref != "any" and user_gender:
                        if candidate_pref == "m" and user_gender != "آقا":
                            compatible = False
                        elif candidate_pref == "f" and user_gender != "خانم":
                            compatible = False
                    
                    if compatible:
                        # حذف از صف
                        queue["general"] = [uid for uid in queue["general"] if uid not in [user_id, candidate_id]]
                        queue["vip"] = [uid for uid in queue["vip"] if uid not in [user_id, candidate_id]]
                        
                        # ایجاد چت
                        chat_id = str(uuid.uuid4())
                        chats = self.db.read("chats")
                        chats[chat_id] = {
                            "users": [user_id, candidate_id],
                            "started_at": time.time(),
                            "last_activity": time.time()
                        }
                        
                        # بروزرسانی کاربران
                        users["users"][user_id]["partner"] = candidate_id
                        users["users"][user_id]["state"] = "chatting"
                        users["users"][candidate_id]["partner"] = user_id
                        users["users"][candidate_id]["state"] = "chatting"
                        
                        self.db.write("queue", queue)
                        self.db.write("chats", chats)
                        self.db.write("users", users)
                        
                        # ارسال پیام شروع
                        try:
                            user_name = users["users"][user_id].get("name", "کاربر")
                            candidate_name = candidate.get("name", "کاربر")
                            
                            self.bot.send_message(
                                user_id,
                                f"🎉 <b>هم‌صحبت پیدا شد!</b>\n\n"
                                f"👤 نام: {candidate_name}\n"
                                f"🔞 سن: {candidate.get('age', 'نامشخص')}\n"
                                f"👫 جنسیت: {candidate_gender}\n\n"
                                f"حالا می‌توانید چت کنید ✨",
                                reply_markup=self.kb_chatting()
                            )
                            
                            self.bot.send_message(
                                candidate_id,
                                f"🎉 <b>هم‌صحبت پیدا شد!</b>\n\n"
                                f"👤 نام: {user_name}\n"
                                f"🔞 سن: {users['users'][user_id].get('age', 'نامشخص')}\n"
                                f"👫 جنسیت: {user_gender}\n\n"
                                f"حالا می‌توانید چت کنید ✨",
                                reply_markup=self.kb_chatting()
                            )
                        except Exception as e:
                            logger.error(f"خطا در ارسال پیام شروع چت: {e}")
                        
                        return
            
            # ارسال وضعیت
            if int(time.time() - start_time) % 30 == 0:  # هر 30 ثانیه
                try:
                    wait_time = int(time.time() - start_time)
                    self.bot.send_message(
                        user_id,
                        f"⏳ هنوز در حال جستجو... ({wait_time//60}:{wait_time%60:02d})\n"
                        f"تعداد کاربران در صف: {len(queue[queue_type])}"
                    )
                except:
                    pass
        
        # زمان انتظار تمام شد
        queue = self.db.read("queue")
        users = self.db.read("users")
        
        if user_id in queue[queue_type]:
            queue[queue_type].remove(user_id)
        
        if user_id in users["users"]:
            users["users"][user_id]["state"] = "idle"
        
        self.db.write("queue", queue)
        self.db.write("users", users)
        
        self.bot.send_message(
            user_id,
            "⏰ زمان جستجو به پایان رسید.\nلطفاً دوباره تلاش کنید.",
            reply_markup=self.kb_main(user_id)
        )
    
    def show_profile(self, user_id):
        """نمایش پروفایل"""
        users = self.db.read("users")
        user = users["users"].get(user_id, {})
        
        if not user.get("name"):
            self.bot.send_message(user_id, "⚠️ لطفاً ابتدا ثبت‌نام کنید")
            return
        
        # شمارش بازدید پروفایل برای ماموریت
        user["daily_profile_views"] = user.get("daily_profile_views", 0) + 1
        self.db.write("users", users)
        
        # اطلاعات پروفایل
        vip_end = user.get("vip_end", 0)
        is_vip = self.is_vip(vip_end=vip_end)
        
        profile_text = f"👤 <b>پروفایل شما</b>\n\n"
        profile_text += f"📛 نام: {user.get('name', 'نامشخص')}\n"
        profile_text += f"👫 جنسیت: {user.get('gender', 'نامشخص')}\n"
        profile_text += f"🔞 سن: {user.get('age', 'نامشخص')}\n"
        profile_text += f"💰 سکه: {user.get('coins', 0):,}\n"
        profile_text += f"🎖 وضعیت: {'⭐ VIP' if is_vip else '👤 عادی'}\n"
        
        if is_vip:
            remaining = int((vip_end - time.time()) / (24 * 3600))
            end_date = datetime.datetime.fromtimestamp(vip_end).strftime("%Y/%m/%d")
            profile_text += f"⏳ باقی‌مانده: {remaining} روز (تا {end_date})\n"
        
        profile_text += f"👥 دعوت‌ها: {user.get('referrals', 0)} نفر\n"
        profile_text += f"💬 چت‌ها: {user.get('total_chats', 0)}\n"
        profile_text += f"⚠️ اخطار: {user.get('warnings', 0)}/3\n"
        profile_text += f"📅 عضویت: {user.get('join_date', 'نامشخص')}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام", callback_data="change_name"),
            types.InlineKeyboardButton("🔢 تغییر سن", callback_data="change_age")
        )
        
        self.bot.send_message(user_id, profile_text, reply_markup=markup)
        
        # بررسی ماموریت
        self.check_mission_completion(user_id)
    
    def show_inbox(self, user_id):
        """نمایش پیام‌های ناشناس"""
        messages = self.db.read("messages")
        user_inbox = messages["inbox"].get(user_id, [])
        
        if not user_inbox:
            self.bot.send_message(user_id, "📭 پیام ناشناسی دریافت نکرده‌اید")
            return
        
        text = "📥 <b>پیام‌های ناشناس شما</b>\n\n"
        
        for i, msg in enumerate(user_inbox[:10]):  # فقط 10 پیام اول
            status = "✅" if msg.get("seen") else "🔵"
            text += f"{status} <b>پیام {i+1}:</b>\n{msg['text']}\n"
            text += f"<i>🕐 {msg.get('time', 'نامشخص')}</i>\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for i in range(min(5, len(user_inbox))):
            markup.add(
                types.InlineKeyboardButton(f"📝 پاسخ {i+1}", callback_data=f"anon_reply_{i}"),
                types.InlineKeyboardButton(f"🗑 حذف {i+1}", callback_data=f"anon_delete_{i}")
            )
        
        self.bot.send_message(user_id, text, reply_markup=markup)
        
        # علامت‌گذاری به عنوان دیده شده
        for msg in user_inbox:
            msg["seen"] = True
        
        self.db.write("messages", messages)
    
    def spin_wheel(self, user_id):
        """چرخاندن گردونه شانس"""
        users = self.db.read("users")
        user = users["users"].get(user_id, {})
        
        today = str(datetime.date.today())
        
        # بررسی اگر امروز چرخانده
        if user.get("daily_spin"):
            self.bot.send_message(user_id, "⏳ امروز قبلاً گردونه را چرخانده‌اید!\nفردا دوباره امتحان کنید.")
            return
        
        # چرخاندن
        spin_result = random.random()
        
        if spin_result < 0.01:  # 1% شانس
            reward = {"type": "vip", "duration": "week", "amount": 0}
            reward_text = "🎉 جکپات! 🎖 VIP 1 هفته"
            self.add_vip(user_id, "week", "گردونه شانس")
        
        elif spin_result < 0.1:  # 9% شانس
            coins = random.randint(200, 500)
            reward = {"type": "coins", "amount": coins}
            reward_text = f"🎁 برنده شدید! 💰 {coins} سکه"
            self.add_coins(user_id, coins, "گردونه شانس")
        
        elif spin_result < 0.4:  # 30% شانس
            coins = random.randint(50, 150)
            reward = {"type": "coins", "amount": coins}
            reward_text = f"🎯 آفرین! 💰 {coins} سکه"
            self.add_coins(user_id, coins, "گردونه شانس")
        
        else:  # 60% شانس
            reward = {"type": "none", "amount": 0}
            reward_text = "😔 متأسفانه برنده نشدید\nشانس بعدی!"
        
        # بروزرسانی وضعیت کاربر
        user["daily_spin"] = True
        users["users"][user_id] = user
        self.db.write("users", users)
        
        # نمایش نتیجه
        self.bot.send_message(
            user_id,
            f"🎡 <b>گردونه شانس</b>\n\n"
            f"گردونه در حال چرخش...\n\n"
            f"<b>نتیجه:</b> {reward_text}"
        )
        
        # بررسی ماموریت
        self.check_mission_completion(user_id)
    
    def show_daily_mission(self, user_id):
        """نمایش ماموریت روزانه"""
        missions = self.db.read("missions")
        users = self.db.read("users")
        
        daily = missions.get("daily", {})
        user = users["users"].get(user_id, {})
        today = str(datetime.date.today())
        
        mission_text = f"🎯 <b>ماموریت روزانه</b>\n\n"
        mission_text += f"📋 {daily.get('name', 'ماموریت')}\n"
        mission_text += f"📝 {daily.get('description', '')}\n\n"
        
        # پیشرفت
        mission_type = daily.get("type", "")
        target = daily.get("target", 0)
        
        if mission_type == "chat_count":
            progress = user.get("daily_chat_count", 0)
            mission_text += f"📊 پیشرفت: {progress}/{target} پیام\n"
        elif mission_type == "unique_chats":
            progress = len(user.get("daily_unique_chats", []))
            mission_text += f"📊 پیشرفت: {progress}/{target} نفر\n"
        elif mission_type == "referrals":
            progress = user.get("referrals", 0)
            mission_text += f"📊 پیشرفت: {progress}/{target} دعوت\n"
        
        # پاداش
        reward = daily.get("reward", {})
        if reward.get("type") == "coins":
            mission_text += f"🎁 پاداش: {reward.get('amount', 0)} سکه\n"
        elif reward.get("type") == "vip":
            mission_text += f"🎁 پاداش: VIP {reward.get('duration', '')}\n"
        
        # وضعیت تکمیل
        if user.get("mission_completed_date") == today:
            mission_text += "\n✅ <b>تکمیل شده!</b>"
        else:
            mission_text += "\n📌 برای دریافت پاداش ماموریت را تکمیل کنید."
        
        self.bot.send_message(user_id, mission_text)
        
        # بررسی ماموریت
        self.check_mission_completion(user_id)
    
    def show_referral_info(self, user_id):
        """نمایش اطلاعات دعوت"""
        users = self.db.read("users")
        user = users["users"].get(user_id, {})
        
        ref_link = f"https://t.me/{self.username}?start=ref_{user_id}"
        ref_count = user.get("referrals", 0)
        
        ref_text = f"👥 <b>سیستم دعوت دوستان</b>\n\n"
        ref_text += f"🔗 لینک اختصاصی شما:\n<code>{ref_link}</code>\n\n"
        ref_text += f"📊 تعداد دعوت شده‌ها: {ref_count} نفر\n\n"
        ref_text += "🎁 <b>پاداش‌ها:</b>\n"
        ref_text += "• هر دعوت موفق: 100 سکه\n"
        ref_text += "• ۲ دعوت: VIP 1 هفته\n"
        ref_text += "• ۵ دعوت: VIP 1 ماه\n\n"
        ref_text += "لینک خود را با دوستان به اشتراک بگذارید و پاداش بگیرید! ✨"
        
        self.bot.send_message(user_id, ref_text)
    
    def show_vip_store(self, user_id):
        """نمایش فروشگاه VIP"""
        vip_prices = self.db.read("vip_prices")
        users = self.db.read("users")
        user = users["users"].get(user_id, {})
        
        if self.is_vip(user_id):
            vip_end = user.get("vip_end", 0)
            remaining = int((vip_end - time.time()) / (24 * 3600))
            end_date = datetime.datetime.fromtimestamp(vip_end).strftime("%Y/%m/%d")
            
            self.bot.send_message(
                user_id,
                f"🎖 <b>شما در حال حاضر VIP هستید!</b>\n\n"
                f"⏳ باقی‌مانده: {remaining} روز\n"
                f"📅 تا تاریخ: {end_date}\n\n"
                f"می‌توانید مدت VIP خود را تمدید کنید:"
            )
        
        store_text = "💎 <b>فروشگاه VIP</b>\n\n"
        
        for duration, price in vip_prices.items():
            if duration == "christmas":
                if user.get("christmas_vip_taken"):
                    continue
                store_text += f"🎄 3 ماه رایگان (کریسمس)\n"
            else:
                duration_name = {
                    "week": "۱ هفته",
                    "month": "۱ ماه", 
                    "3month": "۳ ماه",
                    "6month": "۶ ماه",
                    "year": "۱ سال"
                }.get(duration, duration)
                store_text += f"{duration_name}: {price:,} سکه\n"
        
        store_text += f"\n💰 موجودی شما: {user.get('coins', 0):,} سکه"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for duration in ["week", "month", "3month", "6month", "year"]:
            if duration in vip_prices:
                markup.add(types.InlineKeyboardButton(
                    f"{duration} - {vip_prices[duration]:,} سکه",
                    callback_data=f"vip_{duration}"
                ))
        
        if not user.get("christmas_vip_taken") and "christmas" in vip_prices:
            markup.add(types.InlineKeyboardButton(
                "🎄 3 ماه رایگان",
                callback_data="vip_christmas"
            ))
        
        self.bot.send_message(user_id, store_text, reply_markup=markup)
    
    def purchase_vip(self, user_id, duration):
        """خرید VIP"""
        vip_prices = self.db.read("vip_prices")
        users = self.db.read("users")
        
        if user_id not in users["users"]:
            self.bot.send_message(user_id, "⚠️ ابتدا ثبت‌نام کنید")
            return
        
        user = users["users"][user_id]
        
        # بررسی VIP کریسمس
        if duration == "christmas":
            if user.get("christmas_vip_taken"):
                self.bot.send_message(user_id, "⚠️ قبلاً از این پیشنهاد استفاده کرده‌اید")
                return
            
            self.add_vip(user_id, "christmas", "VIP کریسمس")
            user["christmas_vip_taken"] = True
            self.db.write("users", users)
            return
        
        # بررسی موجودی
        price = vip_prices.get(duration, 0)
        if user.get("coins", 0) < price:
            self.bot.send_message(user_id, f"❌ موجودی کافی نیست!\n💰 نیاز: {price:,} سکه\n💰 موجود: {user['coins']:,} سکه")
            return
        
        # کسر سکه
        user["coins"] -= price
        self.db.write("users", users)
        
        # افزودن VIP
        self.add_vip(user_id, duration, "خرید VIP")
    
    def show_help(self, user_id):
        """نمایش راهنما"""
        help_text = """
📚 <b>راهنمای Shadow Titan</b>

🎯 <b>امکانات اصلی:</b>
• چت ناشناس: با افراد جدید آشنا شوید
• پیام ناشناس: پیام مخفی برای دیگران بفرستید
• گردونه شانس: هر روز شانس خود را امتحان کنید
• ماموریت روزانه: پاداش روزانه بگیرید
• سیستم دعوت: دوستان خود را دعوت کنید و پاداش بگیرید
• سیستم VIP: امکانات ویژه دریافت کنید

🔐 <b>قوانین:</b>
۱. احترام به دیگران الزامی است
۲. ارسال محتوای نامناسب ممنوع
۳. حداقل سن ۱۲ سال
۴. هر کاربر ۳ اخطار دارد
۵. در صورت تخلف حساب مسدود می‌شود

📞 <b>پشتیبانی:</b>
• کانال: @ChatNaAnnouncements
• پشتیبانی: @its_alimo

✅ از ربات لذت ببرید!
        """
        
        self.bot.send_message(user_id, help_text)
    
    def show_settings(self, user_id):
        """نمایش تنظیمات"""
        users = self.db.read("users")
        user = users["users"].get(user_id, {})
        
        settings_text = "⚙️ <b>تنظیمات حساب</b>\n\n"
        settings_text += f"📛 نام: {user.get('name', 'تعیین نشده')}\n"
        settings_text += f"🔞 سن: {user.get('age', 'تعیین نشده')}\n"
        settings_text += f"👫 جنسیت: {user.get('gender', 'تعیین نشده')}\n"
        settings_text += f"🔔 نوتیفیکیشن: {'فعال ✅' if user.get('notifications', True) else 'غیرفعال ❌'}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام", callback_data="change_name"),
            types.InlineKeyboardButton("🔢 تغییر سن", callback_data="change_age")
        )
        markup.add(
            types.InlineKeyboardButton("🔔 تنظیم نوتیفیکیشن", callback_data="toggle_notif")
        )
        
        self.bot.send_message(user_id, settings_text, reply_markup=markup)
    
    def handle_change_name(self, user_id, message):
        """تغییر نام"""
        if message.content_type != 'text':
            self.bot.send_message(user_id, "❌ لطفاً فقط متن وارد کنید")
            return
        
        name = message.text.strip()
        if len(name) < 2 or len(name) > 20:
            self.bot.send_message(user_id, "❌ نام باید بین ۲ تا ۲۰ حرف باشد")
            return
        
        if self.contains_bad_word(name):
            self.bot.send_message(user_id, "❌ نام شامل کلمات نامناسب است")
            return
        
        users = self.db.read("users")
        users["users"][user_id]["name"] = name
        users["users"][user_id]["state"] = "idle"
        self.db.write("users", users)
        
        self.bot.send_message(user_id, f"✅ نام به <b>{name}</b> تغییر یافت", reply_markup=self.kb_main(user_id))
    
    def handle_change_age(self, user_id, message):
        """تغییر سن"""
        if message.content_type != 'text' or not message.text.isdigit():
            self.bot.send_message(user_id, "❌ لطفاً فقط عدد وارد کنید")
            return
        
        age = int(message.text)
        if age < 12 or age > 99:
            self.bot.send_message(user_id, "❌ سن باید بین ۱۲ تا ۹۹ باشد")
            return
        
        users = self.db.read("users")
        users["users"][user_id]["age"] = age
        users["users"][user_id]["state"] = "idle"
        self.db.write("users", users)
        
        self.bot.send_message(user_id, f"✅ سن به <b>{age}</b> تغییر یافت", reply_markup=self.kb_main(user_id))
    
    def reply_to_anonymous(self, user_id, index):
        """پاسخ به پیام ناشناس"""
        messages = self.db.read("messages")
        user_inbox = messages["inbox"].get(user_id, [])
        
        if index >= len(user_inbox):
            self.bot.send_message(user_id, "❌ پیام مورد نظر یافت نشد")
            return
        
        message = user_inbox[index]
        sender_id = message.get("from")
        
        if not sender_id:
            self.bot.send_message(user_id, "❌ خطا در یافتن فرستنده")
            return
        
        users = self.db.read("users")
        users["users"][user_id]["state"] = "anon_reply"
        users["users"][user_id]["anon_reply_to"] = sender_id
        self.db.write("users", users)
        
        self.bot.send_message(
            user_id,
            f"📝 <b>پاسخ به پیام ناشناس</b>\n\n"
            f"پیام اصلی: {message['text']}\n\n"
            f"لطفاً پاسخ خود را بنویسید:"
        )
    
    def delete_anonymous(self, user_id, index):
        """حذف پیام ناشناس"""
        messages = self.db.read("messages")
        user_inbox = messages["inbox"].get(user_id, [])
        
        if index < len(user_inbox):
            del user_inbox[index]
            messages["inbox"][user_id] = user_inbox
            self.db.write("messages", messages)
            self.bot.send_message(user_id, "✅ پیام حذف شد")
        else:
            self.bot.send_message(user_id, "❌ پیام مورد نظر یافت نشد")
    
    # ==========================================
    # پنل مدیریت
    # ==========================================
    
    def show_admin_panel(self, user_id):
        """نمایش پنل مدیریت"""
        if str(user_id) not in self.admins:
            self.bot.send_message(user_id, "⛔ دسترسی غیرمجاز")
            return
        
        stats = self.db.read("stats")
        
        panel_text = f"""
👑 <b>پنل مدیریت Shadow Titan</b>

📊 <b>آمار کلی:</b>
├ 👥 کل کاربران: {stats.get('total_users', 0):,}
├ 🌟 کاربران VIP: {stats.get('vip_users', 0):,}
├ 💬 چت‌های فعال: {len(self.db.read('chats'))}
├ 🔍 در حال جستجو: {len(self.db.read('queue')['general']) + len(self.db.read('queue')['vip'])}
└ 🚫 بن شده‌ها: {len(self.db.read('bans')['permanent']) + len(self.db.read('bans')['temporary'])}

📈 <b>امروز:</b>
├ 👤 کاربران فعال: {stats.get('active_today', 0)}
└ 📅 تاریخ: {datetime.datetime.now().strftime('%Y/%m/%d')}

⚙️ <b>وضعیت:</b>
├ 🔧 تعمیر: {'فعال 🔴' if self.config.get('maintenance', {}).get('enabled') else 'غیرفعال 🟢'}
└ 🤖 ربات: فعال 🟢
        """
        
        self.bot.send_message(user_id, panel_text, reply_markup=self.kb_admin())
    
    def handle_admin_command(self, user_id, text):
        """مدیریت دستورات ادمین"""
        if str(user_id) not in self.admins:
            return
        
        if text == "📈 آمار کامل":
            self.show_full_stats(user_id)
        
        elif text == "⚠️ هشدار تعمیر":
            self.start_maintenance_warning(user_id)
        
        elif text == "🛠 تعمیر و نگهداری":
            self.toggle_maintenance(user_id)
        
        elif text == "🎖 گیفت VIP تکی":
            self.gift_vip_single(user_id)
        
        elif text == "🎖 گیفت VIP همگانی":
            self.gift_vip_bulk(user_id)
        
        elif text == "❌ حذف VIP":
            self.remove_vip(user_id)
        
        elif text == "📋 لیست VIP":
            self.list_vip_users(user_id)
        
        elif text == "💰 اهدای سکه":
            self.gift_coins(user_id)
        
        elif text == "🎯 مدیریت ماموریت‌ها":
            self.manage_missions(user_id)
        
        elif text == "📁 دانلود دیتابیس":
            self.send_database(user_id)
        
        elif text == "🚫 لیست بن‌شده‌ها":
            self.list_banned_users(user_id)
        
        elif text == "🔙 بازگشت به منو":
            self.bot.send_message(user_id, "بازگشت به منوی اصلی", reply_markup=self.kb_main(user_id))
        
        elif text == "📝 مدیریت کلمات ممنوعه":
            self.manage_badwords(user_id)
        
        elif text == "💰 تنظیم قیمت‌های VIP":
            self.manage_vip_prices(user_id)
        
        elif text == "⚙️ تنظیمات پیشرفته":
            self.manage_settings(user_id)
        
        elif text == "📊 گزارش‌های کاربران":
            self.show_reports(user_id)
        
        else:
            self.bot.send_message(user_id, "⚠️ دستور ادمین نامعتبر!")
    
    def show_full_stats(self, user_id):
        """نمایش آمار کامل"""
        stats = self.db.read("stats")
        users = self.db.read("users")
        
        # محاسبه آمار پیشرفته
        total_coins = sum(u.get("coins", 0) for u in users.get("users", {}).values())
        avg_coins = total_coins // max(len(users.get("users", {})), 1)
        
        # توزیع سنی
        age_groups = {"12-18": 0, "19-25": 0, "26-35": 0, "36+": 0}
        for user in users.get("users", {}).values():
            age = user.get("age", 0)
            if 12 <= age <= 18:
                age_groups["12-18"] += 1
            elif 19 <= age <= 25:
                age_groups["19-25"] += 1
            elif 26 <= age <= 35:
                age_groups["26-35"] += 1
            elif age > 35:
                age_groups["36+"] += 1
        
        stats_text = f"""
📊 <b>آمار کامل ربات</b>

👥 <b>کاربران:</b>
├ کل: {stats.get('total_users', 0):,}
├ فعال امروز: {stats.get('active_today', 0):,}
└ VIP: {stats.get('vip_users', 0):,}

💰 <b>اقتصاد:</b>
├ کل سکه‌ها: {total_coins:,}
└ میانگین سکه: {avg_coins:,}

📈 <b>توزیع سنی:</b>
├ 12-18 سال: {age_groups['12-18']:,}
├ 19-25 سال: {age_groups['19-25']:,}
├ 26-35 سال: {age_groups['26-35']:,}
└ 36+ سال: {age_groups['36+']:,}

📅 <b>آخرین بروزرسانی:</b>
└ {datetime.datetime.now().strftime('%Y/%m/%d %H:%M')}
        """
        
        self.bot.send_message(user_id, stats_text)
    
    def start_maintenance_warning(self, user_id):
        """شروع هشدار تعمیر"""
        self.bot.send_message(
            user_id,
            "⚠️ <b>هشدار تعمیر</b>\n\n"
            "با فعال کردن این گزینه، به همه کاربران اعلام می‌شود که ربات 3 دقیقه دیگر به حالت تعمیر می‌رود.\n\n"
            "آیا مطمئن هستید؟",
            reply_markup=self.kb_confirm_maintenance()
        )
    
    def kb_confirm_maintenance(self):
        """کیبورد تایید تعمیر"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ بله، شروع کن", callback_data="maintenance_start"),
            types.InlineKeyboardButton("❌ خیر، لغو", callback_data="maintenance_cancel")
        )
        return markup
    
    def toggle_maintenance(self, user_id):
        """تغییر حالت تعمیر"""
        config = self.db.read("config")
        maintenance = config.get("maintenance", {})
        current = maintenance.get("enabled", False)
        
        maintenance["enabled"] = not current
        config["maintenance"] = maintenance
        self.db.write("config", config)
        
        status = "فعال 🔴" if not current else "غیرفعال 🟢"
        self.bot.send_message(user_id, f"✅ حالت تعمیر {status} شد")
    
    def gift_vip_single(self, user_id):
        """گیفت VIP تکی"""
        self.bot.send_message(
            user_id,
            "🎁 <b>گیفت VIP تکی</b>\n\n"
            "لطفاً آیدی کاربر و مدت VIP را ارسال کنید:\n\n"
            "فرمت: آیدی مدت\n"
            "مثال: 123456789 week\n\n"
            "مدت‌های موجود: week, month, 3month, 6month, year, christmas",
            reply_markup=types.ForceReply()
        )
        # ذخیره وضعیت برای دریافت پاسخ
        users = self.db.read("users")
        users["users"][user_id]["admin_state"] = "gift_vip_single"
        self.db.write("users", users)
    
    def gift_vip_bulk(self, user_id):
        """گیفت VIP همگانی"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("1 هفته", callback_data="bulk_vip_week"),
            types.InlineKeyboardButton("1 ماه", callback_data="bulk_vip_month"),
            types.InlineKeyboardButton("3 ماه", callback_data="bulk_vip_3month"),
            types.InlineKeyboardButton("6 ماه", callback_data="bulk_vip_6month"),
            types.InlineKeyboardButton("1 سال", callback_data="bulk_vip_year")
        )
        
        self.bot.send_message(
            user_id,
            "🎁 <b>گیفت VIP همگانی</b>\n\n"
            "این عمل به همه کاربران VIP اعطا می‌کند.\n"
            "لطفاً مدت را انتخاب کنید:",
            reply_markup=markup
        )
    
    def remove_vip(self, user_id):
        """حذف VIP"""
        self.bot.send_message(
            user_id,
            "❌ <b>حذف VIP</b>\n\n"
            "لطفاً آیدی کاربر را ارسال کنید:",
            reply_markup=types.ForceReply()
        )
        users = self.db.read("users")
        users["users"][user_id]["admin_state"] = "remove_vip"
        self.db.write("users", users)
    
    def list_vip_users(self, user_id):
        """لیست کاربران VIP"""
        users_db = self.db.read("users")
        vip_users = []
        
        for uid, user in users_db.get("users", {}).items():
            if self.is_vip(vip_end=user.get("vip_end", 0)):
                name = user.get("name", "نامشخص")
                vip_end = user.get("vip_end", 0)
                remaining = int((vip_end - time.time()) / (24 * 3600))
                vip_users.append((uid, name, remaining))
        
        if not vip_users:
            self.bot.send_message(user_id, "📭 هیچ کاربر VIP‌ای وجود ندارد")
            return
        
        # تقسیم به بخش‌های کوچکتر
        chunk_size = 20
        for i in range(0, len(vip_users), chunk_size):
            chunk = vip_users[i:i + chunk_size]
            text = f"👑 <b>لیست کاربران VIP ({i+1}-{i+len(chunk)} از {len(vip_users)})</b>\n\n"
            
            for uid, name, remaining in chunk:
                text += f"👤 {name}\n🆔: <code>{uid}</code>\n⏳ باقی‌مانده: {remaining} روز\n\n"
            
            self.bot.send_message(user_id, text)
    
    def gift_coins(self, user_id):
        """اهدای سکه"""
        self.bot.send_message(
            user_id,
            "💰 <b>اهدای سکه</b>\n\n"
            "لطفاً آیدی کاربر و مقدار سکه را ارسال کنید:\n\n"
            "فرمت: آیدی مقدار\n"
            "مثال: 123456789 1000",
            reply_markup=types.ForceReply()
        )
        users = self.db.read("users")
        users["users"][user_id]["admin_state"] = "gift_coins"
        self.db.write("users", users)
    
    def manage_missions(self, user_id):
        """مدیریت ماموریت‌ها"""
        missions = self.db.read("missions")
        daily = missions.get("daily", {})
        
        text = f"""
🎯 <b>مدیریت ماموریت‌ها</b>

📅 <b>ماموریت روزانه:</b>
├ نام: {daily.get('name', 'نامشخص')}
├ نوع: {daily.get('type', 'نامشخص')}
├ هدف: {daily.get('target', 0)}
└ پاداش: {daily.get('reward', {}).get('amount', 0)} {daily.get('reward', {}).get('type', '')}

📋 <b>ماموریت‌های موجود: {len(missions.get('available', []))}</b>
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🔄 تغییر ماموریت روزانه", callback_data="change_daily_mission"),
            types.InlineKeyboardButton("📊 آمار ماموریت‌ها", callback_data="mission_stats")
        )
        
        self.bot.send_message(user_id, text, reply_markup=markup)
    
    def send_database(self, user_id):
        """ارسال دیتابیس"""
        try:
            # ایجاد فایل ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for key, file_path in self.db.files.items():
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            zip_file.writestr(f"{key}.json", f.read())
            
            zip_buffer.seek(0)
            
            # ارسال فایل
            self.bot.send_document(
                user_id,
                zip_buffer,
                caption="📁 <b>دیتابیس ربات</b>\n\n"
                       "فایل ZIP حاوی تمام داده‌های ربات.",
                visible_file_name="shadow_titan_database.zip"
            )
        except Exception as e:
            logger.error(f"خطا در ارسال دیتابیس: {e}")
            self.bot.send_message(user_id, "❌ خطا در ایجاد دیتابیس")
    
    def list_banned_users(self, user_id):
        """لیست کاربران بن شده"""
        bans = self.db.read("bans")
        users_db = self.db.read("users")
        
        text = "🚫 <b>لیست کاربران بن شده</b>\n\n"
        
        if bans.get("permanent"):
            text += "🔴 <b>بن دائم:</b>\n"
            for uid, info in bans["permanent"].items():
                name = users_db["users"].get(uid, {}).get("name", "نامشخص")
                reason = info.get("reason", "نامشخص")
                text += f"├ {name}\n🆔: <code>{uid}</code>\n📌 دلیل: {reason}\n\n"
        
        if bans.get("temporary"):
            text += "🟡 <b>بن موقت:</b>\n"
            for uid, info in bans["temporary"].items():
                name = users_db["users"].get(uid, {}).get("name", "نامشخص")
                reason = info.get("reason", "نامشخص")
                end_time = info.get("end", 0)
                remaining = max(0, int((end_time - time.time()) / 60))
                text += f"├ {name}\n🆔: <code>{uid}</code>\n📌 دلیل: {reason}\n⏳ باقی‌مانده: {remaining} دقیقه\n\n"
        
        if not bans.get("permanent") and not bans.get("temporary"):
            text += "✅ هیچ کاربر بن شده‌ای وجود ندارد"
        
        self.bot.send_message(user_id, text)
    
    def manage_badwords(self, user_id):
        """مدیریت کلمات ممنوعه"""
        badwords = self.db.read("badwords")
        words = badwords.get("words", [])
        
        text = f"""
📝 <b>مدیریت کلمات ممنوعه</b>

🔢 تعداد کلمات: {len(words)}
⚙️ بن خودکار: {'فعال ✅' if badwords.get('auto_ban') else 'غیرفعال ❌'}

📋 <b>لیست کلمات:</b>
        """
        
        # نمایش 20 کلمه اول
        for i, word in enumerate(words[:20]):
            text += f"{i+1}. {word}\n"
        
        if len(words) > 20:
            text += f"\n... و {len(words) - 20} کلمه دیگر"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ افزودن کلمه", callback_data="badwords_add"),
            types.InlineKeyboardButton("➖ حذف کلمه", callback_data="badwords_remove"),
            types.InlineKeyboardButton("🔄 بن خودکار", callback_data="badwords_toggle"),
            types.InlineKeyboardButton("📥 دانلود لیست", callback_data="badwords_download")
        )
        
        self.bot.send_message(user_id, text, reply_markup=markup)
    
    def manage_vip_prices(self, user_id):
        """مدیریت قیمت‌های VIP"""
        vip_prices = self.db.read("vip_prices")
        
        text = "💰 <b>مدیریت قیمت‌های VIP</b>\n\n"
        
        for duration, price in vip_prices.items():
            if duration == "christmas":
                text += f"🎄 3 ماه رایگان: {price} سکه\n"
            else:
                duration_name = {
                    "week": "۱ هفته",
                    "month": "۱ ماه",
                    "3month": "۳ ماه",
                    "6month": "۶ ماه",
                    "year": "۱ سال"
                }.get(duration, duration)
                text += f"{duration_name}: {price:,} سکه\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر قیمت‌ها", callback_data="vip_prices_edit")
        )
        
        self.bot.send_message(user_id, text, reply_markup=markup)
    
    def manage_settings(self, user_id):
        """مدیریت تنظیمات"""
        settings = self.db.read("settings")
        
        text = """
⚙️ <b>تنظیمات پیشرفته</b>

🔐 <b>امنیت:</b>
├ فیلتر AI: {ai_filter}
├ بن خودکار: {auto_ban}
├ نیاز به کانال: {require_channel}
└ حداکثر اخطار: {max_warnings}

🎮 <b>امکانات:</b>
├ چت ناشناس: {anonymous_chat}
├ گردونه شانس: {wheel}
├ ماموریت روزانه: {daily_missions}
├ سیستم دعوت: {referral}
└ سیستم VIP: {vip}

📏 <b>محدودیت‌ها:</b>
├ طول پیام: {message_length}
├ پیام روزانه: {daily_messages}
├ مدت چت: {chat_duration} ثانیه
└ زمان انتظار: {queue_timeout} ثانیه
        """.format(
            ai_filter='فعال ✅' if settings.get('security', {}).get('ai_filter') else 'غیرفعال ❌',
            auto_ban='فعال ✅' if settings.get('security', {}).get('auto_ban') else 'غیرفعال ❌',
            require_channel='فعال ✅' if settings.get('security', {}).get('require_channel') else 'غیرفعال ❌',
            max_warnings=settings.get('security', {}).get('max_warnings', 3),
            anonymous_chat='فعال ✅' if settings.get('features', {}).get('anonymous_chat') else 'غیرفعال ❌',
            wheel='فعال ✅' if settings.get('features', {}).get('wheel') else 'غیرفعال ❌',
            daily_missions='فعال ✅' if settings.get('features', {}).get('daily_missions') else 'غیرفعال ❌',
            referral='فعال ✅' if settings.get('features', {}).get('referral') else 'غیرفعال ❌',
            vip='فعال ✅' if settings.get('features', {}).get('vip') else 'غیرفعال ❌',
            message_length=settings.get('limits', {}).get('message_length', 1000),
            daily_messages=settings.get('limits', {}).get('daily_messages', 100),
            chat_duration=settings.get('limits', {}).get('chat_duration', 7200),
            queue_timeout=settings.get('limits', {}).get('queue_timeout', 300)
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("⚙️ تغییر تنظیمات", callback_data="settings_edit")
        )
        
        self.bot.send_message(user_id, text, reply_markup=markup)
    
    def show_reports(self, user_id):
        """نمایش گزارش‌ها"""
        reports = self.db.read("reports")
        pending = reports.get("pending", [])
        
        text = f"""
📊 <b>گزارش‌های کاربران</b>

⏳ <b>در انتظار بررسی: {len(pending)}</b>
✅ <b>حل شده: {len(reports.get('resolved', []))}</b>

📋 <b>آخرین گزارش‌ها:</b>
        """
        
        for i, report in enumerate(pending[:5]):
            text += f"\n{i+1}. کاربر {report.get('user_id', 'نامشخص')}\n"
            text += f"   نوع: {report.get('type', 'نامشخص')}\n"
            text += f"   زمان: {report.get('time', 'نامشخص')}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📋 گزارش کامل", callback_data="reports_full"),
            types.InlineKeyboardButton("🗑 پاکسازی گزارش‌ها", callback_data="reports_clear")
        )
        
        self.bot.send_message(user_id, text, reply_markup=markup)
    
    def run(self):
        """اجرای ربات"""
        logger.info("🚀 ربات در حال اجراست...")
        try:
            self.bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"خطا در اجرای ربات: {e}")
            raise

# ==========================================
# اجرای ربات
# ==========================================
if __name__ == "__main__":
    try:
        bot = ShadowTitanBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("ربات متوقف شد")
    except Exception as e:
        logger.error(f"خطای غیرمنتظره: {e}", exc_info=True) I
