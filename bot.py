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
    return "Shadow Titan v20.0 – کامل‌ترین نسخه با متن‌های زیبا و بدون باگ 🌟"

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
            "config": "db_config.json"
        }
        self.lock = threading.Lock()
        self.init()

    def init(self):
        defaults = {
            "users": {"users": {}},
            "bans": {"permanent": {}, "temporary": {}},
            "queue": {"general": []},
            "messages": {"inbox": {}},
            "config": {"settings": {"maintenance": False}, "broadcast": {"text": None}}
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
                return {}

    def write(self, key, data):
        with self.lock:
            with open(self.files[key], "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# ربات اصلی – کامل‌ترین نسخه
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

        # لیست فحش خیلی قوی
        self.bad_words = [
            "کیر", "کس", "کص", "کوس", "جنده", "قحبه", "مادرجنده", "پدرسگ", "حرامزاده", "گایید", "سیکتیر",
            "کون", "گوه", "لاشی", "فاحشه", "سکس", "پورن", "خارکصه", "تخمم", "شاسگول", "پفیوز", "خر", "مرتیکه",
            "گوز", "جق", "بکن", "دیوث", "كير", "كس", "كص", "جنده", "قحبه", "گاييد", "كون", "گوه"
        ]

        self.register()
        logger.info("Shadow Titan v20.0 – کامل و بدون باگ")

    def contains_bad(self, text):
        if not text:
            return False
        t = text.lower()
        t = re.sub(r'[\s\*\-_\.\d]+', '', t)
        return any(word in t for word in self.bad_words)

    # کیبوردهای زیبا
    def kb_main(self, uid):
        db_u = self.db.read("users")
        vip = db_u["users"].get(uid, {}).get("vip", False)
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        kb.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        kb.add("🎡 گردونه شانس روزانه")
        kb.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if uid == self.owner:
            kb.add("📊 پنل مدیریت")
        return kb

    def kb_chatting(self):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        kb.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return kb

    def kb_admin(self):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("📈 آمار کامل", "🛠 تعمیر و نگهداری")
        kb.add("🎖 گیفت VIP تکی", "🎖 گیفت VIP همگانی")
        kb.add("❌ حذف VIP", "📋 لیست VIP")
        kb.add("📁 دانلود دیتابیس", "🚫 لیست بن‌شده‌ها")
        kb.add("🔙 بازگشت به منو")
        return kb

    def kb_report(self):
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton("فحاشی", callback_data="rep_insult"),
               types.InlineKeyboardButton("+18", callback_data="rep_nsfw"))
        kb.add(types.InlineKeyboardButton("اسپم", callback_data="rep_spam"),
               types.InlineKeyboardButton("آزار", callback_data="rep_harass"))
        kb.add(types.InlineKeyboardButton("لغو ❌", callback_data="rep_cancel"))
        return kb

    # توابع کمکی
    def ban_perm(self, uid, reason="تخلف"):
        db_b = self.db.read("bans")
        db_b["permanent"][uid] = reason
        self.db.write("bans", db_b)
        try:
            self.bot.send_message(uid, f"🚫 <b>بن دائم شدید!</b>\nدلیل: {reason}\nپشتیبانی: {self.support}")
        except:
            pass

    def end_chat(self, a, b, msg="ترک کرد"):
        db_u = self.db.read("users")
        db_u["users"][a]["partner"] = None
        db_u["users"][b]["partner"] = None
        self.db.write("users", db_u)
        self.bot.send_message(a, "چت با موفقیت پایان یافت 🌙", reply_markup=self.kb_main(a))
        self.bot.send_message(b, f"هم‌صحبت شما چت رو {msg} 🌙", reply_markup=self.kb_main(b))

    # ثبت هندلرها
    def register(self):
        @self.bot.message_handler(commands=['start'])
        def start(msg):
            uid = str(msg.chat.id)
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None

            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            db_c = self.db.read("config")

            # چک بن
            if uid in db_b["permanent"]:
                self.bot.send_message(uid, f"🚫 <b>حساب شما بن دائم است</b>\nدلیل: {db_b['permanent'][uid]}\nپشتیبانی: {self.support}")
                return
            if uid in db_b["temporary"]:
                if datetime.datetime.now().timestamp() < db_b["temporary"][uid]["end"]:
                    rem = int((db_b["temporary"][uid]["end"] - datetime.datetime.now().timestamp()) / 60)
                    self.bot.send_message(uid, f"🚫 <b>بن موقت</b>\nزمان باقی‌مانده: {rem} دقیقه")
                    return

            # تعمیر
            vip = db_u["users"].get(uid, {}).get("vip", False)
            if db_c["settings"]["maintenance"] and not (vip or uid == self.owner):
                self.bot.send_message(uid, "🔧 <b>ربات در حال تعمیر و نگهداری است</b>\n\n"
                                          "فقط کاربران VIP دسترسی دارند 🌟\nپشتیبانی: {self.support}")
                return

            # لینک ناشناس
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    self.bot.send_message(uid, "نمی‌تونید به خودتون پیام بدید 😊")
                    return
                if uid not in db_u["users"]:
                    db_u["users"][uid] = {"state": "name", "vip": False, "warns": 0, "blocks": [], "last_spin": "", "anon_target": target}
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "برای ارسال پیام ناشناس، نام مستعار وارد کنید ✨")
                else:
                    db_u["users"][uid]["state"] = "anon_send"
                    db_u["users"][uid]["anon_target"] = target
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "پیام ناشناس خود را بنویسید ✉️")
                return

            # ثبت‌نام
            if uid not in db_u["users"]:
                db_u["users"][uid] = {"state": "name", "vip": False, "warns": 0, "blocks": [], "last_spin": ""}
                self.db.write("users", db_u)
                self.bot.send_message(uid, "🌟 به Shadow Titan خوش آمدی!\nنام مستعار خود را وارد کنید:")
            else:
                self.bot.send_message(uid, "خوش برگشتی عزیز 🌹", reply_markup=self.kb_main(uid))

        @self.bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def handler(msg):
            uid = str(msg.chat.id)
            db_u = self.db.read("users")
            db_b = self.db.read("bans")

            if uid in db_b["permanent"] or (uid in db_b["temporary"] and datetime.datetime.now().timestamp() < db_b["temporary"][uid]["end"]):
                return

            user = db_u["users"].get(uid)
            if not user:
                return

            # ثبت‌نام
            if user["state"] == "name":
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

            if user["state"] == "age":
                if not msg.text.isdigit() or not 12 <= int(msg.text) <= 99:
                    self.bot.send_message(uid, "❌ سن باید عددی بین ۱۲ تا ۹۹ باشد")
                    return
                user["age"] = int(msg.text)
                user["state"] = "idle"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "ثبت‌نام با موفقیت انجام شد 🎉\nحالا از ربات لذت ببر!", reply_markup=self.kb_main(uid))
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
                    self.db.write("users", db_u)
                    return

                if msg.text == "🚫 بلاک و خروج":
                    if partner not in user.get("blocks", []):
                        user["blocks"].append(partner)
                    self.db.write("users", db_u)
                    self.end_chat(uid, partner, "بلاک کرد")
                    return

                # فیلتر فحش
                if msg.text and self.contains_bad(msg.text):
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
                    self.bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3\nفحاشی ممنوع است!")
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
                self.bot.send_message(uid, "جستجو لغو شد ✅", reply_markup=self.kb_main(uid))
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
                rank = "🎖 VIP" if user.get("vip", False) else "عادی"
                self.bot.send_message(uid, f"<b>پروفایل شما</b>\n\n"
                                          f"نام: {user['name']}\n"
                                          f"جنسیت: {user.get('sex', '—')}\n"
                                          f"سن: {user.get('age', '—')}\n"
                                          f"رنک: {rank}\n"
                                          f"اخطار: {user.get('warns', 0)}")

            elif text == "📩 لینک ناشناس من":
                link = f"https://t.me/{self.username}?start=msg_{uid}"
                self.bot.send_message(uid, f"<b>لینک ناشناس شما</b>\n\n{link}\n\n"
                                          "با اشتراک این لینک، دیگران می‌تونن ناشناس به شما پیام بفرستن ✨")

            elif text == "📥 پیام‌های ناشناس":
                db_m = self.db.read("messages")
                inbox = db_m["inbox"].get(uid, [])
                if not inbox:
                    self.bot.send_message(uid, "هیچ پیام ناشناسی ندارید 📭")
                    return
                kb = types.InlineKeyboardMarkup()
                txt = "<b>پیام‌های ناشناس شما</b>\n\n"
                for i, m in enumerate(inbox):
                    txt += f"{i+1}. {m['text']}\n<i>{m['time']}</i>\n\n"
                    kb.add(types.InlineKeyboardButton(f"پاسخ به پیام {i+1}", callback_data=f"anon_reply_{i}"))
                self.bot.send_message(uid, txt, reply_markup=kb)

            elif text == "🎡 گردونه شانس روزانه":
                today = str(datetime.date.today())
                if user.get("last_spin") == today:
                    self.bot.send_message(uid, "امروز قبلاً چرخوندید 😊")
                    return
                user["last_spin"] = today
                if random.random() < 0.05:
                    user["vip"] = True
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "🎉🎉 <b>تبریک! شما رنک VIP گرفتید!</b> 🎖\nمبارک باشه ✨")
                else:
                    self.bot.send_message(uid, "گردونه چرخید... پوچ! شانس بعدی 🌟")
                self.db.write("users", db_u)

            elif text == "📊 پنل مدیریت" and uid == self.owner:
                self.bot.send_message(uid, "<b>پنل مدیریت پیشرفته</b>", reply_markup=self.kb_admin())

            # ادمین
            if uid == self.owner:
                if text == "📈 آمار کامل":
                    total = len(db_u["users"])
                    males = sum(1 for d in db_u["users"].values() if d.get("sex") == "آقا")
                    females = total - males
                    vips = sum(1 for d in db_u["users"].values() if d.get("vip"))
                    self.bot.send_message(uid, f"<b>آمار ربات</b>\n\n"
                                              f"کل کاربران: {total}\n"
                                              f"آقا: {males}\n"
                                              f"خانم: {females}\n"
                                              f"VIP: {vips}")

                elif text == "🛠 تعمیر و نگهداری":
                    db_c = self.db.read("config")
                    db_c["settings"]["maintenance"] = not db_c["settings"]["maintenance"]
                    self.db.write("config", db_c)
                    status = "فعال 🟢" if db_c["settings"]["maintenance"] else "غیرفعال 🔴"
                    self.bot.send_message(uid, f"حالت تعمیر: {status}")

                elif text == "🎖 گیفت VIP تکی":
                    user["state"] = "gift_single_id"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "آیدی عددی کاربر را وارد کنید:")

                elif text == "🎖 گیفت VIP همگانی":
                    user["state"] = "gift_all_reason"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "دلیل گیفت همگانی را بنویسید:")

                elif text == "❌ حذف VIP":
                    user["state"] = "remove_vip_id"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "آیدی عددی برای حذف VIP:")

                elif text == "📋 لیست VIP":
                    vips = [u for u, d in db_u["users"].items() if d.get("vip")]
                    if not vips:
                        self.bot.send_message(uid, "هیچ کاربر VIP وجود ندارد")
                    else:
                        msg = "<b>لیست کاربران VIP</b>\n\n"
                        for v in vips:
                            name = db_u["users"][v]["name"]
                            msg += f"{v} - {name}\n"
                        self.bot.send_message(uid, msg)

                elif text == "📁 دانلود دیتابیس":
                    for file in self.db.files.values():
                        if os.path.exists(file):
                            self.bot.send_document(uid, open(file, 'rb'), caption=f"📄 {file}")

                elif text == "🚫 لیست بن‌شده‌ها":
                    msg = "<b>لیست بن‌شده‌ها</b>\n\n"
                    kb = types.InlineKeyboardMarkup()
                    for u, reason in db_b["permanent"].items():
                        name = db_u["users"].get(u, {}).get("name", "نامشخص")
                        msg += f"🆔 {u} - {name} (دائم - {reason})\n"
                        kb.add(types.InlineKeyboardButton(f"بخشیدن {u}", callback_data=f"unban_perm_{u}"))
                    for u, data in db_b["temporary"].items():
                        name = db_u["users"].get(u, {}).get("name", "نامشخص")
                        msg += f"🆔 {u} - {name} (موقت)\n"
                    self.bot.send_message(uid, msg, reply_markup=kb)

                # حالت‌های گیفت VIP
                if user.get("state") == "gift_single_id" and msg.text.isdigit():
                    user["gift_target"] = msg.text
                    user["state"] = "gift_single_reason"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "دلیل گیفت VIP را بنویسید:")

                if user.get("state") == "gift_single_reason":
                    reason = msg.text
                    target = user["gift_target"]
                    if target in db_u["users"]:
                        db_u["users"][target]["vip"] = True
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, f"✅ VIP به {target} گیفت شد")
                        try:
                            self.bot.send_message(target, f"🎉 <b>تبریک! رنک VIP دریافت کردید 🎖</b>\n\n"
                                                         f"دلیل: {reason}\nمبارک باشه! ✨")
                        except:
                            pass
                    user["state"] = "idle"
                    self.db.write("users", db_u)

                if user.get("state") == "gift_all_reason":
                    reason = msg.text
                    sent = 0
                    for u in db_u["users"]:
                        db_u["users"][u]["vip"] = True
                        try:
                            self.bot.send_message(u, f"🎉 <b>تبریک! رنک VIP دریافت کردید 🎖</b>\n\n"
                                                     f"دلیل: {reason}\nاز طرف مدیریت 🌟")
                            sent += 1
                        except:
                            pass
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, f"✅ VIP به {sent} کاربر گیفت شد")
                    user["state"] = "idle"
                    self.db.write("users", db_u)

                if user.get("state") == "remove_vip_id" and msg.text.isdigit():
                    target = msg.text
                    if target in db_u["users"]:
                        db_u["users"][target]["vip"] = False
                        self.db.write("users", db_u)
                        self.bot.send_message(uid, f"❌ VIP از {target} حذف شد")
                    user["state"] = "idle"
                    self.db.write("users", db_u)

            # بازگشت
            if "بازگشت" in text:
                self.bot.send_message(uid, "منوی اصلی 🌟", reply_markup=self.kb_main(uid))

        # کال‌بک‌ها
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback(call):
            uid = str(call.from_user.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            if not user: return

            if call.data.startswith("sex_"):
                user["sex"] = "آقا" if call.data == "sex_m" else "خانم"
                user["state"] = "age"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "سن خود را وارد کنید (۱۲–۹۹):")

            if call.data.startswith("find_"):
                self.bot.edit_message_text("در حال جستجو... 🔍", call.message.chat.id, call.message.message_id)
                self.bot.send_message(uid, "برای لغو جستجو دکمه زیر را بزنید:", reply_markup=types.ReplyKeyboardMarkup().add("❌ لغو جستجو"))

                db_q = self.db.read("queue")
                if uid not in db_q["general"]:
                    db_q["general"].append(uid)
                self.db.write("queue", db_q)

                pots = [p for p in db_q["general"] if p != uid]
                pots = [p for p in pots if uid not in db_u["users"][p].get("blocks", []) and p not in user.get("blocks", [])]

                if pots:
                    partner = random.choice(pots)
                    db_q["general"].remove(uid)
                    db_q["general"].remove(partner)
                    self.db.write("queue", db_q)

                    user["partner"] = partner
                    db_u["users"][partner]["partner"] = uid
                    self.db.write("users", db_u)

                    self.bot.send_message(uid, "هم‌صحبت پیدا شد! 💬 شروع کنید", reply_markup=self.kb_chatting())
                    self.bot.send_message(partner, "هم‌صحبت پیدا شد! 💬 شروع کنید", reply_markup=self.kb_chatting())
                # اگر نه، در صف می‌مونه

            if call.data == "end_yes":
                self.end_chat(uid, user["partner"], "پایان داد")

            if call.data == "rep_cancel":
                self.bot.answer_callback_query(call.id, "گزارش لغو شد ✅")

            if call.data.startswith("unban_perm_"):
                if uid == self.owner:
                    target = call.data.split("_")[2]
                    db_b = self.db.read("bans")
                    if target in db_b["permanent"]:
                        del db_b["permanent"][target]
                        self.db.write("bans", db_b)
                        self.bot.edit_message_text("کاربر بخشیده شد ✅", self.owner, call.message.message_id)
                        try:
                            self.bot.send_message(target, "حساب شما از بن خارج شد 🌟")
                        except:
                            pass

    def run(self):
        print("Shadow Titan v20.0 – کامل‌ترین و بدون باگ")
        self.bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot = ShadowTitanBot()
    bot.run()
