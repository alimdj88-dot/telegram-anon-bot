import telebot
from telebot import types
import json
import os
import time
from datetime import datetime, timedelta
import random
import hashlib
import threading
import asyncio
import string

# ==========================================
# تنظیمات اصلی - کاملاً قابل تنظیم
# ==========================================
TOKEN = "8213706320:AAFnu2EgXqRf05dPuJE_RU0AlQcXQkNdRZI"
OWNER_ID = "8013245091"  # آی‌دی ادمین اصلی
ADMINS = [OWNER_ID]  # لیست اولیه ادمین‌ها
SUPPORT_USERNAME = "@its_alimo"
CHANNEL_USERNAME = "@ChatNaAnnouncements"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================================
# سیستم فایل‌های دیتابیس
# ==========================================
class Database:
    def __init__(self):
        self.files = {
            'users': 'users.json',
            'admins': 'admins.json',
            'vip_plans': 'vip_plans.json',
            'settings': 'settings.json',
            'stats': 'stats.json',
            'transactions': 'transactions.json',
            'events': 'events.json',
            'discounts': 'discounts.json',
            'banned': 'banned.json',
            'backups': 'backups/'
        }
        
        # ایجاد پوشه‌ها
        if not os.path.exists('backups'):
            os.makedirs('backups')
        
        # ایجاد فایل‌ها اگر وجود ندارند
        self.init_files()
    
    def init_files(self):
        """ایجاد فایل‌های اولیه"""
        defaults = {
            'users': {},
            'admins': {
                'admins': ADMINS,
                'admin_passwords': {},
                'master_password': 'admin123',
                'permissions': {}
            },
            'vip_plans': {
                '1': {'name': 'VIP هفتگی', 'price': 300, 'days': 7, 'bonus': 50, 'features': ['چت ناشناس', '50 سکه هدیه']},
                '2': {'name': 'VIP ماهانه', 'price': 1000, 'days': 30, 'bonus': 200, 'features': ['تمام امکانات هفتگی', 'هدیه ماهانه 100 سکه']},
                '3': {'name': 'VIP سه ماهه', 'price': 2500, 'days': 90, 'bonus': 500, 'features': ['تمام امکانات ماهانه', 'پشتیبانی ویژه']},
                '4': {'name': 'VIP شش ماهه', 'price': 4500, 'days': 180, 'bonus': 1000, 'features': ['تمام امکانات', 'اولویت در سرویس']},
                '5': {'name': 'VIP سالانه', 'price': 7000, 'days': 365, 'bonus': 2000, 'features': ['تمام امکانات', 'مدیر اختصاصی']}
            },
            'settings': {
                'bot_name': 'Shadow Titan',
                'maintenance_mode': False,
                'maintenance_reason': '',
                'welcome_message': 'به ربات Shadow Titan خوش آمدید!',
                'min_coins_for_withdraw': 1000,
                'referral_reward': 50,
                'daily_reward_vip': 100,
                'daily_reward_normal': 10,
                'max_warns': 3
            },
            'stats': {
                'total_users': 0,
                'total_vip': 0,
                'total_coins': 0,
                'total_transactions': 0,
                'daily_income': 0,
                'weekly_income': 0,
                'monthly_income': 0,
                'last_reset': datetime.now().strftime('%Y-%m-%d')
            },
            'transactions': {},
            'events': {},
            'discounts': {},
            'banned': {}
        }
        
        for key, filename in self.files.items():
            if key == 'backups':
                continue
                
            if not os.path.exists(filename):
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(defaults.get(key, {}), f, ensure_ascii=False, indent=4)
    
    # ========== کاربران ==========
    def get_users(self):
        try:
            with open(self.files['users'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_users(self, users):
        try:
            with open(self.files['users'], 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def get_user(self, user_id):
        users = self.get_users()
        return users.get(str(user_id))
    
    def save_user(self, user_id, user_data):
        users = self.get_users()
        users[str(user_id)] = user_data
        return self.save_users(users)
    
    def delete_user(self, user_id):
        users = self.get_users()
        if str(user_id) in users:
            del users[str(user_id)]
            return self.save_users(users)
        return False
    
    def get_all_users(self):
        return self.get_users()
    
    def count_users(self):
        return len(self.get_users())
    
    def get_vip_users(self):
        users = self.get_users()
        vip_users = []
        now = time.time()
        
        for user_id, user in users.items():
            if user.get('vip_end', 0) > now:
                vip_users.append(user_id)
        
        return vip_users
    
    def count_vip_users(self):
        return len(self.get_vip_users())
    
    def get_total_coins(self):
        users = self.get_users()
        total = 0
        for user in users.values():
            total += user.get('coins', 0)
        return total
    
    # ========== ادمین‌ها ==========
    def get_admins(self):
        try:
            with open(self.files['admins'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'admins': ADMINS, 'admin_passwords': {}, 'master_password': 'admin123'}
    
    def save_admins(self, admins):
        try:
            with open(self.files['admins'], 'w', encoding='utf-8') as f:
                json.dump(admins, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def is_admin(self, user_id):
        admins = self.get_admins()
        return str(user_id) in admins.get('admins', [])
    
    def get_admin_password(self, user_id):
        admins = self.get_admins()
        return admins.get('admin_passwords', {}).get(str(user_id))
    
    def set_admin_password(self, user_id, password):
        admins = self.get_admins()
        admins['admin_passwords'][str(user_id)] = password
        return self.save_admins(admins)
    
    def get_master_password(self):
        admins = self.get_admins()
        return admins.get('master_password', 'admin123')
    
    def set_master_password(self, new_pass):
        admins = self.get_admins()
        admins['master_password'] = new_pass
        return self.save_admins(admins)
    
    def add_admin(self, user_id):
        admins = self.get_admins()
        if str(user_id) not in admins['admins']:
            admins['admins'].append(str(user_id))
            return self.save_admins(admins)
        return False
    
    def remove_admin(self, user_id):
        admins = self.get_admins()
        if str(user_id) in admins['admins']:
            admins['admins'].remove(str(user_id))
            if str(user_id) in admins.get('admin_passwords', {}):
                del admins['admin_passwords'][str(user_id)]
            return self.save_admins(admins)
        return False
    
    def get_all_admins(self):
        admins = self.get_admins()
        return admins.get('admins', [])
    
    # ========== پلن‌های VIP ==========
    def get_vip_plans(self):
        try:
            with open(self.files['vip_plans'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_vip_plans(self, plans):
        try:
            with open(self.files['vip_plans'], 'w', encoding='utf-8') as f:
                json.dump(plans, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def add_vip_plan(self, plan_id, plan_data):
        plans = self.get_vip_plans()
        plans[plan_id] = plan_data
        return self.save_vip_plans(plans)
    
    def delete_vip_plan(self, plan_id):
        plans = self.get_vip_plans()
        if plan_id in plans:
            del plans[plan_id]
            return self.save_vip_plans(plans)
        return False
    
    def update_vip_plan(self, plan_id, plan_data):
        plans = self.get_vip_plans()
        if plan_id in plans:
            plans[plan_id].update(plan_data)
            return self.save_vip_plans(plans)
        return False
    
    # ========== تنظیمات ==========
    def get_settings(self):
        try:
            with open(self.files['settings'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_settings(self, settings):
        try:
            with open(self.files['settings'], 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def get_setting(self, key, default=None):
        settings = self.get_settings()
        return settings.get(key, default)
    
    def set_setting(self, key, value):
        settings = self.get_settings()
        settings[key] = value
        return self.save_settings(settings)
    
    def set_maintenance(self, status, reason=""):
        settings = self.get_settings()
        settings['maintenance_mode'] = status
        settings['maintenance_reason'] = reason
        return self.save_settings(settings)
    
    def is_maintenance(self):
        settings = self.get_settings()
        return settings.get('maintenance_mode', False)
    
    # ========== آمار ==========
    def get_stats(self):
        try:
            with open(self.files['stats'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_stats(self, stats):
        try:
            with open(self.files['stats'], 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def update_stat(self, key, value):
        stats = self.get_stats()
        stats[key] = value
        return self.save_stats(stats)
    
    def increment_stat(self, key, amount=1):
        stats = self.get_stats()
        stats[key] = stats.get(key, 0) + amount
        return self.save_stats(stats)
    
    # ========== تراکنش‌ها ==========
    def get_transactions(self):
        try:
            with open(self.files['transactions'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_transactions(self, transactions):
        try:
            with open(self.files['transactions'], 'w', encoding='utf-8') as f:
                json.dump(transactions, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def add_transaction(self, transaction_id, transaction_data):
        transactions = self.get_transactions()
        transactions[transaction_id] = transaction_data
        return self.save_transactions(transactions)
    
    # ========== رویدادها ==========
    def get_events(self):
        try:
            with open(self.files['events'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_events(self, events):
        try:
            with open(self.files['events'], 'w', encoding='utf-8') as f:
                json.dump(events, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def add_event(self, event_id, event_data):
        events = self.get_events()
        events[event_id] = event_data
        return self.save_events(events)
    
    # ========== تخفیف‌ها ==========
    def get_discounts(self):
        try:
            with open(self.files['discounts'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_discounts(self, discounts):
        try:
            with open(self.files['discounts'], 'w', encoding='utf-8') as f:
                json.dump(discounts, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def add_discount(self, discount_id, discount_data):
        discounts = self.get_discounts()
        discounts[discount_id] = discount_data
        return self.save_discounts(discounts)
    
    # ========== بن‌ها ==========
    def get_banned(self):
        try:
            with open(self.files['banned'], 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_banned(self, banned):
        try:
            with open(self.files['banned'], 'w', encoding='utf-8') as f:
                json.dump(banned, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def ban_user(self, user_id, reason, admin_id, duration_days=0):
        banned = self.get_banned()
        banned[str(user_id)] = {
            'reason': reason,
            'banned_by': admin_id,
            'banned_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'duration_days': duration_days,
            'unban_at': (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S') if duration_days > 0 else 'permanent'
        }
        return self.save_banned(banned)
    
    def unban_user(self, user_id):
        banned = self.get_banned()
        if str(user_id) in banned:
            del banned[str(user_id)]
            return self.save_banned(banned)
        return False
    
    def is_banned(self, user_id):
        banned = self.get_banned()
        if str(user_id) in banned:
            ban_data = banned[str(user_id)]
            if ban_data.get('duration_days', 0) > 0:
                unban_at = datetime.strptime(ban_data['unban_at'], '%Y-%m-%d %H:%M:%S')
                if datetime.now() > unban_at:
                    self.unban_user(user_id)
                    return False
            return True
        return False
    
    # ========== بکاپ ==========
    def create_backup(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_data = {}
            
            for key, filename in self.files.items():
                if key == 'backups':
                    continue
                    
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        backup_data[key] = json.load(f)
                except:
                    backup_data[key] = {}
            
            backup_file = f"backups/backup_{timestamp}.json"
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)
            
            # حذف بکاپ‌های قدیمی (نگه‌داری 7 بکاپ آخر)
            backup_files = sorted([f for f in os.listdir('backups') if f.startswith('backup_')])
            if len(backup_files) > 7:
                for old_file in backup_files[:-7]:
                    os.remove(f"backups/{old_file}")
            
            return True
        except:
            return False
    
    def restore_backup(self, backup_file):
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            for key, data in backup_data.items():
                if key in self.files and key != 'backups':
                    with open(self.files[key], 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
            
            return True
        except:
            return False

# ==========================================
# سیستم مدیریت استیت
# ==========================================
class StateManager:
    def __init__(self):
        self.user_states = {}
        self.admin_states = {}
        self.temp_data = {}
    
    def set_user_state(self, user_id, state, data=None):
        self.user_states[str(user_id)] = {
            'state': state,
            'data': data or {},
            'timestamp': time.time()
        }
    
    def get_user_state(self, user_id):
        return self.user_states.get(str(user_id))
    
    def clear_user_state(self, user_id):
        if str(user_id) in self.user_states:
            del self.user_states[str(user_id)]
    
    def set_admin_state(self, user_id, state, data=None):
        self.admin_states[str(user_id)] = {
            'state': state,
            'data': data or {},
            'timestamp': time.time()
        }
    
    def get_admin_state(self, user_id):
        return self.admin_states.get(str(user_id))
    
    def clear_admin_state(self, user_id):
        if str(user_id) in self.admin_states:
            del self.admin_states[str(user_id)]
    
    def set_temp_data(self, user_id, key, value):
        if str(user_id) not in self.temp_data:
            self.temp_data[str(user_id)] = {}
        self.temp_data[str(user_id)][key] = value
    
    def get_temp_data(self, user_id, key, default=None):
        return self.temp_data.get(str(user_id), {}).get(key, default)
    
    def clear_temp_data(self, user_id):
        if str(user_id) in self.temp_data:
            del self.temp_data[str(user_id)]
    
    def cleanup_old_states(self):
        """پاک‌سازی استیت‌های قدیمی"""
        now = time.time()
        timeout = 3600  # 1 ساعت
        
        for user_id in list(self.user_states.keys()):
            if now - self.user_states[user_id]['timestamp'] > timeout:
                del self.user_states[user_id]
        
        for user_id in list(self.admin_states.keys()):
            if now - self.admin_states[user_id]['timestamp'] > timeout:
                del self.admin_states[user_id]

# ==========================================
# سیستم امنیت
# ==========================================
class SecuritySystem:
    def __init__(self, db):
        self.db = db
        self.failed_logins = {}
        self.ip_attempts = {}
        self.login_timeout = 300  # 5 دقیقه برای قفل شدن
    
    def check_login_attempts(self, user_id):
        """بررسی تعداد تلاش‌های ناموفق"""
        user_id = str(user_id)
        now = time.time()
        
        if user_id in self.failed_logins:
            attempts, lock_time = self.failed_logins[user_id]
            
            if now - lock_time < self.login_timeout and attempts >= 5:
                remaining = int(self.login_timeout - (now - lock_time))
                return False, f"حساب شما به دلیل تلاش‌های ناموفق قفل شده است. {remaining} ثانیه دیگر تلاش کنید."
        
        return True, "OK"
    
    def record_failed_login(self, user_id):
        """ثبت تلاش ناموفق"""
        user_id = str(user_id)
        now = time.time()
        
        if user_id not in self.failed_logins:
            self.failed_logins[user_id] = [1, now]
        else:
            attempts, last_time = self.failed_logins[user_id]
            
            if now - last_time > 300:  # ریست بعد از 5 دقیقه
                self.failed_logins[user_id] = [1, now]
            else:
                self.failed_logins[user_id] = [attempts + 1, now]
    
    def record_successful_login(self, user_id):
        """پاک کردن رکوردهای ناموفق بعد از ورود موفق"""
        user_id = str(user_id)
        if user_id in self.failed_logins:
            del self.failed_logins[user_id]
    
    def check_user_access(self, user_id):
        """بررسی دسترسی کاربر"""
        # چک اگر بن شده
        if self.db.is_banned(user_id):
            banned_data = self.db.get_banned().get(str(user_id), {})
            reason = banned_data.get('reason', 'نامشخص')
            unban_at = banned_data.get('unban_at', 'نامشخص')
            return False, f"حساب شما مسدود شده است.\nدلیل: {reason}\nتاریخ آزادسازی: {unban_at}"
        
        # چک حالت تعمیر
        if self.db.is_maintenance() and not self.db.is_admin(user_id):
            settings = self.db.get_settings()
            reason = settings.get('maintenance_reason', 'تعمیرات دوره‌ای')
            return False, f"ربات در حال تعمیر است.\nدلیل: {reason}"
        
        return True, "OK"

# ==========================================
# سیستم هشدار و نوتیفیکیشن
# ==========================================
class NotificationSystem:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
    
    def send_to_admins(self, message, parse_mode="HTML"):
        """ارسال پیام به تمام ادمین‌ها"""
        admins = self.db.get_all_admins()
        sent = 0
        
        for admin_id in admins:
            try:
                self.bot.send_message(admin_id, message, parse_mode=parse_mode)
                sent += 1
            except:
                pass
        
        return sent
    
    def send_vip_expiry_warning(self, user_id, days_left):
        """ارسال هشدار انقضای VIP"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        message = f"""
⚠️ **هشدار انقضای VIP**

👤 کاربر: {user.get('name', 'نامشخص')}
🆔 آی‌دی: {user_id}
⏳ روزهای باقی‌مانده: {days_left} روز

لطفاً به کاربر اطلاع دهید که VIP خود را تمدید کند.
        """
        
        self.send_to_admins(message)
    
    def send_vip_purchased_notification(self, user_id, plan_name, price):
        """اطلاع خرید VIP جدید"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        message = f"""
🛒 **خرید VIP جدید**

👤 کاربر: {user.get('name', 'نامشخص')}
🆔 آی‌دی: {user_id}
🎖 پلن: {plan_name}
💰 قیمت: {price:,} سکه
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_to_admins(message)
    
    def send_user_banned_notification(self, user_id, reason, admin_id):
        """اطلاع بن کاربر"""
        user = self.db.get_user(user_id)
        admin = self.db.get_user(admin_id)
        
        admin_name = admin.get('name', 'نامشخص') if admin else admin_id
        
        message = f"""
🚫 **کاربر مسدود شد**

👤 کاربر: {user.get('name', 'نامشخص') if user else 'نامشخص'}
🆔 آی‌دی: {user_id}
📝 دلیل: {reason}
🛡️ توسط ادمین: {admin_name}
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_to_admins(message)
    
    def send_coins_added_notification(self, user_id, amount, admin_id):
        """اطلاع اضافه شدن سکه"""
        user = self.db.get_user(user_id)
        admin = self.db.get_user(admin_id)
        
        admin_name = admin.get('name', 'نامشخص') if admin else admin_id
        
        message = f"""
💰 **سکه اضافه شد**

👤 کاربر: {user.get('name', 'نامشخص') if user else 'نامشخص'}
🆔 آی‌دی: {user_id}
🪙 مقدار: {amount:,} سکه
🛡️ توسط ادمین: {admin_name}
📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        self.send_to_admins(message)

# ==========================================
# سیستم قیمت‌گذاری پویا
# ==========================================
class DynamicPricing:
    def __init__(self, db):
        self.db = db
    
    def calculate_dynamic_price(self, base_price, user_id=None):
        """محاسبه قیمت پویا بر اساس عوامل مختلف"""
        price = base_price
        
        # تخفیف رویدادها
        events = self.db.get_events()
        for event in events.values():
            if event.get('active', False) and event.get('discount', 0) > 0:
                if datetime.now() < datetime.strptime(event.get('end_date'), '%Y-%m-%d'):
                    discount = event.get('discount', 0)
                    price = price * (100 - discount) / 100
        
        # تخفیف‌های ویژه
        discounts = self.db.get_discounts()
        for discount in discounts.values():
            if discount.get('active', False) and discount.get('type') == 'global':
                if datetime.now() < datetime.strptime(discount.get('end_date'), '%Y-%m-%d'):
                    disc = discount.get('percentage', 0)
                    price = price * (100 - disc) / 100
        
        # تخفیف برای کاربران وفادار
        if user_id:
            user = self.db.get_user(user_id)
            if user:
                referrals = user.get('referrals', 0)
                if referrals >= 10:
                    price = price * 0.9  # 10% تخفیف برای دعوت 10 نفر
                elif referrals >= 5:
                    price = price * 0.95  # 5% تخفیف برای دعوت 5 نفر
        
        return int(price)
    
    def get_time_based_multiplier(self):
        """ضریب بر اساس زمان"""
        hour = datetime.now().hour
        
        if 0 <= hour < 6:  # نیمه شب
            return 0.9  # 10% تخفیف
        elif 18 <= hour < 24:  # عصر
            return 1.1  # 10% گرانتر
        else:
            return 1.0  # قیمت عادی

# ==========================================
# سیستم پاداش و ماموریت
# ==========================================
class RewardSystem:
    def __init__(self, db):
        self.db = db
    
    def check_daily_reward(self, user_id):
        """بررسی پاداش روزانه"""
        user = self.db.get_user(user_id)
        if not user:
            return False, "کاربر یافت نشد"
        
        last_reward = user.get('last_daily_reward')
        today = datetime.now().strftime('%Y-%m-%d')
        
        if last_reward == today:
            return False, "امروز پاداش خود را دریافت کرده‌اید"
        
        # محاسبه پاداش
        is_vip = user.get('vip_end', 0) > time.time()
        base_reward = self.db.get_setting('daily_reward_vip' if is_vip else 'daily_reward_normal', 10)
        
        # ضریب بر اساس تعداد روزهای متوالی
        streak = user.get('reward_streak', 0) + 1
        if streak > 7:
            streak = 7
        
        multiplier = 1 + (streak * 0.1)  # 10% افزایش برای هر روز متوالی
        reward = int(base_reward * multiplier)
        
        # اعطای پاداش
        user['coins'] = user.get('coins', 0) + reward
        user['last_daily_reward'] = today
        user['reward_streak'] = streak
        self.db.save_user(user_id, user)
        
        # ثبت در آمار
        self.db.increment_stat('total_coins', reward)
        
        return True, f"🎁 پاداش روزانه شما: {reward} سکه\n🔥 روز متوالی: {streak}\n💰 موجودی جدید: {user['coins']:,} سکه"
    
    def give_referral_reward(self, referrer_id, referred_id):
        """اعطای پاداش دعوت"""
        referrer = self.db.get_user(referrer_id)
        if not referrer:
            return False
        
        reward = self.db.get_setting('referral_reward', 50)
        
        # اعطای پاداش به دعوت‌کننده
        referrer['coins'] = referrer.get('coins', 0) + reward
        referrer['referrals'] = referrer.get('referrals', 0) + 1
        referrer['total_referral_rewards'] = referrer.get('total_referral_rewards', 0) + reward
        self.db.save_user(referrer_id, referrer)
        
        # اعطای پاداش به دعوت‌شده
        referred = self.db.get_user(referred_id)
        if referred:
            referred['coins'] = referred.get('coins', 0) + (reward // 2)  # نصف پاداش
            self.db.save_user(referred_id, referred)
        
        # ثبت در آمار
        self.db.increment_stat('total_coins', reward + (reward // 2))
        
        return True
    
    def check_vip_expiry_rewards(self, user_id):
        """پاداش وفاداری برای تمدید VIP"""
        user = self.db.get_user(user_id)
        if not user:
            return
        
        vip_end = user.get('vip_end', 0)
        now = time.time()
        
        if vip_end > now:
            days_left = int((vip_end - now) / (24 * 3600))
            
            # پاداش وفاداری بر اساس مدت زمان VIP
            if days_left >= 180:  # 6 ماه یا بیشتر
                reward = 500
            elif days_left >= 90:  # 3 ماه یا بیشتر
                reward = 250
            elif days_left >= 30:  # 1 ماه یا بیشتر
                reward = 100
            else:
                reward = 0
            
            if reward > 0:
                user['coins'] = user.get('coins', 0) + reward
                user['vip_loyalty_rewards'] = user.get('vip_loyalty_rewards', 0) + reward
                self.db.save_user(user_id, user)
                
                try:
                    bot.send_message(user_id, f"🎁 پاداش وفاداری VIP: {reward} سکه\n💰 برای ادامه عضویت VIP")
                except:
                    pass

# ==========================================
# سیستم بازی‌ها
# ==========================================
class GameSystem:
    def __init__(self, db):
        self.db = db
        self.games = {
            'dice': {'name': 'تاس', 'cost': 10, 'min_win': 5, 'max_win': 50},
            'dart': {'name': 'دارت', 'cost': 15, 'min_win': 10, 'max_win': 75},
            'basketball': {'name': 'بسکتبال', 'cost': 20, 'min_win': 15, 'max_win': 100},
            'slot': {'name': 'اسلات', 'cost': 25, 'min_win': 0, 'max_win': 200},
            'roulette': {'name': 'رولت', 'cost': 30, 'min_win': 0, 'max_win': 300}
        }
    
    def play_game(self, user_id, game_type, bet_amount=None):
        """اجرای بازی"""
        if game_type not in self.games:
            return False, "بازی یافت نشد"
        
        user = self.db.get_user(user_id)
        if not user:
            return False, "کاربر یافت نشد"
        
        game = self.games[game_type]
        cost = bet_amount if bet_amount else game['cost']
        
        if user.get('coins', 0) < cost:
            return False, f"سکه کافی ندارید!\n💰 نیاز: {cost}\n💰 موجودی: {user.get('coins', 0)}"
        
        # محاسبه شانس برد
        win_chance = random.randint(1, 100)
        is_vip = user.get('vip_end', 0) > time.time()
        
        # افزایش شانس برای VIP ها
        if is_vip:
            win_chance += 10
        
        if win_chance > 70:  # 30% شانس برد عادی
            # محاسبه جایزه
            if game_type == 'slot':
                # اسلات ماشین با شانس کمتر اما جایزه بیشتر
                if random.randint(1, 100) > 80:  # 20% شانس برد
                    prize = random.randint(game['min_win'], game['max_win'])
                else:
                    prize = 0
            elif game_type == 'roulette':
                # رولت با شانس کمتر اما جایزه بیشتر
                if random.randint(1, 100) > 85:  # 15% شانس برد
                    prize = random.randint(game['min_win'], game['max_win'])
                else:
                    prize = 0
            else:
                prize = random.randint(game['min_win'], game['max_win'])
            
            result = "🎉 برنده شدید!"
            net_gain = prize - cost
            user['coins'] = user.get('coins', 0) - cost + prize
            
            # ثبت برد
            user['games_won'] = user.get('games_won', 0) + 1
            user['total_game_winnings'] = user.get('total_game_winnings', 0) + prize
        else:
            prize = 0
            result = "😞 باختید!"
            net_gain = -cost
            user['coins'] = user.get('coins', 0) - cost
            
            # ثبت باخت
            user['games_lost'] = user.get('games_lost', 0) + 1
        
        # ثبت آمار بازی
        user['games_played'] = user.get('games_played', 0) + 1
        self.db.save_user(user_id, user)
        
        # ثبت تراکنش
        transaction_id = f"game_{int(time.time())}_{random.randint(1000, 9999)}"
        self.db.add_transaction(transaction_id, {
            'user_id': user_id,
            'type': 'game',
            'game': game_type,
            'cost': cost,
            'prize': prize,
            'net': net_gain,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # به‌روزرسانی آمار
        self.db.increment_stat('total_transactions')
        
        return True, {
            'result': result,
            'game': game['name'],
            'cost': cost,
            'prize': prize,
            'net_gain': net_gain,
            'new_balance': user['coins'],
            'is_vip': is_vip
        }

# ==========================================
# سیستم گزارش‌گیری
# ==========================================
class ReportSystem:
    def __init__(self, db):
        self.db = db
    
    def generate_user_report(self, user_id):
        """تولید گزارش کاربر"""
        user = self.db.get_user(user_id)
        if not user:
            return "کاربر یافت نشد"
        
        is_vip = user.get('vip_end', 0) > time.time()
        vip_status = "✅ فعال" if is_vip else "❌ غیرفعال"
        
        if is_vip:
            days_left = int((user.get('vip_end', 0) - time.time()) / (24 * 3600))
            vip_info = f"{days_left} روز باقی مانده"
        else:
            vip_info = "ندارد"
        
        report = f"""
📊 **گزارش کاربر**

👤 اطلاعات اصلی:
├─ نام: {user.get('name', 'نامشخص')}
├─ آی‌دی: {user_id}
├─ سن: {user.get('age', 'نامشخص')}
├─ جنسیت: {user.get('gender', 'نامشخص')}
├─ وضعیت VIP: {vip_status}
└─ اطلاعات VIP: {vip_info}

💰 مالی:
├─ سکه: {user.get('coins', 0):,}
├─ کل دریافتی: {user.get('total_earned', 0):,}
├─ کل هزینه‌ها: {user.get('total_spent', 0):,}
└─ موجودی خالص: {user.get('coins', 0) - user.get('total_spent', 0):,}

📈 آمار:
├─ دعوت‌ها: {user.get('referrals', 0)}
├─ بازی‌ها: {user.get('games_played', 0)} بار
├─ بردها: {user.get('games_won', 0)} بار
├─ باخت‌ها: {user.get('games_lost', 0)} بار
└─ اخطارها: {user.get('warns', 0)}/{self.db.get_setting('max_warns', 3)}

📅 تاریخی:
├─ عضویت: {user.get('register_date', 'نامشخص')}
├─ آخرین فعالیت: {user.get('last_seen', 'نامشخص')}
├─ آخرین پاداش: {user.get('last_daily_reward', 'ندارد')}
└─ روزهای متوالی: {user.get('reward_streak', 0)} روز
        """
        
        return report
    
    def generate_system_report(self):
        """تولید گزارش سیستم"""
        stats = self.db.get_stats()
        settings = self.db.get_settings()
        
        total_users = self.db.count_users()
        vip_users = self.db.count_vip_users()
        total_coins = self.db.get_total_coins()
        
        report = f"""
📈 **گزارش سیستم**

👥 کاربران:
├─ کل کاربران: {total_users}
├─ کاربران VIP: {vip_users}
├─ کاربران عادی: {total_users - vip_users}
└─ درصد VIP: {(vip_users/total_users*100 if total_users > 0 else 0):.1f}%

💰 مالی:
├─ کل سکه‌ها: {total_coins:,}
├─ میانگین سکه هر کاربر: {total_coins//total_users if total_users > 0 else 0:,}
├─ کل تراکنش‌ها: {stats.get('total_transactions', 0)}
├─ درآمد امروز: {stats.get('daily_income', 0):,}
├─ درآمد هفته: {stats.get('weekly_income', 0):,}
└─ درآمد ماه: {stats.get('monthly_income', 0):,}

⚙️ تنظیمات:
├─ نام ربات: {settings.get('bot_name', 'نامشخص')}
├─ حالت تعمیر: {'✅ فعال' if settings.get('maintenance_mode') else '❌ غیرفعال'}
├─ پاداش دعوت: {settings.get('referral_reward', 50)} سکه
├─ پاداش روزانه VIP: {settings.get('daily_reward_vip', 100)} سکه
├─ پاداش روزانه عادی: {settings.get('daily_reward_normal', 10)} سکه
└─ حداقل برداشت: {settings.get('min_coins_for_withdraw', 1000):,} سکه

📅 اطلاعات:
├─ تاریخ گزارش: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
├─ آخرین ریست آمار: {stats.get('last_reset', 'نامشخص')}
└─ تعداد ادمین‌ها: {len(self.db.get_all_admins())}
        """
        
        return report

# ==========================================
# نصب سیستم‌ها
# ==========================================
db = Database()
state_manager = StateManager()
security = SecuritySystem(db)
notification = NotificationSystem(bot, db)
pricing = DynamicPricing(db)
rewards = RewardSystem(db)
games = GameSystem(db)
reports = ReportSystem(db)

# ==========================================
# تابع‌های کمکی
# ==========================================
def generate_referral_code(user_id):
    """تولید کد دعوت"""
    chars = string.ascii_letters + string.digits
    code = ''.join(random.choice(chars) for _ in range(8))
    return f"REF{user_id[:4]}{code}"

def format_coin(amount):
    """فرمت کردن سکه"""
    return f"{amount:,}"

def format_date(date_str):
    """فرمت کردن تاریخ"""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y/%m/%d %H:%M')
    except:
        return date_str

def is_valid_date(date_str):
    """بررسی اعتبار تاریخ"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except:
        return False

def calculate_vip_end(days):
    """محاسبه تاریخ انقضای VIP"""
    return time.time() + (days * 24 * 3600)

def get_vip_days_left(vip_end):
    """محاسبه روزهای باقی‌مانده VIP"""
    if vip_end <= 0:
        return 0
    now = time.time()
    if vip_end <= now:
        return 0
    return int((vip_end - now) / (24 * 3600))

# ==========================================
# منوهای اصلی
# ==========================================
def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    user = db.get_user(user_id)
    is_vip = user and user.get('vip_end', 0) > time.time()
    
    markup.add("👤 پروفایل من", "💰 کیف پول")
    markup.add("🎖 خرید VIP", "🎰 بازی‌ها")
    markup.add("🎁 پاداش روزانه", "👥 دعوت دوستان")
    markup.add("📊 گزارش کامل", "📞 پشتیبانی")
    
    if is_vip:
        markup.add("⭐ ویژه‌های VIP", "🎪 رویدادها")
    
    if db.is_admin(user_id):
        markup.add("🛡️ پنل مدیریت")
    
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    markup.add("📊 آمار کامل", "👥 مدیریت کاربران")
    markup.add("🎖 مدیریت VIP", "💰 مدیریت مالی")
    markup.add("🎪 مدیریت رویدادها", "⚙️ تنظیمات پیشرفته")
    markup.add("📈 گزارش‌گیری", "🔧 ابزارها")
    markup.add("📢 ارسال همگانی", "➕ ادمین جدید")
    markup.add("🔙 بازگشت به منو")
    
    return markup

def get_user_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📋 لیست کاربران", callback_data="admin_users_list"),
        types.InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="admin_users_search")
    )
    markup.add(
        types.InlineKeyboardButton("📊 گزارش کاربر", callback_data="admin_user_report"),
        types.InlineKeyboardButton("🪙 مدیریت سکه", callback_data="admin_coins_manage")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 مدیریت بن", callback_data="admin_ban_manage"),
        types.InlineKeyboardButton("⚠️ مدیریت اخطار", callback_data="admin_warn_manage")
    )
    markup.add(
        types.InlineKeyboardButton("🗑️ حذف کاربر", callback_data="admin_user_delete"),
        types.InlineKeyboardButton("📧 پیام به کاربر", callback_data="admin_user_message")
    )
    
    return markup

def get_vip_management_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("➕ افزودن پلن", callback_data="vip_add_plan"),
        types.InlineKeyboardButton("✏️ ویرایش پلن", callback_data="vip_edit_plan")
    )
    markup.add(
        types.InlineKeyboardButton("🗑️ حذف پلن", callback_data="vip_delete_plan"),
        types.InlineKeyboardButton("📋 لیست پلن‌ها", callback_data="vip_list_plans")
    )
    markup.add(
        types.InlineKeyboardButton("💰 تنظیم قیمت", callback_data="vip_set_prices"),
        types.InlineKeyboardButton("🎁 اعطای VIP", callback_data="vip_give_free")
    )
    markup.add(
        types.InlineKeyboardButton("📊 آمار VIP", callback_data="vip_stats"),
        types.InlineKeyboardButton("🔄 تمدید دسته‌ای", callback_data="vip_bulk_renew")
    )
    
    return markup

def get_financial_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("💰 افزودن سکه", callback_data="finance_add_coins"),
        types.InlineKeyboardButton("➖ کسر سکه", callback_data="finance_remove_coins")
    )
    markup.add(
        types.InlineKeyboardButton("📊 آمار مالی", callback_data="finance_stats"),
        types.InlineKeyboardButton("📈 تراکنش‌ها", callback_data="finance_transactions")
    )
    markup.add(
        types.InlineKeyboardButton("💸 تنظیم پاداش", callback_data="finance_set_rewards"),
        types.InlineKeyboardButton("🎯 تنظیم بازی", callback_data="finance_set_games")
    )
    markup.add(
        types.InlineKeyboardButton("🔄 ریست مالی", callback_data="finance_reset"),
        types.InlineKeyboardButton("💾 بکاپ مالی", callback_data="finance_backup")
    )
    
    return markup

def get_settings_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    settings = db.get_settings()
    maintenance = "🔴 فعال" if settings.get('maintenance_mode') else "🟢 غیرفعال"
    
    markup.add(
        types.InlineKeyboardButton(f"🔧 تعمیر: {maintenance}", callback_data="settings_maintenance"),
        types.InlineKeyboardButton("🔐 رمز اصلی", callback_data="settings_master_pass")
    )
    markup.add(
        types.InlineKeyboardButton("📛 نام ربات", callback_data="settings_bot_name"),
        types.InlineKeyboardButton("💬 پیام خوش‌آمد", callback_data="settings_welcome_msg")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 تنظیم پاداش", callback_data="settings_rewards"),
        types.InlineKeyboardButton("⚖️ محدودیت‌ها", callback_data="settings_limits")
    )
    markup.add(
        types.InlineKeyboardButton("🔄 ریست داده", callback_data="settings_reset_data"),
        types.InlineKeyboardButton("💾 بکاپ کامل", callback_data="settings_full_backup")
    )
    
    return markup

def get_tools_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("🔄 بررسی انقضا VIP", callback_data="tools_check_vip"),
        types.InlineKeyboardButton("🧹 پاک‌سازی داده", callback_data="tools_cleanup")
    )
    markup.add(
        types.InlineKeyboardButton("📊 به‌روزرسانی آمار", callback_data="tools_update_stats"),
        types.InlineKeyboardButton("🔍 بررسی خطاها", callback_data="tools_check_errors")
    )
    markup.add(
        types.InlineKeyboardButton("📤 خروجی اکسل", callback_data="tools_export_excel"),
        types.InlineKeyboardButton("📥 وارد کردن داده", callback_data="tools_import_data")
    )
    
    return markup

# ==========================================
# هندلرهای اصلی ربات
# ==========================================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = str(message.chat.id)
    
    # بررسی دسترسی
    has_access, error_msg = security.check_user_access(user_id)
    if not has_access:
        bot.send_message(user_id, f"🚫 {error_msg}")
        return
    
    # بررسی Rate Limiting
    allowed, rate_msg = security.check_login_attempts(user_id)
    if not allowed:
        bot.send_message(user_id, f"⏳ {rate_msg}")
        return
    
    # پردازش لینک دعوت
    payload = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    
    if payload:
        if payload.startswith('ref_'):
            referrer_id = payload[4:]
            handle_referral(user_id, referrer_id)
    
    # ثبت یا نمایش کاربر
    user = db.get_user(user_id)
    
    if not user:
        start_registration(user_id)
    else:
        welcome_back(user_id, user)

def start_registration(user_id):
    """شروع ثبت‌نام کاربر جدید"""
    state_manager.set_user_state(user_id, 'name')
    
    settings = db.get_settings()
    welcome_msg = settings.get('welcome_message', 'به ربات خوش آمدید!')
    
    bot.send_message(user_id, f"👋 {welcome_msg}\n\nلطفاً نام خود را وارد کنید:")

def handle_referral(user_id, referrer_id):
    """پردازش لینک دعوت"""
    if user_id == referrer_id:
        return
    
    referrer = db.get_user(referrer_id)
    if not referrer:
        return
    
    # ثبت دعوت
    rewards.give_referral_reward(referrer_id, user_id)
    
    # اطلاع به دعوت‌کننده
    try:
        bot.send_message(referrer_id, f"🎉 کاربر جدید با لینک دعوت شما ثبت‌نام کرد!\n💰 پاداش دعوت دریافت شد.")
    except:
        pass

def welcome_back(user_id, user):
    """خوش‌آمدگویی به کاربر بازگشته"""
    # به‌روزرسانی آخرین فعالیت
    user['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.save_user(user_id, user)
    
    # بررسی VIP
    rewards.check_vip_expiry_rewards(user_id)
    
    is_vip = user.get('vip_end', 0) > time.time()
    vip_status = "🎖 VIP" if is_vip else "⭐ عادی"
    
    # بررسی رویدادهای فعال
    events = db.get_events()
    active_events = []
    for event_id, event in events.items():
        if event.get('active', False):
            if datetime.now() < datetime.strptime(event.get('end_date'), '%Y-%m-%d'):
                active_events.append(event.get('name', 'رویداد'))
    
    event_text = ""
    if active_events:
        event_text = f"\n🎪 رویدادهای فعال: {', '.join(active_events)}"
    
    welcome_text = f"""
🔄 خوش برگشتید {user.get('name', 'عزیز')}!

🔸 وضعیت: {vip_status}
💰 سکه: {user.get('coins', 0):,}
👥 دعوت‌ها: {user.get('referrals', 0)}
{event_text}

برای شروع از دکمه‌های زیر استفاده کنید:
    """
    
    bot.send_message(user_id, welcome_text, reply_markup=get_main_menu(user_id))

# ==========================================
# هندلر پیام‌ها
# ==========================================
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = str(message.chat.id)
    text = message.text
    
    # بررسی دسترسی
    has_access, error_msg = security.check_user_access(user_id)
    if not has_access:
        bot.send_message(user_id, f"🚫 {error_msg}")
        return
    
    # پردازش استیت کاربر
    user_state = state_manager.get_user_state(user_id)
    if user_state:
        handle_user_state(user_id, text, user_state)
        return
    
    # پردازش استیت ادمین
    admin_state = state_manager.get_admin_state(user_id)
    if admin_state:
        handle_admin_state(user_id, text, admin_state)
        return
    
    # پردازش دستورات ادمین
    if db.is_admin(user_id) and text == "🛡️ پنل مدیریت":
        admin_login_start(user_id)
        return
    
    if db.is_admin(user_id) and admin_state and admin_state.get('state') == 'admin_logged_in':
        handle_admin_command(user_id, text)
        return
    
    # پردازش دستورات کاربر
    handle_user_command(user_id, text)

# ==========================================
# پردازش ثبت‌نام کاربر
# ==========================================
def handle_user_state(user_id, text, state):
    """پردازش استیت کاربر"""
    current_state = state['state']
    
    if current_state == 'name':
        if len(text) < 2:
            bot.send_message(user_id, "❌ نام باید حداقل ۲ حرف باشد. دوباره وارد کنید:")
            return
        
        state_manager.set_user_state(user_id, 'age', {'name': text})
        bot.send_message(user_id, "🎂 سن خود را وارد کنید:")
    
    elif current_state == 'age':
        try:
            age = int(text)
            if age < 1 or age > 150:
                raise ValueError
        except:
            bot.send_message(user_id, "❌ سن باید عدد بین ۱ تا ۱۵۰ باشد. دوباره وارد کنید:")
            return
        
        user_data = state_manager.get_user_state(user_id)['data']
        user_data['age'] = age
        state_manager.set_user_state(user_id, 'gender', user_data)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("👨 مرد", "👩 زن")
        bot.send_message(user_id, "⚧️ جنسیت خود را انتخاب کنید:", reply_markup=markup)
    
    elif current_state == 'gender':
        if text not in ["👨 مرد", "👩 زن"]:
            bot.send_message(user_id, "❌ لطفاً از دکمه‌ها استفاده کنید.")
            return
        
        gender = "مرد" if text == "👨 مرد" else "زن"
        user_data = state_manager.get_user_state(user_id)['data']
        
        # تکمیل ثبت‌نام
        complete_registration(user_id, user_data, gender)

def complete_registration(user_id, user_data, gender):
    """تکمیل ثبت‌نام کاربر"""
    user_info = {
        'name': user_data['name'],
        'age': user_data['age'],
        'gender': gender,
        'coins': 100,  # سکه هدیه عضویت
        'vip_end': 0,
        'referrals': 0,
        'warns': 0,
        'register_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'games_played': 0,
        'games_won': 0,
        'games_lost': 0,
        'total_earned': 100,
        'total_spent': 0,
        'reward_streak': 0
    }
    
    db.save_user(user_id, user_info)
    state_manager.clear_user_state(user_id)
    
    # به‌روزرسانی آمار
    db.increment_stat('total_users')
    db.increment_stat('total_coins', 100)
    
    # ارسال پیام تبریک
    bot.send_message(
        user_id,
        f"✅ **ثبت‌نام با موفقیت انجام شد!**\n\n"
        f"👤 نام: {user_data['name']}\n"
        f"🎂 سن: {user_data['age']}\n"
        f"⚧️ جنسیت: {gender}\n"
        f"💰 سکه هدیه: 100 سکه\n\n"
        f"🆔 آی‌دی شما: `{user_id}`\n"
        f"🔗 لینک دعوت شما: https://t.me/{bot.get_me().username}?start=ref_{user_id}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    # نمایش منوی اصلی
    time.sleep(2)
    bot.send_message(user_id, "🏠 منوی اصلی:", reply_markup=get_main_menu(user_id))

# ==========================================
# دستورات کاربران
# ==========================================
def handle_user_command(user_id, text):
    """پردازش دستورات کاربر"""
    user = db.get_user(user_id)
    if not user:
        bot.send_message(user_id, "❌ شما ثبت‌نام نکرده‌اید! لطفاً /start را بزنید.")
        return
    
    # به‌روزرسانی آخرین فعالیت
    user['last_seen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.save_user(user_id, user)
    
    if text == "👤 پروفایل من":
        show_user_profile(user_id)
    
    elif text == "💰 کیف پول":
        show_wallet(user_id)
    
    elif text == "🎖 خرید VIP":
        show_vip_store(user_id)
    
    elif text == "🎰 بازی‌ها":
        show_games_menu(user_id)
    
    elif text == "🎁 پاداش روزانه":
        claim_daily_reward(user_id)
    
    elif text == "👥 دعوت دوستان":
        show_referral_system(user_id)
    
    elif text == "📊 گزارش کامل":
        show_user_report(user_id)
    
    elif text == "📞 پشتیبانی":
        show_support(user_id)
    
    elif text == "⭐ ویژه‌های VIP":
        show_vip_features(user_id)
    
    elif text == "🎪 رویدادها":
        show_events(user_id)
    
    else:
        bot.send_message(user_id, "🤔 دستور نامعتبر است. لطفاً از دکمه‌های منو استفاده کنید.")

# ==========================================
# توابع کاربران
# ==========================================
def show_user_profile(user_id):
    """نمایش پروفایل کاربر"""
    report = reports.generate_user_report(user_id)
    bot.send_message(user_id, report)

def show_wallet(user_id):
    """نمایش کیف پول"""
    user = db.get_user(user_id)
    if not user:
        return
    
    wallet_text = f"""
💰 **کیف پول شما**

🪙 موجودی: {user.get('coins', 0):,} سکه

📊 آمار مالی:
├─ کل دریافتی: {user.get('total_earned', 0):,}
├─ کل هزینه‌ها: {user.get('total_spent', 0):,}
├─ سود خالص: {user.get('coins', 0) - user.get('total_spent', 0):,}
└─ دعوت‌های موفق: {user.get('referrals', 0)}

💡 روش‌های افزایش موجودی:
1. خرید VIP (سکه هدیه دریافت کنید)
2. دعوت دوستان (هر دعوت {db.get_setting('referral_reward', 50)} سکه)
3. دریافت پاداش روزانه
4. شرکت در بازی‌ها
5. شرکت در رویدادها
    """
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎰 بازی کن", callback_data="user_play_game"),
        types.InlineKeyboardButton("👥 دعوت کن", callback_data="user_invite_friends")
    )
    
    bot.send_message(user_id, wallet_text, reply_markup=markup)

def show_vip_store(user_id):
    """نمایش فروشگاه VIP"""
    user = db.get_user(user_id)
    plans = db.get_vip_plans()
    
    if not plans:
        bot.send_message(user_id, "📭 در حال حاضر پلن VIP‌ای موجود نیست.")
        return
    
    coins = user.get('coins', 0) if user else 0
    is_vip = user and user.get('vip_end', 0) > time.time()
    
    if is_vip:
        days_left = get_vip_days_left(user.get('vip_end', 0))
        vip_status = f"🎖 VIP فعال ({days_left} روز باقی مانده)"
    else:
        vip_status = "⭐ عادی"
    
    text = f"""
🎖 **فروشگاه VIP**

📊 وضعیت شما: {vip_status}
💰 موجودی شما: {coins:,} سکه

🔥 **پلن‌های ویژه:**
    """
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for plan_id, plan in plans.items():
        price = pricing.calculate_dynamic_price(plan.get('price', 0), user_id)
        days = plan.get('days', 0)
        bonus = plan.get('bonus', 0)
        features = plan.get('features', [])
        
        can_buy = coins >= price
        
        button_text = f"{'✅' if can_buy else '🔒'} {plan['name']} - {price:,} سکه"
        callback_data = f"buy_vip_{plan_id}"
        
        if can_buy:
            markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        else:
            markup.add(types.InlineKeyboardButton(button_text, callback_data="insufficient_coins"))
        
        text += f"\n\n📛 **{plan['name']}**"
        for feature in features[:3]:
            text += f"\n• {feature}"
        text += f"\n💰 قیمت: {price:,} سکه"
        text += f"\n🎁 هدیه: {bonus} سکه"
        text += f"\n📅 مدت: {days} روز"
    
    # بررسی تخفیف‌ها
    discounts = db.get_discounts()
    active_discounts = []
    for discount in discounts.values():
        if discount.get('active', False) and discount.get('type') == 'vip':
            if datetime.now() < datetime.strptime(discount.get('end_date'), '%Y-%m-%d'):
                active_discounts.append(discount)
    
    if active_discounts:
        text += "\n\n🎪 **تخفیف‌های فعال:**"
        for discount in active_discounts[:3]:
            text += f"\n• {discount.get('name')}: {discount.get('percentage')}%"
    
    bot.send_message(user_id, text, reply_markup=markup)

def show_games_menu(user_id):
    """نمایش منوی بازی‌ها"""
    user = db.get_user(user_id)
    coins = user.get('coins', 0) if user else 0
    
    text = f"""
🎰 **سالن بازی**

💰 موجودی شما: {coins:,} سکه

🎮 **بازی‌های موجود:**
    """
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for game_id, game in games.games.items():
        cost = game['cost']
        can_play = coins >= cost
        
        button_text = f"{game['name']} ({cost} سکه)"
        callback_data = f"play_game_{game_id}"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
        
        text += f"\n\n🎯 **{game['name']}**"
        text += f"\n💰 هزینه: {cost} سکه"
        text += f"\n🏆 جایزه: {game['min_win']}-{game['max_win']} سکه"
    
    bot.send_message(user_id, text, reply_markup=markup)

def claim_daily_reward(user_id):
    """دریافت پاداش روزانه"""
    success, message = rewards.check_daily_reward(user_id)
    bot.send_message(user_id, message)

def show_referral_system(user_id):
    """نمایش سیستم دعوت"""
    user = db.get_user(user_id)
    if not user:
        return
    
    referrals = user.get('referrals', 0)
    referral_reward = db.get_setting('referral_reward', 50)
    total_rewards = user.get('total_referral_rewards', 0)
    
    text = f"""
👥 **سیستم دعوت**

📊 آمار شما:
├─ دعوت‌های موفق: {referrals}
├─ پاداش هر دعوت: {referral_reward} سکه
├─ کل پاداش‌ها: {total_rewards:,} سکه
└─ موجودی از دعوت: {referrals * referral_reward:,} سکه

🔗 **لینک دعوت شما:**
`https://t.me/{bot.get_me().username}?start=ref_{user_id}`

📝 **قوانین دعوت:**
1. هر دعوت موفق: {referral_reward} سکه برای شما
2. دعوت‌شده: {referral_reward // 2} سکه هدیه
3. دعوت‌شده باید با لینک شما ثبت‌نام کند
4. پاداش بعد از اولین فعالیت دعوت‌شده واریز می‌شود

🎯 **اهداف ویژه:**
├─ دعوت ۵ نفر: ۱۰۰ سکه جایزه ویژه
├─ دعوت ۱۰ نفر: ۲۵۰ سکه جایزه ویژه
└─ دعوت ۲۰ نفر: ۵۰۰ سکه جایزه ویژه
    """
    
    bot.send_message(user_id, text)

def show_user_report(user_id):
    """نمایش گزارش کامل کاربر"""
    report = reports.generate_user_report(user_id)
    bot.send_message(user_id, report)

def show_support(user_id):
    """نمایش پشتیبانی"""
    text = f"""
📞 **پشتیبانی**

👤 مدیر ربات: {SUPPORT_USERNAME}
📢 کانال اطلاع‌رسانی: {CHANNEL_USERNAME}

⏰ **ساعات پاسخگویی:**
├─ شنبه تا چهارشنبه: ۹ صبح تا ۹ شب
├─ پنج‌شنبه: ۹ صبح تا ۲ بعدازظهر
└─ جمعه: ۴ بعدازظهر تا ۹ شب

📝 **راه‌های ارتباط:**
1. پیام مستقیم به مدیر
2. گزارش در ربات با دستور /report
3. عضویت در کانال اطلاع‌رسانی

⚠️ **قوانین پشتیبانی:**
├─ محترمانه برخورد کنید
├─ مشکل را با جزئیات شرح دهید
├─ آی‌دی خود را ارسال کنید
└─ شکیبا باشید

💡 **راهنمای سریع:**
• برای ثبت‌نام: /start
• برای خرید VIP: دکمه 🎖 خرید VIP
• برای بازی: دکمه 🎰 بازی‌ها
• برای پاداش: دکمه 🎁 پاداش روزانه
    """
    
    bot.send_message(user_id, text)

def show_vip_features(user_id):
    """نمایش ویژگی‌های VIP"""
    user = db.get_user(user_id)
    
    if not user or user.get('vip_end', 0) <= time.time():
        bot.send_message(user_id, "❌ شما VIP نیستید!\nبرای دسترسی به این ویژگی‌ها VIP بخرید.")
        return
    
    text = """
⭐ **ویژگی‌های VIP**

✅ **امکانات اصلی:**
├─ چت ناشناس نامحدود
├─ ارسال پیام ناشناس
├─ شرکت در گردونه شانس روزانه
├─ دسترسی به پروفایل پیشرفته
└─ مشاهده آمار کامل ربات

🎁 **پاداش‌های ویژه:**
├─ ۱۰۰ سکه هدیه ماهانه
├─ پاداش روزانه ۲ برابری
├─ ۵۰% تخفیف در بازی‌ها
└─ جایزه ویژه در رویدادها

🚀 **اولویت‌ها:**
├─ اولویت در جستجوی چت
├─ سرعت بالاتر در ربات
├─ پشتیبانی VIP 24/7
└─ دسترسی زودهنگام به قابلیت‌های جدید

🔒 **امنیت پیشرفته:**
├─ احراز هویت دو مرحله‌ای
├─ هشدارهای امنیتی
├─ بازیابی حساب سریع
└─ پشتیبان‌گیری خودکار

📊 **آمار پیشرفته:**
├─ نمودارهای تعاملی
├─ گزارش‌های هفتگی
├─ پیش‌بینی درآمد
└─ تحلیل عملکرد

🎪 **ورود به رویدادها:**
├─ ورود رایگان به همه رویدادها
├─ جایگاه ویژه در رویدادها
├─ شانس برنده شدن بیشتر
└─ جوایز اختصاصی VIP

📅 **تاریخ انقضای VIP شما:**
    """
    
    vip_end = user.get('vip_end', 0)
    expiry_date = datetime.fromtimestamp(vip_end).strftime('%Y/%m/%d')
    days_left = get_vip_days_left(vip_end)
    
    text += f"\n📅 {expiry_date} ({days_left} روز باقی مانده)"
    
    bot.send_message(user_id, text)

def show_events(user_id):
    """نمایش رویدادها"""
    events = db.get_events()
    active_events = []
    upcoming_events = []
    
    now = datetime.now()
    
    for event_id, event in events.items():
        if event.get('active', False):
            end_date = datetime.strptime(event.get('end_date'), '%Y-%m-%d')
            if now < end_date:
                active_events.append(event)
            else:
                upcoming_events.append(event)
    
    text = "🎪 **رویدادها**\n\n"
    
    if active_events:
        text += "🔥 **رویدادهای فعال:**\n\n"
        for event in active_events[:5]:  # فقط ۵ رویداد اول
            end_date = datetime.strptime(event.get('end_date'), '%Y-%m-%d')
            days_left = (end_date - now).days
            
            text += f"📛 **{event.get('name')}**\n"
            text += f"📝 {event.get('description', 'بدون توضیح')}\n"
            text += f"🎁 جایزه: {event.get('prize', 'ندارد')}\n"
            text += f"⏳ {days_left} روز باقی مانده\n\n"
    else:
        text += "📭 در حال حاضر رویداد فعالی وجود ندارد.\n\n"
    
    text += "📅 **رویدادهای آینده:**\n\n"
    
    if upcoming_events:
        for event in upcoming_events[:3]:
            start_date = datetime.strptime(event.get('start_date'), '%Y-%m-%d')
            days_until = (start_date - now).days
            
            text += f"📛 {event.get('name')}\n"
            text += f"📅 شروع: {event.get('start_date')}\n"
            text += f"⏳ {days_until} روز دیگر\n\n"
    else:
        text += "📭 رویداد آینده‌ای برنامه‌ریزی نشده است.\n\n"
    
    text += f"📢 برای اطلاع از رویدادها در کانال ما عضو شوید:\n{CHANNEL_USERNAME}"
    
    bot.send_message(user_id, text)

# ==========================================
# سیستم ادمین
# ==========================================
def admin_login_start(user_id):
    """شروع ورود ادمین"""
    if not db.is_admin(user_id):
        bot.send_message(user_id, "❌ شما ادمین نیستید!")
        return
    
    # چک اگر رمز شخصی دارد
    admin_pass = db.get_admin_password(user_id)
    
    if admin_pass:
        state_manager.set_admin_state(user_id, 'waiting_admin_pass')
        bot.send_message(user_id, "🔐 **ورود به پنل مدیریت**\n\nلطفاً رمز شخصی خود را وارد کنید:")
    else:
        state_manager.set_admin_state(user_id, 'waiting_master_pass')
        bot.send_message(user_id, "🔐 **ورود به پنل مدیریت**\n\nشما هنوز رمز شخصی تنظیم نکرده‌اید.\nلطفاً رمز اصلی را وارد کنید:")

def handle_admin_state(user_id, text, state):
    """پردازش استیت ادمین"""
    current_state = state['state']
    
    if current_state == 'waiting_master_pass':
        master_pass = db.get_master_password()
        
        if text != master_pass:
            security.record_failed_login(user_id)
            bot.send_message(user_id, "❌ رمز اشتباه است!")
            
            # چک تعداد تلاش‌ها
            allowed, message = security.check_login_attempts(user_id)
            if not allowed:
                bot.send_message(user_id, f"⏳ {message}")
                state_manager.clear_admin_state(user_id)
                return
            
            state_manager.set_admin_state(user_id, 'waiting_master_pass')
            bot.send_message(user_id, "❌ رمز اشتباه است! دوباره وارد کنید:")
            return
        
        # ورود موفق
        security.record_successful_login(user_id)
        
        # اگر رمز شخصی ندارد، تنظیم کند
        if not db.get_admin_password(user_id):
            state_manager.set_admin_state(user_id, 'setting_admin_pass')
            bot.send_message(user_id, "✅ رمز اصلی صحیح!\n\n🔑 حالا یک رمز شخصی برای خود انتخاب کنید (حداقل ۴ حرف):")
        else:
            state_manager.set_admin_state(user_id, 'admin_logged_in')
            bot.send_message(user_id, "✅ وارد پنل مدیریت شدید!", reply_markup=get_admin_menu())
    
    elif current_state == 'waiting_admin_pass':
        admin_pass = db.get_admin_password(user_id)
        
        if text != admin_pass:
            security.record_failed_login(user_id)
            
            allowed, message = security.check_login_attempts(user_id)
            if not allowed:
                bot.send_message(user_id, f"⏳ {message}")
                state_manager.clear_admin_state(user_id)
                return
            
            state_manager.set_admin_state(user_id, 'waiting_admin_pass')
            bot.send_message(user_id, "❌ رمز اشتباه است! دوباره وارد کنید:")
            return
        
        # ورود موفق
        security.record_successful_login(user_id)
        state_manager.set_admin_state(user_id, 'admin_logged_in')
        bot.send_message(user_id, "✅ وارد پنل مدیریت شدید!", reply_markup=get_admin_menu())
    
    elif current_state == 'setting_admin_pass':
        if len(text) < 4:
            bot.send_message(user_id, "❌ رمز باید حداقل ۴ حرف باشد. دوباره وارد کنید:")
            return
        
        db.set_admin_password(user_id, text)
        state_manager.set_admin_state(user_id, 'admin_logged_in')
        
        bot.send_message(
            user_id,
            f"✅ رمز شما ذخیره شد!\n\n"
            f"🔑 رمز شما: `{text}`\n"
            f"⚠️ این رمز را فراموش نکنید!\n\n"
            f"برای ورود بعدی از همین رمز استفاده کنید.",
            reply_markup=get_admin_menu()
        )

def handle_admin_command(user_id, text):
    """پردازش دستورات ادمین"""
    if text == "📊 آمار کامل":
        show_admin_stats(user_id)
    
    elif text == "👥 مدیریت کاربران":
        bot.send_message(user_id, "👥 **مدیریت کاربران**", reply_markup=get_user_management_menu())
    
    elif text == "🎖 مدیریت VIP":
        bot.send_message(user_id, "🎖 **مدیریت VIP**", reply_markup=get_vip_management_menu())
    
    elif text == "💰 مدیریت مالی":
        bot.send_message(user_id, "💰 **مدیریت مالی**", reply_markup=get_financial_menu())
    
    elif text == "🎪 مدیریت رویدادها":
        manage_events_start(user_id)
    
    elif text == "⚙️ تنظیمات پیشرفته":
        bot.send_message(user_id, "⚙️ **تنظیمات پیشرفته**", reply_markup=get_settings_menu())
    
    elif text == "📈 گزارش‌گیری":
        generate_reports_menu(user_id)
    
    elif text == "🔧 ابزارها":
        bot.send_message(user_id, "🔧 **ابزارها**", reply_markup=get_tools_menu())
    
    elif text == "📢 ارسال همگانی":
        start_broadcast(user_id)
    
    elif text == "➕ ادمین جدید":
        add_admin_start(user_id)
    
    elif text == "🔙 بازگشت به منو":
        state_manager.clear_admin_state(user_id)
        bot.send_message(user_id, "🏠 منوی اصلی", reply_markup=get_main_menu(user_id))
    
    else:
        bot.send_message(user_id, "🤔 دستور نامعتبر است.")

# ==========================================
# توابع ادمین
# ==========================================
def show_admin_stats(user_id):
    """نمایش آمار کامل برای ادمین"""
    report = reports.generate_system_report()
    bot.send_message(user_id, report)

def manage_events_start(user_id):
    """شروع مدیریت رویدادها"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("➕ ایجاد رویداد", callback_data="event_create"),
        types.InlineKeyboardButton("✏️ ویرایش رویداد", callback_data="event_edit")
    )
    markup.add(
        types.InlineKeyboardButton("🗑️ حذف رویداد", callback_data="event_delete"),
        types.InlineKeyboardButton("📋 لیست رویدادها", callback_data="event_list")
    )
    markup.add(
        types.InlineKeyboardButton("🎯 تنظیم تخفیف", callback_data="event_discount"),
        types.InlineKeyboardButton("📊 آمار رویداد", callback_data="event_stats")
    )
    
    bot.send_message(user_id, "🎪 **مدیریت رویدادها**", reply_markup=markup)

def generate_reports_menu(user_id):
    """منوی گزارش‌گیری"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📊 گزارش مالی", callback_data="report_financial"),
        types.InlineKeyboardButton("👥 گزارش کاربران", callback_data="report_users")
    )
    markup.add(
        types.InlineKeyboardButton("🎖 گزارش VIP", callback_data="report_vip"),
        types.InlineKeyboardButton("🎰 گزارش بازی‌ها", callback_data="report_games")
    )
    markup.add(
        types.InlineKeyboardButton("📈 گزارش رشد", callback_data="report_growth"),
        types.InlineKeyboardButton("📤 خروجی Excel", callback_data="report_export")
    )
    
    bot.send_message(user_id, "📈 **گزارش‌گیری**", reply_markup=markup)

def start_broadcast(user_id):
    """شروع ارسال همگانی"""
    state_manager.set_admin_state(user_id, 'broadcast_message')
    bot.send_message(user_id, "📢 **ارسال پیام همگانی**\n\nلطفاً پیام خود را وارد کنید:")

def add_admin_start(user_id):
    """شروع افزودن ادمین جدید"""
    state_manager.set_admin_state(user_id, 'add_admin')
    bot.send_message(user_id, "➕ **افزودن ادمین جدید**\n\nلطفاً آی‌دی عددی کاربر را وارد کنید:")

# ==========================================
# کال‌بک‌های ربات
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user_id = str(call.from_user.id)
    data = call.data
    
    try:
        # کال‌بک‌های کاربران
        if data.startswith("buy_vip_"):
            plan_id = data.split("_")[2]
            process_vip_purchase(user_id, plan_id)
        
        elif data == "insufficient_coins":
            bot.answer_callback_query(call.id, "❌ سکه کافی ندارید!")
        
        elif data.startswith("play_game_"):
            game_id = data.split("_")[2]
            play_game_callback(user_id, game_id)
        
        elif data == "user_play_game":
            show_games_menu(user_id)
        
        elif data == "user_invite_friends":
            show_referral_system(user_id)
        
        # کال‌بک‌های ادمین
        elif data.startswith("admin_"):
            handle_admin_callback(user_id, data)
        
        elif data.startswith("vip_"):
            handle_vip_callback(user_id, data)
        
        elif data.startswith("finance_"):
            handle_finance_callback(user_id, data)
        
        elif data.startswith("settings_"):
            handle_settings_callback(user_id, data)
        
        elif data.startswith("tools_"):
            handle_tools_callback(user_id, data)
        
        elif data.startswith("event_"):
            handle_event_callback(user_id, data)
        
        elif data.startswith("report_"):
            handle_report_callback(user_id, data)
        
        bot.answer_callback_query(call.id)
    
    except Exception as e:
        print(f"Error in callback: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در پردازش!")

# ==========================================
# پردازش خرید VIP
# ==========================================
def process_vip_purchase(user_id, plan_id):
    """پردازش خرید VIP"""
    user = db.get_user(user_id)
    if not user:
        bot.send_message(user_id, "❌ شما ثبت‌نام نکرده‌اید!")
        return
    
    plans = db.get_vip_plans()
    if plan_id not in plans:
        bot.send_message(user_id, "❌ پلن یافت نشد!")
        return
    
    plan = plans[plan_id]
    
    # محاسبه قیمت با تخفیف
    base_price = plan.get('price', 0)
    final_price = pricing.calculate_dynamic_price(base_price, user_id)
    bonus = plan.get('bonus', 0)
    days = plan.get('days', 0)
    
    if user.get('coins', 0) < final_price:
        bot.send_message(user_id, f"❌ سکه کافی ندارید!\n💰 نیاز: {final_price:,}\n💰 موجودی: {user.get('coins', 0):,}")
        return
    
    # پردازش خرید
    user['coins'] = user.get('coins', 0) - final_price
    user['coins'] += bonus  # سکه هدیه
    
    # اعطای VIP
    vip_end = user.get('vip_end', 0)
    if vip_end < time.time():
        vip_end = time.time()
    
    user['vip_end'] = vip_end + (days * 24 * 3600)
    user['total_spent'] = user.get('total_spent', 0) + final_price
    
    db.save_user(user_id, user)
    
    # ثبت تراکنش
    transaction_id = f"vip_{int(time.time())}_{random.randint(1000, 9999)}"
    db.add_transaction(transaction_id, {
        'user_id': user_id,
        'type': 'vip_purchase',
        'plan_id': plan_id,
        'plan_name': plan.get('name'),
        'amount': final_price,
        'bonus': bonus,
        'days': days,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # به‌روزرسانی آمار
    db.increment_stat('total_transactions')
    db.increment_stat('total_coins', -final_price + bonus)
    
    # به‌روزرسانی تعداد VIP‌ها
    stats = db.get_stats()
    vip_users = db.count_vip_users()
    stats['total_vip'] = vip_users
    db.save_stats(stats)
    
    # اطلاع به ادمین‌ها
    notification.send_vip_purchased_notification(user_id, plan.get('name'), final_price)
    
    # ارسال پیام موفقیت
    expiry_date = datetime.fromtimestamp(user['vip_end']).strftime('%Y/%m/%d')
    
    message = f"""
✅ **خرید موفق!**

🎖 پلن: {plan.get('name')}
💰 مبلغ پرداختی: {final_price:,} سکه
🎁 سکه هدیه: {bonus} سکه
📅 مدت: {days} روز
📅 انقضا: {expiry_date}

💰 موجودی جدید: {user['coins']:,} سکه
    """
    
    bot.send_message(user_id, message)
    
    # ارسال لینک دعوت ویژه برای VIP
    if days >= 30:  # برای VIP های ماهانه به بالا
        invite_link = f"https://t.me/{bot.get_me().username}?start=vip_ref_{user_id}"
        bot.send_message(
            user_id,
            f"🎉 **تبریک! شما VIP شدید!**\n\n"
            f"🔗 لینک دعوت ویژه VIP:\n"
            f"`{invite_link}`\n\n"
            f"با این لینک دوستان خود را دعوت کنید و پاداش بیشتری دریافت کنید!"
        )

# ==========================================
# پردازش بازی
# ==========================================
def play_game_callback(user_id, game_id):
    """پردازش بازی"""
    success, result = games.play_game(user_id, game_id)
    
    if not success:
        bot.send_message(user_id, result)
        return
    
    # نمایش نتیجه
    result_text = f"""
🎰 **نتیجه بازی {result['game']}**

{result['result']}

💰 هزینه: {result['cost']} سکه
🎁 جایزه: {result['prize']} سکه
📊 سود/زیان: {result['net_gain']} سکه
💰 موجودی جدید: {result['new_balance']:,} سکه
    """
    
    if result['is_vip']:
        result_text += "\n⭐ شما VIP هستید! شانس برد بیشتری دارید."
    
    bot.send_message(user_id, result_text)

# ==========================================
# کال‌بک‌های مدیریت کاربران
# ==========================================
def handle_admin_callback(user_id, data):
    """پردازش کال‌بک‌های مدیریت کاربران"""
    if data == "admin_users_list":
        list_users_admin(user_id)
    
    elif data == "admin_users_search":
        state_manager.set_admin_state(user_id, 'search_user')
        bot.send_message(user_id, "🔍 **جستجوی کاربر**\n\nلطفاً آی‌دی یا نام کاربر را وارد کنید:")
    
    elif data == "admin_user_report":
        state_manager.set_admin_state(user_id, 'user_report')
        bot.send_message(user_id, "📊 **گزارش کاربر**\n\nلطفاً آی‌دی کاربر را وارد کنید:")
    
    elif data == "admin_coins_manage":
        show_coins_management_menu(user_id)
    
    elif data == "admin_ban_manage":
        show_ban_management_menu(user_id)
    
    elif data == "admin_warn_manage":
        show_warn_management_menu(user_id)
    
    elif data == "admin_user_delete":
        state_manager.set_admin_state(user_id, 'delete_user')
        bot.send_message(user_id, "🗑️ **حذف کاربر**\n\nلطفاً آی‌دی کاربر را وارد کنید:")
    
    elif data == "admin_user_message":
        state_manager.set_admin_state(user_id, 'message_user')
        bot.send_message(user_id, "📧 **پیام به کاربر**\n\nلطفاً آی‌دی کاربر را وارد کنید:")

def list_users_admin(user_id):
    """لیست کاربران برای ادمین"""
    users = db.get_all_users()
    
    if not users:
        bot.send_message(user_id, "📭 هیچ کاربری وجود ندارد.")
        return
    
    text = "📋 **لیست کاربران**\n\n"
    
    for i, (uid, user_data) in enumerate(list(users.items())[:15], 1):
        is_vip = user_data.get('vip_end', 0) > time.time()
        is_banned = db.is_banned(uid)
        
        vip_status = "🎖" if is_vip else "👤"
        ban_status = "🚫" if is_banned else "✅"
        
        text += f"{i}. {user_data.get('name', 'بدون نام')}\n"
        text += f"   🆔: `{uid}`\n"
        text += f"   🪙: {user_data.get('coins', 0):,}\n"
        text += f"   {vip_status} {ban_status}\n\n"
    
    bot.send_message(user_id, text)

def show_coins_management_menu(user_id):
    """نمایش منوی مدیریت سکه"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("➕ افزودن سکه", callback_data="coins_add"),
        types.InlineKeyboardButton("➖ کسر سکه", callback_data="coins_remove")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 هدیه گروهی", callback_data="coins_bulk_gift"),
        types.InlineKeyboardButton("📊 آمار سکه‌ها", callback_data="coins_stats")
    )
    
    bot.send_message(user_id, "💰 **مدیریت سکه**", reply_markup=markup)

def show_ban_management_menu(user_id):
    """نمایش منوی مدیریت بن"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("🚫 بن کردن", callback_data="ban_user"),
        types.InlineKeyboardButton("✅ آزاد کردن", callback_data="unban_user")
    )
    markup.add(
        types.InlineKeyboardButton("📋 لیست بن‌ها", callback_data="ban_list"),
        types.InlineKeyboardButton("⏰ بن موقت", callback_data="ban_temporary")
    )
    
    bot.send_message(user_id, "🚫 **مدیریت بن کاربران**", reply_markup=markup)

def show_warn_management_menu(user_id):
    """نمایش منوی مدیریت اخطار"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("⚠️ افزودن اخطار", callback_data="warn_add"),
        types.InlineKeyboardButton("✅ حذف اخطار", callback_data="warn_remove")
    )
    markup.add(
        types.InlineKeyboardButton("📋 اخطارهای کاربر", callback_data="warn_list"),
        types.InlineKeyboardButton("🔄 ریست اخطارها", callback_data="warn_reset")
    )
    
    bot.send_message(user_id, "⚠️ **مدیریت اخطارها**", reply_markup=markup)

# ==========================================
# کال‌بک‌های مدیریت VIP
# ==========================================
def handle_vip_callback(user_id, data):
    """پردازش کال‌بک‌های مدیریت VIP"""
    if data == "vip_add_plan":
        state_manager.set_admin_state(user_id, 'add_vip_plan')
        bot.send_message(user_id, "➕ **افزودن پلن VIP جدید**\n\nلطفاً اطلاعات را وارد کنید:\nفرمت: نام|قیمت|روز|هدیه\nمثال: VIP ویژه|5000|30|200")
    
    elif data == "vip_edit_plan":
        edit_vip_plan_list(user_id)
    
    elif data == "vip_delete_plan":
        delete_vip_plan_list(user_id)
    
    elif data == "vip_list_plans":
        list_vip_plans_admin(user_id)
    
    elif data == "vip_set_prices":
        set_vip_prices_menu(user_id)
    
    elif data == "vip_give_free":
        state_manager.set_admin_state(user_id, 'give_free_vip')
        bot.send_message(user_id, "🎁 **اعطای VIP رایگان**\n\nلطفاً اطلاعات را وارد کنید:\nفرمت: آی‌دی کاربر|روز\nمثال: 123456789|30")
    
    elif data == "vip_stats":
        show_vip_stats_admin(user_id)
    
    elif data == "vip_bulk_renew":
        state_manager.set_admin_state(user_id, 'bulk_renew_vip')
        bot.send_message(user_id, "🔄 **تمدید دسته‌ای VIP**\n\nلطفاً تعداد روز را وارد کنید:\nتمامی کاربران VIP این تعداد روز تمدید می‌شوند.")

def edit_vip_plan_list(user_id):
    """لیست پلن‌ها برای ویرایش"""
    plans = db.get_vip_plans()
    
    if not plans:
        bot.send_message(user_id, "📭 هیچ پلن VIP‌ای وجود ندارد.")
        return
    
    text = "✏️ **لیست پلن‌ها برای ویرایش**\n\n"
    
    for plan_id, plan in plans.items():
        text += f"🆔 {plan_id}: {plan.get('name')} - {plan.get('price'):,} سکه\n"
    
    state_manager.set_admin_state(user_id, 'edit_vip_plan')
    bot.send_message(user_id, text + "\nلطفاً کد پلن را برای ویرایش وارد کنید:")

def delete_vip_plan_list(user_id):
    """لیست پلن‌ها برای حذف"""
    plans = db.get_vip_plans()
    
    if not plans:
        bot.send_message(user_id, "📭 هیچ پلن VIP‌ای وجود ندارد.")
        return
    
    text = "🗑️ **لیست پلن‌ها برای حذف**\n\n"
    
    for plan_id, plan in plans.items():
        text += f"🆔 {plan_id}: {plan.get('name')} - {plan.get('price'):,} سکه\n"
    
    state_manager.set_admin_state(user_id, 'delete_vip_plan_id')
    bot.send_message(user_id, text + "\nلطفاً کد پلن را برای حذف وارد کنید:")

def list_vip_plans_admin(user_id):
    """لیست پلن‌های VIP برای ادمین"""
    plans = db.get_vip_plans()
    
    if not plans:
        bot.send_message(user_id, "📭 هیچ پلن VIP‌ای وجود ندارد.")
        return
    
    text = "📋 **لیست پلن‌های VIP**\n\n"
    
    for plan_id, plan in plans.items():
        text += f"🆔 **کد: {plan_id}**\n"
        text += f"📛 نام: {plan.get('name')}\n"
        text += f"💰 قیمت پایه: {plan.get('price'):,} سکه\n"
        text += f"📅 مدت: {plan.get('days')} روز\n"
        text += f"🎁 هدیه: {plan.get('bonus')} سکه\n"
        
        features = plan.get('features', [])
        if features:
            text += "✨ ویژگی‌ها:\n"
            for feature in features[:3]:
                text += f"• {feature}\n"
        
        text += "\n"
    
    bot.send_message(user_id, text)

def set_vip_prices_menu(user_id):
    """منوی تنظیم قیمت VIP"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("💰 افزایش قیمت", callback_data="vip_increase_price"),
        types.InlineKeyboardButton("💎 کاهش قیمت", callback_data="vip_decrease_price")
    )
    markup.add(
        types.InlineKeyboardButton("🎯 قیمت خاص", callback_data="vip_specific_price"),
        types.InlineKeyboardButton("📊 تحلیل قیمت", callback_data="vip_price_analysis")
    )
    
    bot.send_message(user_id, "💰 **تنظیم قیمت VIP**", reply_markup=markup)

def show_vip_stats_admin(user_id):
    """نمایش آمار VIP برای ادمین"""
    vip_users = db.count_vip_users()
    total_users = db.count_users()
    
    plans = db.get_vip_plans()
    plan_stats = {}
    
    for plan_id, plan in plans.items():
        plan_stats[plan_id] = {
            'name': plan.get('name'),
            'price': plan.get('price'),
            'count': 0,
            'revenue': 0
        }
    
    # محاسبه آمار هر پلن
    users = db.get_all_users()
    for user_data in users.values():
        if user_data.get('vip_end', 0) > time.time():
            # در واقعیت باید تراکنش‌ها را بررسی کرد
            pass
    
    text = f"""
📊 **آمار VIP**

👥 کاربران VIP: {vip_users}
👤 کل کاربران: {total_users}
📈 درصد VIP: {(vip_users/total_users*100 if total_users > 0 else 0):.1f}%

💰 درآمد تخمینی VIP: {vip_users * 1000:,} سکه

🎖 **توزیع پلن‌ها:**
    """
    
    for plan_id, stats in plan_stats.items():
        text += f"\n📛 {stats['name']}: {stats['count']} کاربر"
    
    bot.send_message(user_id, text)

# ==========================================
# کال‌بک‌های مدیریت مالی
# ==========================================
def handle_finance_callback(user_id, data):
    """پردازش کال‌بک‌های مدیریت مالی"""
    if data == "finance_add_coins":
        state_manager.set_admin_state(user_id, 'add_coins')
        bot.send_message(user_id, "💰 **افزودن سکه**\n\nلطفاً اطلاعات را وارد کنید:\nفرمت: آی‌دی کاربر|مقدار\nمثال: 123456789|1000")
    
    elif data == "finance_remove_coins":
        state_manager.set_admin_state(user_id, 'remove_coins')
        bot.send_message(user_id, "➖ **کسر سکه**\n\nلطفاً اطلاعات را وارد کنید:\nفرمت: آی‌دی کاربر|مقدار\nمثال: 123456789|500")
    
    elif data == "finance_bulk_gift":
        state_manager.set_admin_state(user_id, 'bulk_gift')
        bot.send_message(user_id, "🎁 **هدیه گروهی**\n\nلطفاً مقدار سکه را وارد کنید:\nبه تمام کاربران فعال این مقدار سکه داده می‌شود.")
    
    elif data == "finance_stats":
        show_finance_stats(user_id)
    
    elif data == "finance_transactions":
        show_recent_transactions(user_id)
    
    elif data == "finance_set_rewards":
        set_rewards_menu(user_id)
    
    elif data == "finance_set_games":
        set_games_menu(user_id)
    
    elif data == "finance_reset":
        confirm_financial_reset(user_id)
    
    elif data == "finance_backup":
        create_financial_backup(user_id)

def show_finance_stats(user_id):
    """نمایش آمار مالی"""
    stats = db.get_stats()
    total_coins = db.get_total_coins()
    
    text = f"""
💰 **آمار مالی**

📊 کلی:
├─ کل سکه‌ها: {total_coins:,}
├─ کل تراکنش‌ها: {stats.get('total_transactions', 0)}
├─ درآمد امروز: {stats.get('daily_income', 0):,}
├─ درآمد این هفته: {stats.get('weekly_income', 0):,}
└─ درآمد این ماه: {stats.get('monthly_income', 0):,}

👥 سرانه:
├─ میانگین سکه هر کاربر: {total_coins // db.count_users() if db.count_users() > 0 else 0:,}
├─ میانگین تراکنش: {stats.get('total_transactions', 0) // db.count_users() if db.count_users() > 0 else 0}
└─ رشد روزانه: {(stats.get('daily_income', 0) / total_coins * 100 if total_coins > 0 else 0):.1f}%

📈 پیش‌بینی:
├─ درآمد هفته آینده: {stats.get('weekly_income', 0) * 1.1:,.0f}
├─ درآمد ماه آینده: {stats.get('monthly_income', 0) * 1.05:,.0f}
└─ سکه در ۳۰ روز: {total_coins * 1.15:,.0f}
    """
    
    bot.send_message(user_id, text)

def show_recent_transactions(user_id):
    """نمایش تراکنش‌های اخیر"""
    transactions = db.get_transactions()
    
    if not transactions:
        bot.send_message(user_id, "📭 هیچ تراکنشی ثبت نشده است.")
        return
    
    text = "📈 **تراکنش‌های اخیر**\n\n"
    
    # مرتب‌سازی بر اساس زمان
    sorted_transactions = sorted(
        transactions.items(),
        key=lambda x: x[1].get('timestamp', ''),
        reverse=True
    )[:10]  # ۱۰ تراکنش آخر
    
    for trans_id, trans_data in sorted_transactions:
        trans_type = trans_data.get('type', 'unknown')
        amount = trans_data.get('amount', 0)
        timestamp = trans_data.get('timestamp', 'نامشخص')
        
        type_emoji = {
            'vip_purchase': '🎖',
            'game': '🎰',
            'reward': '🎁',
            'manual': '🛡️'
        }.get(trans_type, '💰')
        
        text += f"{type_emoji} {trans_type}: {amount:,} سکه\n"
        text += f"   ⏰ {timestamp}\n\n"
    
    bot.send_message(user_id, text)

def set_rewards_menu(user_id):
    """منوی تنظیم پاداش‌ها"""
    settings = db.get_settings()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton(f"🎁 دعوت: {settings.get('referral_reward', 50)}", callback_data="reward_referral"),
        types.InlineKeyboardButton(f"⭐ VIP روزانه: {settings.get('daily_reward_vip', 100)}", callback_data="reward_daily_vip")
    )
    markup.add(
        types.InlineKeyboardButton(f"👤 عادی روزانه: {settings.get('daily_reward_normal', 10)}", callback_data="reward_daily_normal"),
        types.InlineKeyboardButton(f"🎖 وفاداری VIP", callback_data="reward_vip_loyalty")
    )
    
    bot.send_message(user_id, "🎁 **تنظیم پاداش‌ها**", reply_markup=markup)

def set_games_menu(user_id):
    """منوی تنظیم بازی‌ها"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for game_id, game in games.games.items():
        button_text = f"{game['name']} ({game['cost']})"
        callback_data = f"game_set_{game_id}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))
    
    bot.send_message(user_id, "🎰 **تنظیم بازی‌ها**", reply_markup=markup)

def confirm_financial_reset(user_id):
    """تأیید ریست مالی"""
    markup = types.InlineKeyboardMarkup()
    
    markup.add(
        types.InlineKeyboardButton("✅ بله، ریست کن", callback_data="confirm_finance_reset"),
        types.InlineKeyboardButton("❌ خیر، لغو", callback_data="cancel_finance_reset")
    )
    
    bot.send_message(user_id, "⚠️ **هشدار!**\nآیا مطمئن هستید که می‌خواهید آمار مالی را ریست کنید؟\nاین عمل غیرقابل بازگشت است!", reply_markup=markup)

def create_financial_backup(user_id):
    """ایجاد بکاپ مالی"""
    success = db.create_backup()
    
    if success:
        bot.send_message(user_id, "✅ بکاپ مالی با موفقیت ایجاد شد.")
    else:
        bot.send_message(user_id, "❌ خطا در ایجاد بکاپ.")

# ==========================================
# کال‌بک‌های تنظیمات
# ==========================================
def handle_settings_callback(user_id, data):
    """پردازش کال‌بک‌های تنظیمات"""
    if data == "settings_maintenance":
        toggle_maintenance_mode(user_id)
    
    elif data == "settings_master_pass":
        state_manager.set_admin_state(user_id, 'change_master_pass')
        bot.send_message(user_id, "🔐 **تغییر رمز اصلی**\n\nلطفاً رمز جدید را وارد کنید:")
    
    elif data == "settings_bot_name":
        state_manager.set_admin_state(user_id, 'change_bot_name')
        bot.send_message(user_id, "📛 **تغییر نام ربات**\n\nلطفاً نام جدید را وارد کنید:")
    
    elif data == "settings_welcome_msg":
        state_manager.set_admin_state(user_id, 'change_welcome_msg')
        bot.send_message(user_id, "💬 **تغییر پیام خوش‌آمد**\n\nلطفاً پیام جدید را وارد کنید:")
    
    elif data == "settings_rewards":
        set_rewards_menu(user_id)
    
    elif data == "settings_limits":
        set_limits_menu(user_id)
    
    elif data == "settings_reset_data":
        confirm_full_reset(user_id)
    
    elif data == "settings_full_backup":
        create_full_backup(user_id)

def toggle_maintenance_mode(user_id):
    """تغییر حالت تعمیر"""
    settings = db.get_settings()
    
    if settings.get('maintenance_mode', False):
        db.set_maintenance(False, "")
        bot.send_message(user_id, "✅ حالت تعمیر غیرفعال شد.")
    else:
        state_manager.set_admin_state(user_id, 'set_maintenance_reason')
        bot.send_message(user_id, "🔧 **فعال کردن حالت تعمیر**\n\nلطفاً دلیل تعمیر را وارد کنید:")

def set_limits_menu(user_id):
    """منوی تنظیم محدودیت‌ها"""
    settings = db.get_settings()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton(f"⚠️ اخطارها: {settings.get('max_warns', 3)}", callback_data="limit_warns"),
        types.InlineKeyboardButton(f"💰 حداقل برداشت: {settings.get('min_coins_for_withdraw', 1000):,}", callback_data="limit_withdraw")
    )
    markup.add(
        types.InlineKeyboardButton(f"🎰 حداکثر بازی روزانه", callback_data="limit_daily_games"),
        types.InlineKeyboardButton(f"📊 محدودیت درآمد", callback_data="limit_income")
    )
    
    bot.send_message(user_id, "⚖️ **تنظیم محدودیت‌ها**", reply_markup=markup)

def confirm_full_reset(user_id):
    """تأیید ریست کامل داده"""
    markup = types.InlineKeyboardMarkup()
    
    markup.add(
        types.InlineKeyboardButton("✅ بله، همه چیز را پاک کن", callback_data="confirm_full_reset"),
        types.InlineKeyboardButton("❌ خیر، لغو", callback_data="cancel_full_reset")
    )
    
    bot.send_message(user_id, "⚠️ **هشدار شدید!**\nآیا مطمئن هستید که می‌خواهید تمام داده‌ها را پاک کنید؟\nاین عمل تمام کاربران، تراکنش‌ها و آمار را پاک می‌کند!", reply_markup=markup)

def create_full_backup(user_id):
    """ایجاد بکاپ کامل"""
    success = db.create_backup()
    
    if success:
        # لیست فایل‌های بکاپ
        backup_files = sorted([f for f in os.listdir('backups') if f.startswith('backup_')])
        
        if backup_files:
            latest_backup = backup_files[-1]
            text = f"✅ بکاپ کامل ایجاد شد.\n📁 آخرین بکاپ: `{latest_backup}`\n📊 تعداد بکاپ‌ها: {len(backup_files)}"
        else:
            text = "✅ بکاپ کامل ایجاد شد."
        
        bot.send_message(user_id, text)
    else:
        bot.send_message(user_id, "❌ خطا در ایجاد بکاپ.")

# ==========================================
# کال‌بک‌های ابزارها
# ==========================================
def handle_tools_callback(user_id, data):
    """پردازش کال‌بک‌های ابزارها"""
    if data == "tools_check_vip":
        check_vip_expiries(user_id)
    
    elif data == "tools_cleanup":
        cleanup_data(user_id)
    
    elif data == "tools_update_stats":
        update_all_stats(user_id)
    
    elif data == "tools_check_errors":
        check_system_errors(user_id)
    
    elif data == "tools_export_excel":
        export_to_excel(user_id)
    
    elif data == "tools_import_data":
        import_data_menu(user_id)

def check_vip_expiries(user_id):
    """بررسی انقضای VIP کاربران"""
    users = db.get_all_users()
    expiring_soon = []
    expired = []
    
    now = time.time()
    
    for uid, user_data in users.items():
        vip_end = user_data.get('vip_end', 0)
        
        if vip_end > now:
            days_left = get_vip_days_left(vip_end)
            if days_left <= 3:
                expiring_soon.append((uid, user_data.get('name', 'بدون نام'), days_left))
        elif vip_end > 0 and vip_end <= now:
            expired.append((uid, user_data.get('name', 'بدون نام')))
    
    text = "🔄 **بررسی انقضای VIP**\n\n"
    
    if expiring_soon:
        text += "⚠️ **در حال انقضا (کمتر از ۳ روز):**\n"
        for uid, name, days in expiring_soon[:10]:  # فقط ۱۰ کاربر اول
            text += f"👤 {name} ({uid}): {days} روز\n"
        
        if len(expiring_soon) > 10:
            text += f"\nو {len(expiring_soon) - 10} کاربر دیگر...\n"
    
    if expired:
        text += "\n❌ **منقضی شده:**\n"
        for uid, name in expired[:10]:
            text += f"👤 {name} ({uid})\n"
        
        if len(expired) > 10:
            text += f"\nو {len(expired) - 10} کاربر دیگر...\n"
    
    if not expiring_soon and not expired:
        text += "✅ همه VIP ها معتبر هستند."
    
    bot.send_message(user_id, text)

def cleanup_data(user_id):
    """پاک‌سازی داده‌های قدیمی"""
    # اینجا می‌توانید منطق پاک‌سازی را اضافه کنید
    bot.send_message(user_id, "🧹 **پاک‌سازی داده‌ها**\n\nاین قابلیت در حال توسعه است.")

def update_all_stats(user_id):
    """به‌روزرسانی تمام آمار"""
    # به‌روزرسانی آمار
    total_users = db.count_users()
    vip_users = db.count_vip_users()
    total_coins = db.get_total_coins()
    
    stats = db.get_stats()
    stats['total_users'] = total_users
    stats['total_vip'] = vip_users
    stats['total_coins'] = total_coins
    db.save_stats(stats)
    
    bot.send_message(user_id, f"✅ آمار به‌روزرسانی شد:\n👥 کاربران: {total_users}\n⭐ VIP: {vip_users}\n💰 سکه: {total_coins:,}")

def check_system_errors(user_id):
    """بررسی خطاهای سیستم"""
    # بررسی فایل‌ها
    errors = []
    
    for filename in ['users.json', 'admins.json', 'vip_plans.json', 'settings.json']:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                json.load(f)
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")
    
    # بررسی پوشه بکاپ
    if not os.path.exists('backups'):
        errors.append("پوشه backups وجود ندارد")
    
    if errors:
        text = "❌ **خطاهای یافت شده:**\n\n"
        for error in errors:
            text += f"• {error}\n"
    else:
        text = "✅ سیستم سالم است. هیچ خطایی یافت نشد."
    
    bot.send_message(user_id, text)

def export_to_excel(user_id):
    """خروجی به Excel"""
    bot.send_message(user_id, "📤 **خروجی Excel**\n\nاین قابلیت در حال توسعه است.")

def import_data_menu(user_id):
    """منوی وارد کردن داده"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📥 وارد کردن کاربران", callback_data="import_users"),
        types.InlineKeyboardButton("💾 بازیابی بکاپ", callback_data="import_backup")
    )
    
    bot.send_message(user_id, "📥 **وارد کردن داده**", reply_markup=markup)

# ==========================================
# کال‌بک‌های رویدادها
# ==========================================
def handle_event_callback(user_id, data):
    """پردازش کال‌بک‌های رویدادها"""
    if data == "event_create":
        state_manager.set_admin_state(user_id, 'create_event')
        bot.send_message(user_id, "➕ **ایجاد رویداد جدید**\n\nلطفاً اطلاعات را وارد کنید:\nفرمت: نام|توضیح|تاریخ پایان|جایزه\nمثال: قرعه‌کشی بزرگ|شرکت در قرعه‌کشی|2024-12-31|1000 سکه")
    
    elif data == "event_edit":
        edit_event_list(user_id)
    
    elif data == "event_delete":
        delete_event_list(user_id)
    
    elif data == "event_list":
        list_events_admin(user_id)
    
    elif data == "event_discount":
        set_event_discount(user_id)
    
    elif data == "event_stats":
        show_event_stats(user_id)

def edit_event_list(user_id):
    """لیست رویدادها برای ویرایش"""
    events = db.get_events()
    
    if not events:
        bot.send_message(user_id, "📭 هیچ رویدادی وجود ندارد.")
        return
    
    text = "✏️ **لیست رویدادها برای ویرایش**\n\n"
    
    for event_id, event in events.items():
        text += f"🆔 {event_id}: {event.get('name')}\n"
    
    state_manager.set_admin_state(user_id, 'edit_event')
    bot.send_message(user_id, text + "\nلطفاً کد رویداد را برای ویرایش وارد کنید:")

def delete_event_list(user_id):
    """لیست رویدادها برای حذف"""
    events = db.get_events()
    
    if not events:
        bot.send_message(user_id, "📭 هیچ رویدادی وجود ندارد.")
        return
    
    text = "🗑️ **لیست رویدادها برای حذف**\n\n"
    
    for event_id, event in events.items():
        text += f"🆔 {event_id}: {event.get('name')}\n"
    
    state_manager.set_admin_state(user_id, 'delete_event')
    bot.send_message(user_id, text + "\nلطفاً کد رویداد را برای حذف وارد کنید:")

def list_events_admin(user_id):
    """لیست رویدادها برای ادمین"""
    events = db.get_events()
    
    if not events:
        bot.send_message(user_id, "📭 هیچ رویدادی وجود ندارد.")
        return
    
    text = "📋 **لیست رویدادها**\n\n"
    
    for event_id, event in events.items():
        active = event.get('active', False)
        status = "✅ فعال" if active else "❌ غیرفعال"
        
        text += f"🎪 **{event.get('name')}**\n"
        text += f"🆔 کد: {event_id}\n"
        text += f"📝 {event.get('description', 'بدون توضیح')}\n"
        text += f"🎁 جایزه: {event.get('prize', 'ندارد')}\n"
        text += f"📅 پایان: {event.get('end_date', 'نامشخص')}\n"
        text += f"📊 وضعیت: {status}\n\n"
    
    bot.send_message(user_id, text)

def set_event_discount(user_id):
    """تنظیم تخفیف رویداد"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("🎪 تخفیف VIP", callback_data="event_discount_vip"),
        types.InlineKeyboardButton("💰 تخفیف عمومی", callback_data="event_discount_general")
    )
    
    bot.send_message(user_id, "🎯 **تنظیم تخفیف رویداد**", reply_markup=markup)

def show_event_stats(user_id):
    """نمایش آمار رویدادها"""
    events = db.get_events()
    
    if not events:
        bot.send_message(user_id, "📭 هیچ رویدادی وجود ندارد.")
        return
    
    active_count = 0
    total_prizes = 0
    
    for event in events.values():
        if event.get('active', False):
            active_count += 1
            prize = event.get('prize', 0)
            if isinstance(prize, int):
                total_prizes += prize
    
    text = f"""
📊 **آمار رویدادها**

🎪 تعداد رویدادها: {len(events)}
✅ رویدادهای فعال: {active_count}
❌ رویدادهای غیرفعال: {len(events) - active_count}
🎁 مجموع جوایز: {total_prizes:,} سکه

📅 **رویدادهای فعال:**
    """
    
    now = datetime.now()
    
    for event_id, event in events.items():
        if event.get('active', False):
            end_date = datetime.strptime(event.get('end_date'), '%Y-%m-%d')
            days_left = (end_date - now).days
            
            if days_left >= 0:
                text += f"\n🎪 {event.get('name')}: {days_left} روز باقی مانده"
    
    bot.send_message(user_id, text)

# ==========================================
# کال‌بک‌های گزارش‌گیری
# ==========================================
def handle_report_callback(user_id, data):
    """پردازش کال‌بک‌های گزارش‌گیری"""
    if data == "report_financial":
        show_financial_report(user_id)
    
    elif data == "report_users":
        show_users_report(user_id)
    
    elif data == "report_vip":
        show_vip_report(user_id)
    
    elif data == "report_games":
        show_games_report(user_id)
    
    elif data == "report_growth":
        show_growth_report(user_id)
    
    elif data == "report_export":
        export_reports(user_id)

def show_financial_report(user_id):
    """نمایش گزارش مالی"""
    stats = db.get_stats()
    total_coins = db.get_total_coins()
    
    text = f"""
💰 **گزارش مالی کامل**

📊 **کلیات:**
├─ کل سکه‌های سیستم: {total_coins:,}
├─ کل تراکنش‌ها: {stats.get('total_transactions', 0)}
├─ میانگین تراکنش: {stats.get('total_transactions', 0) // db.count_users() if db.count_users() > 0 else 0}
└─ سرانه سکه: {total_coins // db.count_users() if db.count_users() > 0 else 0:,}

📈 **درآمدها:**
├─ امروز: {stats.get('daily_income', 0):,}
├─ این هفته: {stats.get('weekly_income', 0):,}
├─ این ماه: {stats.get('monthly_income', 0):,}
└─ کل زمان: {stats.get('total_income', 0):,}

📉 **هزینه‌ها:**
├─ پاداش‌ها: {stats.get('total_rewards', 0):,}
├─ جوایز: {stats.get('total_prizes', 0):,}
├─ بازپرداخت‌ها: {stats.get('total_refunds', 0):,}
└─ سایر: {stats.get('other_costs', 0):,}

📊 **سود خالص:**
└─ {(stats.get('total_income', 0) - stats.get('total_rewards', 0) - stats.get('total_prizes', 0) - stats.get('total_refunds', 0) - stats.get('other_costs', 0)):,} سکه
    """
    
    bot.send_message(user_id, text)

def show_users_report(user_id):
    """نمایش گزارش کاربران"""
    users = db.get_all_users()
    total_users = len(users)
    vip_users = db.count_vip_users()
    
    # تحلیل سن
    age_groups = {'زیر 18': 0, '18-25': 0, '26-35': 0, '36-50': 0, 'بالای 50': 0}
    genders = {'مرد': 0, 'زن': 0}
    
    for user_data in users.values():
        age = user_data.get('age', 0)
        gender = user_data.get('gender', 'نامشخص')
        
        if age < 18:
            age_groups['زیر 18'] += 1
        elif 18 <= age <= 25:
            age_groups['18-25'] += 1
        elif 26 <= age <= 35:
            age_groups['26-35'] += 1
        elif 36 <= age <= 50:
            age_groups['36-50'] += 1
        else:
            age_groups['بالای 50'] += 1
        
        if gender in genders:
            genders[gender] += 1
    
    text = f"""
👥 **گزارش کاربران**

📊 **کلیات:**
├─ کل کاربران: {total_users}
├─ کاربران VIP: {vip_users}
├─ کاربران عادی: {total_users - vip_users}
└─ درصد VIP: {(vip_users/total_users*100 if total_users > 0 else 0):.1f}%

👤 **تحلیل جنسیت:**
├─ مرد: {genders['مرد']} ({(genders['مرد']/total_users*100 if total_users > 0 else 0):.1f}%)
├─ زن: {genders['زن']} ({(genders['زن']/total_users*100 if total_users > 0 else 0):.1f}%)
└─ نامشخص: {total_users - genders['مرد'] - genders['زن']}

🎂 **تحلیل سن:**
    """
    
    for group, count in age_groups.items():
        percentage = (count/total_users*100 if total_users > 0 else 0)
        text += f"\n├─ {group}: {count} ({percentage:.1f}%)"
    
    # تحلیل فعالیت
    active_users = 0
    for user_data in users.values():
        last_seen = user_data.get('last_seen', '')
        if last_seen:
            try:
                last_date = datetime.strptime(last_seen, '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - last_date).days <= 7:
                    active_users += 1
            except:
                pass
    
    text += f"\n\n📈 **فعالیت:**\n"
    text += f"├─ کاربران فعال (۷ روز): {active_users}\n"
    text += f"└─ نرخ فعالیت: {(active_users/total_users*100 if total_users > 0 else 0):.1f}%"
    
    bot.send_message(user_id, text)

def show_vip_report(user_id):
    """نمایش گزارش VIP"""
    vip_users = db.get_vip_users()
    total_vip = len(vip_users)
    
    # تحلیل مدت VIP
    duration_groups = {'کمتر از ۷ روز': 0, '۷-۳۰ روز': 0, '۳۱-۹۰ روز': 0, '۹۱-۱۸۰ روز': 0, 'بالای ۱۸۰ روز': 0}
    
    now = time.time()
    for uid in vip_users:
        user = db.get_user(uid)
        if user:
            vip_end = user.get('vip_end', 0)
            days_left = get_vip_days_left(vip_end)
            
            if days_left < 7:
                duration_groups['کمتر از ۷ روز'] += 1
            elif 7 <= days_left <= 30:
                duration_groups['۷-۳۰ روز'] += 1
            elif 31 <= days_left <= 90:
                duration_groups['۳۱-۹۰ روز'] += 1
            elif 91 <= days_left <= 180:
                duration_groups['۹۱-۱۸۰ روز'] += 1
            else:
                duration_groups['بالای ۱۸۰ روز'] += 1
    
    text = f"""
🎖 **گزارش VIP**

📊 **کلیات:**
├─ کل کاربران VIP: {total_vip}
├─ درصد از کل کاربران: {(total_vip/db.count_users()*100 if db.count_users() > 0 else 0):.1f}%
└─ درآمد تخمینی: {total_vip * 1000:,} سکه

📅 **مدت باقی‌مانده:**
    """
    
    for group, count in duration_groups.items():
        percentage = (count/total_vip*100 if total_vip > 0 else 0)
        text += f"\n├─ {group}: {count} ({percentage:.1f}%)"
    
    # تحلیل پلن‌های محبوب
    plans = db.get_vip_plans()
    plan_stats = {plan_id: 0 for plan_id in plans.keys()}
    
    # در واقعیت باید از تراکنش‌ها استخراج شود
    # اینجا فقط نمونه است
    
    text += f"\n\n📈 **پیش‌بینی:**
├─ تمدید انتظاری: {(duration_groups['کمتر از ۷ روز'] * 0.3 + duration_groups['۷-۳۰ روز'] * 0.5):.0f} کاربر
├─ درآمد ماه آینده: {total_vip * 500:,} سکه
└─ رشد VIP: {(total_vip/db.count_users()*100 if db.count_users() > 0 else 0):.1f}%"
    
    bot.send_message(user_id, text)

def show_games_report(user_id):
    """نمایش گزارش بازی‌ها"""
    users = db.get_all_users()
    
    total_games = 0
    total_wins = 0
    total_losses = 0
    total_spent = 0
    total_won = 0
    
    for user_data in users.values():
        total_games += user_data.get('games_played', 0)
        total_wins += user_data.get('games_won', 0)
        total_losses += user_data.get('games_lost', 0)
        total_spent += user_data.get('total_spent', 0)
        total_won += user_data.get('total_game_winnings', 0)
    
    win_rate = (total_wins/total_games*100 if total_games > 0 else 0)
    net_profit = total_won - total_spent
    
    text = f"""
🎰 **گزارش بازی‌ها**

📊 **کلیات:**
├─ کل بازی‌ها: {total_games}
├─ بردها: {total_wins}
├─ باخت‌ها: {total_losses}
└─ نرخ برد: {win_rate:.1f}%

💰 **مالی:**
├─ کل هزینه‌ها: {total_spent:,} سکه
├─ کل جوایز: {total_won:,} سکه
├─ سود/زیان: {net_profit:,} سکه
└─ درصد بازگشت: {(total_won/total_spent*100 if total_spent > 0 else 0):.1f}%

👥 **کاربران:**
├─ میانگین بازی هر کاربر: {total_games//len(users) if users else 0}
├─ کاربران فعال بازی: {sum(1 for u in users.values() if u.get('games_played', 0) > 0)}
└─ درصد بازیکنان: {(sum(1 for u in users.values() if u.get('games_played', 0) > 0)/len(users)*100 if users else 0):.1f}%

🎮 **بازی‌های محبوب:**
├─ تاس: {total_games//5} بازی
├─ دارت: {total_games//5} بازی
├─ بسکتبال: {total_games//5} بازی
├─ اسلات: {total_games//5} بازی
└─ رولت: {total_games//5} بازی
    """
    
    bot.send_message(user_id, text)

def show_growth_report(user_id):
    """نمایش گزارش رشد"""
    stats = db.get_stats()
    
    text = f"""
📈 **گزارش رشد**

🚀 **رشد کاربران:**
├─ کاربران امروز: {stats.get('new_users_today', 0)}
├─ کاربران این هفته: {stats.get('new_users_week', 0)}
├─ کاربران این ماه: {stats.get('new_users_month', 0)}
└─ نرخ رشد ماهانه: {(stats.get('new_users_month', 0)/db.count_users()*100 if db.count_users() > 0 else 0):.1f}%

💰 **رشد مالی:**
├─ درآمد روزانه: {stats.get('daily_income', 0):,}
├─ درآمد هفتگی: {stats.get('weekly_income', 0):,}
├─ درآمد ماهانه: {stats.get('monthly_income', 0):,}
└─ رشد درآمد ماهانه: {(stats.get('monthly_income', 0)/(stats.get('last_month_income', 1))*100 if stats.get('last_month_income', 0) > 0 else 0):.1f}%

🎖 **رشد VIP:**
├─ VIP های جدید امروز: {stats.get('new_vip_today', 0)}
├─ VIP های جدید این هفته: {stats.get('new_vip_week', 0)}
├─ VIP های جدید این ماه: {stats.get('new_vip_month', 0)}
└─ نرخ تبدیل به VIP: {(db.count_vip_users()/db.count_users()*100 if db.count_users() > 0 else 0):.1f}%

📊 **پیش‌بینی رشد:**
├─ کاربران ماه آینده: {db.count_users() * 1.1:.0f}
├─ درآمد ماه آینده: {stats.get('monthly_income', 0) * 1.05:,.0f}
├─ VIP های ماه آینده: {db.count_vip_users() * 1.15:.0f}
└─ سکه ماه آینده: {db.get_total_coins() * 1.2:,.0f}
    """
    
    bot.send_message(user_id, text)

def export_reports(user_id):
    """خروجی گزارش‌ها"""
    bot.send_message(user_id, "📤 **خروجی گزارش‌ها**\n\nاین قابلیت در حال توسعه است.")

# ==========================================
# سیستم زمان‌بندی
# ==========================================
def schedule_tasks():
    """زمان‌بندی وظایف"""
    def daily_tasks():
        """وظایف روزانه"""
        try:
            # بکاپ روزانه
            db.create_backup()
            
            # پاک‌سازی استیت‌های قدیمی
            state_manager.cleanup_old_states()
            
            # ریست آمار روزانه
            stats = db.get_stats()
            today = datetime.now().strftime('%Y-%m-%d')
            
            if stats.get('last_reset') != today:
                stats['daily_income'] = 0
                stats['last_reset'] = today
                db.save_stats(stats)
            
            # بررسی انقضای VIP
            check_and_notify_vip_expiry()
            
            print(f"✅ وظایف روزانه انجام شد: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"❌ خطا در وظایف روزانه: {e}")
    
    def weekly_tasks():
        """وظایف هفتگی"""
        try:
            # ریست آمار هفتگی
            stats = db.get_stats()
            stats['weekly_income'] = 0
            db.save_stats(stats)
            
            # پاک‌سازی لاگ‌های قدیمی
            cleanup_old_logs()
            
            print(f"✅ وظایف هفتگی انجام شد: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"❌ خطا در وظایف هفتگی: {e}")
    
    def monthly_tasks():
        """وظایف ماهانه"""
        try:
            # ریست آمار ماهانه
            stats = db.get_stats()
            stats['monthly_income'] = 0
            stats['last_month_income'] = stats.get('monthly_income', 0)
            db.save_stats(stats)
            
            # ایجاد بکاپ کامل
            db.create_backup()
            
            print(f"✅ وظایف ماهانه انجام شد: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"❌ خطا در وظایف ماهانه: {e}")
    
    # زمان‌بندی وظایف
    import schedule
    import time as t
    
    # روزانه در نیمه شب
    schedule.every().day.at("00:00").do(daily_tasks)
    
    # هفتگی روز شنبه
    schedule.every().saturday.at("00:00").do(weekly_tasks)
    
    # ماهانه روز اول
    schedule.every().month.at("00:00").do(monthly_tasks)
    
    # اجرای زمان‌بند در پس‌زمینه
    def run_scheduler():
        while True:
            schedule.run_pending()
            t.sleep(60)  # چک هر دقیقه
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

def check_and_notify_vip_expiry():
    """بررسی و اطلاع‌رسانی انقضای VIP"""
    users = db.get_all_users()
    now = time.time()
    
    for uid, user_data in users.items():
        vip_end = user_data.get('vip_end', 0)
        
        if vip_end > now:
            days_left = get_vip_days_left(vip_end)
            
            # هشدار برای انقضای نزدیک
            if days_left in [1, 3, 7]:
                try:
                    expiry_date = datetime.fromtimestamp(vip_end).strftime('%Y/%m/%d')
                    
                    message = f"""
⚠️ **هشدار انقضای VIP**

مدت VIP شما {days_left} روز دیگر به پایان می‌رسد!
📅 تاریخ انقضا: {expiry_date}

برای تمدید VIP به بخش 🎖 خرید VIP مراجعه کنید.
                    """
                    
                    bot.send_message(uid, message)
                    
                    # اطلاع به ادمین‌ها
                    notification.send_vip_expiry_warning(uid, days_left)
                except:
                    pass
    
    print(f"✅ بررسی انقضای VIP انجام شد: {len(users)} کاربر")

def cleanup_old_logs():
    """پاک‌سازی لاگ‌های قدیمی"""
    try:
        # اینجا می‌توانید لاگ‌های قدیمی را پاک کنید
        pass
    except:
        pass

# ==========================================
# اجرای ربات
# ==========================================
def main():
    """تابع اصلی اجرای ربات"""
    print("=" * 60)
    print("🤖 **ربات Shadow Titan v2.0**")
    print("=" * 60)
    print(f"🛡️ ادمین اصلی: {OWNER_ID}")
    print(f"🔑 رمز پیش‌فرض: admin123")
    print(f"📅 تاریخ راه‌اندازی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # راه‌اندازی سیستم‌ها
    try:
        # شروع زمان‌بندی
        schedule_tasks()
        print("✅ سیستم زمان‌بندی راه‌اندازی شد")
        
        # نمایش آمار اولیه
        total_users = db.count_users()
        vip_users = db.count_vip_users()
        total_coins = db.get_total_coins()
        
        print(f"📊 آمار اولیه:")
        print(f"👥 کاربران: {total_users}")
        print(f"⭐ VIP: {vip_users}")
        print(f"💰 سکه: {total_coins:,}")
        print("=" * 60)
        
        # راه‌اندازی ربات
        print("🚀 در حال راه‌اندازی ربات...")
        bot.remove_webhook()
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")
        print("🔄 تلاش مجدد در 10 ثانیه...")
        time.sleep(10)
        main()

if __name__ == "__main__":
    main()
