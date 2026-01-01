# shadow_titan_rewrite_full.py
# Shadow Titan — complete rewritten single-file
# - enforced registration flow (name -> sex -> age)
# - admin panel as InlineKeyboard (glass-like buttons)
# - robust profanity filter (obfuscation resistant)
# - VIP time-based plans (including Xmas 3-month free, 4-day window)
# - invoice fallback + manual confirmation (/confirm_manual)
# - gift single / gift all with duration selector
# - improved state machine and bug fixes
#
# Replace TOKEN and OWNER_ID at top before running.

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
TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"   # <-- جایگزین کن
OWNER_ID = "8013245091"             # <-- جایگزین کن (رشته یا عدد)
CHANNEL = "@ChatNaAnnouncements"
SUPPORT = "@its_alimo"
HF_TOKEN = ""                        # اختیاری برای AI scan
PROVIDER_TOKEN = ""                  # اگر درگاه داری اینجا بذار؛ برای Stars معمولاً خالی است

DATA_DIR = "db_files"
LOG_FILE = "shadow_titan_rewrite.log"
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

CURRENCY = "XTR"

# VIP plans
VIP_PLANS = {
    "vip_1w":  {"days": 7,   "stars": 25,   "title": "VIP 1 هفته"},
    "vip_1m":  {"days": 30,  "stars": 100,  "title": "VIP 1 ماهه"},
    "vip_3m":  {"days": 90,  "stars": 280,  "title": "VIP 3 ماهه"},
    "vip_6m":  {"days": 180, "stars": 560,  "title": "VIP 6 ماهه"},
    "vip_12m": {"days": 365, "stars": 860,  "title": "VIP 1 ساله"},
    "vip_xmas_free": {"days": 90,  "stars": 0,   "title": "VIP کریسمس — 3 ماه (رایگان)"},
    "vip_xmas_paid": {"days": 365,"stars": 600, "title": "VIP کریسمس ویژه (پرداختی)"},
}

# Xmas free window in seconds
CHRISTMAS_WINDOW_SECONDS = 4 * 86400  # 4 days

# Iran timezone offset (no DST)
IRAN_OFFSET_H = 3
IRAN_OFFSET_M = 30
IRAN_OFFSET = datetime.timedelta(hours=IRAN_OFFSET_H, minutes=IRAN_OFFSET_M)

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- Logging ----------------
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ShadowTitanRewrite")

# ---------------- Flask keepalive ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Shadow Titan Rewritten — alive"

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

