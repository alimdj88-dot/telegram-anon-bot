"""
Shadow Titan Bot - Secure Edition v42.1
Anonymous Chat Bot with Advanced Security Fixes
"""

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
from functools import wraps
from typing import Dict, Any, Optional, Callable

# ==========================================
# Configuration & Environment Setup
# ==========================================
from dotenv import load_dotenv

load_dotenv()

# Security: All sensitive data from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@ChatNaAnnouncements")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@its_alimo")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not set in environment variables!")
if not OWNER_ID:
    raise ValueError("❌ OWNER_ID not set!")

# Convert OWNER_ID to string for consistent comparison
OWNER_ID = str(OWNER_ID)

# ==========================================
# Secure Logging System
# ==========================================
logging.basicConfig(
    filename='shadow_titan_secure.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(funcName)s | %(message)s'
)
logger = logging.getLogger("ShadowTitanSecure")

# Add console handler for immediate feedback
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

# ==========================================
# Web Server (Keep Alive)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Shadow Titan v42.1 – Secure Edition Running"

@app.route('/health')
def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

def run_web():
    app.run(host='0.0.0.0', port=8080, threaded=True)

# ==========================================
# Thread-Safe Database Manager
# ==========================================
class SecureDB:
    def __init__(self):
        self.files = {
            "users": "db_users.json",
            "bans": "db_bans.json",
            "queue": "db_queue.json",
            "messages": "db_messages.json",
            "config": "db_config.json",
            "missions": "db_missions.json",
            "chats": "db_chats.json"
        }
        self.lock = threading.RLock()  # Reentrant lock for nested operations
        self.init_files()

    def init_files(self):
        defaults = {
            "users": {"users": {}, "events": {}, "discounts": {}},
            "bans": {"permanent": {}, "temporary": {}},
            "queue": {"general": []},
            "messages": {"inbox": {}},
            "config": {
                "settings": {
                    "maintenance": False,
                    "vip_message_limit": 100,
                    "chat_search_time": 30,
                    "daily_report_limit": 5,
                    "auto_search": True,
                    "word_filter": True,
                    "ai_scan": True,
                    "chat_restore": True,
                    "welcome_message": True,
                    "reward_message": True,
                    "warning_message": True,
                    "anon_notify": True
                },
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
            "chats": {}
        }
        
        with self.lock:
            for key, path in self.files.items():
                if not os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(defaults.get(key, {}), f, ensure_ascii=False, indent=4)
                    logger.info(f"Created default database: {path}")

    def read(self, key: str) -> Dict[str, Any]:
        """Thread-safe read operation"""
        with self.lock:
            try:
                with open(self.files[key], "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
                logger.error(f"Error reading {key}: {e}")
                return {}

    def write(self, key: str, data: Dict[str, Any]) -> bool:
        """Thread-safe write operation"""
        with self.lock:
            try:
                # Write to temp file first (atomic operation)
                temp_path = self.files[key] + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                # Atomic rename
                os.replace(temp_path, self.files[key])
                return True
            except Exception as e:
                logger.error(f"Error writing {key}: {e}")
                return False

    def atomic_update(self, key: str, update_func: Callable[[Dict], Dict]) -> Optional[Dict]:
        """Atomic read-modify-write operation"""
        with self.lock:
            try:
                # Read current state
                with open(self.files[key], "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Apply update
                updated_data = update_func(data.copy())
                
                # Write atomically
                temp_path = self.files[key] + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(updated_data, f, ensure_ascii=False, indent=4)
                
                os.replace(temp_path, self.files[key])
                return updated_data
            except Exception as e:
                logger.error(f"Error in atomic update {key}: {e}")
                return None

    def get_user(self, uid: str) -> Optional[Dict]:
        """Get user data safely"""
        db = self.read("users")
        return db.get("users", {}).get(str(uid))

    def update_user(self, uid: str, update_func: Callable[[Dict], Dict]) -> bool:
        """Update specific user atomically"""
        uid = str(uid)
        
        def updater(data):
            if "users" not in data:
                data["users"] = {}
            if uid not in data["users"]:
                data["users"][uid] = {}
            
            user_data = data["users"][uid]
            updated_user = update_func(user_data.copy())
            data["users"][uid] = updated_user
            return data
        
        result = self.atomic_update("users", updater)
        return result is not None

# ==========================================
# Input Validation & Sanitization
# ==========================================
class InputValidator:
    @staticmethod
    def validate_user_id(uid: Any) -> Optional[str]:
        """Validate and sanitize user ID"""
        try:
            uid_str = str(uid)
            # Telegram user IDs are positive integers
            if not uid_str.isdigit():
                return None
            uid_int = int(uid_str)
            if uid_int <= 0 or uid_int > 999999999999:
                return None
            return uid_str
        except (ValueError, TypeError):
            return None

    @staticmethod
    def sanitize_text(text: str, max_length: int = 4096) -> str:
        """Sanitize user input text"""
        if not text or not isinstance(text, str):
            return ""
        
        # Remove control characters except newlines
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length
        return text[:max_length]

    @staticmethod
    def validate_age(age_str: str) -> Optional[int]:
        """Validate age input"""
        try:
            age = int(age_str)
            if 12 <= age <= 99:
                return age
            return None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def validate_coins(amount_str: str) -> Optional[int]:
        """Validate coin amount"""
        try:
            amount = int(amount_str)
            if 0 <= amount <= 1000000:  # Reasonable limit
                return amount
            return None
        except (ValueError, TypeError):
            return None

# ==========================================
# Main Bot Class - Secure Edition
# ==========================================
class ShadowTitanBot:
    def __init__(self):
        self.token = BOT_TOKEN
        self.owner = OWNER_ID
        self.channel = CHANNEL_ID
        self.support = SUPPORT_USERNAME
        self.hf_token = HF_TOKEN
        
        self.validator = InputValidator()
        self.db = SecureDB()
        
        # Initialize bot with exception handling
        try:
            self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
            bot_info = self.bot.get_me()
            self.username = bot_info.username
            logger.info(f"Bot initialized: @{self.username}")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

        # VIP Configuration
        self.vip_prices_coins = {
            "week": 500,
            "month": 1800,
            "3month": 5000,
            "6month": 9000,
            "year": 15000,
            "christmas": 0
        }

        self.vip_durations = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "3month": 90 * 24 * 3600,
            "6month": 180 * 24 * 3600,
            "year": 365 * 24 * 3600,
            "christmas": 90 * 24 * 3600
        }

        # Bad words list (can be loaded from external file)
        self.bad_words = self._load_bad_words()
        
        # Maintenance warning system
        self.maintenance_warning_active = False
        self.maintenance_warning_event = threading.Event()
        self.maintenance_lock = threading.Lock()

        # Restore active chats on startup
        self.restore_active_chats()
        
        # Start daily mission updater
        self.auto_update_daily_mission()
        
        # Register all handlers
        self.register_handlers()
        
        logger.info("Shadow Titan Secure v42.1 initialized successfully")

    def _load_bad_words(self) -> list:
        """Load bad words from file or use default"""
        default_words = [
            "کیر", "کیرم", "کیرت", "کیری", "کس", "کص", "کوس", "کوث",
            "جنده", "جهنده", "مادرجنده", "قحبه", "قهبه",
            "پدرسگ", "پدرسوخته", "حرامزاده", "گاییدم", "گاییدن",
            "سیکتیر", "کون", "کونی", "گوه", "لاشی", "فاحشه",
            "ناموس", "اوبی", "بی‌ناموس", "سکس", "پورن",
            "خارکصه", "تخمم", "شاسگول", "پفیوز", "دیوث"
        ]
        
        try:
            if os.path.exists("bad_words.txt"):
                with open("bad_words.txt", "r", encoding="utf-8") as f:
                    words = [line.strip() for line in f if line.strip()]
                    return words if words else default_words
        except Exception as e:
            logger.error(f"Error loading bad words: {e}")
        
        return default_words

    # ==========================================
    # Security & Utility Methods
    # ==========================================
    def is_owner(self, uid: str) -> bool:
        """Secure owner check"""
        return str(uid) == str(self.owner)

    def is_vip(self, uid: str) -> bool:
        """Check VIP status with proper error handling"""
        try:
            user = self.db.get_user(str(uid))
            if not user:
                return False
            vip_end = user.get("vip_end", 0)
            return vip_end > datetime.datetime.now().timestamp()
        except Exception as e:
            logger.error(f"Error checking VIP status for {uid}: {e}")
            return False

    def check_ban_status(self, uid: str) -> tuple:
        """
        Check if user is banned
        Returns: (is_banned: bool, ban_info: dict)
        """
        uid = str(uid)
        db_b = self.db.read("bans")
        
        # Check permanent ban
        if uid in db_b.get("permanent", {}):
            return True, {
                "type": "permanent",
                "reason": db_b["permanent"][uid]
            }
        
        # Check temporary ban
        if uid in db_b.get("temporary", {}):
            ban_data = db_b["temporary"][uid]
            end_time = ban_data.get("end", 0)
            
            if datetime.datetime.now().timestamp() < end_time:
                remaining = int((end_time - datetime.datetime.now().timestamp()) / 60)
                return True, {
                    "type": "temporary",
                    "reason": ban_data.get("reason", "تخلف"),
                    "remaining_minutes": remaining,
                    "end_time": end_time
                }
            else:
                # Ban expired, remove it
                def updater(data):
                    if "temporary" in data and uid in data["temporary"]:
                        del data["temporary"][uid]
                    return data
                self.db.atomic_update("bans", updater)
        
        return False, {}

    def check_channel_membership(self, uid: str) -> bool:
        """Check if user is member of required channel"""
        if self.is_owner(uid):
            return True
        
        try:
            member = self.bot.get_chat_member(self.channel, uid)
            return member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            logger.error(f"Channel check error for {uid}: {e}")
            # Fail open for better UX, or change to False for strict security
            return True

    def contains_bad_words(self, text: str) -> bool:
        """Check for bad words with normalization"""
        if not text:
            return False
        
        # Normalize text
        normalized = text.lower()
        normalized = re.sub(r'[\s\*\-_\.\d]+', '', normalized)
        normalized = re.sub(r'(.)\1+', r'\1', normalized)  # Remove repeated chars
        
        return any(word in normalized for word in self.bad_words)

    def ai_content_scan(self, text: str, scan_type: str = "toxic") -> float:
        """
        AI-powered content scanning
        Returns confidence score (0.0 - 1.0)
        """
        if not text or len(text.strip()) < 2:
            return 0.0
        
        # Rate limiting for API calls
        # In production, implement proper rate limiting
        
        clean_text = re.sub(r'[^ا-یa-zA-Z0-9\s]', '', text)
        
        endpoints = {
            "toxic": "unitary/toxic-bert",
            "nsfw": "michellejieli/nsfw_text_classifier"
        }
        
        if scan_type not in endpoints:
            return 0.0
        
        url = f"https://api-inference.huggingface.co/models/{endpoints[scan_type]}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                json={"inputs": clean_text}, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data and isinstance(data[0], list):
                    for item in data[0]:
                        if item.get('label') == scan_type:
                            return item.get('score', 0.0)
            elif response.status_code == 429:
                logger.warning("Rate limited by HuggingFace API")
                
        except requests.Timeout:
            logger.error("Timeout in AI scan")
        except Exception as e:
            logger.error(f"Error in AI scan: {e}")
        
        return 0.0

    # ==========================================
    # Chat Management
    # ==========================================
    def restore_active_chats(self):
        """Restore active chats after restart with validation"""
        logger.info("Restoring active chats...")
        
        db_c = self.db.read("chats")
        valid_chats = []
        
        for uid, partner in list(db_c.items()):
            uid_str, partner_str = str(uid), str(partner)
            
            # Validate both users exist
            user_u = self.db.get_user(uid_str)
            user_p = self.db.get_user(partner_str)
            
            if not user_u or not user_p:
                continue
            
            # Verify mutual connection and idle state
            if (user_u.get("state") == "idle" and 
                user_p.get("state") == "idle" and
                not user_u.get("partner") and 
                not user_p.get("partner") and
                db_c.get(partner_str) == uid_str):
                
                valid_chats.append((uid_str, partner_str))
        
        # Update database atomically
        for uid, partner in valid_chats:
            success = self.db.update_user(uid, lambda u: {**u, "partner": partner, "state": "chatting"})
            success = success and self.db.update_user(partner, lambda u: {**u, "partner": uid, "state": "chatting"})
            
            if success:
                try:
                    self.bot.send_message(
                        uid, 
                        "🔄 <b>چت شما بازیابی شد!</b>\n\nربات ری‌استارت شده بود. می‌توانید ادامه دهید.",
                        reply_markup=self.kb_chatting()
                    )
                    self.bot.send_message(
                        partner,
                        "🔄 <b>چت شما بازیابی شد!</b>\n\nربات ری‌استارت شده بود. می‌توانید ادامه دهید.",
                        reply_markup=self.kb_chatting()
                    )
                except Exception as e:
                    logger.error(f"Error notifying restored chat {uid}-{partner}: {e}")
        
        logger.info(f"Restored {len(valid_chats)} active chats")

    def save_active_chat(self, uid: str, partner: str):
        """Save active chat to database"""
        def updater(data):
            if "chats" not in data:
                data["chats"] = {}
            data["chats"][str(uid)] = str(partner)
            return data
        self.db.atomic_update("chats", updater)

    def remove_active_chat(self, uid: str):
        """Remove active chat from database"""
        uid = str(uid)
        
        def updater(data):
            if "chats" not in data:
                return data
            
            if uid in data["chats"]:
                partner = data["chats"][uid]
                # Remove mutual connection
                if partner in data["chats"] and data["chats"][partner] == uid:
                    del data["chats"][partner]
                del data["chats"][uid]
            return data
        
        self.db.atomic_update("chats", updater)

    def end_chat(self, user_a: str, user_b: str, reason: str = "چت پایان یافت"):
        """Safely end a chat between two users"""
        user_a, user_b = str(user_a), str(user_b)
        
        # Update both users atomically
        self.db.update_user(user_a, lambda u: {**u, "partner": None, "state": "idle"})
        self.db.update_user(user_b, lambda u: {**u, "partner": None, "state": "idle"})
        
        # Remove from active chats
        self.remove_active_chat(user_a)
        
        # Notify users
        try:
            self.bot.send_message(user_a, f"🔚 {reason}", reply_markup=self.kb_main(user_a))
        except Exception as e:
            logger.error(f"Error ending chat for {user_a}: {e}")
        
        try:
            self.bot.send_message(user_b, f"🔚 هم‌صحبت شما {reason}", reply_markup=self.kb_main(user_b))
        except Exception as e:
            logger.error(f"Error ending chat for {user_b}: {e}")

    # ==========================================
    # VIP & Economy System
    # ==========================================
    def add_vip(self, uid: str, duration_key: str, reason: str = "گیفت") -> bool:
        """Add VIP to user with duration stacking"""
        uid = str(uid)
        
        if duration_key not in self.vip_durations:
            logger.error(f"Invalid VIP duration: {duration_key}")
            return False
        
        def updater(user_data):
            now = datetime.datetime.now().timestamp()
            current_end = user_data.get("vip_end", 0)
            
            if current_end < now:
                new_end = now + self.vip_durations[duration_key]
            else:
                new_end = current_end + self.vip_durations[duration_key]
            
            user_data["vip_end"] = new_end
            
            if duration_key == "christmas":
                user_data["christmas_vip_taken"] = True
            
            return user_data
        
        success = self.db.update_user(uid, updater)
        
        if success:
            try:
                user = self.db.get_user(uid)
                end_date = datetime.datetime.fromtimestamp(user["vip_end"]).strftime("%Y-%m-%d")
                remaining_days = int((user["vip_end"] - datetime.datetime.now().timestamp()) / (24 * 3600))
                
                duration_names = {
                    "week": "۱ هفته",
                    "month": "۱ ماه", 
                    "3month": "۳ ماه",
                    "6month": "۶ ماه",
                    "year": "۱ سال",
                    "christmas": "۳ ماه رایگان"
                }
                
                self.bot.send_message(
                    uid,
                    f"🎉 <b>تبریک! رنک VIP دریافت کردید</b>\n\n"
                    f"مدت: {duration_names.get(duration_key, duration_key)}\n"
                    f"تا تاریخ: {end_date}\n"
                    f"مدت باقی‌مانده: {remaining_days} روز\n"
                    f"دلیل: {reason}\n\nمبارک باشد ✨"
                )
            except Exception as e:
                logger.error(f"Error sending VIP notification to {uid}: {e}")
        
        return success

    def add_coins(self, uid: str, amount: int, reason: str = "") -> bool:
        """Add coins to user"""
        uid = str(uid)
        
        def updater(user_data):
            current = user_data.get("coins", 0)
            user_data["coins"] = current + amount
            return user_data
        
        success = self.db.update_user(uid, updater)
        
        if success:
            try:
                user = self.db.get_user(uid)
                self.bot.send_message(
                    uid,
                    f"💰 <b>دریافت سکه!</b>\n\n"
                    f"مقدار: {amount:,} سکه\n"
                    f"دلیل: {reason}\n"
                    f"موجودی: {user['coins']:,} سکه"
                )
            except Exception as e:
                logger.error(f"Error sending coin notification to {uid}: {e}")
        
        return success

    def deduct_coins(self, uid: str, amount: int) -> bool:
        """Deduct coins from user"""
        uid = str(uid)
        user = self.db.get_user(uid)
        
        if not user or user.get("coins", 0) < amount:
            return False
        
        def updater(user_data):
            user_data["coins"] = user_data.get("coins", 0) - amount
            return user_data
        
        return self.db.update_user(uid, updater)

    # ==========================================
    # Mission System
    # ==========================================
    def auto_update_daily_mission(self):
        """Update daily mission if needed"""
        db_m = self.db.read("missions")
        today = str(datetime.date.today())
        
        if db_m.get("daily", {}).get("date") != today:
            available = db_m.get("available", [])
            if available:
                # Select mission different from yesterday if possible
                yesterday_mission = db_m["daily"].get("mission")
                candidates = [m for m in available if m["name"] != yesterday_mission]
                if not candidates:
                    candidates = available
                
                mission = random.choice(candidates)
                
                new_daily = {
                    "date": today,
                    "mission": mission["name"],
                    "reward_type": mission.get("reward_type", "coins"),
                    "reward_value": mission.get("reward_value", mission.get("reward", 50)),
                    "type": mission["type"],
                    "target": mission["target"],
                    "description": mission.get("description", mission["name"])
                }
                
                def updater(data):
                    data["daily"] = new_daily
                    return data
                
                self.db.atomic_update("missions", updater)
                logger.info(f"Daily mission updated: {mission['name']}")

    def check_and_reward_mission(self, uid: str) -> bool:
        """Check mission completion and reward"""
        uid = str(uid)
        today = str(datetime.date.today())
        
        user = self.db.get_user(uid)
        if not user:
            return False
        
        # Already completed today
        if user.get("mission_completed_date") == today:
            return False
        
        db_m = self.db.read("missions")
        mission = db_m.get("daily", {})
        
        mission_type = mission.get("type")
        target = mission.get("target", 1)
        
        completed = False
        
        if mission_type == "chat_count":
            completed = user.get("daily_chat_count", 0) >= target
        elif mission_type == "unique_chats":
            completed = len(user.get("daily_unique_chats", [])) >= target
        elif mission_type == "referrals":
            completed = user.get("total_referrals", 0) >= target
        elif mission_type == "spin_wheel":
            completed = user.get("daily_spin_done", False)
        elif mission_type == "profile_views":
            completed = user.get("daily_profile_views", 0) >= target
        
        if completed:
            reward_type = mission.get("reward_type", "coins")
            reward_value = mission.get("reward_value", 50)
            
            if reward_type == "coins":
                self.add_coins(uid, reward_value, f"ماموریت روزانه: {mission['mission']}")
            elif reward_type == "vip":
                self.add_vip(uid, reward_value, f"ماموریت روزانه: {mission['mission']}")
            
            # Mark as completed
            self.db.update_user(uid, lambda u: {**u, "mission_completed_date": today})
            return True
        
        return False

    # ==========================================
    # Ban System
    # ==========================================
    def ban_permanent(self, uid: str, reason: str = "تخلف"):
        """Permanently ban a user"""
        uid = str(uid)
        
        def updater(data):
            if "permanent" not in data:
                data["permanent"] = {}
            data["permanent"][uid] = reason
            return data
        
        self.db.atomic_update("bans", updater)
        
        # End any active chat
        user = self.db.get_user(uid)
        if user and user.get("partner"):
            self.end_chat(uid, user["partner"], "به دلیل بن دائم از چت خارج شد")
        
        try:
            self.bot.send_message(
                uid,
                f"🚫 <b>شما بن دائم شدید!</b>\n"
                f"دلیل: {reason}\n"
                f"پشتیبانی: {self.support}"
            )
        except Exception as e:
            logger.error(f"Error notifying ban to {uid}: {e}")

    def ban_temporary(self, uid: str, minutes: int, reason: str = "تخلف"):
        """Temporarily ban a user"""
        uid = str(uid)
        end_time = datetime.datetime.now().timestamp() + minutes * 60
        
        def updater(data):
            if "temporary" not in data:
                data["temporary"] = {}
            data["temporary"][uid] = {
                "end": end_time,
                "reason": reason,
                "created": datetime.datetime.now().isoformat()
            }
            return data
        
        self.db.atomic_update("bans", updater)
        
        # End any active chat
        user = self.db.get_user(uid)
        if user and user.get("partner"):
            self.end_chat(uid, user["partner"], "به دلیل بن موقت از چت خارج شد")
        
        try:
            hours = minutes // 60
            mins = minutes % 60
            time_text = ""
            if hours > 0:
                time_text += f"{hours} ساعت"
            if mins > 0:
                if time_text:
                    time_text += " و "
                time_text += f"{mins} دقیقه"
            
            self.bot.send_message(
                uid,
                f"🚫 <b>بن موقت {time_text}</b>\n"
                f"دلیل: {reason}\n"
                f"پشتیبانی: {self.support}"
            )
        except Exception as e:
            logger.error(f"Error notifying temp ban to {uid}: {e}")

    def report_auto_ban(self, uid: str, reason: str, ban_type: str):
        """Report auto-ban to admin for review"""
        uid = str(uid)
        user = self.db.get_user(uid)
        name = user.get("name", "نامشخص") if user else "نامشخص"
        
        tehran_time = datetime.datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")
        
        report_text = (
            f"🤖 <b>بن خودکار توسط ربات</b>\n\n"
            f"کاربر: 🆔 <code>{uid}</code> - {name}\n"
            f"تاریخ (ایران): {tehran_time}\n"
            f"نوع بن: {ban_type}\n"
            f"دلیل: {reason}\n\n"
            f"آیا تصمیم ربات درست بود؟"
        )
        
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ درست بود", callback_data=f"auto_ban_correct_{uid}"),
            types.InlineKeyboardButton("❌ اشتباه بود (بخشیدن)", callback_data=f"auto_ban_pardon_{uid}")
        )
        
        try:
            self.bot.send_message(self.owner, report_text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Error reporting auto-ban: {e}")

    # ==========================================
    # Keyboard Markup Generators
    # ==========================================
    def kb_main(self, uid: str) -> types.ReplyKeyboardMarkup:
        """Main menu keyboard"""
        uid = str(uid)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس", "🎯 ماموریت روزانه")
        markup.add("👥 رفرال و دعوت", "🎖 خرید VIP")
        markup.add("❓ راهنما و قوانین", "⚙ تنظیمات")
        
        if self.is_owner(uid):
            markup.add("📊 پنل مدیریت")
        
        return markup

    def kb_chatting(self) -> types.ReplyKeyboardMarkup:
        """Chatting state keyboard"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🔚 پایان گفتگو", "🚩 گزارش تخلف")
        markup.add("🚫 بلاک و خروج", "👥 درخواست آیدی")
        return markup

    def kb_cancel(self) -> types.ReplyKeyboardMarkup:
        """Cancel operation keyboard"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❌ لغو عملیات")
        return markup

    def kb_admin(self) -> types.ReplyKeyboardMarkup:
        """Admin panel keyboard"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📈 آمار کلی ربات", "👥 مدیریت کاربران")
        markup.add("📅 مدیریت رویدادها", "🎫 مدیریت تخفیف‌ها")
        markup.add("💎 سیستم VIP", "💰 مدیریت مالی")
        markup.add("🔧 تنظیمات ربات", "📈 گزارش‌های پیشرفته")
        markup.add("📤 خروجی دیتابیس", "🚫 مدیریت بن‌ها")
        markup.add("🎖 گیفت VIP تکی", "🎖 گیفت VIP همگانی")
        markup.add("❌ حذف VIP", "📋 لیست VIP")
        markup.add("💰 اهدای سکه", "🎯 مدیریت ماموریت‌ها")
        markup.add("⚠️ هشدار تعمیر", "🛠 تعمیر و نگهداری")
        markup.add("🔙 بازگشت به منو")
        return markup

    def kb_report(self) -> types.InlineKeyboardMarkup:
        """Report reasons keyboard"""
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

    # ==========================================
    # Handler Registration
    # ==========================================
    def register_handlers(self):
        """Register all message and callback handlers"""
        
        # ========== Command Handlers ==========
        @self.bot.message_handler(commands=['start'])
        def handle_start(msg):
            self._handle_start(msg)
        
        @self.bot.message_handler(commands=['help'])
        def handle_help(msg):
            self._handle_help(msg)
        
        @self.bot.message_handler(commands=['stats'])
        def handle_stats(msg):
            self._handle_stats(msg)
        
        # ========== Main Message Handler ==========
        @self.bot.message_handler(func=lambda msg: True, content_types=[
            'text', 'photo', 'video', 'voice', 'sticker', 
            'animation', 'video_note', 'document', 'audio'
        ])
        def handle_message(msg):
            self._handle_message(msg)
        
        # ========== Callback Handlers ==========
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            self._handle_callback(call)

    # ==========================================
    # Handler Implementations
    # ==========================================
    def _handle_start(self, msg):
        """Handle /start command"""
        uid = str(msg.chat.id)
        
        # Validate user ID
        if not self.validator.validate_user_id(uid):
            logger.warning(f"Invalid user ID in start: {uid}")
            return
        
        # Parse payload
        payload = ""
        if len(msg.text.split()) > 1:
            payload = msg.text.split(maxsplit=1)[1]
        
        # Check ban status
        is_banned, ban_info = self.check_ban_status(uid)
        if is_banned:
            if ban_info["type"] == "permanent":
                self.bot.send_message(
                    uid,
                    f"🚫 <b>شما بن دائم هستید!</b>\n"
                    f"دلیل: {ban_info['reason']}\n"
                    f"پشتیبانی: {self.support}"
                )
            else:
                remaining = ban_info.get("remaining_minutes", 0)
                hours = remaining // 60
                mins = remaining % 60
                time_text = ""
                if hours > 0:
                    time_text += f"{hours} ساعت"
                if mins > 0:
                    if time_text:
                        time_text += " و "
                    time_text += f"{mins} دقیقه"
                
                self.bot.send_message(
                    uid,
                    f"🚫 <b>بن موقت هستید!</b>\n"
                    f"زمان باقی‌مانده: {time_text}\n"
                    f"پشتیبانی: {self.support}"
                )
            return
        
        # Check maintenance mode
        db_c = self.db.read("config")
        if (db_c.get("settings", {}).get("maintenance") and 
            not self.is_vip(uid) and 
            not self.is_owner(uid)):
            
            self.bot.send_message(
                uid,
                f"🔧 <b>ربات در حال تعمیر و نگهداری است</b>\n\n"
                f"فقط کاربران VIP دسترسی دارند 🌟\n"
                f"پشتیبانی: {self.support}"
            )
            return
        
        # Check channel membership
        if not self.check_channel_membership(uid):
            self.bot.send_message(
                uid,
                f"❌ برای استفاده از ربات باید در کانال عضو شوید:\n"
                f"{self.channel}"
            )
            return
        
        # Handle referral
        if payload.startswith("ref_"):
            self._process_referral(uid, payload[4:])
            return
        
        # Handle anonymous message link
        if payload.startswith("msg_"):
            self._setup_anonymous_message(uid, payload[4:])
            return
        
        # Normal registration or welcome back
        existing_user = self.db.get_user(uid)
        
        if not existing_user:
            # New user registration
            self.db.update_user(uid, lambda u: {
                **u,
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
                "joined_date": datetime.datetime.now().isoformat(),
                "last_active_date": str(datetime.date.today())
            })
            
            self.bot.send_message(
                uid,
                "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\n"
                "لطفاً نام مستعار خود را وارد کنید:"
            )
        else:
            # Welcome back
            self.db.update_user(uid, lambda u: {
                **u,
                "last_active_date": str(datetime.date.today())
            })
            self.bot.send_message(uid, "خوش برگشتید عزیز 🌹", reply_markup=self.kb_main(uid))

    def _process_referral(self, uid: str, referrer_id: str):
        """Process referral"""
        uid = str(uid)
        referrer_id = str(referrer_id)
        
        # Validate referrer
        if referrer_id == uid:
            self.bot.send_message(uid, "❌ نمی‌توانید خودتان را دعوت کنید!")
            return
        
        if not self.validator.validate_user_id(referrer_id):
            return
        
        # Check if already registered
        existing = self.db.get_user(uid)
        if existing:
            return
        
        # Process referral
        referrer = self.db.get_user(referrer_id)
        if referrer:
            self.db.update_user(referrer_id, lambda u: {
                **u,
                "total_referrals": u.get("total_referrals", 0) + 1,
                "referral_list": u.get("referral_list", []) + [uid]
            })
            
            self.add_coins(referrer_id, 100, "دعوت کاربر جدید")
            
            try:
                self.bot.send_message(
                    referrer_id,
                    "🎉 یک کاربر جدید از لینک شما عضو شد!\n"
                    "💰 +100 سکه پاداش دریافت کردید"
                )
            except Exception as e:
                logger.error(f"Error notifying referrer: {e}")

    def _setup_anonymous_message(self, uid: str, target: str):
        """Setup anonymous message sending"""
        uid = str(uid)
        target = str(target)
        
        if uid == target:
            self.bot.send_message(uid, "❌ نمی‌توانید به خودتان پیام بفرستید!")
            return
        
        if not self.validator.validate_user_id(target):
            self.bot.send_message(uid, "❌ لینک نامعتبر است")
            return
        
        existing = self.db.get_user(uid)
        
        if not existing:
            # New user needs to register first
            self.db.update_user(uid, lambda u: {
                **u,
                "state": "name",
                "anon_target": target
            })
            self.bot.send_message(uid, "✨ برای ارسال پیام ناشناس، ابتدا نام مستعار وارد کنید:")
        else:
            # Existing user
            self.db.update_user(uid, lambda u: {
                **u,
                "state": "anon_send",
                "anon_target": target
            })
            self.bot.send_message(uid, "📝 پیام ناشناس خود را بنویسید:")

    def _handle_help(self, msg):
        """Handle /help command"""
        uid = str(msg.chat.id)
        help_text = (
            "<b>📖 راهنما</b>\n\n"
            "<b>دستورات:</b>\n"
            "/start - شروع ربات\n"
            "/help - نمایش این راهنما\n"
            "/stats - آمار ربات (ادمین)\n\n"
            "<b>قوانین:</b>\n"
            "❌ فحاشی ممنوع\n"
            "❌ محتوای +18 ممنوع\n"
            "❌ اسپم و آزار ممنوع\n\n"
            f"پشتیبانی: {self.support}"
        )
        self.bot.send_message(uid, help_text)

    def _handle_stats(self, msg):
        """Handle /stats command (admin only)"""
        uid = str(msg.chat.id)
        
        if not self.is_owner(uid):
            return
        
        stats = self._get_bot_stats()
        stats_text = (
            f"<b>📊 آمار ربات</b>\n\n"
            f"👥 کل کاربران: {stats['total_users']:,}\n"
            f"📈 فعال امروز: {stats['active_users']:,}\n"
            f"🎖 VIP: {stats['vip_users']:,}\n"
            f"💰 کل سکه: {stats['total_coins']:,}\n"
            f"💬 چت‌های فعال: {stats['active_chats']:,}"
        )
        self.bot.send_message(uid, stats_text)

    def _get_bot_stats(self) -> dict:
        """Get bot statistics"""
        db_u = self.db.read("users")
        db_b = self.db.read("bans")
        db_c = self.db.read("chats")
        
        users = db_u.get("users", {})
        today = str(datetime.date.today())
        
        return {
            "total_users": len(users),
            "active_users": sum(1 for u in users.values() if u.get("last_active_date") == today),
            "vip_users": sum(1 for uid in users if self.is_vip(uid)),
            "total_coins": sum(u.get("coins", 0) for u in users.values()),
            "active_chats": len(db_c),
            "permanent_bans": len(db_b.get("permanent", {})),
            "temporary_bans": len(db_b.get("temporary", {}))
        }

    def _handle_message(self, msg):
        """Main message handler"""
        uid = str(msg.chat.id)
        
        # Security checks
        if not self.validator.validate_user_id(uid):
            return
        
        # Check ban
        is_banned, _ = self.check_ban_status(uid)
        if is_banned:
            return
        
        # Check maintenance
        db_c = self.db.read("config")
        if (db_c.get("settings", {}).get("maintenance") and 
            not self.is_vip(uid) and 
            not self.is_owner(uid)):
            return
        
        # Check channel membership
        if not self.check_channel_membership(uid):
            return
        
        # Get user data
        user = self.db.get_user(uid)
        if not user:
            return
        
        # Reset daily stats if needed
        self._check_daily_reset(uid, user)
        
        # Get message text
        text = msg.text if msg.content_type == "text" else ""
        text = self.validator.sanitize_text(text)
        
        # State machine
        state = user.get("state", "idle")
        
        # Handle states
        if state == "name":
            self._handle_state_name(uid, msg, text)
        elif state == "age":
            self._handle_state_age(uid, msg, text)
        elif state == "anon_send":
            self._handle_state_anon_send(uid, msg, text)
        elif state == "anon_reply":
            self._handle_state_anon_reply(uid, msg, text)
        elif state == "change_name":
            self._handle_state_change_name(uid, msg, text)
        elif state == "change_age":
            self._handle_state_change_age(uid, msg, text)
        elif state == "chatting":
            self._handle_state_chatting(uid, msg, text)
        elif state == "idle":
            self._handle_idle_state(uid, msg, text)
        
        # Handle admin states
        if self.is_owner(uid):
            self._handle_admin_states(uid, msg, text, user.get("admin_state"))

    def _check_daily_reset(self, uid: str, user: dict):
        """Reset daily stats if it's a new day"""
        today = str(datetime.date.today())
        if user.get("last_active_date") != today:
            self.db.update_user(uid, lambda u: {
                **u,
                "daily_chat_count": 0,
                "daily_unique_chats": [],
                "daily_spin_done": False,
                "daily_profile_views": 0,
                "last_active_date": today
            })

    def _handle_state_name(self, uid: str, msg, text: str):
        """Handle name registration state"""
        if msg.content_type != "text":
            self.bot.send_message(uid, "❌ لطفاً فقط متن وارد کنید")
            return
        
        if not text:
            self.bot.send_message(uid, "❌ نام نمی‌تواند خالی باشد")
            return
        
        if self.contains_bad_words(text):
            self.bot.send_message(uid, "❌ نام شامل کلمات نامناسب است")
            return
        
        if len(text) > 20:
            text = text[:20]
        
        self.db.update_user(uid, lambda u: {
            **u,
            "name": text,
            "state": "sex"
        })
        
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("آقا 👦", callback_data="sex_m"),
            types.InlineKeyboardButton("خانم 👧", callback_data="sex_f")
        )
        
        self.bot.send_message(
            uid,
            f"سلام {text} 🌸\n\nجنسیت خود را انتخاب کنید:",
            reply_markup=kb
        )

    def _handle_state_age(self, uid: str, msg, text: str):
        """Handle age registration state"""
        if msg.content_type != "text":
            self.bot.send_message(uid, "❌ لطفاً فقط عدد وارد کنید")
            return
        
        age = self.validator.validate_age(text)
        if age is None:
            self.bot.send_message(uid, "❌ سن باید بین ۱۲ تا ۹۹ باشد")
            return
        
        self.db.update_user(uid, lambda u: {
            **u,
            "age": age,
            "state": "idle"
        })
        
        self.add_coins(uid, 50, "پاداش ثبت‌نام")
        
        self.bot.send_message(
            uid,
            "✅ <b>ثبت‌نام با موفقیت انجام شد!</b>\n\n"
            "🎁 پاداش ثبت‌نام: 50 سکه\n\n"
            "حالا از ربات لذت ببرید!",
            reply_markup=self.kb_main(uid)
        )

    def _handle_state_anon_send(self, uid: str, msg, text: str):
        """Handle anonymous message sending"""
        if msg.content_type != "text":
            self.bot.send_message(uid, "❌ فقط متن مجاز است")
            return
        
        user = self.db.get_user(uid)
        target = user.get("anon_target")
        
        if not target or not self.validator.validate_user_id(target):
            self.bot.send_message(uid, "❌ خطا در ارسال پیام")
            self.db.update_user(uid, lambda u: {**u, "state": "idle", "anon_target": None})
            return
        
        # Save message
        def updater(data):
            if "inbox" not in data:
                data["inbox"] = {}
            if target not in data["inbox"]:
                data["inbox"][target] = []
            
            data["inbox"][target].append({
                "text": text,
                "from": uid,
                "seen": False,
                "time": datetime.datetime.now().strftime("%H:%M %d/%m/%Y")
            })
            return data
        
        self.db.atomic_update("messages", updater)
        
        self.bot.send_message(uid, "✅ پیام ناشناس با موفقیت ارسال شد")
        
        try:
            self.bot.send_message(target, "📩 یک پیام ناشناس جدید دریافت کردید!")
        except Exception as e:
            logger.error(f"Error notifying target {target}: {e}")
        
        self.db.update_user(uid, lambda u: {
            **u,
            "state": "idle",
            "anon_target": None
        })

    def _handle_state_anon_reply(self, uid: str, msg, text: str):
        """Handle anonymous reply"""
        if msg.content_type != "text":
            self.bot.send_message(uid, "❌ فقط متن مجاز است")
            return
        
        user = self.db.get_user(uid)
        target = user.get("anon_reply_target")
        
        if target and self.validator.validate_user_id(target):
            try:
                self.bot.send_message(target, f"📩 <b>پاسخ ناشناس:</b>\n\n{text}")
                self.bot.send_message(uid, "✅ پاسخ ارسال شد")
            except Exception as e:
                logger.error(f"Error sending reply: {e}")
                self.bot.send_message(uid, "❌ خطا در ارسال پاسخ")
        
        self.db.update_user(uid, lambda u: {
            **u,
            "state": "idle",
            "anon_reply_target": None
        })

    def _handle_state_change_name(self, uid: str, msg, text: str):
        """Handle name change"""
        if msg.content_type != "text":
            self.bot.send_message(uid, "❌ فقط متن مجاز است")
            return
        
        if self.contains_bad_words(text):
            self.bot.send_message(uid, "❌ نام شامل کلمات نامناسب است")
            return
        
        self.db.update_user(uid, lambda u: {
            **u,
            "name": text[:20],
            "state": "idle"
        })
        
        self.bot.send_message(uid, "✅ نام با موفقیت تغییر کرد", reply_markup=self.kb_main(uid))

    def _handle_state_change_age(self, uid: str, msg, text: str):
        """Handle age change"""
        if msg.content_type != "text":
            self.bot.send_message(uid, "❌ فقط عدد وارد کنید")
            return
        
        age = self.validator.validate_age(text)
        if age is None:
            self.bot.send_message(uid, "❌ سن باید بین ۱۲ تا ۹۹ باشد")
            return
        
        self.db.update_user(uid, lambda u: {
            **u,
            "age": age,
            "state": "idle"
        })
        
        self.bot.send_message(uid, "✅ سن با موفقیت تغییر کرد", reply_markup=self.kb_main(uid))

    def _handle_state_chatting(self, uid: str, msg, text: str):
        """Handle chatting state"""
        user = self.db.get_user(uid)
        partner = user.get("partner")
        
        if not partner:
            # Should not happen, but handle gracefully
            self.db.update_user(uid, lambda u: {**u, "state": "idle"})
            self.bot.send_message(uid, "خطا در چت. لطفاً دوباره تلاش کنید.", reply_markup=self.kb_main(uid))
            return
        
        # Handle chat commands
        if text == "🔚 پایان گفتگو":
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("✅ بله، پایان بده", callback_data="end_yes"),
                types.InlineKeyboardButton("❌ خیر، ادامه بده", callback_data="end_no")
            )
            self.bot.send_message(uid, "❓ آیا مطمئن هستید؟", reply_markup=kb)
            return
        
        if text == "🚩 گزارش تخلف":
            self.db.update_user(uid, lambda u: {
                **u,
                "report_target": partner,
                "report_last_msg_id": msg.message_id
            })
            self.bot.send_message(uid, "⚠️ دلیل گزارش را انتخاب کنید:", reply_markup=self.kb_report())
            return
        
        if text == "🚫 بلاک و خروج":
            blocks = user.get("blocks", [])
            if partner not in blocks:
                blocks.append(partner)
            
            self.db.update_user(uid, lambda u: {**u, "blocks": blocks})
            self.end_chat(uid, partner, "شما را بلاک کرد")
            return
        
        if text == "👥 درخواست آیدی":
            kb = types.InlineKeyboardMarkup()
            kb.add(
                types.InlineKeyboardButton("✅ بله", callback_data=f"id_share_yes_{uid}"),
                types.InlineKeyboardButton("❌ خیر", callback_data="id_share_no")
            )
            try:
                self.bot.send_message(partner, "📢 هم‌صحبت شما درخواست آیدی دارد. موافقید؟", reply_markup=kb)
                self.bot.send_message(uid, "⏳ درخواست ارسال شد، منتظر تایید باشید")
            except Exception as e:
                logger.error(f"Error requesting ID: {e}")
            return
        
        # Content filtering
        if msg.content_type == "text" and text:
            is_bad = self.contains_bad_words(text)
            toxic_score = self.ai_content_scan(text, "toxic")
            nsfw_score = self.ai_content_scan(text, "nsfw")
            
            if is_bad or toxic_score > 0.8 or nsfw_score > 0.8:
                # Delete message
                try:
                    self.bot.delete_message(uid, msg.message_id)
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
                
                # Add warning
                current_warns = user.get("warns", 0) + 1
                
                if current_warns >= 3:
                    if user.get("had_temp_ban", False):
                        self.ban_permanent(uid, "فحاشی مکرر پس از بن موقت")
                        self.report_auto_ban(uid, "فحاشی مکرر پس از بن موقت", "بن دائم")
                    else:
                        self.ban_temporary(uid, 1440, "فحاشی مکرر (بن ۲۴ ساعته)")
                        self.db.update_user(uid, lambda u: {
                            **u,
                            "had_temp_ban": True,
                            "warns": 0
                        })
                        self.report_auto_ban(uid, "فحاشی مکرر (اولین بار)", "بن ۲۴ ساعته")
                else:
                    self.db.update_user(uid, lambda u: {**u, "warns": current_warns})
                    self.bot.send_message(
                        uid,
                        f"⚠️ <b>اخطار {current_warns}/3</b>\n\nمحتوای نامناسب ممنوع است!"
                    )
                return
        
        # Update stats
        self.db.update_user(uid, lambda u: {
            **u,
            "daily_chat_count": u.get("daily_chat_count", 0) + 1,
            "daily_unique_chats": list(set(u.get("daily_unique_chats", []) + [partner]))
        })
        
        # Check mission
        self.check_and_reward_mission(uid)
        
        # Forward message
        try:
            self.bot.copy_message(partner, uid, msg.message_id)
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            self.bot.send_message(uid, "❌ خطا در ارسال پیام. ممکن است هم‌صحبت بلاک کرده باشد.")
            self.end_chat(uid, partner, "خطا در ارتباط")

    def _handle_idle_state(self, uid: str, msg, text: str):
        """Handle idle state (main menu)"""
        if not text:
            return
        
        # Main menu handlers
        handlers = {
            "🛰 شروع چت ناشناس": self._handle_start_chat,
            "👤 پروفایل من": self._handle_profile,
            "📩 لینک ناشناس من": self._handle_anon_link,
            "📥 پیام‌های ناشناس": self._handle_inbox,
            "🎡 گردونه شانس": self._handle_spin_wheel,
            "🎯 ماموریت روزانه": self._handle_mission,
            "👥 رفرال و دعوت": self._handle_referral,
            "🎖 خرید VIP": self._handle_buy_vip,
            "❓ راهنما و قوانین": self._handle_help_rules,
            "⚙ تنظیمات": self._handle_settings,
            "📊 پنل مدیریت": self._handle_admin_panel,
            "❌ لغو عملیات": self._handle_cancel,
            "🔙 بازگشت به منو": self._handle_back_to_menu
        }
        
        handler = handlers.get(text)
        if handler:
            handler(uid, msg)
        elif text.startswith("🔙"):
            self._handle_back_to_menu(uid, msg)

    def _handle_start_chat(self, uid: str, msg):
        """Start chat search"""
        kb = types.InlineKeyboardMarkup(row_width=3)
        kb.add(
            types.InlineKeyboardButton("آقا 👦", callback_data="find_m"),
            types.InlineKeyboardButton("خانم 👧", callback_data="find_f"),
            types.InlineKeyboardButton("هرکی 🌈", callback_data="find_any")
        )
        self.bot.send_message(uid, "🔍 دنبال چه کسی می‌گردید؟", reply_markup=kb)

    def _handle_profile(self, uid: str, msg):
        """Show user profile"""
        user = self.db.get_user(uid)
        if not user:
            return
        
        # Increment profile view for mission
        self.db.update_user(uid, lambda u: {
            **u,
            "daily_profile_views": u.get("daily_profile_views", 0) + 1
        })
        
        is_vip = self.is_vip(uid)
        rank = "🎖 VIP" if is_vip else "⭐ عادی"
        
        vip_end = user.get("vip_end", 0)
        if vip_end > 0:
            end_date = datetime.datetime.fromtimestamp(vip_end).strftime("%Y-%m-%d")
            remaining_days = int((vip_end - datetime.datetime.now().timestamp()) / (24 * 3600))
            vip_status = f"تا {end_date} ({remaining_days} روز)"
        else:
            vip_status = "ندارید"
        
        profile_text = (
            f"<b>👤 پروفایل شما</b>\n\n"
            f"نام: {user.get('name', 'نامشخص')}\n"
            f"جنسیت: {user.get('sex', 'نامشخص')}\n"
            f"سن: {user.get('age', 'نامشخص')}\n"
            f"رنک: {rank}\n"
            f"VIP: {vip_status}\n"
            f"💰 سکه: {user.get('coins', 0):,}\n"
            f"👥 رفرال: {user.get('total_referrals', 0)} نفر\n"
            f"⚠️ اخطار: {user.get('warns', 0)}/3\n"
        )
        
        if user.get("christmas_vip_taken", False):
            profile_text += "🎄 VIP کریسمس: <b>دریافت شده ✅</b>"
        
        self.bot.send_message(uid, profile_text)
        self.check_and_reward_mission(uid)

    def _handle_anon_link(self, uid: str, msg):
        """Generate anonymous message link"""
        link = f"https://t.me/{self.username}?start=msg_{uid}"
        self.bot.send_message(
            uid,
            f"<b>📩 لینک ناشناس شما</b>\n\n"
            f"<code>{link}</code>\n\n"
            f"با اشتراک این لینک، دیگران می‌توانند ناشناس به شما پیام بفرستند ✨"
        )

    def _handle_inbox(self, uid: str, msg):
        """Show anonymous messages inbox"""
        db_m = self.db.read("messages")
        inbox = db_m.get("inbox", {}).get(uid, [])
        
        if not inbox:
            self.bot.send_message(uid, "📭 هیچ پیام ناشناسی دریافت نکرده‌اید")
            return
        
        kb = types.InlineKeyboardMarkup()
        txt = "<b>📥 پیام‌های ناشناس شما</b>\n\n"
        
        for i, m in enumerate(inbox):
            status = "✅" if m.get("seen") else "🔵"
            txt += f"{status} <b>پیام {i+1}:</b>\n{m['text']}\n"
            txt += f"<i>🕐 {m['time']}</i>\n\n"
            kb.add(types.InlineKeyboardButton(
                f"📝 پاسخ به پیام {i+1}", 
                callback_data=f"anon_reply_{i}"
            ))
        
        self.bot.send_message(uid, txt, reply_markup=kb)
        
        # Mark as seen
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
            self.db.atomic_update("messages", lambda d: d)

    def _handle_spin_wheel(self, uid: str, msg):
        """Handle spin wheel"""
        user = self.db.get_user(uid)
        today = str(datetime.date.today())
        
        if user.get("last_spin") == today:
            self.bot.send_message(
                uid,
                "⏰ امروز قبلاً گردونه را چرخانده‌اید\n\nفردا دوباره امتحان کنید! 🎡"
            )
            return
        
        self.db.update_user(uid, lambda u: {
            **u,
            "last_spin": today,
            "daily_spin_done": True
        })
        
        rand = random.random()
        
        if rand < 0.001:  # 0.1% chance
            self.add_vip(uid, "month", "گردونه شانس")
            result = "🎉 <b>جایزه بزرگ!</b>\n\n🎖 VIP ۳۰ روزه\n\nتبریک! 🎊"
        elif rand < 0.05:  # 5% chance
            coins = random.choice([500, 750, 1000])
            self.add_coins(uid, coins, "گردونه شانس")
            result = f"🎁 <b>برنده شدید!</b>\n\n💰 {coins:,} سکه\n\nآفرین! ✨"
        elif rand < 0.3:  # 25% chance
            coins = random.choice([50, 100, 150, 200])
            self.add_coins(uid, coins, "گردونه شانس")
            result = f"🎯 <b>موفق!</b>\n\n💰 {coins:,} سکه\n\nخوب بود! 👍"
        else:
            result = "😔 <b>متأسفانه پوچ!</b>\n\nشانس بعدی را امتحان کنید 🍀"
        
        self.bot.send_message(uid, f"🎡 گردونه در حال چرخش...\n\n{result}")
        self.check_and_reward_mission(uid)

    def _handle_mission(self, uid: str, msg):
        """Show daily mission"""
        db_m = self.db.read("missions")
        mission = db_m.get("daily", {})
        user = self.db.get_user(uid)
        
        today = str(datetime.date.today())
        completed = user.get("mission_completed_date") == today
        
        mission_text = f"<b>🎯 ماموریت روزانه</b>\n\n"
        mission_text += f"📋 ماموریت: {mission.get('mission', 'نامشخص')}\n"
        mission_text += f"📝 کار: {mission.get('description', mission.get('mission', ''))}\n"
        
        reward_type = mission.get("reward_type", "coins")
        reward_value = mission.get("reward_value", 50)
        
        if reward_type == "coins":
            mission_text += f"🎁 پاداش: {reward_value:,} سکه\n\n"
        else:
            duration_names = {
                "week": "۱ هفته",
                "month": "۱ ماه",
                "3month": "۳ ماه",
                "6month": "۶ ماه",
                "year": "۱ سال"
            }
            mission_text += f"🎁 پاداش: VIP {duration_names.get(reward_value, reward_value)}\n\n"
        
        if completed:
            mission_text += "✅ <b>تکمیل شده!</b>\n\nفردا ماموریت جدید منتظر شماست 🌟"
        else:
            mission_type = mission.get("type")
            target = mission.get("target", 1)
            
            progress_map = {
                "chat_count": user.get("daily_chat_count", 0),
                "unique_chats": len(user.get("daily_unique_chats", [])),
                "referrals": user.get("total_referrals", 0),
                "spin_wheel": 1 if user.get("daily_spin_done") else 0,
                "profile_views": user.get("daily_profile_views", 0)
            }
            
            current = progress_map.get(mission_type, 0)
            
            if mission_type == "spin_wheel":
                mission_text += f"پیشرفت: {'✅' if current else '❌'}\n"
            else:
                mission_text += f"پیشرفت: {current}/{target}\n"
            
            progress_pct = min(100, int((current / target) * 100)) if target > 0 else 0
            mission_text += f"\n📊 {progress_pct}% تکمیل شده"
        
        self.bot.send_message(uid, mission_text)

    def _handle_referral(self, uid: str, msg):
        """Show referral info"""
        user = self.db.get_user(uid)
        ref_link = f"https://t.me/{self.username}?start=ref_{uid}"
        ref_count = user.get("total_referrals", 0)
        
        ref_text = (
            f"<b>👥 سیستم رفرال</b>\n\n"
            f"🎁 به ازای هر دعوت موفق: <b>100 سکه</b>\n"
            f"👤 تعداد دعوت‌های شما: <b>{ref_count} نفر</b>\n"
            f"💰 کل سکه از رفرال: <b>{ref_count * 100:,} سکه</b>\n\n"
            f"🔗 لینک دعوت شما:\n<code>{ref_link}</code>\n\n"
            f"این لینک را با دوستان خود به اشتراک بگذارید!"
        )
        
        self.bot.send_message(uid, ref_text)

    def _handle_buy_vip(self, uid: str, msg):
        """Show VIP shop"""
        user = self.db.get_user(uid)
        coins = user.get("coins", 0)
        
        vip_text = (
            f"<b>🎖 فروشگاه VIP</b>\n\n"
            f"<b>ویژگی‌های VIP:</b>\n"
            f"✅ ارسال آزاد گیف و استیکر\n"
            f"✅ اولویت در بررسی گزارش‌ها\n"
            f"✅ دسترسی در زمان تعمیر\n"
            f"✅ نشان ویژه VIP\n\n"
            f"💰 موجودی شما: <b>{coins:,} سکه</b>\n\n"
        )
        
        christmas_deadline = datetime.datetime(2026, 1, 15)
        today = datetime.datetime.now()
        is_christmas_active = today < christmas_deadline
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        
        vip_options = [
            ("week", "۱ هفته", 500),
            ("month", "۱ ماه", 1800),
            ("3month", "۳ ماه", 5000),
            ("6month", "۶ ماه", 9000),
            ("year", "۱ سال", 15000)
        ]
        
        for key, name, price in vip_options:
            status = "✅" if coins >= price else "🔒"
            kb.add(types.InlineKeyboardButton(
                f"{status} VIP {name} - {price:,} سکه",
                callback_data=f"buy_vip_{key}"
            ))
        
        if is_christmas_active and not user.get("christmas_vip_taken", False):
            vip_text += (
                "🎄 <b>پیشنهاد ویژه کریسمس!</b>\n"
                "VIP ۳ ماهه رایگان فقط تا ۱۵ ژانویه ۲۰۲۶\n"
                "<i>(هر کاربر فقط یکبار می‌تواند دریافت کند)</i>\n\n"
            )
            kb.add(types.InlineKeyboardButton(
                "🎁 VIP ۳ ماه رایگان (ویژه کریسمس) - ۰ سکه",
                callback_data="buy_vip_christmas"
            ))
        
        self.bot.send_message(uid, vip_text, reply_markup=kb)

    def _handle_help_rules(self, uid: str, msg):
        """Show help and rules"""
        help_text = (
            f"<b>📖 راهنما و قوانین</b>\n\n"
            f"<b>چگونه کار می‌کند؟</b>\n"
            f"• چت کاملاً ناشناس است\n"
            f"• با افراد تصادفی گفتگو کنید\n"
            f"• سکه جمع کنید و VIP بخرید\n\n"
            f"<b>قوانین:</b>\n"
            f"❌ فحاشی ممنوع\n"
            f"❌ محتوای +18 ممنوع\n"
            f"❌ اسپم و آزار ممنوع\n\n"
            f"<b>سیستم اخطار:</b>\n"
            f"• اخطار ۳: بن ۲۴ ساعته\n"
            f"• تکرار پس از بن: بن دائم\n\n"
            f"پشتیبانی: {self.support}"
        )
        self.bot.send_message(uid, help_text)

    def _handle_settings(self, uid: str, msg):
        """Show settings menu"""
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("✏️ تغییر نام", "🔢 تغییر سن")
        kb.add("⚧ تغییر جنسیت", "🔙 بازگشت به منو")
        self.bot.send_message(uid, "⚙️ تنظیمات پروفایل:", reply_markup=kb)

    def _handle_admin_panel(self, uid: str, msg):
        """Show admin panel"""
        if not self.is_owner(uid):
            return
        
        self.bot.send_message(
            uid,
            "<b>🛠️ پنل مدیریت پیشرفته</b>",
            reply_markup=self.kb_admin()
        )

    def _handle_cancel(self, uid: str, msg):
        """Cancel current operation"""
        self.db.update_user(uid, lambda u: {
            **u,
            "state": "idle",
            "admin_state": None
        })
        self.bot.send_message(uid, "✅ عملیات لغو شد", reply_markup=self.kb_main(uid))

    def _handle_back_to_menu(self, uid: str, msg):
        """Return to main menu"""
        self.db.update_user(uid, lambda u: {
            **u,
            "state": "idle",
            "admin_state": None
        })
        self.bot.send_message(uid, "🏠 منوی اصلی", reply_markup=self.kb_main(uid))

    def _handle_admin_states(self, uid: str, msg, text: str, admin_state: str):
        """Handle admin-specific states"""
        if not admin_state:
            # Check admin menu buttons
            admin_handlers = {
                "📈 آمار کلی ربات": self._admin_stats,
                "👥 مدیریت کاربران": self._admin_users_menu,
                "🎖 گیفت VIP تکی": lambda u, m: self._set_admin_state(u, "gift_vip_duration"),
                "🎖 گیفت VIP همگانی": lambda u, m: self._set_admin_state(u, "gift_vip_all_duration"),
                "❌ حذف VIP": lambda u, m: self._set_admin_state(u, "remove_vip"),
                "📋 لیست VIP": self._admin_vip_list,
                "💰 اهدای سکه": lambda u, m: self._set_admin_state(u, "gift_coins_amount"),
                "🚫 مدیریت بن‌ها": self._admin_bans,
                "🔙 بازگشت به منو": self._handle_back_to_menu
            }
            
            handler = admin_handlers.get(text)
            if handler:
                handler(uid, msg)
            return
        
        # Handle specific admin states
        state_handlers = {
            "gift_vip_duration": self._admin_gift_vip_duration,
            "gift_vip_reason": self._admin_gift_vip_reason,
            "gift_vip_id": self._admin_gift_vip_id,
            "gift_vip_all_duration": self._admin_gift_vip_all_duration,
            "gift_vip_all_reason": self._admin_gift_vip_all_reason,
            "remove_vip": self._admin_remove_vip,
            "gift_coins_amount": self._admin_gift_coins_amount,
            "gift_coins_reason": self._admin_gift_coins_reason,
            "gift_coins_id": self._admin_gift_coins_id
        }
        
        handler = state_handlers.get(admin_state)
        if handler:
            handler(uid, msg, text)

    def _set_admin_state(self, uid: str, state: str):
        """Set admin state and show appropriate UI"""
        self.db.update_user(uid, lambda u: {**u, "admin_state": state})
        
        if state == "gift_vip_duration":
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            kb.add("۱ هفته", "۱ ماه", "۳ ماه")
            kb.add("۶ ماه", "۱ سال", "🔙 بازگشت")
            self.bot.send_message(uid, "⏰ مدت VIP را انتخاب کنید:", reply_markup=kb)
        
        elif state == "gift_vip_all_duration":
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            kb.add("۱ هفته", "۱ ماه", "۳ ماه")
            kb.add("۶ ماه", "۱ سال", "🔙 بازگشت")
            self.bot.send_message(uid, "⏰ مدت VIP همگانی را انتخاب کنید:", reply_markup=kb)
        
        elif state == "remove_vip":
            self.bot.send_message(uid, "🆔 آیدی عددی کاربر برای حذف VIP:", reply_markup=self.kb_cancel())
        
        elif state == "gift_coins_amount":
            self.bot.send_message(uid, "💰 مقدار سکه را وارد کنید:", reply_markup=self.kb_cancel())

    def _admin_stats(self, uid: str, msg):
        """Show admin statistics"""
        stats = self._get_bot_stats()
        stats_text = (
            f"<b>📊 آمار کلی ربات</b>\n\n"
            f"👥 کل کاربران: {stats['total_users']:,}\n"
            f"📈 کاربران فعال امروز: {stats['active_users']:,}\n"
            f"🎖 کاربران VIP: {stats['vip_users']:,}\n"
            f"💰 کل سکه‌ها: {stats['total_coins']:,}\n"
            f"💬 چت‌های فعال: {stats['active_chats']:,}\n"
            f"🚫 بن دائم: {stats['permanent_bans']:,}\n"
            f"⏰ بن موقت: {stats['temporary_bans']:,}"
        )
        self.bot.send_message(uid, stats_text)

    def _admin_users_menu(self, uid: str, msg):
        """Show users management menu"""
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        kb.add("🔍 جستجوی کاربر", "📋 لیست کاربران")
        kb.add("📊 آمار کاربران", "🔙 بازگشت به پنل")
        self.bot.send_message(uid, "👥 <b>مدیریت کاربران</b>", reply_markup=kb)

    def _admin_vip_list(self, uid: str, msg):
        """Show VIP users list"""
        db_u = self.db.read("users")
        vip_users = [u for u in db_u.get("users", {}) if self.is_vip(u)]
        
        if not vip_users:
            self.bot.send_message(uid, "❌ هیچ کاربر VIP فعال وجود ندارد")
            return
        
        vip_text = "<b>📋 لیست کاربران VIP فعال</b>\n\n"
        
        for v in vip_users[:50]:
            user_data = db_u["users"][v]
            name = user_data.get("name", "نامشخص")
            end_date = datetime.datetime.fromtimestamp(
                user_data.get("vip_end", 0)
            ).strftime("%Y-%m-%d")
            
            remaining_days = int(
                (user_data.get("vip_end", 0) - datetime.datetime.now().timestamp()) / (24 * 3600)
            )
            
            vip_text += f"🆔 <code>{v}</code> - {name}\n📅 تا {end_date} ({remaining_days} روز)\n\n"
        
        if len(vip_users) > 50:
            vip_text += f"\n... و {len(vip_users) - 50} نفر دیگر"
        
        self.bot.send_message(uid, vip_text)

    def _admin_bans(self, uid: str, msg):
        """Show bans management"""
        db_b = self.db.read("bans")
        
        ban_text = "<b>🚫 لیست بن‌شده‌ها</b>\n\n"
        kb = types.InlineKeyboardMarkup()
        
        # Permanent bans
        perm_bans = list(db_b.get("permanent", {}).items())[:20]
        if perm_bans:
            ban_text += "<b>بن دائم:</b>\n"
            for ban_uid, reason in perm_bans:
                ban_text += f"🆔 <code>{ban_uid}</code> - {reason}\n"
                kb.add(types.InlineKeyboardButton(
                    f"🔓 بخشیدن {ban_uid}",
                    callback_data=f"unban_perm_{ban_uid}"
                ))
        
        # Temporary bans
        temp_bans = list(db_b.get("temporary", {}).items())[:20]
        if temp_bans:
            ban_text += "\n<b>بن موقت:</b>\n"
            for ban_uid, data in temp_bans:
                end_time = datetime.datetime.fromtimestamp(data["end"]).strftime("%Y-%m-%d %H:%M")
                ban_text += f"🆔 <code>{ban_uid}</code> - تا {end_time}\n"
        
        if not perm_bans and not temp_bans:
            ban_text += "✅ هیچ کاربر بن‌شده‌ای وجود ندارد"
        
        self.bot.send_message(uid, ban_text, reply_markup=kb if perm_bans else None)

    def _admin_gift_vip_duration(self, uid: str, msg, text: str):
        """Handle VIP gift duration selection"""
        duration_map = {
            "۱ هفته": "week",
            "۱ ماه": "month",
            "۳ ماه": "3month",
            "۶ ماه": "6month",
            "۱ سال": "year"
        }
        
        if text not in duration_map:
            self.bot.send_message(uid, "❌ لطفاً از گزینه‌ها انتخاب کنید")
            return
        
        self.db.update_user(uid, lambda u: {
            **u,
            "gift_vip_duration": duration_map[text],
            "admin_state": "gift_vip_reason"
        })
        self.bot.send_message(uid, "📝 دلیل گیفت VIP را بنویسید:")

    def _admin_gift_vip_reason(self, uid: str, msg, text: str):
        """Handle VIP gift reason"""
        self.db.update_user(uid, lambda u: {
            **u,
            "gift_vip_reason": text,
            "admin_state": "gift_vip_id"
        })
        self.bot.send_message(uid, "🆔 آیدی عددی کاربر را وارد کنید:")

    def _admin_gift_vip_id(self, uid: str, msg, text: str):
        """Handle VIP gift target ID"""
        if not text.isdigit():
            self.bot.send_message(uid, "❌ آیدی باید عدد باشد")
            return
        
        admin_data = self.db.get_user(uid)
        duration = admin_data.get("gift_vip_duration")
        reason = admin_data.get("gift_vip_reason", "گیفت ادمین")
        
        if self.db.get_user(text):
            success = self.add_vip(text, duration, reason)
            if success:
                self.bot.send_message(uid, f"✅ گیفت VIP به {text} ارسال شد", reply_markup=self.kb_admin())
            else:
                self.bot.send_message(uid, "❌ خطا در ارسال گیفت")
        else:
            self.bot.send_message(uid, "❌ کاربر پیدا نشد")
        
        self.db.update_user(uid, lambda u: {**u, "admin_state": None})

    def _admin_gift_vip_all_duration(self, uid: str, msg, text: str):
        """Handle mass VIP gift duration"""
        duration_map = {
            "۱ هفته": "week",
            "۱ ماه": "month",
            "۳ ماه": "3month",
            "۶ ماه": "6month",
            "۱ سال": "year"
        }
        
        if text not in duration_map:
            self.bot.send_message(uid, "❌ لطفاً از گزینه‌ها انتخاب کنید")
            return
        
        self.db.update_user(uid, lambda u: {
            **u,
            "gift_vip_all_duration": duration_map[text],
            "admin_state": "gift_vip_all_reason"
        })
        self.bot.send_message(uid, "📝 دلیل گیفت همگانی را بنویسید:")

    def _admin_gift_vip_all_reason(self, uid: str, msg, text: str):
        """Handle mass VIP gift execution"""
        admin_data = self.db.get_user(uid)
        duration = admin_data.get("gift_vip_all_duration")
        
        db_u = self.db.read("users")
        sent_count = 0
        
        for target_uid in db_u.get("users", {}):
            if self.add_vip(target_uid, duration, text):
                sent_count += 1
        
        self.bot.send_message(
            uid,
            f"✅ گیفت VIP به {sent_count} کاربر ارسال شد",
            reply_markup=self.kb_admin()
        )
        
        self.db.update_user(uid, lambda u: {**u, "admin_state": None})

    def _admin_remove_vip(self, uid: str, msg, text: str):
        """Handle VIP removal"""
        if not text.isdigit():
            self.bot.send_message(uid, "❌ آیدی باید عدد باشد")
            return
        
        if self.db.get_user(text):
            self.db.update_user(text, lambda u: {
                **u,
                "vip_end": 0,
                "christmas_vip_taken": False
            })
            
            try:
                self.bot.send_message(text, "❌ VIP شما توسط ادمین حذف شد")
            except:
                pass
            
            self.bot.send_message(uid, f"✅ VIP از کاربر {text} حذف شد", reply_markup=self.kb_admin())
        else:
            self.bot.send_message(uid, "❌ کاربر پیدا نشد")
        
        self.db.update_user(uid, lambda u: {**u, "admin_state": None})

    def _admin_gift_coins_amount(self, uid: str, msg, text: str):
        """Handle coin gift amount"""
        amount = self.validator.validate_coins(text)
        if amount is None:
            self.bot.send_message(uid, "❌ مقدار نامعتبر")
            return
        
        self.db.update_user(uid, lambda u: {
            **u,
            "gift_coins_amount": amount,
            "admin_state": "gift_coins_reason"
        })
        self.bot.send_message(uid, "📝 دلیل اهدا سکه را بنویسید:")

    def _admin_gift_coins_reason(self, uid: str, msg, text: str):
        """Handle coin gift reason"""
        self.db.update_user(uid, lambda u: {
            **u,
            "gift_coins_reason": text,
            "admin_state": "gift_coins_id"
        })
        self.bot.send_message(uid, "🆔 آیدی عددی کاربر را وارد کنید:")

    def _admin_gift_coins_id(self, uid: str, msg, text: str):
        """Handle coin gift execution"""
        if not text.isdigit():
            self.bot.send_message(uid, "❌ آیدی باید عدد باشد")
            return
        
        admin_data = self.db.get_user(uid)
        amount = admin_data.get("gift_coins_amount", 0)
        reason = admin_data.get("gift_coins_reason", "هدیه ادمین")
        
        if self.db.get_user(text):
            success = self.add_coins(text, amount, reason)
            if success:
                user_data = self.db.get_user(text)
                self.bot.send_message(
                    uid,
                    f"✅ {amount:,} سکه به {text} اهدا شد\n"
                    f"موجودی جدید: {user_data.get('coins', 0):,} سکه",
                    reply_markup=self.kb_admin()
                )
            else:
                self.bot.send_message(uid, "❌ خطا در اهدا سکه")
        else:
            self.bot.send_message(uid, "❌ کاربر پیدا نشد")
        
        self.db.update_user(uid, lambda u: {**u, "admin_state": None})

    def _handle_callback(self, call):
        """Handle all callback queries"""
        uid = str(call.from_user.id)
        data = call.data
        
        # Answer callback to remove loading state
        self.bot.answer_callback_query(call.id)
        
        # Route to appropriate handler
        if data.startswith("sex_"):
            self._callback_sex(uid, call, data)
        elif data.startswith("change_sex_"):
            self._callback_change_sex(uid, call, data)
        elif data.startswith("find_"):
            self._callback_find(uid, call, data)
        elif data == "end_yes":
            self._callback_end_yes(uid, call)
        elif data == "end_no":
            self.bot.answer_callback_query(call.id, "✅ چت ادامه دارد")
        elif data.startswith("id_share_yes_"):
            self._callback_id_share_yes(uid, call, data)
        elif data == "id_share_no":
            self.bot.answer_callback_query(call.id, "❌ درخواست رد شد")
        elif data.startswith("anon_reply_"):
            self._callback_anon_reply(uid, call, data)
        elif data.startswith("rep_"):
            self._callback_report(uid, call, data)
        elif data.startswith("adm_"):
            self._callback_admin_action(uid, call, data)
        elif data.startswith("auto_ban_"):
            self._callback_auto_ban(uid, call, data)
        elif data.startswith("unban_perm_"):
            self._callback_unban_perm(uid, call, data)
        elif data.startswith("buy_vip_"):
            self._callback_buy_vip(uid, call, data)
        elif data.startswith("select_mission_"):
            self._callback_select_mission(uid, call, data)

    def _callback_sex(self, uid: str, call, data: str):
        """Handle sex selection"""
        sex = "آقا" if data == "sex_m" else "خانم"
        
        self.db.update_user(uid, lambda u: {
            **u,
            "sex": sex,
            "state": "age"
        })
        
        self.bot.edit_message_text(
            "✅ جنسیت ثبت شد",
            call.message.chat.id,
            call.message.message_id
        )
        self.bot.send_message(uid, "🔢 سن خود را وارد کنید (۱۲-۹۹):")

    def _callback_change_sex(self, uid: str, call, data: str):
        """Handle sex change"""
        sex = "آقا" if data == "change_sex_m" else "خانم"
        
        self.db.update_user(uid, lambda u: {**u, "sex": sex})
        
        self.bot.edit_message_text(
            "✅ جنسیت تغییر کرد",
            call.message.chat.id,
            call.message.message_id
        )
        self.bot.send_message(uid, "✅ جنسیت با موفقیت تغییر کرد", reply_markup=self.kb_main(uid))

    def _callback_find(self, uid: str, call, data: str):
        """Handle chat search"""
        search_gender = data.split("_")[1]
        
        self.db.update_user(uid, lambda u: {**u, "search_gender": search_gender})
        
        self.bot.edit_message_text(
            "🔍 در حال جستجو برای هم‌صحبت...",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Add to queue
        def updater(data):
            if "general" not in data:
                data["general"] = []
            if uid not in data["general"]:
                data["general"].append(uid)
            return data
        
        self.db.atomic_update("queue", updater)
        
        # Show cancel button
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("❌ لغو جستجو")
        self.bot.send_message(uid, "⏳ منتظر بمانید...", reply_markup=kb)
        
        # Try to find match
        self._find_match(uid, search_gender)

    def _find_match(self, uid: str, search_gender: str):
        """Find chat match for user"""
        db_q = self.db.read("queue")
        db_u = self.db.read("users")
        user = self.db.get_user(uid)
        
        if not user:
            return
        
        potential = [p for p in db_q.get("general", []) if p != uid]
        
        # Filter blocked users
        potential = [
            p for p in potential 
            if uid not in db_u.get("users", {}).get(p, {}).get("blocks", []) 
            and p not in user.get("blocks", [])
        ]
        
        # Filter by gender preference
        valid_partners = []
        for p in potential:
            partner_sex = db_u.get("users", {}).get(p, {}).get("sex")
            
            if search_gender == "any":
                # Check if partner also accepts any or matches user's gender
                partner_pref = db_u.get("users", {}).get(p, {}).get("search_gender", "any")
                if partner_pref == "any" or partner_pref == ("m" if user.get("sex") == "آقا" else "f"):
                    valid_partners.append(p)
            elif search_gender == "m" and partner_sex == "آقا":
                valid_partners.append(p)
            elif search_gender == "f" and partner_sex == "خانم":
                valid_partners.append(p)
        
        if valid_partners:
            partner = random.choice(valid_partners)
            
            # Remove both from queue
            def remove_from_queue(data):
                if "general" in data:
                    if uid in data["general"]:
                        data["general"].remove(uid)
                    if partner in data["general"]:
                        data["general"].remove(partner)
                return data
            
            self.db.atomic_update("queue", remove_from_queue)
            
            # Connect users
            self.db.update_user(uid, lambda u: {**u, "partner": partner, "state": "chatting"})
            self.db.update_user(partner, lambda u: {**u, "partner": uid, "state": "chatting"})
            
            # Save active chat
            self.save_active_chat(uid, partner)
            
            # Notify both
            self.bot.send_message(uid, "✅ هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chatting())
            self.bot.send_message(partner, "✅ هم‌صحبت پیدا شد! چت را شروع کنید 💬", reply_markup=self.kb_chatting())

    def _callback_end_yes(self, uid: str, call):
        """Handle chat end confirmation"""
        user = self.db.get_user(uid)
        partner = user.get("partner") if user else None
        
        if partner:
            self.end_chat(uid, partner, "چت پایان یافت")
        
        self.bot.answer_callback_query(call.id, "چت پایان یافت")

    def _callback_id_share_yes(self, uid: str, call, data: str):
        """Handle ID share acceptance"""
        requester = data.split("_")[3]
        username = call.from_user.username or "ندارد"
        
        share_text = f"<b>👤 اطلاعات هم‌صحبت:</b>\n\n"
        if username != "ندارد":
            share_text += f"یوزرنیم: @{username}\n"
        share_text += f"آیدی: <code>{uid}</code>"
        
        try:
            self.bot.send_message(requester, share_text)
            self.bot.answer_callback_query(call.id, "✅ اطلاعات ارسال شد")
        except Exception as e:
            logger.error(f"Error sharing ID: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در ارسال")

    def _callback_anon_reply(self, uid: str, call, data: str):
        """Setup anonymous reply"""
        msg_index = int(data.split("_")[2])
        
        db_m = self.db.read("messages")
        inbox = db_m.get("inbox", {}).get(uid, [])
        
        if msg_index < len(inbox):
            msg_data = inbox[msg_index]
            
            self.db.update_user(uid, lambda u: {
                **u,
                "state": "anon_reply",
                "anon_reply_target": msg_data["from"]
            })
            
            self.bot.send_message(uid, "📝 پاسخ خود را بنویسید:")
            self.bot.answer_callback_query(call.id, "✅ پاسخ دهید")

    def _callback_report(self, uid: str, call, data: str):
        """Handle report submission"""
        if data == "rep_cancel":
            self.bot.answer_callback_query(call.id, "✅ گزارش لغو شد")
            return
        
        reasons = {
            "rep_insult": "فحاشی",
            "rep_nsfw": "محتوای +18",
            "rep_spam": "اسپم",
            "rep_harass": "آزار و اذیت"
        }
        
        reason = reasons.get(data, "نامشخص")
        user = self.db.get_user(uid)
        target = user.get("report_target") if user else None
        
        if not target:
            self.bot.answer_callback_query(call.id, "❌ خطا در گزارش")
            return
        
        target_data = self.db.get_user(target)
        target_name = target_data.get("name", "نامشخص") if target_data else "نامشخص"
        reporter_name = user.get("name", "نامشخص")
        
        tehran_time = datetime.datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y-%m-%d %H:%M")
        
        report_text = (
            f"🚩 <b>گزارش جدید</b>\n\n"
            f"<b>شاکی:</b> 🆔 <code>{uid}</code> - {reporter_name}\n"
            f"<b>متهم:</b> 🆔 <code>{target}</code> - {target_name}\n"
            f"<b>دلیل:</b> {reason}\n"
            f"<b>زمان:</b> {tehran_time}\n"
        )
        
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(
            types.InlineKeyboardButton("Ignore", callback_data=f"adm_ignore_{target}"),
            types.InlineKeyboardButton("Permanent Ban", callback_data=f"adm_ban_perm_{target}")
        )
        kb.add(
            types.InlineKeyboardButton("Temp Ban", callback_data=f"adm_ban_temp_{target}"),
            types.InlineKeyboardButton("Warning +1", callback_data=f"adm_warn1_{target}")
        )
        
        try:
            self.bot.send_message(self.owner, report_text, reply_markup=kb)
            self.bot.answer_callback_query(call.id, "✅ گزارش ارسال شد")
        except Exception as e:
            logger.error(f"Error sending report: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در ارسال گزارش")

    def _callback_admin_action(self, uid: str, call, data: str):
        """Handle admin actions on reports"""
        if not self.is_owner(uid):
            self.bot.answer_callback_query(call.id, "❌ فقط ادمین")
            return
        
        parts = data.split("_")
        action = parts[1]
        target = parts[2] if len(parts) > 2 else None
        
        if action == "ignore":
            self.bot.edit_message_text(
                call.message.text + "\n\n✅ <b>Ignored</b>",
                call.message.chat.id,
                call.message.message_id
            )
        
        elif action == "ban" and target:
            ban_type = parts[2] if len(parts) > 2 else None
            actual_target = parts[3] if len(parts) > 3 else target
            
            if ban_type == "perm":
                self.ban_permanent(actual_target, "گزارش تأیید شده")
                self.bot.edit_message_text(
                    call.message.text + "\n\n🚫 <b>Permanent Ban</b>",
                    call.message.chat.id,
                    call.message.message_id
                )
            
            elif ban_type == "temp":
                self.db.update_user(uid, lambda u: {
                    **u,
                    "admin_temp_ban_target": actual_target,
                    "admin_state": "admin_temp_ban_minutes"
                })
                self.bot.send_message(uid, f"⏰ دقیقه بن موقت برای {actual_target}:")
        
        elif action.startswith("warn") and target:
            warns_count = 1 if action == "warn1" else 2
            
            self.db.update_user(target, lambda u: {
                **u,
                "warns": u.get("warns", 0) + warns_count
            })
            
            try:
                self.bot.send_message(target, f"⚠️ {warns_count} اخطار از ادمین دریافت کردید!")
            except:
                pass
            
            self.bot.edit_message_text(
                call.message.text + f"\n\n⚠️ <b>+{warns_count} Warning</b>",
                call.message.chat.id,
                call.message.message_id
            )

    def _callback_auto_ban(self, uid: str, call, data: str):
        """Handle auto-ban review"""
        if not self.is_owner(uid):
            return
        
        action = data.split("_")[2]  # correct or pardon
        target = data.split("_")[3]
        
        if action == "correct":
            self.bot.edit_message_text(
                call.message.text + "\n\n✅ <b>Confirmed by admin</b>",
                call.message.chat.id,
                call.message.message_id
            )
        
        elif action == "pardon":
            # Remove ban
            def updater(data):
                if "permanent" in data and target in data["permanent"]:
                    del data["permanent"][target]
                if "temporary" in data and target in data["temporary"]:
                    del data["temporary"][target]
                return data
            
            self.db.atomic_update("bans", updater)
            
            # Reset user warnings
            self.db.update_user(target, lambda u: {
                **u,
                "warns": 0,
                "had_temp_ban": False
            })
            
            try:
                self.bot.send_message(target, "🌟 حساب شما توسط ادمین از بن خارج شد")
            except:
                pass
            
            self.bot.edit_message_text(
                call.message.text + "\n\n🌟 <b>Pardoned by admin</b>",
                call.message.chat.id,
                call.message.message_id
            )

    def _callback_unban_perm(self, uid: str, call, data: str):
        """Handle permanent unban"""
        if not self.is_owner(uid):
            return
        
        target = data.split("_")[2]
        
        def updater(data):
            if "permanent" in data and target in data["permanent"]:
                del data["permanent"][target]
            return data
        
        self.db.atomic_update("bans", updater)
        
        try:
            self.bot.send_message(target, "🌟 حساب شما از بن دائم خارج شد")
        except:
            pass
        
        self.bot.answer_callback_query(call.id, "✅ بخشیده شد")

    def _callback_buy_vip(self, uid: str, call, data: str):
        """Handle VIP purchase"""
        vip_type = data.split("_")[2]
        
        if vip_type == "christmas":
            self._handle_christmas_vip(uid, call)
            return
        
        price = self.vip_prices_coins.get(vip_type)
        if price is None:
            self.bot.answer_callback_query(call.id, "❌ نوع VIP نامعتبر")
            return
        
        user = self.db.get_user(uid)
        if not user or user.get("coins", 0) < price:
            self.bot.answer_callback_query(
                call.id,
                f"❌ سکه کافی ندارید! نیاز: {price:,}",
                show_alert=True
            )
            return
        
        # Deduct coins and add VIP
        if self.deduct_coins(uid, price):
            reason_map = {
                "week": "خرید با سکه - ۱ هفته",
                "month": "خرید با سکه - ۱ ماه",
                "3month": "خرید با سکه - ۳ ماه",
                "6month": "خرید با سکه - ۶ ماه",
                "year": "خرید با سکه - ۱ سال"
            }
            
            self.add_vip(uid, vip_type, reason_map.get(vip_type, "خرید با سکه"))
            self.bot.answer_callback_query(call.id, "✅ VIP فعال شد!")
        else:
            self.bot.answer_callback_query(call.id, "❌ خطا در پردازش")

    def _handle_christmas_vip(self, uid: str, call):
        """Handle Christmas VIP gift"""
        christmas_deadline = datetime.datetime(2026, 1, 15)
        today = datetime.datetime.now()
        
        if today >= christmas_deadline:
            self.bot.answer_callback_query(
                call.id,
                "❌ مهلت دریافت VIP رایگان کریسمس به پایان رسیده!",
                show_alert=True
            )
            return
        
        user = self.db.get_user(uid)
        if user and user.get("christmas_vip_taken", False):
            self.bot.answer_callback_query(
                call.id,
                "❌ شما قبلاً VIP رایگان کریسمس را دریافت کرده‌اید!",
                show_alert=True
            )
            return
        
        self.add_vip(uid, "christmas", "هدیه کریسمس")
        self.bot.answer_callback_query(call.id, "✅ VIP رایگان کریسمس فعال شد!")

    def _callback_select_mission(self, uid: str, call, data: str):
        """Handle mission selection (admin)"""
        if not self.is_owner(uid):
            return
        
        index = int(data.split("_")[2])
        db_m = self.db.read("missions")
        
        if index >= len(db_m.get("available", [])):
            return
        
        mission = db_m["available"][index]
        
        new_daily = {
            "date": str(datetime.date.today()),
            "mission": mission["name"],
            "reward_type": mission.get("reward_type", "coins"),
            "reward_value": mission.get("reward_value", mission.get("reward", 50)),
            "type": mission["type"],
            "target": mission["target"],
            "description": mission.get("description", mission["name"])
        }
        
        def updater(data):
            data["daily"] = new_daily
            return data
        
        self.db.atomic_update("missions", updater)
        
        reward_text = ""
        if mission.get("reward_type") == "coins":
            reward_text = f"{mission.get('reward_value', mission.get('reward', 0)):,} سکه"
        else:
            duration_names = {
                "week": "۱ هفته",
                "month": "۱ ماه",
                "3month": "۳ ماه",
                "6month": "۶ ماه",
                "year": "۱ سال"
            }
            reward_text = f"VIP {duration_names.get(mission.get('reward_value', 'week'), 'VIP')}"
        
        self.bot.edit_message_text(
            f"✅ ماموریت روزانه به '{mission['name']}' تغییر کرد.\n\n"
            f"کار: {mission.get('description', mission['name'])}\n"
            f"پاداش: {reward_text}",
            call.message.chat.id,
            call.message.message_id
        )

    # ==========================================
    # Bot Execution
    # ==========================================
    def run(self):
        """Run the bot"""
        print("=" * 60)
        print("Shadow Titan v42.1 - Secure Edition")
        print("Security Hardened - All Features Active")
        print("=" * 60)
        
        # Start web server
        try:
            server_thread = Thread(target=run_web, daemon=True)
            server_thread.start()
            print("✅ Web Server started on port 8080")
        except Exception as e:
            logger.error(f"Web Server Error: {e}")
        
        # Start bot
        try:
            print("🚀 Connecting to Telegram...")
            logger.info("Bot polling started")
            self.bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30
            )
        except Exception as e:
            logger.critical(f"Bot crashed: {e}")
            print(f"❌ Bot Error: {e}")
            raise

if __name__ == "__main__":
    try:
        bot = ShadowTitanBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n💥 Fatal Error: {e}")
        logger.critical(f"Fatal error: {e}")
