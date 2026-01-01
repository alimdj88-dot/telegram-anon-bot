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
import csv
from flask import Flask
import telebot
from telebot import types
import requests
import math

BOT_TOKEN = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
BOT_TOKEN_DIRECT = ""
if not BOT_TOKEN:
    BOT_TOKEN = BOT_TOKEN_DIRECT
if not BOT_TOKEN:
    print("BOT_TOKEN is empty - please set BOT_TOKEN or BOT_TOKEN_DIRECT")
    sys.exit(1)

PROVIDER_TOKEN = ""  # leave empty for Stars/XTR or set your provider token
OWNER_ID = os.getenv("OWNER_ID", "") or "8013245091"
CHANNEL = os.getenv("CHANNEL", "") or "@ChatNaAnnouncements"
SUPPORT = os.getenv("SUPPORT", "") or "@its_alimo"

VIP_PLANS = {
    "vip_1w":  {"days": 7,   "stars": 25,  "title": "VIP 1 هفته"},
    "vip_1m":  {"days": 30,  "stars": 100, "title": "VIP 1 ماهه"},
    "vip_3m":  {"days": 90,  "stars": 280, "title": "VIP 3 ماهه"},
    "vip_6m":  {"days": 180, "stars": 560, "title": "VIP 6 ماهه"},
    "vip_12m": {"days": 365, "stars": 860, "title": "VIP 1 ساله"},
    "vip_xmas": {"days": 90, "stars": 0, "title": "VIP کریسمس — 3 ماه (رایگان)"}
}
XMAS_WINDOW_SECONDS = 4 * 86400
CURRENCY = "XTR"

DATA_DIR = "shadow_db_full"
os.makedirs(DATA_DIR, exist_ok=True)
FILES = {
    "users": os.path.join(DATA_DIR, "users.json"),
    "bans": os.path.join(DATA_DIR, "bans.json"),
    "queue": os.path.join(DATA_DIR, "queue.json"),
    "messages": os.path.join(DATA_DIR, "messages.json"),
    "config": os.path.join(DATA_DIR, "config.json"),
    "payments": os.path.join(DATA_DIR, "payments.json"),
    "backups": os.path.join(DATA_DIR, "backups.json")
}

LOG_FILE = "shadow_titan_pro_full.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ShadowTitanProFull")

IRAN_OFFSET = datetime.timedelta(hours=3, minutes=30)
def now_ts(): return int(time.time())
def iran_now_dt(): return datetime.datetime.utcnow() + IRAN_OFFSET
def ts_to_iran_str(ts):
    try:
        return (datetime.datetime.utcfromtimestamp(int(ts)) + IRAN_OFFSET).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(ts)

