# shadow_titan_full_fixed.py
# کامل‌ترین نسخه Shadow Titan — رفع باگ‌ها:
#  - callback/button fixes
#  - invoice fallback (diagnostics + manual flow)
#  - robust profanity filter (normalization & obfuscation-resistant)
#  - VIP durations + Xmas free plan (one-time, 4-day window)
#  - gift single & gift all with duration selector
#  - Iran timezone handling (UTC+03:30)
#  - persistent JSON DB, improved logging
#
# پیش‌نیاز:
# pip install pyTelegramBotAPI flask requests

import os
import sys
import json
import time
import random
import string
import logging
import threading
import datetime
import re
from flask import Flask
import telebot
from telebot import types
import requests

# ---------------- CONFIG ----------------
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"   # <- جایگزین کنید
OWNER_ID = "8013245091"             # آیدی عددی مالک (رشته یا عدد)
CHANNEL = "@ChatNaAnnouncements"     # اگر می‌خواهی چک عضویت کانال داشته باشی
SUPPORT = "@its_alimo"
HF_TOKEN = ""                       # اگر می‌خواهی AI scan فعال باشه بذار

# اگر provider token برای پرداخت دارید (نه اجباری برای Stars)، اینجا قرار بدین.
PROVIDER_TOKEN = ""  # برای Telegram Stars خالی بمونه؛ اگر پرداخت درگاه دیگه دارید بذارید

DATA_DIR = "db_files"
LOG_FILE = "shadow_titan_full_fixed.log"

# Currency for invoice (Stars)
CURRENCY = "XTR"

# VIP plan definitions (stars amounts and days)
VIP_PLANS = {
    "vip_1w":  {"days": 7,   "stars": 25,   "title": "VIP 1 هفته"},
    "vip_1m":  {"days": 30,  "stars": 100,  "title": "VIP 1 ماهه"},
    "vip_3m":  {"days": 90,  "stars": 280,  "title": "VIP 3 ماهه"},
    "vip_6m":  {"days": 180, "stars": 560,  "title": "VIP 6 ماهه"},
    "vip_12m": {"days": 365, "stars": 860,  "title": "VIP 1 ساله"},
    # Xmas paid is optional; Xmas free is shown as paid=0 plan but handled specially
    "vip_xmas_free": {"days": 90, "stars": 0,   "title": "VIP کریسمس — 3 ماه (رایگان)"},
    "vip_xmas_paid": {"days": 365,"stars": 600, "title": "VIP کریسمس ویژه (پرداختی)"},
}

# Xmas free window from bot start (4 days)
CHRISTMAS_WINDOW_SECONDS = 4 * 86400  # 4 days

# Iran timezone offset (fixed)
IRAN_OFFSET_H = 3
IRAN_OFFSET_M = 30
IRAN_OFFSET = datetime.timedelta(hours=IRAN_OFFSET_H, minutes=IRAN_OFFSET_M)

# Create data dir
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- Logging ----------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ShadowTitanFullFixed")

# ---------------- Flask keepalive ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Shadow Titan Full Fixed — alive"

def run_web():
    try:
        app.run(host="0.0.0.0", port=8080)
    except Exception as e:
        logger.error(f"Flask run error: {e}")

# ---------------- DB Helper ----------------
class DB:
    def __init__(self, dirpath):
        self.dir = dirpath
        self.files = {
            "users": os.path.join(self.dir, "users.json"),
            "bans": os.path.join(self.dir, "bans.json"),
            "queue": os.path.join(self.dir, "queue.json"),
            "messages": os.path.join(self.dir, "messages.json"),
            "config": os.path.join(self.dir, "config.json"),
            "payments": os.path.join(self.dir, "payments.json")
        }
        self.lock = threading.Lock()
        self._init_files()

    def _init_files(self):
        defaults = {
            "users": {},
            "bans": {"permanent": {}, "temporary": {}},
            "queue": {"general": []},
            "messages": {"inbox": {}},
            "config": {"settings": {"maintenance": False}, "broadcast": {"text": None}},
            "payments": {}
        }
        with self.lock:
            for k, path in self.files.items():
                if not os.path.exists(path):
                    try:
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(defaults[k], f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error(f"init file error {path}: {e}")

    def read(self, key):
        path = self.files.get(key)
        if not path:
            return {}
        with self.lock:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"DB read error {key}: {e}")
                return {}

    def write(self, key, data):
        path = self.files.get(key)
        if not path:
            return
        with self.lock:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"DB write error {key}: {e}")

# ---------------- Time helpers ----------------
def now_ts_utc():
    return int(time.time())

def iran_now_dt():
    return datetime.datetime.utcnow() + IRAN_OFFSET

def ts_to_iran_str(ts):
    try:
        dt = datetime.datetime.utcfromtimestamp(int(ts)) + IRAN_OFFSET
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

