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
import schedule

# ==========================================
# سیستم لاگ و وب‌سرور پیشرفته
# ==========================================
logging.basicConfig(
    filename='shadow_titan.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s | IP: %(ip)s | User: %(user)s',
    style='%'
)
logger = logging.getLogger("ShadowTitan")

# فیلتر لاگ برای حذف اطلاعات حساس
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        record.ip = getattr(record, 'ip', 'N/A')
        record.user = getattr(record, 'user', 'N/A')
        
        # حذف توکن‌ها و اطلاعات حساس از لاگ
        message = record.getMessage()
        message = re.sub(r'token=[^&\s]+', 'token=***', message)
        message = re.sub(r'password=[^&\s]+', 'password=***', message)
        message = re.sub(r'\b\d{10,}\b', '***', message)  # اعداد طولانی
        
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
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }
                h1 { text-align: center; margin-bottom: 30px; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin: 30px 0; }
                .stat-box { background: rgba(255,255,255,0.2); padding: 20px; border-radius: 10px; text-align: center; }
                .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
                .online { background: #10B981; }
                .maintenance { background: #F59E0B; }
                .offline { background: #EF4444; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ Shadow Titan v42.2</h1>
                <p><strong>Ultimate VIP & Event Management System</strong></p>
                <div class="status online">🟢 Status: Online & Active</div>
                <div class="stats">
                    <div class="stat-box">🚀 Version: 42.2</div>
                    <div class="stat-box">🎖 VIP Management: Full Control</div>
                    <div class="stat-box">💰 Dynamic Pricing</div>
                    <div class="stat-box">🎪 Event System</div>
                </div>
                <p>🤖 Advanced Persian Chat Bot with Full Management</p>
                <p>🎯 Real-time Discounts & Promotions</p>
                <p>🔔 Event Creation & Management</p>
            </div>
        </body>
    </html>
    """

def run_web():
    app.run(host='0.0.0.0', port=8080, threaded=True)

# ==========================================
# سیستم رمزنگاری پیشرفته (با fallback برای cryptography)
# ==========================================
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("⚠️ cryptography library not available, using simple encryption")

class AdvancedEncryption:
    def __init__(self):
        self.key_file = "encryption.key"
        
        if CRYPTOGRAPHY_AVAILABLE:
            self.key = self.load_or_generate_key_cryptography()
            self.fernet = Fernet(self.key)
            self.use_cryptography = True
            print("✅ Using cryptography library for encryption")
        else:
            self.key = self.load_or_generate_key_simple()
            self.use_cryptography = False
            print("⚠️ Using simple XOR encryption (for development only)")
            
    def load_or_generate_key_cryptography(self):
        """بارگذاری یا تولید کلید رمزنگاری با cryptography"""
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            return key
    
    def load_or_generate_key_simple(self):
        """بارگذاری یا تولید کلید ساده"""
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            # تولید کلید ساده 32 بایتی
            key = os.urandom(32)
            with open(self.key_file, "wb") as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)
            return key
    
    def encrypt_data(self, data):
        """رمزنگاری داده‌ها"""
        try:
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)
            
            if self.use_cryptography and CRYPTOGRAPHY_AVAILABLE:
                encrypted = self.fernet.encrypt(data.encode())
                return base64.urlsafe_b64encode(encrypted).decode()
            else:
                # رمزنگاری ساده XOR (فقط برای توسعه)
                data_bytes = data.encode()
                key_bytes = self.key[:len(data_bytes)] if len(data_bytes) < len(self.key) else self.key
                encrypted = bytes([data_bytes[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(data_bytes))])
                return base64.urlsafe_b64encode(encrypted).decode()
                
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return data
    
    def decrypt_data(self, encrypted_data):
        """رمزگشایی داده‌ها"""
        try:
            if self.use_cryptography and CRYPTOGRAPHY_AVAILABLE:
                encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
                decrypted = self.fernet.decrypt(encrypted).decode()
            else:
                # رمزگشایی ساده XOR
                encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
                key_bytes = self.key[:len(encrypted)] if len(encrypted) < len(self.key) else self.key
                decrypted = bytes([encrypted[i] ^ key_bytes[i % len(key_bytes)] for i in range(len(encrypted))]).decode()
            
            try:
                return json.loads(decrypted)
            except:
                return decrypted
                
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_data
    
    def hash_password(self, password, salt=None):
        """هش کردن رمز عبور"""
        if CRYPTOGRAPHY_AVAILABLE:
            if salt is None:
                salt = os.urandom(32)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return key.decode(), salt.hex()
        else:
            # هش ساده با SHA256
            if salt is None:
                salt = os.urandom(16).hex()
            hash_obj = hashlib.sha256((password + salt).encode())
            return hash_obj.hexdigest(), salt

# ==========================================
# سیستم دیتابیس امن SQLite با رمزنگاری
# ==========================================
class SecureDatabase:
    def __init__(self):
        self.encryption = AdvancedEncryption()
        self.db_file = "secure_chat.db"
        self.backup_dir = "backups"
        self.init_database()
        self.init_backup_system()
        
    def init_database(self):
        """ایجاد جداول دیتابیس"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # جدول کاربران با داده‌های رمزنگاری شده
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
        
        # جدول VIP ها
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
        
        # جدول پیام‌های ناشناس
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
        
        # جدول چت‌های فعال
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_chats (
                user1_id TEXT PRIMARY KEY,
                user2_id TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user1_id) REFERENCES users (user_id),
                FOREIGN KEY (user2_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول ماموریت‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                description TEXT,
                mission_type TEXT,
                target_value INTEGER,
                reward_type TEXT,
                reward_value TEXT,
                is_daily INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # جدول گزارشات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id TEXT,
                reported_id TEXT,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reporter_id) REFERENCES users (user_id),
                FOREIGN KEY (reported_id) REFERENCES users (user_id)
            )
        ''')
        
        # جدول ادمین‌ها با احراز هویت دو مرحله‌ای
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id TEXT PRIMARY KEY,
                encrypted_password TEXT,
                salt TEXT,
                permissions TEXT DEFAULT 'basic',
                two_factor_enabled INTEGER DEFAULT 0,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول لاگ امنیتی
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول جدید: تخفیف‌ها
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
        
        # جدول جدید: رویدادها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT,
                description TEXT,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                vip_plans TEXT, -- JSON containing special VIP plans for this event
                is_active INTEGER DEFAULT 1,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول جدید: تنظیمات تعمیر
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                maintenance_mode INTEGER DEFAULT 0, -- 0: off, 1: only non-VIP blocked, 2: all users blocked
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
        
        # ایجاد ایندکس‌ها برای سرعت بیشتر
        self.create_indexes()
    
    def create_indexes(self):
        """ایجاد ایندکس برای عملکرد بهتر"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_vip ON users(vip_end)",
            "CREATE INDEX IF NOT EXISTS idx_users_coins ON users(coins)",
            "CREATE INDEX IF NOT EXISTS idx_messages_receiver ON anonymous_messages(receiver_id, is_read)",
            "CREATE INDEX IF NOT EXISTS idx_active_chats_user1 ON active_chats(user1_id)",
            "CREATE INDEX IF NOT EXISTS idx_active_chats_user2 ON active_chats(user2_id)",
            "CREATE INDEX IF NOT EXISTS idx_security_logs_user ON security_logs(user_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status)",
            "CREATE INDEX IF NOT EXISTS idx_discounts_active ON discounts(is_active, end_date)",
            "CREATE INDEX IF NOT EXISTS idx_events_active ON events(is_active, end_date)",
            "CREATE INDEX IF NOT EXISTS idx_discounts_vip_type ON discounts(vip_type, is_active)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        conn.close()
    
    def init_backup_system(self):
        """ایجاد پوشه بکاپ"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, mode=0o700)
    
    def backup_database(self):
        """ایجاد بکاپ خودکار و رمزنگاری شده"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"backup_{timestamp}.db.enc")
            
            # خواندن دیتابیس
            with open(self.db_file, 'rb') as f:
                db_data = f.read()
            
            # رمزنگاری بکاپ
            encrypted_backup = self.encryption.encrypt_data(db_data.decode() if isinstance(db_data, bytes) else db_data)
            
            # ذخیره بکاپ
            with open(backup_file, 'wb') as f:
                f.write(encrypted_backup.encode() if isinstance(encrypted_backup, str) else encrypted_backup)
            
            # حذف بکاپ‌های قدیمی (نگه‌داری 7 روز آخر)
            self.cleanup_old_backups(days=7)
            
            logger.info(f"Backup created: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return False
    
    def cleanup_old_backups(self, days=7):
        """پاک‌سازی بکاپ‌های قدیمی"""
        try:
            cutoff = time.time() - (days * 24 * 3600)
            for filename in os.listdir(self.backup_dir):
                filepath = os.path.join(self.backup_dir, filename)
                if os.path.getmtime(filepath) < cutoff:
                    os.remove(filepath)
                    logger.info(f"Removed old backup: {filename}")
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
    
    def restore_backup(self, backup_file):
        """بازیابی از بکاپ"""
        try:
            with open(backup_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.encryption.decrypt_data(encrypted_data.decode() if isinstance(encrypted_data, bytes) else encrypted_data)
            
            # ایجاد کپی از دیتابیس فعلی
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            old_db = f"{self.db_file}.old.{timestamp}"
            os.rename(self.db_file, old_db)
            
            # نوشتن دیتابیس بازیابی شده
            with open(self.db_file, 'wb') as f:
                f.write(decrypted_data.encode() if isinstance(decrypted_data, str) else decrypted_data)
            
            logger.info(f"Database restored from {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Restore error: {e}")
            return False
    
    def get_connection(self):
        """ایجاد connection به دیتابیس"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # برای دسترسی به ستون‌ها با نام
        return conn
    
    # متدهای اصلی برای کاربران
    def save_user(self, user_id, user_data):
        """ذخیره کاربر در دیتابیس امن"""
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
        """دریافت اطلاعات کاربر"""
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
            
            # افزودن فیلدهای دیتابیس
            user_data['vip_end'] = row['vip_end']
            user_data['coins'] = row['coins']
            user_data['total_referrals'] = row['total_referrals']
            user_data['warns'] = row['warns']
            user_data['is_banned'] = row['is_banned']
            user_data['ban_reason'] = row['ban_reason']
            
            return user_data
        return None
    
    def update_user_field(self, user_id, field, value):
        """به‌روزرسانی فیلد خاص کاربر"""
        user = self.get_user(user_id)
        if user:
            user[field] = value
            self.save_user(user_id, user)
            return True
        return False
    
    def get_all_users(self, limit=1000):
        """دریافت همه کاربران (برای ادمین)"""
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

    # متدهای جدید برای تخفیف‌ها
    def add_discount(self, vip_type, discount_percentage, start_date, end_date, reason, created_by):
        """افزودن تخفیف جدید"""
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
        """حذف تخفیف"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE discounts SET is_active = 0 WHERE id = ?', (discount_id,))
        conn.commit()
        conn.close()
        return True
    
    def get_active_discounts(self, vip_type=None):
        """دریافت تخفیف‌های فعال"""
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
        """دریافت تخفیف فعال برای نوع VIP"""
        discounts = self.get_active_discounts(vip_type)
        if discounts:
            # بازگشت بزرگترین تخفیف
            return max(discounts, key=lambda x: x['discount_percentage'])
        return None

    # متدهای جدید برای رویدادها
    def add_event(self, event_name, description, start_date, end_date, vip_plans_json, created_by):
        """افزودن رویداد جدید"""
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
        """دریافت رویدادهای فعال"""
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
            # تبدیل JSON به دیکشنری
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
        """دریافت رویداد بر اساس ID"""
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

    # متدهای جدید برای تنظیمات تعمیر
    def get_maintenance_settings(self):
        """دریافت تنظیمات تعمیر فعلی"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM maintenance_settings ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        
        # اگر تنظیماتی وجود نداشت، تنظیمات پیش‌فرض
        return {
            'maintenance_mode': 0,
            'vip_access_during_maintenance': 1,
            'reason': '',
            'start_time': None,
            'end_time': None
        }
    
    def update_maintenance_settings(self, maintenance_mode, vip_access, reason, start_time, end_time, created_by):
        """به‌روزرسانی تنظیمات تعمیر"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # غیرفعال کردن همه تنظیمات قبلی
        cursor.execute('UPDATE maintenance_settings SET is_active = 0 WHERE is_active = 1')
        
        # افزودن تنظیمات جدید
        cursor.execute('''
            INSERT INTO maintenance_settings 
            (maintenance_mode, vip_access_during_maintenance, reason, start_time, end_time, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (maintenance_mode, vip_access, reason, start_time, end_time, created_by))
        
        conn.commit()
        conn.close()
        return True
    
    def disable_maintenance(self):
        """غیرفعال کردن حالت تعمیر"""
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
        
        # محدودیت‌های مختلف
        self.limits = {
            'general': {'limit': 30, 'window': 60},  # 30 درخواست در دقیقه
            'message': {'limit': 10, 'window': 10},  # 10 پیام در 10 ثانیه
            'search': {'limit': 5, 'window': 30},    # 5 جستجو در 30 ثانیه
            'vip': {'limit': 100, 'window': 60},     # VIP ها محدودیت بیشتر
        }
        
        # لیست IP های بلاک شده
        self.blocked_ips = {}
        
    def check_rate_limit(self, user_id, action='general', ip=None):
        """بررسی Rate Limit"""
        with self.lock:
            now = time.time()
            
            # چک IP بلاک شده
            if ip and ip in self.blocked_ips:
                block_until = self.blocked_ips[ip]
                if now < block_until:
                    return False, f"IP blocked until {datetime.datetime.fromtimestamp(block_until).strftime('%H:%M:%S')}"
                else:
                    del self.blocked_ips[ip]
            
            # دریافت محدودیت مناسب
            limit_info = self.limits.get(action, self.limits['general'])
            limit = limit_info['limit']
            window = limit_info['window']
            
            key = f"{user_id}:{action}"
            
            if key not in self.requests:
                self.requests[key] = []
            
            # حذف درخواست‌های قدیمی
            self.requests[key] = [req_time for req_time in self.requests[key] 
                                 if now - req_time < window]
            
            if len(self.requests[key]) >= limit:
                # بلاک IP در صورت تکرار
                if ip and action == 'general':
                    self.blocked_ips[ip] = now + 300  # بلاک 5 دقیقه‌ای
                    logger.warning(f"IP {ip} blocked for 5 minutes due to rate limit violation")
                
                remaining_time = window - (now - self.requests[key][0])
                return False, f"Rate limit exceeded. Try again in {int(remaining_time)} seconds"
            
            self.requests[key].append(now)
            return True, "OK"
    
    def cleanup_old_requests(self):
        """پاک‌سازی درخواست‌های قدیمی"""
        with self.lock:
            now = time.time()
            keys_to_delete = []
            
            for key, timestamps in self.requests.items():
                self.requests[key] = [t for t in timestamps if now - t < 3600]  # 1 ساعت
                if not self.requests[key]:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.requests[key]
            
            # پاک‌سازی IP های بلاک شده قدیمی
            ips_to_delete = [ip for ip, until in self.blocked_ips.items() 
                           if now > until]
            for ip in ips_to_delete:
                del self.blocked_ips[ip]

# ==========================================
# هوش مصنوعی فارسی محلی
# ==========================================
class PersianAI:
    def __init__(self):
        # دیکشنری‌های فارسی برای تشخیص محتوا
        self.bad_words_fa = self.load_persian_dictionary()
        self.patterns = self.load_patterns()
        
    def load_persian_dictionary(self):
        """بارگذاری دیکشنری کلمات نامناسب فارسی"""
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
        """بارگذاری الگوهای تشخیص"""
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
        """آنالیز متن فارسی"""
        if not text or len(text.strip()) < 3:
            return {'risk': 0, 'categories': []}
        
        text_lower = text.lower()
        risk_score = 0
        categories = []
        
        # بررسی فحش
        for category, words in self.bad_words_fa.items():
            for word in words:
                if word in text_lower:
                    risk_score += 0.3
                    if category not in categories:
                        categories.append(category)
        
        # بررسی الگوها
        if re.search(self.patterns['phone'], text):
            risk_score += 0.2
            categories.append('شماره تماس')
        
        if re.search(self.patterns['email'], text):
            risk_score += 0.1
            categories.append('ایمیل')
        
        if re.search(self.patterns['link'], text):
            risk_score += 0.3
            categories.append('لینک')
        
        # بررسی الگوهای اسپم
        for pattern in self.patterns['spam_patterns']:
            if re.search(pattern, text_lower):
                risk_score += 0.4
                categories.append('اسپم/تبلیغ')
                break
        
        # بررسی طول متن (متن‌های خیلی طولانی ممکن اسپم باشند)
        if len(text) > 500:
            risk_score += 0.1
            categories.append('متن طولانی')
        
        # بررسی تکرار حروف
        repeated_chars = re.findall(r'(.)\1{3,}', text)
        if repeated_chars:
            risk_score += 0.2
            categories.append('تکرار حروف')
        
        # نرمال‌سازی امتیاز بین 0 تا 1
        risk_score = min(1.0, risk_score)
        
        return {
            'risk': risk_score,
            'categories': list(set(categories)),
            'is_safe': risk_score < 0.6,
            'needs_review': 0.3 <= risk_score < 0.6,
            'is_dangerous': risk_score >= 0.6
        }
    
    def contains_inappropriate_content(self, text):
        """بررسی سریع برای محتوای نامناسب"""
        analysis = self.analyze_text_persian(text)
        return analysis['is_dangerous'], analysis

# ==========================================
# سیستم مدیریت VIP و تخفیف‌ها
# ==========================================
class VIPManager:
    def __init__(self, db):
        self.db = db
        
        # قیمت‌های پایه VIP (قیمت‌های منطقی و متنوع)
        self.base_prices = {
            "week": 300,      # ۱ هفته
            "month": 1000,    # ۱ ماه
            "3month": 2500,   # ۳ ماه
            "6month": 4500,   # ۶ ماه
            "year": 7000,     # ۱ سال
            "christmas": 0    # رایگان در رویداد
        }
        
        # مدت‌های VIP به ثانیه
        self.vip_durations = {
            "week": 7 * 24 * 3600,
            "month": 30 * 24 * 3600,
            "3month": 90 * 24 * 3600,
            "6month": 180 * 24 * 3600,
            "year": 365 * 24 * 3600,
            "christmas": 90 * 24 * 3600
        }
        
        # نام‌های فارسی انواع VIP
        self.vip_names = {
            "week": "۱ هفته",
            "month": "۱ ماه",
            "3month": "۳ ماه",
            "6month": "۶ ماه",
            "year": "۱ سال",
            "christmas": "۳ ماه رایگان"
        }
        
        # ویژگی‌های VIP بر اساس سطح
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
        """محاسبه قیمت نهایی با احتساب تخفیف‌ها"""
        base_price = self.base_prices.get(vip_type, 0)
        
        if not apply_discounts or base_price == 0:  # اگر رایگان است
            return base_price, 0, base_price
        
        # دریافت تخفیف‌های فعال
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
        """دریافت همه پلن‌های VIP با تخفیف‌ها"""
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
            
            # افزودن ویژگی‌ها بر اساس نوع
            if vip_type in ["week", "month"]:
                plan['features'] = self.vip_features["basic"]
                plan['level'] = "basic"
            elif vip_type in ["3month"]:
                plan['features'] = self.vip_features["basic"] + self.vip_features["premium"]
                plan['level'] = "premium"
            else:  # 6month, year
                plan['features'] = self.vip_features["basic"] + self.vip_features["premium"] + self.vip_features["exclusive"]
                plan['level'] = "exclusive"
            
            plans.append(plan)
        
        return plans
    
    def get_event_vip_plans(self, event_vip_plans):
        """دریافت پلن‌های VIP ویژه رویداد"""
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
    
    def check_vip_expiry(self, user_id):
        """بررسی انقضای VIP و ارسال هشدار"""
        user = self.db.get_user(user_id)
        if not user:
            return None
        
        vip_end = user.get('vip_end', 0)
        if vip_end <= 0:
            return None
        
        now = time.time()
        days_left = int((vip_end - now) / (24 * 3600))
        
        # هشدارهای انقضا
        warning_days = [7, 3, 1]
        if days_left in warning_days:
            return self.create_expiry_warning(days_left, vip_end)
        
        # اگر VIP تمام شده
        if now > vip_end:
            return self.handle_vip_expiry(user_id)
        
        return None
    
    def create_expiry_warning(self, days_left, vip_end):
        """ایجاد پیام هشدار انقضا"""
        expiry_date = datetime.datetime.fromtimestamp(vip_end).strftime('%Y-%m-%d')
        
        message = f"""
⚠️ <b>هشدار انقضای VIP</b>

⏳ مدت VIP شما <b>{days_left} روز</b> دیگر به پایان می‌رسد!
📅 تاریخ انقضا: <b>{expiry_date}</b>

برای تمدید VIP:
1. به بخش 🎖 خرید VIP مراجعه کنید
2. از طرح‌های ویژه استفاده نمایید
3. با تمدید زودهنگام از تخفیف‌های ویژه بهره‌مند شوید

💎 <i>ویژگی‌های VIP را از دست ندهید!</i>
        """
        return message
    
    def handle_vip_expiry(self, user_id):
        """مدیریت پایان VIP"""
        user = self.db.get_user(user_id)
        if user:
            # حذف VIP
            user['vip_end'] = 0
            self.db.save_user(user_id, user)
            
            # ایجاد پیام اتمام
            message = """
🔚 <b>VIP شما به پایان رسید</b>

متأسفانه مدت VIP شما تمام شده است.

اما نگران نباشید! می‌توانید دوباره VIP بخرید و از مزایای آن استفاده کنید:

🎁 <b>پیشنهاد ویژه برای شما:</b>
• خرید مجدد VIP با <b>۲۰٪ تخفیف</b> (فقط ۲۴ ساعت)
• شرکت در قرعه‌کشی ماهانه VIP رایگان
• انجام ماموریت‌ها برای دریافت VIP رایگان

برای خرید مجدد به بخش 🎖 خرید VIP مراجعه کنید.
            """
            return message
        
        return None

# ==========================================
# سیستم مدیریت رویدادها
# ==========================================
class EventManager:
    def __init__(self, db):
        self.db = db
    
    def create_event(self, event_name, description, start_date, end_date, vip_plans, created_by):
        """ایجاد رویداد جدید"""
        # تبدیل vip_plans به JSON
        vip_plans_json = json.dumps(vip_plans, ensure_ascii=False)
        
        # ذخیره در دیتابیس
        return self.db.add_event(event_name, description, start_date, end_date, vip_plans_json, created_by)
    
    def get_active_events(self):
        """دریافت رویدادهای فعال"""
        return self.db.get_active_events()
    
    def is_event_active(self, event_id):
        """بررسی فعال بودن رویداد"""
        event = self.db.get_event_by_id(event_id)
        if not event:
            return False
        
        now = datetime.datetime.now()
        start_date = datetime.datetime.fromisoformat(event['start_date'].replace('Z', '+00:00'))
        end_date = datetime.datetime.fromisoformat(event['end_date'].replace('Z', '+00:00'))
        
        return start_date <= now <= end_date and event['is_active'] == 1
    
    def get_event_vip_plans(self, event_id):
        """دریافت پلن‌های VIP ویژه رویداد"""
        event = self.db.get_event_by_id(event_id)
        if event and self.is_event_active(event['id']):
            return event.get('vip_plans', [])
        return []

# ==========================================
# سیستم مدیریت تخفیف‌ها
# ==========================================
class DiscountManager:
    def __init__(self, db):
        self.db = db
    
    def add_discount(self, vip_type, discount_percentage, start_date, end_date, reason, created_by):
        """افزودن تخفیف جدید"""
        # اعتبارسنجی تخفیف
        if discount_percentage < 1 or discount_percentage > 99:
            return False, "درصد تخفیف باید بین ۱ تا ۹۹ باشد"
        
        if start_date >= end_date:
            return False, "تاریخ شروع باید قبل از تاریخ پایان باشد"
        
        # افزودن به دیتابیس
        success = self.db.add_discount(vip_type, discount_percentage, start_date, end_date, reason, created_by)
        if success:
            return True, "تخفیف با موفقیت اضافه شد"
        else:
            return False, "خطا در افزودن تخفیف"
    
    def get_all_discounts(self):
        """دریافت همه تخفیف‌ها"""
        return self.db.get_active_discounts()
    
    def remove_discount(self, discount_id):
        """حذف تخفیف"""
        return self.db.remove_discount(discount_id)
    
    def get_discount_stats(self):
        """دریافت آمار تخفیف‌ها"""
        discounts = self.get_all_discounts()
        
        stats = {
            'total': len(discounts),
            'by_type': {},
            'active': 0,
            'expired': 0
        }
        
        now = datetime.datetime.now()
        
        for discount in discounts:
            # شمارش بر اساس نوع VIP
            vip_type = discount['vip_type']
            if vip_type not in stats['by_type']:
                stats['by_type'][vip_type] = 0
            stats['by_type'][vip_type] += 1
            
            # بررسی انقضا
            end_date = datetime.datetime.fromisoformat(discount['end_date'].replace('Z', '+00:00'))
            if now > end_date:
                stats['expired'] += 1
            else:
                stats['active'] += 1
        
        return stats

# ==========================================
# سیستم مدیریت تعمیر و نگهداری
# ==========================================
class MaintenanceManager:
    def __init__(self, db):
        self.db = db
    
    def set_maintenance_mode(self, maintenance_mode, vip_access, reason, start_time, end_time, created_by):
        """تنظیم حالت تعمیر"""
        # اعتبارسنجی
        if maintenance_mode not in [0, 1, 2]:
            return False, "حالت تعمیر نامعتبر است"
        
        if vip_access not in [0, 1]:
            return False, "تنظیمات دسترسی VIP نامعتبر است"
        
        if start_time and end_time and start_time >= end_time:
            return False, "تاریخ شروع باید قبل از تاریخ پایان باشد"
        
        # ذخیره تنظیمات
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
        """غیرفعال کردن حالت تعمیر"""
        success = self.db.disable_maintenance()
        if success:
            return True, "حالت تعمیر غیرفعال شد"
        else:
            return False, "خطا در غیرفعال کردن حالت تعمیر"
    
    def check_access(self, user_id, is_vip):
        """بررسی دسترسی کاربر در حالت تعمیر"""
        settings = self.db.get_maintenance_settings()
        
        if settings['maintenance_mode'] == 0:
            return True, None  # دسترسی آزاد
        
        # حالت 1: فقط غیر-VIP مسدود هستند
        if settings['maintenance_mode'] == 1:
            if is_vip and settings['vip_access_during_maintenance'] == 1:
                return True, None
            else:
                return False, "ربات در حال تعمیر است. لطفاً بعداً تلاش کنید."
        
        # حالت 2: همه مسدود هستند
        if settings['maintenance_mode'] == 2:
            return False, "ربات در حال تعمیر است. لطفاً بعداً تلاش کنید."
        
        return True, None
    
    def get_maintenance_info(self):
        """دریافت اطلاعات حالت تعمیر"""
        settings = self.db.get_maintenance_settings()
        
        if settings['maintenance_mode'] == 0:
            return "🟢 حالت تعمیر: غیرفعال", settings
        
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
        
        return info_text, settings

# ==========================================
# ربات اصلی با قابلیت‌های مدیریتی کامل
# ==========================================
class ShadowTitanBotEnhanced:
    def __init__(self):
        # توکن ربات
        self.token = "8213706320:AAFnu2EgXqRf05dPuJE_RU0AlQcXQkNdRZI"
        self.owner = "8013245091"
        self.channel = "@ChatNaAnnouncements"
        self.support = "@its_alimo"
        
        # سیستم‌های پیشرفته
        self.db = SecureDatabase()
        self.rate_limiter = RateLimiter()
        self.persian_ai = PersianAI()
        self.vip_manager = VIPManager(self.db)
        self.event_manager = EventManager(self.db)
        self.discount_manager = DiscountManager(self.db)
        self.maintenance_manager = MaintenanceManager(self.db)
        
        # لیست ادمین‌ها
        self.admins = ["8013245091"]
        
        # کانفیگ
        self.bot = telebot.TeleBot(self.token, parse_mode="HTML")
        self.username = self.bot.get_me().username if self.bot.get_me() else "ShadowTitanBot"
        
        # Stateهای مدیریتی
        self.admin_states = {}  # {admin_id: state_data}
        
        # شروع سیستم‌ها
        self.register_handlers()
        self.start_background_tasks()
        
        logger.info("🤖 Shadow Titan v42.2 Ultimate Management Edition Started")
    
    def start_background_tasks(self):
        """شروع وظایف پس‌زمینه"""
        # بررسی انقضای VIP
        self.schedule_task(self.check_all_vip_expiry, hours=6)
        
        # پاک‌سازی کش
        self.schedule_task(self.rate_limiter.cleanup_old_requests, minutes=30)
        
        # بکاپ خودکار
        self.schedule_task(self.db.backup_database, hours=24)
        
        logger.info("✅ Background tasks started")
    
    def schedule_task(self, func, minutes=0, hours=0):
        """زمان‌بندی وظایف"""
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
        """بررسی انقضای VIP همه کاربران"""
        try:
            users = self.db.get_all_users()
            for user in users:
                if 'user_id' in user:
                    warning = self.vip_manager.check_vip_expiry(user['user_id'])
                    if warning:
                        try:
                            self.bot.send_message(user['user_id'], warning)
                        except:
                            pass
        except Exception as e:
            logger.error(f"VIP expiry check error: {e}")
    
    # ==========================================
    # کیبوردها و رابط کاربری
    # ==========================================
    def kb_main(self, uid):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        user = self.db.get_user(uid)
        is_vip = user and user.get('vip_end', 0) > time.time()
        
        # دکمه‌های اصلی
        markup.add("🛰 شروع چت ناشناس", "👤 پروفایل من")
        markup.add("📩 لینک ناشناس من", "📥 پیام‌های ناشناس")
        markup.add("🎡 گردونه شانس", "🎯 ماموریت روزانه")
        markup.add("👥 رفرال و دعوت", "🎖 خرید VIP")
        
        # دکمه‌های ویژه VIP
        if is_vip:
            markup.add("⭐ ویژگی‌های VIP", "🎁 هدیه ماهانه")
        
        # دکمه رویدادها
        active_events = self.event_manager.get_active_events()
        if active_events:
            markup.add("🎪 رویدادهای ویژه")
        
        markup.add("❓ راهنما")
        
        if uid in self.admins:
            markup.add("🛡️ پنل مدیریت")
        
        return markup
    
    def kb_admin_main(self):
        """کیبورد اصلی ادمین"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📊 آمار کامل", "👥 مدیریت کاربران")
        markup.add("🎖 مدیریت VIP", "💰 مدیریت تخفیف‌ها")
        markup.add("🎪 مدیریت رویدادها", "🔧 مدیریت تعمیر")
        markup.add("📁 مدیریت فایل‌ها", "🚫 مدیریت بن‌ها")
        markup.add("🔙 بازگشت به منو")
        return markup
    
    def kb_vip_management(self):
        """کیبورد مدیریت VIP"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📋 لیست VIP ها", callback_data="admin_list_vips"),
            types.InlineKeyboardButton("🎁 گیفت VIP", callback_data="admin_gift_vip")
        )
        markup.add(
            types.InlineKeyboardButton("📊 آمار فروش", callback_data="admin_vip_stats"),
            types.InlineKeyboardButton("⚙ تنظیمات قیمت", callback_data="admin_price_settings")
        )
        return markup
    
    def kb_discount_management(self):
        """کیبورد مدیریت تخفیف‌ها"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ افزودن تخفیف", callback_data="admin_add_discount"),
            types.InlineKeyboardButton("🗑 حذف تخفیف", callback_data="admin_remove_discount")
        )
        markup.add(
            types.InlineKeyboardButton("📋 لیست تخفیف‌ها", callback_data="admin_list_discounts"),
            types.InlineKeyboardButton("📊 آمار تخفیف‌ها", callback_data="admin_discount_stats")
        )
        markup.add(
            types.InlineKeyboardButton("🎯 تخفیف روی محصول خاص", callback_data="admin_specific_discount")
        )
        return markup
    
    def kb_event_management(self):
        """کیبورد مدیریت رویدادها"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ ایجاد رویداد", callback_data="admin_create_event"),
            types.InlineKeyboardButton("🗑 حذف رویداد", callback_data="admin_remove_event")
        )
        markup.add(
            types.InlineKeyboardButton("📋 رویدادهای فعال", callback_data="admin_active_events"),
            types.InlineKeyboardButton("➕ افزودن پلن ویژه", callback_data="admin_add_event_plan")
        )
        markup.add(
            types.InlineKeyboardButton("📊 آمار رویدادها", callback_data="admin_event_stats")
        )
        return markup
    
    def kb_maintenance_management(self):
        """کیبورد مدیریت تعمیر"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔧 تنظیم حالت تعمیر", callback_data="admin_set_maintenance"),
            types.InlineKeyboardButton("❌ غیرفعال کردن", callback_data="admin_disable_maintenance")
        )
        markup.add(
            types.InlineKeyboardButton("📊 وضعیت فعلی", callback_data="admin_maintenance_status"),
            types.InlineKeyboardButton("⚙ تنظیمات دسترسی", callback_data="admin_access_settings")
        )
        return markup
    
    # ==========================================
    # هندلرهای اصلی
    # ==========================================
    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start(msg):
            uid = str(msg.chat.id)
            
            # بررسی دسترسی در حالت تعمیر
            user = self.db.get_user(uid)
            is_vip = user and user.get('vip_end', 0) > time.time()
            has_access, error_msg = self.maintenance_manager.check_access(uid, is_vip)
            
            if not has_access:
                self.bot.send_message(uid, f"🚫 {error_msg}")
                return
            
            # بررسی Rate Limiting
            allowed, message = self.rate_limiter.check_rate_limit(uid, 'general')
            if not allowed:
                self.bot.send_message(uid, f"⏳ {message}")
                return
            
            payload = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else None
            
            # پردازش لینک‌های ویژه
            if payload:
                if payload.startswith('ref_'):
                    self.handle_referral(uid, payload[4:])
                elif payload.startswith('msg_'):
                    self.handle_anonymous_link(uid, payload[4:])
                elif payload.startswith('event_'):
                    self.handle_event_link(uid, payload[6:])
            
            # ثبت‌نام یا خوش‌آمدگویی
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
            
            # بررسی دسترسی در حالت تعمیر
            user = self.db.get_user(uid)
            is_vip = user and user.get('vip_end', 0) > time.time()
            has_access, error_msg = self.maintenance_manager.check_access(uid, is_vip)
            
            if not has_access:
                self.bot.send_message(uid, f"🚫 {error_msg}")
                return
            
            # بررسی Rate Limiting
            allowed, message = self.rate_limiter.check_rate_limit(uid, 'message')
            if not allowed:
                self.bot.send_message(uid, f"⏳ {message}")
                return
            
            # بررسی امنیتی
            is_dangerous, analysis = self.persian_ai.contains_inappropriate_content(text)
            if is_dangerous:
                self.handle_inappropriate_content(uid, analysis)
                return
            
            # پردازش دستورات مدیریتی
            if uid in self.admins:
                if text == "🛡️ پنل مدیریت":
                    self.show_admin_panel(uid)
                    return
                elif text == "🔙 بازگشت به منو":
                    self.bot.send_message(uid, "🏠 منوی اصلی", reply_markup=self.kb_main(uid))
                    return
                
                # بررسی stateهای مدیریتی
                if uid in self.admin_states:
                    state_handled = self.handle_admin_state(uid, text)
                    if state_handled:
                        return
            
            # پردازش دستورات کاربری
            self.handle_user_command(uid, text, user)
    
    def handle_admin_state(self, uid, text):
        """پردازش stateهای مدیریتی"""
        if uid not in self.admin_states:
            return False
        
        state_data = self.admin_states[uid]
        state = state_data.get('state')
        
        if state == 'waiting_for_discount_vip_type':
            self.process_discount_vip_type(uid, text)
            return True
        
        elif state == 'waiting_for_discount_percentage':
            self.process_discount_percentage(uid, text)
            return True
        
        elif state == 'waiting_for_discount_dates':
            self.process_discount_dates(uid, text)
            return True
        
        elif state == 'waiting_for_discount_reason':
            self.process_discount_reason(uid, text)
            return True
        
        elif state == 'waiting_for_event_name':
            self.process_event_name(uid, text)
            return True
        
        elif state == 'waiting_for_event_description':
            self.process_event_description(uid, text)
            return True
        
        elif state == 'waiting_for_event_dates':
            self.process_event_dates(uid, text)
            return True
        
        elif state == 'waiting_for_event_vip_plans':
            self.process_event_vip_plans(uid, text)
            return True
        
        elif state == 'waiting_for_maintenance_mode':
            self.process_maintenance_mode(uid, text)
            return True
        
        elif state == 'waiting_for_maintenance_vip_access':
            self.process_maintenance_vip_access(uid, text)
            return True
        
        elif state == 'waiting_for_maintenance_reason':
            self.process_maintenance_reason(uid, text)
            return True
        
        elif state == 'waiting_for_maintenance_dates':
            self.process_maintenance_dates(uid, text)
            return True
        
        return False
    
    def handle_user_command(self, uid, text, user):
        """پردازش دستورات کاربری"""
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
        
        elif text == "💰 مدیریت تخفیف‌ها":
            self.show_discount_management(uid)
        
        elif text == "🎪 مدیریت رویدادها":
            self.show_event_management(uid)
        
        elif text == "🔧 مدیریت تعمیر":
            self.show_maintenance_management(uid)
        
        else:
            self.bot.send_message(uid, "🤔 دستور نامعتبر است. لطفاً از دکمه‌های منو استفاده کنید.")
    
    # ==========================================
    # سیستم مدیریت تخفیف‌ها
    # ==========================================
    def show_discount_management(self, uid):
        """نمایش مدیریت تخفیف‌ها"""
        markup = self.kb_discount_management()
        self.bot.send_message(uid, "💰 <b>مدیریت تخفیف‌ها</b>\n\nلطفا عمل مورد نظر را انتخاب کنید:", reply_markup=markup)
    
    def start_add_discount(self, uid):
        """شروع فرآیند افزودن تخفیف"""
        self.admin_states[uid] = {
            'state': 'waiting_for_discount_vip_type',
            'data': {}
        }
        
        # نمایش انواع VIP برای انتخاب
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("۱ هفته", "۱ ماه", "۳ ماه", "۶ ماه", "۱ سال", "همه انواع")
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, "🎯 <b>افزودن تخفیف جدید</b>\n\nلطفا نوع VIP مورد نظر برای تخفیف را انتخاب کنید:", reply_markup=markup)
    
    def process_discount_vip_type(self, uid, text):
        """پردازش انتخاب نوع VIP برای تخفیف"""
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
            self.bot.send_message(uid, "❌ نوع VIP نامعتبر است. لطفا از دکمه‌ها استفاده کنید.")
            return
        
        self.admin_states[uid]['data']['vip_type'] = vip_type
        self.admin_states[uid]['state'] = 'waiting_for_discount_percentage'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, f"✅ نوع VIP: {text}\n\nلطفا درصد تخفیف را وارد کنید (۱ تا ۹۹):", reply_markup=markup)
    
    def process_discount_percentage(self, uid, text):
        """پردازش درصد تخفیف"""
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        try:
            percentage = int(text)
            if not 1 <= percentage <= 99:
                raise ValueError
        except:
            self.bot.send_message(uid, "❌ درصد تخفیف نامعتبر است. لطفا عددی بین ۱ تا ۹۹ وارد کنید.")
            return
        
        self.admin_states[uid]['data']['percentage'] = percentage
        self.admin_states[uid]['state'] = 'waiting_for_discount_dates'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("امروز تا فردا", "امروز تا هفته آینده")
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, f"✅ درصد تخفیف: {percentage}%\n\nلطفا بازه زمانی تخفیف را انتخاب کنید:", reply_markup=markup)
    
    def process_discount_dates(self, uid, text):
        """پردازش تاریخ‌های تخفیف"""
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
            self.bot.send_message(uid, "❌ گزینه نامعتبر است. لطفا از دکمه‌ها استفاده کنید.")
            return
        
        self.admin_states[uid]['data']['start_date'] = start_date.isoformat()
        self.admin_states[uid]['data']['end_date'] = end_date.isoformat()
        self.admin_states[uid]['state'] = 'waiting_for_discount_reason'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون دلیل", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ بازه زمانی: {start_date} تا {end_date}\n\nلطفا دلیل تخفیف را وارد کنید (یا 'بدون دلیل' را انتخاب کنید):", reply_markup=markup)
    
    def process_discount_reason(self, uid, text):
        """پردازش دلیل تخفیف"""
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
        
        # اگر تخفیف برای همه انواع است
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
        """نمایش لیست تخفیف‌ها"""
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
        """نمایش آمار تخفیف‌ها"""
        stats = self.discount_manager.get_discount_stats()
        
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
    
    # ==========================================
    # سیستم مدیریت رویدادها
    # ==========================================
    def show_event_management(self, uid):
        """نمایش مدیریت رویدادها"""
        markup = self.kb_event_management()
        self.bot.send_message(uid, "🎪 <b>مدیریت رویدادها</b>\n\nلطفا عمل مورد نظر را انتخاب کنید:", reply_markup=markup)
    
    def start_create_event(self, uid):
        """شروع فرآیند ایجاد رویداد"""
        self.admin_states[uid] = {
            'state': 'waiting_for_event_name',
            'data': {}
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("❌ لغو")
        
        self.bot.send_message(uid, "🎪 <b>ایجاد رویداد جدید</b>\n\nلطفا نام رویداد را وارد کنید:", reply_markup=markup)
    
    def process_event_name(self, uid, text):
        """پردازش نام رویداد"""
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        self.admin_states[uid]['data']['name'] = text
        self.admin_states[uid]['state'] = 'waiting_for_event_description'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون توضیح", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ نام رویداد: {text}\n\nلطفا توضیح رویداد را وارد کنید (یا 'بدون توضیح' را انتخاب کنید):", reply_markup=markup)
    
    def process_event_description(self, uid, text):
        """پردازش توضیح رویداد"""
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        description = text if text != "بدون توضیح" else ""
        
        self.admin_states[uid]['data']['description'] = description
        self.admin_states[uid]['state'] = 'waiting_for_event_dates'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("امروز تا فردا", "امروز تا هفته آینده")
        markup.add("امروز تا ماه آینده", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ توضیح رویداد: {description or 'بدون توضیح'}\n\nلطفا بازه زمانی رویداد را انتخاب کنید:", reply_markup=markup)
    
    def process_event_dates(self, uid, text):
        """پردازش تاریخ‌های رویداد"""
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
            self.bot.send_message(uid, "❌ گزینه نامعتبر است. لطفا از دکمه‌ها استفاده کنید.")
            return
        
        self.admin_states[uid]['data']['start_date'] = start_date.isoformat()
        self.admin_states[uid]['data']['end_date'] = end_date.isoformat()
        self.admin_states[uid]['state'] = 'waiting_for_event_vip_plans'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون پلن ویژه", "❌ لغو")
        
        example = json.dumps([
            {
                "type": "month",
                "name": "VIP ویژه رویداد",
                "special_price": 800,
                "original_price": 1000,
                "description": "پلن ویژه برای شرکت‌کنندگان رویداد",
                "features": ["ویژگی ۱", "ویژگی ۲"]
            }
        ], ensure_ascii=False, indent=2)
        
        self.bot.send_message(uid, f"✅ بازه زمانی: {start_date} تا {end_date}\n\nلطفا پلن‌های VIP ویژه رویداد را به صورت JSON وارد کنید (یا 'بدون پلن ویژه' را انتخاب کنید):\n\nمثال:\n{example}", reply_markup=markup)
    
    def process_event_vip_plans(self, uid, text):
        """پردازش پلن‌های VIP ویژه رویداد"""
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
                self.bot.send_message(uid, "❌ فرمت JSON نامعتبر است. لطفا مجدداً تلاش کنید.")
                return
        
        # ایجاد رویداد
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
        """نمایش رویدادهای فعال برای ادمین"""
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
    
    # ==========================================
    # سیستم مدیریت تعمیر
    # ==========================================
    def show_maintenance_management(self, uid):
        """نمایش مدیریت تعمیر"""
        markup = self.kb_maintenance_management()
        self.bot.send_message(uid, "🔧 <b>مدیریت تعمیر و نگهداری</b>\n\nلطفا عمل مورد نظر را انتخاب کنید:", reply_markup=markup)
    
    def start_set_maintenance(self, uid):
        """شروع فرآیند تنظیم حالت تعمیر"""
        self.admin_states[uid] = {
            'state': 'waiting_for_maintenance_mode',
            'data': {}
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("0 - غیرفعال", "1 - فقط غیر-VIP مسدود")
        markup.add("2 - همه مسدود", "❌ لغو")
        
        self.bot.send_message(uid, "🔧 <b>تنظیم حالت تعمیر</b>\n\nلطفا حالت تعمیر را انتخاب کنید:", reply_markup=markup)
    
    def process_maintenance_mode(self, uid, text):
        """پردازش حالت تعمیر"""
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
            self.bot.send_message(uid, "❌ حالت نامعتبر است. لطفا از دکمه‌ها استفاده کنید.")
            return
        
        self.admin_states[uid]['data']['mode'] = mode
        self.admin_states[uid]['state'] = 'waiting_for_maintenance_vip_access'
        
        if mode == 0:
            # اگر غیرفعال است، نیازی به ادامه نیست
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
        """پردازش دسترسی VIP"""
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        vip_access = 1 if text == "✅ بله - VIP دسترسی دارند" else 0
        
        self.admin_states[uid]['data']['vip_access'] = vip_access
        self.admin_states[uid]['state'] = 'waiting_for_maintenance_reason'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("بدون دلیل", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ دسترسی VIP: {'✅ دارند' if vip_access == 1 else '❌ ندارند'}\n\nلطفا دلیل تعمیر را وارد کنید (یا 'بدون دلیل' را انتخاب کنید):", reply_markup=markup)
    
    def process_maintenance_reason(self, uid, text):
        """پردازش دلیل تعمیر"""
        if text == "❌ لغو":
            del self.admin_states[uid]
            self.bot.send_message(uid, "❌ فرآیند لغو شد.", reply_markup=self.kb_admin_main())
            return
        
        reason = text if text != "بدون دلیل" else ""
        
        self.admin_states[uid]['data']['reason'] = reason
        self.admin_states[uid]['state'] = 'waiting_for_maintenance_dates'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("۱ ساعت", "۲۴ ساعت")
        markup.add("بدون محدودیت زمانی", "❌ لغو")
        
        self.bot.send_message(uid, f"✅ دلیل تعمیر: {reason or 'بدون دلیل'}\n\nلطفا مدت زمان تعمیر را انتخاب کنید:", reply_markup=markup)
    
    def process_maintenance_dates(self, uid, text):
        """پردازش مدت زمان تعمیر"""
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
        """نمایش وضعیت تعمیر"""
        info_text, settings = self.maintenance_manager.get_maintenance_info()
        self.bot.send_message(uid, info_text)
    
    def disable_maintenance_mode(self, uid):
        """غیرفعال کردن حالت تعمیر"""
        success, message = self.maintenance_manager.disable_maintenance()
        
        if success:
            self.bot.send_message(uid, message, reply_markup=self.kb_admin_main())
        else:
            self.bot.send_message(uid, f"❌ {message}", reply_markup=self.kb_admin_main())
    
    # ==========================================
    # نمایش پلن‌های VIP با تخفیف‌ها
    # ==========================================
    def show_vip_plans(self, uid):
        """نمایش پلن‌های VIP با تخفیف‌ها"""
        user = self.db.get_user(uid)
        coins = user.get('coins', 0) if user else 0
        
        # دریافت پلن‌های عادی با تخفیف
        normal_plans = self.vip_manager.get_vip_plans_with_discounts()
        
        # دریافت پلن‌های ویژه رویدادها
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
        
        # نمایش پلن‌های عادی
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
            for feature in plan['features'][:3]:  # فقط ۳ ویژگی اول
                message += f"\n{feature}"
            
            if plan['has_discount']:
                message += f"\n💰 قیمت اصلی: <s>{plan['original_price']:,}</s> ← {plan['final_price']:,} سکه"
            else:
                message += f"\n💰 قیمت: {plan['final_price']:,} سکه"
        
        # نمایش پلن‌های ویژه رویدادها
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
    
    # ==========================================
    # سایر متدها (مشابه قبل)
    # ==========================================
    def show_admin_panel(self, uid):
        """نمایش پنل مدیریت"""
        self.bot.send_message(uid, "🛡️ <b>پنل مدیریت پیشرفته</b>\n\nلطفا بخش مورد نظر را انتخاب کنید:", reply_markup=self.kb_admin_main())
    
    def show_vip_features(self, uid):
        """نمایش ویژگی‌های VIP"""
        user = self.db.get_user(uid)
        is_vip = user and user.get('vip_end', 0) > time.time()
        
        if is_vip:
            message = """