class SimpleDB:
    def __init__(self, files):
        self.files = files
        self.lock = threading.Lock()
        self._init_default_files()
    def _init_default_files(self):
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
            for k,p in self.files.items():
                if not os.path.exists(p):
                    try:
                        with open(p,"w",encoding="utf-8") as f:
                            json.dump(defaults.get(k, {}), f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.error("init file error %s %s", p, e)
    def read(self,key):
        p = self.files.get(key)
        if not p:
            return {}
        with self.lock:
            try:
                with open(p,"r",encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("DB read error %s %s", key, e)
                return {}
    def write(self,key,val):
        p = self.files.get(key)
        if not p:
            return
        with self.lock:
            try:
                with open(p,"w",encoding="utf-8") as f:
                    json.dump(val,f,ensure_ascii=False,indent=2)
            except Exception as e:
                logger.error("DB write error %s %s", key, e)

db = SimpleDB(FILES)

BAD_WORDS = [
"کیر","کیرد","کیرت","کیرم","کیری","کس","کص","کوس","کون","کونی","گای","گایید","گاییدن",
"گاییدم","گوه","گوهر","جنده","جنده‌","جنده‌ها","جنده‌باز","قحبه","قهبه","فاحشه",
"پدرسگ","پدرسوخته","پدرسک","پدرسگه","ناموس","ناموسی","هرزه","سکس","سکسی","پورن",
"لاش","لاشی","لاشخور","احمق","خر","خرم","گوز","گوزید","دیوث","جق","مالیدن","بکن",
"بمال","پفیوز","پیفیوز","مرتیکه","شاسگول","شاسگولت","گوهخور","گوخور","کسخل","کسکش",
"کسشر","کسده","کسفروش","مادرجنده","مادرجند","پفیوز","پفیوزی","کونی","کون‌گشاد","کون‌لق"
]
DIACRITICS_RE = re.compile(r'[\u064B-\u065F\u0610-\u061A\u06D6-\u06ED\u0640]')
PUNCT_RE = re.compile(r'[\s\.\-\_\*\|\\\/\:\;\'\"\,\(\)\[\]\{\}\?!،؛•·–]')
DIGIT_RE = re.compile(r'[0-9۰-۹]')
ZERO_WIDTH_RE = re.compile(r'[\u200b\u200c]')

def normalize_persian(text):
    if not text:
        return ""
    s = text.lower()
    s = s.replace('ك','ک').replace('ي','ی').replace('ى','ی').replace('ؤ','و').replace('إ','ا').replace('أ','ا')
    s = DIACRITICS_RE.sub('', s)
    s = ZERO_WIDTH_RE.sub('', s)
    s = s.replace('ـ','')
    s = PUNCT_RE.sub('', s)
    s = DIGIT_RE.sub('', s)
    s = re.sub(r'(.)\1{2,}', r'\1\1', s)
    return s

BAD_NORM = [normalize_persian(w) for w in BAD_WORDS]

def contains_bad(text):
    n = normalize_persian(text)
    for bw in BAD_NORM:
        if bw and bw in n:
            return True
    return False

def rand_token(n=8):
    return ''.join(random.choices(string.ascii_lowercase+string.digits,k=n))

def make_payload(uid, plan):
    return f"{plan}_{uid}_{now_ts()}_{rand_token(6)}"

app = Flask(__name__)
@app.route("/")
def alive(): return "Shadow Titan Pro Full — alive"
def run_web():
    try:
        app.run(host="0.0.0.0", port=8080)
    except Exception as e:
        logger.error("flask run error %s", e)

class ShadowTitanBot:
    def __init__(self, token):
        self.token = token
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.owner = str(OWNER_ID)
        self.provider_token = PROVIDER_TOKEN or ""
        cfg = db.read("config")
        self.start_ts = cfg.get("start_ts", now_ts())
        self.xmas_expires_at = self.start_ts + XMAS_WINDOW_SECONDS
        self._register_handlers()
        self._start_maintenance_worker()
    def ensure_user(self, uid):
        uid = str(uid)
        users = db.read("users")
        if uid not in users:
            users[uid] = {
                "state":"name","name":"","sex":"","age":0,"warns":0,"partner":None,
                "vip_until":0,"blocks":[],"last_spin":"","used_xmas":False,
                "anon_target":None,"last_chat_msg_id":None,"report_target":None,"report_last_msg_id":None,
                "gift_days":0
            }
            db.write("users", users)
        return users[uid]
    def save_user(self, uid, userd):
        users = db.read("users"); users[str(uid)] = userd; db.write("users", users)
    def is_vip(self, userd):
        try: return int(userd.get("vip_until",0)) > now_ts()
        except: return False
    def register_payment(self,payload,uid,plan,amount):
        payments = db.read("payments")
        payments[payload] = {"uid":str(uid),"plan":plan,"amount":int(amount),"time":now_ts(),"done":False}
        db.write("payments",payments)
    def mark_payment_done(self,payload):
        payments = db.read("payments")
        if payload in payments:
            payments[payload]["done"] = True
            db.write("payments",payments)
            return payments[payload]
        return None
    def kb_main(self, uid):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("🛰 شروع چت ناشناس","👤 پروفایل من")
        kb.add("📩 لینک ناشناس من","📥 پیام‌های ناشناس")
        kb.add("🎡 گردونه شانس روزانه","🎖 خرید VIP (پلن‌ها)")
        kb.add("❓ راهنما و قوانین","⚙ تنظیمات")
        if str(uid) == self.owner:
            kb.add("📊 پنل مدیریت")
        return kb
    def kb_chat(self):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("🔚 پایان گفتگو","🚩 گزارش تخلف")
        kb.add("🚫 بلاک و خروج","👥 درخواست آیدی")
        return kb
    def kb_vip_inline(self, uid):
        kb = types.InlineKeyboardMarkup(row_width=1)
        users = db.read("users")
        user = users.get(str(uid), {})
        if now_ts() < self.xmas_expires_at and not user.get("used_xmas", False):
            kb.add(types.InlineKeyboardButton(VIP_PLANS["vip_xmas"]["title"], callback_data="buy_xmas"))
        for k,p in VIP_PLANS.items():
            if k == "vip_xmas":
                continue
            kb.add(types.InlineKeyboardButton(f"{p['title']} — {p['stars']} ⭐", callback_data=f"buy|{k}"))
        return kb
    def kb_admin(self):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("📈 آمار کامل",callback_data="adm_stats"),
               types.InlineKeyboardButton("🛠 تعمیر/نگهداری",callback_data="adm_maint"))
        kb.add(types.InlineKeyboardButton("🎁 گیفت VIP تکی",callback_data="adm_gift_single"),
               types.InlineKeyboardButton("🎁 گیفت VIP همگانی",callback_data="adm_gift_all"))
        kb.add(types.InlineKeyboardButton("❌ حذف VIP",callback_data="adm_remove_vip"),
               types.InlineKeyboardButton("📋 لیست VIP",callback_data="adm_list_vip"))
        kb.add(types.InlineKeyboardButton("📁 دانلود DB",callback_data="adm_download_db"),
               types.InlineKeyboardButton("🚫 لیست بن‌شده‌ها",callback_data="adm_bans"))
        kb.add(types.InlineKeyboardButton("📤 خروجی CSV",callback_data="adm_export_csv"),
               types.InlineKeyboardButton("📥 بازیابی بکاپ",callback_data="adm_restore_backup"))
        kb.add(types.InlineKeyboardButton("🔙 بازگشت",callback_data="adm_back"))
        return kb
    def kb_duration(self,prefix):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("1 هفته",callback_data=f"{prefix}_7"),
               types.InlineKeyboardButton("1 ماه",callback_data=f"{prefix}_30"))
        kb.add(types.InlineKeyboardButton("3 ماه",callback_data=f"{prefix}_90"),
               types.InlineKeyboardButton("6 ماه",callback_data=f"{prefix}_180"))
        kb.add(types.InlineKeyboardButton("1 سال",callback_data=f"{prefix}_365"))
        return kb
    def kbreport(self):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
               types.InlineKeyboardButton("+18", callback_data="rep_nsfw"))
        kb.add(types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
               types.InlineKeyboardButton("آزار", callback_data="rep_harass"))
        kb.add(types.InlineKeyboardButton("لغو ❌", callback_data="rep_cancel"))
        return kb
    def _start_maintenance_worker(self):
        def worker():
            while True:
                try:
                    cfg = db.read("config")
                    if cfg.get("settings",{}).get("maintenance",False):
                        logger.info("Maintenance mode active")
                    time.sleep(60)
                except Exception as e:
                    logger.error("maintenance worker error %s", e)
                    time.sleep(10)
        t = threading.Thread(target=worker, daemon=True)
        t.start()
    def _save_backup(self):
        try:
            now = iran_now_dt().strftime("%Y%m%d%H%M%S")
            backup = {}
            for k in FILES:
                backup[k] = db.read(k)
            bfile = db.read("backups")
            bfile[now] = backup
            db.write("backups", bfile)
            logger.info("backup saved %s", now)
            return now
        except Exception as e:
            logger.error("backup error %s", e)
            return None
    def _restore_backup(self, ts):
        try:
            bfile = db.read("backups")
            if ts not in bfile:
                return False
            backup = bfile[ts]
            for k,v in backup.items():
                db.write(k, v)
            return True
        except Exception as e:
            logger.error("restore error %s", e)
            return False
    def _export_csv(self, path):
        try:
            users = db.read("users")
            with open(path, "w", newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["uid","name","sex","age","vip_until","warns","partner"])
                for uid,u in users.items():
                    w.writerow([uid, u.get("name",""), u.get("sex",""), u.get("age",0), u.get("vip_until",0), u.get("warns",0), u.get("partner")])
            return True
        except Exception as e:
            logger.error("export csv error %s", e)
            return False
    def _import_csv_users(self, path):
        try:
            with open(path, "r", encoding='utf-8') as f:
                r = csv.DictReader(f)
                users = db.read("users")
                for row in r:
                    uid = row.get("uid")
                    if not uid:
                        continue
                    users[uid] = {
                        "state":"idle",
                        "name": row.get("name",""),
                        "sex": row.get("sex",""),
                        "age": int(row.get("age") or 0),
                        "warns": int(row.get("warns") or 0),
                        "partner": row.get("partner"),
                        "vip_until": int(row.get("vip_until") or 0),
                        "blocks": [], "last_spin": "", "used_xmas": False
                    }
                db.write("users", users)
            return True
        except Exception as e:
            logger.error("import csv error %s", e)
            return False
    def _register_handlers(self):
        bot = self.bot
        @bot.message_handler(commands=['start'])
        def handle_start(msg):
            uid = str(msg.chat.id)
            payload = None
            if msg.text and len(msg.text.split())>1:
                payload = msg.text.split(maxsplit=1)[1]
            user = self.ensure_user(uid)
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    bot.send_message(uid, "نمی‌توانید به خودتان پیام ناشناس بفرستید.")
                    return
                user["state"] = "anon_send"
                user["anon_target"] = target
                self.save_user(uid, user)
                bot.send_message(uid, "پیام ناشناس: متن را ارسال کنید:")
                return
            if user.get("state") in ("name","sex","age"):
                user["state"] = "name"
                user["name"] = ""
                user["sex"] = ""
                user["age"] = 0
                self.save_user(uid, user)
                bot.send_message(uid, "به Shadow Titan خوش آمدی! نام مستعار خود را وارد کن:")
                return
            bot.send_message(uid, "خوش آمدی!", reply_markup=self.kb_main(uid))
        @bot.pre_checkout_query_handler(func=lambda q: True)
        def precheckout(q):
            try:
                bot.answer_pre_checkout_query(q.id, ok=True)
            except Exception as e:
                logger.error("precheckout error %s", e)
        @bot.message_handler(content_types=['successful_payment'])
        def successful_payment(msg):
            try:
                payload = ""
                try:
                    payload = msg.successful_payment.invoice_payload
                except:
                    payload = getattr(msg.successful_payment, 'payload','')
                if not payload:
                    logger.warning("successful_payment no payload")
                    return
                payments = db.read("payments")
                if payload not in payments:
                    logger.warning("unknown successful payload %s", payload)
                    return
                pay = payments[payload]
                uid = str(msg.chat.id)
                users = db.read("users")
                user = users.get(uid) or self.ensure_user(uid)
                plan_key = pay.get("plan")
                plan = VIP_PLANS.get(plan_key)
                if plan:
                    now = now_ts()
                    start = max(now, int(user.get("vip_until",0)))
                    user["vip_until"] = start + plan["days"] * 86400
                    users[uid] = user
                    pay["done"] = True
                    payments[payload] = pay
                    db.write("users", users)
                    db.write("payments", payments)
                    bot.send_message(uid, f"🎉 پرداخت موفق! پلن {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
            except Exception as e:
                logger.error("successful_payment handler err %s", e)
        @bot.message_handler(content_types=['text','photo','video','voice','sticker','animation','video_note'])
        def main_message(msg):
            try:
                uid = str(msg.chat.id)
                users = db.read("users")
                if uid not in users:
                    user = self.ensure_user(uid)
                else:
                    user = users[uid]
                bans = db.read("bans")
                cfg = db.read("config")
                if uid in bans.get("permanent", {}):
                    return
                if uid in bans.get("temporary", {}) and now_ts() < bans["temporary"][uid]["end"]:
                    return
                if cfg.get("settings", {}).get("maintenance", False) and not (self.is_vip(user) or uid == self.owner):
                    bot.send_message(uid, "ربات در حالت تعمیر است. فقط VIP ها دسترسی دارند.")
                    return
                text = msg.text or ""
                if user.get("state") == "name":
                    if not text or contains_bad(text):
                        bot.send_message(uid, "نام نامعتبر — لطفاً نامی بدون کلمات نامناسب وارد کن:")
                        return
                    user["name"] = text.strip()[:30]
                    user["state"] = "sex"
                    self.save_user(uid, user)
                    kb = types.InlineKeyboardMarkup()
                    kb.add(types.InlineKeyboardButton("آقا 👦", callback_data="reg_sex_m"),
                           types.InlineKeyboardButton("خانم 👧", callback_data="reg_sex_f"))
                    bot.send_message(uid, f"سلام {user['name']}! جنسیت را انتخاب کن:", reply_markup=kb)
                    return
                if user.get("state") == "age":
                    if not text or not text.isdigit() or not 12 <= int(text) <= 99:
                        bot.send_message(uid, "سن نامعتبر — یک عدد بین 12 و 99 وارد کن:")
                        return
                    user["age"] = int(text)
                    user["state"] = "idle"
                    self.save_user(uid, user)
                    bot.send_message(uid, "ثبت‌نام انجام شد", reply_markup=self.kb_main(uid))
                    return
                if user.get("state") == "anon_send":
                    if msg.content_type != "text":
                        bot.send_message(uid, "فقط متن مجاز است برای پیام ناشناس.")
                        return
                    target = user.get("anon_target")
                    if not target:
                        bot.send_message(uid, "مقصد پیام ناشناس نامشخص شد")
                        user["state"] = "idle"
                        self.save_user(uid, user)
                        return
                    mdb = db.read("messages")
                    inbox = mdb.get("inbox", {})
                    inbox.setdefault(target, []).append({
                        "text": msg.text,
                        "from": uid,
                        "seen": False,
                        "time": iran_now_dt().strftime("%H:%M %d/%m")
                    })
                    mdb["inbox"] = inbox
                    db.write("messages", mdb)
                    bot.send_message(uid, "✅ پیام ناشناس ارسال شد")
                    try:
                        bot.send_message(target, "📩 یک پیام ناشناس جدید دریافت کردید!")
                    except:
                        pass
                    user["state"] = "idle"
                    self.save_user(uid, user)
                    return
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
                        bot.send_message(uid, "دلیل گزارش را انتخاب کنید:", reply_markup=self.kbreport())
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
                        logger.warning("copy msg error %s", e)
                    return
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
                    if vip_until and vip_until > now_ts():
                        vip_text = ts_to_iran_str(vip_until)
                    bot.send_message(uid, f"<b>پروفایل شما</b>\n\nنام: {user.get('name','نامشخص')}\nجنسیت: {user.get('sex','نامشخص')}\nسن: {user.get('age','نامشخص')}\nرنک: {rank}\nاعتبار VIP تا: {vip_text}\nاخطار: {user.get('warns',0)}")
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
                    mdb = db.read("messages")
                    inbox = mdb.get("inbox", {}).get(uid, [])
                    if not inbox:
                        bot.send_message(uid, "هیچ پیام ناشناسی دریافت نکرده‌اید 📭")
                        return
                    kb = types.InlineKeyboardMarkup()
                    txt = "<b>پیام‌های ناشناس شما</b>\n\n"
                    for i,m in enumerate(inbox):
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
                        mdb["inbox"][uid] = inbox
                        db.write("messages", mdb)
                    return
                if text == "🎡 گردونه شانس روزانه":
                    today = iran_now_dt().strftime("%Y-%m-%d")
                    if user.get("last_spin") == today:
                        bot.send_message(uid, "امروز قبلاً گردونه را چرخانده‌اید 😊")
                        return
                    user["last_spin"] = today
                    self.save_user(uid, user)
                    if random.random() < 0.05:
                        now = now_ts()
                        start = max(now, int(user.get("vip_until", 0)))
                        user["vip_until"] = start + 30*86400
                        self.save_user(uid, user)
                        bot.send_message(uid, f"🎉 تبریک! رنک VIP (۳۰ روزه) گرفتید تا {ts_to_iran_str(user['vip_until'])}")
                    else:
                        bot.send_message(uid, "گردونه چرخید... پوچ! شانس بعدی را امتحان کنید 🌟")
                    return
                if text == "🎖 خرید VIP (پلن‌ها)":
                    features = ("<b>🎖 امکانات VIP</b>\n\n• ارسال آزاد گیف و استیکر\n• دسترسی در زمان تعمیر\n• اتصال سریع‌تر و بهتر به هم‌صحبت\n\n⏳ VIP زمان‌دار است\n💳 پرداخت با Telegram Stars")
                    bot.send_message(uid, features, reply_markup=self.kb_vip_inline(uid))
                    return
                if text == "⚙ تنظیمات":
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    kb.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت")
                    kb.add("🔙 بازگشت به منو")
                    bot.send_message(uid, "تنظیمات پروفایل:", reply_markup=kb)
                    return
                if text == "✏️ تغییر نام":
                    user["state"] = "change_name"
                    self.save_user(uid, user)
                    bot.send_message(uid, "نام جدید را وارد کن:")
                    return
                if user.get("state") == "change_name":
                    if contains_bad(text):
                        bot.send_message(uid, "نام نامعتبر")
                        return
                    user["name"] = text[:30]
                    user["state"] = "idle"
                    self.save_user(uid, user)
                    bot.send_message(uid, "نام تغییر کرد ✅", reply_markup=self.kb_main(uid))
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
                if uid == str(self.owner) and text == "📊 پنل مدیریت":
                    bot.send_message(uid, "پنل مدیریت:", reply_markup=self.kb_admin())
                    return
                bot.send_message(uid, "لطفاً از دکمه‌های منو استفاده کن", reply_markup=self.kb_main(uid))
            except Exception as e:
                logger.error("main_message error %s", e)
        @bot.callback_query_handler(func=lambda c: True)
        def callback_handler(call):
            try:
                uid = str(call.from_user.id)
                data = call.data or ""
                users = db.read("users")
                user = users.get(uid) or self.ensure_user(uid)
                try:
                    bot.answer_callback_query(call.id)
                except:
                    pass
                if data in ("reg_sex_m", "reg_sex_f"):
                    user["sex"] = "آقا" if data == "reg_sex_m" else "خانم"
                    user["state"] = "age"
                    users[uid] = user
                    db.write("users", users)
                    bot.send_message(uid, "سن خود را وارد کن (۱۲–۹۹):")
                    return
                if data in ("change_sex_m", "change_sex_f"):
                    user["sex"] = "آقا" if data=="change_sex_m" else "خانم"
                    user["state"] = "idle"
                    users[uid] = user
                    db.write("users", users)
                    bot.send_message(uid, "جنسیت تغییر کرد ✅", reply_markup=self.kb_main(uid))
                    return
                if data.startswith("find_"):
                    dbq = db.read("queue")
                    if uid not in dbq.get("general", []):
                        dbq["general"].append(uid)
                    db.write("queue", dbq)
                    bot.send_message(uid, "در حال جستجو برای هم‌صحبت...")
                    pots = [p for p in dbq.get("general", []) if p != uid]
                    pots = [p for p in pots if uid not in db.read("users").get(p, {}).get("blocks", [])]
                    if pots:
                        partner = random.choice(pots)
                        try: dbq["general"].remove(uid)
                        except: pass
                        try: dbq["general"].remove(partner)
                        except: pass
                        users[uid]["partner"] = partner
                        users[partner]["partner"] = uid
                        db.write("queue", dbq)
                        db.write("users", users)
                        bot.send_message(uid, "هم‌صحبت پیدا شد! چت را شروع کن", reply_markup=self.kb_chat())
                        bot.send_message(partner, "هم‌صحبت پیدا شد! چت را شروع کن", reply_markup=self.kb_chat())
                    else:
                        bot.send_message(uid, "در صف قرار گرفتی؛ لطفاً صبور باش...")
                    return
                if data.startswith("anon_reply_"):
                    idx = int(data.split("_")[2])
                    mdb = db.read("messages")
                    inbox = mdb.get("inbox", {}).get(uid, [])
                    if idx < 0 or idx >= len(inbox):
                        bot.answer_callback_query(call.id, "پیام نامعتبر")
                        return
                    msgdata = inbox[idx]
                    user["state"] = "anon_reply"
                    user["anon_target"] = msgdata["from"]
                    users[uid] = user
                    db.write("users", users)
                    bot.send_message(uid, "پاسخ را ارسال کن:")
                    return
                if data == "end_yes":
                    partner = user.get("partner")
                    self.end_chat(uid, partner, "پایان داد")
                    return
                if data == "end_no":
                    bot.answer_callback_query(call.id, "چت ادامه دارد ✅")
                    return
                if data.startswith("rep_"):
                    if data == "rep_cancel":
                        bot.answer_callback_query(call.id, "گزارش لغو شد ✅")
                        return
                    reasons = {"rep_insult":"فحاشی","rep_nsfw":"+18","rep_spam":"اسپم","rep_harass":"آزار"}
                    reason = reasons.get(data, "نامشخص")
                    target = user.get("report_target")
                    last_msg = user.get("report_last_msg_id")
                    bot.send_message(self.owner, f"🚩 گزارش جدید\nشاکی: {uid}\nمتهم: {target}\nدلیل: {reason}")
                    if last_msg:
                        try: bot.forward_message(self.owner, uid, last_msg)
                        except: pass
                    kb = types.InlineKeyboardMarkup(row_width=2)
                    kb.add(types.InlineKeyboardButton("Ignore", callback_data=f"adm_ignore_{target}"),
                           types.InlineKeyboardButton("Ban Perm", callback_data=f"adm_ban_perm_{target}"))
                    kb.add(types.InlineKeyboardButton("Ban Temp", callback_data=f"adm_ban_temp_{target}"),
                           types.InlineKeyboardButton("Warn 1", callback_data=f"adm_warn1_{target}"))
                    bot.send_message(self.owner, "اقدام:", reply_markup=kb)
                    bot.answer_callback_query(call.id, "گزارش ارسال شد ✅")
                    return
                if data.startswith("adm_"):
                    if str(call.from_user.id) != str(self.owner):
                        bot.answer_callback_query(call.id, "مجوز نداری")
                        return
                    if data == "adm_stats":
                        users = db.read("users")
                        total = len(users)
                        males = sum(1 for d in users.values() if d.get("sex") == "آقا")
                        females = total - males
                        nowv = now_ts()
                        vips = sum(1 for d in users.values() if int(d.get("vip_until",0)) > nowv)
                        bot.send_message(self.owner, f"<b>آمار ربات</b>\n\nکل کاربران: {total}\nآقا: {males}\nخانم: {females}\nVIPها: {vips}")
                        return
                    if data == "adm_maint":
                        cfg = db.read("config")
                        s = cfg.get("settings", {})
                        s["maintenance"] = not s.get("maintenance", False)
                        cfg["settings"] = s
                        db.write("config", cfg)
                        bot.send_message(self.owner, f"تعمیر: {'فعال' if s['maintenance'] else 'غیرفعال'}")
                        return
                    if data == "adm_gift_single":
                        bot.send_message(self.owner, "مدت VIP برای گیفت تکی را انتخاب کن:", reply_markup=self.kb_duration("gift_single"))
                        return
                    if data == "adm_gift_all":
                        bot.send_message(self.owner, "مدت VIP برای گیفت همگانی را انتخاب کن:", reply_markup=self.kb_duration("gift_all"))
                        return
                    if data == "adm_remove_vip":
                        users = db.read("users")
                        users[self.owner]["state"] = "remove_vip"
                        db.write("users", users)
                        bot.send_message(self.owner, "آیدی عددی کاربر برای حذف VIP را وارد کن:")
                        return
                    if data == "adm_list_vip":
                        users = db.read("users")
                        nowv = now_ts()
                        vip_list = [(u,d) for u,d in users.items() if int(d.get("vip_until",0)) > nowv]
                        if not vip_list:
                            bot.send_message(self.owner, "هیچ کاربر VIP وجود ندارد")
                            return
                        msgt = "<b>لیست VIP ها</b>\n\n"
                        for u,d in vip_list:
                            msgt += f"🆔 {u} - {d.get('name','نامشخص')} تا {ts_to_iran_str(d.get('vip_until'))}\n"
                        bot.send_message(self.owner, msgt)
                        return
                    if data == "adm_download_db":
                        for p in FILES.values():
                            if os.path.exists(p):
                                try: bot.send_document(self.owner, open(p,'rb'))
                                except Exception as e: logger.error("send db file error %s", e)
                        return
                    if data == "adm_bans":
                        bans = db.read("bans")
                        txt = "<b>بن‌شدگان</b>\n\n"
                        for u,r in bans.get("permanent", {}).items():
                            txt += f"🆔 {u} - {r} (دائم)\n"
                        for u,d in bans.get("temporary", {}).items():
                            txt += f"🆔 {u} - موقت تا {ts_to_iran_str(d.get('end'))}\n"
                        bot.send_message(self.owner, txt)
                        return
                    if data == "adm_export_csv":
                        fname = os.path.join(DATA_DIR, f"users_export_{now_ts()}.csv")
                        ok = self._export_csv(fname)
                        if ok: bot.send_document(self.owner, open(fname,'rb'))
                        else: bot.send_message(self.owner, "خطا در خروجی CSV")
                        return
                    if data == "adm_restore_backup":
                        bks = db.read("backups")
                        if not bks:
                            bot.send_message(self.owner, "هیچ بکاپی موجود نیست")
                            return
                        opts = types.InlineKeyboardMarkup()
                        for k in bks.keys():
                            opts.add(types.InlineKeyboardButton(k, callback_data=f"restore_{k}"))
                        bot.send_message(self.owner, "بکاپ‌ها:", reply_markup=opts)
                        return
                    if data == "adm_back":
                        bot.send_message(self.owner, "پنل مدیریت:", reply_markup=self.kb_admin())
                        return
                if data.startswith("gift_single_") or data.startswith("gift_all_"):
                    parts = data.split("_")
                    days = int(parts[-1])
                    users = db.read("users")
                    if data.startswith("gift_single_"):
                        users[self.owner]["gift_days"] = days
                        users[self.owner]["state"] = "gift_single_id"
                        db.write("users", users)
                        bot.send_message(self.owner, f"مدت انتخاب شد {days} روز. آیدی عددی کاربر را وارد کنید:")
                    else:
                        users[self.owner]["gift_days"] = days
                        users[self.owner]["state"] = "gift_all_reason"
                        db.write("users", users)
                        bot.send_message(self.owner, f"مدت انتخاب شد {days} روز. دلیل گیفت همگانی را وارد کن:")
                    return
                if data == "buy_xmas":
                    now = now_ts()
                    if now > self.xmas_expires_at:
                        bot.answer_callback_query(call.id, "مهلت این پلن به پایان رسیده")
                        return
                    if user.get("used_xmas", False):
                        bot.answer_callback_query(call.id, "شما قبلاً این پلن را گرفته‌اید")
                        return
                    start = max(now, int(user.get("vip_until",0)))
                    user["vip_until"] = start + VIP_PLANS["vip_xmas"]["days"] * 86400
                    user["used_xmas"] = True
                    users[uid] = user
                    db.write("users", users)
                    bot.send_message(uid, f"🎉 VIP کریسمس (۳ ماهه) فعال شد — دلیل: ویژه کریسمس 🎄\nاعتبار تا: {ts_to_iran_str(user['vip_until'])}")
                    return
                if data.startswith("buy|"):
                    _, plan_key = data.split("|",1)
                    plan = VIP_PLANS.get(plan_key)
                    if not plan:
                        bot.answer_callback_query(call.id, "پلن نامعتبر")
                        return
                    payload = make_payload(uid, plan_key)
                    prices = [types.LabeledPrice(label=plan["title"], amount=int(plan["stars"]))]
                    try:
                        bot.send_invoice(chat_id=int(uid),
                                         title=plan["title"],
                                         description=f"⏳ مدت: {plan['days']} روز\n{plan['title']}",
                                         payload=payload,
                                         provider_token=self.provider_token if self.provider_token else "",
                                         currency=CURRENCY,
                                         prices=prices,
                                         start_parameter="vip_buy")
                        self.register_payment(payload, uid, plan_key, plan["stars"])
                        bot.answer_callback_query(call.id, "فاکتور ارسال شد ✅")
                    except Exception as e:
                        logger.error("send_invoice failed %s", e)
                        self.register_payment(payload, uid, plan_key, plan["stars"])
                        kb = types.InlineKeyboardMarkup()
                        kb.add(types.InlineKeyboardButton("✅ اعلام پرداخت (دستی)", callback_data=f"manual|{payload}"))
                        bot.send_message(uid, "⚠️ خطا در ایجاد فاکتور پرداخت خودکار. می‌توانید پرداخت دستی انجام دهید و سپس اعلام پرداخت را بزنید.", reply_markup=kb)
                        bot.send_message(uid, f"<code>{payload}</code>")
                    return
                if data.startswith("manual|"):
                    payload = data.split("|",1)[1]
                    payments = db.read("payments")
                    pay = payments.get(payload)
                    if not pay:
                        bot.answer_callback_query(call.id, "پرداخت نامشخص")
                        return
                    bot.send_message(self.owner, f"اعلام پرداخت دستی از {uid}\nکد: {payload}\nمبلغ: {pay.get('amount')}\nپلن: {pay.get('plan')}\nبرای تایید از دستور: /confirm_manual {payload} استفاده کن")
                    bot.send_message(uid, "اعلام پرداخت ثبت شد، ادمین پس از بررسی تایید می‌کند.")
                    return
                if data.startswith("restore_"):
                    ts = data.split("_",1)[1]
                    ok = self._restore_backup(ts)
                    if ok:
                        bot.send_message(self.owner, f"بکاپ {ts} بازیابی شد")
                    else:
                        bot.send_message(self.owner, "بازیابی ناموفق بود")
                    return
                bot.answer_callback_query(call.id, "عملیات انجام شد")
            except Exception as e:
                logger.error("callback_handler error %s", e)
        @bot.message_handler(commands=["confirm_manual"])
        def confirm_manual(msg):
            if str(msg.chat.id) != str(self.owner):
                return
            parts = msg.text.split()
            if len(parts) < 2:
                bot.send_message(self.owner, "Usage: /confirm_manual <payload>")
                return
            payload = parts[1]
            payments = db.read("payments")
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
            users = db.read("users")
            user = users.get(uid) or self.ensure_user(uid)
            now = now_ts()
            start = max(now, int(user.get("vip_until",0)))
            user["vip_until"] = start + plan["days"] * 86400
            payments[payload]["done"] = True
            users[uid] = user
            db.write("payments", payments)
            db.write("users", users)
            bot.send_message(self.owner, f"✅ پرداخت با کد {payload} تایید شد و VIP اعمال شد.")
            try:
                bot.send_message(uid, f"🎉 پرداخت شما تایید شد. پلن {plan['title']} تا {ts_to_iran_str(user['vip_until'])} فعال شد.")
            except:
                pass
    def ban_perm(self, uid, reason="تخلف"):
        bans = db.read("bans")
        bans.setdefault("permanent", {})[str(uid)] = reason
        db.write("bans", bans)
        logger.info("ban_perm %s %s", uid, reason)
    def ban_temp(self, uid, minutes=60, reason="تخلف"):
        bans = db.read("bans")
        end = now_ts() + minutes * 60
        bans.setdefault("temporary", {})[str(uid)] = {"end": end, "reason": reason}
        db.write("bans", bans)
        logger.info("ban_temp %s until %s", uid, end)
    def end_chat(self, a, b, msg="ترک کرد"):
        users = db.read("users")
        if a in users: users[a]["partner"] = None
        if b in users: users[b]["partner"] = None
        db.write("users", users)
        try: self.bot.send_message(a, "چت پایان یافت", reply_markup=self.kb_main(a))
        except: pass
        try: self.bot.send_message(b, f"هم‌صحبت شما {msg}", reply_markup=self.kb_main(b))
        except: pass
    def run(self):
        t = threading.Thread(target=run_web, daemon=True)
        t.start()
        try:
            self.bot.infinity_polling(long_polling_timeout=60)
        except Exception as e:
            logger.error("polling crash %s", e)
            time.sleep(2)
            try:
                self.bot.infinity_polling(long_polling_timeout=60)
            except Exception as e2:
                logger.error("second crash %s", e2)
                sys.exit(1)

if __name__ == "__main__":
    bot = ShadowTitanBot(BOT_TOKEN)
    bot.run()
