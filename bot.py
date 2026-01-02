#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shadow Titan - complete fixed version
Features:
 - Registration (name/sex/age)
 - Anonymous chat matching (queue)
 - Anonymous messages via start payload
 - VIP plans (Stars/XTR) + Xmas free 3-month limited window
 - Payments (invoice + manual fallback)
 - Admin panel actions (basic)
 - Profanity detection robust (normalization)
 - HF moderation hooks (optional)
 - Persistent JSON DB with locking
 - Safe send wrapper, backups, basic housekeeping
"""

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
import traceback
from typing import Dict, Any

# Optional: run a tiny web server to keep bot alive on some hosts (Heroku-like)
try:
    from flask import Flask
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False

try:
    import telebot
    from telebot import types
except Exception:
    print("pyTelegramBotAPI required. Install: pip install pyTelegramBotAPI")
    raise

try:
    import requests
except Exception:
    print("requests required. Install: pip install requests")
    raise

# -----------------------------
# CONFIG (edit as needed)
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # prefer env var
BOT_TOKEN_DIRECT = ""  # e.g. "123456:ABC-DEF..." if you must paste (keep empty for safety)
if not BOT_TOKEN:
    BOT_TOKEN = BOT_TOKEN_DIRECT

PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN", "")  # payment provider token (Stars/XTR)
HF_TOKEN = os.getenv("HF_TOKEN", "")  # HuggingFace token for optional moderation
OWNER_ID = str(os.getenv("OWNER_ID", "") or "8013245091")
CHANNEL = os.getenv("CHANNEL", "") or "@ChatNaAnnouncements"
SUPPORT = os.getenv("SUPPORT", "") or "@its_alimo"

# VIP plans config (stars)
VIP_PLANS = {
    "vip_1w":  {"days": 7,   "stars": 25,  "title": "VIP 1 هفته"},
    "vip_1m":  {"days": 30,  "stars": 100, "title": "VIP 1 ماهه"},
    "vip_3m":  {"days": 90,  "stars": 280, "title": "VIP 3 ماهه"},
    "vip_6m":  {"days": 180, "stars": 560, "title": "VIP 6 ماهه"},
    "vip_12m": {"days": 365, "stars": 860, "title": "VIP 1 ساله"},
    # xmas is free special 3-month plan (stars=0)
    "vip_xmas":{"days": 90,  "stars": 0,   "title": "VIP کریسمس — 3 ماه (رایگان)"}
}
# Xmas availability window after bot first run (seconds)
XMAS_WINDOW_SECONDS = 4 * 24 * 3600

CURRENCY = "XTR"  # currency used for invoice (Stars token)

# -----------------------------
# Storage files
# -----------------------------
DATA_DIR = "shadow_titan_data"
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "users": os.path.join(DATA_DIR, "db_users.json"),
    "bans": os.path.join(DATA_DIR, "db_bans.json"),
    "queue": os.path.join(DATA_DIR, "db_queue.json"),
    "messages": os.path.join(DATA_DIR, "db_messages.json"),
    "config": os.path.join(DATA_DIR, "db_config.json"),
    "payments": os.path.join(DATA_DIR, "db_payments.json"),
    "backups": os.path.join(DATA_DIR, "db_backups.json")
}

# -----------------------------
# Logging
# -----------------------------
LOG_FILE = os.path.join(DATA_DIR, "shadow_titan.log")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ShadowTitan")

# -----------------------------
# Time helpers (Iran UTC+3:30)
# -----------------------------
IRAN_OFFSET = datetime.timedelta(hours=3, minutes=30)

def now_ts() -> int:
    return int(time.time())

def iran_now_dt() -> datetime.datetime:
    return datetime.datetime.utcnow() + IRAN_OFFSET

def ts_to_iran_str(ts: int) -> str:
    try:
        return (datetime.datetime.utcfromtimestamp(int(ts)) + IRAN_OFFSET).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

# -----------------------------
# Simple thread-safe JSON DB
# -----------------------------
class SimpleDB:
    def __init__(self, files: Dict[str,str]):
        self.files = files
        self.lock = threading.Lock()
        self._ensure_files()

    def _ensure_files(self):
        defaults = {
            "users": {},
            "bans": {"permanent": {}, "temporary": {}},
            "queue": {"general": []},
            "messages": {"inbox": {}},
            "config": {"settings": {"maintenance": False}, "start_ts": now_ts(), "broadcast": {"text": None}},
            "payments": {},
            "backups": {}
        }
        with self.lock:
            for k, p in self.files.items():
                if not os.path.exists(p):
                    try:
                        with open(p, "w", encoding="utf-8") as f:
                            json.dump(defaults.get(k, {}), f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error("Failed to create %s: %s", p, e)

    def read(self, key: str):
        path = self.files.get(key)
        if not path:
            return {}
        with self.lock:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("DB read %s error: %s", key, e)
                return {}

    def write(self, key: str, data):
        path = self.files.get(key)
        if not path:
            return
        with self.lock:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error("DB write %s error: %s", key, e)

db = SimpleDB(FILES)

# -----------------------------
# Profanity detection + normalization
# -----------------------------
BAD_WORDS = [
    "کیر","کیرد","کیرت","کیرم","کیری","کیریش","کیرها",
    "کس","کسکش","کسکول","کص","کوس","کوسم","کوسش",
    "کون","کونی","کونم","گای","گایید","گاییدن","گاییدم",
    "گوه","گوهخور","گوخور","گوز","گوزی","جنده","قحبه",
    "فاحشه","پدرسگ","پدرسوخته","ناموس","سکس","پورن",
    "لاش","لاشی","احمق","خر","دیوث","جق","مالیدن","بکن",
    "مرتیکه","شاسگول","کسخل","کسده","کسشر","مادرجنده"
]

DIACRITICS_RE = re.compile(r'[\u064B-\u065F\u0610-\u061A\u06D6-\u06ED\u0640]')
ZERO_WIDTH_RE = re.compile(r'[\u200b\u200c]')
PUNCT_RE = re.compile(r'[\s\.\-\_\*\|\\\/\:\;\'\"\,\(\)\[\]\{\}\?\!\،\؛•·–]')
DIGIT_RE = re.compile(r'[0-9۰-۹]')
REPEAT_RE = re.compile(r'(.)\1{2,}')

def normalize_persian(text: str) -> str:
    if not text:
        return ""
    s = text.lower()
    s = s.replace('ك', 'ک').replace('ي', 'ی').replace('ى', 'ی').replace('ؤ', 'و').replace('أ', 'ا').replace('إ', 'ا')
    s = DIACRITICS_RE.sub('', s)
    s = ZERO_WIDTH_RE.sub('', s)
    s = s.replace('ـ', '')
    s = PUNCT_RE.sub('', s)
    s = DIGIT_RE.sub('', s)
    s = REPEAT_RE.sub(r'\1\1', s)
    return s

BAD_NORM = [normalize_persian(w) for w in BAD_WORDS]

def contains_bad(text: str) -> bool:
    if not text:
        return False
    n = normalize_persian(text)
    for bw in BAD_NORM:
        if bw and bw in n:
            return True
    return False

# -----------------------------
# Utilities
# -----------------------------
def rand_token(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def make_payload(uid: str, plan_key: str) -> str:
    return f"{plan_key}_{uid}_{now_ts()}_{rand_token(6)}"

def safe_send(bot: telebot.TeleBot, chat_id: int, text: str, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logger.warning("send_message failed to %s: %s", chat_id, e)
        return None

# -----------------------------
# Optional HF moderation wrappers
# -----------------------------
def hf_text_toxicity_score(text: str) -> float:
    if not HF_TOKEN:
        return 0.0
    try:
        url = "https://api-inference.huggingface.co/models/unitary/toxic-bert"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        resp = requests.post(url, headers=headers, json={"inputs": text}, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                for item in data[0]:
                    if item.get("label", "").lower() == "toxic":
                        return float(item.get("score", 0.0))
    except Exception as e:
        logger.debug("hf_text_toxicity_score error: %s", e)
    return 0.0

def hf_image_nsfw_score(image_bytes: bytes) -> float:
    if not HF_TOKEN:
        return 0.0
    try:
        url = "https://api-inference.huggingface.co/models/michellejieli/nsfw_detector"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        files = {"file": image_bytes}
        resp = requests.post(url, headers=headers, files=files, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "nsfw_score" in data:
                return float(data.get("nsfw_score", 0.0))
    except Exception as e:
        logger.debug("hf_image_nsfw_score error: %s", e)
    return 0.0

# -----------------------------
# Keyboards
# -----------------------------
def kb_main(uid: str) -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
    kb.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
    kb.add("🎡 گردونه شانس روزانه", "🎖 خرید VIP (پلن‌ها)")
    kb.add("❓ راهنما و قوانین", "⚙ تنظیمات")
    if str(uid) == OWNER_ID:
        kb.add("📊 پنل مدیریت")
    return kb

def kb_chatting() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
    kb.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
    return kb

def vip_inline_menu(uid: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    cfg = db.read("config")
    start = cfg.get("start_ts", now_ts())
    users = db.read("users")
    user = users.get(str(uid), {})
    # show Xmas if within window and not used
    if now_ts() <= start + XMAS_WINDOW_SECONDS and not user.get("used_xmas", False):
        kb.add(types.InlineKeyboardButton(VIP_PLANS["vip_xmas"]["title"], callback_data="buy_xmas"))
    for key, plan in VIP_PLANS.items():
        if key == "vip_xmas":
            continue
        kb.add(types.InlineKeyboardButton(f"{plan['title']} — {plan['stars']} ⭐", callback_data=f"buy|{key}"))
    return kb

def kb_admin() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("📈 آمار کامل", callback_data="adm_stats"),
           types.InlineKeyboardButton("🛠 تعمیر/نگهداری", callback_data="adm_maint"))
    kb.add(types.InlineKeyboardButton("🎖 گیفت VIP تکی", callback_data="adm_gift_single"),
           types.InlineKeyboardButton("🎖 گیفت VIP همگانی", callback_data="adm_gift_all"))
    kb.add(types.InlineKeyboardButton("❌ حذف VIP", callback_data="adm_remove_vip"),
           types.InlineKeyboardButton("📋 لیست VIP", callback_data="adm_list_vip"))
    kb.add(types.InlineKeyboardButton("📁 دانلود دیتابیس", callback_data="adm_download_db"),
           types.InlineKeyboardButton("📤 خروجی CSV", callback_data="adm_export_csv"))
    kb.add(types.InlineKeyboardButton("📥 بازیابی بکاپ", callback_data="adm_restore"),
           types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back"))
    return kb

def kb_report_inline() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
           types.InlineKeyboardButton("+18", callback_data="rep_nsfw"))
    kb.add(types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
           types.InlineKeyboardButton("آزار", callback_data="rep_harass"))
    kb.add(types.InlineKeyboardButton("لغو ❌", callback_data="rep_cancel"))
    return kb

def duration_choice_kb(prefix: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("1 هفته", callback_data=f"{prefix}_7"),
           types.InlineKeyboardButton("1 ماه", callback_data=f"{prefix}_30"))
    kb.add(types.InlineKeyboardButton("3 ماه", callback_data=f"{prefix}_90"),
           types.InlineKeyboardButton("6 ماه", callback_data=f"{prefix}_180"))
    kb.add(types.InlineKeyboardButton("1 سال", callback_data=f"{prefix}_365"))
    return kb

# -----------------------------
# Bot core
# -----------------------------
class ShadowTitanBot:
    def __init__(self, token: str):
        self.token = token or BOT_TOKEN
        if not self.token:
            logger.error("BOT token is not set.")
            print("ERROR: BOT token is not set. Set BOT_TOKEN env or BOT_TOKEN_DIRECT in file.")
            sys.exit(1)
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.owner = str(OWNER_ID)
        self.provider_token = PROVIDER_TOKEN
        # init housekeeping timestamps
        cfg = db.read("config")
        self.start_ts = cfg.get("start_ts", now_ts())
        self.xmas_expire_ts = self.start_ts + XMAS_WINDOW_SECONDS
        # register handlers
        self.register_handlers()
        # start background workers
        self._start_background_workers()
        logger.info("ShadowTitanBot initialized")

    # ---- user helpers ----
    def ensure_user(self, uid: str) -> Dict[str, Any]:
        uid = str(uid)
        users = db.read("users")
        if uid not in users:
            users[uid] = {
                "state": "name",
                "name": "",
                "sex": "",
                "age": 0,
                "warns": 0,
                "partner": None,
                "vip_until": 0,
                "blocks": [],
                "last_spin": "",
                "used_xmas": False,
                "anon_target": None,
                "last_chat_msg_id": None,
                "report_target": None,
                "report_last_msg_id": None,
                "gift_days": 0
            }
            db.write("users", users)
        return users[uid]

    def save_user(self, uid: str, data: Dict[str, Any]):
        users = db.read("users")
        users[str(uid)] = data
        db.write("users", users)

    def is_vip(self, uid_or_user) -> bool:
        if isinstance(uid_or_user, str):
            users = db.read("users")
            user = users.get(uid_or_user, {})
        else:
            user = uid_or_user or {}
        try:
            return int(user.get("vip_until", 0)) > now_ts()
        except Exception:
            return False

    # ---- payments ----
    def register_payment(self, payload: str, uid: str, plan_key: str, amount: int):
        payments = db.read("payments")
        payments[payload] = {"uid": str(uid), "plan": plan_key, "amount": int(amount), "time": now_ts(), "done": False}
        db.write("payments", payments)
        logger.info("Registered payment %s for %s plan %s amount %s", payload, uid, plan_key, amount)

    def mark_payment_done(self, payload: str):
        payments = db.read("payments")
        if payload in payments:
            payments[payload]["done"] = True
            db.write("payments", payments)
            logger.info("Payment payload %s marked done", payload)
            return payments[payload]
        return None

    # ---- background ----
    def _start_background_workers(self):
        def worker():
            while True:
                try:
                    # hourly backup at minute 0
                    if datetime.datetime.utcnow().minute == 0:
                        self._create_backup()
                    time.sleep(60)
                except Exception as e:
                    logger.error("Background worker error: %s", e)
                    time.sleep(5)
        th = threading.Thread(target=worker, daemon=True)
        th.start()

    def _create_backup(self):
        try:
            timestamp = iran_now_dt().strftime("%Y%m%d%H%M%S")
            snap = {}
            for k in FILES.keys():
                snap[k] = db.read(k)
            backups = db.read("backups")
            backups[timestamp] = snap
            db.write("backups", backups)
            logger.info("Backup %s created", timestamp)
            # keep last 60
            if len(backups) > 60:
                keys = sorted(backups.keys())
                for k in keys[:-60]:
                    del backups[k]
                db.write("backups", backups)
        except Exception as e:
            logger.error("Backup failed: %s", e)

    # ---- register handlers ----
    def register_handlers(self):
        bot = self.bot

        # /start handler
        @bot.message_handler(commands=['start'])
        def handle_start(msg):
            uid = str(msg.chat.id)
            payload = None
            if msg.text and len(msg.text.split()) > 1:
                payload = msg.text.split(maxsplit=1)[1]
            user = self.ensure_user(uid)
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    safe_send(bot, int(uid), "نمی‌توانید به خودتان پیام ناشناس بفرستید 😊")
                    return
                user["state"] = "anon_send"
                user["anon_target"] = target
                self.save_user(uid, user)
                safe_send(bot, int(uid), "برای ارسال پیام ناشناس، متن را بفرستید ✉️")
                return
            # if incomplete registration, ask name
            if user.get("state") in ("name", "sex", "age"):
                user["state"] = "name"
                user["name"] = ""
                user["sex"] = ""
                user["age"] = 0
                self.save_user(uid, user)
                safe_send(bot, int(uid), "🌟 به Shadow Titan خوش آمدی! لطفاً نام مستعار خود را وارد کن:")
                return
            safe_send(bot, int(uid), "خوش برگشتی عزیز 🌹", reply_markup=kb_main(uid))

        # pre-checkout (answer)
        @bot.pre_checkout_query_handler(func=lambda q: True)
        def pre_checkout(q):
            try:
                bot.answer_pre_checkout_query(q.id, ok=True)
            except Exception as e:
                logger.error("pre_checkout error: %s", e)

        # successful payment handler
        @bot.message_handler(content_types=['successful_payment'])
        def successful_payment_handler(msg):
            try:
                payload = ""
                try:
                    payload = msg.successful_payment.invoice_payload
                except Exception:
                    payload = getattr(msg.successful_payment, 'payload', '')
                if not payload:
                    logger.warning("successful_payment without payload")
                    return
                payments = db.read("payments")
                if payload not in payments:
                    logger.warning("unknown payment payload: %s", payload)
                    return
                pay = payments[payload]
                uid = str(msg.chat.id)
                users = db.read("users")
                user = users.get(uid) or self.ensure_user(uid)
                plan_key = pay.get("plan")
                plan = VIP_PLANS.get(plan_key)
                if plan:
                    now = now_ts()
                    start_until = max(now, int(user.get("vip_until", 0)))
                    user["vip_until"] = start_until + plan["days"] * 86400
                    users[uid] = user
                    pay["done"] = True
                    db.write("users", users)
                    payments[payload] = pay
                    db.write("payments", payments)
                    safe_send(bot, int(uid), f"🎉 پرداخت موفق! {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
            except Exception as e:
                logger.error("successful_payment_handler error: %s", e)
                logger.debug(traceback.format_exc())

        # main messages
        @bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def main_handler(msg):
            uid = str(msg.chat.id)
            text = msg.text or ""
            users = db.read("users")
            user = users.get(uid) or self.ensure_user(uid)
            bans = db.read("bans")
            cfg = db.read("config")

            # ban checks
            if uid in bans.get("permanent", {}):
                return
            if uid in bans.get("temporary", {}) and now_ts() < bans["temporary"][uid]["end"]:
                return

            # maintenance
            if cfg.get("settings", {}).get("maintenance", False) and not (self.is_vip(user) or uid == self.owner):
                safe_send(bot, int(uid), "🔧 ربات در حال تعمیر است. فقط VIP دسترسی دارد.")
                return

            # registration flow
            if user.get("state") == "name":
                if not text or contains_bad(text):
                    safe_send(bot, int(uid), "نام نامعتبر — لطفاً نام مستعار مناسب وارد کن:")
                    return
                user["name"] = text.strip()[:30]
                user["state"] = "sex"
                self.save_user(uid, user)
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="reg_sex_m"),
                       types.InlineKeyboardButton("خانم 👧", callback_data="reg_sex_f"))
                safe_send(bot, int(uid), f"سلام {user['name']} 🌸\nجنسیت خود را انتخاب کنید:", reply_markup=kb)
                return

            if user.get("state") == "age":
                if not text or not text.isdigit() or not 12 <= int(text) <= 99:
                    safe_send(bot, int(uid), "سن نامعتبر — عدد بین ۱۲ تا ۹۹ وارد کنید:")
                    return
                user["age"] = int(text)
                user["state"] = "idle"
                self.save_user(uid, user)
                safe_send(bot, int(uid), "ثبت‌نام موفق 🎉", reply_markup=kb_main(uid))
                return

            # anon link send state
            if user.get("state") == "anon_send":
                if msg.content_type != "text":
                    safe_send(bot, int(uid), "❌ فقط متن برای پیام ناشناس مجاز است")
                    return
                target = user.get("anon_target")
                if not target:
                    safe_send(bot, int(uid), "مقصد نامشخص شد — دوباره تلاش کنید")
                    user["state"] = "idle"; self.save_user(uid, user)
                    return
                mdb = db.read("messages")
                inbox = mdb.get("inbox", {})
                inbox.setdefault(str(target), []).append({
                    "text": text, "from": uid, "seen": False,
                    "time": iran_now_dt().strftime("%H:%M %d/%m")
                })
                mdb["inbox"] = inbox
                db.write("messages", mdb)
                safe_send(bot, int(uid), "✅ پیام ناشناس ارسال شد")
                try:
                    safe_send(bot, int(target), "📩 یک پیام ناشناس جدید دریافت کردید!")
                except Exception:
                    logger.debug("notify failed")
                user["state"] = "idle"; self.save_user(uid, user)
                return

            # if inside chat with partner
            if user.get("partner"):
                partner = user["partner"]
                if text == "🔚 پایان گفتگو":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("بله، پایان بده", callback_data="end_yes"),
                           types.InlineKeyboardButton("خیر، ادامه بده", callback_data="end_no"))
                    safe_send(bot, int(uid), "آیا مطمئنی؟", reply_markup=kb)
                    return

                if text == "🚩 گزارش تخلف":
                    user["report_target"] = partner
                    user["report_last_msg_id"] = msg.message_id
                    self.save_user(uid, user)
                    safe_send(bot, int(uid), "دلیل گزارش:", reply_markup=kb_report_inline())
                    return

                if text == "🚫 بلاک و خروج":
                    blocks = user.get("blocks", [])
                    if partner not in blocks:
                        blocks.append(partner)
                    user["blocks"] = blocks
                    self.save_user(uid, user)
                    self.end_chat(uid, partner, "بلاک کرد")
                    return

                if text == "👥 درخواست آیدی":
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("بله ✅", callback_data=f"id_share_yes_{uid}"),
                           types.InlineKeyboardButton("خیر ❌", callback_data="id_share_no"))
                    safe_send(bot, int(partner), "هم‌صحبت درخواست آیدی شما را دارد. موافقید؟", reply_markup=kb)
                    safe_send(bot, int(uid), "درخواست ارسال شد")
                    return

                # profanity check
                if text and contains_bad(text):
                    try:
                        bot.delete_message(int(uid), msg.message_id)
                    except Exception:
                        pass
                    user["warns"] = user.get("warns", 0) + 1
                    self.save_user(uid, user)
                    if user["warns"] >= 3:
                        self.ban_perm(uid, "فحاشی مکرر")
                        self.end_chat(uid, partner, "بن شد")
                        return
                    safe_send(bot, int(uid), f"⚠️ اخطار {user['warns']}/3 – فحاشی ممنوع است!")
                    return

                # HF scan optional
                toxic_score = hf_text_toxicity_score(text)
                if toxic_score > 0.85:
                    try:
                        bot.delete_message(int(uid), msg.message_id)
                    except Exception:
                        pass
                    user["warns"] = user.get("warns", 0) + 1
                    self.save_user(uid, user)
                    if user["warns"] >= 3:
                        self.ban_perm(uid, "محتوای نامناسب (AI)")
                        self.end_chat(uid, partner, "بن شد")
                        return
                    safe_send(bot, int(uid), f"⚠️ اخطار {user['warns']}/3 – محتوای نامناسب شناسایی شد")
                    return

                # copy to partner
                try:
                    bot.copy_message(int(partner), int(uid), msg.message_id)
                except Exception as e:
                    logger.debug("copy_message failed: %s", e)
                return

            # Not in chat: main menu actions
            if text == "🛰 شروع چت ناشناس":
                kb = types.InlineKeyboardMarkup(row_width=3)
                kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                       types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                       types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any"))
                safe_send(bot, int(uid), "دنبال چه کسی می‌گردی؟", reply_markup=kb)
                return

            if text == "👤 پروفایل من":
                vip_status = "🎖 VIP" if self.is_vip(user) else "عادی"
                vip_until = user.get("vip_until", 0)
                vip_until_str = "ندارد"
                if vip_until and vip_until > now_ts():
                    vip_until_str = ts_to_iran_str(vip_until)
                safe_send(bot, int(uid),
                          f"<b>پروفایل شما</b>\n\n"
                          f"نام: {user.get('name','نامشخص')}\n"
                          f"جنسیت: {user.get('sex','نامشخص')}\n"
                          f"سن: {user.get('age','نامشخص')}\n"
                          f"رنک: {vip_status}\n"
                          f"اعتبار VIP تا: {vip_until_str}\n"
                          f"اخطار: {user.get('warns', 0)}")
                return

            if text == "📩 لینک ناشناس من":
                try:
                    botname = self.bot.get_me().username
                except Exception:
                    botname = "ShadowTitanBot"
                link = f"https://t.me/{botname}?start=msg_{uid}"
                safe_send(bot, int(uid), f"<b>لینک ناشناس شما</b>\n\n{link}")
                return

            if text == "📥 پیام‌های ناشناس":
                mdb = db.read("messages")
                inbox = mdb.get("inbox", {}).get(uid, [])
                if not inbox:
                    safe_send(bot, int(uid), "هیچ پیام ناشناسی ندارید")
                    return
                kb = types.InlineKeyboardMarkup()
                txt = "<b>پیام‌های ناشناس شما</b>\n\n"
                for i, m in enumerate(inbox):
                    txt += f"{i+1}. {m['text']}\n<i>{m['time']}</i>\n\n"
                    kb.add(types.InlineKeyboardButton(f"پاسخ به پیام {i+1}", callback_data=f"anon_reply_{i}"))
                safe_send(bot, int(uid), txt, reply_markup=kb)
                updated = False
                for m in inbox:
                    if not m.get("seen"):
                        m["seen"] = True
                        updated = True
                        try:
                            safe_send(bot, int(m["from"]), "✅ پیام شما دیده شد")
                        except Exception:
                            pass
                if updated:
                    mdb["inbox"][uid] = inbox
                    db.write("messages", mdb)
                return

            if text == "🎡 گردونه شانس روزانه":
                today = iran_now_dt().strftime("%Y-%m-%d")
                if user.get("last_spin") == today:
                    safe_send(bot, int(uid), "امروز قبلاً گردونه را زدی")
                    return
                user["last_spin"] = today
                # 5% chance => 30 day VIP
                if random.random() < 0.05:
                    now = now_ts()
                    start_until = max(now, int(user.get("vip_until", 0)))
                    user["vip_until"] = start_until + 30 * 86400
                    self.save_user(uid, user)
                    safe_send(bot, int(uid), f"🎉 برنده شدی! VIP 30 روزه — اعتبار تا {ts_to_iran_str(user['vip_until'])}")
                else:
                    self.save_user(uid, user)
                    safe_send(bot, int(uid), "متاسفانه اینبار نه — دوباره شانس رو امتحان کن")
                return

            if text == "🎖 خرید VIP (پلن‌ها)":
                features = ("<b>🎖 خرید رنک VIP Shadow Titan</b>\n\n"
                            "✨ امکانات VIP:\n"
                            "• ارسال آزاد گیف و استیکر\n"
                            "• دسترسی به ربات در زمان تعمیر\n"
                            "• اتصال سریع‌تر به هم‌صحبت\n\n"
                            "⏳ VIP زمان‌دار است\n"
                            "💳 پرداخت با Telegram Stars (یا پرداخت دستی)")
                safe_send(bot, int(uid), features, reply_markup=vip_inline_menu(uid))
                return

            if text == "⚙ تنظیمات":
                kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                kb.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت")
                kb.add("🔙 بازگشت به منو")
                safe_send(bot, int(uid), "تنظیمات:", reply_markup=kb)
                return

            if text == "✏️ تغییر نام":
                user["state"] = "change_name"
                self.save_user(uid, user)
                safe_send(bot, int(uid), "نام جدید را وارد کنید:")
                return

            if user.get("state") == "change_name":
                if contains_bad(text):
                    safe_send(bot, int(uid), "نام نامعتبر")
                    return
                user["name"] = text[:30]
                user["state"] = "idle"
                self.save_user(uid, user)
                safe_send(bot, int(uid), "نام تغییر کرد ✅", reply_markup=kb_main(uid))
                return

            if text == "🔢 تغییر سن":
                user["state"] = "change_age"
                self.save_user(uid, user)
                safe_send(bot, int(uid), "سن جدید را وارد کنید:")
                return

            if user.get("state") == "change_age":
                if not text.isdigit() or not 12 <= int(text) <= 99:
                    safe_send(bot, int(uid), "سن نامعتبر")
                    return
                user["age"] = int(text)
                user["state"] = "idle"
                self.save_user(uid, user)
                safe_send(bot, int(uid), "سن ذخیره شد ✅", reply_markup=kb_main(uid))
                return

            if text == "⚧ تغییر جنسیت":
                kb = types.InlineKeyboardMarkup()
                kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="change_sex_m"),
                       types.InlineKeyboardButton("خانم 👧", callback_data="change_sex_f"))
                safe_send(bot, int(uid), "جنسیت جدید را انتخاب کنید:", reply_markup=kb)
                return

            # admin menu
            if uid == self.owner and text == "📊 پنل مدیریت":
                safe_send(bot, int(uid), "پنل مدیریت", reply_markup=kb_admin())
                return

            # fallback
            safe_send(bot, int(uid), "لطفاً از دکمه‌های منو استفاده کنید", reply_markup=kb_main(uid))

        # callback query handler
        @bot.callback_query_handler(func=lambda c: True)
        def callback_handler(call):
            uid = str(call.from_user.id)
            data = call.data or ""
            users = db.read("users")
            user = users.get(uid) or self.ensure_user(uid)
            # quick answer to remove loading...
            try:
                bot.answer_callback_query(call.id, text="درحال اجرا...")
            except Exception:
                pass

            # registration sexes
            if data in ("reg_sex_m", "reg_sex_f"):
                user["sex"] = "آقا" if data == "reg_sex_m" else "خانم"
                user["state"] = "age"
                users[uid] = user; db.write("users", users)
                safe_send(bot, int(uid), "سن خود را وارد کنید (۱۲–۹۹):")
                return

            if data in ("change_sex_m", "change_sex_f"):
                user["sex"] = "آقا" if data == "change_sex_m" else "خانم"
                user["state"] = "idle"
                users[uid] = user; db.write("users", users)
                safe_send(bot, int(uid), "جنسیت تغییر کرد ✅", reply_markup=kb_main(uid))
                return

            # find partner callbacks
            if data.startswith("find_"):
                dbq = db.read("queue")
                if uid not in dbq.get("general", []):
                    dbq["general"].append(uid)
                db.write("queue", dbq)
                safe_send(bot, int(uid), "در حال جستجو برای هم‌صحبت... 🔍")
                pots = [p for p in dbq.get("general", []) if p != uid]
                pots = [p for p in pots if uid not in db.read("users").get(p, {}).get("blocks", [])]
                if pots:
                    partner = random.choice(pots)
                    try:
                        dbq["general"].remove(uid)
                    except Exception:
                        pass
                    try:
                        dbq["general"].remove(partner)
                    except Exception:
                        pass
                    users[uid]["partner"] = partner
                    users[partner]["partner"] = uid
                    db.write("queue", dbq)
                    db.write("users", users)
                    safe_send(bot, int(uid), "هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=kb_chatting())
                    try:
                        safe_send(bot, int(partner), "هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=kb_chatting())
                    except Exception:
                        pass
                else:
                    safe_send(bot, int(uid), "اضافه شدی به صف — لطفاً شکیبا باش")
                return

            # anon reply selection
            if data.startswith("anon_reply_"):
                try:
                    idx = int(data.split("_")[2])
                except Exception:
                    bot.answer_callback_query(call.id, "پیام نامعتبر")
                    return
                mdb = db.read("messages")
                inbox = mdb.get("inbox", {}).get(uid, [])
                if idx < 0 or idx >= len(inbox):
                    bot.answer_callback_query(call.id, "پیام نامعتبر")
                    return
                msgdata = inbox[idx]
                user["state"] = "anon_reply"
                user["anon_target"] = msgdata["from"]
                users[uid] = user; db.write("users", users)
                safe_send(bot, int(uid), "پاسخ خود را بنویسید:")
                return

            # end chat
            if data == "end_yes":
                partner = user.get("partner")
                self.end_chat(uid, partner, "پایان داد")
                return
            if data == "end_no":
                bot.answer_callback_query(call.id, "چت ادامه دارد ✅")
                return

            # report handling
            if data.startswith("rep_"):
                if data == "rep_cancel":
                    bot.answer_callback_query(call.id, "لغو شد ✅"); return
                reasons = {"rep_insult": "فحاشی", "rep_nsfw": "+18", "rep_spam": "اسپم", "rep_harass": "آزار"}
                reason = reasons.get(data, "نامشخص")
                target = user.get("report_target")
                last_msg_id = user.get("report_last_msg_id")
                report_text = f"🚩 گزارش\nشاکی: {uid}\nمتهم: {target}\nدلیل: {reason}"
                safe_send(bot, int(self.owner), report_text)
                if last_msg_id:
                    try:
                        bot.forward_message(int(self.owner), int(uid), last_msg_id)
                    except Exception:
                        safe_send(bot, int(self.owner), "فوروارد رسانه با خطا")
                admin_kb = types.InlineKeyboardMarkup(row_width=2)
                admin_kb.add(types.InlineKeyboardButton("Ignore", callback_data=f"adm_ignore_{target}"),
                             types.InlineKeyboardButton("Permanent Ban", callback_data=f"adm_ban_perm_{target}"))
                admin_kb.add(types.InlineKeyboardButton("Temp Ban", callback_data=f"adm_ban_temp_{target}"),
                             types.InlineKeyboardButton("Warning 1", callback_data=f"adm_warn1_{target}"))
                safe_send(bot, int(self.owner), "اقدام:", reply_markup=admin_kb)
                bot.answer_callback_query(call.id, "گزارش ارسال شد ✅")
                return

            # admin actions
            if data.startswith("adm_"):
                if str(call.from_user.id) != str(self.owner):
                    bot.answer_callback_query(call.id, "مجوز نداری")
                    return
                parts = data.split("_", 2)
                action = parts[1]
                target = parts[2] if len(parts) >= 3 else None
                if action == "ignore":
                    try:
                        bot.edit_message_text("عملیات لغو شد", int(self.owner), call.message.message_id)
                    except Exception:
                        pass
                    return
                if action == "ban" and parts[2] == "perm":
                    self.ban_perm(target, "گزارش تایید شد")
                    try:
                        bot.edit_message_text("بن دائم اعمال شد", int(self.owner), call.message.message_id)
                    except Exception:
                        pass
                    return
                if action == "ban" and parts[2] == "temp":
                    us = db.read("users")
                    us[self.owner]["state"] = f"temp_ban_minutes_{target}"
                    db.write("users", us)
                    safe_send(bot, int(self.owner), f"دقیقه بن موقت برای {target} را وارد کنید:")
                    return
                if action.startswith("warn"):
                    warns = 1 if "1" in action else 2
                    us = db.read("users")
                    if target in us:
                        us[target]["warns"] = us[target].get("warns", 0) + warns
                        db.write("users", us)
                        try:
                            safe_send(bot, int(target), f"⚠️ {warns} اخطار")
                        except Exception:
                            pass
                    try:
                        bot.edit_message_text(f"{warns} اخطار اعمال شد", int(self.owner), call.message.message_id)
                    except Exception:
                        pass
                    return

            # unban
            if data.startswith("unban_perm_"):
                target = data.split("_", 2)[2]
                bans = db.read("bans")
                if target in bans.get("permanent", {}):
                    del bans["permanent"][target]
                    db.write("bans", bans)
                    try:
                        bot.edit_message_text("کاربر بخشیده شد ✅", int(self.owner), call.message.message_id)
                    except Exception:
                        pass
                    try:
                        safe_send(bot, int(target), "شما از بن دائم در آمدید")
                    except Exception:
                        pass
                return

            # buy/gift callbacks
            if data.startswith("buy|"):
                try:
                    _, plan_key = data.split("|", 1)
                    plan = VIP_PLANS.get(plan_key)
                    if not plan:
                        bot.answer_callback_query(call.id, "پلن نامعتبر")
                        return
                    payload = make_payload(uid, plan_key)
                    prices = [types.LabeledPrice(label=plan["title"], amount=int(plan["stars"]))]
                    try:
                        bot.send_invoice(
                            chat_id=int(uid),
                            title=plan["title"],
                            description=f"⏳ مدت: {plan['days']} روز\n✨ امکانات VIP",
                            payload=payload,
                            provider_token=self.provider_token if self.provider_token else "",
                            currency=CURRENCY,
                            prices=prices,
                            start_parameter="vip_buy"
                        )
                        self.register_payment(payload, uid, plan_key, plan["stars"])
                        bot.answer_callback_query(call.id, "فاکتور ارسال شد ✅")
                    except Exception as e:
                        logger.error("send_invoice failed: %s", e)
                        # fallback manual
                        self.register_payment(payload, uid, plan_key, plan["stars"])
                        kb = types.InlineKeyboardMarkup()
                        kb.add(types.InlineKeyboardButton("✅ اعلام پرداخت (دستی)", callback_data=f"manual|{payload}"))
                        safe_send(bot, int(uid), "خطا در ساخت فاکتور خودکار. اگر پرداخت دستی انجام شد، اعلام کن.", reply_markup=kb)
                        safe_send(bot, int(uid), f"<code>{payload}</code>")
                except Exception as e:
                    logger.error("buy| handler error: %s", e)
                return

            if data == "buy_xmas":
                cfg = db.read("config")
                start_ts = cfg.get("start_ts", now_ts())
                if now_ts() > start_ts + XMAS_WINDOW_SECONDS:
                    bot.answer_callback_query(call.id, "مهلت به پایان رسید")
                    return
                if user.get("used_xmas", False):
                    bot.answer_callback_query(call.id, "قبلاً گرفتید")
                    return
                start_until = max(now_ts(), int(user.get("vip_until", 0)))
                user["vip_until"] = start_until + VIP_PLANS["vip_xmas"]["days"] * 86400
                user["used_xmas"] = True
                users[uid] = user; db.write("users", users)
                safe_send(bot, int(uid), f"🎉 VIP کریسمس فعال شد — دلیل: ویژه کریسمس 🎄\nاعتبار تا: {ts_to_iran_str(user['vip_until'])}")
                return

            # manual payment announce from user
            if data.startswith("manual|"):
                try:
                    payload = data.split("|", 1)[1]
                    payments = db.read("payments")
                    pay = payments.get(payload)
                    if not pay:
                        bot.answer_callback_query(call.id, "پرداخت نامشخص")
                        return
                    safe_send(
                        bot,
                        int(self.owner),
                        f"اعلام پرداخت دستی\nاز: {uid}\nکد: {payload}\nمبلغ: {pay.get('amount')}\nپلن: {pay.get('plan')}\nبرای تایید: /confirm_manual {payload}"
                    )
                    bot.answer_callback_query(call.id, "اعلام پرداخت ارسال شد ✅")
                except Exception as e:
                    logger.error("manual| callback error: %s", e)
                    try:
                        bot.answer_callback_query(call.id, "❌ خطا در اعلام پرداخت")
                    except Exception:
                        pass
                return

            # fallback small answer
            try:
                bot.answer_callback_query(call.id, "انجام شد")
            except Exception:
                pass

        # end of register_handlers

    # ---- helper methods used above ----
    def ban_perm(self, uid: str, reason: str = "تخلف"):
        db_b = db.read("bans")
        db_b["permanent"][str(uid)] = reason
        db.write("bans", db_b)

    def end_chat(self, a: str, b: str, msg: str = "ترک کرد"):
        users = db.read("users")
        if a in users:
            users[a]["partner"] = None
        if b in users:
            users[b]["partner"] = None
        db.write("users", users)
        try:
            safe_send(self.bot, int(a), f"چت به پایان رسید — {msg}", reply_markup=kb_main(a))
        except Exception:
            pass
        try:
            safe_send(self.bot, int(b), f"هم‌صحبت شما چت را {msg}", reply_markup=kb_main(b))
        except Exception:
            pass

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    # optional tiny web server to keep alive
    if FLASK_AVAILABLE:
        app = Flask(__name__)
        @app.route("/")
        def home():
            return "Shadow Titan - alive"
        # run flask in background thread
        def run_flask():
            try:
                app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
            except Exception:
                pass
        threading.Thread(target=run_flask, daemon=True).start()

    try:
        bot_app = ShadowTitanBot(BOT_TOKEN)
        print("Bot is running...")
        bot_app.bot.infinity_polling(skip_pending=True)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print("Fatal error:", e)
        logger.exception("Fatal error: %s", e)
        sys.exit(1)
