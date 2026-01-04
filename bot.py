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
            "logs": "db_logs.json",
            "tickets": "db_tickets.json",
            "transactions": "db_transactions.json",
            "settings": "db_settings.json"
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
            "logs": {"admin": [], "system": [], "errors": []},
            "tickets": {"open": {}, "closed": {}},
            "transactions": {},
            "settings": {
                "vip_prices": {
                    "week": 500,
                    "month": 1800,
                    "3month": 5000,
                    "6month": 9000,
                    "year": 15000
                },
                "ai_sensitivity": {"toxic": 0.8, "nsfw": 0.8},
                "filters": {
                    "bad_words": [
                        "کیر", "کیرم", "کیرت", "کیری", "کس", "کص", "کوس", "کوث",
                        "جنده", "جهنده", "مادرجنده", "قحبه", "قهبه",
                        "پدرسگ", "پدرسوخته", "حرامزاده", "گاییدم", "گاییدن",
                        "سیکتیر", "کون", "کونی", "گوه", "لاشی", "فاحشه",
                        "ناموس", "اوبی", "بی‌ناموس", "سکس", "پورن",
                        "خارکصه", "تخمم", "شاسگول", "پفیوز", "دیوث"
                    ]
                },
                "limits": {
                    "max_warnings": 3,
                    "temp_ban_duration": 1440,
                    "daily_messages": 100
                },
                "referral": {
                    "reward": 100,
                    "levels": 2,
                    "level2_reward": 20
                }
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

    def log_admin_action(self, admin_id, action, target=None, details=None):
        """ثبت لاگ اقدامات ادمین"""
        db_l = self.read("logs")
        log_entry = {
            "admin": admin_id,
            "action": action,
            "target": target,
            "details": details,
            "timestamp": datetime.datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M:%S")
        }
        db_l["admin"].append(log_entry)
        self.write("logs", db_l)

# ==========================================
# ربات اصلی
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        self.token = "8213706320:AAEXMsOv6lP-lvgyvaeGawJltv5zxM3bA6A"
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

        # بارگیری تنظیمات از دیتابیس
        self.load_settings()
        
        # متغیرهای هشدار تعمیر
        self.maintenance_warning_active = False
        self.maintenance_warning_event = None
        self.maintenance_warning_thread = None
        
        # بازیابی چت‌های فعال
        self.restore_active_chats()
        
        # بروزرسانی خودکار ماموریت روزانه
        self.auto_update_daily_mission()
        
        self.register_handlers()
        logger.info("Shadow Titan v42.0 شروع شد")

    def load_settings(self):
        """بارگیری تنظیمات از دیتابیس"""
        settings = self.db.read("settings")
        self.vip_prices_coins = settings.get("vip_prices", {
            "week": 500,
            "month": 1800,
            "3month": 5000,
            "6month": 9000,
            "year": 15000,
            "christmas": 0
        })
        self.bad_words = settings.get("filters", {}).get("bad_words", [])
        self.ai_sensitivity = settings.get("ai_sensitivity", {"toxic": 0.8, "nsfw": 0.8})
        self.limits = settings.get("limits", {
            "max_warnings": 3,
            "temp_ban_duration": 1440,
            "daily_messages": 100
        })
        self.referral_settings = settings.get("referral", {
            "reward": 100,
            "levels": 2,
            "level2_reward": 20
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

    def save_settings(self):
        """ذخیره تنظیمات در دیتابیس"""
        settings = {
            "vip_prices": self.vip_prices_coins,
            "filters": {"bad_words": self.bad_words},
            "ai_sensitivity": self.ai_sensitivity,
            "limits": self.limits,
            "referral": self.referral_settings
        }
        self.db.write("settings", settings)

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
        
        # ثبت تراکنش
        self.log_transaction(uid, "add", amount, reason)
        
        try:
            self.bot.send_message(uid, f"💰 <b>دریافت سکه!</b>\n\n"
                                       f"مقدار: {amount:,} سکه\n"
                                       f"دلیل: {reason}\n"
                                       f"موجودی: {db_u['users'][uid]['coins']:,} سکه")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام سکه به {uid}: {e}")
        
        return True

    def deduct_coins(self, uid, amount, reason=""):
        """کسر سکه"""
        db_u = self.db.read("users")
        if uid not in db_u["users"]:
            return False
        
        current_coins = db_u["users"][uid].get("coins", 0)
        if current_coins < amount:
            return False
        
        db_u["users"][uid]["coins"] = current_coins - amount
        self.db.write("users", db_u)
        
        # ثبت تراکنش
        self.log_transaction(uid, "deduct", amount, reason)
        
        return True

    def log_transaction(self, uid, tx_type, amount, reason=""):
        """ثبت تراکنش مالی"""
        db_t = self.db.read("transactions")
        if uid not in db_t:
            db_t[uid] = []
        
        tx_entry = {
            "type": tx_type,
            "amount": amount,
            "reason": reason,
            "timestamp": datetime.datetime.now().timestamp()
        }
        db_t[uid].append(tx_entry)
        self.db.write("transactions", db_t)

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
            
            # ارسال پیام موفقیت
            try:
                self.bot.send_message(uid, f"🎉 <b>ماموریت روزانه تکمیل شد!</b>\n\n"
                                          f"ماموریت: {mission['mission']}\n"
                                          f"پاداش دریافت شد! ✨")
            except:
                pass
            
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

    # کیبوردها
    def kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس", "🎯 ماموریت روزانه")
        markup.add("👥 رفرال و دعوت", "🎖 خرید VIP")
        markup.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if uid == self.owner:
            markup.add("📊 پنل مدیریت پیشرفته")
        return markup

    def kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def kb_admin(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add("📊 آمار کامل", "👥 مدیریت کاربران", "💬 مدیریت چت‌ها")
        markup.add("📈 آمار و تحلیل", "💰 مدیریت مالی", "🚫 مدیریت بن")
        markup.add("⚙️ تنظیمات ربات", "🛠️ ابزارهای توسعه", "📋 گزارشات")
        markup.add("🎯 ماموریت‌ها", "🎫 تیکت‌ها", "🔙 بازگشت به منو")
        return markup

    def kb_admin_users(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📋 لیست کاربران", "🔍 جستجوی کاربر", "✏️ ویرایش کاربر")
        markup.add("📊 آمار کاربران", "📈 تاریخچه فعالیت", "🔙 بازگشت")
        return markup

    def kb_admin_chats(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("💬 چت‌های فعال", "📝 پیام‌های چت", "📋 گزارشات")
        markup.add("🎫 تیکت‌ها", "🚩 گزارشات تخلف", "🔙 بازگشت")
        return markup

    def kb_admin_finance(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("💰 تاریخچه تراکنش‌ها", "💸 کسر سکه", "⚙️ تنظیم قیمت‌ها")
        markup.add("🏷️ کدهای تخفیف", "📊 آمار مالی", "🔙 بازگشت")
        return markup

    def kb_admin_bans(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🚫 لیست بن‌ها", "🎯 بن الگوریتمی", "⏱️ بن موقت")
        markup.add("⚠️ اخطار به کاربر", "🔄 بازیابی حساب", "🔙 بازگشت")
        return markup

    def kb_admin_settings(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✏️ متن‌های ربات", "🚫 کلمات فیلتر", "⚙️ حساسیت AI")
        markup.add("📢 پیام همگانی", "🎛️ قابلیت‌ها", "🔙 بازگشت")
        return markup

    def kb_admin_tools(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🧪 تست ربات", "🐛 دیباگ", "📊 مانیتور منابع")
        markup.add("❌ آمار خطاها", "💾 بکاپ", "🔙 بازگشت")
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
    # توابع جدید برای مدیریت پیشرفته
    # ==========================================

    def get_user_stats(self):
        """گرفتن آمار کامل کاربران"""
        db_u = self.db.read("users")
        stats = {
            "total": len(db_u["users"]),
            "male": 0,
            "female": 0,
            "vip": 0,
            "active_today": 0,
            "new_today": 0,
            "total_coins": 0,
            "avg_age": 0
        }
        
        age_sum = 0
        age_count = 0
        today = str(datetime.date.today())
        
        for user_data in db_u["users"].values():
            if user_data.get("sex") == "آقا":
                stats["male"] += 1
            elif user_data.get("sex") == "خانم":
                stats["female"] += 1
            
            if self.is_vip(user_data.get("id", "")):
                stats["vip"] += 1
            
            if user_data.get("last_active_date") == today:
                stats["active_today"] += 1
            
            if user_data.get("join_date") == today:
                stats["new_today"] += 1
            
            stats["total_coins"] += user_data.get("coins", 0)
            
            if "age" in user_data:
                age_sum += user_data["age"]
                age_count += 1
        
        if age_count > 0:
            stats["avg_age"] = age_sum / age_count
        
        return stats

    def search_users(self, query):
        """جستجوی کاربران"""
        db_u = self.db.read("users")
        results = []
        
        for uid, user_data in db_u["users"].items():
            name = user_data.get("name", "").lower()
            if query.lower() in name or query == uid:
                results.append({
                    "id": uid,
                    "name": user_data.get("name", "نامشخص"),
                    "age": user_data.get("age", "نامشخص"),
                    "sex": user_data.get("sex", "نامشخص"),
                    "coins": user_data.get("coins", 0),
                    "vip": self.is_vip(uid)
                })
        
        return results

    def get_active_chats(self):
        """دریافت چت‌های فعال"""
        db_c = self.db.read("chats")
        db_u = self.db.read("users")
        active_chats = []
        
        for uid, partner in db_c.items():
            user1 = db_u["users"].get(uid, {})
            user2 = db_u["users"].get(partner, {})
            
            active_chats.append({
                "user1": {"id": uid, "name": user1.get("name", "نامشخص")},
                "user2": {"id": partner, "name": user2.get("name", "نامشخص")},
                "start_time": user1.get("chat_start_time", "نامشخص")
            })
        
        return active_chats

    def create_ticket(self, user_id, category, message):
        """ایجاد تیکت پشتیبانی"""
        db_t = self.db.read("tickets")
        ticket_id = f"T{int(datetime.datetime.now().timestamp())}"
        
        ticket = {
            "id": ticket_id,
            "user_id": user_id,
            "category": category,
            "message": message,
            "status": "open",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "responses": []
        }
        
        db_t["open"][ticket_id] = ticket
        self.db.write("tickets", db_t)
        
        return ticket_id

    def reply_ticket(self, ticket_id, responder_id, message):
        """پاسخ به تیکت"""
        db_t = self.db.read("tickets")
        
        if ticket_id in db_t["open"]:
            ticket = db_t["open"][ticket_id]
            response = {
                "responder_id": responder_id,
                "message": message,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            ticket["responses"].append(response)
            self.db.write("tickets", db_t)
            return True
        
        return False

    def close_ticket(self, ticket_id):
        """بستن تیکت"""
        db_t = self.db.read("tickets")
        
        if ticket_id in db_t["open"]:
            ticket = db_t["open"][ticket_id]
            ticket["status"] = "closed"
            ticket["closed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
            db_t["closed"][ticket_id] = ticket
            del db_t["open"][ticket_id]
            
            self.db.write("tickets", db_t)
            return True
        
        return False

    def get_user_transactions(self, user_id):
        """دریافت تاریخچه تراکنش‌های کاربر"""
        db_t = self.db.read("transactions")
        return db_t.get(user_id, [])

    def update_vip_prices(self, new_prices):
        """بروزرسانی قیمت‌های VIP"""
        for key, value in new_prices.items():
            if key in self.vip_prices_coins:
                self.vip_prices_coins[key] = value
        
        self.save_settings()

    def add_filter_word(self, word):
        """اضافه کردن کلمه به فیلتر"""
        if word not in self.bad_words:
            self.bad_words.append(word)
            self.save_settings()
            return True
        return False

    def remove_filter_word(self, word):
        """حذف کلمه از فیلتر"""
        if word in self.bad_words:
            self.bad_words.remove(word)
            self.save_settings()
            return True
        return False

    def update_ai_sensitivity(self, toxic=None, nsfw=None):
        """بروزرسانی حساسیت AI"""
        if toxic is not None:
            self.ai_sensitivity["toxic"] = toxic
        if nsfw is not None:
            self.ai_sensitivity["nsfw"] = nsfw
        
        self.save_settings()

    def send_broadcast(self, message, target="all"):
        """ارسال پیام همگانی"""
        db_u = self.db.read("users")
        sent_count = 0
        
        for uid in db_u["users"]:
            if target == "vip" and not self.is_vip(uid):
                continue
            
            try:
                self.bot.send_message(uid, message)
                sent_count += 1
                time.sleep(0.05)  # جلوگیری از محدودیت تلگرام
            except Exception as e:
                logger.error(f"خطا در ارسال پیام همگانی به {uid}: {e}")
        
        return sent_count

    def get_system_stats(self):
        """دریافت آمار سیستم"""
        import psutil
        import os
        
        stats = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "process_memory": psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,  # MB
            "active_threads": threading.active_count(),
            "db_size": {}
        }
        
        # محاسبه حجم دیتابیس
        for key, path in self.db.files.items():
            if os.path.exists(path):
                stats["db_size"][key] = os.path.getsize(path) / 1024  # KB
        
        return stats

    def backup_database(self):
        """ایجاد بکاپ از دیتابیس"""
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.zip")
        
        import zipfile
        with zipfile.ZipFile(backup_file, 'w') as zipf:
            for key, path in self.db.files.items():
                if os.path.exists(path):
                    zipf.write(path, os.path.basename(path))
        
        return backup_file

    def algorithmic_ban(self):
        """بن الگوریتمی بر اساس رفتار"""
        db_u = self.db.read("users")
        db_b = self.db.read("bans")
        
        for uid, user_data in db_u["users"].items():
            # بررسی الگوهای مشکوک
            warns = user_data.get("warns", 0)
            reports = user_data.get("reports_received", 0)
            chat_count = user_data.get("daily_chat_count", 0)
            
            # اگر کاربر بیش از 10 گزارش دریافت کرده
            if reports >= 10:
                self.ban_perm(uid, "گزارش‌های زیاد از کاربران مختلف")
                self.db.log_admin_action("system", "algorithmic_ban", uid, f"reports={reports}")
            
            # اگر کاربر در یک روز بیش از 500 پیام فرستاده (اسپم)
            elif chat_count > 500:
                self.ban_temp(uid, 720, "ارسال پیام‌های زیاد (اسپم)")
                self.db.log_admin_action("system", "algorithmic_temp_ban", uid, f"chat_count={chat_count}")

    def check_suspicious_activity(self):
        """بررسی فعالیت مشکوک"""
        db_u = self.db.read("users")
        suspicious = []
        
        for uid, user_data in db_u["users"].items():
            # فعالیت در ساعت‌های غیرعادی (3-6 صبح)
            last_active = user_data.get("last_active_time", "")
            if "03:00" <= last_active <= "06:00":
                suspicious.append({
                    "user": uid,
                    "reason": "فعالیت در ساعت غیرعادی",
                    "last_active": last_active
                })
        
        return suspicious

    def get_referral_tree(self, user_id):
        """دریافت درخت دعوت کاربر"""
        db_u = self.db.read("users")
        user = db_u["users"].get(user_id, {})
        referrals = user.get("referral_list", [])
        
        tree = {
            "user": user_id,
            "direct": [],
            "level2": []
        }
        
        for ref_id in referrals:
            tree["direct"].append(ref_id)
            ref_user = db_u["users"].get(ref_id, {})
            ref_referrals = ref_user.get("referral_list", [])
            tree["level2"].extend(ref_referrals)
        
        return tree

    def update_bot_texts(self, text_type, new_text):
        """بروزرسانی متن‌های ربات"""
        # در اینجا می‌توانید متن‌های مختلف ربات را بروزرسانی کنید
        # برای سادگی، فعلاً فقط لاگ می‌کنیم
        logger.info(f"متن {text_type} به {new_text[:50]}... بروزرسانی شد")
        return True

    def toggle_feature(self, feature, enable=True):
        """فعال/غیرفعال کردن قابلیت"""
        features = {
            "chat": "چت ناشناس",
            "anon_messages": "پیام ناشناس",
            "wheel": "گردونه شانس",
            "missions": "ماموریت روزانه",
            "referral": "سیستم رفرال"
        }
        
        if feature in features:
            status = "فعال" if enable else "غیرفعال"
            logger.info(f"قابلیت {features[feature]} {status} شد")
            return True
        
        return False

    def run_diagnostic(self):
        """اجرای تشخیص مشکلات"""
        issues = []
        
        # بررسی اتصال به تلگرام
        try:
            self.bot.get_me()
        except Exception as e:
            issues.append(f"❌ مشکل در اتصال به تلگرام: {str(e)}")
        
        # بررسی فایل‌های دیتابیس
        for key, path in self.db.files.items():
            if not os.path.exists(path):
                issues.append(f"❌ فایل دیتابیس {key} یافت نشد")
        
        # بررسی حافظه
        import psutil
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            issues.append(f"⚠️ مصرف حافظه بالا: {memory.percent}%")
        
        # بررسی تعداد خطاها در لاگ
        if os.path.exists('shadow_titan.log'):
            with open('shadow_titan.log', 'r') as f:
                lines = f.readlines()
                error_count = sum(1 for line in lines if 'ERROR' in line)
                if error_count > 100:
                    issues.append(f"⚠️ تعداد خطاهای زیاد در لاگ: {error_count}")
        
        return issues

    def register_handlers(self):
        # تمام هندلرهای قبلی به همان صورت باقی می‌مانند
        # فقط هندلرهای جدید برای پنل مدیریت اضافه می‌شوند
        
        @self.bot.message_handler(func=lambda msg: msg.text == "📊 پنل مدیریت پیشرفته" and str(msg.chat.id) == self.owner)
        def admin_panel(msg):
            uid = str(msg.chat.id)
            self.bot.send_message(uid, "<b>📊 پنل مدیریت پیشرفته Shadow Titan</b>\n\n"
                                      "لطفاً بخش مورد نظر را انتخاب کنید:", 
                                reply_markup=self.kb_admin())

        @self.bot.message_handler(func=lambda msg: msg.text == "👥 مدیریت کاربران" and str(msg.chat.id) == self.owner)
        def admin_users(msg):
            uid = str(msg.chat.id)
            self.bot.send_message(uid, "<b>👥 مدیریت کاربران</b>\n\n"
                                      "عملیات مورد نظر را انتخاب کنید:", 
                                reply_markup=self.kb_admin_users())

        @self.bot.message_handler(func=lambda msg: msg.text == "📋 لیست کاربران" and str(msg.chat.id) == self.owner)
        def list_users(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("🎖 فقط VIP", callback_data="list_vip"),
                types.InlineKeyboardButton("👦 فقط آقا", callback_data="list_male")
            )
            kb.add(
                types.InlineKeyboardButton("👧 فقط خانم", callback_data="list_female"),
                types.InlineKeyboardButton("📊 همه", callback_data="list_all")
            )
            
            stats = self.get_user_stats()
            stats_text = f"<b>📊 آمار کاربران</b>\n\n"
            stats_text += f"👥 کل کاربران: {stats['total']:,}\n"
            stats_text += f"👦 آقا: {stats['male']:,}\n"
            stats_text += f"👧 خانم: {stats['female']:,}\n"
            stats_text += f"🎖 VIP: {stats['vip']:,}\n"
            stats_text += f"🟢 فعال امروز: {stats['active_today']:,}\n"
            stats_text += f"🆕 جدید امروز: {stats['new_today']:,}\n"
            stats_text += f"💰 کل سکه‌ها: {stats['total_coins']:,}\n"
            stats_text += f"📊 میانگین سن: {stats['avg_age']:.1f}\n\n"
            stats_text += "برای مشاهده لیست فیلترشده کلیک کنید:"
            
            self.bot.send_message(uid, stats_text, reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "🔍 جستجوی کاربر" and str(msg.chat.id) == self.owner)
        def search_user(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_u["users"][uid]["admin_state"] = "search_user"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "🔍 آیدی یا نام کاربر را وارد کنید:")

        @self.bot.message_handler(func=lambda msg: msg.text == "💬 مدیریت چت‌ها" and str(msg.chat.id) == self.owner)
        def admin_chats(msg):
            uid = str(msg.chat.id)
            self.bot.send_message(uid, "<b>💬 مدیریت چت‌ها و گزارشات</b>\n\n"
                                      "عملیات مورد نظر را انتخاب کنید:", 
                                reply_markup=self.kb_admin_chats())

        @self.bot.message_handler(func=lambda msg: msg.text == "💬 چت‌های فعال" and str(msg.chat.id) == self.owner)
        def active_chats_list(msg):
            uid = str(msg.chat.id)
            active_chats = self.get_active_chats()
            
            if not active_chats:
                self.bot.send_message(uid, "❌ هیچ چت فعالی وجود ندارد.")
                return
            
            text = "<b>💬 چت‌های فعال</b>\n\n"
            for i, chat in enumerate(active_chats[:20], 1):
                text += f"{i}. {chat['user1']['name']} ↔️ {chat['user2']['name']}\n"
                text += f"   🆔: {chat['user1']['id']} ↔️ {chat['user2']['id']}\n"
                text += f"   ⏰ شروع: {chat.get('start_time', 'نامشخص')}\n\n"
            
            if len(active_chats) > 20:
                text += f"\n... و {len(active_chats) - 20} چت فعال دیگر"
            
            self.bot.send_message(uid, text)

        @self.bot.message_handler(func=lambda msg: msg.text == "📈 آمار و تحلیل" and str(msg.chat.id) == self.owner)
        def admin_analytics(msg):
            uid = str(msg.chat.id)
            
            # آمار 7 روز اخیر
            import matplotlib.pyplot as plt
            import io
            
            days = []
            new_users = []
            active_users = []
            
            for i in range(7):
                day = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                days.append(day)
                
                # محاسبه کاربران جدید و فعال برای هر روز
                db_u = self.db.read("users")
                new = sum(1 for u in db_u["users"].values() if u.get("join_date") == day)
                active = sum(1 for u in db_u["users"].values() if u.get("last_active_date") == day)
                
                new_users.append(new)
                active_users.append(active)
            
            # ایجاد نمودار
            plt.figure(figsize=(10, 5))
            plt.plot(days[::-1], new_users[::-1], label='کاربران جدید', marker='o')
            plt.plot(days[::-1], active_users[::-1], label='کاربران فعال', marker='s')
            plt.xlabel('تاریخ')
            plt.ylabel('تعداد')
            plt.title('رشد کاربران در 7 روز اخیر')
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # ذخیره نمودار در بافر
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            # ارسال نمودار
            stats_text = "<b>📈 آمار و تحلیل پیشرفته</b>\n\n"
            stats_text += f"📊 کاربران جدید امروز: {new_users[0]}\n"
            stats_text += f"🟢 کاربران فعال امروز: {active_users[0]}\n"
            stats_text += f"📈 میانگین رشد روزانه: {sum(new_users)/7:.1f}\n\n"
            stats_text += "نمودار رشد 7 روز اخیر:"
            
            self.bot.send_photo(uid, buf, caption=stats_text)

        @self.bot.message_handler(func=lambda msg: msg.text == "💰 مدیریت مالی" and str(msg.chat.id) == self.owner)
        def admin_finance(msg):
            uid = str(msg.chat.id)
            self.bot.send_message(uid, "<b>💰 مدیریت مالی و سکه‌ها</b>\n\n"
                                      "عملیات مورد نظر را انتخاب کنید:", 
                                reply_markup=self.kb_admin_finance())

        @self.bot.message_handler(func=lambda msg: msg.text == "🚫 مدیریت بن" and str(msg.chat.id) == self.owner)
        def admin_bans(msg):
            uid = str(msg.chat.id)
            self.bot.send_message(uid, "<b>🚫 سیستم مدیریت بن پیشرفته</b>\n\n"
                                      "عملیات مورد نظر را انتخاب کنید:", 
                                reply_markup=self.kb_admin_bans())

        @self.bot.message_handler(func=lambda msg: msg.text == "⚙️ تنظیمات ربات" and str(msg.chat.id) == self.owner)
        def admin_settings(msg):
            uid = str(msg.chat.id)
            self.bot.send_message(uid, "<b>⚙️ تنظیمات پیشرفته ربات</b>\n\n"
                                      "عملیات مورد نظر را انتخاب کنید:", 
                                reply_markup=self.kb_admin_settings())

        @self.bot.message_handler(func=lambda msg: msg.text == "🛠️ ابزارهای توسعه" and str(msg.chat.id) == self.owner)
        def admin_tools(msg):
            uid = str(msg.chat.id)
            self.bot.send_message(uid, "<b>🛠️ ابزارهای توسعه و دیباگ</b>\n\n"
                                      "عملیات مورد نظر را انتخاب کنید:", 
                                reply_markup=self.kb_admin_tools())

        @self.bot.message_handler(func=lambda msg: msg.text == "📋 گزارشات" and str(msg.chat.id) == self.owner)
        def admin_reports(msg):
            uid = str(msg.chat.id)
            
            # خواندن لاگ‌ها
            db_l = self.db.read("logs")
            admin_logs = db_l.get("admin", [])
            system_logs = db_l.get("system", [])
            error_logs = db_l.get("errors", [])
            
            text = "<b>📋 گزارشات و لاگ سیستم</b>\n\n"
            text += f"📝 اقدامات ادمین: {len(admin_logs)} مورد\n"
            text += f"🤖 لاگ سیستم: {len(system_logs)} مورد\n"
            text += f"❌ خطاها: {len(error_logs)} مورد\n\n"
            
            # آخرین 5 اقدام ادمین
            text += "<b>آخرین اقدامات ادمین:</b>\n"
            for log in admin_logs[-5:]:
                text += f"• {log.get('action', 'نامشخص')} - {log.get('timestamp', 'نامشخص')}\n"
            
            # آمار سیستم
            system_stats = self.get_system_stats()
            text += f"\n<b>آمار سیستم:</b>\n"
            text += f"💾 CPU: {system_stats['cpu_percent']}%\n"
            text += f"🧠 حافظه: {system_stats['memory_percent']}%\n"
            text += f"💿 دیسک: {system_stats['disk_percent']}%\n"
            text += f"📊 حافظه فرآیند: {system_stats['process_memory']:.1f} MB\n"
            
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("📥 دانلود لاگ‌ها", callback_data="download_logs"),
                types.InlineKeyboardButton("🗑️ پاکسازی لاگ‌ها", callback_data="clear_logs")
            )
            
            self.bot.send_message(uid, text, reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "🎫 تیکت‌ها" and str(msg.chat.id) == self.owner)
        def admin_tickets(msg):
            uid = str(msg.chat.id)
            db_t = self.db.read("tickets")
            
            open_tickets = db_t.get("open", {})
            closed_tickets = db_t.get("closed", {})
            
            text = "<b>🎫 سیستم تیکت پشتیبانی</b>\n\n"
            text += f"📨 تیکت‌های باز: {len(open_tickets)}\n"
            text += f"✅ تیکت‌های بسته: {len(closed_tickets)}\n\n"
            
            if open_tickets:
                text += "<b>تیکت‌های باز:</b>\n"
                for ticket_id, ticket in list(open_tickets.items())[:5]:
                    text += f"• #{ticket_id} - {ticket.get('category', 'عمومی')}\n"
                    text += f"  👤 کاربر: {ticket.get('user_id', 'نامشخص')}\n"
                    text += f"  ⏰ زمان: {ticket.get('created_at', 'نامشخص')}\n\n"
            
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("📋 مشاهده تیکت‌ها", callback_data="view_tickets"),
                types.InlineKeyboardButton("📊 آمار تیکت‌ها", callback_data="ticket_stats")
            )
            
            self.bot.send_message(uid, text, reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "💾 بکاپ" and str(msg.chat.id) == self.owner)
        def backup_db(msg):
            uid = str(msg.chat.id)
            
            try:
                backup_file = self.backup_database()
                file_size = os.path.getsize(backup_file) / 1024  # KB
                
                with open(backup_file, 'rb') as f:
                    self.bot.send_document(uid, f, caption=f"✅ <b>بکاپ موفقیت‌آمیز بود</b>\n\n"
                                                        f"📁 فایل: {os.path.basename(backup_file)}\n"
                                                        f"📊 حجم: {file_size:.1f} KB\n"
                                                        f"⏰ زمان: {datetime.datetime.now().strftime('%H:%M')}")
            except Exception as e:
                self.bot.send_message(uid, f"❌ خطا در ایجاد بکاپ: {str(e)}")

        @self.bot.message_handler(func=lambda msg: msg.text == "🧪 تست ربات" and str(msg.chat.id) == self.owner)
        def test_bot(msg):
            uid = str(msg.chat.id)
            
            issues = self.run_diagnostic()
            
            if not issues:
                self.bot.send_message(uid, "✅ <b>همه چیز خوب است!</b>\n\n"
                                          "هیچ مشکلی در سیستم تشخیص داده نشد.")
            else:
                text = "⚠️ <b>مشکلات تشخیص داده شده:</b>\n\n"
                for i, issue in enumerate(issues, 1):
                    text += f"{i}. {issue}\n"
                
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("🔧 رفع مشکلات", callback_data="fix_issues"),
                    types.InlineKeyboardButton("📊 گزارش کامل", callback_data="full_report")
                )
                
                self.bot.send_message(uid, text, reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "📊 مانیتور منابع" and str(msg.chat.id) == self.owner)
        def monitor_resources(msg):
            uid = str(msg.chat.id)
            
            stats = self.get_system_stats()
            
            text = "<b>📊 مانیتور منابع سیستم</b>\n\n"
            text += f"💾 مصرف CPU: {stats['cpu_percent']}%\n"
            text += f"🧠 مصرف حافظه: {stats['memory_percent']}%\n"
            text += f"💿 مصرف دیسک: {stats['disk_percent']}%\n"
            text += f"📊 حافظه فرآیند: {stats['process_memory']:.1f} MB\n"
            text += f"🧵 تردهای فعال: {stats['active_threads']}\n\n"
            
            text += "<b>حجم دیتابیس‌ها:</b>\n"
            for db_name, size in stats['db_size'].items():
                text += f"• {db_name}: {size:.1f} KB\n"
            
            # ایجاد نمودار مصرف منابع
            import matplotlib.pyplot as plt
            import io
            
            labels = ['CPU', 'Memory', 'Disk']
            values = [stats['cpu_percent'], stats['memory_percent'], stats['disk_percent']]
            
            plt.figure(figsize=(8, 4))
            bars = plt.bar(labels, values, color=['#FF6B6B', '#4ECDC4', '#45B7D1'])
            plt.ylim(0, 100)
            plt.ylabel('درصد مصرف')
            plt.title('مصرف منابع سیستم')
            
            # اضافه کردن مقادیر روی نمودار
            for bar, value in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                        f'{value}%', ha='center', va='bottom')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            self.bot.send_photo(uid, buf, caption=text)

        @self.bot.message_handler(func=lambda msg: msg.text == "❌ آمار خطاها" and str(msg.chat.id) == self.owner)
        def error_stats(msg):
            uid = str(msg.chat.id)
            
            if os.path.exists('shadow_titan.log'):
                with open('shadow_titan.log', 'r') as f:
                    lines = f.readlines()
                
                error_lines = [line for line in lines if 'ERROR' in line]
                warning_lines = [line for line in lines if 'WARNING' in line]
                
                text = "<b>❌ آمار خطاها و اخطارها</b>\n\n"
                text += f"📊 کل خطوط لاگ: {len(lines):,}\n"
                text += f"❌ خطاها: {len(error_lines):,}\n"
                text += f"⚠️ اخطارها: {len(warning_lines):,}\n\n"
                
                if error_lines:
                    text += "<b>آخرین خطاها:</b>\n"
                    for line in error_lines[-3:]:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            text += f"• {parts[2].strip()}\n"
                
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("📋 مشاهده لاگ", callback_data="view_log"),
                    types.InlineKeyboardButton("🗑️ پاکسازی لاگ", callback_data="clear_log")
                )
                
                self.bot.send_message(uid, text, reply_markup=kb)
            else:
                self.bot.send_message(uid, "❌ فایل لاگ یافت نشد.")

        @self.bot.message_handler(func=lambda msg: msg.text == "🎯 بن الگوریتمی" and str(msg.chat.id) == self.owner)
        def algorithmic_ban_command(msg):
            uid = str(msg.chat.id)
            
            self.bot.send_message(uid, "🔍 در حال بررسی کاربران برای بن الگوریتمی...")
            self.algorithmic_ban()
            
            self.bot.send_message(uid, "✅ بررسی الگوریتمی انجام شد. کاربران متخلف بن شدند.")

        @self.bot.message_handler(func=lambda msg: msg.text == "⚠️ اخطار به کاربر" and str(msg.chat.id) == self.owner)
        def warn_user_admin(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_u["users"][uid]["admin_state"] = "warn_user"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "🆔 آیدی کاربر برای اخطار را وارد کنید:")

        @self.bot.message_handler(func=lambda msg: msg.text == "🔄 بازیابی حساب" and str(msg.chat.id) == self.owner)
        def recover_account(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_u["users"][uid]["admin_state"] = "recover_account"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "🆔 آیدی کاربر برای بازیابی حساب را وارد کنید:")

        @self.bot.message_handler(func=lambda msg: msg.text == "✏️ متن‌های ربات" and str(msg.chat.id) == self.owner)
        def edit_bot_texts(msg):
            uid = str(msg.chat.id)
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("🛰 متن شروع چت", callback_data="edit_start_chat"),
                types.InlineKeyboardButton("👤 متن پروفایل", callback_data="edit_profile")
            )
            kb.add(
                types.InlineKeyboardButton("🎯 متن ماموریت", callback_data="edit_mission"),
                types.InlineKeyboardButton("📖 متن راهنما", callback_data="edit_help")
            )
            kb.add(
                types.InlineKeyboardButton("⚠️ متن اخطار", callback_data="edit_warning"),
                types.InlineKeyboardButton("🚫 متن بن", callback_data="edit_ban")
            )
            
            self.bot.send_message(uid, "<b>✏️ ویرایش متن‌های ربات</b>\n\n"
                                      "متن مورد نظر برای ویرایش را انتخاب کنید:", 
                                reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "🚫 کلمات فیلتر" and str(msg.chat.id) == self.owner)
        def manage_filter_words(msg):
            uid = str(msg.chat.id)
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("➕ اضافه کردن کلمه", callback_data="add_filter_word"),
                types.InlineKeyboardButton("➖ حذف کلمه", callback_data="remove_filter_word")
            )
            kb.add(
                types.InlineKeyboardButton("📋 لیست کلمات", callback_data="list_filter_words"),
                types.InlineKeyboardButton("🔄 بازنشانی لیست", callback_data="reset_filter_words")
            )
            
            self.bot.send_message(uid, f"<b>🚫 مدیریت کلمات فیلتر</b>\n\n"
                                      f"تعداد کلمات فعلی: {len(self.bad_words)}\n\n"
                                      f"عملیات مورد نظر را انتخاب کنید:", 
                                reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "⚙️ حساسیت AI" and str(msg.chat.id) == self.owner)
        def ai_sensitivity_settings(msg):
            uid = str(msg.chat.id)
            
            text = "<b>⚙️ تنظیمات حساسیت AI</b>\n\n"
            text += f"🎯 حساسیت فعلی:\n"
            text += f"• محتوای سمی: {self.ai_sensitivity['toxic']}\n"
            text += f"• محتوای +18: {self.ai_sensitivity['nsfw']}\n\n"
            text += "مقدار پیشنهادی: 0.7-0.9\n"
            text += "مقدار کمتر = حساسیت کمتر\n"
            text += "مقدار بیشتر = حساسیت بیشتر"
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("➕ افزایش حساسیت", callback_data="increase_sensitivity"),
                types.InlineKeyboardButton("➖ کاهش حساسیت", callback_data="decrease_sensitivity")
            )
            kb.add(
                types.InlineKeyboardButton("🔙 مقدار پیش‌فرض", callback_data="reset_sensitivity"),
                types.InlineKeyboardButton("🧪 تست AI", callback_data="test_ai")
            )
            
            self.bot.send_message(uid, text, reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "📢 پیام همگانی" and str(msg.chat.id) == self.owner)
        def broadcast_message(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_u["users"][uid]["admin_state"] = "broadcast_message"
            self.db.write("users", db_u)
            
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            kb.add("👥 همه کاربران", "🎖 فقط VIP", "🔙 بازگشت")
            
            self.bot.send_message(uid, "<b>📢 ارسال پیام همگانی</b>\n\n"
                                      "ابتدا مخاطبان را انتخاب کنید:", 
                                reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "🎛️ قابلیت‌ها" and str(msg.chat.id) == self.owner)
        def manage_features(msg):
            uid = str(msg.chat.id)
            
            text = "<b>🎛️ مدیریت قابلیت‌های ربات</b>\n\n"
            text += "قابلیت‌های قابل فعال/غیرفعال کردن:\n\n"
            text += "🛰 چت ناشناس\n"
            text += "📩 پیام ناشناس\n"
            text += "🎡 گردونه شانس\n"
            text += "🎯 ماموریت روزانه\n"
            text += "👥 سیستم رفرال\n"
            text += "🎖 فروشگاه VIP\n"
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("✅ فعال کردن", callback_data="enable_features"),
                types.InlineKeyboardButton("❌ غیرفعال کردن", callback_data="disable_features")
            )
            
            self.bot.send_message(uid, text, reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "💰 تاریخچه تراکنش‌ها" and str(msg.chat.id) == self.owner)
        def transaction_history(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_u["users"][uid]["admin_state"] = "view_transactions"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "🆔 آیدی کاربر برای مشاهده تاریخچه تراکنش‌ها را وارد کنید:")

        @self.bot.message_handler(func=lambda msg: msg.text == "💸 کسر سکه" and str(msg.chat.id) == self.owner)
        def deduct_coins_admin(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_u["users"][uid]["admin_state"] = "deduct_coins_amount"
            self.db.write("users", db_u)
            self.bot.send_message(uid, "💰 مقدار سکه برای کسر را وارد کنید:")

        @self.bot.message_handler(func=lambda msg: msg.text == "⚙️ تنظیم قیمت‌ها" and str(msg.chat.id) == self.owner)
        def set_vip_prices(msg):
            uid = str(msg.chat.id)
            
            text = "<b>⚙️ تنظیم قیمت‌های VIP</b>\n\n"
            text += f"قیمت‌های فعلی (سکه):\n"
            for key, price in self.vip_prices_coins.items():
                if key != "christmas":
                    duration_name = {
                        "week": "۱ هفته",
                        "month": "۱ ماه",
                        "3month": "۳ ماه",
                        "6month": "۶ ماه",
                        "year": "۱ سال"
                    }.get(key, key)
                    text += f"• {duration_name}: {price:,}\n"
            
            db_u = self.db.read("users")
            db_u["users"][uid]["admin_state"] = "set_vip_price"
            self.db.write("users", db_u)
            
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            kb.add("۱ هفته", "۱ ماه", "۳ ماه", "۶ ماه", "۱ سال", "🔙 بازگشت")
            
            self.bot.send_message(uid, text + "\nابتدا مدت VIP را انتخاب کنید:", 
                                reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "🏷️ کدهای تخفیف" and str(msg.chat.id) == self.owner)
        def discount_codes(msg):
            uid = str(msg.chat.id)
            
            text = "<b>🏷️ مدیریت کدهای تخفیف</b>\n\n"
            text += "امکانات سیستم کد تخفیف:\n"
            text += "• ایجاد کد تخفیف درصدی\n"
            text += "• ایجاد کد تخفیف مقدار ثابت\n"
            text += "• محدودیت تعداد استفاده\n"
            text += "• تاریخ انقضا\n"
            text += "• تخفیف ویژه VIP\n"
            
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(
                types.InlineKeyboardButton("➕ ایجاد کد جدید", callback_data="create_discount"),
                types.InlineKeyboardButton("📋 لیست کدها", callback_data="list_discounts")
            )
            kb.add(
                types.InlineKeyboardButton("📊 آمار کدها", callback_data="discount_stats"),
                types.InlineKeyboardButton("🗑️ حذف کد", callback_data="delete_discount")
            )
            
            self.bot.send_message(uid, text, reply_markup=kb)

        @self.bot.message_handler(func=lambda msg: msg.text == "📊 آمار مالی" and str(msg.chat.id) == self.owner)
        def financial_stats(msg):
            uid = str(msg.chat.id)
            
            # محاسبه آمار مالی
            db_t = self.db.read("transactions")
            db_u = self.db.read("users")
            
            total_added = 0
            total_deducted = 0
            vip_income = 0
            referral_income = 0  # درآمد از رفرال (در واقع هزینه)
            wheel_cost = 0  # هزینه گردونه
            
            for user_id, transactions in db_t.items():
                for tx in transactions:
                    if tx["type"] == "add":
                        total_added += tx["amount"]
                        if "referral" in tx["reason"].lower():
                            referral_income += tx["amount"]
                    elif tx["type"] == "deduct":
                        total_deducted += tx["amount"]
                        if "vip" in tx["reason"].lower():
                            vip_income += tx["amount"]
                        elif "wheel" in tx["reason"].lower():
                            wheel_cost += tx["amount"]
            
            total_coins = sum(u.get("coins", 0) for u in db_u["users"].values())
            
            text = "<b>📊 آمار مالی جامع</b>\n\n"
            text += f"💰 کل سکه‌های موجود: {total_coins:,}\n"
            text += f"📈 کل سکه‌های توزیع شده: {total_added:,}\n"
            text += f"📉 کل سکه‌های کسر شده: {total_deducted:,}\n"
            text += f"🎖 درآمد از VIP: {vip_income:,}\n"
            text += f"👥 هزینه رفرال: {referral_income:,}\n"
            text += f"🎡 هزینه گردونه: {wheel_cost:,}\n\n"
            
            # نمودار دایره‌ای
            import matplotlib.pyplot as plt
            import io
            
            labels = ['موجودی', 'VIP', 'رفرال', 'گردونه']
            sizes = [total_coins, vip_income, referral_income, wheel_cost]
            colors = ['#4ECDC4', '#FF6B6B', '#45B7D1', '#96CEB4']
            
            plt.figure(figsize=(8, 8))
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title('توزیع سکه‌ها')
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close()
            
            self.bot.send_photo(uid, buf, caption=text)

        # هندلرهای جدید برای stateهای ادمین
        @self.bot.message_handler(func=lambda msg: True)
        def handle_admin_states(msg):
            uid = str(msg.chat.id)
            if uid != self.owner:
                return
            
            db_u = self.db.read("users")
            user = db_u["users"].get(uid, {})
            admin_state = user.get("admin_state")
            
            if not admin_state:
                return
            
            # جستجوی کاربر
            if admin_state == "search_user":
                query = msg.text
                results = self.search_users(query)
                
                if not results:
                    self.bot.send_message(uid, "❌ کاربری یافت نشد.")
                else:
                    text = f"<b>🔍 نتایج جستجو برای '{query}'</b>\n\n"
                    for i, result in enumerate(results[:10], 1):
                        text += f"{i}. {result['name']} (آیدی: {result['id']})\n"
                        text += f"   👤 جنسیت: {result['sex']} | سن: {result['age']}\n"
                        text += f"   💰 سکه: {result['coins']:,} | VIP: {'✅' if result['vip'] else '❌'}\n\n"
                    
                    if len(results) > 10:
                        text += f"\n... و {len(results) - 10} نتیجه دیگر"
                    
                    kb = types.InlineKeyboardMarkup()
                    for i, result in enumerate(results[:5], 1):
                        kb.add(types.InlineKeyboardButton(
                            f"👤 {result['name']} - {result['id']}", 
                            callback_data=f"admin_view_user_{result['id']}"
                        ))
                    
                    self.bot.send_message(uid, text, reply_markup=kb)
                
                user["admin_state"] = None
                self.db.write("users", db_u)
                return
            
            # مشاهده تاریخچه تراکنش‌ها
            elif admin_state == "view_transactions":
                target_id = msg.text
                transactions = self.get_user_transactions(target_id)
                
                if not transactions:
                    self.bot.send_message(uid, f"❌ هیچ تراکنشی برای کاربر {target_id} یافت نشد.")
                else:
                    text = f"<b>💰 تاریخچه تراکنش‌های کاربر {target_id}</b>\n\n"
                    total_added = 0
                    total_deducted = 0
                    
                    for tx in transactions[-20:]:  # آخرین 20 تراکنش
                        amount = tx["amount"]
                        if tx["type"] == "add":
                            total_added += amount
                            text += f"➕ +{amount:,} - {tx['reason']}\n"
                        else:
                            total_deducted += amount
                            text += f"➖ -{amount:,} - {tx['reason']}\n"
                        
                        timestamp = datetime.datetime.fromtimestamp(tx["timestamp"]).strftime("%Y-%m-%d %H:%M")
                        text += f"   ⏰ {timestamp}\n\n"
                    
                    text += f"📊 جمع کل:\n"
                    text += f"➕ افزوده شده: {total_added:,}\n"
                    text += f"➖ کسر شده: {total_deducted:,}\n"
                    text += f"📈 خالص: {total_added - total_deducted:,}"
                    
                    self.bot.send_message(uid, text)
                
                user["admin_state"] = None
                self.db.write("users", db_u)
                return
            
            # کسر سکه - مرحله 1: مقدار
            elif admin_state == "deduct_coins_amount":
                if msg.text.isdigit():
                    amount = int(msg.text)
                    user["deduct_amount"] = amount
                    user["admin_state"] = "deduct_coins_reason"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "📝 دلیل کسر سکه را بنویسید:")
                else:
                    self.bot.send_message(uid, "❌ لطفاً عدد وارد کنید.")
                return
            
            # کسر سکه - مرحله 2: دلیل
            elif admin_state == "deduct_coins_reason":
                reason = msg.text
                user["deduct_reason"] = reason
                user["admin_state"] = "deduct_coins_target"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🆔 آیدی کاربر برای کسر سکه را وارد کنید:")
                return
            
            # کسر سکه - مرحله 3: کاربر هدف
            elif admin_state == "deduct_coins_target":
                target_id = msg.text
                amount = user.get("deduct_amount", 0)
                reason = user.get("deduct_reason", "کسر توسط ادمین")
                
                if self.deduct_coins(target_id, amount, reason):
                    # گرفتن موجودی جدید
                    db_u = self.db.read("users")
                    new_balance = db_u["users"].get(target_id, {}).get("coins", 0)
                    
                    self.bot.send_message(uid, f"✅ {amount:,} سکه از کاربر {target_id} کسر شد.\n"
                                              f"موجودی جدید: {new_balance:,} سکه\n"
                                              f"دلیل: {reason}")
                    
                    # ثبت لاگ ادمین
                    self.db.log_admin_action(uid, "deduct_coins", target_id, 
                                           f"amount={amount}, reason={reason}")
                else:
                    self.bot.send_message(uid, "❌ خطا در کسر سکه. کاربر یافت نشد یا موجودی کافی نیست.")
                
                # پاک کردن stateها
                user["admin_state"] = None
                user.pop("deduct_amount", None)
                user.pop("deduct_reason", None)
                self.db.write("users", db_u)
                return
            
            # تنظیم قیمت VIP - مرحله 1: انتخاب مدت
            elif admin_state == "set_vip_price":
                duration_map = {
                    "۱ هفته": "week",
                    "۱ ماه": "month",
                    "۳ ماه": "3month",
                    "۶ ماه": "6month",
                    "۱ سال": "year"
                }
                
                if msg.text in duration_map:
                    user["set_vip_duration"] = duration_map[msg.text]
                    user["admin_state"] = "set_vip_price_amount"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "💰 قیمت جدید را وارد کنید (سکه):")
                else:
                    self.bot.send_message(uid, "❌ لطفاً از گزینه‌ها استفاده کنید.")
                return
            
            # تنظیم قیمت VIP - مرحله 2: وارد کردن قیمت
            elif admin_state == "set_vip_price_amount":
                if msg.text.isdigit():
                    price = int(msg.text)
                    duration = user.get("set_vip_duration")
                    
                    # بروزرسانی قیمت
                    old_price = self.vip_prices_coins.get(duration, 0)
                    self.vip_prices_coins[duration] = price
                    self.save_settings()
                    
                    duration_name = {
                        "week": "۱ هفته",
                        "month": "۱ ماه",
                        "3month": "۳ ماه",
                        "6month": "۶ ماه",
                        "year": "۱ سال"
                    }.get(duration, duration)
                    
                    self.bot.send_message(uid, f"✅ قیمت VIP {duration_name} بروزرسانی شد:\n"
                                              f"قیمت قبلی: {old_price:,} سکه\n"
                                              f"قیمت جدید: {price:,} سکه")
                    
                    # ثبت لاگ ادمین
                    self.db.log_admin_action(uid, "update_vip_price", duration, 
                                           f"old={old_price}, new={price}")
                else:
                    self.bot.send_message(uid, "❌ لطفاً عدد وارد کنید.")
                
                user["admin_state"] = None
                user.pop("set_vip_duration", None)
                self.db.write("users", db_u)
                return
            
            # ارسال پیام همگانی - مرحله 1: انتخاب مخاطب
            elif admin_state == "broadcast_message":
                target_map = {
                    "👥 همه کاربران": "all",
                    "🎖 فقط VIP": "vip"
                }
                
                if msg.text in target_map:
                    user["broadcast_target"] = target_map[msg.text]
                    user["admin_state"] = "broadcast_message_text"
                    self.db.write("users", db_u)
                    
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("🔙 بازگشت")
                    
                    self.bot.send_message(uid, "📝 متن پیام همگانی را وارد کنید:", 
                                        reply_markup=kb)
                else:
                    self.bot.send_message(uid, "❌ لطفاً از گزینه‌ها استفاده کنید.")
                return
            
            # ارسال پیام همگانی - مرحله 2: متن پیام
            elif admin_state == "broadcast_message_text":
                message = msg.text
                target = user.get("broadcast_target", "all")
                
                # تأیید نهایی
                kb = types.InlineKeyboardMarkup()
                kb.add(
                    types.InlineKeyboardButton("✅ بله، ارسال کن", 
                                             callback_data=f"confirm_broadcast_{target}"),
                    types.InlineKeyboardButton("❌ خیر، لغو کن", 
                                             callback_data="cancel_broadcast")
                )
                
                target_text = "همه کاربران" if target == "all" else "کاربران VIP"
                self.bot.send_message(uid, f"📢 <b>تأیید ارسال پیام همگانی</b>\n\n"
                                          f"مخاطب: {target_text}\n\n"
                                          f"متن پیام:\n{message}\n\n"
                                          f"آیا مطمئن هستید؟", 
                                    reply_markup=kb)
                
                # ذخیره پیام موقت
                user["broadcast_message"] = message
                self.db.write("users", db_u)
                return
            
            # اخطار به کاربر - مرحله 1: آیدی کاربر
            elif admin_state == "warn_user":
                target_id = msg.text
                user["warn_target"] = target_id
                user["admin_state"] = "warn_user_reason"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "📝 دلیل اخطار را بنویسید:")
                return
            
            # اخطار به کاربر - مرحله 2: دلیل
            elif admin_state == "warn_user_reason":
                reason = msg.text
                target_id = user.get("warn_target")
                
                if target_id:
                    db_u = self.db.read("users")
                    if target_id in db_u["users"]:
                        db_u["users"][target_id]["warns"] = db_u["users"][target_id].get("warns", 0) + 1
                        self.db.write("users", db_u)
                        
                        try:
                            self.bot.send_message(target_id, f"⚠️ <b>اخطار از ادمین!</b>\n\n"
                                                           f"دلیل: {reason}\n"
                                                           f"لطفاً قوانین را رعایت کنید.")
                        except:
                            pass
                        
                        self.bot.send_message(uid, f"✅ اخطار به کاربر {target_id} ارسال شد.\n"
                                                  f"تعداد اخطارهای فعلی: {db_u['users'][target_id]['warns']}/3")
                        
                        # ثبت لاگ ادمین
                        self.db.log_admin_action(uid, "warn_user", target_id, f"reason={reason}")
                    else:
                        self.bot.send_message(uid, "❌ کاربر یافت نشد.")
                
                user["admin_state"] = None
                user.pop("warn_target", None)
                self.db.write("users", db_u)
                return
            
            # بازیابی حساب - مرحله 1: آیدی کاربر
            elif admin_state == "recover_account":
                target_id = msg.text
                
                # حذف بن‌ها
                db_b = self.db.read("bans")
                recovered = False
                
                if target_id in db_b["permanent"]:
                    del db_b["permanent"][target_id]
                    recovered = True
                
                if target_id in db_b["temporary"]:
                    del db_b["temporary"][target_id]
                    recovered = True
                
                if recovered:
                    self.db.write("bans", db_b)
                    
                    # بازنشانی اخطارها
                    db_u = self.db.read("users")
                    if target_id in db_u["users"]:
                        db_u["users"][target_id]["warns"] = 0
                        db_u["users"][target_id]["had_temp_ban"] = False
                        self.db.write("users", db_u)
                    
                    try:
                        self.bot.send_message(target_id, "🌟 <b>حساب شما بازیابی شد!</b>\n\n"
                                                       "شما می‌توانید دوباره از ربات استفاده کنید.")
                    except:
                        pass
                    
                    self.bot.send_message(uid, f"✅ حساب کاربر {target_id} با موفقیت بازیابی شد.")
                    
                    # ثبت لاگ ادمین
                    self.db.log_admin_action(uid, "recover_account", target_id, "full_recovery")
                else:
                    self.bot.send_message(uid, f"❌ کاربر {target_id} بن نبوده است.")
                
                user["admin_state"] = None
                self.db.write("users", db_u)
                return

        # کال‌بک‌های جدید برای پنل مدیریت
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            uid = str(call.from_user.id)
            if uid != self.owner:
                return
            
            # لیست کاربران بر اساس فیلتر
            if call.data == "list_vip":
                db_u = self.db.read("users")
                vip_users = [u for u in db_u["users"] if self.is_vip(u)]
                
                text = "<b>🎖 لیست کاربران VIP</b>\n\n"
                for i, user_id in enumerate(vip_users[:20], 1):
                    user = db_u["users"][user_id]
                    text += f"{i}. {user.get('name', 'نامشخص')}\n"
                    text += f"   🆔: {user_id}\n"
                    text += f"   💰 سکه: {user.get('coins', 0):,}\n"
                    text += f"   ⚠️ اخطار: {user.get('warns', 0)}/3\n\n"
                
                if len(vip_users) > 20:
                    text += f"\n... و {len(vip_users) - 20} کاربر VIP دیگر"
                
                self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data == "list_male":
                db_u = self.db.read("users")
                male_users = [u for u, data in db_u["users"].items() if data.get("sex") == "آقا"]
                
                text = "<b>👦 لیست کاربران آقا</b>\n\n"
                for i, user_id in enumerate(male_users[:20], 1):
                    user = db_u["users"][user_id]
                    text += f"{i}. {user.get('name', 'نامشخص')}\n"
                    text += f"   🆔: {user_id} | سن: {user.get('age', 'نامشخص')}\n"
                    text += f"   💰 سکه: {user.get('coins', 0):,}\n"
                    text += f"   VIP: {'✅' if self.is_vip(user_id) else '❌'}\n\n"
                
                if len(male_users) > 20:
                    text += f"\n... و {len(male_users) - 20} کاربر دیگر"
                
                self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data == "list_female":
                db_u = self.db.read("users")
                female_users = [u for u, data in db_u["users"].items() if data.get("sex") == "خانم"]
                
                text = "<b>👧 لیست کاربران خانم</b>\n\n"
                for i, user_id in enumerate(female_users[:20], 1):
                    user = db_u["users"][user_id]
                    text += f"{i}. {user.get('name', 'نامشخص')}\n"
                    text += f"   🆔: {user_id} | سن: {user.get('age', 'نامشخص')}\n"
                    text += f"   💰 سکه: {user.get('coins', 0):,}\n"
                    text += f"   VIP: {'✅' if self.is_vip(user_id) else '❌'}\n\n"
                
                if len(female_users) > 20:
                    text += f"\n... و {len(female_users) - 20} کاربر دیگر"
                
                self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data == "list_all":
                db_u = self.db.read("users")
                
                text = "<b>👥 لیست تمام کاربران</b>\n\n"
                for i, (user_id, user) in enumerate(list(db_u["users"].items())[:20], 1):
                    text += f"{i}. {user.get('name', 'نامشخص')}\n"
                    text += f"   🆔: {user_id} | {user.get('sex', 'نامشخص')} | سن: {user.get('age', 'نامشخص')}\n"
                    text += f"   💰 سکه: {user.get('coins', 0):,} | VIP: {'✅' if self.is_vip(user_id) else '❌'}\n\n"
                
                if len(db_u["users"]) > 20:
                    text += f"\n... و {len(db_u['users']) - 20} کاربر دیگر"
                
                self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅")
            
            # مشاهده کاربر خاص
            elif call.data.startswith("admin_view_user_"):
                user_id = call.data.split("_")[3]
                db_u = self.db.read("users")
                user = db_u["users"].get(user_id, {})
                
                if user:
                    text = f"<b>👤 اطلاعات کاربر</b>\n\n"
                    text += f"🆔 آیدی: {user_id}\n"
                    text += f"📛 نام: {user.get('name', 'نامشخص')}\n"
                    text += f"⚧ جنسیت: {user.get('sex', 'نامشخص')}\n"
                    text += f"🔢 سن: {user.get('age', 'نامشخص')}\n"
                    text += f"💰 سکه: {user.get('coins', 0):,}\n"
                    text += f"🎖 VIP: {'✅ فعال' if self.is_vip(user_id) else '❌ غیرفعال'}\n"
                    text += f"⚠️ اخطار: {user.get('warns', 0)}/3\n"
                    text += f"👥 رفرال: {user.get('total_referrals', 0)} نفر\n"
                    text += f"📅 عضویت: {user.get('join_date', 'نامشخص')}\n"
                    text += f"🕐 آخرین فعالیت: {user.get('last_active_date', 'نامشخص')}\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(
                        types.InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_user_{user_id}"),
                        types.InlineKeyboardButton("💰 اهدا سکه", callback_data=f"gift_user_{user_id}")
                    )
                    kb.add(
                        types.InlineKeyboardButton("🎖 گیفت VIP", callback_data=f"vip_user_{user_id}"),
                        types.InlineKeyboardButton("🚫 بن کاربر", callback_data=f"ban_user_{user_id}")
                    )
                    kb.add(
                        types.InlineKeyboardButton("📊 تاریخچه", callback_data=f"history_user_{user_id}"),
                        types.InlineKeyboardButton("🌳 درخت رفرال", callback_data=f"referral_tree_{user_id}")
                    )
                    
                    self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
                else:
                    self.bot.answer_callback_query(call.id, "❌ کاربر یافت نشد")
            
            # تأیید ارسال پیام همگانی
            elif call.data.startswith("confirm_broadcast_"):
                target = call.data.split("_")[2]
                db_u = self.db.read("users")
                message = db_u["users"][uid].get("broadcast_message", "")
                
                if message:
                    sent_count = self.send_broadcast(message, target)
                    target_text = "همه کاربران" if target == "all" else "کاربران VIP"
                    
                    self.bot.edit_message_text(f"✅ پیام همگانی ارسال شد\n\n"
                                              f"مخاطب: {target_text}\n"
                                              f"تعداد ارسال شده: {sent_count} کاربر\n\n"
                                              f"متن پیام:\n{message}",
                                              call.message.chat.id, call.message.message_id)
                    
                    # ثبت لاگ ادمین
                    self.db.log_admin_action(uid, "broadcast", None, 
                                           f"target={target}, sent={sent_count}")
                    
                    # پاک کردن پیام موقت
                    db_u["users"][uid].pop("broadcast_message", None)
                    db_u["users"][uid].pop("broadcast_target", None)
                    db_u["users"][uid]["admin_state"] = None
                    self.db.write("users", db_u)
                else:
                    self.bot.answer_callback_query(call.id, "❌ خطا در ارسال پیام")
            
            elif call.data == "cancel_broadcast":
                db_u = self.db.read("users")
                db_u["users"][uid].pop("broadcast_message", None)
                db_u["users"][uid].pop("broadcast_target", None)
                db_u["users"][uid]["admin_state"] = None
                self.db.write("users", db_u)
                
                self.bot.edit_message_text("❌ ارسال پیام همگانی لغو شد",
                                          call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅ لغو شد")
            
            # مدیریت کلمات فیلتر
            elif call.data == "add_filter_word":
                db_u = self.db.read("users")
                db_u["users"][uid]["admin_state"] = "add_filter_word"
                self.db.write("users", db_u)
                
                self.bot.send_message(uid, "➕ کلمه جدید برای افزودن به فیلتر را وارد کنید:")
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data == "remove_filter_word":
                db_u = self.db.read("users")
                db_u["users"][uid]["admin_state"] = "remove_filter_word"
                self.db.write("users", db_u)
                
                self.bot.send_message(uid, "➖ کلمه برای حذف از فیلتر را وارد کنید:")
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data == "list_filter_words":
                text = "<b>📋 لیست کلمات فیلتر</b>\n\n"
                for i, word in enumerate(self.bad_words, 1):
                    text += f"{i}. {word}\n"
                
                self.bot.send_message(uid, text)
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data == "reset_filter_words":
                # بازنشانی به لیست پیش‌فرض
                default_words = [
                    "کیر", "کیرم", "کیرت", "کیری", "کس", "کص", "کوس", "کوث",
                    "جنده", "جهنده", "مادرجنده", "قحبه", "قهبه",
                    "پدرسگ", "پدرسوخته", "حرامزاده", "گاییدم", "گاییدن",
                    "سیکتیر", "کون", "کونی", "گوه", "لاشی", "فاحشه",
                    "ناموس", "اوبی", "بی‌ناموس", "سکس", "پورن",
                    "خارکصه", "تخمم", "شاسگول", "پفیوز", "دیوث"
                ]
                
                self.bad_words = default_words
                self.save_settings()
                
                self.bot.answer_callback_query(call.id, "✅ لیست کلمات بازنشانی شد")
                self.bot.send_message(uid, "✅ لیست کلمات فیلتر به حالت پیش‌فرض بازنشانی شد.")
            
            # تنظیم حساسیت AI
            elif call.data == "increase_sensitivity":
                self.ai_sensitivity["toxic"] = min(1.0, self.ai_sensitivity["toxic"] + 0.1)
                self.ai_sensitivity["nsfw"] = min(1.0, self.ai_sensitivity["nsfw"] + 0.1)
                self.save_settings()
                
                self.bot.answer_callback_query(call.id, "✅ حساسیت افزایش یافت")
                self.bot.send_message(uid, f"✅ حساسیت AI افزایش یافت:\n"
                                          f"• محتوای سمی: {self.ai_sensitivity['toxic']:.1f}\n"
                                          f"• محتوای +18: {self.ai_sensitivity['nsfw']:.1f}")
            
            elif call.data == "decrease_sensitivity":
                self.ai_sensitivity["toxic"] = max(0.1, self.ai_sensitivity["toxic"] - 0.1)
                self.ai_sensitivity["nsfw"] = max(0.1, self.ai_sensitivity["nsfw"] - 0.1)
                self.save_settings()
                
                self.bot.answer_callback_query(call.id, "✅ حساسیت کاهش یافت")
                self.bot.send_message(uid, f"✅ حساسیت AI کاهش یافت:\n"
                                          f"• محتوای سمی: {self.ai_sensitivity['toxic']:.1f}\n"
                                          f"• محتوای +18: {self.ai_sensitivity['nsfw']:.1f}")
            
            elif call.data == "reset_sensitivity":
                self.ai_sensitivity = {"toxic": 0.8, "nsfw": 0.8}
                self.save_settings()
                
                self.bot.answer_callback_query(call.id, "✅ حساسیت بازنشانی شد")
                self.bot.send_message(uid, "✅ حساسیت AI به مقدار پیش‌فرض بازنشانی شد.")
            
            elif call.data == "test_ai":
                test_texts = [
                    "این یک متن تستی است",
                    "تو خیلی کیری هستی",
                    "می‌خواهم با تو رابطه جنسی داشته باشم"
                ]
                
                text = "<b>🧪 تست سیستم AI</b>\n\n"
                for test_text in test_texts:
                    toxic_score = self.ai_toxic_scan(test_text)
                    nsfw_score = self.ai_nsfw_scan(test_text)
                    
                    text += f"📝 متن: {test_text}\n"
                    text += f"☠️ امتیاز سمی: {toxic_score:.2f} ({'✅' if toxic_score < self.ai_sensitivity['toxic'] else '❌'})\n"
                    text += f"🔞 امتیاز +18: {nsfw_score:.2f} ({'✅' if nsfw_score < self.ai_sensitivity['nsfw'] else '❌'})\n\n"
                
                self.bot.send_message(uid, text)
                self.bot.answer_callback_query(call.id, "✅")
            
            # مدیریت قابلیت‌ها
            elif call.data == "enable_features":
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("🛰 چت ناشناس", callback_data="enable_chat"),
                    types.InlineKeyboardButton("📩 پیام ناشناس", callback_data="enable_anon_msg")
                )
                kb.add(
                    types.InlineKeyboardButton("🎡 گردونه شانس", callback_data="enable_wheel"),
                    types.InlineKeyboardButton("🎯 ماموریت روزانه", callback_data="enable_missions")
                )
                kb.add(
                    types.InlineKeyboardButton("👥 سیستم رفرال", callback_data="enable_referral"),
                    types.InlineKeyboardButton("🎖 فروشگاه VIP", callback_data="enable_vip_shop")
                )
                kb.add(
                    types.InlineKeyboardButton("✅ همه", callback_data="enable_all"),
                    types.InlineKeyboardButton("❌ انصراف", callback_data="cancel_features")
                )
                
                self.bot.edit_message_text("<b>✅ فعال کردن قابلیت‌ها</b>\n\n"
                                          "قابلیت مورد نظر برای فعال کردن را انتخاب کنید:",
                                          call.message.chat.id, call.message.message_id,
                                          reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data == "disable_features":
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("🛰 چت ناشناس", callback_data="disable_chat"),
                    types.InlineKeyboardButton("📩 پیام ناشناس", callback_data="disable_anon_msg")
                )
                kb.add(
                    types.InlineKeyboardButton("🎡 گردونه شانس", callback_data="disable_wheel"),
                    types.InlineKeyboardButton("🎯 ماموریت روزانه", callback_data="disable_missions")
                )
                kb.add(
                    types.InlineKeyboardButton("👥 سیستم رفرال", callback_data="disable_referral"),
                    types.InlineKeyboardButton("🎖 فروشگاه VIP", callback_data="disable_vip_shop")
                )
                kb.add(
                    types.InlineKeyboardButton("❌ همه", callback_data="disable_all"),
                    types.InlineKeyboardButton("✅ انصراف", callback_data="cancel_features")
                )
                
                self.bot.edit_message_text("<b>❌ غیرفعال کردن قابلیت‌ها</b>\n\n"
                                          "قابلیت مورد نظر برای غیرفعال کردن را انتخاب کنید:",
                                          call.message.chat.id, call.message.message_id,
                                          reply_markup=kb)
                self.bot.answer_callback_query(call.id, "✅")
            
            elif call.data.startswith("enable_"):
                feature = call.data.split("_")[1]
                feature_names = {
                    "chat": "چت ناشناس",
                    "anon_msg": "پیام ناشناس",
                    "wheel": "گردونه شانس",
                    "missions": "ماموریت روزانه",
                    "referral": "سیستم رفرال",
                    "vip_shop": "فروشگاه VIP",
                    "all": "همه قابلیت‌ها"
                }
                
                if self.toggle_feature(feature, True):
                    self.bot.answer_callback_query(call.id, f"✅ {feature_names.get(feature, feature)} فعال شد")
                else:
                    self.bot.answer_callback_query(call.id, "❌ خطا")
            
            elif call.data.startswith("disable_"):
                feature = call.data.split("_")[1]
                feature_names = {
                    "chat": "چت ناشناس",
                    "anon_msg": "پیام ناشناس",
                    "wheel": "گردونه شانس",
                    "missions": "ماموریت روزانه",
                    "referral": "سیستم رفرال",
                    "vip_shop": "فروشگاه VIP",
                    "all": "همه قابلیت‌ها"
                }
                
                if self.toggle_feature(feature, False):
                    self.bot.answer_callback_query(call.id, f"✅ {feature_names.get(feature, feature)} غیرفعال شد")
                else:
                    self.bot.answer_callback_query(call.id, "❌ خطا")
            
            elif call.data == "cancel_features":
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
                self.bot.answer_callback_query(call.id, "✅ انصراف")
            
            # سایر کال‌بک‌ها...
            
            # هندلر برای stateهای فیلتر کلمات
            @self.bot.message_handler(func=lambda msg: True)
            def handle_filter_states(msg):
                uid = str(msg.chat.id)
                if uid != self.owner:
                    return
                
                db_u = self.db.read("users")
                user = db_u["users"].get(uid, {})
                admin_state = user.get("admin_state")
                
                if admin_state == "add_filter_word":
                    word = msg.text.strip()
                    if self.add_filter_word(word):
                        self.bot.send_message(uid, f"✅ کلمه '{word}' به فیلتر اضافه شد.")
                    else:
                        self.bot.send_message(uid, f"❌ کلمه '{word}' قبلاً در فیلتر وجود دارد.")
                    
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                
                elif admin_state == "remove_filter_word":
                    word = msg.text.strip()
                    if self.remove_filter_word(word):
                        self.bot.send_message(uid, f"✅ کلمه '{word}' از فیلتر حذف شد.")
                    else:
                        self.bot.send_message(uid, f"❌ کلمه '{word}' در فیلتر وجود ندارد.")
                    
                    user["admin_state"] = None
                    self.db.write("users", db_u)

        # هندلرهای اصلی باقی می‌مانند (همان کد قبلی)
        # برای جلوگیری از طولانی شدن کد، هندلرهای اصلی حذف نشده‌اند
        # فقط تغییرات لازم اعمال شده‌اند

    def run(self):
        """اجرای ربات"""
        print("=" * 50)
        print("Shadow Titan v42.0 - Ultimate Edition")
        print("پنل مدیریت پیشرفته فعال شده است")
        print("=" * 50)
        
        try:
            server_thread = Thread(target=run_web)
            server_thread.daemon = True
            server_thread.start()
            print("✅ وب سرور روی پورت 8080 راه‌اندازی شد")
        except Exception as e:
            logger.error(f"خطای وب سرور: {e}")

        # شروع مانیتورینگ خودکار
        def auto_monitor():
            while True:
                try:
                    # بررسی فعالیت مشکوک هر 30 دقیقه
                    suspicious = self.check_suspicious_activity()
                    if suspicious and self.owner:
                        text = "⚠️ <b>فعالیت مشکوک شناسایی شد</b>\n\n"
                        for item in suspicious[:5]:
                            text += f"👤 کاربر: {item['user']}\n"
                            text += f"📝 دلیل: {item['reason']}\n"
                            text += f"🕐 زمان: {item['last_active']}\n\n"
                        
                        try:
                            self.bot.send_message(self.owner, text)
                        except:
                            pass
                    
                    # بن الگوریتمی هر 1 ساعت
                    self.algorithmic_ban()
                    
                    time.sleep(1800)  # 30 دقیقه
                except Exception as e:
                    logger.error(f"خطا در مانیتورینگ خودکار: {e}")
                    time.sleep(300)  # 5 دقیقه در صورت خطا
        
        monitor_thread = threading.Thread(target=auto_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            print("🚀 در حال اتصال به تلگرام...")
            self.bot.infinity_polling(skip_pending=True)
        except Exception as e:
            logger.error(f"خطای Polling: {e}")
            print(f"❌ خطای Polling: {e}")

if __name__ == "__main__":
    bot_instance = ShadowTitanBot()
    bot_instance.run()
