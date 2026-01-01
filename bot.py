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
# 1. سیستم مدیریت لاگ و مانیتورینگ پیشرفته
# ==========================================
logging.basicConfig(
    filename='bot_internal_core.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger("ShadowTitan")

# وب‌سرور برای زنده نگه داشتن ربات
app = Flask('')
@app.route('/')
def status(): return "Shadow Titan v14.0: Full Systems Operational"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# ==========================================
# 2. کلاس مدیریت دیتابیس
# ==========================================
class DatabaseManager:
    def __init__(self):
        self.files = {
            "users": "db_users.json",
            "bans": "db_bans.json",
            "queue": "db_queue.json",
            "messages": "db_messages.json",  # پیام‌های ناشناس
            "reports": "db_reports.json",
            "config": "db_config.json"
        }
        self.lock = threading.Lock()
        self._init_files()

    def _init_files(self):
        with self.lock:
            defaults = {
                "users": {"users": {}},
                "bans": {"blacklist": {}},
                "queue": {"general": []},
                "messages": {"inbox": {}},
                "reports": {"archive": []},
                "config": {"stats": {"chats": 0, "ai_detections": 0, "users": 0}, "settings": {"maintenance": False}}
            }
            for key, path in self.files.items():
                if not os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(defaults[key], f, indent=4, ensure_ascii=False)

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
# 3. هسته اصلی ربات
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        self.token = "8213706320:AAFH18CeAGRu-3Jkn8EZDYDhgSgDl_XMtvU"
        self.owner_id = "8013245091"  # آیدی عددی صاحب
        self.support_username = "@its_alimo"  # پشتیبانی
        self.channel = "@ChatNaAnnouncements"
        self.hf_token = "Hf_YKgVObJxRxvxIXQWIKOEmGpcZxwehvCKqk"
        
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.db = DatabaseManager()
        
        try:
            self.bot_username = self.bot.get_me().username
        except:
            self.bot_username = "ShadowTitanBot"  # fallback
        
        self.register_actions()
        logger.info("Bot Engine Started Successfully.")

    # ------------------------------------------
    # لایه هوش مصنوعی
    # ------------------------------------------
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

    # ------------------------------------------
    # کیبوردها
    # ------------------------------------------
    def get_kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس روزانه", "🏆 برترین‌ها")
        markup.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        if str(uid) == self.owner_id:
            markup.add("📊 پنل مدیریت", "📢 ارسال همگانی")
        return markup

    def get_kb_chatting(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def get_kb_gender(self):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("آقا 👦", callback_data="reg_sex_m"),
                   types.InlineKeyboardButton("خانم 👧", callback_data="reg_sex_f"))
        return markup

    # ------------------------------------------
    # هندلرها
    # ------------------------------------------
    def register_actions(self):
        @self.bot.message_handler(commands=['start'])
        def welcome(message):
            uid = str(message.chat.id)
            payload = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
            
            db_u = self.db.read("users")
            
            # حالت لینک ناشناس
            if payload and payload.startswith("msg_"):
                target = payload[4:]
                if target == uid:
                    self.bot.send_message(uid, "❌ نمی‌توانید به خودتان پیام ناشناس بفرستید.")
                    if uid in db_u["users"]:
                        self.bot.send_message(uid, "منوی اصلی:", reply_markup=self.get_kb_main(uid))
                    return
                
                if uid not in db_u["users"]:
                    db_u["users"][uid] = {
                        "state": "STEP_NAME", "name": "نامشخص", "sex": "نامشخص", "age": 0,
                        "warns": 0, "partner": None, "score": 10, "last_spin": "", "level": 1,
                        "blocks": [], "anon_target": target
                    }
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "👋 برای ارسال پیام ناشناس ابتدا نام مستعار خود را وارد کنید:")
                else:
                    user = db_u["users"][uid]
                    user["state"] = "ANON_SENDING"
                    user["anon_target"] = target
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "✉️ پیام ناشناس خود را بنویسید (فقط متن):")
                return
            
            # ثبت‌نام عادی
            if uid not in db_u["users"]:
                db_u["users"][uid] = {
                    "state": "STEP_NAME", "name": "نامشخص", "sex": "نامشخص", "age": 0,
                    "warns": 0, "partner": None, "score": 10, "last_spin": "", "level": 1,
                    "blocks": []
                }
                self.db.write("users", db_u)
                self.bot.send_message(uid, "👋 به ربات چت ناشناس شادو خوش آمدید!\n\nلطفاً <b>نام مستعار</b> خود را بفرستید:", reply_markup=types.ReplyKeyboardRemove())
            else:
                self.bot.send_message(uid, "خوش برگشتی! 🌟", reply_markup=self.get_kb_main(uid))

        @self.bot.message_handler(content_types=['text', 'photo', 'video', 'voice', 'sticker', 'animation', 'video_note'])
        def central_logic(message):
            uid = str(message.chat.id)
            db_u = self.db.read("users")
            db_b = self.db.read("bans")
            
            if uid in db_b["blacklist"]:
                self.bot.send_message(uid, "🚫 حساب شما مسدود است.")
                return
            
            try:
                if uid != self.owner_id:
                    status = self.bot.get_chat_member(self.channel, uid).status
                    if status not in ['member', 'administrator', 'creator']:
                        self.bot.send_message(uid, f"❌ برای استفاده باید در کانال عضو شوید:\n{self.channel}")
                        return
            except: pass
            
            user = db_u["users"].get(uid)
            if not user: return
            
            # ثبت‌نام
            if user["state"] == "STEP_NAME":
                if self.ai_toxic_scan(message.text) > 0.7 or self.ai_nsfw_scan(message.text) > 0.7:
                    self.bot.send_message(uid, "❌ نام نامناسب. دوباره امتحان کنید:")
                    return
                user["name"] = message.text[:20]
                user["state"] = "STEP_SEX"
                self.db.write("users", db_u)
                self.bot.send_message(uid, f"خوش آمدی <b>{user['name']}</b>!\nجنسیت خود را انتخاب کن:", reply_markup=self.get_kb_gender())
                return
            
            if user["state"] == "STEP_AGE":
                if not message.text.isdigit() or not 12 <= int(message.text) <= 99:
                    self.bot.send_message(uid, "❌ سن باید بین ۱۲ تا ۹۹ باشد:")
                    return
                user["age"] = int(message.text)
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "✅ ثبت‌نام کامل شد!", reply_markup=self.get_kb_main(uid))
                return
            
            # ارسال پیام ناشناس
            if user["state"] == "ANON_SENDING":
                if message.content_type != "text":
                    self.bot.send_message(uid, "❌ فقط متن مجاز است.")
                    return
                target = user["anon_target"]
                db_m = self.db.read("messages")
                if target not in db_m["inbox"]:
                    db_m["inbox"][target] = []
                db_m["inbox"][target].append({
                    "text": message.text,
                    "from": uid,
                    "seen": False,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                self.db.write("messages", db_m)
                self.bot.send_message(uid, "✅ پیام ناشناس ارسال شد.")
                try:
                    self.bot.send_message(target, "📩 یک پیام ناشناس جدید دریافت کردید!\nبرای مشاهده به «پیام‌های ناشناس» بروید.")
                except: pass
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                return
            
            # پاسخ به پیام ناشناس
            if user["state"] == "ANON_REPLYING":
                target = user["anon_reply_to"]
                self.bot.send_message(target, f"📩 پاسخ ناشناس:\n{message.text}")
                self.bot.send_message(uid, "✅ پاسخ ارسال شد.")
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                return
            
            # چت فعال
            if user.get("partner"):
                pid = user["partner"]
                
                if message.text == "🔚 پایان گفتگو":
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("بله 🔚", callback_data="chat_end_y"),
                               types.InlineKeyboardButton("خیر 🔙", callback_data="chat_end_n"))
                    self.bot.send_message(uid, "آیا مطمئن هستید؟", reply_markup=markup)
                    return
                
                if message.text == "🚩 گزارش تخلف":
                    user["state"] = "REPORT"
                    self.db.write("users", db_u)
                    self.bot.send_message(uid, "دلیل گزارش را بنویسید:")
                    return
                
                if message.text == "🚫 بلاک و خروج":
                    self.block_user(uid, pid)
                    self.end_chat(uid, pid, "بلاک شد")
                    return
                
                if message.text == "👥 درخواست آیدی":
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("بله ✅", callback_data=f"id_share_y_{uid}"),
                               types.InlineKeyboardButton("خیر ❌", callback_data="id_share_n"))
                    self.bot.send_message(pid, "هم‌صحبت درخواست آیدی شما را دارد. موافقید؟", reply_markup=markup)
                    self.bot.send_message(uid, "درخواست ارسال شد.")
                    return
                
                # بررسی محتوای نامناسب
                if message.text:
                    toxic = self.ai_toxic_scan(message.text)
                    nsfw = self.ai_nsfw_scan(message.text)
                    if toxic > 0.85 or nsfw > 0.85:
                        self.bot.delete_message(uid, message.message_id)
                        user["warns"] += 1
                        self.db.write("users", db_u)
                        if user["warns"] >= 3:
                            self.auto_ban(uid, pid)
                            return
                        self.bot.send_message(uid, f"⚠️ اخطار {user['warns']}/3 - محتوای نامناسب تشخیص داده شد.")
                        return
                
                try:
                    self.bot.copy_message(pid, uid, message.message_id)
                except: pass
                return
            
            if user["state"] == "REPORT":
                db_r = self.db.read("reports")
                db_r["archive"].append({"from": uid, "target": user["partner"], "reason": message.text, "date": str(datetime.datetime.now())})
                self.db.write("reports", db_r)
                self.bot.send_message(uid, "✅ گزارش ثبت شد.")
                try:
                    self.bot.send_message(self.owner_id, f"🚩 گزارش جدید از {uid} علیه {user['partner']}: {message.text}")
                except: pass
                user["state"] = "IDLE"
                self.db.write("users", db_u)
                return
            
            # منوی اصلی
            self.handle_main_menu(message, uid, user, db_u)

        self.init_callbacks()

    def handle_main_menu(self, message, uid, user, db_u):
        text = message.text
        
        if text == "🛰 شروع چت ناشناس":
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
                       types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
                       types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any"))
            self.bot.send_message(uid, "🔍 دنبال چه کسی می‌گردی؟", reply_markup=markup)
        
        elif text == "👤 پروفایل من":
            self.bot.send_message(uid, f"👤 <b>پروفایل شما:</b>\n\n🏷 نام: {user['name']}\n⚧ جنسیت: {user['sex']}\n🔢 سن: {user['age']}\n🏆 امتیاز: {user['score']}\n⚠️ اخطار: {user['warns']}")
        
        elif text == "📩 لینک ناشناس من":
            link = f"https://t.me/{self.bot_username}?start=msg_{uid}"
            self.bot.send_message(uid, f"📩 <b>لینک ناشناس شما:</b>\n\n{link}\n\nبا اشتراک این لینک، دیگران می‌توانند ناشناس به شما پیام بفرستند.")
        
        elif text == "📥 پیام‌های ناشناس":
            db_m = self.db.read("messages")
            messages = db_m["inbox"].get(uid, [])
            if not messages:
                self.bot.send_message(uid, "📥 هیچ پیام ناشناسی ندارید.")
                return
            
            markup = types.InlineKeyboardMarkup()
            text_msg = "<b>پیام‌های ناشناس شما:</b>\n\n"
            for i, msg in enumerate(messages):
                text_msg += f"<b>{i+1}.</b> {msg['text']}\n<i>{msg['time']}</i>\n\n"
                markup.add(types.InlineKeyboardButton(f"پاسخ به پیام {i+1}", callback_data=f"anon_reply_{i}"))
            
            self.bot.send_message(uid, text_msg, reply_markup=markup)
            
            # علامت‌گذاری به عنوان دیده شده
            updated = False
            for msg in messages:
                if not msg["seen"]:
                    msg["seen"] = True
                    updated = True
                    try:
                        self.bot.send_message(msg["from"], "✅ پیام ناشناس شما دیده شد.")
                    except: pass
            if updated:
                self.db.write("messages", db_m)
        
        elif text == "🎡 گردونه شانس روزانه":
            today = str(datetime.date.today())
            if user["last_spin"] == today:
                self.bot.send_message(uid, "❌ امروز قبلاً چرخوندید!")
                return
            win = random.choice([5, 10, 15, 20, -5, 0])
            user["score"] += win
            user["last_spin"] = today
            self.db.write("users", db_u)
            self.bot.send_message(uid, f"🎡 گردونه چرخید! شما <b>{win}</b> امتیاز {'بردید' if win > 0 else 'باختید'}!\nامتیاز کل: {user['score']}")
        
        elif text == "🏆 برترین‌ها":
            all_users = sorted(db_u["users"].items(), key=lambda x: x[1]["score"], reverse=True)[:10]
            msg = "<b>🏆 برترین کاربران:</b>\n\n"
            for i, (u, data) in enumerate(all_users, 1):
                msg += f"{i}. {data['name']} - {data['score']} امتیاز\n"
            self.bot.send_message(uid, msg)
        
        elif text == "❓ راهنما و قوانین":
            guide = (f"<b>📜 راهنما و قوانین</b>\n\n"
                     "• چت ناشناس کاملاً ناشناس است\n"
                     "• فحاشی، محتوای +18 و اسپم ممنوع\n"
                     "• گزارش تخلف = اخطار → بن\n"
                     "• لینک ناشناس برای دریافت پیام ناشناس\n"
                     f"• پشتیبانی: {self.support_username}")
            self.bot.send_message(uid, guide)
        
        elif text == "⚙ تنظیمات":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت", "🔙 منوی اصلی")
            self.bot.send_message(uid, "⚙ تنظیمات:", reply_markup=markup)
        
        elif text in ["✏️ تغییر نام", "🔢 تغییر سن", "⚧ تغییر جنسیت", "🔙 منوی اصلی"]:
            if text == "🔙 منوی اصلی":
                self.bot.send_message(uid, "بازگشت به منو", reply_markup=self.get_kb_main(uid))
            elif text == "✏️ تغییر نام":
                user["state"] = "SET_NAME"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "نام جدید را وارد کنید:")
            elif text == "🔢 تغییر سن":
                user["state"] = "SET_AGE"
                self.db.write("users", db_u)
                self.bot.send_message(uid, "سن جدید را وارد کنید:")
            elif text == "⚧ تغییر جنسیت":
                self.bot.send_message(uid, "جنسیت جدید:", reply_markup=self.get_kb_gender())

        # تنظیمات ادمین (در صورت نیاز بیشتر اضافه کنید)

    # ------------------------------------------
    # کال‌بک‌ها
    # ------------------------------------------
    def init_callbacks(self):
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            uid = str(call.from_user.id)
            db_u = self.db.read("users")
            user = db_u["users"].get(uid)
            if not user: return
            
            if call.data.startswith("reg_sex_"):
                user["sex"] = "آقا" if call.data.endswith("m") else "خانم"
                user["state"] = "STEP_AGE"
                self.db.write("users", db_u)
                self.bot.edit_message_text(chat_id=uid, message_id=call.message.message_id, text="🔢 سن خود را وارد کنید:")
            
            elif call.data.startswith("find_"):
                pref = call.data[5:]  # m, f, any
                self.bot.edit_message_text(chat_id=uid, message_id=call.message.message_id, text="🔍 در حال جستجو...")
                
                db_q = self.db.read("queue")
                q = db_q["general"]
                
                if uid not in q:
                    q.append(uid)
                self.db.write("queue", db_q)
                
                # پیدا کردن پارتنر
                all_pots = [p for p in q if p != uid]
                # حذف بلاک‌شده‌ها
                all_pots = [p for p in all_pots if uid not in db_u["users"][p].get("blocks", []) and p not in user.get("blocks", [])]
                
                if not all_pots:
                    self.bot.send_message(uid, "⏳ در صف انتظار هستید... کمی صبر کنید یا دوباره جستجو کنید.")
                    return
                
                # اولویت جنسیت
                opposite = "خانم" if user["sex"] == "آقا" else "آقا"
                target_sex = opposite if pref in ["m", "f"] else None
                if pref == "m": target_sex = "خانم"
                if pref == "f": target_sex = "آقا"
                
                preferred = [p for p in all_pots if target_sex is None or db_u["users"][p]["sex"] == target_sex]
                pots = preferred or all_pots
                
                partner = random.choice(pots)
                q.remove(uid)
                q.remove(partner)
                self.db.write("queue", db_q)
                
                user["partner"] = partner
                db_u["users"][partner]["partner"] = uid
                self.db.write("users", db_u)
                
                db_c = self.db.read("config")
                db_c["stats"]["chats"] += 1
                self.db.write("config", db_c)
                
                self.bot.send_message(uid, "💎 هم‌صحبت پیدا شد! چت را شروع کنید.", reply_markup=self.get_kb_chatting())
                self.bot.send_message(partner, "💎 هم‌صحبت پیدا شد! چت را شروع کنید.", reply_markup=self.get_kb_chatting())
            
            elif call.data == "chat_end_y":
                pid = user["partner"]
                self.end_chat(uid, pid, "ترک کرد")
            
            elif call.data.startswith("id_share_y_"):
                sharer = call.data.split("_")[3]
                username = call.from_user.username
                self.bot.send_message(sharer, f"👥 آیدی هم‌صحبت: @{username or call.from_user.id}")
            
            elif call.data.startswith("anon_reply_"):
                index = int(call.data.split("_")[2])
                db_m = self.db.read("messages")
                msg = db_m["inbox"][uid][index]
                user["state"] = "ANON_REPLYING"
                user["anon_reply_to"] = msg["from"]
                self.db.write("users", db_u)
                self.bot.send_message(uid, "پاسخ خود را بنویسید:")
            
    def end_chat(self, uid, pid, reason):
        db_u = self.db.read("users")
        db_u["users"][uid]["partner"] = None
        db_u["users"][pid]["partner"] = None
        self.db.write("users", db_u)
        self.bot.send_message(uid, "👋 چت پایان یافت.", reply_markup=self.get_kb_main(uid))
        self.bot.send_message(pid, f"⚠️ هم‌صحبت چت را {reason}.", reply_markup=self.get_kb_main(pid))
    
    def block_user(self, uid, target):
        db_u = self.db.read("users")
        if target not in db_u["users"][uid]["blocks"]:
            db_u["users"][uid]["blocks"].append(target)
        self.db.write("users", db_u)
        self.bot.send_message(uid, "🚫 کاربر بلاک شد و دیگر متصل نمی‌شوید.")
    
    def auto_ban(self, uid, pid=None):
        db_b = self.db.read("bans")
        db_b["blacklist"][uid] = {"reason": "محتوای نامناسب", "date": str(datetime.datetime.now())}
        self.db.write("bans", db_b)
        self.bot.send_message(uid, "🚫 به دلیل تخلف مکرر بن شدید.")
        if pid:
            self.bot.send_message(pid, "⚠️ هم‌صحبت بن شد.", reply_markup=self.get_kb_main(pid))

    def run(self):
        print("--- Shadow Titan v14.0 Running ---")
        self.bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_web_server).start()
    bot = ShadowTitanBot()
    bot.run()
