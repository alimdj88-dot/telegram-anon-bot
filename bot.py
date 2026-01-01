 # shadow_titan_complete.py
# Shadow Titan — Complete version with:
#  - VIP time-based plans (including free Xmas 90-day plan)
#  - Robust profanity filter (normalization + obfuscation resistance)
#  - Gift VIP (single + global) with duration selector
#  - Time handling in Iran timezone (UTC+03:30)
#  - Telegram Stars invoices (provider_token="" and currency="XTR")
#  - Persistent JSON DB, admin panel, queue, anon messages, reports, bans
#
# Replace TOKEN, OWNER_ID, CHANNEL, HF_TOKEN before running.

import os
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

# ---------------- CONFIG (REPLACE THESE) ----------------
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"   # <--- جایگزین کن
OWNER_ID = "8013245091"             # آیدی عددی خودت به صورت رشته یا عدد
CHANNEL = "@ChatNaAnnouncements"     # یا "" اگر چک کانال نمی‌خوای
SUPPORT = "@its_alimo"
HF_TOKEN = ""                       # اگر می‌خوای AI scan فعال باشه بذار، در غیر اینصورت خالی
# -------------------------------------------------------

DATA_DIR = "db_files"
LOG_FILE = "shadow_titan_full_log.log"
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

# Timezone offset for Iran (no DST handling)
IRAN_OFFSET_H = 3
IRAN_OFFSET_M = 30
IRAN_OFFSET = datetime.timedelta(hours=IRAN_OFFSET_H, minutes=IRAN_OFFSET_M)

# Payment / Stars configuration
CURRENCY = "XTR"

# VIP plans: note vip_xmas_free (price 0) added to list so it's visible in menu
VIP_PLANS = {
    "vip_1w":  {"days": 7,   "stars": 25,   "title": "VIP 1 هفته"},
    "vip_1m":  {"days": 30,  "stars": 100,  "title": "VIP 1 ماهه"},
    "vip_3m":  {"days": 90,  "stars": 280,  "title": "VIP 3 ماهه"},
    "vip_6m":  {"days": 180, "stars": 560,  "title": "VIP 6 ماهه"},
    "vip_12m": {"days": 365, "stars": 860,  "title": "VIP 1 ساله"},
    "vip_xmas_free": {"days": 90,  "stars": 0,   "title": "VIP کریسمس — 3 ماه (رایگان)"},
    "vip_xmas_paid": {"days": 365,"stars": 600, "title": "VIP کریسمس ویژه (پرداختی)"},
}

# Christmas free window (from bot start) in seconds
CHRISTMAS_WINDOW_SECONDS = 4 * 86400  # 4 days

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)

# Logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ShadowTitanComplete")

# Flask keepalive
app = Flask(__name__)
@app.route("/")
def home():
    return "Shadow Titan Complete — alive"

def run_web():
    try:
        app.run(host=WEB_HOST, port=WEB_PORT)
    except Exception as e:
        logger.error(f"Flask run error: {e}")

# ---------------- DB helper ----------------
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
            for k, fp in self.files.items():
                if not os.path.exists(fp):
                    try:
                        with open(fp, "w", encoding="utf-8") as f:
                            json.dump(defaults[k], f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error(f"init file error {fp}: {e}")

    def read(self, key):
        fp = self.files.get(key)
        if not fp: return {}
        with self.lock:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"DB read error {key}: {e}")
                return {}

    def write(self, key, data):
        fp = self.files.get(key)
        if not fp: return
        with self.lock:
            try:
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"DB write error {key}: {e}")

# ---------------- Time helpers ----------------
def now_ts_utc():
    return int(time.time())

def iran_now_dt():
    # naive datetime in Iran offset (no DST)
    return datetime.datetime.utcnow() + IRAN_OFFSET

def ts_to_iran_str(ts):
    try:
        dt = datetime.datetime.utcfromtimestamp(int(ts)) + IRAN_OFFSET
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

# ---------------- profanity normalization ----------------
# Full list taken/expanded from user's provided list (kept comprehensive)
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
    # Short obscene stems to be safe
    "گای", "گایید", "کصک"
]

# Pre-normalize bad words for matching
BAD_WORDS_NORM = []

# Unicode diacritics and tatweel etc to remove
DIACRITICS_RE = re.compile(r'[\u064B-\u065F\u0610-\u061A\u06D6-\u06ED\u0640]')