⭐ <b>ویژگی‌های VIP شما:</b>

<b>ویژگی‌های اصلی:</b>
✅ چت ناشناس نامحدود
✅ ارسال پیام ناشناس
✅ شرکت در گردونه شانس روزانه
✅ دسترسی به پروفایل پیشرفته

<b>ویژگی‌های ویژه:</b>
🎁 100 سکه هدیه ماهانه
🚀 اولویت در جستجوی چت
🎯 ماموریت‌های ویژه
📊 آمار پیشرفته پروفایل

<b>ویژگی‌های انحصاری:</b>
⭐ نماد VIP طلایی در کنار نام
⚡ سرعت چت 2 برابری
👑 دسترسی به چت خصوصی ادمین
📈 مشاهده آمار زنده ربات
            """
        else:
            message = """
🔓 <b>ویژگی‌های VIP</b>

با خرید VIP به ویژگی‌های فوق‌العاده‌ای دسترسی پیدا می‌کنید:

<b>ویژگی‌های اصلی (همه VIP ها):</b>
✅ چت ناشناس نامحدود
✅ ارسال پیام ناشناس
✅ شرکت در گردونه شانس روزانه
✅ دسترسی به پروفایل پیشرفته

<b>ویژگی‌های ویژه (VIP 3 ماه و بیشتر):</b>
🎁 100 سکه هدیه ماهانه
🚀 اولویت در جستجوی چت
🎯 ماموریت‌های ویژه
📊 آمار پیشرفته پروفایل
🔔 نوتیفیکیشن اختصاصی

