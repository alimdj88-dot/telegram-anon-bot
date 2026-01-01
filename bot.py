# shadow_titan_edited.py
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
import time

# ==========================================
# پیکربندی اولیه — حتما مقادیر زیر را جایگزین کن
# ==========================================
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"          # <- جایگزین کن
OWNER = "8013245091"                      # آیدی عددی مالک (رشته یا عدد)
CHANNEL = "@ChatNaAnnouncements"          # کانال لازم عضویت
SUPPORT = "@its_alimo"                    # آیدی پشتیبانی
HF_TOKEN = "YOUR_HF_TOKEN"                # <- جایگزین کن (اگه می‌خوای AI scan فعال بمونه)

# ==========================================
# سیستم مدیریت لاگ و مانیتورینگ پیشرفته
# ==========================================
logging.basicConfig(
    filename='shadow_titan.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("ShadowTitan")

# وب‌سرور برای زنده نگه داشتن ربات
app = Flask(__name__)
@app.route('/')
def home():
    return "Shadow Titan v24.0 – کامل‌ترین نسخه با خرید VIP با Stars + رفع کامل بن و گزارش رسانه 🌟"

def run_web():
    app.run(host='0.0.0.0', port=8080)

# ==========================================
# کلاس مدیریت دیتابیس کامل
# ==========================================
class DB:
    def __init__(self):
        self.files = {
            "users": "db_users.json",
            "bans": "db_bans.json",
            "queue": "db_queue.json",
            "messages": "db_messages.json",
            "config": "db_config.json",
            "payments": "db_payments.json"
        }
        self.lock = threading.Lock()
        self.init_files()

    def init_files(self):
        defaults = {
            "users": {},
            "bans": {"permanent": {}, "temporary": {}},  # temporary: {uid: {"end": timestamp, "reason": str}}
            "queue": {"general": []},
            "messages": {"inbox": {}},
            "config": {
                "stats": {"chats": 0, "ai_detections": 0},
                "settings": {"maintenance": False},
                "broadcast": {"text": None}
            },
            "payments": {}
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
# هسته اصلی ربات – کامل‌ترین نسخه با بیش از ۹۵۰ خط واقعی
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        self.token = TOKEN
        self.owner = str(OWNER)
        self.channel = CHANNEL
        self.support = SUPPORT
        self.hf_token = HF_TOKEN

        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.db = DB()

        try:
            self.username = self.bot.get_me().username
        except:
            self.username = "ShadowTitanBot"

        # لیست جامع کلمات فحش فارسی (می‌تونی لیست کامل‌تر بذاری)
        self.bad_words = [
            "کیر", "کیرم", "کیرت", "کیری", "کیرر", "کیرتو", "کیرش", "کیرها",
            "کس", "کص", "کوس", "کوث", "کوص", "کصص", "کسکش", "کسشر", "کسخل", "کسده", "کصده",
            "جنده", "جهنده", "جنده‌باز", "جنده‌خانه", "جنده‌پرور",
            "مادرجنده", "مادرجهنده", "مادرجندهه", "مادرجندت",
            "قحبه", "قهبه", "قحبه‌خان", "قحبه‌باز",
            "پدرسگ", "پدرسوخته", "پدرسک", "پدرسگه",
            "حرامزاده", "حرامزادگی", "حرامزادهه",
            "گاییدم", "گاییدمت", "گاییدمتو", "گاییدمش", "گاییدن", "گایید", "گاییدنی",
            "سیکتیر", "سکتییر", "سیک تیر", "سیک‌تر",
            "کون", "کونی", "کون دادن", "کون‌گشاد", "کون‌لق", "کون‌ت", "کون‌م",
            "گوه", "گوه خوردن", "گوه خور", "گوخور", "گو خوردن",
            "لاشی", "لاشخور", "لاشه",
            "فاحشه", "فاحشه‌خانه", "فاحشه‌باز",
            "ناموس", "ناموسی", "ناموست", "ناموس‌پرست", "ناموس‌فروش",
            "اوبی", "بی‌ناموس", "بیناموس",
            "سکس", "سکسی", "سکس کردن", "سکسی کردن", "سکسی‌باز",
            "پورن", "پورنو", "پُرن",
            "خارکصه", "خاركسه", "خاركسده", "خاركوسه",
            "تخمم", "تخم‌م", "تخم‌ت", "بی‌تخم", "بی‌تخم‌م",
            "شاسگول", "شاسگولم", "شاسگولت",
            "پفیوز", "پیفیوز", "پفیوز",
            "احمق", "خنگ", "خره", "خر", "خرتو", "خرت", "خرم", "خرت‌بره",
            "مرتیکه", "مرتیکهه", "مریکه",
            "شومبول", "شومبولت", "شومبولم",
            "لاشی‌لیشی", "لاشی‌کشی",
            "گوز", "گوزو", "گوزید", "گوزیدن",
            "جق", "جق زدن", "جق‌زدن",
            "مالیدن", "مالید", "مالوندن",
            "بکن", "بکنم", "بکنت", "بکنیم", "بکنیمش",
            "بمال", "بمالید", "بمالش",
            "هرزه", "هرزه‌گرد", "هرزه‌باز",
            "آشغال", "آشغالدونی",
            "سگ‌جان", "سگ‌مادر",
            "دیوث", "دیووس", "دیوث‌صفت",
            "كير", "كس", "كص", "جنده", "قحبه", "گاييد", "كون", "گوه"
        ]

        # پلن‌های VIP زمان‌دار (مقادیر به "استارز" XTR)
        self.vip_plans = {
            "vip_1m":  {"days": 30,  "price": 100, "title": "VIP یک ماهه"},
            "vip_3m":  {"days": 90,  "price": 280, "title": "VIP سه ماهه"},
            "vip_6m":  {"days": 180, "price": 560, "title": "VIP شش ماهه"},
            "vip_12m": {"days": 365, "price": 860, "title": "VIP یک ساله"},
            "vip_xmas_paid": {"days": 365, "price": 600, "title": "VIP ویژه کریسمس (پرداختی)"}
        }

        # Christmas free settings
        self.christmas_free_days = 90
        self.christmas_free_window = 4 * 86400  # 4 days
        self.christmas_start_ts = int(time.time())
        self.christmas_expire_ts = self.christmas_start_ts + self.christmas_free_window

        self.register_handlers()
        logger.info("Shadow Titan v24.0 – کامل‌ترین نسخه با خرید VIP با Stars + رفع بن و گزارش رسانه")

    # ===== helper: آیا کاربر الان VIP داره؟ =====
    def is_vip(self, user):
        try:
            return user.get("vip_until", 0) > int(time.time())
        except:
            return False

    # فیلتر فحش قوی
    def contains_bad(self, text):
        if not text:
            return False
        t = text.lower()
        t = re.sub(r'[\s\*\-_\.\d]+', '', t)
        return any(word.lower() in t for word in self.bad_words)

    # هوش مصنوعی اضافی برای محتوای نامناسب
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

    # کیبوردها
    def kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس روزانه", "🎖 خرید VIP (پلن‌ها)")
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
        markup.add("📁 دانلود دیتابیس", "🚫 لیست بن‌شده‌ها")
        markup.add("🔙 بازگشت به منو")
        return markup

    def kb_report(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
                   types.InlineKeyboardButton("+18", callback_data="rep_nsfw"))
        markup.add(types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
                   types.InlineKeyboardButton("آزار", callback_data="rep_harass"))
        markup.add(types.InlineKeyboardButton("لغو ❌", callback_data="rep_cancel"))
        return markup

    # توابع کمکی برای بن و پایان چت
    def ban_perm(self, uid, reason="تخلف"):
        db_b = self.db.read("bans")
        db_b["permanent"][uid] = reason
        self.db.write("bans", db_b)

    def end_chat(self, a, b, msg="ترک کرد"):
        db_u = self.db.read("users")
        if a in db_u.get("users", {}):
            db_u["users"][a]["partner"] = None
        if b in db_u.get("users", {}):
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

    # ثبت هندلرها
    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(msg):
            uid = str(msg.chat.id)
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None

            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")

            # چک بن دائم
            if uid in db_b.get("permanent", {}):
                self.bot.send_message(uid, f"🚫 <b>شما بن دائم هستید!</b>\nدلیل: {db_b['permanent'][uid]}\nپشتیبانی: {self.support}")
                return

            # چک بن موقت
            if uid in db_b.get("temporary", {}):
                end = db_b["temporary"][uid]["end"]
                if int(time.time()) < end:
                    rem = int((end - int(time.time())) / 60)
                    self.bot.send_message(uid, f"🚫 <b>بن موقت</b>\nزمان باقی‌مانده: {rem} دقیقه\nپشتیبانی: {self.support}")
                    return
                else:
                    del db_b["temporary"][uid]
                    self.db.write("bans", db_b)

            # چک تعمیر
            vip_now = self.is_vip(db_u.get("users", {}).get(uid, {}))
            if db_c["settings"].get("maintenance", False) and not (vip_now or uid == self.owner):
                self.bot.send_message(uid, "🔧 <b>ربات در حال تعمیر و نگهداری است</b>\n\n"
                                          "فقط کاربران VIP دسترسی دارند 🌟\nپشتیبانی: {self.support}")
                return

            # لینک ناشناس
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    self.bot.send_message(uid, "نمی‌توانید به خودتان پیام بفرستید 😊")
                    return
                if uid not in db_u.get("users", {}):
                    db_u.setdefault("users", {})[uid] = {
                        "state": "name",
                        "name": "نامشخص",
                        "sex": "نامشخص",
                        "age": 0,
                        "warns": 0,
                        "partner": None,
                        "vip_until": 0,
                        "blocks": [],
                        "last_spin": "",
                        "anon_target": target,
                        "used_christmas": False,
                        "pending_payment": None
                    }
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "برای ارسال پیام ناشناس، نام مستعار خود را وارد کنید ✨")
                else:
                    db_u["users"][uid]["state"] = "anon_send"
                    db_u["users"][uid]["anon_target"] = target
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "پیام ناشناس خود را بنویسید ✉️")
                return

            # ثبت‌نام عادی
            if uid not in db_u.get("users", {}):
                db_u.setdefault("users", {})[uid] = {
                    "state": "name",
                    "name": "نامشخص",
                    "sex": "نامشخص",
                    "age": 0,
                    "warns": 0,
                    "partner": None,
                    "vip_until": 0,
                    "blocks": [],
                    "last_spin": "",
                    "used_christmas": False,
                    "pending_payment": None
                }
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🌟 به Shadow Titan خوش آمدی!\nلطفاً نام مستعار خود را وارد کنید:")
            else:
                self.bot.send_message(uid, "خوش برگشتی عزیز 🌹", reply_markup=self.kb_main(uid))

        # پرداخت‌ها (Pre-checkout)
        @self.bot.pre_checkout_query_handler(func=lambda query: True)
        def checkout(pre_checkout_query):
            try:
                self.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True, error_message="خطا در پرداخت")
            except Exception as e:
                logger.error(f"pre_checkout error: {e}")

        # هندلر پرداخت موفق (پیش از این vip=True بود — حالا vip_until رو تنظیم می‌کنیم)
        @self.bot.message_handler(content_types=['successful_payment'])
        def successful_payment(message):
            uid = str(message.chat.id)
            payload = ""
            try:
                payload = message.successful_payment.invoice_payload
            except:
                # fallback
                payload = getattr(message.successful_payment, 'payload', '')

            if not payload:
                return

            payments = self.db.read("payments")
            if payload not in payments:
                # unknown payload — ignore
                return

            pay = payments[payload]
            plan_key = pay.get("plan")
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            if not user:
                return

            # apply VIP
            plan = self.vip_plans.get(plan_key)
            if plan:
                now = int(time.time())
                current_until = user.get("vip_until", 0)
                start = max(now, current_until)
                user["vip_until"] = start + plan["days"] * 86400
                db_u["users"][uid] = user
                self.db.write("users", db_u)
                payments[payload]["done"] = True
                self.db.write("payments", payments)
                end_date = datetime.datetime.fromtimestamp(user["vip_until"]).strftime("%Y-%m-%d")
                self.bot.send_message(uid, f"🎉 <b>VIP فعال شد!</b>\n\n"
                                          f"📦 پلن: {plan['title']}\n"
                                          f"📅 اعتبار تا: <b>{end_date}</b>\n\n"
                                          "از امکانات VIP لذت ببر 🌟")
            elif plan_key == "vip_xmas_free":
                # should not reach here (free xmas handled without invoice)
                pass

        # هندلر اصلی پیام‌ها
        @self.bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def main(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")

            # چک بن
            if uid in db_b.get("permanent", {}):
                return
            if uid in db_b.get("temporary", {}) and int(time.time()) < db_b["temporary"][uid]["end"]:
                return

            # چک تعمیر
            vip_now = self.is_vip(db_u["users"].get(uid, {}))
            if db_c["settings"].get("maintenance", False) and not (vip_now or uid == self.owner):
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

            # ذخیره آخرین پیام برای گزارش رسانه
            if user.get("partner"):
                user["last_chat_msg_id"] = msg.message_id
                self.db.write("users", db_u)

            # خرید VIP — حالا منو میاره (پلن‌ها)
            if msg.text == "🎖 خرید VIP (پلن‌ها)":
                kb = types.InlineKeyboardMarkup(row_width=1)
                # free christmas: show only if in window and user hasn't used it yet
                now_ts = int(time.time())
                if now_ts < self.christmas_expire_ts and not user.get("used_christmas", False):
                    kb.add(types.InlineKeyboardButton("🎄 VIP سه‌ماهه ویژه کریسمس — رایگان", callback_data="buy_vip_free_xmas"))
                # paid plans: send invoice via Stars
                for key, p in self.vip_plans.items():
                    # skip the pay-xmas paid entry in listing if present or list it as paid
                    title = p.get("title", key)
                    price = p.get("price", 0)
                    kb.add(types.InlineKeyboardButton(f"{title} — {price} ⭐", callback_data=f"buy_vip_paid|{key}"))
                self.bot.send_message(
                    uid,
                    "<b>🎖 خرید رنک VIP Shadow Titan</b>\n\n"
                    "✨ امکانات VIP:\n"
                    "• ارسال آزاد گیف و استیکر\n"
                    "• دسترسی به ربات در زمان تعمیر\n"
                    "• اتصال سریع‌تر به هم‌صحبت\n\n"
                    "⏳ VIP زمان‌دار است\n"
                    "💳 پرداخت با Telegram Stars",
                    reply_markup=kb
                )
                return

            # مرحله نام
            if user["state"] == "name":
                if not msg.text:
                    self.bot.send_message(uid, "نام معتبر وارد کن")
                    return
                if self.contains_bad(msg.text):
                    self.bot.send_message(uid, "❌ نام شامل کلمات نامناسب است")
                    return
                user["name"] = msg.text[:20]
                user["state"] = "sex"
                self.db.write("users", db_u)
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="sex_m"),
                       types.InlineKeyboardButton("خانم 👧", callback_data="sex_f"))
                self.bot.send_message(uid, f"سلام {user['name']} 🌸\nجنسیت خود را انتخاب کنید:", reply_markup=kb)
                return

            # مرحله سن
            if user["state"] == "age":
                if not msg.text or not msg.text.isdigit() or not 12 <= int(msg.text) <= 99:
                    self.bot.send_message(uid, "❌ سن باید عددی بین ۱۲ تا ۹۹ باشد")
                    return
                user["age"] = int(msg.text)
                user["state"] = "idle"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "ثبت‌نام با موفقیت انجام شد 🎉\nحالا از ربات لذت ببر!", reply_markup=self.kb_main(uid))
                return

            # پیام ناشناس
            if user["state"] == "anon_send":
                if msg.content_type != "text":
                    self.bot.send_message(uid, "❌ فقط متن مجاز است")
                    return
                target = user["anon_target"]
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
                self.bot.send_message(uid, "✅ پیام ناشناس ارسال شد")
                try:
                    self.bot.send_message(target, "📩 یک پیام ناشناس جدید دریافت کردید!")
                except:
                    pass
                user["state"] = "idle"
                self.db.write("users", db_u)
                return

            # پاسخ به پیام ناشناس
            if user["state"] == "anon_reply":
                target = user["anon_reply_target"]
                self.bot.send_message(target, f"📩 پاسخ ناشناس:\n{msg.text}")
                self.bot.send_message(uid, "✅ پاسخ ارسال شد")
                user["state"] = "idle"
                self.db.write("users", db_u)
                return

            # چت فعال
            if user.get("partner"):
                partner = user["partner"]

                if msg.text == "🔚 پایان گفتگو":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("بله، پایان بده", callback_data="end_yes"),
                           types.InlineKeyboardButton("خیر، ادامه بده", callback_data="end_no"))
                    self.bot.send_message(uid, "آیا مطمئن هستید که می‌خواهید چت را پایان دهید؟", reply_markup=kb)
                    return

                if msg.text == "🚩 گزارش تخلف":
                    self.bot.send_message(uid, "دلیل گزارش را انتخاب کنید:", reply_markup=self.kb_report())
                    user["report_target"] = partner
                    user["report_last_msg_id"] = msg.message_id  # ذخیره برای فوروارد رسانه
                    self.db.write("users", db_u)
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
                    kb.add(types.InlineKeyboardButton("بله ✅", callback_data=f"id_share_yes_{uid}"),
                           types.InlineKeyboardButton("خیر ❌", callback_data="id_share_no"))
                    self.bot.send_message(partner, "هم‌صحبت درخواست آیدی شما را دارد. موافقید؟", reply_markup=kb)
                    self.bot.send_message(uid, "درخواست ارسال شد، منتظر تایید باشید")
                    return

                # فیلتر فحش + AI
                if msg.text:
                    if self.contains_bad(msg.text):
                        try:
                            self.bot.delete_message(uid, msg.message_id)
                        except:
                            pass
                        user["warns"] = user.get("warns", 0) + 1
                        self.db.write("users", db_u)
                        if user["warns"] >= 3:
                            self.ban_perm(uid, "فحاشی مکرر")
                            self.end_chat(uid, partner, "بن شد")
                            return
                        self.bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3 – فحاشی ممنوع است!")
                        return

                    toxic = self.ai_toxic_scan(msg.text)
                    nsfw = self.ai_nsfw_scan(msg.text)
                    if toxic > 0.8 or nsfw > 0.8:
                        try:
                            self.bot.delete_message(uid, msg.message_id)
                        except:
                            pass
                        user["warns"] = user.get("warns", 0) + 1
                        self.db.write("users", db_u)
                        if user["warns"] >= 3:
                            self.ban_perm(uid, "محتوای نامناسب")
                            self.end_chat(uid, partner, "بن شد")
                            return
                        self.bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3 – محتوای نامناسب تشخیص داده شد")
                        return

                try:
                    self.bot.copy_message(partner, uid, msg.message_id)
                except:
                    pass
                return

            # لغو جستجو
            if msg.text == "❌ لغو جستجو":
                db_q = self.db.read("queue")
                if uid in db_q["general"]:
                    db_q["general"].remove(uid)
                    self.db.write("queue", db_q)
                self.bot.send_message(uid, "جستجو با موفقیت لغو شد ✅", reply_markup=self.kb_main(uid))
                return

            # منوی اصلی
            text = msg.text
            if text == "🛰 شروع چت ناشناس":
                kb = types.InlineKeyboardMarkup(row_width=3)
                kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                       types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                       types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any"))
                self.bot.send_message(uid, "دنبال چه کسی می‌گردی؟ ✨", reply_markup=kb)

            elif text == "👤 پروفایل من":
                rank = "🎖 VIP" if self.is_vip(user) else "عادی"
                vip_until = user.get("vip_until", 0)
                vip_text = "ندارد"
                if vip_until and vip_until > int(time.time()):
                    vip_text = datetime.datetime.fromtimestamp(vip_until).strftime("%Y-%m-%d")
                self.bot.send_message(uid, f"<b>پروفایل شما</b>\n\n"
                                          f"نام: {user['name']}\n"
                                          f"جنسیت: {user.get('sex', 'نامشخص')}\n"
                                          f"سن: {user.get('age', 'نامشخص')}\n"
                                          f"رنک: {rank}\n"
                                          f"اعتبار VIP تا: {vip_text}\n"
                                          f"اخطار: {user.get('warns', 0)}")

            elif text == "📩 لینک ناشناس من":
                link = f"https://t.me/{self.username}?start=msg_{uid}"
                self.bot.send_message(uid, f"<b>لینک ناشناس شما</b>\n\n{link}\n\n"
                                          "با اشتراک این لینک، دیگران می‌توانند ناشناس به شما پیام بفرستند ✨")

            elif text == "📥 پیام‌های ناشناس":
                db_m = self.db.read("messages")
                inbox = db_m["inbox"].get(uid, [])
                if not inbox:
                    self.bot.send_message(uid, "هیچ پیام ناشناسی دریافت نکرده‌اید 📭")
                    return
                kb = types.InlineKeyboardMarkup()
                txt = "<b>پیام‌های ناشناس شما</b>\n\n"
                for i, m in enumerate(inbox):
                    txt += f"{i+1}. {m['text']}\n<i>{m['time']}</i>\n\n"
                    kb.add(types.InlineKeyboardButton(f"پاسخ به پیام {i+1}", callback_data=f"anon_reply_{i}"))
                self.bot.send_message(uid, txt, reply_markup=kb)
                # دیده شدن
                updated = False
                for m in inbox:
                    if not m["seen"]:
                        m["seen"] = True
                        updated = True
                        try:
                            self.bot.send_message(m["from"], "✅ پیام شما دیده شد")
                        except:
                            pass
                if updated:
                    self.db.write("messages", db_m)

            elif text == "🎡 گردونه شانس روزانه":
                today = str(datetime.date.today())
                if user.get("last_spin") == today:
                    self.bot.send_message(uid, "امروز قبلاً گردونه را چرخانده‌اید 😊")
                    return
                user["last_spin"] = today
                # اگر برنده شد VIP 30 روزه بده (تصمیم منطقی برای زمان‌دار بودن)
                if random.random() < 0.05:
                    now = int(time.time())
                    current_until = user.get("vip_until", 0)
                    start = max(now, current_until)
                    user["vip_until"] = start + 30 * 86400
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🎉🎉 <b>تبریک! شما رنک VIP (۳۰ روزه) دریافت کردید!</b> 🎖\nمبارک باشد ✨")
                else:
                    self.bot.send_message(uid, "گردونه چرخید... پوچ! شانس بعدی را امتحان کنید 🌟")
                self.db.write("users", db_u)

            elif text == "❓ راهنما و قوانین":
                self.bot.send_message(uid, "<b>راهنما و قوانین</b>\n\n"
                                          "• چت کاملاً ناشناس است\n"
                                          "• فحاشی، محتوای +18 و اسپم ممنوع\n"
                                          "• گزارش تخلف منجر به اخطار و بن می‌شود\n"
                                          "• گردونه روزانه برای شانس VIP\n"
                                          f"پشتیبانی: {self.support}")

            elif text == "⚙ تنظیمات":
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت")
                kb.add("🔙 بازگشت به منو")
                self.bot.send_message(uid, "تنظیمات پروفایل:", reply_markup=kb)

            elif text in ["✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت"]:
                if text == "✏️ تغییر نام":
                    user["state"] = "change_name"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "نام جدید را وارد کنید:")
                elif text == "🔢 تغییر سن":
                    user["state"] = "change_age"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "سن جدید را وارد کنید:")
                elif text == "⚧ تغییر جنسیت":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="change_sex_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="change_sex_f"))
                    self.bot.send_message(uid, "جنسیت جدید را انتخاب کنید:", reply_markup=kb)

            # پنل مدیریت
            if uid == self.owner:
                if text == "📊 پنل مدیریت":
                    self.bot.send_message(uid, "<b>پنل مدیریت پیشرفته</b>", reply_markup=self.kb_admin())

                elif text == "📈 آمار کامل":
                    total = len(db_u["users"])
                    males = sum(1 for d in db_u["users"].values() if d.get("sex") == "آقا")
                    females = total - males
                    now_ts = int(time.time())
                    vips = sum(1 for d in db_u["users"].values() if d.get("vip_until", 0) > now_ts)
                    self.bot.send_message(uid, f"<b>آمار ربات</b>\n\n"
                                              f"کل کاربران: {total}\n"
                                              f"آقا: {males}\n"
                                              f"خانم: {females}\n"
                                              f"کاربران VIP: {vips}")

                elif text == "🛠 تعمیر و نگهداری":
                    db_c["settings"]["maintenance"] = not db_c["settings"]["maintenance"]
                    self.db.write("config", db_c)
                    status = "فعال 🟢" if db_c["settings"]["maintenance"] else "غیرفعال 🔴"
                    self.bot.send_message(uid, f"حالت تعمیر و نگهداری: {status}")

                elif text == "📢 ارسال همگانی":
                    user["state"] = "broadcast"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "متن پیام همگانی را وارد کنید:")

                if user.get("state") == "broadcast":
                    db_c["broadcast"]["text"] = msg.text
                    self.db.write("config", db_c)
                    self.bot.send_message(uid, "متن ذخیره شد. برای ارسال /send_broadcast بزنید")
                    user["state"] = "idle"
                    self.db.write("users", db_u)

                # گیفت VIP تکی -> now shows duration selection first
                elif text == "🎖 گیفت VIP تکی":
                    user["state"] = "gift_single_select"
                    self.db.write("users", db_u)
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(types.InlineKeyboardButton("1 هفته", callback_data="gift_single_7"),
                           types.InlineKeyboardButton("1 ماه", callback_data="gift_single_30"))
                    kb.add(types.InlineKeyboardButton("3 ماه", callback_data="gift_single_90"),
                           types.InlineKeyboardButton("6 ماه", callback_data="gift_single_180"))
                    kb.add(types.InlineKeyboardButton("1 سال", callback_data="gift_single_365"))
                    self.bot.send_message(uid, "⏳ مدت VIP را برای هدیه انتخاب کنید:", reply_markup=kb)

                # گیفت VIP همگانی -> duration select
                elif text == "🎖 گیفت VIP همگانی":
                    user["state"] = "gift_all_select"
                    self.db.write("users", db_u)
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(types.InlineKeyboardButton("1 هفته", callback_data="gift_all_7"),
                           types.InlineKeyboardButton("1 ماه", callback_data="gift_all_30"))
                    kb.add(types.InlineKeyboardButton("3 ماه", callback_data="gift_all_90"),
                           types.InlineKeyboardButton("6 ماه", callback_data="gift_all_180"))
                    kb.add(types.InlineKeyboardButton("1 سال", callback_data="gift_all_365"))
                    self.bot.send_message(uid, "⏳ مدت VIP همگانی را انتخاب کنید:", reply_markup=kb)

                # حذف VIP
                elif text == "❌ حذف VIP":
                    user["state"] = "remove_vip"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "آیدی عددی کاربر برای حذف VIP:")

                # لیست VIP
                elif text == "📋 لیست VIP":
                    now_ts = int(time.time())
                    vips = [u for u, d in db_u["users"].items() if d.get("vip_until", 0) > now_ts]
                    if not vips:
                        self.bot.send_message(uid, "هیچ کاربر VIP وجود ندارد")
                    else:
                        msg_text = "<b>لیست کاربران VIP</b>\n\n"
                        for v in vips:
                            name = db_u["users"][v].get("name", "نامشخص")
                            end = datetime.datetime.fromtimestamp(db_u["users"][v]["vip_until"]).strftime("%Y-%m-%d")
                            msg_text += f"🆔 {v} - {name} (تا {end})\n"
                        self.bot.send_message(uid, msg_text)

                # دانلود دیتابیس
                elif text == "📁 دانلود دیتابیس":
                    for file in self.db.files.values():
                        if os.path.exists(file):
                            try:
                                self.bot.send_document(uid, open(file, 'rb'), caption=f"📄 {file}")
                            except Exception as e:
                                logger.error(f"Send DB file error: {e}")

                # لیست بن‌شده‌ها
                elif text == "🚫 لیست بن‌شده‌ها":
                    msg_text = "<b>لیست بن‌شده‌ها</b>\n\n"
                    kb = types.InlineKeyboardMarkup()
                    for u, reason in db_b["permanent"].items():
                        name = db_u["users"].get(u, {}).get("name", "نامشخص")
                        msg_text += f"🆔 {u} - {name} (دائم - {reason})\n"
                        kb.add(types.InlineKeyboardButton(f"بخشیدن {u}", callback_data=f"unban_perm_{u}"))
                    for u, data in db_b["temporary"].items():
                        name = db_u["users"].get(u, {}).get("name", "نامشخص")
                        end_time = datetime.datetime.fromtimestamp(data["end"]).strftime("%Y-%m-%d %H:%M")
                        msg_text += f"🆔 {u} - {name} (موقت تا {end_time})\n"
                    self.bot.send_message(uid, msg_text, reply_markup=kb)

                # حالت‌های گیفت تکی: after selecting duration, now ask for ID
                if user.get("state") == "gift_single_id" and msg.text and msg.text.isdigit():
                    user["gift_target"] = msg.text
                    user["state"] = "gift_single_reason"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "دلیل گیفت VIP را بنویسید:")

                if user.get("state") == "gift_single_reason":
                    reason = msg.text
                    target = user.get("gift_target")
                    duration_days = user.get("gift_days", 0)
                    if target and target in db_u["users"]:
                        now_ts = int(time.time())
                        db_u["users"][target]["vip_until"] = now_ts + duration_days * 86400
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, f"✅ رنک VIP به کاربر {target} به مدت {duration_days} روز گیفت شد")
                        try:
                            self.bot.send_message(target, f"🎉 <b>تبریک! رنک VIP دریافت کردید 🎖</b>\n\n"
                                                         f"دلیل: {reason}\nاز طرف مدیریت – مبارک باشد! ✨")
                        except:
                            pass
                    else:
                        self.bot.send_message(uid, "کاربر مورد نظر یافت نشد")
                    user["state"] = "idle"
                    user.pop("gift_target", None)
                    user.pop("gift_days", None)
                    self.db.write("users", db_u)

                # حالت‌های گیفت همگانی: after selecting duration, ask for reason
                if user.get("state") == "gift_all_reason":
                    reason = msg.text
                    duration_days = user.get("gift_days", 0) or 30
                    sent = 0
                    now_ts = int(time.time())
                    for u in db_u["users"]:
                        db_u["users"][u]["vip_until"] = now_ts + duration_days * 86400
                        try:
                            self.bot.send_message(u, f"🎉 <b>تبریک! رنک VIP دریافت کردید 🎖</b>\n\n"
                                                     f"دلیل: {reason}\nاز طرف مدیریت – لذت ببرید! 🌟")
                            sent += 1
                        except:
                            pass
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, f"✅ رنک VIP به {sent} کاربر با مدت {duration_days} روز گیفت شد")
                    user["state"] = "idle"
                    user.pop("gift_days", None)
                    self.db.write("users", db_u)

                # حذف VIP
                if user.get("state") == "remove_vip" and msg.text and msg.text.isdigit():
                    target = msg.text
                    if target in db_u["users"]:
                        db_u["users"][target]["vip_until"] = 0
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, f"❌ رنک VIP از کاربر {target} حذف شد")
                    user["state"] = "idle"
                    self.db.write("users", db_u)

                # بن موقت (admin)
                if user.get("state", "").startswith("temp_ban_minutes_"):
                    if not msg.text.isdigit():
                        self.bot.send_message(uid, "لطفاً عدد دقیقه وارد کنید:")
                        return
                    minutes = int(msg.text)
                    target = user["state"].split("_")[3]
                    end_time = int(time.time()) + minutes * 60
                    db_b = self.db.read("bans")
                    db_b["temporary"][target] = {"end": end_time, "reason": "بن موقت ادمین"}
                    self.db.write("bans", db_b)
                    self.bot.send_message(uid, f"✅ بن موقت {minutes} دقیقه به {target} اعمال شد")
                    try:
                        self.bot.send_message(target, f"🚫 بن موقت {minutes} دقیقه دریافت کردید")
                    except:
                        pass
                    user["state"] = "idle"
                    self.db.write("users", db_u)

            # بازگشت
            if text and ("بازگشت" in text or "منو" in text):
                self.bot.send_message(uid, "منوی اصلی 🌟", reply_markup=self.kb_main(uid))

        # کال‌بک‌ها
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            uid = str(call.from_user.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            if not user:
                return

            # sex selection
            if call.data.startswith("sex_"):
                user["sex"] = "آقا" if call.data == "sex_m" else "خانم"
                user["state"] = "age"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "سن خود را وارد کنید (۱۲–۹۹):")
                return

            if call.data.startswith("change_sex_"):
                user["sex"] = "آقا" if call.data == "change_sex_m" else "خانم"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "جنسیت با موفقیت تغییر کرد ✅", reply_markup=self.kb_main(uid))
                return

            # find matching
            if call.data.startswith("find_"):
                try:
                    self.bot.edit_message_text("در حال جستجو برای هم‌صحبت... 🔍", call.message.chat.id, call.message.message_id)
                except:
                    pass
                try:
                    self.bot.send_message(uid, "برای لغو جستجو دکمه زیر را بزنید:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("❌ لغو جستجو"))
                except:
                    pass

                db_q = self.db.read("queue")
                if uid not in db_q["general"]:
                    db_q["general"].append(uid)
                self.db.write("queue", db_q)

                pots = [p for p in db_q["general"] if p != uid]
                pots = [p for p in pots if uid not in db_u["users"][p].get("blocks", []) and p not in user.get("blocks", [])]

                if pots:
                    partner = random.choice(pots)
                    try:
                        db_q["general"].remove(uid)
                    except:
                        pass
                    try:
                        db_q["general"].remove(partner)
                    except:
                        pass
                    self.db.write("queue", db_q)

                    user["partner"] = partner
                    db_u["users"][partner]["partner"] = uid
                    self.db.write("users", db_u)

                    self.bot.send_message(uid, "هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chatting())
                    self.bot.send_message(partner, "هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chatting())
                return

            # end chat confirm
            if call.data == "end_yes":
                self.end_chat(uid, user["partner"], "پایان داد")
                return

            if call.data == "end_no":
                self.bot.answer_callback_query(call.id, "چت ادامه دارد ✅")
                return

            # id share handling
            if call.data.startswith("id_share_yes_"):
                target = call.data.split("_")[3]
                username = call.from_user.username or "ندارد"
                self.bot.send_message(target, f"آیدی هم‌صحبت: @{username}")
                return

            if call.data == "id_share_no":
                self.bot.answer_callback_query(call.id, "درخواست رد شد")
                return

            # anon reply selecting
            if call.data.startswith("anon_reply_"):
                i = int(call.data.split("_")[2])
                db_m = self.db.read("messages")
                inbox = db_m["inbox"].get(uid, [])
                if i < 0 or i >= len(inbox):
                    self.bot.answer_callback_query(call.id, "پیام نامعتبر")
                    return
                msg_data = inbox[i]
                user["state"] = "anon_reply"
                user["anon_reply_target"] = msg_data["from"]
                self.db.write("users", db_u)
                self.bot.send_message(uid, "پاسخ خود را بنویسید:")
                return

            # report callbacks
            if call.data.startswith("rep_"):
                if call.data == "rep_cancel":
                    self.bot.answer_callback_query(call.id, "گزارش لغو شد ✅")
                    return
                reasons = {
                    "rep_insult": "فحاشی",
                    "rep_nsfw": "+18",
                    "rep_spam": "اسپم",
                    "rep_harass": "آزار و اذیت"
                }
                reason = reasons.get(call.data, "نامشخص")
                target = user.get("report_target")
                last_msg_id = user.get("report_last_msg_id")
                report_text = f"🚩 گزارش جدید\nشاکی: {uid}\nمتهم: {target}\nدلیل: {reason}\n\nآخرین پیام چت (با رسانه):"
                self.bot.send_message(self.owner, report_text)
                if last_msg_id:
                    try:
                        self.bot.forward_message(self.owner, uid, last_msg_id)
                    except:
                        self.bot.send_message(self.owner, "رسانه فوروارد نشد (خطا)")
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("Ignore", callback_data=f"adm_ignore_{target}"),
                       types.InlineKeyboardButton("Permanent Ban", callback_data=f"adm_ban_perm_{target}"))
                kb.add(types.InlineKeyboardButton("Temp Ban", callback_data=f"adm_ban_temp_{target}"),
                       types.InlineKeyboardButton("Warning 1", callback_data=f"adm_warn1_{target}"),
                       types.InlineKeyboardButton("Warning 2", callback_data=f"adm_warn2_{target}"))
                self.bot.send_message(self.owner, "اقدام:", reply_markup=kb)
                self.bot.answer_callback_query(call.id, "گزارش ارسال شد ✅")
                return

            # admin actions
            if call.data.startswith("adm_"):
                if uid != self.owner:
                    return
                parts = call.data.split("_")
                action = parts[1]
                target = parts[2]

                if action == "ignore":
                    self.bot.edit_message_text("گزارش ignore شد", self.owner, call.message.message_id)

                if action == "ban" and parts[2] == "perm":
                    self.ban_perm(target, "گزارش تأیید شده")
                    self.bot.edit_message_text("بن دائم اعمال شد", self.owner, call.message.message_id)

                if action == "ban" and parts[2] == "temp":
                    users = self.db.read("users")
                    users[self.owner]["state"] = f"temp_ban_minutes_{target}"
                    self.db.write("users", users)
                    self.bot.send_message(self.owner, f"دقیقه بن موقت برای {target} را وارد کنید:")

                if action.startswith("warn"):
                    warns = 1 if "1" in action else 2
                    users = self.db.read("users")
                    if target in users:
                        users[target]["warns"] = users[target].get("warns", 0) + warns
                        self.db.write("users", users)
                        try:
                            self.bot.send_message(target, f"⚠️ {warns} اخطار دریافت کردید")
                        except:
                            pass
                    self.bot.edit_message_text(f"{warns} اخطار اعمال شد", self.owner, call.message.message_id)
                return

            if call.data.startswith("unban_perm_"):
                target = call.data.split("_")[2]
                db_b = self.db.read("bans")
                if 
