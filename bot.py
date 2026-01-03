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
            "badwords": "db_badwords.json",
            "vip_prices": "db_vip_prices.json",
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
            "badwords": {"words": [
                "کیر", "کیرم", "کیرت", "کیری", "کس", "کص", "کوس", "کوث",
                "جنده", "جهنده", "مادرجنده", "قحبه", "قهبه",
                "پدرسگ", "پدرسوخته", "حرامزاده", "گاییدم", "گاییدن",
                "سیکتیر", "کون", "کونی", "گوه", "لاشی", "فاحشه",
                "ناموس", "اوبی", "بی‌ناموس", "سکس", "پورن",
                "خارکصه", "تچمم", "شاسگول", "پفیوز", "دیوث"
            ]},
            "vip_prices": {
                "week": 500,
                "month": 1800,
                "3month": 5000,
                "6month": 9000,
                "year": 15000,
                "christmas": 0
            },
            "settings": {
                "maintenance": False,
                "ai_toxic_filter": True,
                "ai_nsfw_filter": True,
                "save_logs": True,
                "show_public_stats": True
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
# ربات اصلی
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

        # قیمت‌های VIP با سکه
        self.vip_prices_coins = self.db.read("vip_prices")

        # مدت‌های VIP به ثانیه
        self.vip_durations = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "3month": 90 * 24 * 3600,
            "6month": 180 * 24 * 3600,
            "year": 365 * 24 * 3600,
            "christmas": 90 * 24 * 3600  # 3 ماه رایگان
        }

        # لیست فحش
        self.bad_words = self.db.read("badwords")["words"]

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

    def restore_active_chats(self):
        """بازیابی چت‌های فعال از دیتابیس"""
        db_c = self.db.read("chats")
        db_u = self.db.read("users")
        
        for uid, partner in db_c.items():
            if uid in db_u["users"] and partner in db_u["users"]:
                # بررسی کنید که هر دو کاربر هنوز موجود هستند
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
            # انتخاب ماموریت تصادفی از لیست
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
        
        # مدت جدید را به انتهای مدت فعلی اضافه کن (جمع شدن مدت VIP ها)
        if current_end < now:
            # اگر VIP قبلی تمام شده، از الان شروع کن
            new_end = now + self.vip_durations[duration_key]
        else:
            # اگر VIP فعال داره، مدت جدید رو به انتهای اون اضافه کن
            new_end = current_end + self.vip_durations[duration_key]
        
        db_u["users"][uid]["vip_end"] = new_end
        
        # ذخیره اینکه کاربر VIP رایگان کریسمس را دریافت کرده
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
            
            # محاسبه مدت باقی‌مانده
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
        
        # اطمینان از وجود کلید coins
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
        
        # بررسی شرایط ماموریت
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
        
        # حذف از چت‌های فعال
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
            markup.add("📊 پنل مدیریت")
        return markup

    def kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def kb_admin(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📈 آمار کامل", "⚠️ هشدار تعمیر")
        markup.add("🛠 تعمیر و نگهداری", "🎖 گیفت VIP تکی")
        markup.add("🎖 گیفت VIP همگانی", "❌ حذف VIP")
        markup.add("📋 لیست VIP", "💰 اهدای سکه")
        markup.add("🎯 مدیریت ماموریت‌ها", "📁 دانلود دیتابیس")
        markup.add("🚫 لیست بن‌شده‌ها", "🔙 بازگشت به منو")
        # اضافه کردن منوهای جدید:
        markup.add("📝 مدیریت کلمات ممنوعه", "💰 تنظیم قیمت‌های VIP")
        markup.add("⚙️ تنظیمات پیشرفته", "📊 گزارش‌های کاربران")
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
                for i in range(6):  # 6 * 30 ثانیه = 3 دقیقه
                    # بررسی اگر رویداد تنظیم شده (یعنی لغو شده)
                    if self.maintenance_warning_event.is_set():
                        logger.info("هشدار تعمیر توسط ادمین لغو شد")
                        return
                    
                    time.sleep(30)
                    remaining = 3 - (i * 0.5)
                    
                    # ارسال هشدار به ادمین
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
                
                # بعد از 3 دقیقه، بررسی اگر لغو نشده
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
        
        # تنظیم رویداد برای متوقف کردن ترد
        if self.maintenance_warning_event:
            self.maintenance_warning_event.set()
        
        self.maintenance_warning_active = False
        
        # ارسال پیام عذرخواهی به کاربران
        self.send_maintenance_cancel_notification()
        
        return True

    def send_maintenance_cancel_notification(self):
        """ارسال پیام لغو هشدار به کاربران"""
        db_u = self.db.read("users")
        users_to_notify = []
        
        # فقط به کاربران VIP و کاربرانی که اخیرا فعال بودند پیام بده
        for uid, user_data in db_u["users"].items():
            if self.is_vip(uid):
                users_to_notify.append(uid)
        
        # محدود کردن به 50 کاربر برای جلوگیری از اسپم
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
                    # کاربر جدید از رفرال
                    if referrer_id in db_u["users"]:
                        db_u["users"][referrer_id]["total_referrals"] = db_u["users"][referrer_id].get("total_referrals", 0) + 1
                        db_u["users"][referrer_id]["referral_list"] = db_u["users"][referrer_id].get("referral_list", [])
                        db_u["users"][referrer_id]["referral_list"].append(uid)
                        self.db.write("users", db_u)
                        
                        # پاداش رفرال
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
                        "anon_target": target
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
                    "had_temp_ban": False
                }
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\n"
                                          "لطفاً نام مستعار خود را وارد کنید:")
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
                    is_bad = self.contains_bad(msg.text)
                    toxic_score = self.ai_toxic_scan(msg.text)
                    nsfw_score = self.ai_nsfw_scan(msg.text)
                    
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
                kb = types.InlineKeyboardMarkup(row_width=3)
                kb.add(
                    types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                    types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                    types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any")
                )
                self.bot.send_message(uid, "🔍 دنبال چه کسی می‌گردید؟", reply_markup=kb)

            elif text == "👤 پروفایل من":
                # بارگیری دیتابیس تازه
                db_u = self.db.read("users")
                user = db_u["users"].get(uid)
                
                if not user:
                    return
                
                # شمارش برای ماموریت
                user["daily_profile_views"] = user.get("daily_profile_views", 0) + 1
                self.db.write("users", db_u)
                
                rank = "🎖 VIP" if self.is_vip(uid) else "⭐ عادی"
                vip_end = user.get("vip_end", 0)
                
                if vip_end > 0:
                    vip_status = f"تا {datetime.datetime.fromtimestamp(vip_end).strftime('%Y-%m-%d')}"
                    
                    # محاسبه مدت باقی‌مانده
                    now = datetime.datetime.now().timestamp()
                    remaining_days = int((vip_end - now) / (24 * 3600))
                    if remaining_days > 0:
                        vip_status += f" ({remaining_days} روز)"
                else:
                    vip_status = "ندارید"
                
                # اطمینان از وجود coins
                coins = user.get("coins", 0)
                
                profile_text = f"<b>👤 پروفایل شما</b>\n\n"
                profile_text += f"نام: {user.get('name', 'نامشخص')}\n"
                profile_text += f"جنسیت: {user.get('sex', 'نامشخص')}\n"
                profile_text += f"سن: {user.get('age', 'نامشخص')}\n"
                profile_text += f"رنک: {rank}\n"
                profile_text += f"VIP: {vip_status}\n"
                profile_text += f"💰 سکه: {coins:,}\n"
                profile_text += f"👥 رفرال: {user.get('total_referrals', 0)} نفر\n"
                profile_text += f"⚠️ اخطار: {user.get('warns', 0)}/3\n"
                
                # نمایش وضعیت VIP کریسمس
                if user.get("christmas_vip_taken", False):
                    profile_text += f"🎄 VIP کریسمس: <b>دریافت شده ✅</b>"
                
                self.bot.send_message(uid, profile_text)
                
                # بررسی ماموریت
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
                    txt += f"{status} <b>پیام {i+1}:</b>\n{m['text']}\n"
                    txt += f"<i>🕐 {m['time']}</i>\n\n"
                    kb.add(types.InlineKeyboardButton(f"📝 پاسخ به پیام {i+1}", 
                                                     callback_data=f"anon_reply_{i}"))
                
                self.bot.send_message(uid, txt, reply_markup=kb)
                
                # علامت‌گذاری به عنوان دیده شده
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
                today = str(datetime.date.today())
                if user.get("last_spin") == today:
                    self.bot.send_message(uid, "⏰ امروز قبلاً گردونه را چرخانده‌اید\n\n"
                                              "فردا دوباره امتحان کنید! 🎡")
                    return
                
                user["last_spin"] = today
                user["daily_spin_done"] = True
                self.db.write("users", db_u)
                
                # احتمالات جدید
                rand = random.random()
                
                if rand < 0.001:  # 0.1% - VIP 30 روزه
                    self.add_vip(uid, "month", "گردونه شانس")
                    result = "🎉 <b>جایزه بزرگ!</b>\n\n🎖 VIP ۳۰ روزه\n\nتبریک! 🎊"
                elif rand < 0.05:  # 4.9% - سکه زیاد
                    coins = random.choice([500, 750, 1000])
                    self.add_coins(uid, coins, "گردونه شانس")
                    result = f"🎁 <b>برنده شدید!</b>\n\n💰 {coins:,} سکه\n\nآفرین! ✨"
                elif rand < 0.3:  # 25% - سکه معمولی
                    coins = random.choice([50, 100, 150, 200])
                    self.add_coins(uid, coins, "گردونه شانس")
                    result = f"🎯 <b>موفق!</b>\n\n💰 {coins:,} سکه\n\nخوب بود! 👍"
                else:  # 70% - پوچ
                    result = "😔 <b>متأسفانه پوچ!</b>\n\nشانس بعدی را امتحان کنید 🍀"
                
                self.bot.send_message(uid, f"🎡 گردونه در حال چرخش...\n\n{result}")
                
                # بررسی ماموریت
                self.check_and_reward_mission(uid)

            elif text == "🎯 ماموریت روزانه":
                db_m = self.db.read("missions")
                mission = db_m["daily"]
                
                today = str(datetime.date.today())
                completed = user.get("mission_completed_date") == today
                
                # دریافت توضیح ماموریت
                mission_description = mission.get("description", self.get_mission_description(mission['type'], mission['target']))
                
                mission_text = f"<b>🎯 ماموریت روزانه</b>\n\n"
                mission_text += f"📋 ماموریت: {mission['mission']}\n"
                mission_text += f"📝 کار انجام‌دادنی: {mission_description}\n"
                
                # نمایش پاداش
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
                    # نمایش پیشرفت
                    mission_type = mission['type']
                    target = mission['target']
                    
                    if mission_type == "chat_count":
                        progress = f"{user.get('daily_chat_count', 0)}/{target}"
                    elif mission_type == "unique_chats":
                        progress = f"{len(user.get('daily_unique_chats', []))}/{target}"
                    elif mission_type == "referrals":
                        progress = f"{user.get('total_referrals', 0)}/{target}"
                    elif mission_type == "spin_wheel":
                        progress = "✅" if user.get("daily_spin_done") else "❌"
                    elif mission_type == "profile_views":
                        progress = f"{user.get('daily_profile_views', 0)}/{target}"
                    else:
                        progress = "❓"
                    
                    mission_text += f"📊 پیشرفت: {progress}\n\n"
                    mission_text += "برای تکمیل ماموریت تلاش کنید! 💪"
                
                self.bot.send_message(uid, mission_text)
                
                # بررسی ماموریت
                self.check_and_reward_mission(uid)

            elif text == "👥 رفرال و دعوت":
                db_u = self.db.read("users")
                user = db_u["users"].get(uid)
                
                if not user:
                    return
                
                ref_link = f"https://t.me/{self.username}?start=ref_{uid}"
                ref_count = user.get("total_referrals", 0)
                
                ref_text = f"<b>👥 سیستم دعوت دوستان</b>\n\n"
                ref_text += f"🔗 لینک دعوت شما:\n<code>{ref_link}</code>\n\n"
                ref_text += f"📊 تعداد دعوت شده‌ها: {ref_count} نفر\n\n"
                ref_text += "🎁 پاداش‌ها:\n"
                ref_text += "• دعوت هر کاربر جدید: 100 سکه\n"
                ref_text += "• دعوت 2 نفر: VIP 1 هفته\n"
                ref_text += "• دعوت 5 نفر: VIP 1 ماه\n\n"
                ref_text += "با دوستان خود به اشتراک بگذارید و پاداش بگیرید! ✨"
                
                self.bot.send_message(uid, ref_text)

            elif text == "🎖 خرید VIP":
                if self.is_vip(uid):
                    self.bot.send_message(uid, "⚠️ شما در حال حاضر VIP هستید!")
                    return
                
                db_prices = self.db.read("vip_prices")
                prices_text = "\n".join([
                    f"{k}: {v:,} سکه" for k, v in db_prices.items() if k != "christmas"
                ])
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("1 هفته - 500 سکه", callback_data="vip_buy_week"),
                    types.InlineKeyboardButton("1 ماه - 1800 سکه", callback_data="vip_buy_month")
                )
                kb.add(
                    types.InlineKeyboardButton("3 ماه - 5000 سکه", callback_data="vip_buy_3month"),
                    types.InlineKeyboardButton("6 ماه - 9000 سکه", callback_data="vip_buy_6month")
                )
                kb.add(
                    types.InlineKeyboardButton("1 سال - 15000 سکه", callback_data="vip_buy_year")
                )
                
                # VIP رایگان کریسمس (فقط یک بار)
                if not user.get("christmas_vip_taken", False):
                    kb.add(
                        types.InlineKeyboardButton("🎄 3 ماه رایگان (کریسمس)", callback_data="vip_buy_christmas")
                    )
                
                self.bot.send_message(
                    uid,
                    f"<b>🎖 خرید VIP</b>\n\n"
                    f"قیمت‌ها (سکه):\n{prices_text}\n\n"
                    f"موجودی شما: {user.get('coins', 0):,} سکه\n\n"
                    "مدت مورد نظر را انتخاب کنید:",
                    reply_markup=kb
                )

            elif text == "❓ راهنما و قوانین":
                rules = [
                    "1. ارسال محتوای غیراخلاقی ممنوع",
                    "2. فحاشی و توهین ممنوع",
                    "3. اسپم و ارسال پیام‌های تکراری ممنوع",
                    "4. احترام به حریم خصوصی دیگران الزامی است",
                    "5. هر کاربر حداکثر 3 اخطار دارد",
                    "6. در صورت تخلف، حساب شما مسدود می‌شود",
                    "7. ربات برای افراد بالای 12 سال مناسب است",
                    "8. از سیستم گزارش سوءاستفاده نکنید"
                ]
                
                help_text = "<b>📚 راهنما و قوانین</b>\n\n"
                help_text += "🔹 <b>قوانین اصلی:</b>\n"
                help_text += "\n".join(rules[:4]) + "\n\n"
                help_text += "🔹 <b>قوانین امنیتی:</b>\n"
                help_text += "\n".join(rules[4:]) + "\n\n"
                help_text += f"📞 پشتیبانی: {self.support}\n"
                help_text += f"📢 کانال: {self.channel}"
                
                self.bot.send_message(uid, help_text)

            elif text == "⚙ تنظیمات":
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("✏️ تغییر نام", callback_data="set_name"),
                    types.InlineKeyboardButton("🔢 تغییر سن", callback_data="set_age")
                )
                kb.add(
                    types.InlineKeyboardButton("🔔 نوتیفیکیشن", callback_data="set_notif"),
                    types.InlineKeyboardButton("🔞 فیلتر +18", callback_data="set_nsfw")
                )
                
                self.bot.send_message(
                    uid,
                    "⚙️ <b>تنظیمات حساب کاربری</b>\n\n"
                    "گزینه مورد نظر را انتخاب کنید:",
                    reply_markup=kb
                )

            elif text == "📊 پنل مدیریت" and uid == self.owner:
                self.bot.send_message(uid, "🔐 <b>پنل مدیریت</b>", reply_markup=self.kb_admin())

            # مدیریت کلمات ممنوعه
            elif text == "📝 مدیریت کلمات ممنوعه":
                if uid != self.owner:
                    return
                
                db_badwords = self.db.read("badwords")
                words_list = "\n".join([f"• {word}" for word in db_badwords["words"]])
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("➕ افزودن کلمه", callback_data="badwords_add"),
                    types.InlineKeyboardButton("➖ حذف کلمه", callback_data="badwords_remove")
                )
                kb.add(
                    types.InlineKeyboardButton("🔄 ریست به پیش‌فرض", callback_data="badwords_reset")
                )
                
                self.bot.send_message(
                    uid,
                    f"<b>📝 مدیریت کلمات ممنوعه</b>\n\n"
                    f"تعداد کلمات: {len(db_badwords['words'])}\n\n"
                    f"<b>کلمات فعلی:</b>\n{words_list}",
                    reply_markup=kb
                )

            # تنظیم قیمت‌های VIP
            elif text == "💰 تنظیم قیمت‌های VIP":
                if uid != self.owner:
                    return
                
                db_prices = self.db.read("vip_prices")
                prices_text = "\n".join([f"{k}: {v:,} سکه" for k, v in db_prices.items()])
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("🔄 تغییر قیمت‌ها", callback_data="vip_prices_edit"),
                )
                
                self.bot.send_message(
                    uid,
                    f"<b>💰 تنظیم قیمت‌های VIP</b>\n\n"
                    f"<b>قیمت‌ها (سکه):</b>\n{prices_text}",
                    reply_markup=kb
                )

            # تنظیمات پیشرفته
            elif text == "⚙️ تنظیمات پیشرفته":
                if uid != self.owner:
                    return
                
                db_settings = self.db.read("settings")
                
                settings_text = "<b>⚙️ تنظیمات پیشرفته ربات</b>\n\n"
                settings_text += f"🔧 حالت تعمیر: {'🟢 فعال' if db_settings.get('maintenance') else '🔴 غیرفعال'}\n"
                settings_text += f"🤖 AI فیلتر فحش: {'🟢 فعال' if db_settings.get('ai_toxic_filter', True) else '🔴 غیرفعال'}\n"
                settings_text += f"🔞 AI فیلتر +18: {'🟢 فعال' if db_settings.get('ai_nsfw_filter', True) else '🔴 غیرفعال'}\n"
                settings_text += f"📊 ذخیره لاگ: {'🟢 فعال' if db_settings.get('save_logs', True) else '🔴 غیرفعال'}\n"
                settings_text += f"👁️‍🗨️ نمایش آمار عمومی: {'🟢 فعال' if db_settings.get('show_public_stats', True) else '🔴 غیرفعال'}\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("🔧 تغییر تنظیمات", callback_data="settings_edit"),
                )
                
                self.bot.send_message(uid, settings_text, reply_markup=kb)

            # گزارش‌های کاربران
            elif text == "📊 گزارش‌های کاربران":
                if uid != self.owner:
                    return
                
                today = str(datetime.date.today())
                db_u = self.db.read("users")
                
                total_reports = 0
                resolved_reports = 0
                pending_reports = 0
                
                for user_data in db_u["users"].values():
                    total_reports += user_data.get("reports_received", 0)
                    resolved_reports += user_data.get("reports_resolved", 0)
                
                pending_reports = total_reports - resolved_reports
                
                reports_text = "<b>📊 گزارش‌های کاربران</b>\n\n"
                reports_text += f"📅 تاریخ: {today}\n"
                reports_text += f"📤 کل گزارش‌ها: {total_reports}\n"
                reports_text += f"✅ حل شده: {resolved_reports}\n"
                reports_text += f"⏳ در انتظار: {pending_reports}\n"
                reports_text += f"📊 درصد حل‌شده: {int((resolved_reports/total_reports*100) if total_reports>0 else 0)}%\n"
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                kb.add(
                    types.InlineKeyboardButton("📅 گزارش روزانه", callback_data="reports_daily"),
                    types.InlineKeyboardButton("📆 گزارش هفتگی", callback_data="reports_weekly")
                )
                kb.add(
                    types.InlineKeyboardButton("📋 گزارش کامل", callback_data="reports_full")
                )
                
                self.bot.send_message(uid, reports_text, reply_markup=kb)

            else:
                # اگر پیام نامشخص بود
                self.bot.send_message(uid, "⚠️ دستور نامعتبر!\n\n"
                                          "لطفاً از منوی اصلی گزینه مورد نظر را انتخاب کنید.")

        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            uid = str(call.message.chat.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            
            if not user:
                return
            
            # ثبت کلیک برای ماموریت
            user["daily_profile_views"] = user.get("daily_profile_views", 0) + 1
            self.db.write("users", db_u)
            
            # بررسی ماموریت
            self.check_and_reward_mission(uid)
            
            # انتخاب جنسیت
            if call.data.startswith("sex_"):
                sex = call.data.split("_")[1]
                user["sex"] = "آقا" if sex == "m" else "خانم"
                user["state"] = "age"
                self.db.write("users", db_u)
                
                self.bot.edit_message_text(
                    f"جنسیت شما {user['sex']} ثبت شد\n\n"
                    "لطفاً سن خود را وارد کنید (بین ۱۲ تا ۹۹):",
                    call.message.chat.id,
                    call.message.message_id
                )
            
            # جستجوی هم‌صحبت
            elif call.data.startswith("find_"):
                sex_pref = call.data.split("_")[1]
                
                # اگر در حال چت هستید
                if user.get("partner"):
                    self.bot.answer_callback_query(call.id, "⚠️ شما در حال چت هستید!")
                    return
                
                # اگر قبلاً در صف هستید
                db_q = self.db.read("queue")
                if uid in db_q["general"]:
                    self.bot.answer_callback_query(call.id, "⏳ شما در صف انتظار هستید!")
                    return
                
                # اضافه به صف
                db_q["general"].append(uid)
                user["state"] = "searching"
                user["search_pref"] = sex_pref
                self.db.write("queue", db_q)
                self.db.write("users", db_u)
                
                self.bot.edit_message_text(
                    "🔍 در حال جستجوی هم‌صحبت...\n\n"
                    "برای لغو جستجو روی دکمه زیر کلیک کنید.",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("❌ لغو جستجو", callback_data="cancel_search")
                    )
                )
                
                # شروع جستجو
                self.start_search(uid, sex_pref)
            
            # لغو جستجو
            elif call.data == "cancel_search":
                db_q = self.db.read("queue")
                if uid in db_q["general"]:
                    db_q["general"].remove(uid)
                    self.db.write("queue", db_q)
                
                user["state"] = "idle"
                self.db.write("users", db_u)
                
                self.bot.edit_message_text(
                    "✅ جستجو با موفقیت لغو شد",
                    call.message.chat.id,
                    call.message.message_id
                )
            
            # پایان چت
            elif call.data == "end_yes":
                partner = user.get("partner")
                if partner:
                    self.end_chat(uid, partner)
            
            elif call.data == "end_no":
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
            
            # گزارش تخلف
            elif call.data.startswith("rep_"):
                report_type = call.data.split("_")[1]
                
                if report_type == "cancel":
                    self.bot.delete_message(call.message.chat.id, call.message.message_id)
                    return
                
                partner = user.get("report_target")
                if not partner:
                    self.bot.answer_callback_query(call.id, "❌ خطا در گزارش")
                    return
                
                # ارسال گزارش به ادمین
                report_text = f"⚠️ <b>گزارش تخلف</b>\n\n"
                report_text += f"👤 گزارش دهنده: {user.get('name')} ({uid})\n"
                report_text += f"👥 گزارش شده: {db_u['users'].get(partner, {}).get('name', '?')} ({partner})\n"
                report_text += f"📌 نوع تخلف: {report_type}\n"
                report_text += f"🕒 زمان: {datetime.datetime.now().strftime('%H:%M %d/%m')}"
                
                try:
                    self.bot.send_message(
                        self.owner,
                        report_text,
                        reply_markup=types.InlineKeyboardMarkup().add(
                            types.InlineKeyboardButton("🚫 بن موقت", callback_data=f"admin_tempban_{partner}"),
                            types.InlineKeyboardButton("⛔ بن دائم", callback_data=f"admin_permban_{partner}")
                        )
                    )
                except Exception as e:
                    logger.error(f"خطا در ارسال گزارش: {e}")
                
                # افزایش شمارنده گزارش‌ها
                if partner in db_u["users"]:
                    db_u["users"][partner]["reports_received"] = db_u["users"][partner].get("reports_received", 0) + 1
                    self.db.write("users", db_u)
                
                self.bot.edit_message_text(
                    "✅ گزارش شما با موفقیت ثبت شد\n\n"
                    "تیم پشتیبانی به زودی بررسی خواهد کرد.",
                    call.message.chat.id,
                    call.message.message_id
                )
            
            # اشتراک‌گذاری آیدی
            elif call.data.startswith("id_share_"):
                action = call.data.split("_")[2]
                
                if action == "yes":
                    target = call.data.split("_")[3]
                    if target in db_u["users"]:
                        try:
                            # ارسال آیدی به درخواست کننده
                            self.bot.send_message(
                                target,
                                f"✅ هم‌صحبت شما موافقت کرد!\n\n"
                                f"👤 نام: {user.get('name')}\n"
                                f"🆔 آیدی: @{call.message.chat.username or uid}"
                            )
                            
                            # اطلاع به کاربر فعلی
                            self.bot.send_message(
                                uid,
                                f"✅ آیدی شما با موفقیت ارسال شد\n\n"
                                f"👤 به: {db_u['users'][target].get('name')}"
                            )
                        except Exception as e:
                            logger.error(f"خطا در اشتراک آیدی: {e}")
                
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
            
            # پاسخ به پیام ناشناس
            elif call.data.startswith("anon_reply_"):
                index = int(call.data.split("_")[2])
                db_m = self.db.read("messages")
                
                if uid in db_m["inbox"] and index < len(db_m["inbox"][uid]):
                    message = db_m["inbox"][uid][index]
                    user["state"] = "anon_reply"
                    user["anon_reply_target"] = message["from"]
                    self.db.write("users", db_u)
                    
                    self.bot.send_message(
                        uid,
                        f"📩 پاسخ به پیام:\n\n{message['text']}\n\n"
                        "پاسخ خود را بنویسید:"
                    )
            
            # تغییر نام
            elif call.data == "set_name":
                user["state"] = "change_name"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✏️ نام جدید خود را وارد کنید:")
            
            # تغییر سن
            elif call.data == "set_age":
                user["state"] = "change_age"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🔢 سن جدید خود را وارد کنید (بین ۱۲ تا ۹۹):")
            
            # خرید VIP
            elif call.data.startswith("vip_buy_"):
                duration = call.data.split("_")[2]
                
                if duration == "christmas":
                    if user.get("christmas_vip_taken", False):
                        self.bot.answer_callback_query(call.id, "❌ قبلاً از این پیشنهاد استفاده کرده‌اید!")
                        return
                    
                    # VIP رایگان کریسمس
                    self.add_vip(uid, "christmas", "VIP رایگان کریسمس")
                    user["christmas_vip_taken"] = True
                    self.db.write("users", db_u)
                    return
                
                price = self.vip_prices_coins.get(duration, 0)
                if user.get("coins", 0) < price:
                    self.bot.answer_callback_query(call.id, "❌ موجودی سکه کافی نیست!")
                    return
                
                # کسر سکه
                user["coins"] -= price
                self.db.write("users", db_u)
                
                # افزودن VIP
                self.add_vip(uid, duration, "خرید VIP")
            
            # مدیریت کلمات ممنوعه
            elif call.data.startswith("badwords_"):
                action = call.data.split("_")[1]
                
                if action == "add":
                    self.bot.send_message(uid, "📝 کلمه جدید را وارد کنید:")
                    user["admin_state"] = "badwords_add"
                elif action == "remove":
                    self.bot.send_message(uid, "📝 کلمه برای حذف را وارد کنید:")
                    user["admin_state"] = "badwords_remove"
                elif action == "reset":
                    db_badwords = self.db.read("badwords")
                    db_badwords["words"] = self.db.init_files()["badwords"]["words"]
                    self.db.write("badwords", db_badwords)
                    self.bot.answer_callback_query(call.id, "✅ کلمات به پیش‌فرض بازگشتند")
                
                self.db.write("users", db_u)
            
            # تنظیم قیمت‌های VIP
            elif call.data == "vip_prices_edit":
                db_prices = self.db.read("vip_prices")
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                for key in db_prices.keys():
                    kb.add(types.InlineKeyboardButton(f"تغییر {key}", callback_data=f"vip_price_edit_{key}"))
                
                self.bot.edit_message_text(
                    "<b>💰 تغییر قیمت‌های VIP</b>\n\nقیمت مورد نظر را انتخاب کنید:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=kb
                )
            
            # تغییر قیمت VIP خاص
            elif call.data.startswith("vip_price_edit_"):
                price_key = call.data.split("_")[3]
                user["admin_state"] = f"vip_price_edit_{price_key}"
                self.db.write("users", db_u)
                
                self.bot.send_message(
                    uid,
                    f"💰 قیمت جدید برای {price_key} را وارد کنید (سکه):"
                )
            
            # تغییر تنظیمات پیشرفته
            elif call.data == "settings_edit":
                db_settings = self.db.read("settings")
                
                kb = types.InlineKeyboardMarkup(row_width=2)
                for key in db_settings.keys():
                    kb.add(types.InlineKeyboardButton(f"تغییر {key}", callback_data=f"setting_edit_{key}"))
                
                self.bot.edit_message_text(
                    "<b>⚙️ تغییر تنظیمات پیشرفته</b>\n\nتنظیمات مورد نظر را انتخاب کنید:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=kb
                )
            
            # تغییر یک تنظیم خاص
            elif call.data.startswith("setting_edit_"):
                setting_key = call.data.split("_")[2]
                user["admin_state"] = f"setting_edit_{setting_key}"
                self.db.write("users", db_u)
                
                current_value = self.db.read("settings").get(setting_key, False)
                self.bot.send_message(
                    uid,
                    f"⚙️ تنظیم جدید برای {setting_key} را وارد کنید (فعلی: {'فعال' if current_value else 'غیرفعال'}):\n\n"
                    "مقادیر مجاز: true/false یا فعال/غیرفعال"
                )
            
            # گزارش‌های کاربران
            elif call.data.startswith("reports_"):
                report_type = call.data.split("_")[1]
                
                if report_type == "daily":
                    # گزارش روزانه
                    today = str(datetime.date.today())
                    db_u = self.db.read("users")
                    
                    reports_today = []
                    for u_id, u_data in db_u["users"].items():
                        if u_data.get("last_active_date") == today:
                            reports = u_data.get("reports_received", 0)
                            if reports > 0:
                                reports_today.append((u_id, u_data.get("name"), reports))
                    
                    reports_text = f"<b>📅 گزارش روزانه ({today})</b>\n\n"
                    if reports_today:
                        reports_text += "\n".join([
                            f"👤 {name} ({u_id}): {count} گزارش"
                            for u_id, name, count in sorted(reports_today, key=lambda x: -x[2])[:20]
                        ])
                    else:
                        reports_text += "⚠️ هیچ گزارشی امروز ثبت نشده"
                    
                    self.bot.edit_message_text(
                        reports_text,
                        call.message.chat.id,
                        call.message.message_id
                    )
                
                elif report_type == "weekly":
                    # گزارش هفتگی
                    today = datetime.date.today()
                    week_ago = today - datetime.timedelta(days=7)
                    
                    db_u = self.db.read("users")
                    
                    reports_week = []
                    for u_id, u_data in db_u["users"].items():
                        last_active = u_data.get("last_active_date")
                        if last_active and datetime.datetime.strptime(last_active, "%Y-%m-%d").date() >= week_ago:
                            reports = u_data.get("reports_received", 0)
                            if reports > 0:
                                reports_week.append((u_id, u_data.get("name"), reports))
                    
                    reports_text = f"<b>📆 گزارش هفتگی ({week_ago} تا {today})</b>\n\n"
                    if reports_week:
                        reports_text += "\n".join([
                            f"👤 {name} ({u_id}): {count} گزارش"
                            for u_id, name, count in sorted(reports_week, key=lambda x: -x[2])[:20]
                        ])
                    else:
                        reports_text += "⚠️ هیچ گزارشی در این هفته ثبت نشده"
                    
                    self.bot.edit_message_text(
                        reports_text,
                        call.message.chat.id,
                        call.message.message_id
                    )
                
                elif report_type == "full":
                    # گزارش کامل
                    db_u = self.db.read("users")
                    
                    reports_all = []
                    for u_id, u_data in db_u["users"].items():
                        reports = u_data.get("reports_received", 0)
                        if reports > 0:
                            reports_all.append((u_id, u_data.get("name"), reports))
                    
                    reports_text = "<b>📋 گزارش کامل کاربران</b>\n\n"
                    if reports_all:
                        reports_text += "\n".join([
                            f"👤 {name} ({u_id}): {count} گزارش"
                            for u_id, name, count in sorted(reports_all, key=lambda x: -x[2])[:50]
                        ])
                    else:
                        reports_text += "⚠️ هیچ گزارشی ثبت نشده"
                    
                    self.bot.edit_message_text(
                        reports_text,
                        call.message.chat.id,
                        call.message.message_id
                    )
            
            # بن کاربر توسط ادمین
            elif call.data.startswith("admin_"):
                action = call.data.split("_")[1]
                target = call.data.split("_")[2]
                
                if action == "tempban":
                    self.ban_temp(target, 1440, "تخلف گزارش شده توسط ادمین")
                    self.bot.answer_callback_query(call.id, f"✅ کاربر {target} بن موقت شد")
                elif action == "permban":
                    self.ban_perm(target, "تخلف گزارش شده توسط ادمین")
                    self.bot.answer_callback_query(call.id, f"✅ کاربر {target} بن دائم شد")
                
                # افزایش شمارنده گزارش‌های حل شده
                db_u = self.db.read("users")
                if target in db_u["users"]:
                    db_u["users"][target]["reports_resolved"] = db_u["users"][target].get("reports_resolved", 0) + 1
                    self.db.write("users", db_u)
                
                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=None
                )
            
            # بن خودکار
            elif call.data.startswith("auto_ban_"):
                action = call.data.split("_")[2]
                target = call.data.split("_")[3]
                
                if action == "pardon":
                    # بخشیدن کاربر
                    db_b = self.db.read("bans")
                    if target in db_b["permanent"]:
                        del db_b["permanent"][target]
                    if target in db_b["temporary"]:
                        del db_b["temporary"][target]
                    self.db.write("bans", db_b)
                    
                    try:
                        self.bot.send_message(
                            target,
                            "🎉 <b>بن شما لغو شد!</b>\n\n"
                            "تیم پشتیبانی پس از بررسی، بن شما را لغو کرده است.\n"
                            "مجددا می‌توانید از ربات استفاده کنید."
                        )
                    except:
                        pass
                    
                    self.bot.answer_callback_query(call.id, f"✅ کاربر {target} بخشیده شد")
                
                self.bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=None
                )

    def start_search(self, uid, sex_pref):
        """شروع جستجوی هم‌صحبت"""
        db_u = self.db.read("users")
        db_q = self.db.read("queue")
        
        # اگر کاربر از صف خارج شده
        if uid not in db_q["general"]:
            return
        
        user = db_u["users"].get(uid)
        if not user:
            return
        
        # جستجوی هم‌صحبت مناسب
        for candidate_id in db_q["general"]:
            if candidate_id == uid:
                continue
            
            candidate = db_u["users"].get(candidate_id)
            if not candidate:
                continue
            
            # بررسی تطابق جنسیت
            if sex_pref == "any" or candidate.get("sex") == user.get("search_pref"):
                # حذف از صف
                db_q["general"].remove(uid)
                db_q["general"].remove(candidate_id)
                self.db.write("queue", db_q)
                
                # تنظیم هم‌صحبت
                user["partner"] = candidate_id
                user["state"] = "chatting"
                candidate["partner"] = uid
                candidate["state"] = "chatting"
                self.db.write("users", db_u)
                
                # ذخیره چت فعال
                self.save_active_chat(uid, candidate_id)
                self.save_active_chat(candidate_id, uid)
                
                # ارسال پیام به کاربران
                try:
                    self.bot.send_message(
                        uid,
                        f"🎉 <b>هم‌صحبت پیدا شد!</b>\n\n"
                        f"👤 نام: {candidate.get('name')}\n"
                        f"🔞 سن: {candidate.get('age')}\n"
                        f"👫 جنسیت: {candidate.get('sex')}\n\n"
                        f"حالا می‌توانید چت کنید ✨",
                        reply_markup=self.kb_chatting()
                    )
                    
                    self.bot.send_message(
                        candidate_id,
                        f"🎉 <b>هم‌صحبت پیدا شد!</b>\n\n"
                        f"👤 نام: {user.get('name')}\n"
                        f"🔞 سن: {user.get('age')}\n"
                        f"👫 جنسیت: {user.get('sex')}\n\n"
                        f"حالا می‌توانید چت کنید ✨",
                        reply_markup=self.kb_chatting()
                    )
                except Exception as e:
                    logger.error(f"خطا در ارسال پیام شروع چت: {e}")
                
                return
        
        # اگر هم‌صحبت پیدا نشد، بعد از 30 ثانیه دوباره امتحان کن
        threading.Timer(30, self.start_search, args=[uid, sex_pref]).start()

    def run(self):
        """اجرای ربات"""
        try:
            # شروع وب سرور در ترد جداگانه
            Thread(target=run_web).start()
            
            # شروع چک‌رهای دوره‌ای
            self.periodic_checks()
            
            # شروع ربات
            self.bot.infinity_polling()
        except Exception as e:
            logger.critical(f"خطای بحرانی در اجرای ربات: {e}")
            raise

    def periodic_checks(self):
        """بررسی‌های دوره‌ای"""
        def check_temp_bans():
            while True:
                try:
                    db_b = self.db.read("bans")
                    now = datetime.datetime.now().timestamp()
                    updated = False
                    
                    for uid, data in list(db_b["temporary"].items()):
                        if data["end"] < now:
                            del db_b["temporary"][uid]
                            updated = True
                    
                    if updated:
                        self.db.write("bans", db_b)
                except Exception as e:
                    logger.error(f"خطا در بررسی بن‌های موقت: {e}")
                
                time.sleep(60)
        
        def check_active_chats():
            while True:
                try:
                    db_u = self.db.read("users")
                    updated = False
                    
                    for uid, user in db_u["users"].items():
                        if user.get("partner"):
                            partner = user["partner"]
                            if partner not in db_u["users"] or not db_u["users"][partner].get("partner"):
                                # اگر هم‌صحبت وجود ندارد یا هم‌صحبت را تنظیم نکرده
                                user["partner"] = None
                                updated = True
                                try:
                                    self.bot.send_message(
                                        uid,
                                        "⚠️ ارتباط با هم‌صحبت قطع شد!",
                                        reply_markup=self.kb_main(uid)
                                    )
                                except:
                                    pass
                    
                    if updated:
                        self.db.write("users", db_u)
                except Exception as e:
                    logger.error(f"خطا در بررسی چت‌های فعال: {e}")
                
                time.sleep(30)
        
        # شروع تردهای بررسی دوره‌ای
        Thread(target=check_temp_bans, daemon=True).start()
        Thread(target=check_active_chats, daemon=True).start()

# ==========================================
# اجرای ربات
# ==========================================
if __name__ == "__main__":
    bot_instance = ShadowTitanBot()
    bot_instance.run()