<b>ویژگی‌های انحصاری (VIP 6 ماه و بیشتر):</b>
⭐ نماد VIP طلایی در کنار نام
⚡ سرعت چت 2 برابری
👑 دسترسی به چت خصوصی ادمین
📈 مشاهده آمار زنده ربات
🎪 ورود رایگان به همه رویدادها
🛡️ پشتیبانی VIP 24/7

برای مشاهده طرح‌های VIP روی «🎖 خرید VIP» کلیک کنید.
            """
        
        self.bot.send_message(uid, message)
    
    def handle_inappropriate_content(self, uid, analysis):
        """مدیریت محتوای نامناسب"""
        user = self.db.get_user(uid)
        if user:
            user['warns'] = user.get('warns', 0) + 1
            self.db.save_user(uid, user)
            
            if user['warns'] >= 3:
                self.ban_user(uid, "ارسال محتوای نامناسب مکرر")
            else:
                self.bot.send_message(uid, f"⚠️ <b>اخطار {user['warns']}/3</b>\n\nمحتوای نامناسب ممنوع است!")
    
    def ban_user(self, uid, reason):
        """بن کردن کاربر"""
        user = self.db.get_user(uid)
        if user:
            user['is_banned'] = 1
            user['ban_reason'] = reason
            self.db.save_user(uid, user)
            
            self.bot.send_message(uid, f"🚫 حساب شما بن شد!\nدلیل: {reason}\nپشتیبانی: {self.support}")
            
            logger.warning(f"User {uid} banned. Reason: {reason}")
    
    def register_new_user(self, uid):
        """ثبت‌نام کاربر جدید"""
        self.bot.send_message(uid, "🌟 <b>به Shadow Titan خوش آمدید!</b>\n\nلطفاً نام مستعار خود را وارد کنید:")
        
        user_data = {
            'name': '',
            'state': 'name',
            'vip_end': 0,
            'coins': 50,  # سکه هدیه ثبت‌نام
            'total_referrals': 0,
            'warns': 0,
            'created_at': time.time(),
            'is_banned': 0,
            'ban_reason': ''
        }
        self.db.save_user(uid, user_data)
    
    def welcome_back_user(self, uid, user):
        """خوش‌آمدگویی به کاربر بازگشته"""
        is_vip = user.get('vip_end', 0) > time.time()
        vip_status = "🎖 VIP" if is_vip else "⭐ عادی"
        
        # بررسی رویدادهای فعال
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
    
    def show_profile(self, uid, user):
        """نمایش پروفایل"""
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
        """نمایش رویدادهای ویژه"""
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
    
    # ==========================================
    # کال‌بک‌ها
    # ==========================================
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
        
        elif call.data == "insufficient_coins":
            self.bot.send_message(uid, "❌ سکه کافی ندارید! برای دریافت سکه می‌توانید:\n1. دوستان خود را دعوت کنید\n2. ماموریت‌های روزانه را انجام دهید\n3. در گردونه شانس شرکت کنید")
        
        elif call.data.startswith("admin_"):
            # برای سایر کال‌بک‌های ادمین
            self.bot.send_message(uid, f"این قابلیت به زودی اضافه خواهد شد. (کال‌بک: {call.data})")
        
        self.bot.answer_callback_query(call.id)
    
    def handle_vip_purchase(self, uid, vip_type):
        """پردازش خرید VIP"""
        user = self.db.get_user(uid)
        if not user:
            return
        
        final_price, discount_percentage, original_price = self.vip_manager.get_final_price(vip_type)
        
        if user['coins'] < final_price:
            self.bot.send_message(uid, f"❌ سکه کافی ندارید!\nنیاز: {final_price:,} سکه\nموجودی: {user['coins']:,} سکه")
            return
        
        # کسر سکه
        user['coins'] -= final_price
        
        # افزودن VIP
        vip_end = user.get('vip_end', 0)
        now = time.time()
        if vip_end < now:
            vip_end = now
        user['vip_end'] = vip_end + self.vip_manager.vip_durations.get(vip_type, 0)
        
        self.db.save_user(uid, user)
        
        # پیام موفقیت
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
    
    # ==========================================
    # اجرای ربات
    # ==========================================
    def run(self):
        """اجرای ربات"""
        print("=" * 60)
        print("🛡️  Shadow Titan v42.2 - Ultimate Management Edition")
        print("=" * 60)
        print("✅ سیستم مدیریت تخفیف: فعال")
        print("✅ سیستم مدیریت رویداد: فعال")
        print("✅ سیستم مدیریت تعمیر: فعال")
        print("✅ کنترل دسترسی VIP: کامل")
        print("✅ قیمت‌گذاری پویا: فعال")
        print("=" * 60)
        
        # ثبت هندلر کال‌بک
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback(call):
            self.callback_handler(call)
        
        try:
            # راه‌اندازی وب سرور
            web_thread = Thread(target=run_web, daemon=True)
            web_thread.start()
            print("🌐 وب سرور: فعال (پورت 8080)")
            
            # شروع ربات
            print("🤖 در حال اتصال به تلگرام...")
            self.bot.infinity_polling(skip_pending=True, timeout=60)
            
        except Exception as e:
            logger.error(f"ربات متوقف شد: {e}")
            print(f"❌ خطا: {e}")
            
            # تلاش برای بازیابی
            print("🔄 در حال تلاش برای بازیابی...")
            time.sleep(5)
            self.run()

# ==========================================
# اجرای ربات
# ==========================================
if __name__ == "__main__":
    # ایجاد پوشه‌های لازم
    for folder in ['backups', 'logs']:
        if not os.path.exists(folder):
            os.makedirs(folder, mode=0o700)
    
    # تنظیم مجوزهای امن برای فایل‌ها
    sensitive_files = ['secure_chat.db', 'encryption.key', 'shadow_titan.log']
    for file in sensitive_files:
        if os.path.exists(file):
            try:
                os.chmod(file, 0o600)
            except:
                pass
    
    # اجرای ربات
    bot = ShadowTitanBotEnhanced()
    bot.run()