# Normalize function: map Arabic chars -> Persian, remove diacritics, remove non-letters,
# collapse repeated letters (>2 -> 2), lower-case
def normalize_persian(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    # map variant letters to common Persian forms
    s = s.replace('ك', 'ک').replace('ي', 'ی').replace('ى', 'ی').replace('ؤ', 'و').replace('إ', 'ا').replace('أ', 'ا')
    # remove diacritics/tashkeel and tatweel
    s = DIACRITICS_RE.sub('', s)
    s = s.replace('\u200c', '')  # zero-width non-joiner
    s = s.replace('\u200b', '')  # zero width space
    s = s.replace('-', '').replace('_', '').replace('.', '').replace('*', '').replace('/', '').replace('\\', '')
    # remove punctuation and digits but keep letters (Persian/Arabic/Latin) and joiners removed above
    s = re.sub(r'[^آ-یa-zA-Z]', '', s)
    # collapse repeated letters: aaa -> aa (keep up to 2 repeats)
    s = re.sub(r'(.)\1{2,}', r'\1\1', s)
    return s

# Prepare normalized bad words set
for w in BAD_WORDS:
    BAD_WORDS_NORM.append(normalize_persian(w))

# ---------------- Utility ----------------
def rand_token(n=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

# ---------------- Bot class ----------------
class ShadowTitanComplete:
    def __init__(self, token):
        self.token = token
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.owner = str(OWNER_ID)
        self.channel = CHANNEL
        self.support = SUPPORT
        self.hf_token = HF_TOKEN
        self.db = DB(DATA_DIR)
        self.start_ts = now_ts_utc()
        self.christmas_expires_at = self.start_ts + CHRISTMAS_WINDOW_SECONDS
        self._prepare_handlers()
        logger.info("ShadowTitanComplete initialized")

    # DB user helpers
    def _ensure_user(self, uid):
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

    def _save_user(self, uid, user):
        users = self.db.read("users")
        users[str(uid)] = user
        self.db.write("users", users)

    def _is_vip(self, user):
        try:
            return int(user.get("vip_until", 0)) > now_ts_utc()
        except:
            return False

    def _contains_bad(self, text):
        # normalize and check substrings
        if not text:
            return False
        n = normalize_persian(text)
        # check each normalized bad word if in normalized text
        for bw in BAD_WORDS_NORM:
            if bw and bw in n:
                return True
        return False

    # Payment helpers
    def _make_payload(self, uid, plan_key):
        return f"{plan_key}_{uid}_{now_ts_utc()}_{rand_token(6)}"

    def _register_payment(self, payload, uid, plan_key, amount):
        payments = self.db.read("payments")
        payments[payload] = {
            "uid": str(uid),
            "plan": plan_key,
            "amount": int(amount),
            "time": now_ts_utc(),
            "done": False
        }
        self.db.write("payments", payments)

    def _mark_payment_done(self, payload):
        payments = self.db.read("payments")
        if payload in payments:
            payments[payload]["done"] = True
            self.db.write("payments", payments)
            return payments[payload]
        return None

    # Keyboards
    def _kb_main(self, uid):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        kb.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        kb.add("🎡 گردونه شانس روزانه", "🎖 خرید VIP (پلن‌ها)")
        kb.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if str(uid) == str(self.owner):
            kb.add("📊 پنل مدیریت")
        return kb

    def _kb_chat(self):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        kb.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return kb

    def _kb_report(self):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
               types.InlineKeyboardButton("+18", callback_data="rep_nsfw"))
        kb.add(types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
               types.InlineKeyboardButton("آزار", callback_data="rep_harass"))
        kb.add(types.InlineKeyboardButton("لغو ❌", callback_data="rep_cancel"))
        return kb

    def _kb_vip_durations_for_admin(self, prefix):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("1 هفته", callback_data=f"{prefix}_7"),
               types.InlineKeyboardButton("1 ماه", callback_data=f"{prefix}_30"))
        kb.add(types.InlineKeyboardButton("3 ماه", callback_data=f"{prefix}_90"),
               types.InlineKeyboardButton("6 ماه", callback_data=f"{prefix}_180"))
        kb.add(types.InlineKeyboardButton("1 سال", callback_data=f"{prefix}_365"))
        return kb

    # Prepare handlers
    def _prepare_handlers(self):
        bot = self.bot

        @bot.message_handler(commands=['start'])
        def _start(msg):
            uid = str(msg.chat.id)
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None
            self._ensure_user(uid)
            db_bans = self.db.read("bans")
            db_cfg = self.db.read("config")

            # permanent ban
            if uid in db_bans.get("permanent", {}):
                reason = db_bans["permanent"].get(uid, "تخلف")
                bot.send_message(uid, f"🚫 بن دائم\nدلیل: {reason}\nپشتیبانی: {self.support}")
                return

            # temp ban
            tmp = db_bans.get("temporary", {})
            if uid in tmp:
                end = int(tmp[uid]["end"])
                if now_ts_utc() < end:
                    rem_m = int((end - now_ts_utc()) / 60)
                    bot.send_message(uid, f"🚫 بن موقت. مانده: {rem_m} دقیقه\nپشتیبانی: {self.support}")
                    return
                else:
                    del tmp[uid]
                    db_bans["temporary"] = tmp
                    self.db.write("bans", db_bans)

            # maintenance
            users = self.db.read("users")
            vip_now = self._is_vip(users.get(uid, {}))
            if db_cfg.get("settings", {}).get("maintenance", False) and not (vip_now or uid == self.owner):
                bot.send_message(uid, "🔧 ربات در حالت تعمیر است. فقط VIPها دسترسی دارند.")
                return

            # link payload (anon)
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    bot.send_message(uid, "نمی‌توانید به خودتان پیام بفرستید.")
                    return
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
                        "pending_payment": None
                    }
                    self.db.write("users", users)
                    bot.send_message(uid, "برای ارسال پیام ناشناس، نام مستعار خود را وارد کنید:")
                else:
                    users[uid]["state"] = "anon_send"
                    users[uid]["anon_target"] = target
                    self.db.write("users", users)
                    bot.send_message(uid, "پیام ناشناس خود را وارد کنید:")
                return

            bot.send_message(uid, "🌟 به Shadow Titan خوش آمدی!", reply_markup=self._kb_main(uid))

        # pre checkout
        @bot.pre_checkout_query_handler(func=lambda q: True)
        def _precheckout(query):
            try:
                bot.answer_pre_checkout_query(query.id, ok=True)
            except Exception as e:
                logger.error(f"pre_checkout answer failed: {e}")

        # successful payment
        @bot.message_handler(content_types=['successful_payment'])
        def _successful_payment(message):
            try:
                payload = ""
                try:
                    payload = message.successful_payment.invoice_payload
                except:
                    payload = getattr(message.successful_payment, "payload", "")
                if not payload:
                    logger.warning("successful_payment had no payload")
                    return
                payments = self.db.read("payments")
                if payload not in payments:
                    logger.warning(f"unknown payload: {payload}")
                    return
                pay = payments[payload]
                uid = str(message.chat.id)
                users = self.db.read("users")
                user = users.get(uid)
                if not user:
                    user = self._ensure_user(uid)
                plan_key = pay.get("plan")
                # if free plan somehow had invoice, ignore (free handled without invoice)
                plan = VIP_PLANS.get(plan_key)
                if plan:
                    now = now_ts_utc()
                    start = max(now, int(user.get("vip_until", 0)))
                    user["vip_until"] = start + int(plan["days"]) * 86400
                    users[uid] = user
                    self.db.write("users", users)
                    payments[payload]["done"] = True
                    self.db.write("payments", payments)
                    bot.send_message(uid, f"🎉 پرداخت موفق! {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
                else:
                    logger.warning(f"plan not found on payment success: {plan_key}")
            except Exception as e:
                logger.error(f"successful_payment handler error: {e}")

        # main message handler
        @bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def _main(msg):
            try:
                uid = str(msg.chat.id)
                users = self.db.read("users")
                if uid not in users:
                    user = self._ensure_user(uid)
                else:
                    user = users[uid]
                bans = self.db.read("bans")
                cfg = self.db.read("config")

                # bans check
                if uid in bans.get("permanent", {}):
                    return
                if uid in bans.get("temporary", {}) and now_ts_utc() < bans["temporary"][uid]["end"]:
                    return

                # maintenance
                if cfg.get("settings", {}).get("maintenance", False) and not (self._is_vip(user) or uid == self.owner):
                    return

                # store last msg id if chatting
                if user.get("partner"):
                    user["last_chat_msg_id"] = msg.message_id
                    users[uid] = user
                    self.db.write("users", users)

                text = msg.text or ""

                # If in chat => forwarding, commands inside chat
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
                        bot.send_message(uid, "دلیل گزارش را انتخاب کن:", reply_markup=self._kb_report())
                        return

                    if text == "🚫 بلاک و خروج":
                        blocks = user.get("blocks", [])
                        if partner not in blocks:
                            blocks.append(partner)
                        user["blocks"] = blocks
                        users[uid] = user
                        self.db.write("users", users)
                        self._end_chat(uid, partner, "بلاک کرد")
                        return

                    # profanity filter (robust)
                    if text and self._contains_bad(text):
                        try:
                            bot.delete_message(uid, msg.message_id)
                        except:
                            pass
                        user["warns"] = user.get("warns", 0) + 1
                        users[uid] = user
                        self.db.write("users", users)
                        if user["warns"] >= 3:
                            self._ban_perm(uid, "فحاشی مکرر")
                            self._end_chat(uid, partner, "بن شد")
                            return
                        bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3 – فحاشی ممنوع است!")
                        return

                    # forward/copy
                    try:
                        bot.copy_message(partner, uid, msg.message_id)
                    except Exception as e:
                        logger.warning(f"copy_message error: {e}")
                    return

                # Not in chat: handle menus
                if text == "🛰 شروع چت ناشناس":
                    kb = types.InlineKeyboardMarkup(row_width=3)
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                           types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any"))
                    bot.send_message(uid, "دنبال چه کسی می‌گردی؟", reply_markup=kb)
                    return

                if text == "👤 پروفایل من":
                    rank = "🎖 VIP" if self._is_vip(user) else "عادی"
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
                    username = None
                    try:
                        username = self.bot.get_me().username
                    except:
                        username = "ShadowTitanBot"
                    link = f"https://t.me/{username}?start=msg_{uid}"
                    bot.send_message(uid, f"<b>لینک ناشناس شما</b>\n\n{link}")
                    return

                if text == "📥 پیام‌های ناشناس":
                    db_m = self.db.read("messages")
                    inbox = db_m.get("inbox", {}).get(uid, [])
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
                        db_m["inbox"][uid] = inbox
                        self.db.write("messages", db_m)
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
                    # show Xmas free if in window and not used
                    now = now_ts_utc()
                    if now < self.christmas_expires_at and not user.get("used_christmas", False):
                        # vip_xmas_free is shown as free plan
                        kb.add(types.InlineKeyboardButton(VIP_PLANS["vip_xmas_free"]["title"], callback_data="buy_vip_free_xmas"))
                    # show paid plans (and paid xmas if present)
                    for key, p in VIP_PLANS.items():
                        # skip the free entry here because we've inserted specially
                        if key == "vip_xmas_free":
                            continue
                        kb.add(types.InlineKeyboardButton(f"{p['title']} — {p['stars']} ⭐", callback_data=f"buy_vip_paid|{key}"))
                    bot.send_message(uid, "<b>پلن‌های VIP</b>\nانتخاب کن:", reply_markup=kb)
                    return

                if text == "⚙ تنظیمات":
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    kb.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت")
                    kb.add("🔙 بازگشت به منو")
                    bot.send_message(uid, "تنظیمات:", reply_markup=kb)
                    return

                if text == "✏️ تغییر نام":
                    user["state"] = "change_name"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "نام جدید را وارد کن:")
                    return

                if user.get("state") == "change_name":
                    if self._contains_bad(text):
                        bot.send_message(uid, "نام نامعتبر است")
                        return
                    user["name"] = text[:30]
                    user["state"] = "idle"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "نام ذخیره شد ✅", reply_markup=self._kb_main(uid))
                    return

                if text == "🔢 تغییر سن":
                    user["state"] = "change_age"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "سن خود را وارد کن:")
                    return

                if user.get("state") == "change_age":
                    if not text.isdigit() or not 12 <= int(text) <= 99:
                        bot.send_message(uid, "سن باید بین 12 و 99 باشد")
                        return
                    user["age"] = int(text)
                    user["state"] = "idle"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "سن ذخیره شد ✅", reply_markup=self._kb_main(uid))
                    return

                if text == "⚧ تغییر جنسیت":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="change_sex_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="change_sex_f"))
                    bot.send_message(uid, "جنسیت را انتخاب کن:", reply_markup=kb)
                    return

                # Admin panel quick
                if str(uid) == str(self.owner) and text == "📊 پنل مدیریت":
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    kb.add("📈 آمار کامل", "🛠 تعمیر و نگهداری")
                    kb.add("🎖 گیفت VIP تکی", "🎖 گیفت VIP همگانی")
                    kb.add("❌ حذف VIP", "📋 لیست VIP")
                    kb.add("📁 دانلود دیتابیس", "🚫 لیست بن‌شده‌ها")
                    bot.send_message(uid, "پنل مدیریت:", reply_markup=kb)
                    return

                # Admin gift single ID input
                if user.get("state") == "gift_single_id" and text and text.isdigit() and str(uid) == str(self.owner):
                    user["gift_target"] = text
                    user["state"] = "gift_single_reason"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "دلیل گیفت را وارد کنید:")
                    return

                if user.get("state") == "gift_single_reason" and str(uid) == str(self.owner):
                    reason = text
                    target = user.get("gift_target")
                    days = int(user.get("gift_days", 0) or 0)
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

                if user.get("state") == "gift_all_reason" and str(uid) == str(self.owner):
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
                    bot.send_message(uid, "منوی اصلی", reply_markup=self._kb_main(uid))
                    return

                # fallback
                bot.send_message(uid, "از منو استفاده کن", reply_markup=self._kb_main(uid))

            except Exception as e:
                logger.error(f"main message handler error: {e}")

        # callback handler
        @bot.callback_query_handler(func=lambda c: True)
        def _callback(c):
            try:
                uid = str(c.from_user.id)
                data = c.data or ""
                users = self.db.read("users")
                user = users.get(uid) or self._ensure_user(uid)

                # sex change
                if data in ("change_sex_m", "change_sex_f"):
                    user["sex"] = "آقا" if data == "change_sex_m" else "خانم"
                    user["state"] = "idle"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.answer_callback_query(c.id, "جنسیت تغییر کرد")
                    bot.send_message(uid, "تغییر انجام شد", reply_markup=self._kb_main(uid))
                    return

                # find matching
                if data.startswith("find_"):
                    dbq = self.db.read("queue")
                    if uid not in dbq.get("general", []):
                        dbq["general"].append(uid)
                    self.db.write("queue", dbq)
                    bot.answer_callback_query(c.id, "در حال جستجو...")
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
                        bot.send_message(uid, "هم‌صحبت پیدا شد!", reply_markup=self._kb_chat())
                        bot.send_message(partner, "هم‌صحبت پیدا شد!", reply_markup=self._kb_chat())
                    else:
                        bot.send_message(uid, "در صف قرار گرفتی؛ صبور باش...")
                    return

                # anon reply selection
                if data.startswith("anon_reply_"):
                    idx = int(data.split("_")[2])
                    db_m = self.db.read("messages")
                    inbox = db_m.get("inbox", {}).get(uid, [])
                    if idx < 0 or idx >= len(inbox):
                        bot.answer_callback_query(c.id, "پیام نامعتبر")
                        return
                    msgdata = inbox[idx]
                    user["state"] = "anon_reply"
                    user["anon_reply_target"] = msgdata["from"]
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "پاسخ بنویس:")
                    return

                # end chat confirmation
                if data == "end_yes":
                    partner = user.get("partner")
                    self._end_chat(uid, partner, "پایان داد")
                    return
                if data == "end_no":
                    bot.answer_callback_query(c.id, "چت ادامه دارد")
                    return

                # report callbacks
                if data.startswith("rep_"):
                    if data == "rep_cancel":
                        bot.answer_callback_query(c.id, "گزارش لغو شد")
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
                    bot.answer_callback_query(c.id, "گزارش ارسال شد")
                    return

                # admin actions
                if data.startswith("adm_"):
                    if str(c.from_user.id) != str(self.owner):
                        bot.answer_callback_query(c.id, "مجاز نیستی")
                        return
                    parts = data.split("_")
                    action = parts[1] if len(parts) > 1 else None
                    target = parts[2] if len(parts) > 2 else None
                    if action == "ignore":
                        try:
                            bot.edit_message_text("گزارش ignore شد", self.owner, c.message.message_id)
                        except:
                            pass
                    if action == "ban" and target == "perm":
                        self._ban_perm(target, "گزارش تایید")
                        try:
                            bot.edit_message_text("بن دائم اعمال شد", self.owner, c.message.message_id)
                        except:
                            pass
                    if action == "ban" and target == "temp":
                        users = self.db.read("users")
                        users[self.owner]["state"] = f"temp_ban_minutes_{target}"
                        self.db.write("users", users)
                        bot.send_message(self.owner, f"مدت بن موقت (دقیقه) برای {target} را وارد کن:")
                    if action and action.startswith("warn"):
                        warns = 1 if "1" in action else 2
                        users = self.db.read("users")
                        if target in users:
                            users[target]["warns"] = users[target].get("warns", 0) + warns
                            self.db.write("users", users)
                            try:
                                bot.send_message(target, f"⚠️ {warns} اخطار دریافت شد")
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

                # CHRISTMAS FREE plan (no invoice)
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

                # Paid plan: create invoice for Stars (provider_token must be empty)
                if data.startswith("buy_vip_paid|"):
                    _, plan_key = data.split("|", 1)
                    plan = VIP_PLANS.get(plan_key)
                    if not plan:
                        bot.answer_callback_query(c.id, "پلن نامعتبر")
                        return
                    # if plan price == 0, treat as free (but for paid flows price>0)
                    if int(plan.get("stars", 0)) == 0:
                        bot.answer_callback_query(c.id, "این پلن رایگان است و باید به صورت مستقیم دریافت شود")
                        return
                    payload = self._make_payload(uid, plan_key)
                    prices = [types.LabeledPrice(label=plan["title"], amount=int(plan["stars"]))]
                    try:
                        bot.send_invoice(
                            chat_id=int(uid),
                            title=plan["title"],
                            description=f"⏳ مدت: {plan['days']} روز\n{plan['title']}",
                            payload=payload,
                            provider_token="",  # MUST be empty for Telegram Stars
                            currency=CURRENCY,
                            prices=prices,
                            start_parameter="vip_buy"
                        )
                    except Exception as e:
                        logger.error(f"send_invoice error: {e}")
                        try:
                            bot.answer_callback_query(c.id, "خطا در ایجاد فاکتور")
                        except:
                            pass
                        return
                    self._register_payment(payload, uid, plan_key, plan["stars"])
                    bot.answer_callback_query(c.id, "فاکتور ارسال شد ✅")
                    return

                # gift single duration selection (admin)
                if data.startswith("gift_single_"):
                    days = int(data.split("_")[2])
                    user["gift_days"] = days
                    user["state"] = "gift_single_id"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "آیدی عددی کاربر را وارد کنید:")
                    return

                # gift all duration selection
                if data.startswith("gift_all_"):
                    days = int(data.split("_")[2])
                    user["gift_days"] = days
                    user["state"] = "gift_all_reason"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "دلیل هدیه VIP همگانی را وارد کنید:")
                    return

                # default
            except Exception as e:
                logger.error(f"callback handler error: {e}")

        # end of handler registration

    # admin helpers
    def _ban_perm(self, uid, reason="تخلف"):
        bans = self.db.read("bans")
        bans.setdefault("permanent", {})[str(uid)] = reason
        self.db.write("bans", bans)
        logger.info(f"perm ban {uid} reason {reason}")

    def _ban_temp(self, uid, minutes=60, reason="تخلف"):
        bans = self.db.read("bans")
        end = now_ts_utc() + minutes * 60
        bans.setdefault("temporary", {})[str(uid)] = {"end": end, "reason": reason}
        self.db.write("bans", bans)
        logger.info(f"temp ban {uid} until {end}")

    def _end_chat(self, a, b, msg="ترک کرد"):
        users = self.db.read("users")
        if a in users:
            users[a]["partner"] = None
        if b in users:
            users[b]["partner"] = None
        self.db.write("users", users)
        try:
            self.bot.send_message(a, "چت پایان یافت", reply_markup=self._kb_main(a))
        except:
            pass
        try:
            self.bot.send_message(b, f"هم‌صحبت شما چت را {msg}", reply_markup=self._kb_main(b))
        except:
            pass

    def run(self):
        # start flask keepalive
        t = threading.Thread(target=run_web, daemon=True)
        t.start()
        logger.info("Bot started polling")
        self.bot.infinity_polling()

# ----------------- RUN -----------------
if __name__ == "__main__":
    if TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("لطفاً TOKEN را در بالای فایل تنظیم کنید.")
        exit(1)
    bot = ShadowTitanComplete(TOKEN)
    bot.run()
