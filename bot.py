import telebot
from telebot import types
import json
import os
from datetime import datetime

# توکن ربات
TOKEN = 'YOUR_BOT_TOKEN_HERE'
bot = telebot.TeleBot(TOKEN)

# فایل داده‌ها
DATA_FILE = 'bot_data.json'

# بارگذاری داده‌ها
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'admins': [],  # لیست آی‌دی ادمین‌ها
        'users': {},   # اطلاعات کاربران
        'admin_passwords': {},  # رمزهای ادمین‌ها
        'vip_plans': {},  # پلن‌های VIP
        'settings': {
            'admin_password': 'admin123',  # رمز اصلی ادمین شدن
            'bot_name': 'ربات من'
        },
        'banned_users': [],  # کاربران مسدود شده
        'logs': []
    }

# ذخیره داده‌ها
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ثبت رویداد
def log_event(data, event, user_id=None):
    log = {
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'event': event,
        'user_id': user_id
    }
    data['logs'].append(log)
    if len(data['logs']) > 1000:  # محدود کردن تعداد لاگ‌ها
        data['logs'] = data['logs'][-1000:]
    save_data(data)

# --- ثبت نام کاربران عادی ---
@bot.message_handler(commands=['start', 'register'])
def register_user(message):
    data = load_data()
    user_id = str(message.from_user.id)
    
    if user_id in data['banned_users']:
        bot.send_message(message.chat.id, "❌ شما مسدود شده‌اید!")
        return
    
    if user_id in data['users']:
        bot.send_message(message.chat.id, "✅ شما قبلاً ثبت‌نام کرده‌اید!")
        return
    
    # درخواست نام
    msg = bot.send_message(message.chat.id, "👤 لطفاً نام خود را وارد کنید:")
    bot.register_next_step_handler(msg, process_name, user_id)

def process_name(message, user_id):
    name = message.text.strip()
    if len(name) < 2:
        msg = bot.send_message(message.chat.id, "❌ نام باید حداقل ۲ حرف باشد. دوباره وارد کنید:")
        bot.register_next_step_handler(msg, process_name, user_id)
        return
    
    # درخواست سن
    msg = bot.send_message(message.chat.id, "🎂 لطفاً سن خود را وارد کنید:")
    bot.register_next_step_handler(msg, process_age, user_id, name)

