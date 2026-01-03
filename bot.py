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
import hashlib
import pickle
import base64
import sqlite3
import queue
from flask import Flask
from threading import Thread, Timer
from zoneinfo import ZoneInfo
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import schedule

# ==========================================
# سیستم لاگ و وب‌سرور پیشرفته
# ==========================================
logging.basicConfig(
    filename='shadow_titan.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("ShadowTitan")

class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        message = re.sub(r'token=[^&\s]+', 'token=***', message)
        message = re.sub(r'password=[^&\s]+', 'password=***', message)
        message = re.sub(r'\b\d{10,}\b', '***', message)
        record.msg = message
        return True

logger.addFilter(SensitiveDataFilter())

app = Flask(__name__)
@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Shadow Titan v42.2 - Ultimate Management Edition</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; }
                h1 { text-align: center; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin: 30px 0; }
                .stat-box { background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; text-align: center; }
                .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
                .online { background: #10B981; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ Shadow Titan v42.2</h1>
                <p><strong>Ultimate VIP & Event Management System</strong></p>
                <div class="status online">🟢 Status: Online & Active</div>
                <div class="stats">
                    <div class="stat-box">🚀 Version: 42.2</div>
                    <div class="stat-box">🎖 VIP Management</div>
                    <div class="stat-box">💰 Dynamic Pricing</div>
                    <div class="stat-box">🎪 Event System</div>
                </div>
                <p>🤖 Advanced Persian Chat Bot with Full Management</p>
            </div>
        </body>
    </html>
    """

def run_web():
    app.run(host='0.0.0.0', port=8080, threaded=True)

# ==========================================
# سیستم رمزنگاری پیشرفته
# ==========================================
class AdvancedEncryption:
    def __init__(self):
        self.key_file = "encryption.key"
        self.key = self.load_or_generate_key()
        self.fernet = Fernet(self.key)
        
    def load_or_generate_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            return key
    
    def encrypt_data(self, data):
        try:
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)
            encrypted = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return data
    
    def decrypt_data(self, encrypted_data):
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(encrypted).decode()
            try:
                return json.loads(decrypted)
            except:
                return decrypted
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_data

# ==========================================
# سیستم دیتابیس امن SQLite با رمزنگاری
# ==========================================
class SecureDatabase:
    def __init__(self):
        self.encryption = AdvancedEncryption()
        self.db_file = "secure_chat.db"
        self.backup_dir = "backups"
        self.init_database()
        
    def init_database(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                encrypted_data TEXT,
                vip_end REAL DEFAULT 0,
                coins INTEGER DEFAULT 0,
                total_referrals INTEGER DEFAULT 0,
                warns INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT DEFAULT '',
                ban_until TIMESTAMP DEFAULT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                vip_type TEXT,
                amount_paid INTEGER,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anonymous_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT,
                receiver_id TEXT,
                encrypted_message TEXT,
                sent_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read INTEGER DEFAULT 0,
                FOREIGN KEY (sender_id) REFERENCES users (user_id),
                FOREIGN KEY (receiver_id) REFERENCES users (user_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vip_type TEXT,
                discount_percentage INTEGER,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                reason TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT,
                description TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                vip_plans TEXT,
                is_active INTEGER DEFAULT 1,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                maintenance_mode INTEGER DEFAULT 0,
                vip_access_during_maintenance INTEGER DEFAULT 1,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                reason TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        self.create_indexes()
    
    def create_indexes(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_vip ON users(vip_end)",
            "CREATE INDEX IF NOT EXISTS idx_discounts_active ON discounts(is_active, end_date)",
            "CREATE INDEX IF NOT EXISTS idx_events_active ON events(is_active, end_date)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
    
    def init_backup_system(self):
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, mode=0o700)
    
    def backup_database(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"backup_{timestamp}.db.enc")
            
            with open(self.db_file, 'rb') as f:
                db_data = f.read()
            
            encrypted_backup = self.encryption.fernet.encrypt(db_data)
            
            with open(backup_file, 'wb') as f:
                f.write(encrypted_backup)
            
            self.cleanup_old_backups(days=7)
            
            logger.info(f"Backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return False
    
    def cleanup_old_backups(self, days=7):
        try:
            cutoff = time.time() - (days * 24 * 3600)
            for filename in os.listdir(self.backup_dir):
                filepath = os.path.join(self.backup_dir, filename)
                if os.path.getmtime(filepath) < cutoff:
                    os.remove(filepath)
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def save_user(self, user_id, user_data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        encrypted_data = self.encryption.encrypt_data(user_data)
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, encrypted_data, vip_end, coins, total_referrals, warns, last_active)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, encrypted_data, 
              user_data.get('vip_end', 0),
              user_data.get('coins', 0),
              user_data.get('total_referrals', 0),
              user_data.get('warns', 0)))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user_data = self.encryption.decrypt_data(row['encrypted_data'])
            if isinstance(user_data, str):
                try:
                    user_data = json.loads(user_data)
                except:
                    user_data = {'name': user_data}
            
            user_data['vip_end'] = row['vip_end']
            user_data['coins'] = row['coins']
            user_data['total_referrals'] = row['total_referrals']
            user_data['warns'] = row['warns']
            user_data['is_banned'] = row['is_banned']
            user_data['ban_reason'] = row['ban_reason']
            
            return user_data
        return None
    
    def update_user_field(self, user_id, field, value):
        user = self.get_user(user_id)
        if user:
            user[field] = value
            self.save_user(user_id, user)
            return True
        return False
    
    def get_all_users(self, limit=1000):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, encrypted_data FROM users LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            user_data = self.encryption.decrypt_data(row['encrypted_data'])
            if isinstance(user_data, str):
                try:
                    user_data = json.loads(user_data)
                except:
                    user_data = {'name': user_data}
            user_data['user_id'] = row['user_id']
            users.append(user_data)
        
        return users

    def add_discount(self, vip_type, discount_percentage, start_date, end_date, reason, created_by):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO discounts 
            (vip_type, discount_percentage, start_date, end_date, reason, created_by, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (vip_type, discount_percentage, start_date, end_date, reason, created_by))
        
        conn.commit()
        conn.close()
        return True
    
    def remove_discount(self, discount_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE discounts SET is_active = 0 WHERE id = ?', (discount_id,))
        conn.commit()
        conn.close()
        return True
    
    def get_active_discounts(self, vip_type=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if vip_type:
            cursor.execute('''
                SELECT * FROM discounts 
                WHERE is_active = 1 AND vip_type = ? AND end_date > datetime('now')
                ORDER BY end_date
            ''', (vip_type,))
        else:
            cursor.execute('''
                SELECT * FROM discounts 
                WHERE is_active = 1 AND end_date > datetime('now')
                ORDER BY end_date
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        discounts = []
        for row in rows:
            discounts.append(dict(row))
        
        return discounts
    
    def get_discount_for_vip_type(self, vip_type):
        discounts = self.get_active_discounts(vip_type)
        if discounts:
            return max(discounts, key=lambda x: x['discount_percentage'])
        return None

    def add_event(self, event_name, description, start_date, end_date, vip_plans_json, created_by):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events 
            (event_name, description, start_date, end_date, vip_plans, is_active, created_by)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (event_name, description, start_date, end_date, vip_plans_json, created_by))
        
        conn.commit()
        conn.close()
        return True
    
    def get_active_events(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM events 
            WHERE is_active = 1 AND end_date > datetime('now')
            ORDER BY start_date
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            event = dict(row)
            if event['vip_plans']:
                try:
                    event['vip_plans'] = json.loads(event['vip_plans'])
                except:
                    event['vip_plans'] = []
            else:
                event['vip_plans'] = []
            events.append(event)
        
        return events
    
    def get_event_by_id(self, event_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            event = dict(row)
            if event['vip_plans']:
                try:
                    event['vip_plans'] = json.loads(event['vip_plans'])
                except:
                    event['vip_plans'] = []
            return event
        return None

    def get_maintenance_settings(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM maintenance_settings ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        
        return {
            'maintenance_mode': 0,
            'vip_access_during_maintenance': 1,
            'reason': '',
            'start_time': None,
            'end_time': None
        }
    
    def update_maintenance_settings(self, maintenance_mode, vip_access, reason, start_time, end_time, created_by):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE maintenance_settings SET is_active = 0 WHERE is_active = 1')
        
        cursor.execute('''
            INSERT INTO maintenance_settings 
            (maintenance_mode, vip_access_during_maintenance, reason, start_time, end_time, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (maintenance_mode, vip_access, reason, start_time, end_time, created_by))
        
        conn.commit()
        conn.close()
        return True
    
    def disable_maintenance(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE maintenance_settings SET is_active = 0 WHERE is_active = 1')
        
        conn.commit()
        conn.close()
        return True

# ==========================================
# سیستم Rate Limiting پیشرفته
# ==========================================
class RateLimiter:
    def __init__(self):
        self.requests = {}
        self.lock = threading.Lock()
        
        self.limits = {
            'general': {'limit': 30, 'window': 60},
            'message': {'limit': 10, 'window': 10},
            'search': {'limit': 5, 'window': 30},
            'vip': {'limit': 100, 'window': 60},
        }
        
        self.blocked_ips = {}
        
    def check_rate_limit(self, user_id, action='general', ip=None):
        with self.lock:
            now = time.time()
            
            if ip and ip in self.blocked_ips:
                block_until = self.blocked_ips[ip]
                if now < block_until:
                    return False, f"IP blocked until {datetime.datetime.fromtimestamp(block_until).strftime('%H:%M:%S')}"
                else:
                    del self.blocked_ips[ip]
            
            limit_info = self.limits.get(action, self.limits['general'])
            limit = limit_info['limit']
            window = limit_info['window']
            
            key = f"{user_id}:{action}"
            
            if key not in self.requests:
                self.requests[key] = []
            
            self.requests[key] = [req_time for req_time in self.requests[key] 
                                 if now - req_time < window]
            
            if len(self.requests[key]) >= limit:
                if ip and action == 'general':
                    self.blocked_ips[ip] = now + 300
                    logger.warning(f"IP {ip} blocked for 5 minutes due to rate limit violation")
                
                remaining_time = window - (now - self.requests[key][0])
                return False, f"Rate limit exceeded. Try again in {int(remaining_time)} seconds"
            
            self.requests[key].append(now)
            return True, "OK"
    
    def cleanup_old_requests(self):
        with self.lock:
            now = time.time()
            keys_to_delete = []
            
            for key, timestamps in self.requests.items():
                self.requests[key] = [t for t in timestamps if now - t < 3600]
                if not self.requests[key]:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.requests[key]
            
            ips_to_delete = [ip for ip, until in self.blocked_ips.items() 
                           if now > until]
            for ip in ips_to_delete:
                del self.blocked_ips[ip]

# ==========================================
# هوش مصنوعی فارسی محلی
# ==========================================
class PersianAI:
    def __init__(self):
        self.bad_words_fa = self.load_persian_dictionary()
        self.patterns = self.load_patterns()
        
    def load_persian_dictionary(self):
        return {
            'فحاشی': [
                "کیر", "کص", "کس", "کون", "کیری", "کس کش", "کونی", "کص کش",
                "جنده", "مادرجنده", "پدرسگ", "حرومزاده", "لاشی", "بی ناموس",
                "خارکصه", "تخم", "شاسگول", "پفیوز", "دیوث", "کس ننه", "ننه کس",
                "گایید", "گاییدن", "گاییدم", "گاییده", "لاشخور", "بیناموس"
            ],
            'جسمانی': [
                "سکس", "سکسی", "پورن", "سوپر", "مستهجن", "لخت", "برهنه",
                "سینمایی سوپر", "فیلم سوپر", "فیلم سکسی", "+18", "18+",
                "همخوابی", "رابطه جنسی", "مقاربت", "نزدیکی", "آمیزش"
            ],
            'اعتیاد': [
                "حشیش", "هروئین", "شیشه", "کوکائین", "ماری جوانا", "تریاک",
                "قرص", "اکستازی", "ال اس دی", "متامفتامین", "تریپ", "گیاه"
            ],
            'کلاهبرداری': [
                "هاک", "هک", "کریpto", "بیت کوین", "ترون", "رمزارز",
                "سرمایه گذاری", "سود", "درصد", "پولدار", "ثروتمند",
                "کلیک", "کلیک کنید", "وارد شوید", "اکانت", "پسورد"
            ]
        }
    
    def load_patterns(self):
        return {
            'phone': r'(\+98|0)?9\d{9}',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'link': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+',
            'spam_patterns': [
                r'کلیک.*کن',
                r'وارد.*شو',
                r'سود.*درصد',
                r'پول.*سریع',
                r'ثروتمند.*شو'
            ]
        }
    
    def analyze_text_persian(self, text):
        if not text or len(text.strip()) < 3:
            return {'risk': 0, 'categories': []}
        
        text_lower = text.lower()
        risk_score = 0
        categories = []
        
        for category, words in self.bad_words_fa.items():
            for word in words:
                if word in text_lower:
                    risk_score += 0.3
                    if category not in categories:
                        categories.append(category)
        
        if re.search(self.patterns['phone'], text):
            risk_score += 0.2
            categories.append('شماره تماس')
        
        if re.search(self.patterns['email'], text):
            risk_score += 0.1
            categories.append('ایمیل')
        
        if re.search(self.patterns['link'], text):
            risk_score += 0.3
            categories.append('لینک')
        
        for pattern in self.patterns['spam_patterns']:
            if re.search(pattern, text_lower):
                risk_score += 0.4
                categories.append('اسپم/تبلیغ')
                break
        
        if len(text) > 500:
            risk_score += 0.1
            categories.append('متن طولانی')
        
        repeated_chars = re.findall(r'(.)\1{3,}', text)
        if repeated_chars:
            risk_score += 0.2
            categories.append('تکرار حروف')
        
        risk_score = min(1.0, risk_score)
        
        return {
            'risk': risk_score,
            'categories': list(set(categories)),
            'is_safe': risk_score < 0.6,
            'needs_review': 0.3 <= risk_score < 0.6,
            'is_dangerous': risk_score >= 0.6
        }
    
    def contains_inappropriate_content(self, text):
        analysis = self.analyze_text_persian(text)
        return analysis['is_dangerous'], analysis

# ==========================================
# سیستم مدیریت VIP و تخفیف‌ها
# ==========================================
class VIPManager:
    def __init__(self, db):
        self.db = db
        
        self.base_prices = {
            "week": 300,
            "month": 1000,
            "3month": 2500,
            "6month": 4500,
            "year": 7000,
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
        
        self.vip_names = {
            "week": "۱ هفته",
            "month": "۱ ماه",
            "3month": "۳ ماه",
            "6month": "۶ ماه",
            "year": "۱ سال",
            "christmas": "۳ ماه رایگان"
        }
        
        self.vip_features = {
            "basic": [
                "✅ چت ناشناس نامحدود",
                "✅ ارسال پیام ناشناس",
                "✅ شرکت در گردونه شانس روزانه",
                "✅ دسترسی به پروفایل پیشرفته"
            ],
            "premium": [
                "🎁 100 سکه هدیه ماهانه",
                "🚀 اولویت در جستجوی چت",
                "🎯 ماموریت‌های ویژه",
                "📊 آمار پیشرفته پروفایل",
                "🔔 نوتیفیکیشن اختصاصی",
                "🌈 انتخاب رنگ نام در چت"
            ],
            "exclusive": [
                "⭐ نماد VIP طلایی در کنار نام",
                "⚡ سرعت چت 2 برابری",
                "👑 دسترسی به چت خصوصی ادمین",
                "📈 مشاهده آمار زنده ربات",
                "🎪 ورود رایگان به همه رویدادها",
                "🛡️ پشتیبانی VIP 24/7",
                "🔓 قفل‌شکنی همه محدودیت‌ها"
            ]
        }
    
    def get_final_price(self, vip_type, apply_discounts=True):
        base_price = self.base_prices.get(vip_type, 0)
        
        if not apply_discounts or base_price == 0:
            return base_price, 0, base_price
        
        discount = self.db.get_discount_for_vip_type(vip_type)
        discount_percentage = 0
        discount_amount = 0
        final_price = base_price
        
        if discount:
            discount_percentage = discount['discount_percentage']
            discount_amount = (base_price * discount_percentage) // 100
            final_price = base_price - discount_amount
        
        return final_price, discount_percentage, base_price
    
    def get_vip_plans_with_discounts(self):
        plans = []
        
        for vip_type in ["week", "month", "3month", "6month", "year"]:
            final_price, discount_percentage, original_price = self.get_final_price(vip_type)
            
            plan = {
                'type': vip_type,
                'name': self.vip_names[vip_type],
                'original_price': original_price,
                'final_price': final_price,
                'discount': discount_percentage,
                'duration': self.vip_durations[vip_type],
                'duration_text': self.vip_names[vip_type],
                'has_discount': discount_percentage > 0
            }
            
            if vip_type in ["week", "month"]:
                plan['features'] = self.vip_features["basic"]
                plan['level'] = "basic"
            elif vip_type in ["3month"]:
                plan['features'] = self.vip_features["basic"] + self.vip_features["premium"]
                plan['level'] = "premium"
            else:
                plan['features'] = self.vip_features["basic"] + self.vip_features["premium"] + self.vip_features["exclusive"]
                plan['level'] = "exclusive"
            
            plans.append(plan)
        
        return plans
    
    def get_event_vip_plans(self, event_vip_plans):
        if not event_vip_plans:
            return []
        
        plans = []
        for vip_plan in event_vip_plans:
            vip_type = vip_plan.get('type')
            if vip_type in self.base_prices:
                final_price, discount_percentage, original_price = self.get_final_price(vip_type)
                
                plan = {
                    'type': vip_type,
                    'name': vip_plan.get('name', self.vip_names.get(vip_type, vip_type)),
                    'original_price': vip_plan.get('original_price', original_price),
                    'final_price': vip_plan.get('special_price', final_price),
                    'discount': vip_plan.get('discount', discount_percentage),
                    'duration': vip_plan.get('duration', self.vip_durations.get(vip_type, 0)),
                    'duration_text': vip_plan.get('duration_text', self.vip_names.get(vip_type, vip_type)),
                    'has_discount': True,
                    'is_event_special': True,
                    'event_description': vip_plan.get('description', 'پلن ویژه رویداد'),
                    'features': vip_plan.get('features', [])
                }
                
                plans.append(plan)
        
        return plans

# ==========================================
# سیستم مدیریت رویدادها
# ==========================================
class EventManager:
    def __init__(self, db):
        self.db = db
    
    def create_event(self, event_name, description, start_date, end_date, vip_plans, created_by):
        vip_plans_json = json.dumps(vip_plans, ensure_ascii=False)
        return self.db.add_event(event_name, description, start_date, end_date, vip_plans_json, created_by)
    
    def get_active_events(self):
        return self.db.get_active_events()

# ==========================================
# سیستم مدیریت تخفیف‌ها
# ==========================================
class DiscountManager:
    def __init__(self, db):
        self.db = db
    
    def add_discount(self, vip_type, discount_percentage, start_date, end_date, reason, created_by):
        if discount_percentage < 1 or discount_percentage > 99:
            return False, "درصد تخفیف باید بین ۱ تا ۹۹ باشد"
        
        if start_date >= end_date:
            return False, "تاریخ شروع باید قبل از تاریخ پایان باشد"
        
        success = self.db.add_discount(vip_type, discount_percentage, start_date, end_date, reason, created_by)
        if success:
            return True, "تخفیف با موفقیت اضافه شد"
        else:
            return False, "خطا در افزودن تخفیف"
    
    def get_all_discounts(self):
        return self.db.get_active_discounts()
    
    def remove_discount(self, discount_id):
        return self.db.remove_discount(discount_id)

# ==========================================
# سیستم مدیریت تعمیر و نگهداری
# ==========================================
class MaintenanceManager:
    def __init__(self, db):
        self.db = db
    
    def set_maintenance_mode(self, maintenance_mode, vip_access, reason, start_time, end_time, created_by):
        if maintenance_mode not in [0, 1, 2]:
            return False, "حالت تعمیر نامعتبر است"
        
        if vip_access not in [0, 1]:
            return False, "تنظیمات دسترسی VIP نامعتبر است"
        
        if start_time and end_time and start_time >= end_time:
            return False, "تاریخ شروع باید قبل از تاریخ پایان باشد"
        
        success = self.db.update_maintenance_settings(maintenance_mode, vip_access, reason, start_time, end_time, created_by)
        
        if success:
            mode_text = {
                0: "غیرفعال",
                1: "فعال (فقط غیر-VIP مسدود)",
                2: "فعال (همه کاربران مسدود)"
            }.get(maintenance_mode, "نامشخص")
            
            vip_text = "✅ دارند" if vip_access == 1 else "❌ ندارند"
            
            message = f"""
🔧 <b>حالت تعمیر تنظیم شد</b>

📊 وضعیت: <b>{mode_text}</b>
👥 دسترسی VIP: {vip_text}
📝 دلیل: {reason or 'بدون دلیل'}
            """
            
            if start_time and end_time:
                start_str = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                end_str = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                message += f"\n⏰ زمان: {start_str} تا {end_str}"
            
            return True, message
        else:
            return False, "خطا در ذخیره تنظیمات"
    
    def disable_maintenance(self):
        success = self.db.disable_maintenance()
        if success:
            return True, "حالت تعمیر غیرفعال شد"
        else:
            return False, "خطا در غیرفعال کردن حالت تعمیر"
    
    def check_access(self, user_id, is_vip):
        settings = self.db.get_maintenance_settings()
        
        if settings['maintenance_mode'] == 0:
            return True, None
        
        if settings['maintenance_mode'] == 1:
            if is_vip and settings['vip_access_during_maintenance'] == 1:
                return True, None
            else:
                return False, "ربات در حال تعمیر است. لطفاً بعداً تلاش کنید."
        
        if settings['maintenance_mode'] == 2:
            return False, "ربات در حال تعمیر است. لطفاً بعداً تلاش کنید."
        
        return True, None

# ==========================================
# ربات اصلی با قابلیت‌های مدیریتی کامل
# ==========================================
class ShadowTitanBotEnhanced:
    def __init__(self):
        self.token = "8213706320:AAFnu2EgXqRf05dPuJE_RU0AlQcXQkNdRZI"
        self.owner = "8013245091"
        self.channel = "@ChatNaAnnouncements"
        self.support = "@its_alimo"
        
        self.db = SecureDatabase()
        self.rate_limiter = RateLimiter()
        self.persian_ai = PersianAI()
        self.vip_manager = VIPManager(self.db)
        self.event_manager = EventManager(self.db)
        self.discount_manager = DiscountManager(self.db)
        self.maintenance_manager = MaintenanceManager(self.db)
        
        self.admins = ["8013245091"]
        
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.username = self.bot.get_me().username if self.bot.get_me() else "ShadowTitanBot"
        
        self.admin_states = {}
        
        self.register_handlers()
        self.start_background_tasks()
        
        logger.info("🤖 Shadow Titan v42.2 Ultimate Management Edition Started")
    
    def start_background_tasks(self):
        self.schedule_task(self.check_all_vip_expiry, hours=6)
        self.schedule_task(self.rate_limiter.cleanup_old_requests, minutes=30)
        self.schedule_task(self.db.backup_database, hours=24)
    
    def schedule_task(self, func, minutes=0, hours=0):
        def task_wrapper():
            try:
                func()
            except Exception as e:
                logger.error(f"Scheduled task error: {e}")
        
        interval = (hours * 3600) + (minutes * 60)
        if interval > 0:
            timer = threading.Timer(interval, task_wrapper)
            timer.daemon = True
            timer.start()
            return timer
        return None
    
    def check_all_vip_expiry(self):
        try:
            users = self.db.get_all_users()
            for user in users:
                if 'user_id' in user:
                    pass
        except Exception as e:
            logger.error(f"VIP expiry check error: {e}")
    
    def kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        user = self.db.get_user(uid)
        is_vip = user and user.get('vip_end', 0) > time.time()
        
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس", "🎯 ماموریت روزانه")
        markup.add("👥 رفرال و دعوت", "🎖 خرید VIP")
        
        if is_vip:
            markup.add("⭐ ویژگی‌های VIP", "🎁 هدیه ماهانه")
        
        active_events = self.event_manager.get_active_events()
        if active_events:
            markup.add("🎪 رویدادهای ویژه")
        
        markup.add("❓ راهنما")
        
        if uid in self.admins:
            markup.add("🛡️ پنل مدیریت")
        
        return markup
    
    def kb_admin_main(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📊 آمار کامل", "👥 مدیریت کاربران")
        markup.add("🎖 مدیریت VIP", "💰 مدیریت تخفیف‌ها")
        markup.add("🎪 مدیریت رویدادها", "🔧 مدیریت تعمیر")
        markup.add("📁 مدیریت فایل‌ها", "🚫 مدیریت بن‌ها")
        markup.add("🔙 بازگشت به منو")
        return markup
    
    def kb_discount_management(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ افزودن تخفیف", callback_data="admin_add_discount"),
            types.InlineKeyboardButton("🗑 حذف تخفیف", callback_data="admin_remove_discount")
        )
        markup.add(
            types.InlineKeyboardButton("📋 لیست تخفیف‌ها", callback_data="admin_list_discounts"),
            types.InlineKeyboardButton("📊 آمار تخفیف‌ها", callback_data="admin_discount_stats")
        )
        return markup
    
    def kb_event_management(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ ایجاد رویداد", callback_data="admin_create_event"),
            types.InlineKeyboardButton("🗑 حذف رویداد", callback_data="admin_remove_event")
        )
        markup.add(
            types.InlineKeyboardButton("📋 رویدادهای فعال", callback_data="admin_active_events"),
            types.InlineKeyboardButton("➕ افزودن پلن ویژه", callback_data="admin_add_event_plan")
        )
        return markup
    
    def kb_maintenance_management(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔧 تنظیم حالت تعمیر", callback_data="admin_set_maintenance"),
            types.InlineKeyboardButton("❌ غیرفعال کردن", callback_data="admin_disable_maintenance")
        )
        markup.add(
            types.InlineKeyboardButton("📊 وضعیت فعلی", callback_data="admin_maintenance_status")
        )
        return markup
    
    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(msg):
            uid = str(msg.chat.id)
            
            user = self.db.get_user(uid)
            is_vip = user and user.get('vip_end', 0) > time.time()
            has_access, error_msg = self.maintenance_manager.check_access(uid, is_vip)
            
            if not has_access:
                self.bot.send_message(uid, f"🚫 {error_msg}")
                return
            
            allowed, message = self.rate_limiter.check_rate_limit(uid, 'general')
            if not allowed:
                self.bot.send_message(uid, f"⏳ {message}")
                return
            
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None
            
            if payload:
                if payload.startswith('ref_'):
                    self.handle_referral(uid, payload[4:])
                elif payload.startswith('msg_'):
                    pass
                elif payload.startswith('event_'):
                    pass
            
            if not user:
                self.register_new_user(uid)
            else:
                self.welcome_back_user(uid, user)
        
        @self.bot.message_handler(func=lambda msg: True)
        def all_messages(msg):
            uid = str(msg.chat.id)
            text = msg.text
            
            if not text:
                return
            
            user = self.db.get_user(uid)
            is_vip = user and user.get('vip_end', 0) > time.time()
            has_access, error_msg = self.maintenance_manager.check_access(uid, is_vip)
            
            if not has_access:
                self.bot.send_message(uid, f"🚫 {error_msg}")
                return
            
            allowed, message = self.rate_limiter.check_rate_limit(uid, 'message')
            if not allowed:
                self.bot.send_message(uid, f"⏳ {message}")
                return
            
            is_dangerous, analysis = self.persian_ai.contains_inappropriate_content(text)
            if is_dangerous:
                self.handle_inappropriate_content(uid, analysis)
                return
            
            if uid in self.admins:
                if text == "🛡️ پنل مدیریت":
                    self.show_admin_panel(uid)
                    return
                elif text == "🔙 بازگشت به منو":
                    self.bot.send_message(uid, "🏠 منوی اصلی", reply_markup=self.kb_main(uid))
                    return
                
                if uid in self.admin_states:
                    self.handle_admin_state(uid, text)
                    return
            
            self.handle_user_command(uid, text, user)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_wrapper(call):
            self.callback_handler(call)
    
    def callback_handler(self, call):
        uid = str(call.from_user.id)
        
        if call.data == "admin_add_discount":
            self.start_add_discount(uid)
        elif call.data == "admin_list_discounts":
            self.show_discount_list(uid)
        elif call.data == "admin_discount_stats":
            self.show_discount_stats(uid)
        elif call.data == "admin_create_event":
            self.start_create_event(uid)
        elif call.data == "admin_active_events":
            self.show_active_events_admin(uid)
        elif call.data == "admin_set_maintenance":
            self.start_set_maintenance(uid)
        elif call.data == "admin_disable_maintenance":
            self.disable_maintenance_mode(uid)
        elif call.data == "admin_maintenance_status":
            self.show_maintenance_status(uid)
        elif call.data.startswith("buy_vip_"):
            vip_type = call.data[8:]
            self.handle_vip_purchase(uid, vip_type)
        
        self.bot.answer_callback_query(call.id)
    
    def handle_admin_state(self, uid, text):
        state_data = self.admin_states[uid]
        state = state_data.get('state')
        
        if state == 'waiting_for_discount_vip_type':
            self.process_discount_vip_type(uid, text)
        elif state == 'waiting_for_discount_percentage':
            self.process_discount_percentage(uid, text)
        elif state == 'waiting_for_discount_dates':
            self.process_discount_dates(uid, text)
        elif state == 'waiting_for_discount_reason':
            self.process_discount_reason(uid, text)
        elif state == 'waiting_for_event_name':
            self.process_event_name(uid, text)
        elif state == 'waiting_for_event_description':
            self.process_event_description(uid, text)
        elif state == 'waiting_for_event_dates':
            self.process_event_dates(uid, text)
        elif state == 'waiting_for_event_vip_plans':
            self.process_event_vip_plans(uid, text)
        elif state == 'waiting_for_maintenance_mode':
            self.process_maintenance_mode(uid, text)
        elif state == 'waiting_for_maintenance_vip_access':
            self.process_maintenance_vip_access(uid, text)
        elif state == 'waiting_for_maintenance_reason':
            self.process_maintenance_reason(uid, text)
        elif state == 'waiting_for_maintenance_dates':
            self.process_maintenance_dates(uid, text)
    
    def handle_user_command(self, uid, text, user):
        if text == "🎖 خرید VIP":
            self.show_vip_plans(uid)
        elif text == "⭐ ویژگی‌های VIP":
            self.show_vip_features(uid)
        elif text == "🎪 رویدادهای ویژه":
            self.show_events(uid)
        elif text == "👤 پروفایل من":
            self.show_profile(uid, user)
        elif text == "🎡 گردونه شانس":
            self.spin_wheel(uid, user)
        elif text == "🎯 ماموریت روزانه":
            self.show_daily_mission(uid, user)
        elif text == "👥 رفرال و دعوت":
            self.show_referral_system(uid, user)
        elif text == "📩 لینک ناشناس من":
            self.show_anonymous_link(uid)
        elif text == "📥 پیام‌های ناشناس":
            self.show_anonymous_messages(uid)
        elif text == "❓ راهنما":
            self.show_help(uid)
        elif text == "🛰 شروع چت ناشناس":
            self.start_chat_search(uid, user)
        else:
            self.bot.send_message(uid, "🤔 دستور نامعتبر است.")
    
    def show_vip_features(self, uid):
        user = self.db.get_user(uid)
        is_vip = user and user.get('vip_end', 0) > time.time()
        
        if not is_vip:
            message = """
⭐ <b>ویژگی‌های VIP</b>

🎖 با خرید VIP از مزایای زیر بهره‌مند شوید:

<b>ویژگی‌های پایه:</b>
✅ چت ناشناس نامحدود
✅ ارسال پیام ناشناس
✅ شرکت در گردونه شانس روزانه
✅ دسترسی به پروفایل پیشرفته

<b>ویژگی‌های ویژه:</b>
🎁 سکه هدیه ماهانه
🚀 اولویت در جستجوی چت
🎯 ماموریت‌های ویژه
📊 آمار پیشرفته پروفایل

برای خرید VIP به بخش 🎖 خرید VIP مراجعه کنید.
            """
        else:
            message = f"""
🎖 <b>ویژگی‌های VIP شما فعال است!</b>

✅ از تمام مزایای VIP بهره‌مند هستید.
📅 تاریخ انقضا: {datetime.datetime.fromtimestamp(user['vip_end']).strftime('%Y-%m-%d')}
            """
        
        self.bot.send_message(uid, message)
    
    def spin_wheel(self, uid, user):
        if not user:
            return
        
        is_vip = user.get('vip_end', 0) > time.time()
        spins_today = user.get('spins_today', 0)
        
        if spins_today >= (3 if is_vip else 1):
            self.bot.send_message(uid, "⚠️ شما امروز از گردونه شانس خود استفاده کرده‌اید. فردا دوباره امتحان کنید!")
            return
        
        prizes = [10, 20, 50, 100, 200, 500]
        prize = random.choice(prizes)
        
        user['coins'] = user.get('coins', 0) + prize
        user['spins_today'] = spins_today + 1
        self.db.save_user(uid, user)
        
        self.bot.send_message(uid, f"🎡 گردونه شانس!\n🎁 جایزه شما: {prize} سکه\n💰 موجودی جدید: {user['coins']} سکه")
    
    def show_daily_mission(self, uid, user):
        missions = [
            {"task": "ورود روزانه به ربات", "reward": 10},
            {"task": "ارسال ۵ پیام ناشناس", "reward": 25},
            {"task": "دعوت یک دوست", "reward": 50},
        ]
        
        message = "🎯 <b>ماموریت‌های روزانه</b>\n\n"
        for i, mission in enumerate(missions, 1):
            message += f"{i}. {mission['task']}\n   🎁 جایزه: {mission['reward']} سکه\n\n"
        
        message += "💡 با انجام ماموریت‌ها سکه دریافت کنید و VIP بخرید!"
        self.bot.send_message(uid, message)
    
    def show_referral_system(self, uid, user):
        ref_link = f"https://t.me/{self.username}?start=ref_{uid}"
        
        message = f"""
👥 <b>سیستم دعوت دوستان</b>

🔗 لینک دعوت شما:
<code>{ref_link}</code>

📊 آمار دعوت‌ها:
👤 تعداد دعوت شده: {user.get('total_referrals', 0)}
💰 سکه کسب شده: {user.get('total_referrals', 0) * 100}

🎁 پاداش‌ها:
• هر دعوت موفق: 100 سکه
• هر ۵ دعوت: ۱ روز VIP رایگان
• هر ۱۰ دعوت: ۵۰۰ سکه هدیه

📣 دوستان خود را دعوت کنید و سکه کسب کنید!
        """
        
        self.bot.send_message(uid, message)
    
    def show_anonymous_link(self, uid):
        msg_id = hashlib.md5(f"{uid}_{time.time()}".encode()).hexdigest()[:8]
        link = f"https://t.me/{self.username}?start=msg_{msg_id}"
        
        message = f"""
📩 <b>لینک ناشناس شما</b>

🔗 این لینک را با دوستان خود به اشتراک بگذارید:

<code>{link}</code>

⚠️ توجه:
• پیام‌ها کاملاً ناشناس هستند
• می‌توانید پاسخ دهید
• پیام‌های نامناسب را گزارش دهید
        """
        
        self.bot.send_message(uid, message)
    
    def show_anonymous_messages(self, uid):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM anonymous_messages 
            WHERE receiver_id = ? AND is_read = 0
            ORDER BY sent_time DESC
        ''', (uid,))
        
        messages = cursor.fetchall()
        conn.close()
        
        if not messages:
            self.bot.send_message(uid, "📭 پیام ناشناسی ندارید.")
            return
        
        for msg in messages[:5]:
            decrypted_msg = self.db.encryption.decrypt_data(msg['encrypted_message'])
            sender_hash = msg['sender_id'][:8] if msg['sender_id'] else "ناشناس"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📩 پاسخ", callback_data=f"reply_msg_{msg['id']}"),
                types.InlineKeyboardButton("🚫 گزارش", callback_data=f"report_msg_{msg['id']}")
            )
            
            self.bot.send_message(uid, f"📩 از: {sender_hash}\n📝 {decrypted_msg}\n⏰ {msg['sent_time']}", reply_markup=markup)
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE anonymous_messages SET is_read = 1 WHERE id = ?', (msg['id'],))
            conn.commit()
            conn.close()
    
    def show_help(self, uid):
        message = f"""
❓ <b>راهنمای استفاده از Shadow Titan</b>

<b>دستورات اصلی:</b>
🛰 شروع چت ناشناس - چت تصادفی با کاربران دیگر
👤 پروفایل من - مشاهده اطلاعات حساب
📩 لینک ناشناس من - دریافت لینک برای دریافت پیام ناشناس
📥 پیام‌های ناشناس - مشاهده پیام‌های دریافتی
🎡 گردونه شانس - چرخاندن گردونه برای دریافت سکه
🎯 ماموریت روزانه - انجام ماموریت برای دریافت سکه
👥 رفرال و دعوت - دعوت دوستان و دریافت پاداش
🎖 خرید VIP - خرید اشتراک ویژه
❓ راهنما - نمایش این صفحه

<b>پشتیبانی:</b>
🔧 {self.support}
📢 {self.channel}
        """
        
        self.bot.send_message(uid, message)
    
    def start_chat_search(self, uid, user):
        is_vip = user and user.get('vip_end', 0) > time.time()
        
        if not is_vip and user.get('chats_today', 0) >= 5:
            self.bot.send_message(uid, "⚠️ امروز از سهمیه چت رایگان خود استفاده کرده‌اید. برای چت نامحدود VIP بخرید.")
            return
        
        if not is_vip:
            user['chats_today'] = user.get('chats_today', 0) + 1
            self.db.save_user(uid, user)
        
        self.bot.send_message(uid, "🔍 در حال جستجوی کاربر...")
        
        search_msg = self.bot.send_message(uid, "🔄 جستجوی کاربر...")
        time.sleep(2)
        
        self.bot.edit_message_text("✅ کاربر یافت شد! شروع چت...", uid, search_msg.message_id)
        time.sleep(1)
        
        self.bot.send_message(uid, """
💬 <b>چت ناشناس شروع شد!</b>

📝 می‌توانید پیام خود را ارسال کنید.
⏹ برای پایان چت، /end را ارسال کنید.
⚠️ ارسال اطلاعات شخصی ممنوع است.
        """)
    
    def handle_referral(self, uid, ref_id):
        if uid == ref_id:
            self.bot.send_message(uid, "❌ نمی‌توانید خود را دعوت کنید!")
            return
        
        ref_user = self.db.get_user(ref_id)
        if ref_user:
            ref_user['total_referrals'] = ref_user.get('total_referrals', 0) + 1
            ref_user['coins'] = ref_user.get('coins', 0) + 100
            self.db.save_user(ref_id, ref_user)
            
            new_user = self.db.get_user(uid)
            if new_user:
                new_user['coins'] = new_user.get('coins', 0) + 50
                self.db.save_user(uid, new_user)
                
                self.bot.send_message(ref_id, f"🎉 کاربر جدیدی با لینک شما وارد شد!\n💰 100 سکه پاداش دریافت کردید.")
                self.bot.send_message(uid, f"🎁 50 سکه هدیه ثبت‌نام دریافت کردید!")
    
    def show_vip_plans(self, uid):
        user = self.db.get_user(uid)
        coins = user.get('coins', 0) if user else 0
        
        normal_plans = self.vip_manager.get_vip_plans_with_discounts()
        
        event_plans = []
        active_events = self.event_manager.get_active_events()
        for event in active_events:
            event_vip_plans = self.vip_manager.get_event_vip_plans(event['vip_plans'])
            for plan in event_vip_plans:
                plan['event_name'] = event['event_name']
                event_plans.append(plan)
        
        message = f"""
🎖 <b>فروشگاه VIP</b>

💰 <b>موجودی شما:</b> {coins:,} سکه

<b>طرح‌های VIP:</b>
        """
        
        kb = types.InlineKeyboardMarkup(row_width=1)
        
        for plan in normal_plans:
            status = "✅" if coins >= plan['final_price'] else "🔒"
            
            if plan['has_discount']:
                button_text = f"🎁 {plan['name']} - {plan['final_price']:,} سکه (تخفیف {plan['discount']}%)"
            else:
                button_text = f"{status} {plan['name']} - {plan['final_price']:,} سکه"
            
            callback_data = f"buy_vip_{plan['type']}"
            
            if coins >= plan['final_price']:
                kb.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
            else:
                kb.add(types.InlineKeyboardButton(button_text, callback_data="insufficient_coins"))
            
            message += f"\n\n<b>{plan['name']}:</b>"
            for feature in plan['features'][:3]:
                message += f"\n{feature}"
            
            if plan['has_discount']:
                message += f"\n💰 قیمت اصلی: <s>{plan['original_price']:,}</s> ← {plan['final_price']:,} سکه"
            else:
                message += f"\n💰 قیمت: {plan['final_price']:,} سکه"
        
        if event_plans:
            message += "\n\n🎪 <b>پلن‌های ویژه رویدادها:</b>"
            
            for plan in event_plans:
                status = "✅" if coins >= plan['final_price'] else "🔒"
                button_text = f"🎪 {plan['name']} - {plan['final_price']:,} سکه"
                callback_data = f"buy_event_vip_{plan['type']}_{hashlib.md5(plan['event_name'].encode()).hexdigest()[:8]}"
                
                if coins >= plan['final_price']:
                    kb.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
                else:
                    kb.add(types.InlineKeyboardButton(button_text, callback_data="insufficient_coins"))
                
                message += f"\n\n<b>{plan['name']} ({plan['event_name']}):</b>"
                message += f"\n📝 {plan.get('event_description', 'پلن ویژه رویداد')}"
                message += f"\n💰 قیمت ویژه: {plan['final_price']:,} سکه"
        
        self.bot.send_message(uid, message, reply_markup=kb)
    
    def show_profile(self, uid, user):
        is_vip = user.get('vip_end', 0) > time.time()
        vip_end = user.get('vip_end', 0)
        
        if is_vip:
            days_left = int((vip_end - time.time()) / (24 * 3600))
            vip_status = f"🎖 VIP ({days_left} روز باقی مانده)"
        else:
            vip_status = "⭐ معمولی"
        
        message = f"""
👤 <b>پروفایل شما</b>

📛 نام: {user.get('name', 'نامشخص')}
🎭 وضعیت: {vip_status}
💰 سکه: {user.get('coins', 0):,}
👥 دعوت‌ها: {user.get('total_referrals', 0)}
⚠️ اخطارها: {user.get('warns', 0)}/3

📅 تاریخ عضویت: {datetime.datetime.fromtimestamp(user.get('created_at', time.time())).strftime('%Y-%m-%d')}
        """
        
        self.bot.send_message(uid, message)
    
    def show_events(self, uid):
        active_events = self.event_manager.get_active_events()
        
        if not active_events:
            message = """
🎪 <b>رویدادهای ویژه</b>

در حال حاضر رویداد فعالی وجود ندارد.

📅 به زودی رویدادهای جدیدی برگزار خواهد شد!
            """
        else:
            message = """
🎪 <b>رویدادهای ویژه فعال</b>

🔥 فرصت طلایی برای دریافت جوایز فوق‌العاده!
            """
            
            for event in active_events:
                start_date = datetime.datetime.fromisoformat(event['start_date'].replace('Z', '+00:00')).strftime('%Y/%m/%d')
                end_date = datetime.datetime.fromisoformat(event['end_date'].replace('Z', '+00:00')).strftime('%Y/%m/%d')
                
                message += f"\n\n<b>🎪 {event['event_name']}</b>"
                message += f"\n📝 {event['description'] or 'بدون توضیح'}"
                message += f"\n⏰ از {start_date} تا {end_date}"
                
                if event['vip_plans']:
                    message += "\n\n<b>🎁 پلن‌های ویژه این رویداد:</b>"
                    for plan in event['vip_plans']:
                        message += f"\n• {plan.get('name', 'پلن ویژه')}: {plan.get('special_price', '?')} سکه"
        
        self.bot.send_message(uid, message)
    
    def handle_inappropriate_content(self, uid, analysis):
        user = self.db.get_user(uid)
        if user:
            user['warns'] = user.get('warns', 0) + 1
            self.db.save_user(uid, user)
            
            if user['warns'] >= 3:
                self.ban_user(uid, "ارسال محتوای نامناسب مکرر")
            else:
                self.bot.send_message(uid, f"⚠️ <b>اخطار {user['warns']}/3</b>\n\nمحتوای نامناسب ممنوع است!")
    
    def ban_user(self, uid, reason):
        user = self.db.get_user(uid)
        if user:
            user['is_banned'] = 1
            user['ban_reason'] = reason
            self.db.save_user(uid, user)
            
            self.bot.send_message(uid, f"🚫 حساب شما بن شد!\nدلیل: {reason}\nپشتیبانی: {self.support}")
    
    def register_new_user(self, uid):
        self.bot.send_message(uid, "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\nلطفاً نام مستعار خود را وارد کنید:")
        
        user_data = {
            'name': '',
            'state': 'name',
            'vip_end': 0,
            'coins': 50,
            'total_referrals': 0,
            'warns': 0,
            'created_at': time.time(),
            'is_banned': 0,
            'ban_reason': ''
        }
        self.db.save_user(uid, user_data)
    
    def welcome_back_user(self, uid, user):
        is_vip = user.get('vip_end', 0) > time.time()
        vip_status = "🎖 VIP" if is_vip else "⭐ عادی"
        
        active_events = self.event_manager.get_active_events()
        event_text = ""
        if active_events:
            event_text = "\n\n🎪 <b>رویدادهای فعال:</b>\n"
            for event in active_events:
                event_text += f"• {event['event_name']}\n"
        
        welcome_message = f"""
🔄 <b>خوش برگشتید {user.get('name', 'عزیز')}!</b>

🔸 وضعیت: {vip_status}
💰 سکه: {user.get('coins', 0):,}
👥 دعوت‌ها: {user.get('total_referrals', 0)}
{event_text}
        """
        
        self.bot.send_message(uid, welcome_message, reply_markup=self.kb_main(uid))
    
    def show_admin_panel(self, uid):
        self.bot.send_message(uid, "🛡️ <b>پنل مدیریت پیشرفته</b>\n\nلطفا بخش مورد نظر را انتخاب کنید:", reply_markup=self.kb_admin_main())
    
    def start_add_discount(self, uid):
        self.admin_states[uid] = {
            'state': 'waiting_for_discount_vip_type',
            'data': {}
        }
        
        vip_types = [
            ("week", "۱ هفته"),
            ("month", "۱ ماه"),
            ("3month", "۳ ماه"),
            ("6month", "۶ ماه"),
            ("year", "۱ سال"),
            ("all", "همه انواع")
        ]
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for vip_id, vip_name in vip_types:
            markup.add(f"{vip_name}")
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, "🎯 <b>افزودن تخفیف جدید</b>\n\nلطفا نوع VIP مورد نظر برای تخفیف را انتخاب کنید:", reply_markup=markup)
    
    def process_discount_vip_type(self, uid, text):
        vip_type_map = {
            "۱ هفته": "week",
            "۱ ماه": "month",
            "۳ ماه": "3month",
            "۶ ماه": "6month",
            "۱ سال": "year",
            "همه انواع": "all"
        }
        
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        vip_type = vip_type_map.get(text)
        if not vip_type:
            self.bot.send_message(uid, "❌ نوع VIP نامعتبر است.")
            return
        
        self.admin_states[uid]['data']['vip_type'] = vip_type
        self.admin_states[uid]['state'] = 'waiting_for_discount_percentage'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, f"✅ نوع VIP: {text}\n\nلطفا درصد تخفیف را وارد کنید (۱ تا ۹۹):", reply_markup=markup)
    
    def process_discount_percentage(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        try:
            percentage = int(text)
            if not 1 <= percentage <= 99:
                raise ValueError
        except:
            self.bot.send_message(uid, "❌ درصد تخفیف نامعتبر است.")
            return
        
        self.admin_states[uid]['data']['percentage'] = percentage
        self.admin_states[uid]['state'] = 'waiting_for_discount_dates'
        
        today = datetime.date.today()
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("امروز تا فردا", "امروز تا هفته آینده")
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, f"✅ درصد تخفیف: {percentage}%\n\nلطفا بازه زمانی تخفیف را انتخاب کنید:", reply_markup=markup)
    
    def process_discount_dates(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        today = datetime.date.today()
        
        if text == "امروز تا فردا":
            start_date = today
            end_date = today + datetime.timedelta(days=1)
        elif text == "امروز تا هفته آینده":
            start_date = today
            end_date = today + datetime.timedelta(days=7)
        else:
            try:
                dates = text.split('-')
                if len(dates) != 2:
                    raise ValueError
                
                start_str, end_str = dates
                start_date = datetime.datetime.strptime(start_str.strip(), '%Y/%m/%d').date()
                end_date = datetime.datetime.strptime(end_str.strip(), '%Y/%m/%d').date()
                
                if start_date >= end_date:
                    raise ValueError
            except:
                self.bot.send_message(uid, "❌ فرمت تاریخ نامعتبر است.")
                return
        
        self.admin_states[uid]['data']['start_date'] = start_date.isoformat()
        self.admin_states[uid]['data']['end_date'] = end_date.isoformat()
        self.admin_states[uid]['state'] = 'waiting_for_discount_reason'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون دلیل", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ بازه زمانی: {start_date} تا {end_date}\n\nلطفا دلیل تخفیف را وارد کنید:", reply_markup=markup)
    
    def process_discount_reason(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        reason = text if text != "بدون دلیل" else ""
        
        data = self.admin_states[uid]['data']
        vip_type = data['vip_type']
        percentage = data['percentage']
        start_date = data['start_date']
        end_date = data['end_date']
        
        if vip_type == "all":
            vip_types = ["week", "month", "3month", "6month", "year"]
            success_count = 0
            
            for vt in vip_types:
                success, message = self.discount_manager.add_discount(
                    vt, percentage, start_date, end_date, reason, uid
                )
                if success:
                    success_count += 1
            
            if success_count > 0:
                self.bot.send_message(uid, f"✅ تخفیف {percentage}% با موفقیت برای {success_count} نوع VIP اضافه شد.", reply_markup=self.kb_admin_main())
            else:
                self.bot.send_message(uid, "❌ خطا در افزودن تخفیف‌ها.", reply_markup=self.kb_admin_main())
        else:
            success, message = self.discount_manager.add_discount(
                vip_type, percentage, start_date, end_date, reason, uid
            )
            
            if success:
                self.bot.send_message(uid, f"✅ {message}", reply_markup=self.kb_admin_main())
            else:
                self.bot.send_message(uid, f"❌ {message}", reply_markup=self.kb_admin_main())
        
        del self.admin_states[uid]
    
    def show_discount_list(self, uid):
        discounts = self.discount_manager.get_all_discounts()
        
        if not discounts:
            self.bot.send_message(uid, "📭 هیچ تخفیف فعالی وجود ندارد.")
            return
        
        message = "💰 <b>لیست تخفیف‌های فعال</b>\n\n"
        
        for i, discount in enumerate(discounts, 1):
            vip_type = discount['vip_type']
            percentage = discount['discount_percentage']
            start_date = datetime.datetime.fromisoformat(discount['start_date'].replace('Z', '+00:00')).strftime('%Y/%m/%d')
            end_date = datetime.datetime.fromisoformat(discount['end_date'].replace('Z', '+00:00')).strftime('%Y/%m/%d')
            reason = discount['reason'] or "بدون دلیل"
            
            message += f"<b>{i}. {self.vip_manager.vip_names.get(vip_type, vip_type)}</b>\n"
            message += f"   📊 تخفیف: {percentage}%\n"
            message += f"   ⏰ از: {start_date} تا {end_date}\n"
            message += f"   📝 دلیل: {reason}\n"
            message += f"   🆔 کد: <code>{discount['id']}</code>\n\n"
        
        self.bot.send_message(uid, message)
    
    def show_discount_stats(self, uid):
        discounts = self.discount_manager.get_all_discounts()
        
        stats = {
            'total': len(discounts),
            'by_type': {},
            'active': 0,
            'expired': 0
        }
        
        now = datetime.datetime.now()
        
        for discount in discounts:
            vip_type = discount['vip_type']
            if vip_type not in stats['by_type']:
                stats['by_type'][vip_type] = 0
            stats['by_type'][vip_type] += 1
            
            end_date = datetime.datetime.fromisoformat(discount['end_date'].replace('Z', '+00:00'))
            if now > end_date:
                stats['expired'] += 1
            else:
                stats['active'] += 1
        
        message = "📊 <b>آمار تخفیف‌ها</b>\n\n"
        message += f"📈 تعداد کل تخفیف‌ها: {stats['total']}\n"
        message += f"✅ تخفیف‌های فعال: {stats['active']}\n"
        message += f"❌ تخفیف‌های منقضی: {stats['expired']}\n\n"
        
        if stats['by_type']:
            message += "<b>توزیع بر اساس نوع VIP:</b>\n"
            for vip_type, count in stats['by_type'].items():
                vip_name = self.vip_manager.vip_names.get(vip_type, vip_type)
                message += f"• {vip_name}: {count} تخفیف\n"
        
        self.bot.send_message(uid, message)
    
    def start_create_event(self, uid):
        self.admin_states[uid] = {
            'state': 'waiting_for_event_name',
            'data': {}
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, "🎪 <b>ایجاد رویداد جدید</b>\n\nلطفا نام رویداد را وارد کنید:", reply_markup=markup)
    
    def process_event_name(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        self.admin_states[uid]['data']['name'] = text
        self.admin_states[uid]['state'] = 'waiting_for_event_description'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون توضیح", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ نام رویداد: {text}\n\nلطفا توضیح رویداد را وارد کنید:", reply_markup=markup)
    
    def process_event_description(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        description = text if text != "بدون توضیح" else ""
        
        self.admin_states[uid]['data']['description'] = description
        self.admin_states[uid]['state'] = 'waiting_for_event_dates'
        
        today = datetime.date.today()
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("امروز تا فردا", "امروز تا هفته آینده")
        markup.add("امروز تا ماه آینده", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ توضیح رویداد: {description or 'بدون توضیح'}\n\nلطفا بازه زمانی رویداد را انتخاب کنید:", reply_markup=markup)
    
    def process_event_dates(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        today = datetime.date.today()
        
        if text == "امروز تا فردا":
            start_date = today
            end_date = today + datetime.timedelta(days=1)
        elif text == "امروز تا هفته آینده":
            start_date = today
            end_date = today + datetime.timedelta(days=7)
        elif text == "امروز تا ماه آینده":
            start_date = today
            end_date = today + datetime.timedelta(days=30)
        else:
            try:
                dates = text.split('-')
                if len(dates) != 2:
                    raise ValueError
                
                start_str, end_str = dates
                start_date = datetime.datetime.strptime(start_str.strip(), '%Y/%m/%d').date()
                end_date = datetime.datetime.strptime(end_str.strip(), '%Y/%m/%d').date()
                
                if start_date >= end_date:
                    raise ValueError
            except:
                self.bot.send_message(uid, "❌ فرمت تاریخ نامعتبر است.")
                return
        
        self.admin_states[uid]['data']['start_date'] = start_date.isoformat()
        self.admin_states[uid]['data']['end_date'] = end_date.isoformat()
        self.admin_states[uid]['state'] = 'waiting_for_event_vip_plans'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون پلن ویژه", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ بازه زمانی: {start_date} تا {end_date}\n\nلطفا پلن‌های VIP ویژه رویداد را به صورت JSON وارد کنید:", reply_markup=markup)
    
    def process_event_vip_plans(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        data = self.admin_states[uid]['data']
        
        if text == "بدون پلن ویژه":
            vip_plans = []
        else:
            try:
                vip_plans = json.loads(text)
                if not isinstance(vip_plans, list):
                    raise ValueError
            except:
                self.bot.send_message(uid, "❌ فرمت JSON نامعتبر است.")
                return
        
        success = self.event_manager.create_event(
            data['name'],
            data['description'],
            data['start_date'],
            data['end_date'],
            vip_plans,
            uid
        )
        
        if success:
            self.bot.send_message(uid, f"✅ رویداد '{data['name']}' با موفقیت ایجاد شد.", reply_markup=self.kb_admin_main())
        else:
            self.bot.send_message(uid, "❌ خطا در ایجاد رویداد.", reply_markup=self.kb_admin_main())
        
        del self.admin_states[uid]
    
    def show_active_events_admin(self, uid):
        events = self.event_manager.get_active_events()
        
        if not events:
            self.bot.send_message(uid, "📭 هیچ رویداد فعالی وجود ندارد.")
            return
        
        message = "🎪 <b>رویدادهای فعال</b>\n\n"
        
        for i, event in enumerate(events, 1):
            start_date = datetime.datetime.fromisoformat(event['start_date'].replace('Z', '+00:00')).strftime('%Y/%m/%d')
            end_date = datetime.datetime.fromisoformat(event['end_date'].replace('Z', '+00:00')).strftime('%Y/%m/%d')
            
            message += f"<b>{i}. {event['event_name']}</b>\n"
            message += f"   📝 {event['description'] or 'بدون توضیح'}\n"
            message += f"   ⏰ از: {start_date} تا {end_date}\n"
            message += f"   🎁 پلن‌های ویژه: {len(event['vip_plans'])}\n"
            message += f"   🆔 کد: <code>{event['id']}</code>\n\n"
        
        self.bot.send_message(uid, message)
    
    def start_set_maintenance(self, uid):
        self.admin_states[uid] = {
            'state': 'waiting_for_maintenance_mode',
            'data': {}
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("0 - غیرفعال", "1 - فقط غیر-VIP مسدود")
        markup.add("2 - همه مسدود", "❌ لغو")
        
        self.bot.send_message(uid, "🔧 <b>تنظیم حالت تعمیر</b>\n\nلطفا حالت تعمیر را انتخاب کنید:", reply_markup=markup)
    
    def process_maintenance_mode(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        mode_map = {
            "0 - غیرفعال": 0,
            "1 - فقط غیر-VIP مسدود": 1,
            "2 - همه مسدود": 2
        }
        
        mode = mode_map.get(text)
        if mode is None:
            self.bot.send_message(uid, "❌ حالت نامعتبر است.")
            return
        
        self.admin_states[uid]['data']['mode'] = mode
        self.admin_states[uid]['state'] = 'waiting_for_maintenance_vip_access'
        
        if mode == 0:
            success, message = self.maintenance_manager.set_maintenance_mode(
                mode, 1, "", None, None, uid
            )
            
            if success:
                self.bot.send_message(uid, message, reply_markup=self.kb_admin_main())
            else:
                self.bot.send_message(uid, f"❌ {message}", reply_markup=self.kb_admin_main())
            
            del self.admin_states[uid]
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ بله - VIP دسترسی دارند", "❌ خیر - VIP هم مسدود هستند")
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, f"✅ حالت تعمیر: {'غیرفعال' if mode == 0 else 'فعال'}\n\nآیا کاربران VIP در حین تعمیر دسترسی داشته باشند؟", reply_markup=markup)
    
    def process_maintenance_vip_access(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        vip_access = 1 if text == "✅ بله - VIP دسترسی دارند" else 0
        
        self.admin_states[uid]['data']['vip_access'] = vip_access
        self.admin_states[uid]['state'] = 'waiting_for_maintenance_reason'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون دلیل", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ دسترسی VIP: {'✅ دارند' if vip_access == 1 else '❌ ندارند'}\n\nلطفا دلیل تعمیر را وارد کنید:", reply_markup=markup)
    
    def process_maintenance_reason(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        reason = text if text != "بدون دلیل" else ""
        
        self.admin_states[uid]['data']['reason'] = reason
        self.admin_states[uid]['state'] = 'waiting_for_maintenance_dates'
        
        today = datetime.datetime.now()
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("۱ ساعت", "۲۴ ساعت")
        markup.add("بدون محدودیت زمانی", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ دلیل تعمیر: {reason or 'بدون دلیل'}\n\nلطفا مدت زمان تعمیر را انتخاب کنید:", reply_markup=markup)
    
    def process_maintenance_dates(self, uid, text):
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        now = datetime.datetime.now()
        
        if text == "بدون محدودیت زمانی":
            start_time = None
            end_time = None
        elif text == "۱ ساعت":
            start_time = now
            end_time = now + datetime.timedelta(hours=1)
        elif text == "۲۴ ساعت":
            start_time = now
            end_time = now + datetime.timedelta(hours=24)
        else:
            self.bot.send_message(uid, "❌ گزینه نامعتبر است.")
            return
        
        data = self.admin_states[uid]['data']
        
        success, message = self.maintenance_manager.set_maintenance_mode(
            data['mode'],
            data['vip_access'],
            data['reason'],
            start_time.isoformat() if start_time else None,
            end_time.isoformat() if end_time else None,
            uid
        )
        
        if success:
            self.bot.send_message(uid, message, reply_markup=self.kb_admin_main())
        else:
            self.bot.send_message(uid, f"❌ {message}", reply_markup=self.kb_admin_main())
        
        del self.admin_states[uid]
    
    def show_maintenance_status(self, uid):
        settings = self.db.get_maintenance_settings()
        
        if settings['maintenance_mode'] == 0:
            info_text = "🟢 حالت تعمیر: غیرفعال"
        else:
            mode_text = {
                1: "🟡 حالت تعمیر: فعال (فقط غیر-VIP مسدود)",
                2: "🔴 حالت تعمیر: فعال (همه کاربران مسدود)"
            }.get(settings['maintenance_mode'], "⚫ حالت نامشخص")
            
            vip_access = "✅ دارند" if settings['vip_access_during_maintenance'] == 1 else "❌ ندارند"
            reason = settings['reason'] or "بدون دلیل مشخص"
            
            info_text = f"""
{mode_text}
👥 دسترسی VIP: {vip_access}
📝 دلیل: {reason}
            """
            
            if settings['start_time'] and settings['end_time']:
                try:
                    start_str = datetime.datetime.fromisoformat(settings['start_time'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                    end_str = datetime.datetime.fromisoformat(settings['end_time'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                    info_text += f"\n⏰ زمان: {start_str} تا {end_str}"
                except:
                    pass
        
        self.bot.send_message(uid, info_text)
    
    def disable_maintenance_mode(self, uid):
        success, message = self.maintenance_manager.disable_maintenance()
        
        if success:
            self.bot.send_message(uid, message, reply_markup=self.kb_admin_main())
        else:
            self.bot.send_message(uid, f"❌ {message}", reply_markup=self.kb_admin_main())
    
    def handle_vip_purchase(self, uid, vip_type):
        user = self.db.get_user(uid)
        if not user:
            return
        
        final_price, discount_percentage, original_price = self.vip_manager.get_final_price(vip_type)
        
        if user['coins'] < final_price:
            self.bot.send_message(uid, f"❌ سکه کافی ندارید!\nنیاز: {final_price:,} سکه\nموجودی: {user['coins']:,} سکه")
            return
        
        user['coins'] -= final_price
        
        vip_end = user.get('vip_end', 0)
        now = time.time()
        if vip_end < now:
            vip_end = now
        user['vip_end'] = vip_end + self.vip_manager.vip_durations.get(vip_type, 0)
        
        self.db.save_user(uid, user)
        
        vip_name = self.vip_manager.vip_names.get(vip_type, vip_type)
        expiry_date = datetime.datetime.fromtimestamp(user['vip_end']).strftime('%Y-%m-%d')
        
        message = f"""
✅ <b>خرید موفق!</b>

🎖 شما {vip_name} VIP خریداری کردید.
💰 مبلغ پرداختی: {final_price:,} سکه
📅 تاریخ انقضا: {expiry_date}
        """
        
        if discount_percentage > 0:
            message += f"\n🎁 تخفیف اعمال شده: {discount_percentage}% (صرفه‌جویی: {original_price - final_price:,} سکه)"
        
        self.bot.send_message(uid, message)
    
    def run(self):
        print("=" * 60)
        print("🛡️  Shadow Titan v42.2 - Ultimate Management Edition")
        print("=" * 60)
        print("✅ سیستم مدیریت تخفیف: فعال")
        print("✅ سیستم مدیریت رویداد: فعال")
        print("✅ سیستم مدیریت تعمیر: فعال")
        print("✅ کنترل دسترسی VIP: کامل")
        print("✅ قیمت‌گذاری پویا: فعال")
        print("=" * 60)
        
        try:
            web_thread = Thread(target=run_web, daemon=True)
            web_thread.start()
            print("🌐 وب سرور: فعال (پورت 8080)")
            
            print("🤖 در حال اتصال به تلگرام...")
            self.bot.polling(none_stop=True, timeout=60)
            
        except Exception as e:
            logger.error(f"ربات متوقف شد: {e}")
            print(f"❌ خطا: {e}")
            
            print("🔄 در حال تلاش برای بازیابی...")
            time.sleep(5)
            self.run()

# ==========================================
# اجرای ربات
# ==========================================
if __name__ == "__main__":
    for folder in ['backups', 'logs']:
        if not os.path.exists(folder):
            os.makedirs(folder, mode=0o700)
    
    sensitive_files = ['secure_chat.db', 'encryption.key', 'shadow_titan.log']
    for file in sensitive_files:
        if os.path.exists(file):
            try:
                os.chmod(file, 0o600)
            except:
                pass
    
    bot = ShadowTitanBotEnhanced()
    bot.run()