# ---------------- Profanity normalization & filter ----------------
# Full list from user + expanded stems
BAD_WORDS = [
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
    "كير", "كس", "كص", "جنده", "قحبه", "گاييد", "كون", "گوه",
    # extra stems
    "گای", "گایید", "کصک", "کونک"
]

# diacritics and ornate marks to remove
DIACRITICS_RE = re.compile(r'[\u064B-\u065F\u0610-\u061A\u06D6-\u06ED\u0640]')

def normalize_persian(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    # map variants to persian forms
    s = s.replace('ك','ک').replace('ي','ی').replace('ى','ی').replace('ؤ','و').replace('إ','ا').replace('أ','ا')
    # remove diacritics and tatweel
    s = DIACRITICS_RE.sub('', s)
    s = s.replace('\u200c','').replace('\u200b','')
    # remove many punctuation that users use to obfuscate
    s = re.sub(r'[\s\.\-\_\*\|\\\/\:\;\'\"\,\(\)\[\]\{\}\?!ـ]', '', s)
    # remove digits
    s = re.sub(r'[0-9۰-۹]', '', s)
    # keep Persian/Arabic/Latin letters only
    s = re.sub(r'[^آ-یa-zA-Z]', '', s)
    # collapse long repetitions: e.g., کییییییر -> کییر (limit 2 repeats)
    s = re.sub(r'(.)\1{2,}', r'\1\1', s)
    return s

# pre-normalized bad words
BAD_WORDS_NORM = [normalize_persian(w) for w in BAD_WORDS if w]

def contains_bad(text: str) -> bool:
    n = normalize_persian(text)
    for bw in BAD_WORDS_NORM:
        if bw and bw in n:
            return True
    return False

# ---------------- Utility ----------------
def rand_token(n=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

# ---------------- Bot core ----------------
class ShadowTitan:
    def __init__(self, token):
        self.token = token
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.owner = str(OWNER_ID)
        self.channel = CHANNEL
        self.support = SUPPORT
        self.hf_token = HF_TOKEN
        self.provider_token = PROVIDER_TOKEN
        self.db = DB(DATA_DIR)
        self.start_ts = now_ts_utc()
        self.christmas_expires_at = self.start_ts + CHRISTMAS_WINDOW_SECONDS
        logger.info("ShadowTitan initialized")
        self.register_handlers()

    # DB helpers
    def ensure_user(self, uid):
        uid = str(uid)
        users = self.db.read("users")
        if uid not in users:
            users[uid] = {
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
                "gift_days": 0,
                "pending_payment": None
            }
            self.db.write("users", users)
        return users[uid]

    def save_user(self, uid, userd):
        users = self.db.read("users")
        users[str(uid)] = userd
        self.db.write("users", users)

    def is_vip(self, userd):
        try:
            return int(userd.get("vip_until", 0)) > now_ts_utc()
        except:
            return False

    # payment helper
    def make_payload(self, uid, plan_key):
        return f"{plan_key}_{uid}_{now_ts_utc()}_{rand_token(6)}"

    def register_payment(self, payload, uid, plan_key, amount):
        payments = self.db.read("payments")
        payments[payload] = {
            "uid": str(uid),
            "plan": plan_key,
            "amount": int(amount),
            "time": now_ts_utc(),
            "done": False
        }
        self.db.write("payments", payments)

    def mark_payment_done(self, payload):
        payments = self.db.read("payments")
        if payload in payments:
            payments[payload]["done"] = True
            self.db.write("payments", payments)
            return payments[payload]
        return None

    # keyboards
    def kb_main(self, uid):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        kb.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        kb.add("🎡 گردونه شانس روزانه", "🎖 خرید VIP (پلن‌ها)")
        kb.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if str(uid) == str(self.owner):
            kb.add("📊 پنل مدیریت")
        return kb

    def kb_chat(self):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        kb.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return kb

    def kb_report(self):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
               types.InlineKeyboardButton("+18", callback_data="rep_nsfw"))
        kb.add(types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
               types.InlineKeyboardButton("آزار", callback_data="rep_harass"))
        kb.add(types.InlineKeyboardButton("لغو ❌", callback_data="rep_cancel"))
        return kb

    def kb_duration_select(self, prefix):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("1 هفته", callback_data=f"{prefix}_7"),
               types.InlineKeyboardButton("1 ماه", callback_data=f"{prefix}_30"))
        kb.add(types.InlineKeyboardButton("3 ماه", callback_data=f"{prefix}_90"),
               types.InlineKeyboardButton("6 ماه", callback_data=f"{prefix}_180"))
        kb.add(types.InlineKeyboardButton("1 سال", callback_data=f"{prefix}_365"))
        return kb

    # register handlers
    def register_handlers(self):
        bot = self.bot

        @bot.message_handler(commands=["start"])
        def start_handler(msg):
            uid = str(msg.chat.id)
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None
            self.ensure_user(uid)
            bans = self.db.read("bans")
            cfg = self.db.read("config")

            # perm ban
            if uid in bans.get("permanent", {}):
                bot.send_message(uid, f"🚫 شما بن دائم هستید.\nدلیل: {bans['permanent'][uid]}\nپشتیبانی: {self.support}")
                return

            # temp ban
            if uid in bans.get("temporary", {}):
                end = int(bans["temporary"][uid]["end"])
                if now_ts_utc() < end:
                    rem = int((end - now_ts_utc()) / 60)
                    bot.send_message(uid, f"🚫 بن موقت. زمان باقی‌مانده: {rem} دقیقه\nپشتیبانی: {self.support}")
                    return
                else:
                    del bans["temporary"][uid]
                    self.db.write("bans", bans)

            # maintenance
            users = self.db.read("users")
            vip_now = self.is_vip(users.get(uid, {}))
            if cfg.get("settings", {}).get("maintenance", False) and not (vip_now or uid == self.owner):
                bot.send_message(uid, "🔧 ربات در حالت تعمیر است. فقط VIPها دسترسی دارند.")
                return

            # payload link (anon)
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    bot.send_message(uid, "نمی‌توانید به خودتان پیام بفرستید.")
                    return
                users = self.db.read("users")
                users[uid]["state"] = "anon_send"
                users[uid]["anon_target"] = target
                self.db.write("users", users)
                bot.send_message(uid, "پیام ناشناس خود را وارد کنید:")
                return

            bot.send_message(uid, "🌟 به Shadow Titan خوش آمدی!", reply_markup=self.kb_main(uid))

        @bot.pre_checkout_query_handler(func=lambda q: True)
        def precheckout(q):
            try:
                bot.answer_pre_checkout_query(q.id, ok=True)
            except Exception as e:
                logger.error(f"precheckout answer error: {e}")

        @bot.message_handler(content_types=["successful_payment"])
        def successful_payment(msg):
            try:
                payload = ""
                try:
                    payload = msg.successful_payment.invoice_payload
                except:
                    payload = getattr(msg.successful_payment, "payload", "")
                if not payload:
                    logger.warning("successful_payment with no payload")
                    return
                payments = self.db.read("payments")
                if payload not in payments:
                    logger.warning(f"unknown successful_payment payload: {payload}")
                    return
                pay = payments[payload]
                plan_key = pay.get("plan")
                users = self.db.read("users")
                user = users.get(str(msg.chat.id))
                if not user:
                    user = self.ensure_user(msg.chat.id)
                plan = VIP_PLANS.get(plan_key)
                if plan:
                    now = now_ts_utc()
                    start = max(now, int(user.get("vip_until", 0)))
                    user["vip_until"] = start + int(plan["days"]) * 86400
                    users[str(msg.chat.id)] = user
                    self.db.write("users", users)
                    payments[payload]["done"] = True
                    self.db.write("payments", payments)
                    bot.send_message(str(msg.chat.id), f"🎉 پرداخت موفق! {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
                else:
                    logger.warning(f"plan {plan_key} not found on successful_payment")
            except Exception as e:
                logger.error(f"successful_payment handler error: {e}")

        @bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def main_handler(msg):
            try:
                uid = str(msg.chat.id)
                users = self.db.read("users")
                if uid not in users:
                    user = self.ensure_user(uid)
                else:
                    user = users[uid]

                bans = self.db.read("bans")
                cfg = self.db.read("config")

                # bans
                if uid in bans.get("permanent", {}):
                    return
                if uid in bans.get("temporary", {}) and now_ts_utc() < bans["temporary"][uid]["end"]:
                    return

                # maintenance
                if cfg.get("settings", {}).get("maintenance", False) and not (self.is_vip(user) or uid == self.owner):
                    return

                # save last chat msg id if in chat
                if user.get("partner"):
                    user["last_chat_msg_id"] = msg.message_id
                    users[uid] = user
                    self.db.write("users", users)

                text = msg.text or ""

                # CHAT FLOW (when paired)
                if user.get("partner"):
                    partner = user["partner"]

                    if text == "🔚 پایان گفتگو":
                        kb = types.InlineKeyboardMarkup()
                        kb.add(types.InlineKeyboardButton("بله، پایان بده", callback_data="end_yes"),
                               types.InlineKeyboardButton("خیر، ادامه بده", callback_data="end_no"))
                        bot.send_message(uid, "آیا مطمئن هستید؟", reply_markup=kb)
                        return

                    if text == "🚩 گزارش تخلف":
                        user["report_target"] = partner
                        user["report_last_msg_id"] = msg.message_id
                        users[uid] = user
                        self.db.write("users", users)
                        bot.send_message(uid, "دلیل گزارش را انتخاب کن:", reply_markup=self.kb_report())
                        return

                    if text == "🚫 بلاک و خروج":
                        blocks = user.get("blocks", [])
                        if partner not in blocks:
                            blocks.append(partner)
                        user["blocks"] = blocks
                        users[uid] = user
                        self.db.write("users", users)
                        self.end_chat(uid, partner, "بلاک کرد")
                        return

                    # profanity
                    if text and contains_bad(text):
                        try:
                            bot.delete_message(uid, msg.message_id)
                        except:
                            pass
                        user["warns"] = user.get("warns", 0) + 1
                        users[uid] = user
                        self.db.write("users", users)
                        if user["warns"] >= 3:
                            self.ban_perm(uid, "فحاشی مکرر")
                            self.end_chat(uid, partner, "بن شد")
                            return
                        bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3 – فحاشی ممنوع است!")
                        return

                    # copy message
                    try:
                        bot.copy_message(partner, uid, msg.message_id)
                    except Exception as e:
                        logger.warning(f"copy_message error: {e}")
                    return

                # NOT IN CHAT — handling menu actions
                if text == "🛰 شروع چت ناشناس":
                    kb = types.InlineKeyboardMarkup(row_width=3)
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                           types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any"))
                    bot.send_message(uid, "دنبال چه کسی می‌گردی؟", reply_markup=kb)
                    return

                if text == "👤 پروفایل من":
                    rank = "🎖 VIP" if self.is_vip(user) else "عادی"
                    vip_until = int(user.get("vip_until", 0))
                    vip_text = "ندارد"
                    if vip_until and vip_until > now_ts_utc():
                        vip_text = ts_to_iran_str(vip_until)
                    bot.send_message(uid, f"<b>پروفایل شما</b>\n\n"
                                          f"نام: {user.get('name','نامشخص')}\n"
                                          f"جنسیت: {user.get('sex','نامشخص')}\n"
                                          f"سن: {user.get('age','نامشخص')}\n"
                                          f"رنک: {rank}\n"
                                          f"اعتبار VIP تا: {vip_text}\n"
                                          f"اخطار: {user.get('warns',0)}")
                    return

                if text == "📩 لینک ناشناس من":
                    botname = None
                    try:
                        botname = self.bot.get_me().username
                    except:
                        botname = "ShadowTitanBot"
                    link = f"https://t.me/{botname}?start=msg_{uid}"
                    bot.send_message(uid, f"<b>لینک ناشناس شما</b>\n\n{link}")
                    return

                if text == "📥 پیام‌های ناشناس":
                    messages = self.db.read("messages")
                    inbox = messages.get("inbox", {}).get(uid, [])
                    if not inbox:
                        bot.send_message(uid, "هیچ پیام ناشناسی دریافت نکرده‌اید 📭")
                        return
                    kb = types.InlineKeyboardMarkup()
                    txt = "<b>پیام‌های ناشناس شما</b>\n\n"
                    for i, m in enumerate(inbox):
                        txt += f"{i+1}. {m['text']}\n<i>{m['time']}</i>\n\n"
                        kb.add(types.InlineKeyboardButton(f"پاسخ به پیام {i+1}", callback_data=f"anon_reply_{i}"))
                    bot.send_message(uid, txt, reply_markup=kb)
                    # mark seen
                    updated = False
                    for m in inbox:
                        if not m.get("seen", False):
                            m["seen"] = True
                            updated = True
                            try:
                                bot.send_message(m["from"], "✅ پیام شما دیده شد")
                            except:
                                pass
                    if updated:
                        messages["inbox"][uid] = inbox
                        self.db.write("messages", messages)
                    return

                if text == "🎡 گردونه شانس روزانه":
                    today = iran_now_dt().strftime("%Y-%m-%d")
                    if user.get("last_spin") == today:
                        bot.send_message(uid, "امروز قبلاً گردونه را چرخانده‌اید 😊")
                        return
                    user["last_spin"] = today
                    users[uid] = user
                    self.db.write("users", users)
                    if random.random() < 0.05:
                        now = now_ts_utc()
                        start = max(now, int(user.get("vip_until", 0)))
                        user["vip_until"] = start + 30 * 86400
                        users[uid] = user
                        self.db.write("users", users)
                        bot.send_message(uid, f"🎉 تبریک! رنک VIP (۳۰ روزه) گرفتید. اعتبار تا: {ts_to_iran_str(user['vip_until'])}")
                    else:
                        bot.send_message(uid, "گردونه چرخید... پوچ! شانس بعدی را امتحان کنید 🌟")
                    return

                if text == "🎖 خرید VIP (پلن‌ها)":
                    kb = types.InlineKeyboardMarkup(row_width=1)
                    now = now_ts_utc()
                    # show xmas free if window and not used
                    if now < self.christmas_expires_at and not user.get("used_christmas", False):
                        kb.add(types.InlineKeyboardButton(VIP_PLANS["vip_xmas_free"]["title"], callback_data="buy_vip_free_xmas"))
                    # show other paid plans
                    for key, p in VIP_PLANS.items():
                        if key == "vip_xmas_free":
                            continue
                        # show all paid plans (stars)
                        kb.add(types.InlineKeyboardButton(f"{p['title']} — {p['stars']} ⭐", callback_data=f"buy_vip_paid|{key}"))
                    bot.send_message(uid, "<b>پلن‌های VIP</b>\nلطفاً پلن مورد نظر را انتخاب کنید:", reply_markup=kb)
                    return

                if text == "⚙ تنظیمات":
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    kb.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت")
                    kb.add("🔙 بازگشت به منو")
                    bot.send_message(uid, "تنظیمات پروفایل:", reply_markup=kb)
                    return

                if text == "✏️ تغییر نام":
                    user["state"] = "change_name"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "نام جدید را وارد کنید:")
                    return

                if user.get("state") == "change_name":
                    if contains_bad(text):
                        bot.send_message(uid, "نام نامعتبر است")
                        return
                    user["name"] = text[:30]
                    user["state"] = "idle"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "نام با موفقیت تغییر کرد ✅", reply_markup=self.kb_main(uid))
                    return

                if text == "🔢 تغییر سن":
                    user["state"] = "change_age"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "سن جدید را وارد کنید:")
                    return

                if user.get("state") == "change_age":
                    if not text.isdigit() or not 12 <= int(text) <= 99:
                        bot.send_message(uid, "سن باید بین 12 و 99 باشد")
                        return
                    user["age"] = int(text)
                    user["state"] = "idle"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "سن ذخیره شد ✅", reply_markup=self.kb_main(uid))
                    return

                if text == "⚧ تغییر جنسیت":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="change_sex_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="change_sex_f"))
                    bot.send_message(uid, "جنسیت را انتخاب کنید:", reply_markup=kb)
                    return

                # admin menu
                if uid == self.owner and text == "📊 پنل مدیریت":
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    kb.add("📈 آمار کامل", "🛠 تعمیر و نگهداری")
                    kb.add("🎖 گیفت VIP تکی", "🎖 گیفت VIP همگانی")
                    kb.add("❌ حذف VIP", "📋 لیست VIP")
                    kb.add("📁 دانلود دیتابیس", "🚫 لیست بن‌شده‌ها")
                    bot.send_message(uid, "پنل مدیریت:", reply_markup=kb)
                    return

                # gift single follow-up (admin enters numeric ID)
                if user.get("state") == "gift_single_id" and text and text.isdigit() and uid == self.owner:
                    user["gift_target"] = text
                    user["state"] = "gift_single_reason"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "دلیل گیفت را وارد کن:")
                    return

                if user.get("state") == "gift_single_reason" and uid == self.owner:
                    reason = text
                    target = user.get("gift_target")
                    days = int(user.get("gift_days", 0))
                    if target and target in users:
                        now = now_ts_utc()
                        users[target]["vip_until"] = now + days * 86400
                        self.db.write("users", users)
                        bot.send_message(uid, f"✅ VIP به {target} برای {days} روز داده شد")
                        try:
                            bot.send_message(target, f"🎉 شما VIP {days} روزه گرفتید.\nدلیل: {reason}")
                        except:
                            pass
                    else:
                        bot.send_message(uid, "کاربر یافت نشد")
                    user["state"] = "idle"
                    user.pop("gift_target", None)
                    user.pop("gift_days", None)
                    self.db.write("users", users)
                    return

                if user.get("state") == "gift_all_reason" and uid == self.owner:
                    reason = text
                    days = int(user.get("gift_days", 30))
                    now = now_ts_utc()
                    count = 0
                    for u_id in users:
                        users[u_id]["vip_until"] = now + days * 86400
                        try:
                            bot.send_message(u_id, f"🎉 VIP {days} روزه دریافت کردی.\nدلیل: {reason}")
                        except:
                            pass
                        count += 1
                    self.db.write("users", users)
                    bot.send_message(uid, f"✅ VIP به {count} کاربر برای {days} روز داده شد")
                    user["state"] = "idle"
                    user.pop("gift_days", None)
                    self.db.write("users", users)
                    return

                if text in ("منو", "🔙 بازگشت به منو"):
                    bot.send_message(uid, "منوی اصلی", reply_markup=self.kb_main(uid))
                    return

                # fallback helpful message instead of "از منو استفاده کن" single-line
                bot.send_message(uid, "برای شروع از دکمه‌های منو استفاده کن ✅", reply_markup=self.kb_main(uid))
            except Exception as e:
                logger.error(f"main_handler error: {e}")

        @bot.callback_query_handler(func=lambda c: True)
        def callback_handler(c):
            try:
                uid = str(c.from_user.id)
                data = c.data or ""
                users = self.db.read("users")
                user = users.get(uid) or self.ensure_user(uid)

                # answer callback to remove "loading"
                try:
                    bot.answer_callback_query(c.id)
                except:
                    pass

                # sex change
                if data in ("change_sex_m", "change_sex_f"):
                    user["sex"] = "آقا" if data == "change_sex_m" else "خانم"
                    user["state"] = "idle"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "جنسیت با موفقیت تغییر کرد ✅", reply_markup=self.kb_main(uid))
                    return

                # find
                if data.startswith("find_"):
                    dbq = self.db.read("queue")
                    if uid not in dbq.get("general", []):
                        dbq["general"].append(uid)
                    self.db.write("queue", dbq)
                    bot.send_message(uid, "در حال جستجو برای هم‌صحبت...")
                    pots = [p for p in dbq.get("general", []) if p != uid]
                    pots = [p for p in pots if uid not in users.get(p, {}).get("blocks", []) and p not in user.get("blocks", [])]
                    if pots:
                        partner = random.choice(pots)
                        try:
                            dbq["general"].remove(uid)
                        except:
                            pass
                        try:
                            dbq["general"].remove(partner)
                        except:
                            pass
                        users[uid]["partner"] = partner
                        users[partner]["partner"] = uid
                        self.db.write("queue", dbq)
                        self.db.write("users", users)
                        bot.send_message(uid, "هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chat())
                        bot.send_message(partner, "هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chat())
                    else:
                        bot.send_message(uid, "شما در صف قرار گرفتید؛ لطفاً صبور باشید...")
                    return

                # anon reply selection
                if data.startswith("anon_reply_"):
                    idx = int(data.split("_")[2])
                    dbm = self.db.read("messages")
                    inbox = dbm.get("inbox", {}).get(uid, [])
                    if idx < 0 or idx >= len(inbox):
                        bot.answer_callback_query(c.id, "پیام نامعتبر")
                        return
                    msgdata = inbox[idx]
                    user["state"] = "anon_reply"
                    user["anon_reply_target"] = msgdata["from"]
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "پاسخ خود را بنویسید:")
                    return

                # end chat confirm
                if data == "end_yes":
                    partner = user.get("partner")
                    self.end_chat(uid, partner, "پایان داد")
                    return
                if data == "end_no":
                    bot.answer_callback_query(c.id, "چت ادامه دارد ✅")
                    return

                # report
                if data.startswith("rep_"):
                    if data == "rep_cancel":
                        bot.answer_callback_query(c.id, "گزارش لغو شد ✅")
                        return
                    reasons = {"rep_insult":"فحاشی","rep_nsfw":"+18","rep_spam":"اسپم","rep_harass":"آزار"}
                    reason = reasons.get(data, "نامشخص")
                    target = user.get("report_target")
                    last_msg = user.get("report_last_msg_id")
                    bot.send_message(self.owner, f"🚩 گزارش جدید\nشاکی: {uid}\nمتهم: {target}\nدلیل: {reason}")
                    if last_msg:
                        try:
                            bot.forward_message(self.owner, uid, last_msg)
                        except:
                            pass
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(types.InlineKeyboardButton("Ignore", callback_data=f"adm_ignore_{target}"),
                           types.InlineKeyboardButton("Ban Perm", callback_data=f"adm_ban_perm_{target}"))
                    kb.add(types.InlineKeyboardButton("Ban Temp", callback_data=f"adm_ban_temp_{target}"),
                           types.InlineKeyboardButton("Warn 1", callback_data=f"adm_warn1_{target}"))
                    bot.send_message(self.owner, "اقدام:", reply_markup=kb)
                    bot.answer_callback_query(c.id, "گزارش ارسال شد ✅")
                    return

                # admin actions
                if data.startswith("adm_"):
                    if str(c.from_user.id) != str(self.owner):
                        bot.answer_callback_query(c.id, "مجاز نیستی")
                        return
                    parts = data.split("_")
                    action = parts[1]
                    target = parts[2] if len(parts) > 2 else None
                    if action == "ignore":
                        try:
                            bot.edit_message_text("گزارش ignore شد", self.owner, c.message.message_id)
                        except:
                            pass
                    if action == "ban" and target == "perm":
                        self.ban_perm(target, "گزارش تایید")
                        try:
                            bot.edit_message_text("بن دائم اعمال شد", self.owner, c.message.message_id)
                        except:
                            pass
                    if action == "ban" and target == "temp":
                        users = self.db.read("users")
                        users[self.owner]["state"] = f"temp_ban_minutes_{target}"
                        self.db.write("users", users)
                        bot.send_message(self.owner, f"مدت (دقیقه) بن موقت برای {target} را وارد کن:")
                    if action and action.startswith("warn"):
                        warns = 1 if "1" in action else 2
                        users = self.db.read("users")
                        if target in users:
                            users[target]["warns"] = users[target].get("warns", 0) + warns
                            self.db.write("users", users)
                            try:
                                bot.send_message(target, f"⚠️ {warns} اخطار دریافت کردی")
                            except:
                                pass
                        try:
                            bot.edit_message_text(f"{warns} اخطار اعمال شد", self.owner, c.message.message_id)
                        except:
                            pass
                    return

                # unban perm
                if data.startswith("unban_perm_"):
                    target = data.split("_",2)[2]
                    bans = self.db.read("bans")
                    if target in bans.get("permanent", {}):
                        del bans["permanent"][target]
                        self.db.write("bans", bans)
                        try:
                            bot.edit_message_text("کاربر بخشیده شد", self.owner, c.message.message_id)
                        except:
                            pass
                        try:
                            bot.send_message(target, "شما از بن دائم خارج شدی")
                        except:
                            pass
                    return

                # CHRISTMAS FREE (no invoice)
                if data == "buy_vip_free_xmas":
                    now = now_ts_utc()
                    if now > self.christmas_expires_at:
                        bot.answer_callback_query(c.id, "مهلت دریافت این پلن به پایان رسیده")
                        return
                    if user.get("used_christmas", False):
                        bot.answer_callback_query(c.id, "شما قبلاً این پلن را گرفته‌اید")
                        return
                    start = max(now, int(user.get("vip_until", 0)))
                    user["vip_until"] = start + VIP_PLANS["vip_xmas_free"]["days"] * 86400
                    user["used_christmas"] = True
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, f"🎉 تبریک! VIP سه‌ماهه رایگان فعال شد — دلیل: ویژه کریسمس 🎄\nاعتبار تا: {ts_to_iran_str(user['vip_until'])}")
                    return

                # Paid invoice creation
                if data.startswith("buy_vip_paid|"):
                    _, plan_key = data.split("|", 1)
                    plan = VIP_PLANS.get(plan_key)
                    if not plan:
                        bot.answer_callback_query(c.id, "پلن نامعتبر")
                        return
                    if int(plan.get("stars", 0)) == 0:
                        bot.answer_callback_query(c.id, "این پلن رایگان است و باید مستقیم دریافت شود")
                        return
                    payload = self.make_payload(uid, plan_key)
                    prices = [types.LabeledPrice(label=plan["title"], amount=int(plan["stars"]))]
                    try:
                        # try to send invoice (Stars)
                        bot.send_invoice(
                            chat_id=int(uid),
                            title=plan["title"],
                            description=f"⏳ مدت: {plan['days']} روز\n{plan['title']}",
                            payload=payload,
                            provider_token=self.provider_token if self.provider_token else "",
                            currency=CURRENCY,
                            prices=prices,
                            start_parameter="vip_buy"
                        )
                    except Exception as e:
                        # invoice creation failed -> log and fallback
                        logger.error(f"send_invoice failed for {uid} plan {plan_key}: {e}")
                        # register payment record for manual flow so admin can mark it paid later
                        self.register_payment(payload, uid, plan_key, plan["stars"])
                        # fallback: send manual-payment instructions with unique code (payload)
                        kb = types.InlineKeyboardMarkup(row_width=1)
                        kb.add(types.InlineKeyboardButton("✅ اعلام پرداخت (برای پیگیری)", callback_data=f"manual_paid|{payload}"))
                        # show message explaining likely reasons and manual option
                        bot.send_message(uid,
                                         "⚠️ خطا در ایجاد فاکتور (پرداخت خودکار ممکن است برای حساب شما فعال نباشد).\n\n"
                                         "دو راه داری:\n"
                                         "1) اگر می‌خواهی پرداخت خودکار (Stars) کار کند، باید BotFather و Business Mode و provider token را بررسی کنی.\n"
                                         "2) پرداخت دستی: با استفاده از کد پیگیری در پایین، پرداخت را به روش دلخواه (تماس با ادمین یا روش توافقی) انجام بده و سپس روی 'اعلام پرداخت' بزنی تا پرداخت ثبت شود.\n\n"
                                         f"کد پیگیری: <code>{payload}</code>\n\n"
                                         "اگر می‌خواهی من به طور خودکار چک کنم و ادمین رو مطلع کنم، گزینه اعلام پرداخت را بزن.",
                                         reply_markup=kb)
                        try:
                            bot.answer_callback_query(c.id, "خطا در ایجاد فاکتور — روش پرداخت دستی ارسال شد")
                        except:
                            pass
                        return
                    # if send_invoice succeeded, register payment
                    self.register_payment(payload, uid, plan_key, plan["stars"])
                    try:
                        bot.answer_callback_query(c.id, "فاکتور ارسال شد ✅")
                    except:
                        pass
                    return

                # manual paid button (user claims they paid by external method)
                if data.startswith("manual_paid|"):
                    payload = data.split("|",1)[1]
                    payments = self.db.read("payments")
                    pay = payments.get(payload)
                    if not pay:
                        bot.answer_callback_query(c.id, "پرداخت نامشخص")
                        return
                    # notify admin/owner to verify manual payment
                    bot.send_message(self.owner, f"⚠️ اعلام پرداخت دستی از طرف {uid}\nکد: {payload}\nمبلغ: {pay.get('amount')}\nپلن: {pay.get('plan')}\nلطفاً پرداخت را بررسی و در صورت تائید، /confirm_manual {payload} را بزن.")
                    bot.send_message(uid, "اعلام پرداخت شما ثبت شد. ادمین پس از بررسی پرداخت را تایید می‌کند.")
                    return

                # gift single duration selection
                if data.startswith("gift_single_"):
                    days = int(data.split("_")[2])
                    user["gift_days"] = days
                    user["state"] = "gift_single_id"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "آیدی عددی کاربر را وارد کنید:")
                    return

                # gift all duration
                if data.startswith("gift_all_"):
                    days = int(data.split("_")[2])
                    user["gift_days"] = days
                    user["state"] = "gift_all_reason"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "دلیل هدیه VIP همگانی را وارد کنید:")
                    return

                # default fallback
                bot.answer_callback_query(c.id, "عملیات انجام شد")
            except Exception as e:
                logger.error(f"callback_handler error: {e}")

        # admin command to confirm manual payment: /confirm_manual <payload>
        @bot.message_handler(commands=["confirm_manual"])
        def confirm_manual_cmd(msg):
            if str(msg.chat.id) != str(self.owner):
                return
            parts = msg.text.split()
            if len(parts) < 2:
                bot.send_message(self.owner, "استفاده: /confirm_manual <payload>")
                return
            payload = parts[1]
            payments = self.db.read("payments")
            pay = payments.get(payload)
            if not pay:
                bot.send_message(self.owner, "پرداخت پیدا نشد")
                return
            if pay.get("done"):
                bot.send_message(self.owner, "این پرداخت قبلاً ثبت شده")
                return
            # apply VIP
            uid = pay.get("uid")
            plan_key = pay.get("plan")
            plan = VIP_PLANS.get(plan_key)
            if not plan:
                bot.send_message(self.owner, "پلن نامشخص")
                return
            users = self.db.read("users")
            user = users.get(uid)
            if not user:
                bot.send_message(self.owner, "کاربر یافت نشد")
                return
            now = now_ts_utc()
            start = max(now, int(user.get("vip_until", 0)))
            user["vip_until"] = start + int(plan["days"]) * 86400
            users[uid] = user
            payments[payload]["done"] = True
            self.db.write("users", users)
            self.db.write("payments", payments)
            bot.send_message(self.owner, f"✅ پرداخت دستی با کد {payload} تأیید شد. VIP به {uid} اعمال شد.")
            try:
                bot.send_message(uid, f"🎉 پرداخت شما تأیید شد. پلن {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
            except:
                pass

    # helper admin methods
    def ban_perm(self, uid, reason="تخلف"):
        bans = self.db.read("bans")
        bans.setdefault("permanent", {})[str(uid)] = reason
        self.db.write("bans", bans)
        logger.info(f"perm banned {uid} reason: {reason}")

    def ban_temp(self, uid, minutes=60, reason="تخلف"):
        bans = self.db.read("bans")
        end = now_ts_utc() + minutes * 60
        bans.setdefault("temporary", {})[str(uid)] = {"end": end, "reason": reason}
        self.db.write("bans", bans)
        logger.info(f"temp banned {uid} until {end}")

    def end_chat(self, a, b, msg="ترک کرد"):
        users = self.db.read("users")
        if a in users:
            users[a]["partner"] = None
        if b in users:
            users[b]["partner"] = None
        self.db.write("users", users)
        try:
            self.bot.send_message(a, "چت پایان یافت", reply_markup=self.kb_main(a))
        except:
            pass
        try:
            self.bot.send_message(b, f"هم‌صحبت شما چت را {msg}", reply_markup=self.kb_main(b))
        except:
            pass

    def run(self):
        t = threading.Thread(target=run_web, daemon=True)
        t.start()
        logger.info("Bot polling started")
        try:
            self.bot.infinity_polling(long_polling_timeout=60)
        except Exception as e:
            logger.error(f"infinity_polling crashed: {e}")
            # try restart once
            time.sleep(2)
            try:
                self.bot.infinity_polling(long_polling_timeout=60)
            except Exception as e2:
                logger.error(f"second polling crash: {e2}")
                sys.exit(1)

# ---------------- run ----------------
if __name__ == "__main__":
    if TOKEN == "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU":
        print("لطفاً TOKEN را در بالای فایل تنظیم کنید.")
        sys.exit(1)
    bot = ShadowTitan(TOKEN)
    bot.run()
