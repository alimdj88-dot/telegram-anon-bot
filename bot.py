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
            "missions": "db_missions.json"
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
                    "reward": 50,
                    "type": "chat_count",
                    "target": 5
                },
                "available": [
                    {"name": "ارسال 5 پیام در چت", "reward": 50, "type": "chat_count", "target": 5},
                    {"name": "ارسال 10 پیام در چت", "reward": 100, "type": "chat_count", "target": 10},
                    {"name": "چت با 3 نفر مختلف", "reward": 80, "type": "unique_chats", "target": 3},
                    {"name": "چت با 5 نفر مختلف", "reward": 150, "type": "unique_chats", "target": 5},
                    {"name": "دعوت 2 نفر", "reward": 200, "type": "referrals", "target": 2},
                    {"name": "دعوت 5 نفر", "reward": 500, "type": "referrals", "target": 5},
                    {"name": "چرخاندن گردونه", "reward": 30, "type": "spin_wheel", "target": 1},
                    {"name": "بازدید از پروفایل 3 بار", "reward": 40, "type": "profile_views", "target": 3}
                ]
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
            except:
                logger.error(f"خطا در خواندن {key}")
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
        self.token = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
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
        self.vip_prices_coins = {
            "week": 500,
            "month": 1800,
            "3month": 5000,
            "6month": 9000,
            "year": 15000
        }

        # مدت‌های VIP به ثانیه
        self.vip_durations = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "3month": 90 * 24 * 3600,
            "6month": 180 * 24 * 3600,
            "year": 365 * 24 * 3600
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

        # بروزرسانی خودکار ماموریت روزانه
        self.auto_update_daily_mission()
        
        self.register_handlers()
        logger.info("Shadow Titan v42.0 شروع شد")

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
                "reward": mission["reward"],
                "type": mission["type"],
                "target": mission["target"]
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
        """افزودن VIP"""
        db_u = self.db.read("users")
        if uid not in db_u["users"]:
            return False
        now = datetime.datetime.now().timestamp()
        current_end = db_u["users"][uid].get("vip_end", 0)
        new_end = max(current_end, now) + self.vip_durations[duration_key]
        db_u["users"][uid]["vip_end"] = new_end
        self.db.write("users", db_u)
        
        try:
            end_date = datetime.datetime.fromtimestamp(new_end).strftime("%Y-%m-%d")
            duration_name = {
                "week": "۱ هفته",
                "month": "۱ ماه",
                "3month": "۳ ماه",
                "6month": "۶ ماه",
                "year": "۱ سال"
            }[duration_key]
            self.bot.send_message(uid, f"🎉 <b>تبریک! رنک VIP دریافت کردید</b>\n\n"
                                       f"مدت: {duration_name}\n"
                                       f"تا تاریخ: {end_date}\n"
                                       f"دلیل: {reason}\n\nمبارک باشد ✨")
        except Exception as e:
            logger.error(f"خطا در ارسال پیام VIP به {uid}: {e}")
        return True

    def add_coins(self, uid, amount, reason=""):
        """افزودن سکه"""
        db_u = self.db.read("users")
        if uid not in db_u["users"]:
            return False
        db_u["users"][uid]["coins"] = db_u["users"][uid].get("coins", 0) + amount
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
            reward = mission["reward"]
            self.add_coins(uid, reward, f"ماموریت روزانه: {mission['mission']}")
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
            self.bot.send_message(uid, f"🚫 <b>بن موقت {minutes} دقیقه</b>\n"
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

    def end_chat(self, a, b, msg="ترک کرد"):
        """پایان چت"""
        db_u = self.db.read("users")
        if a in db_u["users"]:
            db_u["users"][a]["partner"] = None
        if b in db_u["users"]:
            db_u["users"][b]["partner"] = None
        self.db.write("users", db_u)
        
        try:
            self.bot.send_message(a, "چت با موفقیت پایان یافت 🌙", reply_markup=self.kb_main(a))
        except:
            pass
        try:
            self.bot.send_message(b, f"هم‌صحبت شما چت را {msg} 🌙", reply_markup=self.kb_main(b))
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
        markup.add("📈 آمار کامل", "🛠 تعمیر و نگهداری")
        markup.add("🎖 گیفت VIP تکی", "🎖 گیفت VIP همگانی")
        markup.add("❌ حذف VIP", "📋 لیست VIP")
        markup.add("💰 اهدای سکه", "🎯 مدیریت ماموریت‌ها")
        markup.add("📁 دانلود دیتابیس", "🚫 لیست بن‌شده‌ها")
        markup.add("🔙 بازگشت به منو")
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
                end = db_b["temporary"][uid]["end"]
                if datetime.datetime.now().timestamp() < end:
                    rem = int((end - datetime.datetime.now().timestamp()) / 60)
                    self.bot.send_message(uid, f"🚫 <b>بن موقت هستید!</b>\n"
                                              f"زمان باقی‌مانده: {rem} دقیقه\n"
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
                        "christmas_free_taken": False,
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
                    "christmas_free_taken": False,
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
                    self.end_chat(uid, partner, "بلاک کرد")
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
                                self.end_chat(uid, partner, "بن دائم شد")
                            else:
                                self.ban_temp(uid, 1440, "فحاشی مکرر (بن ۲۴ ساعته)")
                                user["had_temp_ban"] = True
                                user["warns"] = 0
                                self.db.write("users", db_u)
                                self.report_auto_ban(uid, "فحاشی مکرر (اولین بار)", "بن ۲۴ ساعته")
                                self.end_chat(uid, partner, "بن ۲۴ ساعته شد")
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
                # شمارش برای ماموریت
                user["daily_profile_views"] = user.get("daily_profile_views", 0) + 1
                self.db.write("users", db_u)
                
                rank = "🎖 VIP" if self.is_vip(uid) else "⭐ عادی"
                vip_end = user.get("vip_end", 0)
                vip_status = f"تا {datetime.datetime.fromtimestamp(vip_end).strftime('%Y-%m-%d')}" if self.is_vip(uid) else "ندارید"
                
                profile_text = f"<b>👤 پروفایل شما</b>\n\n"
                profile_text += f"نام: {user.get('name', 'نامشخص')}\n"
                profile_text += f"جنسیت: {user.get('sex', 'نامشخص')}\n"
                profile_text += f"سن: {user.get('age', 'نامشخص')}\n"
                profile_text += f"رنک: {rank}\n"
                profile_text += f"VIP: {vip_status}\n"
                profile_text += f"💰 سکه: {user.get('coins', 0):,}\n"
                profile_text += f"👥 رفرال: {user.get('total_referrals', 0)} نفر\n"
                profile_text += f"⚠️ اخطار: {user.get('warns', 0)}/3"
                
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
                
                mission_text = f"<b>🎯 ماموریت روزانه</b>\n\n"
                mission_text += f"📋 ماموریت: {mission['mission']}\n"
                mission_text += f"🎁 پاداش: {mission['reward']:,} سکه\n\n"
                
                if completed:
                    mission_text += "✅ <b>تکمیل شده!</b>\n\nفردا ماموریت جدید منتظر شماست 🌟"
                else:
                    # نمایش پیشرفت
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
                
                kb = types.InlineKeyboardMarkup(row_width=1)
                
                for key, price in self.vip_prices_coins.items():
                    name = {
                        "week": "۱ هفته",
                        "month": "۱ ماه",
                        "3month": "۳ ماه",
                        "6month": "۶ ماه",
                        "year": "۱ سال"
                    }[key]
                    
                    status = "✅" if coins >= price else "🔒"
                    kb.add(types.InlineKeyboardButton(
                        f"{status} VIP {name} - {price:,} سکه",
                        callback_data=f"buy_vip_{key}"
                    ))
                
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

            # پنل مدیریت
            if uid == self.owner:
                if text == "📊 پنل مدیریت":
                    self.bot.send_message(uid, "<b>📊 پنل مدیریت پیشرفته</b>", 
                                        reply_markup=self.kb_admin())

                elif text == "📈 آمار کامل":
                    total = len(db_u["users"])
                    males = sum(1 for u in db_u["users"].values() if u.get("sex") == "آقا")
                    females = total - males
                    vips = sum(1 for uid_key in db_u["users"] if self.is_vip(uid_key))
                    total_coins = sum(u.get("coins", 0) for u in db_u["users"].values())
                    
                    stats_text = f"<b>📈 آمار کامل ربات</b>\n\n"
                    stats_text += f"👥 کل کاربران: {total:,}\n"
                    stats_text += f"👦 آقا: {males:,}\n"
                    stats_text += f"👧 خانم: {females:,}\n"
                    stats_text += f"🎖 VIP فعال: {vips:,}\n"
                    stats_text += f"💰 کل سکه‌ها: {total_coins:,}\n"
                    stats_text += f"🚫 بن دائم: {len(db_b.get('permanent', {})):,}\n"
                    stats_text += f"⏰ بن موقت: {len(db_b.get('temporary', {})):,}"
                    
                    self.bot.send_message(uid, stats_text)

                elif text == "🛠 تعمیر و نگهداری":
                    db_c["settings"]["maintenance"] = not db_c["settings"].get("maintenance", False)
                    self.db.write("config", db_c)
                    status = "🟢 فعال" if db_c["settings"]["maintenance"] else "🔴 غیرفعال"
                    self.bot.send_message(uid, f"حالت تعمیر و نگهداری: {status}")

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
                    active_vips = [u for u in db_u["users"] if self.is_vip(u)]
                    
                    if not active_vips:
                        self.bot.send_message(uid, "❌ هیچ کاربر VIP فعال وجود ندارد")
                    else:
                        vip_text = "<b>📋 لیست کاربران VIP فعال</b>\n\n"
                        for v in active_vips[:50]:  # محدود به 50 نفر اول
                            name = db_u["users"][v].get("name", "نامشخص")
                            end_date = datetime.datetime.fromtimestamp(
                                db_u["users"][v].get("vip_end", 0)
                            ).strftime("%Y-%m-%d")
                            vip_text += f"🆔 <code>{v}</code> - {name}\n📅 تا {end_date}\n\n"
                        
                        if len(active_vips) > 50:
                            vip_text += f"\n... و {len(active_vips) - 50} نفر دیگر"
                        
                        self.bot.send_message(uid, vip_text)

                elif text == "💰 اهدای سکه":
                    user["admin_state"] = "gift_coins_amount"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "💰 مقدار سکه را وارد کنید:")

                elif text == "🎯 مدیریت ماموریت‌ها":
                    db_m = self.db.read("missions")
                    current_mission = db_m["daily"]
                    
                    mission_text = f"<b>🎯 مدیریت ماموریت‌های روزانه</b>\n\n"
                    mission_text += f"<b>ماموریت امروز:</b>\n"
                    mission_text += f"📋 {current_mission['mission']}\n"
                    mission_text += f"🎁 پاداش: {current_mission['reward']:,} سکه\n"
                    mission_text += f"📅 تاریخ: {current_mission['date']}\n\n"
                    
                    kb = types.InlineKeyboardMarkup(row_width=1)
                    kb.add(types.InlineKeyboardButton("🔄 تغییر ماموریت امروز", 
                                                     callback_data="change_daily_mission"))
                    kb.add(types.InlineKeyboardButton("📋 مشاهده لیست ماموریت‌ها", 
                                                     callback_data="view_missions_list"))
                    kb.add(types.InlineKeyboardButton("➕ افزودن ماموریت جدید", 
                                                     callback_data="add_new_mission"))
                    
                    self.bot.send_message(uid, mission_text, reply_markup=kb)

                elif text == "📁 دانلود دیتابیس":
                    for file_name, file_path in self.db.files.items():
                        if os.path.exists(file_path):
                            try:
                                with open(file_path, 'rb') as f:
                                    self.bot.send_document(uid, f, caption=f"📄 {file_name}.json")
                            except Exception as e:
                                logger.error(f"خطا در ارسال فایل {file_name}: {e}")

                elif text == "🚫 لیست بن‌شده‌ها":
                    ban_text = "<b>🚫 لیست بن‌شده‌ها</b>\n\n"
                    kb = types.InlineKeyboardMarkup()
                    
                    if db_b.get("permanent"):
                        ban_text += "<b>بن دائم:</b>\n"
                        for ban_uid, reason in list(db_b["permanent"].items())[:20]:
                            name = db_u["users"].get(ban_uid, {}).get("name", "نامشخص")
                            ban_text += f"🆔 <code>{ban_uid}</code> - {name}\n💬 {reason}\n"
                            kb.add(types.InlineKeyboardButton(
                                f"🔓 بخشیدن {ban_uid}", 
                                callback_data=f"unban_perm_{ban_uid}"
                            ))
                        ban_text += "\n"
                    
                    if db_b.get("temporary"):
                        ban_text += "<b>بن موقت:</b>\n"
                        for ban_uid, data in list(db_b["temporary"].items())[:20]:
                            name = db_u["users"].get(ban_uid, {}).get("name", "نامشخص")
                            end_time = datetime.datetime.fromtimestamp(data["end"]).strftime("%Y-%m-%d %H:%M")
                            ban_text += f"🆔 <code>{ban_uid}</code> - {name}\n⏰ تا {end_time}\n\n"
                    
                    if not db_b.get("permanent") and not db_b.get("temporary"):
                        ban_text += "✅ هیچ کاربر بن‌شده‌ای وجود ندارد"
                    
                    self.bot.send_message(uid, ban_text, reply_markup=kb)

                # مدیریت state های ادمین
                admin_state = user.get("admin_state")
                
                if admin_state == "gift_vip_duration":
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

                elif admin_state == "gift_vip_all_duration":
                    duration_map = {
                        "۱ هفته": "week",
                        "۱ ماه": "month",
                        "۳ ماه": "3month",
                        "۶ ماه": "6month",
                        "۱ سال": "year"
                    }
                    
                    if text in duration_map:
                        user["gift_vip_all_duration"] = duration_map[text]
                        user["admin_state"] = "gift_vip_all_reason"
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, "📝 دلیل گیفت همگانی را بنویسید:")
                    return

                elif admin_state == "gift_vip_all_reason":
                    duration = user.get("gift_vip_all_duration")
                    reason = msg.text
                    
                    sent_count = 0
                    for target_uid in db_u["users"]:
                        if self.add_vip(target_uid, duration, reason):
                            sent_count += 1
                    
                    self.bot.send_message(uid, f"✅ گیفت VIP به {sent_count} کاربر ارسال شد", 
                                        reply_markup=self.kb_admin())
                    user["admin_state"] = None
                    self.db.write("users", db_u)
                    return

                elif admin_state == "remove_vip":
                    if msg.text.isdigit():
                        target_uid = msg.text
                        if target_uid in db_u["users"]:
                            db_u["users"][target_uid]["vip_end"] = 0
                            self.db.write("users", db_u)
                            try:
                                self.bot.send_message(target_uid, "❌ VIP شما توسط ادمین حذف شد")
                            except:
                                pass
                            self.bot.send_message(uid, f"✅ VIP از کاربر {target_uid} حذف شد", 
                                                reply_markup=self.kb_admin())
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
                                self.bot.send_message(uid, f"✅ {amount:,} سکه به {target_uid} اهدا شد", 
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
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🏠 منوی اصلی", reply_markup=self.kb_main(uid))

        # کال‌بک‌ها
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

                # یافتن هم‌صحبت
                potential_partners = [p for p in db_q["general"] if p != uid]
                
                # فیلتر بلاک‌ها
                potential_partners = [
                    p for p in potential_partners 
                    if uid not in db_u["users"].get(p, {}).get("blocks", []) 
                    and p not in user.get("blocks", [])
                ]

                # فیلتر جنسیت
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
                    
                    # حذف از صف
                    if uid in db_q["general"]:
                        db_q["general"].remove(uid)
                    if partner in db_q["general"]:
                        db_q["general"].remove(partner)
                    self.db.write("queue", db_q)

                    # اتصال
                    user["partner"] = partner
                    db_u["users"][partner]["partner"] = uid
                    self.db.write("users", db_u)

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
                
                tehran_time = datetime.datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")
                
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
                price = self.vip_prices_coins.get(vip_type, 0)
                coins = user.get("coins", 0)
                
                if coins < price:
                    self.bot.answer_callback_query(call.id, f"❌ سکه کافی ندارید! نیاز: {price:,}", show_alert=True)
                    return
                
                # کسر سکه
                user["coins"] = coins - price
                self.db.write("users", db_u)
                
                # افزودن VIP
                self.add_vip(uid, vip_type, "خرید با سکه")
                self.bot.answer_callback_query(call.id, "✅ VIP فعال شد!")

            # مدیریت ماموریت‌ها
            elif call.data == "change_daily_mission":
                if uid != self.owner:
                    return
                
                db_m = self.db.read("missions")
                new_mission = random.choice(db_m["available"])
                
                db_m["daily"] = {
                    "date": str(datetime.date.today()),
                    "mission": new_mission["name"],
                    "reward": new_mission["reward"],
                    "type": new_mission["type"],
                    "target": new_mission["target"]
                }
                self.db.write("missions", db_m)
                
                self.bot.answer_callback_query(call.id, "✅ ماموریت تغییر کرد")
                self.bot.edit_message_text(f"<b>✅ ماموریت جدید:</b>\n\n"
                                          f"📋 {new_mission['name']}\n"
                                          f"🎁 پاداش: {new_mission['reward']:,} سکه", 
                                          call.message.chat.id, call.message.message_id)

            elif call.data == "view_missions_list":
                if uid != self.owner:
                    return
                
                db_m = self.db.read("missions")
                missions_text = "<b>📋 لیست کامل ماموریت‌ها</b>\n\n"
                
                for i, m in enumerate(db_m["available"], 1):
                    missions_text += f"{i}. {m['name']}\n"
                    missions_text += f"   🎁 {m['reward']:,} سکه\n"
                    missions_text += f"   🎯 نوع: {m['type']}\n\n"
                
                self.bot.send_message(uid, missions_text)
                self.bot.answer_callback_query(call.id, "✅ لیست ارسال شد")

            elif call.data == "add_new_mission":
                if uid != self.owner:
                    return
                
                self.bot.answer_callback_query(call.id, "⚠️ این قابلیت به زودی اضافه می‌شود")

       def run(self):
        """اجرای ربات"""
        print("=" * 50)
        print("Shadow Titan v42.0 - Ultimate Edition")
        print("با سیستم ماموریت، رفرال و خرید VIP فعال شد.")
        print("=" * 50)
        
        # اجرای وب‌سرور در پس‌زمینه (برای اینکه ربات روی هاست نخوابد)
        try:
            server_thread = threading.Thread(target=run_web)
            server_thread.daemon = True
            server_thread.start()
            print("✅ Web Server started on port 8080")
        except Exception as e:
            logger.error(f"Web Server Error: {e}")

        # اتصال به تلگرام
        try:
            print("🚀 Bot is connecting to Telegram...")
            # این دستور ربات را روشن نگه می‌دارد
            self.bot.infinity_polling(skip_pending=True)
        except Exception as e:
            logger.error(f"Polling Error: {e}")
            print(f"❌ Error: {e}")

# ==========================================
# اجرای برنامه (نقطه شروع)
# ==========================================
if __name__ == "__main__":
    shadow_bot = ShadowTitanBot()
    shadow_bot.run()