# ---------------- Profanity normalization ----------------
# Use user's full list expanded + robust normalize to defeat obfuscation
BAD_WORDS = [
    "کیر","کیرم","کیرت","کیری","کیرر","کیرتو","کیرش","کیرها",
    "کس","کص","کوس","کوث","کوص","کصص","کسکش","کسشر","کسخل","کسده","کصده",
    "جنده","جهنده","جنده‌باز","جنده‌خانه","جنده‌پرور",
    "مادرجنده","مادرجهنده","مادرجندت",
    "قحبه","قهبه","قحبه‌خان",
    "پدرسگ","پدرسوخته","پدرسک","پدرسگه",
    "حرامزاده","گاییدم","گاییدن","گایید","گاییدنی",
    "سیکتیر","سیک‌تر",
    "کون","کونی","کون دادن","کون‌گشاد",
    "گوه","گوخور",
    "لاشی","لاشخور","لاشه",
    "فاحشه","ناموس","ناموسی","ناموست",
    "سکس","سکسی","پورن",
    "خارکصه","تخمم","شاسگول","پفیوز","احمق","آشغال",
    "سگ‌مادر","دیوث","گوز","جق","مالیدن","بکن","بمال", "گای"
]
DIACRITICS_RE = re.compile(r'[\u064B-\u065F\u0610-\u061A\u06D6-\u06ED\u0640]')
def normalize_persian(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = s.replace('ك','ک').replace('ي','ی').replace('ى','ی').replace('ؤ','و').replace('إ','ا').replace('أ','ا')
    s = DIACRITICS_RE.sub('', s)
    s = s.replace('\u200c','').replace('\u200b','')
    # remove punctuation used for obfuscation and digits and spaces
    s = re.sub(r'[\s\.\-\_\*\|\\\/\:\;\'\"\,\(\)\[\]\{\}\?!ـ•·،؛•]', '', s)
    s = re.sub(r'[0-9۰-۹]', '', s)
    # keep letters only
    s = re.sub(r'[^آ-یa-zA-Z]', '', s)
    # collapse repeated letters (3+ -> 2)
    s = re.sub(r'(.)\1{2,}', r'\1\1', s)
    return s

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

# ---------------- Bot main ----------------
class ShadowTitanRewrite:
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
        logger.info("ShadowTitanRewrite init")
        self.register_handlers()

    # DB user helpers
    def ensure_user(self, uid):
        uid = str(uid)
        users = self.db.read("users")
        if uid not in users:
            users[uid] = {
                "state": "name",   # force registration
                "name": "",
                "sex": "",
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

    # payment helpers
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

    # Keyboards (glass-like = InlineKeyboard with emojis)
    def kb_main(self, uid):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        kb.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        kb.add("🎡 گردونه شانس روزانه", "🎖 خرید VIP (پلن‌ها)")
        kb.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        return kb

    def kb_chat(self):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        kb.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return kb

    def kb_report(self):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("🔇 فحاشی", callback_data="rep_insult"),
               types.InlineKeyboardButton("🔞 +18", callback_data="rep_nsfw"))
        kb.add(types.InlineKeyboardButton("📵 اسپم", callback_data="rep_spam"),
               types.InlineKeyboardButton("🚨 آزار", callback_data="rep_harass"))
        kb.add(types.InlineKeyboardButton("❌ لغو", callback_data="rep_cancel"))
        return kb

    def kb_vip_menu(self, uid):
        kb = types.InlineKeyboardMarkup(row_width=1)
        now = now_ts_utc()
        users = self.db.read("users")
        user = users.get(str(uid), {})
        if now < self.christmas_expires_at and not user.get("used_christmas", False):
            kb.add(types.InlineKeyboardButton("🎄 VIP 3 ماهه کریسمس (رایگان)", callback_data="buy_vip_free_xmas"))
        # show paid plans
        for key, p in VIP_PLANS.items():
            if key == "vip_xmas_free":
                continue
            kb.add(types.InlineKeyboardButton(f"{p['title']} — {p['stars']} ⭐", callback_data=f"buy_vip_paid|{key}"))
        return kb

    def kb_admin_panel(self):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("📈 آمار کامل", callback_data="adm_stats"),
            types.InlineKeyboardButton("🛠 تعمیر/نگهداری", callback_data="adm_toggle_maintenance"),
        )
        kb.add(
            types.InlineKeyboardButton("🎁 گیفت VIP تکی", callback_data="adm_gift_single"),
            types.InlineKeyboardButton("🎁 گیفت VIP همگانی", callback_data="adm_gift_all"),
        )
        kb.add(
            types.InlineKeyboardButton("❌ حذف VIP", callback_data="adm_remove_vip"),
            types.InlineKeyboardButton("📋 لیست VIP", callback_data="adm_list_vip"),
        )
        kb.add(
            types.InlineKeyboardButton("📁 دانلود دیتابیس", callback_data="adm_download_db"),
            types.InlineKeyboardButton("🚫 لیست بن‌شده‌ها", callback_data="adm_bans_list"),
        )
        kb.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back"))
        return kb

    def kb_duration_selector(self, prefix):
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

        @bot.message_handler(commands=['start'])
        def start(msg):
            uid = str(msg.chat.id)
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None
            users = self.db.read("users")
            user_exists = uid in users
            user = self.ensure_user(uid)
            # If payload anon link
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    bot.send_message(uid, "نمی‌توانید به خودتان پیام ناشناس بفرستید.")
                    return
                user["state"] = "anon_send"
                user["anon_target"] = target
                self.save_user(uid, user)
                bot.send_message(uid, "برای ارسال پیام ناشناس، پیام خود را بنویسید:")
                return

            # If user exists but name empty or state is name, force registration
            if not user_exists or user.get("state") in ("name","sex","age"):
                user["state"] = "name"
                user["name"] = ""
                user["sex"] = ""
                user["age"] = 0
                self.save_user(uid, user)
                bot.send_message(uid, "🌟 به Shadow Titan خوش آمدی!\nلطفاً نام مستعار خود را وارد کن:")
                return

            # otherwise normal welcome
            bot.send_message(uid, "خوش آمدی! 🎉", reply_markup=self.kb_main(uid))

        @bot.pre_checkout_query_handler(func=lambda q: True)
        def precheckout(q):
            try:
                bot.answer_pre_checkout_query(q.id, ok=True)
            except Exception as e:
                logger.error(f"precheckout error: {e}")

        @bot.message_handler(content_types=['successful_payment'])
        def successful_payment(msg):
            try:
                payload = ""
                try:
                    payload = msg.successful_payment.invoice_payload
                except:
                    payload = getattr(msg.successful_payment, 'payload', '')
                if not payload:
                    logger.warning("successful_payment without payload")
                    return
                payments = self.db.read("payments")
                if payload not in payments:
                    logger.warning(f"unknown payment payload {payload}")
                    return
                pay = payments[payload]
                uid = str(msg.chat.id)
                users = self.db.read("users")
                user = users.get(uid) or self.ensure_user(uid)
                plan_key = pay.get("plan")
                plan = VIP_PLANS.get(plan_key)
                if plan:
                    now = now_ts_utc()
                    start = max(now, int(user.get("vip_until",0)))
                    user["vip_until"] = start + int(plan["days"]) * 86400
                    users[uid] = user
                    self.db.write("users", users)
                    payments[payload]["done"] = True
                    self.db.write("payments", payments)
                    bot.send_message(uid, f"🎉 پرداخت موفق! {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
            except Exception as e:
                logger.error(f"successful_payment handler error: {e}")

        @bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def main(msg):
            try:
                uid = str(msg.chat.id)
                users = self.db.read("users")
                if uid not in users:
                    user = self.ensure_user(uid)
                else:
                    user = users[uid]

                bans = self.db.read("bans")
                cfg = self.db.read("config")

                # ban checks
                if uid in bans.get("permanent", {}):
                    return
                if uid in bans.get("temporary", {}) and now_ts_utc() < bans["temporary"][uid]["end"]:
                    return

                # maintenance
                if cfg.get("settings", {}).get("maintenance", False) and not (self.is_vip(user) or uid == self.owner):
                    bot.send_message(uid, "🔧 ربات در حالت تعمیر است. فقط VIPها دسترسی دارند.")
                    return

                # If user is in registration flow handle it first
                state = user.get("state", "idle")
                text = msg.text or ""

                if state == "name":
                    # check bad words
                    if not text or contains_bad(text):
                        bot.send_message(uid, "نام نامعتبر است. لطفاً نامی بدون کلمات نامناسب وارد کن:")
                        return
                    user["name"] = text.strip()[:30]
                    user["state"] = "sex"
                    self.save_user(uid, user)
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="reg_sex_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="reg_sex_f"))
                    bot.send_message(uid, f"خوب {user['name']}! حالا جنسیت خود را انتخاب کن:", reply_markup=kb)
                    return

                if state == "age":
                    if not text or not text.isdigit() or not 12 <= int(text) <= 99:
                        bot.send_message(uid, "سن نامعتبر. لطفاً عددی بین 12 و 99 وارد کن:")
                        return
                    user["age"] = int(text)
                    user["state"] = "idle"
                    self.save_user(uid, user)
                    bot.send_message(uid, "ثبت‌نام با موفقیت انجام شد 🎉", reply_markup=self.kb_main(uid))
                    return

                # anon_send
                if state == "anon_send":
                    if msg.content_type != 'text':
                        bot.send_message(uid, "فقط متن مجاز است برای پیام ناشناس.")
                        return
                    target = user.get("anon_target")
                    if not target:
                        bot.send_message(uid, "خطا در مقصد پیام ناشناس.")
                        user["state"] = "idle"
                        self.save_user(uid, user)
                        return
                    db_m = self.db.read("messages")
                    if target not in db_m.get("inbox", {}):
                        db_m.setdefault("inbox", {})[target] = []
                    db_m["inbox"].setdefault(target, []).append({
                        "text": msg.text,
                        "from": uid,
                        "seen": False,
                        "time": iran_now_dt().strftime("%H:%M %d/%m")
                    })
                    self.db.write("messages", db_m)
                    bot.send_message(uid, "✅ پیام ناشناس ارسال شد")
                    try:
                        bot.send_message(target, "📩 یک پیام ناشناس جدید دریافت کردید!")
                    except:
                        pass
                    user["state"] = "idle"
                    self.save_user(uid, user)
                    return

                # if in chat, route messages
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
                        self.save_user(uid, user)
                        bot.send_message(uid, "دلیل گزارش را انتخاب کن:", reply_markup=self.kb_report())
                        return

                    if text == "🚫 بلاک و خروج":
                        blocks = user.get("blocks", [])
                        if partner not in blocks:
                            blocks.append(partner)
                        user["blocks"] = blocks
                        self.save_user(uid, user)
                        self.end_chat(uid, partner, "بلاک کرد")
                        return

                    if text and contains_bad(text):
                        try:
                            bot.delete_message(uid, msg.message_id)
                        except:
                            pass
                        user["warns"] = user.get("warns", 0) + 1
                        self.save_user(uid, user)
                        if user["warns"] >= 3:
                            self.ban_perm(uid, "فحاشی مکرر")
                            self.end_chat(uid, partner, "بن شد")
                            return
                        bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3 – فحاشی ممنوع است!")
                        return

                    try:
                        bot.copy_message(partner, uid, msg.message_id)
                    except Exception as e:
                        logger.warning(f"copy_message error: {e}")
                    return

                # Not in chat and not in registration flow
                # Menu commands
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
                    try:
                        botname = self.bot.get_me().username
                    except:
                        botname = "ShadowTitanBot"
                    link = f"https://t.me/{botname}?start=msg_{uid}"
                    bot.send_message(uid, f"<b>لینک ناشناس شما</b>\n\n{link}")
                    return

                if text == "📥 پیام‌های ناشناس":
                    dbm = self.db.read("messages")
                    inbox = dbm.get("inbox", {}).get(uid, [])
                    if not inbox:
                        bot.send_message(uid, "هیچ پیام ناشناسی دریافت نکرده‌اید 📭")
                        return
                    kb = types.InlineKeyboardMarkup()
                    txt = "<b>پیام‌های ناشناس شما</b>\n\n"
                    for i, m in enumerate(inbox):
                        txt += f"{i+1}. {m['text']}\n<i>{m['time']}</i>\n\n"
                        kb.add(types.InlineKeyboardButton(f"پاسخ به پیام {i+1}", callback_data=f"anon_reply_{i}"))
                    bot.send_message(uid, txt, reply_markup=kb)
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
                        dbm["inbox"][uid] = inbox
                        self.db.write("messages", dbm)
                    return

                if text == "🎡 گردونه شانس روزانه":
                    today = iran_now_dt().strftime("%Y-%m-%d")
                    if user.get("last_spin") == today:
                        bot.send_message(uid, "امروز قبلاً گردونه را چرخانده‌اید 😊")
                        return
                    user["last_spin"] = today
                    self.save_user(uid, user)
                    if random.random() < 0.05:
                        now = now_ts_utc()
                        start = max(now, int(user.get("vip_until", 0)))
                        user["vip_until"] = start + 30 * 86400
                        self.save_user(uid, user)
                        bot.send_message(uid, f"🎉 تبریک! رنک VIP (۳۰ روزه) گرفتید. اعتبار تا: {ts_to_iran_str(user['vip_until'])}")
                    else:
                        bot.send_message(uid, "گردونه چرخید... پوچ! شانس بعدی را امتحان کنید 🌟")
                    return

                if text == "🎖 خرید VIP (پلن‌ها)":
                    # send features first with one message then the inline plan buttons
                    features = (
                        "<b>🎖 امکانات VIP</b>\n\n"
                        "• ارسال آزاد گیف و استیکر\n"
                        "• دسترسی به ربات در زمان تعمیر و نگهداری\n"
                        "• پیدا کردن سریع‌تر و بهتر هم‌صحبت\n\n"
                        "⏳ VIP زمان‌دار است\n"
                        "💳 پرداخت با Telegram Stars\n\n"
                        "پلن مورد نظر را انتخاب کنید:"
                    )
                    bot.send_message(uid, features, reply_markup=self.kb_vip_menu(uid))
                    return

                if text == "⚙ تنظیمات":
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    kb.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت")
                    kb.add("🔙 بازگشت به منو")
                    bot.send_message(uid, "تنظیمات:", reply_markup=kb)
                    return

                if text == "✏️ تغییر نام":
                    user["state"] = "change_name"
                    self.save_user(uid, user)
                    bot.send_message(uid, "نام جدید را وارد کن:")
                    return

                if user.get("state") == "change_name":
                    if contains_bad(text):
                        bot.send_message(uid, "نام نامعتبر است")
                        return
                    user["name"] = text[:30]
                    user["state"] = "idle"
                    self.save_user(uid, user)
                    bot.send_message(uid, "نام با موفقیت تغییر کرد ✅", reply_markup=self.kb_main(uid))
                    return

                if text == "🔢 تغییر سن":
                    user["state"] = "change_age"
                    self.save_user(uid, user)
                    bot.send_message(uid, "سن جدید را وارد کن:")
                    return

                if user.get("state") == "change_age":
                    if not text.isdigit() or not 12 <= int(text) <= 99:
                        bot.send_message(uid, "سن باید بین 12 و 99 باشد")
                        return
                    user["age"] = int(text)
                    user["state"] = "idle"
                    self.save_user(uid, user)
                    bot.send_message(uid, "سن ذخیره شد ✅", reply_markup=self.kb_main(uid))
                    return

                if text == "⚧ تغییر جنسیت":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="change_sex_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="change_sex_f"))
                    bot.send_message(uid, "جنسیت را انتخاب کن:", reply_markup=kb)
                    return

                # admin quick (show admin panel as inline)
                if str(uid) == str(self.owner) and text == "📊 پنل مدیریت":
                    bot.send_message(uid, "پنل مدیریت:", reply_markup=self.kb_admin_panel())
                    return

                # fallback
                bot.send_message(uid, "برای استفاده از ربات از دکمه‌های منو استفاده کن", reply_markup=self.kb_main(uid))

            except Exception as e:
                logger.error(f"main handler error: {e}")

        @bot.callback_query_handler(func=lambda c: True)
        def callback(c):
            try:
                uid = str(c.from_user.id)
                data = c.data or ""
                users = self.db.read("users")
                user = users.get(uid) or self.ensure_user(uid)

                # always answer callback to clear loading
                try:
                    bot.answer_callback_query(c.id)
                except:
                    pass

                # registration sex selection
                if data in ("reg_sex_m","reg_sex_f"):
                    user["sex"] = "آقا" if data == "reg_sex_m" else "خانم"
                    user["state"] = "age"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "سن خود را وارد کن (۱۲–۹۹):")
                    return

                # change sex from settings
                if data in ("change_sex_m","change_sex_f"):
                    user["sex"] = "آقا" if data == "change_sex_m" else "خانم"
                    user["state"] = "idle"
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, "جنسیت با موفقیت تغییر کرد ✅", reply_markup=self.kb_main(uid))
                    return

                # finding partner
                if data.startswith("find_"):
                    dbq = self.db.read("queue")
                    if uid not in dbq.get("general", []):
                        dbq["general"].append(uid)
                    self.db.write("queue", dbq)
                    bot.send_message(uid, "در حال جستجو برای هم‌صحبت...")
                    pots = [p for p in dbq.get("general", []) if p != uid]
                    pots = [p for p in pots if uid not in self.db.read("users").get(p, {}).get("blocks", [])]
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
                        bot.send_message(uid, "در صف قرار گرفتی؛ لطفاً صبور باش...")
                    return

                # anon reply
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
                    bot.send_message(uid, "پاسخ خود را بنویس:")
                    return

                # end chat confirmation
                if data == "end_yes":
                    partner = user.get("partner")
                    self.end_chat(uid, partner, "پایان داد")
                    return
                if data == "end_no":
                    bot.answer_callback_query(c.id, "چت ادامه دارد ✅")
                    return

                # reports
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

                # admin callbacks (panel)
                if data.startswith("adm_"):
                    if str(c.from_user.id) != str(self.owner):
                        bot.answer_callback_query(c.id, "مجاز نیستی")
                        return
                    # parse admin actions
                    if data == "adm_stats":
                        users = self.db.read("users")
                        total = len(users)
                        males = sum(1 for d in users.values() if d.get("sex") == "آقا")
                        females = total - males
                        now_ts = now_ts_utc()
                        vips = sum(1 for d in users.values() if int(d.get("vip_until",0)) > now_ts)
                        bot.send_message(self.owner, f"<b>آمار ربات</b>\n\nکل کاربران: {total}\nآقا: {males}\nخانم: {females}\nVIPها: {vips}")
                        return
                    if data == "adm_toggle_maintenance":
                        cfg = self.db.read("config")
                        s = cfg.get("settings", {})
                        is_on = s.get("maintenance", False)
                        s["maintenance"] = not is_on
                        cfg["settings"] = s
                        self.db.write("config", cfg)
                        status = "فعال 🟢" if s["maintenance"] else "غیرفعال 🔴"
                        bot.send_message(self.owner, f"حالت تعمیر و نگهداری: {status}")
                        return
                    if data == "adm_gift_single":
                        # ask admin to choose duration via duration selector
                        bot.send_message(self.owner, "مدت VIP برای گیفت تکی را انتخاب کنید:", reply_markup=self.kb_duration_selector("gift_single"))
                        return
                    if data == "adm_gift_all":
                        bot.send_message(self.owner, "مدت VIP برای گیفت همگانی را انتخاب کنید:", reply_markup=self.kb_duration_selector("gift_all"))
                        return
                    if data == "adm_remove_vip":
                        bot.send_message(self.owner, "آیدی عددی کاربر را وارد کنید تا VIP او حذف شود (یک پیام شامل آیدی بفرست):")
                        users = self.db.read("users")
                        users[self.owner]["state"] = "remove_vip"
                        self.db.write("users", users)
                        return
                    if data == "adm_list_vip":
                        users = self.db.read("users")
                        now_ts = now_ts_utc()
                        vips = [ (u, d) for u,d in users.items() if int(d.get("vip_until",0)) > now_ts ]
                        if not vips:
                            bot.send_message(self.owner, "هیچ کاربر VIP وجود ندارد")
                            return
                        msg = "<b>لیست VIPها</b>\n\n"
                        for u,d in vips:
                            end = ts_to_iran_str(d.get("vip_until"))
                            name = d.get("name","نامشخص")
                            msg += f"🆔 {u} - {name} (تا {end})\n"
                        bot.send_message(self.owner, msg)
                        return
                    if data == "adm_download_db":
                        # send files
                        for f in self.db.files.values():
                            if os.path.exists(f):
                                try:
                                    bot.send_document(self.owner, open(f,'rb'))
                                except Exception as e:
                                    logger.error(f"send db file error: {e}")
                        return
                    if data == "adm_bans_list":
                        bans = self.db.read("bans")
                        msg = "<b>بن‌شده‌ها</b>\n\n"
                        for u, r in bans.get("permanent", {}).items():
                            msg += f"🆔 {u} - {r} (دائم)\n"
                        for u, d in bans.get("temporary", {}).items():
                            end = datetime.datetime.fromtimestamp(d["end"]).strftime("%Y-%m-%d %H:%M")
                            msg += f"🆔 {u} - موقت تا {end}\n"
                        bot.send_message(self.owner, msg)
                        return
                    if data == "adm_back":
                        bot.send_message(self.owner, "بازگشت به منو مدیریت", reply_markup=self.kb_admin_panel())
                        return

                # gift duration selected (admin)
                if data.startswith("gift_single_"):
                    # set admin state to expect target id
                    days = int(data.split("_")[2])
                    users = self.db.read("users")
                    users[self.owner]["gift_days"] = days
                    users[self.owner]["state"] = "gift_single_id"
                    self.db.write("users", users)
                    bot.send_message(self.owner, f"مدت انتخاب شد: {days} روز\nلطفاً آیدی عددی کاربر را وارد کن:")
                    return

                if data.startswith("gift_all_"):
                    days = int(data.split("_")[2])
                    users = self.db.read("users")
                    users[self.owner]["gift_days"] = days
                    users[self.owner]["state"] = "gift_all_reason"
                    self.db.write("users", users)
                    bot.send_message(self.owner, f"مدت انتخاب شد: {days} روز\nلطفاً دلیل گیفت همگانی را وارد کن:")
                    return

                # buy VIP free Xmas
                if data == "buy_vip_free_xmas":
                    now = now_ts_utc()
                    if now > self.christmas_expires_at:
                        bot.answer_callback_query(c.id, "مهلت دریافت این پلن به پایان رسیده")
                        return
                    if user.get("used_christmas", False):
                        bot.answer_callback_query(c.id, "قبلاً این پلن را گرفته‌اید")
                        return
                    start = max(now, int(user.get("vip_until",0)))
                    user["vip_until"] = start + VIP_PLANS["vip_xmas_free"]["days"] * 86400
                    user["used_christmas"] = True
                    users[uid] = user
                    self.db.write("users", users)
                    bot.send_message(uid, f"🎉 VIP سه‌ماهه رایگان فعال شد — دلیل: ویژه کریسمس 🎄\nاعتبار تا: {ts_to_iran_str(user['vip_until'])}")
                    return

                # buy vip paid (invoice)
                if data.startswith("buy_vip_paid|"):
                    _, plan_key = data.split("|",1)
                    plan = VIP_PLANS.get(plan_key)
                    if not plan:
                        bot.answer_callback_query(c.id, "پلن نامعتبر")
                        return
                    if int(plan.get("stars",0)) == 0:
                        bot.answer_callback_query(c.id, "این پلن رایگان است")
                        return
                    payload = self.make_payload(uid, plan_key)
                    prices = [types.LabeledPrice(label=plan["title"], amount=int(plan["stars"]))]
                    try:
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
                        self.register_payment(payload, uid, plan_key, plan["stars"])
                        bot.answer_callback_query(c.id, "فاکتور ارسال شد ✅")
                    except Exception as e:
                        logger.error(f"send_invoice error for {uid} plan {plan_key}: {e}")
                        # register payment for manual flow
                        self.register_payment(payload, uid, plan_key, plan["stars"])
                        kb = types.InlineKeyboardMarkup()
                        kb.add(types.InlineKeyboardButton("✅ اعلام پرداخت (دستی)", callback_data=f"manual_paid|{payload}"))
                        bot.send_message(uid,
                                         "⚠️ خطا در ایجاد فاکتور اتوماتیک. می‌توانید پرداخت دستی انجام دهید و سپس 'اعلام پرداخت' را بزنید.\n"
                                         f"کد پیگیری: <code>{payload}</code>",
                                         reply_markup=kb)
                        bot.answer_callback_query(c.id, "خطا در ایجاد فاکتور — گزینه پرداخت دستی ارسال شد")
                    return

                # manual paid notify admin
                if data.startswith("manual_paid|"):
                    payload = data.split("|",1)[1]
                    payments = self.db.read("payments")
                    pay = payments.get(payload)
                    if not pay:
                        bot.answer_callback_query(c.id, "پرداخت نامشخص")
                        return
                    bot.send_message(self.owner, f"اعلام پرداخت دستی از {uid}\nکد: {payload}\nمبلغ: {pay.get('amount')}\nپلن: {pay.get('plan')}\nدر صورت تایید: /confirm_manual {payload}")
                    bot.send_message(uid, "اعلام پرداخت ثبت شد؛ ادمین پس از بررسی آن را تایید می‌کند.")
                    return

                # default fallback
                bot.answer_callback_query(c.id, "عملیات انجام شد")
            except Exception as e:
                logger.error(f"callback handler error: {e}")

        # admin confirms manual payment
        @bot.message_handler(commands=["confirm_manual"])
        def confirm_manual(msg):
            if str(msg.chat.id) != str(self.owner):
                return
            args = msg.text.split()
            if len(args) < 2:
                bot.send_message(self.owner, "Usage: /confirm_manual <payload>")
                return
            payload = args[1]
            payments = self.db.read("payments")
            pay = payments.get(payload)
            if not pay:
                bot.send_message(self.owner, "پرداخت پیدا نشد")
                return
            if pay.get("done"):
                bot.send_message(self.owner, "این پرداخت قبلاً ثبت شده")
                return
            uid = pay.get("uid")
            plan_key = pay.get("plan")
            plan = VIP_PLANS.get(plan_key)
            if not plan:
                bot.send_message(self.owner, "پلن نامشخص")
                return
            users = self.db.read("users")
            user = users.get(uid) or self.ensure_user(uid)
            now = now_ts_utc()
            start = max(now, int(user.get("vip_until",0)))
            user["vip_until"] = start + int(plan["days"]) * 86400
            users[uid] = user
            payments[payload]["done"] = True
            self.db.write("users", users)
            self.db.write("payments", payments)
            bot.send_message(self.owner, f"✅ پرداخت دستی با کد {payload} تایید شد و VIP اعمال شد.")
            try:
                bot.send_message(uid, f"🎉 پرداخت شما تایید شد. پلن {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
            except:
                pass

    # admin helpers
    def ban_perm(self, uid, reason="تخلف"):
        bans = self.db.read("bans")
        bans.setdefault("permanent", {})[str(uid)] = reason
        self.db.write("bans", bans)
        logger.info(f"perm ban {uid} reason {reason}")

    def ban_temp(self, uid, minutes=60, reason="تخلف"):
        bans = self.db.read("bans")
        end = now_ts_utc() + minutes * 60
        bans.setdefault("temporary", {})[str(uid)] = {"end": end, "reason": reason}
        self.db.write("bans", bans)
        logger.info(f"temp ban {uid} until {end}")

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
        logger.info("Bot polling start")
        try:
            self.bot.infinity_polling()
        except Exception as e:
            logger.error(f"polling crashed: {e}")
            time.sleep(2)
            try:
                self.bot.infinity_polling()
            except Exception as e2:
                logger.error(f"second crash: {e2}")
                sys.exit(1)

# ---------------- Entrypoint ----------------
if __name__ == "__main__":
    if TOKEN == "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU":
        print("لطفاً TOKEN را در بالای فایل تنظیم کنید.")
        sys.exit(1)
    bot = ShadowTitanRewrite(TOKEN)
    bot.run()