def process_age(message, user_id, name):
    try:
        age = int(message.text.strip())
        if age < 1 or age > 150:
            raise ValueError
    except:
        msg = bot.send_message(message.chat.id, "❌ سن باید عدد بین ۱ تا ۱۵۰ باشد. دوباره وارد کنید:")
        bot.register_next_step_handler(msg, process_age, user_id, name)
        return
    
    # درخواست جنسیت
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('👨 مرد', '👩 زن', '🤖 ترجیح نمی‌دهم')
    
    msg = bot.send_message(message.chat.id, "⚧️ جنسیت خود را انتخاب کنید:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_gender, user_id, name, age)

def process_gender(message, user_id, name, age):
    gender = message.text.strip()
    
    data = load_data()
    data['users'][user_id] = {
        'name': name,
        'age': age,
        'gender': gender,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'register_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'coins': 0,
        'vip_level': 0,
        'last_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    log_event(data, f"کاربر جدید ثبت‌نام کرد: {name}", user_id)
    
    bot.send_message(
        message.chat.id,
        f"✅ ثبت‌نام با موفقیت انجام شد!\n\n"
        f"👤 نام: {name}\n"
        f"🎂 سن: {age}\n"
        f"⚧️ جنسیت: {gender}\n\n"
        f"🆔 آی‌دی شما: {user_id}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    save_data(data)

# --- ثبت نام ادمین ---
@bot.message_handler(commands=['register_admin'])
def start_admin_registration(message):
    data = load_data()
    user_id = str(message.from_user.id)
    
    # اگر قبلاً ادمین است
    if user_id in data['admins']:
        bot.send_message(message.chat.id, "✅ شما قبلاً ادمین هستید!")
        return
    
    msg = bot.send_message(message.chat.id, "🔐 لطفاً رمز اصلی ادمین شدن را وارد کنید:")
    bot.register_next_step_handler(msg, verify_admin_password, user_id)

def verify_admin_password(message, user_id):
    password = message.text.strip()
    data = load_data()
    
    if password != data['settings']['admin_password']:
        bot.send_message(message.chat.id, "❌ رمز اشتباه است!")
        return
    
    msg = bot.send_message(message.chat.id, "🔑 حالا یک رمز شخصی برای خودتان انتخاب کنید (حداقل ۴ رقم):")
    bot.register_next_step_handler(msg, set_admin_password, user_id)

def set_admin_password(message, user_id):
    password = message.text.strip()
    
    if len(password) < 4:
        msg = bot.send_message(message.chat.id, "❌ رمز باید حداقل ۴ حرف باشد. دوباره وارد کنید:")
        bot.register_next_step_handler(msg, set_admin_password, user_id)
        return
    
    data = load_data()
    data['admins'].append(user_id)
    data['admin_passwords'][user_id] = password
    
    # اگر کاربر ثبت‌نام نکرده بود، ثبتش کن
    if user_id not in data['users']:
        data['users'][user_id] = {
            'name': 'ادمین',
            'age': 0,
            'gender': '🤖 ربات',
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'register_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'coins': 1000,
            'vip_level': 10,
            'last_seen': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    log_event(data, f"ادمین جدید اضافه شد: {user_id}", user_id)
    save_data(data)
    
    bot.send_message(
        message.chat.id,
        f"🎉 شما ادمین شدید!\n\n"
        f"🔑 رمز شخصی شما: {password}\n"
        f"⚠️ این رمز را فراموش نکنید!\n\n"
        f"برای ورود به پنل مدیریت از دستور /admin استفاده کنید."
    )

# --- ورود به پنل مدیریت ---
@bot.message_handler(commands=['admin'])
def admin_login(message):
    data = load_data()
    user_id = str(message.from_user.id)
    
    if user_id not in data['admins']:
        bot.send_message(message.chat.id, "❌ شما ادمین نیستید!")
        return
    
    msg = bot.send_message(message.chat.id, "🔐 رمز شخصی خود را وارد کنید:")
    bot.register_next_step_handler(msg, verify_admin_login, user_id)

def verify_admin_login(message, user_id):
    password = message.text.strip()
    data = load_data()
    
    if data['admin_passwords'].get(user_id) != password:
        bot.send_message(message.chat.id, "❌ رمز اشتباه است!")
        return
    
    show_admin_panel(message.chat.id, user_id)

# --- پنل مدیریت ---
def show_admin_panel(chat_id, admin_id):
    data = load_data()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # بخش مدیریت کاربران
    btn_users = types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data='manage_users')
    btn_ban = types.InlineKeyboardButton("🚫 مسدود کردن کاربر", callback_data='ban_user')
    btn_unban = types.InlineKeyboardButton("✅ آزاد کردن کاربر", callback_data='unban_user')
    
    # بخش سکه و VIP
    btn_add_coins = types.InlineKeyboardButton("🪙 افزودن سکه", callback_data='add_coins')
    btn_remove_coins = types.InlineKeyboardButton("➖ کم کردن سکه", callback_data='remove_coins')
    btn_set_vip = types.InlineKeyboardButton("⭐ تنظیم VIP", callback_data='set_vip')
    
    # بخش VIP پلن‌ها
    btn_add_vip_plan = types.InlineKeyboardButton("➕ افزودن پلن VIP", callback_data='add_vip_plan')
    btn_edit_vip_plan = types.InlineKeyboardButton("✏️ ویرایش پلن VIP", callback_data='edit_vip_plan')
    btn_delete_vip_plan = types.InlineKeyboardButton("🗑️ حذف پلن VIP", callback_data='delete_vip_plan')
    
    # بخش تنظیمات
    btn_settings = types.InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')
    btn_stats = types.InlineKeyboardButton("📊 آمار", callback_data='stats')
    btn_broadcast = types.InlineKeyboardButton("📢 ارسال به همه", callback_data='broadcast')
    btn_logs = types.InlineKeyboardButton("📋 لاگ‌ها", callback_data='view_logs')
    
    # چیدمان دکمه‌ها
    markup.add(btn_users, btn_ban, btn_unban)
    markup.add(btn_add_coins, btn_remove_coins, btn_set_vip)
    markup.add(btn_add_vip_plan, btn_edit_vip_plan, btn_delete_vip_plan)
    markup.add(btn_settings, btn_stats, btn_broadcast, btn_logs)
    
    # اطلاعات ادمین
    admin_info = data['users'].get(admin_id, {})
    admin_name = admin_info.get('name', 'ادمین')
    
    bot.send_message(
        chat_id,
        f"👑 **پنل مدیریت**\n\n"
        f"👤 ادمین: {admin_name}\n"
        f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"⏰ زمان: {datetime.now().strftime('%H:%M')}\n\n"
        f"📊 آمار سریع:\n"
        f"• کاربران: {len(data['users'])}\n"
        f"• ادمین‌ها: {len(data['admins'])}\n"
        f"• مسدود شده‌ها: {len(data['banned_users'])}\n"
        f"• پلن‌های VIP: {len(data.get('vip_plans', {}))}\n\n"
        f"لطفاً یک گزینه انتخاب کنید:",
        parse_mode='Markdown',
        reply_markup=markup
    )

# --- مدیریت callback‌ها ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = load_data()
    user_id = str(call.from_user.id)
    
    # بررسی ادمین بودن
    if user_id not in data['admins']:
        bot.answer_callback_query(call.id, "❌ شما ادمین نیستید!", show_alert=True)
        return
    
    # مدیریت کاربران
    if call.data == 'manage_users':
        manage_users(call)
    elif call.data == 'ban_user':
        ban_user_prompt(call)
    elif call.data == 'unban_user':
        unban_user_prompt(call)
    
    # مدیریت سکه و VIP
    elif call.data == 'add_coins':
        add_coins_prompt(call)
    elif call.data == 'remove_coins':
        remove_coins_prompt(call)
    elif call.data == 'set_vip':
        set_vip_prompt(call)
    
    # مدیریت VIP پلن‌ها
    elif call.data == 'add_vip_plan':
        add_vip_plan_prompt(call)
    elif call.data == 'edit_vip_plan':
        edit_vip_plan_prompt(call)
    elif call.data == 'delete_vip_plan':
        delete_vip_plan_prompt(call)
    
    # تنظیمات و آمار
    elif call.data == 'settings':
        show_settings(call)
    elif call.data == 'stats':
        show_stats(call)
    elif call.data == 'broadcast':
        broadcast_prompt(call)
    elif call.data == 'view_logs':
        show_logs(call)
    
    # تنظیمات خاص
    elif call.data.startswith('setting_'):
        handle_settings(call)
    
    # برگشت به منوی اصلی
    elif call.data == 'back_to_admin':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_admin_panel(call.message.chat.id, user_id)

# --- مدیریت کاربران ---
def manage_users(call):
    data = load_data()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # فقط ۱۰ کاربر اول را نشان بده
    user_list = list(data['users'].items())[:10]
    
    for uid, user in user_list:
        name = user.get('name', 'بی‌نام')
        coins = user.get('coins', 0)
        vip = "⭐" if user.get('vip_level', 0) > 0 else ""
        
        btn_text = f"{name} ({coins}🪙){vip}"
        btn = types.InlineKeyboardButton(btn_text, callback_data=f'user_detail_{uid}')
        markup.add(btn)
    
    btn_back = types.InlineKeyboardButton("🔙 برگشت", callback_data='back_to_admin')
    markup.add(btn_back)
    
    bot.edit_message_text(
        "👥 **لیست کاربران**\n\n"
        "برای مشاهده جزئیات روی کاربر کلیک کنید:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup
    )

def ban_user_prompt(call):
    msg = bot.send_message(
        call.message.chat.id,
        "🚫 **مسدود کردن کاربر**\n\n"
        "لطفاً آی‌دی عددی کاربر را وارد کنید:"
    )
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message):
    try:
        user_id = message.text.strip()
        data = load_data()
        
        if user_id in data['banned_users']:
            bot.send_message(message.chat.id, "⚠️ این کاربر قبلاً مسدود شده است!")
            return
        
        if user_id not in data['users']:
            bot.send_message(message.chat.id, "❌ کاربر یافت نشد!")
            return
        
        data['banned_users'].append(user_id)
        log_event(data, f"کاربر {user_id} مسدود شد", str(message.from_user.id))
        save_data(data)
        
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} مسدود شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

def unban_user_prompt(call):
    msg = bot.send_message(
        call.message.chat.id,
        "✅ **آزاد کردن کاربر**\n\n"
        "لطفاً آی‌دی عددی کاربر را وارد کنید:"
    )
    bot.register_next_step_handler(msg, process_unban_user)

def process_unban_user(message):
    try:
        user_id = message.text.strip()
        data = load_data()
        
        if user_id not in data['banned_users']:
            bot.send_message(message.chat.id, "⚠️ این کاربر مسدود نیست!")
            return
        
        data['banned_users'].remove(user_id)
        log_event(data, f"کاربر {user_id} آزاد شد", str(message.from_user.id))
        save_data(data)
        
        bot.send_message(message.chat.id, f"✅ کاربر {user_id} آزاد شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

# --- مدیریت سکه‌ها ---
def add_coins_prompt(call):
    msg = bot.send_message(
        call.message.chat.id,
        "🪙 **افزودن سکه**\n\n"
        "لطفاً آی‌دی کاربر و تعداد سکه را به فرمت زیر وارد کنید:\n"
        "`آی‌دی|تعداد سکه`\n\n"
        "مثال:\n"
        "`123456789|100`"
    )
    bot.register_next_step_handler(msg, process_add_coins)

def process_add_coins(message):
    try:
        parts = message.text.split('|')
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ فرمت اشتباه است!")
            return
        
        user_id = parts[0].strip()
        coins = int(parts[1].strip())
        
        data = load_data()
        
        if user_id not in data['users']:
            bot.send_message(message.chat.id, "❌ کاربر یافت نشد!")
            return
        
        data['users'][user_id]['coins'] = data['users'][user_id].get('coins', 0) + coins
        log_event(data, f"به کاربر {user_id}، {coins} سکه اضافه شد", str(message.from_user.id))
        save_data(data)
        
        bot.send_message(message.chat.id, f"✅ {coins} سکه به کاربر {user_id} اضافه شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

def remove_coins_prompt(call):
    msg = bot.send_message(
        call.message.chat.id,
        "➖ **کم کردن سکه**\n\n"
        "لطفاً آی‌دی کاربر و تعداد سکه را به فرمت زیر وارد کنید:\n"
        "`آی‌دی|تعداد سکه`\n\n"
        "مثال:\n"
        "`123456789|50`"
    )
    bot.register_next_step_handler(msg, process_remove_coins)

def process_remove_coins(message):
    try:
        parts = message.text.split('|')
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ فرمت اشتباه است!")
            return
        
        user_id = parts[0].strip()
        coins = int(parts[1].strip())
        
        data = load_data()
        
        if user_id not in data['users']:
            bot.send_message(message.chat.id, "❌ کاربر یافت نشد!")
            return
        
        current_coins = data['users'][user_id].get('coins', 0)
        if current_coins < coins:
            bot.send_message(message.chat.id, f"❌ کاربر فقط {current_coins} سکه دارد!")
            return
        
        data['users'][user_id]['coins'] = current_coins - coins
        log_event(data, f"از کاربر {user_id}، {coins} سکه کم شد", str(message.from_user.id))
        save_data(data)
        
        bot.send_message(message.chat.id, f"✅ {coins} سکه از کاربر {user_id} کم شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

# --- تنظیم VIP ---
def set_vip_prompt(call):
    msg = bot.send_message(
        call.message.chat.id,
        "⭐ **تنظیم سطح VIP**\n\n"
        "لطفاً آی‌دی کاربر و سطح VIP را به فرمت زیر وارد کنید:\n"
        "`آی‌دی|سطح VIP`\n\n"
        "مثال:\n"
        "`123456789|3`\n\n"
        "سطح ۰ = غیر VIP\n"
        "سطح ۱ = نقره‌ای\n"
        "سطح ۲ = طلایی\n"
        "سطح ۳ = پلاتینیوم"
    )
    bot.register_next_step_handler(msg, process_set_vip)

def process_set_vip(message):
    try:
        parts = message.text.split('|')
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ فرمت اشتباه است!")
            return
        
        user_id = parts[0].strip()
        vip_level = int(parts[1].strip())
        
        data = load_data()
        
        if user_id not in data['users']:
            bot.send_message(message.chat.id, "❌ کاربر یافت نشد!")
            return
        
        data['users'][user_id]['vip_level'] = vip_level
        log_event(data, f"سطح VIP کاربر {user_id} به {vip_level} تغییر کرد", str(message.from_user.id))
        save_data(data)
        
        levels = {0: "غیر VIP", 1: "نقره‌ای", 2: "طلایی", 3: "پلاتینیوم"}
        vip_name = levels.get(vip_level, "نامشخص")
        
        bot.send_message(message.chat.id, f"✅ سطح VIP کاربر {user_id} به {vip_name} تغییر کرد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

# --- مدیریت VIP پلن‌ها ---
def add_vip_plan_prompt(call):
    msg = bot.send_message(
        call.message.chat.id,
        "➕ **افزودن پلن VIP جدید**\n\n"
        "لطفاً اطلاعات پلن را به فرمت زیر وارد کنید:\n"
        "`نام|قیمت|سکه|سطح VIP`\n\n"
        "مثال:\n"
        "`پلن نقره‌ای|50000|100|1`"
    )
    bot.register_next_step_handler(msg, process_add_vip_plan)

def process_add_vip_plan(message):
    try:
        parts = message.text.split('|')
        if len(parts) != 4:
            bot.send_message(message.chat.id, "❌ فرمت اشتباه است!")
            return
        
        name = parts[0].strip()
        price = int(parts[1].strip())
        coins = int(parts[2].strip())
        vip_level = int(parts[3].strip())
        
        data = load_data()
        
        if 'vip_plans' not in data:
            data['vip_plans'] = {}
        
        plan_id = len(data['vip_plans']) + 1
        
        data['vip_plans'][str(plan_id)] = {
            'name': name,
            'price': price,
            'coins': coins,
            'vip_level': vip_level,
            'active': True,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        log_event(data, f"پلن VIP جدید: {name} اضافه شد", str(message.from_user.id))
        save_data(data)
        
        bot.send_message(
            message.chat.id,
            f"✅ پلن VIP جدید اضافه شد!\n\n"
            f"🆔 کد پلن: {plan_id}\n"
            f"📛 نام: {name}\n"
            f"💰 قیمت: {price:,} تومان\n"
            f"🪙 سکه: {coins}\n"
            f"⭐ سطح VIP: {vip_level}"
        )
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

def edit_vip_plan_prompt(call):
    data = load_data()
    
    if not data.get('vip_plans'):
        bot.send_message(call.message.chat.id, "⚠️ هیچ پلن VIP‌ای وجود ندارد!")
        return
    
    plans_text = "📋 **پلن‌های VIP موجود:**\n\n"
    for plan_id, plan in data['vip_plans'].items():
        plans_text += f"{plan_id}. {plan['name']} - {plan['price']:,} تومان\n"
    
    msg = bot.send_message(
        call.message.chat.id,
        f"{plans_text}\n"
        "لطفاً کد پلن و اطلاعات جدید را به فرمت زیر وارد کنید:\n"
        "`کد پلن|نام جدید|قیمت جدید|سکه جدید|سطح VIP جدید`\n\n"
        "مثال:\n"
        "`1|پلن نقره‌ای ویژه|60000|150|1`"
    )
    bot.register_next_step_handler(msg, process_edit_vip_plan)

def process_edit_vip_plan(message):
    try:
        parts = message.text.split('|')
        if len(parts) != 5:
            bot.send_message(message.chat.id, "❌ فرمت اشتباه است!")
            return
        
        plan_id = parts[0].strip()
        name = parts[1].strip()
        price = int(parts[2].strip())
        coins = int(parts[3].strip())
        vip_level = int(parts[4].strip())
        
        data = load_data()
        
        if plan_id not in data.get('vip_plans', {}):
            bot.send_message(message.chat.id, "❌ پلن یافت نشد!")
            return
        
        old_name = data['vip_plans'][plan_id]['name']
        data['vip_plans'][plan_id].update({
            'name': name,
            'price': price,
            'coins': coins,
            'vip_level': vip_level
        })
        
        log_event(data, f"پلن VIP {old_name} ویرایش شد", str(message.from_user.id))
        save_data(data)
        
        bot.send_message(
            message.chat.id,
            f"✅ پلن VIP ویرایش شد!\n\n"
            f"📛 نام جدید: {name}\n"
            f"💰 قیمت جدید: {price:,} تومان\n"
            f"🪙 سکه جدید: {coins}\n"
            f"⭐ سطح VIP جدید: {vip_level}"
        )
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

def delete_vip_plan_prompt(call):
    data = load_data()
    
    if not data.get('vip_plans'):
        bot.send_message(call.message.chat.id, "⚠️ هیچ پلن VIP‌ای وجود ندارد!")
        return
    
    plans_text = "📋 **پلن‌های VIP موجود:**\n\n"
    for plan_id, plan in data['vip_plans'].items():
        plans_text += f"{plan_id}. {plan['name']}\n"
    
    msg = bot.send_message(
        call.message.chat.id,
        f"{plans_text}\n"
        "لطفاً کد پلنی که می‌خواهید حذف کنید را وارد کنید:"
    )
    bot.register_next_step_handler(msg, process_delete_vip_plan)

def process_delete_vip_plan(message):
    try:
        plan_id = message.text.strip()
        data = load_data()
        
        if plan_id not in data.get('vip_plans', {}):
            bot.send_message(message.chat.id, "❌ پلن یافت نشد!")
            return
        
        plan_name = data['vip_plans'][plan_id]['name']
        del data['vip_plans'][plan_id]
        
        log_event(data, f"پلن VIP {plan_name} حذف شد", str(message.from_user.id))
        save_data(data)
        
        bot.send_message(message.chat.id, f"✅ پلن VIP {plan_name} حذف شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

# --- تنظیمات ---
def show_settings(call):
    data = load_data()
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_change_pass = types.InlineKeyboardButton("🔐 تغییر رمز اصلی", callback_data='setting_change_pass')
    btn_change_name = types.InlineKeyboardButton("📛 تغییر نام ربات", callback_data='setting_change_name')
    btn_add_admin = types.InlineKeyboardButton("➕ افزودن ادمین", callback_data='setting_add_admin')
    btn_remove_admin = types.InlineKeyboardButton("➖ حذف ادمین", callback_data='setting_remove_admin')
    btn_reset_data = types.InlineKeyboardButton("🔄 بازنشانی داده‌ها", callback_data='setting_reset_data')
    btn_back = types.InlineKeyboardButton("🔙 برگشت", callback_data='back_to_admin')
    
    markup.add(btn_change_pass, btn_change_name, btn_add_admin, btn_remove_admin, btn_reset_data)
    markup.add(btn_back)
    
    bot.edit_message_text(
        "⚙️ **تنظیمات ربات**\n\n"
        f"🔐 رمز اصلی: {data['settings']['admin_password']}\n"
        f"📛 نام ربات: {data['settings']['bot_name']}\n"
        f"👑 تعداد ادمین‌ها: {len(data['admins'])}\n\n"
        "لطفاً گزینه مورد نظر را انتخاب کنید:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup
    )

def handle_settings(call):
    data = load_data()
    
    if call.data == 'setting_change_pass':
        msg = bot.send_message(call.message.chat.id, "لطفاً رمز جدید را وارد کنید:")
        bot.register_next_step_handler(msg, process_change_password)
    
    elif call.data == 'setting_change_name':
        msg = bot.send_message(call.message.chat.id, "لطفاً نام جدید ربات را وارد کنید:")
        bot.register_next_step_handler(msg, process_change_bot_name)
    
    elif call.data == 'setting_add_admin':
        msg = bot.send_message(call.message.chat.id, "لطفاً آی‌دی عددی کاربر جدید را وارد کنید:")
        bot.register_next_step_handler(msg, process_add_admin)
    
    elif call.data == 'setting_remove_admin':
        msg = bot.send_message(
            call.message.chat.id,
            f"👑 **ادمین‌های فعلی:**\n" + 
            "\n".join([f"{uid}" for uid in data['admins']]) + 
            "\n\nلطفاً آی‌دی ادمینی که می‌خواهید حذف کنید را وارد کنید:"
        )
        bot.register_next_step_handler(msg, process_remove_admin)
    
    elif call.data == 'setting_reset_data':
        markup = types.InlineKeyboardMarkup()
        btn_yes = types.InlineKeyboardButton("✅ بله، پاک کن", callback_data='reset_confirm')
        btn_no = types.InlineKeyboardButton("❌ خیر، برگرد", callback_data='back_to_admin')
        markup.add(btn_yes, btn_no)
        
        bot.send_message(
            call.message.chat.id,
            "⚠️ **هشدار!**\n\n"
            "آیا مطمئن هستید که می‌خواهید تمام داده‌ها را پاک کنید؟\n"
            "این عمل غیرقابل بازگشت است!",
            reply_markup=markup
        )
    
    elif call.data == 'reset_confirm':
        # ایجاد داده‌های جدید
        new_data = {
            'admins': data['admins'],  # ادمین‌ها را نگه دار
            'users': {},
            'admin_passwords': data['admin_passwords'],  # رمزها را نگه دار
            'vip_plans': {},
            'settings': data['settings'],
            'banned_users': [],
            'logs': []
        }
        
        save_data(new_data)
        bot.send_message(call.message.chat.id, "✅ تمام داده‌ها پاک شدند!")

def process_change_password(message):
    new_password = message.text.strip()
    data = load_data()
    data['settings']['admin_password'] = new_password
    save_data(data)
    bot.send_message(message.chat.id, "✅ رمز اصلی تغییر کرد!")

def process_change_bot_name(message):
    new_name = message.text.strip()
    data = load_data()
    data['settings']['bot_name'] = new_name
    save_data(data)
    bot.send_message(message.chat.id, f"✅ نام ربات به {new_name} تغییر کرد!")

def process_add_admin(message):
    try:
        new_admin_id = message.text.strip()
        data = load_data()
        
        if new_admin_id in data['admins']:
            bot.send_message(message.chat.id, "⚠️ این کاربر قبلاً ادمین است!")
            return
        
        data['admins'].append(new_admin_id)
        save_data(data)
        
        bot.send_message(
            message.chat.id,
            f"✅ کاربر {new_admin_id} به لیست ادمین‌ها اضافه شد!\n\n"
            f"کاربر باید دستور /register_admin را اجرا کند و رمز اصلی را وارد کند."
        )
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

def process_remove_admin(message):
    try:
        admin_id = message.text.strip()
        data = load_data()
        
        if admin_id not in data['admins']:
            bot.send_message(message.chat.id, "⚠️ این کاربر ادمین نیست!")
            return
        
        data['admins'].remove(admin_id)
        if admin_id in data['admin_passwords']:
            del data['admin_passwords'][admin_id]
        
        save_data(data)
        bot.send_message(message.chat.id, f"✅ کاربر {admin_id} از لیست ادمین‌ها حذف شد!")
    except:
        bot.send_message(message.chat.id, "❌ خطا در پردازش!")

# --- آمار ---
def show_stats(call):
    data = load_data()
    
    total_users = len(data['users'])
    active_admins = len(data['admins'])
    banned_users = len(data['banned_users'])
    vip_users = sum(1 for user in data['users'].values() if user.get('vip_level', 0) > 0)
    total_coins = sum(user.get('coins', 0) for user in data['users'].values())
    vip_plans_count = len(data.get('vip_plans', {}))
    
    # جدیدترین کاربران
    recent_users = []
    for uid, user in list(data['users'].items())[-5:]:
        recent_users.append(f"{user.get('name', 'بی‌نام')} ({uid[:5]}...)")
    
    stats_text = (
        "📊 **آمار کامل ربات**\n\n"
        f"👥 کل کاربران: {total_users}\n"
        f"👑 ادمین‌های فعال: {active_admins}\n"
        f"🚫 کاربران مسدود: {banned_users}\n"
        f"⭐ کاربران VIP: {vip_users}\n"
        f"🪙 مجموع سکه‌ها: {total_coins}\n"
        f"📋 پلن‌های VIP: {vip_plans_count}\n\n"
        f"📅 جدیدترین کاربران:\n" + 
        "\n".join([f"• {user}" for user in recent_users]) + "\n\n"
        f"⏰ آخرین بروزرسانی: {datetime.now().strftime('%H:%M:%S')}"
    )
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🔙 برگشت", callback_data='back_to_admin')
    markup.add(btn_back)
    
    bot.edit_message_text(
        stats_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup
    )

# --- ارسال همگانی ---
def broadcast_prompt(call):
    msg = bot.send_message(
        call.message.chat.id,
        "📢 **ارسال پیام به همه کاربران**\n\n"
        "لطفاً پیام خود را وارد کنید:\n"
        "می‌توانید از اموجی و فرمت‌بندی استفاده کنید."
    )
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    data = load_data()
    text = message.text
    
    sent = 0
    failed = 0
    
    for user_id in data['users']:
        if user_id in data['banned_users']:
            continue
            
        try:
            bot.send_message(user_id, text)
            sent += 1
        except:
            failed += 1
    
    bot.send_message(
        message.chat.id,
        f"✅ ارسال پیام انجام شد!\n\n"
        f"📤 ارسال موفق: {sent}\n"
        f"📭 ارسال ناموفق: {failed}\n"
        f"📊 مجموع: {sent + failed}"
    )

# --- نمایش لاگ‌ها ---
def show_logs(call):
    data = load_data()
    
    if not data['logs']:
        bot.send_message(call.message.chat.id, "📭 هیچ لاگی ثبت نشده است!")
        return
    
    # فقط ۲۰ لاگ آخر
    recent_logs = data['logs'][-20:]
    logs_text = "📋 **۲۰ لاگ آخر:**\n\n"
    
    for log in reversed(recent_logs):
        logs_text += f"⏰ {log['time']}\n"
        logs_text += f"📝 {log['event']}\n"
        if log['user_id']:
            logs_text += f"👤 کاربر: {log['user_id']}\n"
        logs_text += "─" * 30 + "\n"
    
    markup = types.InlineKeyboardMarkup()
    btn_back = types.InlineKeyboardButton("🔙 برگشت", callback_data='back_to_admin')
    markup.add(btn_back)
    
    bot.edit_message_text(
        logs_text[:4000],  # محدودیت تلگرام
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup
    )

# --- دستورات کاربران ---
@bot.message_handler(commands=['profile', 'me'])
def show_profile(message):
    data = load_data()
    user_id = str(message.from_user.id)
    
    if user_id in data['banned_users']:
        bot.send_message(message.chat.id, "❌ شما مسدود شده‌اید!")
        return
    
    if user_id not in data['users']:
        bot.send_message(message.chat.id, "❌ شما ثبت‌نام نکرده‌اید! /register")
        return
    
    user = data['users'][user_id]
    
    vip_names = {0: "❌ غیر فعال", 1: "🥈 نقره‌ای", 2: "🥇 طلایی", 3: "💎 پلاتینیوم"}
    vip_level = user.get('vip_level', 0)
    vip_name = vip_names.get(vip_level, "نامشخص")
    
    profile_text = (
        f"👤 **پروفایل شما**\n\n"
        f"📛 نام: {user.get('name', 'ندارد')}\n"
        f"🎂 سن: {user.get('age', 'ندارد')}\n"
        f"⚧️ جنسیت: {user.get('gender', 'ندارد')}\n"
        f"🆔 آی‌دی: {user_id}\n"
        f"📅 تاریخ ثبت‌نام: {user.get('register_date', 'ندارد')}\n\n"
        f"💰 **موجودی:**\n"
        f"🪙 سکه: {user.get('coins', 0)}\n"
        f"⭐ سطح VIP: {vip_name}\n\n"
        f"🕒 آخرین فعالیت: {user.get('last_seen', 'ندارد')}"
    )
    
    # اگر ادمین است
    if user_id in data['admins']:
        profile_text += "\n\n👑 **شما ادمین هستید!**"
        markup = types.InlineKeyboardMarkup()
        btn_admin = types.InlineKeyboardButton("👑 پنل مدیریت", callback_data='go_to_admin_panel')
        markup.add(btn_admin)
        
        bot.send_message(
            message.chat.id,
            profile_text,
            parse_mode='Markdown',
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'go_to_admin_panel')
def go_to_admin_panel(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_admin_panel(call.message.chat.id, str(call.from_user.id))

# --- دستور VIP Shop ---
@bot.message_handler(commands=['vip', 'shop'])
def show_vip_shop(message):
    data = load_data()
    user_id = str(message.from_user.id)
    
    if user_id not in data['users']:
        bot.send_message(message.chat.id, "❌ ابتدا ثبت‌نام کنید! /register")
        return
    
    if not data.get('vip_plans'):
        bot.send_message(message.chat.id, "⚠️ در حال حاضر پلن VIP‌ای موجود نیست!")
        return
    
    shop_text = "🛒 **فروشگاه VIP**\n\n"
    
    for plan_id, plan in data['vip_plans'].items():
        if plan.get('active', True):
            shop_text += (
                f"🆔 کد: {plan_id}\n"
                f"📛 نام: {plan['name']}\n"
                f"💰 قیمت: {plan['price']:,} تومان\n"
                f"🪙 سکه: {plan['coins']}\n"
                f"⭐ سطح VIP: {plan['vip_level']}\n"
                f"─" * 30 + "\n"
            )
    
    shop_text += "\n📝 برای خرید با پشتیبانی تماس بگیرید."
    
    bot.send_message(message.chat.id, shop_text, parse_mode='Markdown')

# --- به‌روزرسانی آخرین فعالیت ---
@bot.message_handler(func=lambda message: True)
def update_last_seen(message):
    data = load_data()
    user_id = str(message.from_user.id)
    
    if user_id in data['users']:
        data['users'][user_id]['last_seen'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_data(data)

# --- شروع ربات ---
print("🤖 ربات با موفقیت راه‌اندازی شد!")
bot.infinity_polling()
