import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# States for conversations
ADMIN_MENU, EVENT_NAME, EVENT_DATE, EVENT_DESC, EVENT_CONFIRM = range(5)
VIP_TIER_NAME, VIP_TIER_BENEFIT, VIP_TIER_PRICE, VIP_TIER_CONFIRM = range(4)
DISCOUNT_CODE, DISCOUNT_PERCENT, DISCOUNT_EXPIRY, DISCOUNT_CONFIRM = range(4)

# Persian labels
LABELS = {
    'admin_panel': '🔐 پنل مدیریت',
    'events': '📅 مدیریت رویدادها',
    'vip_tiers': '👑 مدیریت سطح VIP',
    'discounts': '🎁 مدیریت تخفیفات',
    'back': '🔙 بازگشت',
    'add': '➕ افزودن',
    'view': '👁️ مشاهده',
    'edit': '✏️ ویرایش',
    'delete': '🗑️ حذف',
    'cancel': '❌ لغو',
    'confirm': '✅ تایید',
    'error': '❌ خطا',
    'success': '✅ موفق',
    'event_name': 'نام رویداد:',
    'event_date': 'تاریخ رویداد:',
    'event_description': 'توضیحات رویداد:',
    'event_added': 'رویداد با موفقیت افزوده شد!',
    'event_list': '📋 لیست رویدادها',
    'no_events': 'هیچ رویدادی وجود ندارد.',
    'vip_tier_name': 'نام سطح VIP:',
    'vip_tier_benefit': 'مزایای سطح VIP:',
    'vip_tier_price': 'قیمت سطح VIP:',
    'vip_added': 'سطح VIP با موفقیت افزوده شد!',
    'vip_list': '👑 لیست سطح های VIP',
    'no_vip': 'هیچ سطح VIP وجود ندارد.',
    'discount_code': 'کد تخفیف:',
    'discount_percent': 'درصد تخفیف:',
    'discount_expiry': 'تاریخ انقضا (YYYY-MM-DD):',
    'discount_added': 'کد تخفیف با موفقیت افزوده شد!',
    'discount_list': '🎁 لیست تخفیفات',
    'no_discounts': 'هیچ تخفیفی وجود ندارد.',
    'unauthorized': '❌ شما اجازه دسترسی به این بخش را ندارید.',
    'welcome': 'سلام! به ربات خوش آمدید.',
    'admin_only': '⚠️ این دستور فقط برای مدیران است.',
}

# Data storage
class DataManager:
    def __init__(self, data_file='bot_data.json'):
        self.data_file = data_file
        self.load_data()
    
    def load_data(self):
        """Load data from JSON file"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                'events': [],
                'vip_tiers': [],
                'discounts': [],
                'users': []
            }
        
        # Ensure all keys exist
        for key in ['events', 'vip_tiers', 'discounts', 'users']:
            if key not in self.data:
                self.data[key] = []
    
    def save_data(self):
        """Save data to JSON file"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
    
    def add_event(self, name: str, date: str, description: str):
        """Add a new event"""
        event = {
            'id': len(self.data['events']) + 1,
            'name': name,
            'date': date,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
        self.data['events'].append(event)
        self.save_data()
        return event
    
    def add_vip_tier(self, name: str, benefits: str, price: float):
        """Add a new VIP tier"""
        tier = {
            'id': len(self.data['vip_tiers']) + 1,
            'name': name,
            'benefits': benefits,
            'price': price,
            'created_at': datetime.now().isoformat()
        }
        self.data['vip_tiers'].append(tier)
        self.save_data()
        return tier
    
    def add_discount(self, code: str, percentage: float, expiry: str):
        """Add a new discount code"""
        discount = {
            'id': len(self.data['discounts']) + 1,
            'code': code.upper(),
            'percentage': percentage,
            'expiry': expiry,
            'created_at': datetime.now().isoformat(),
            'active': True
        }
        self.data['discounts'].append(discount)
        self.save_data()
        return discount
    
    def delete_event(self, event_id: int):
        """Delete an event by ID"""
        self.data['events'] = [e for e in self.data['events'] if e['id'] != event_id]
        self.save_data()
    
    def delete_vip_tier(self, tier_id: int):
        """Delete a VIP tier by ID"""
        self.data['vip_tiers'] = [t for t in self.data['vip_tiers'] if t['id'] != tier_id]
        self.save_data()
    
    def delete_discount(self, discount_id: int):
        """Delete a discount code by ID"""
        self.data['discounts'] = [d for d in self.data['discounts'] if d['id'] != discount_id]
        self.save_data()
    
    def get_events(self) -> List[Dict]:
        """Get all events"""
        return self.data.get('events', [])
    
    def get_vip_tiers(self) -> List[Dict]:
        """Get all VIP tiers"""
        return self.data.get('vip_tiers', [])
    
    def get_discounts(self) -> List[Dict]:
        """Get all discounts"""
        return self.data.get('discounts', [])
    
    def validate_discount(self, code: str) -> Optional[Dict]:
        """Validate and return discount if valid"""
        for discount in self.data['discounts']:
            if discount['code'] == code.upper() and discount['active']:
                expiry_date = datetime.fromisoformat(discount['expiry'])
                if expiry_date > datetime.now():
                    return discount
        return None

# Initialize data manager
data_manager = DataManager()

# Helper functions
def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_IDS

def create_main_keyboard():
    """Create main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton(LABELS['events'], callback_data='events_menu')],
        [InlineKeyboardButton(LABELS['vip_tiers'], callback_data='vip_menu')],
        [InlineKeyboardButton(LABELS['discounts'], callback_data='discounts_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_back_keyboard():
    """Create back button keyboard"""
    keyboard = [[InlineKeyboardButton(LABELS['back'], callback_data='back_to_admin')]]
    return InlineKeyboardMarkup(keyboard)

def create_event_keyboard():
    """Create event management keyboard"""
    keyboard = [
        [InlineKeyboardButton(LABELS['add'], callback_data='add_event')],
        [InlineKeyboardButton(LABELS['view'], callback_data='view_events')],
        [InlineKeyboardButton(LABELS['back'], callback_data='back_to_admin')],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_vip_keyboard():
    """Create VIP management keyboard"""
    keyboard = [
        [InlineKeyboardButton(LABELS['add'], callback_data='add_vip')],
        [InlineKeyboardButton(LABELS['view'], callback_data='view_vip')],
        [InlineKeyboardButton(LABELS['back'], callback_data='back_to_admin')],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_discounts_keyboard():
    """Create discounts management keyboard"""
    keyboard = [
        [InlineKeyboardButton(LABELS['add'], callback_data='add_discount')],
        [InlineKeyboardButton(LABELS['view'], callback_data='view_discounts')],
        [InlineKeyboardButton(LABELS['back'], callback_data='back_to_admin')],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_confirm_keyboard():
    """Create confirmation keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(LABELS['confirm'], callback_data='confirm_yes'),
            InlineKeyboardButton(LABELS['cancel'], callback_data='confirm_no'),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    
    if is_admin(user.id):
        await update.message.reply_text(
            f"{LABELS['welcome']}\n\n{LABELS['admin_panel']}:",
            reply_markup=create_main_keyboard()
        )
    else:
        await update.message.reply_text(LABELS['welcome'])

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.callback_query.answer(LABELS['admin_only'])
        return
    
    await update.callback_query.edit_message_text(
        text=LABELS['admin_panel'],
        reply_markup=create_main_keyboard()
    )

# Event handlers
async def events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Events menu"""
    await update.callback_query.edit_message_text(
        text=LABELS['events'],
        reply_markup=create_event_keyboard()
    )

async def add_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding an event"""
    context.user_data['new_event'] = {}
    await update.callback_query.edit_message_text(
        text=LABELS['event_name'],
        reply_markup=create_back_keyboard()
    )
    context.user_data['state'] = 'waiting_event_name'
    return EVENT_NAME

async def view_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all events"""
    events = data_manager.get_events()
    
    if not events:
        text = LABELS['no_events']
    else:
        text = f"{LABELS['event_list']}:\n\n"
        for event in events:
            text += f"📌 {event['name']}\n"
            text += f"📅 {event['date']}\n"
            text += f"📝 {event['description']}\n"
            text += f"🔗 ID: {event['id']}\n\n"
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=create_event_keyboard()
    )

# VIP Tier handlers
async def vip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """VIP management menu"""
    await update.callback_query.edit_message_text(
        text=LABELS['vip_tiers'],
        reply_markup=create_vip_keyboard()
    )

async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a VIP tier"""
    context.user_data['new_vip'] = {}
    await update.callback_query.edit_message_text(
        text=LABELS['vip_tier_name'],
        reply_markup=create_back_keyboard()
    )
    context.user_data['state'] = 'waiting_vip_name'
    return VIP_TIER_NAME

async def view_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all VIP tiers"""
    vip_tiers = data_manager.get_vip_tiers()
    
    if not vip_tiers:
        text = LABELS['no_vip']
    else:
        text = f"{LABELS['vip_list']}:\n\n"
        for tier in vip_tiers:
            text += f"👑 {tier['name']}\n"
            text += f"💎 {tier['benefits']}\n"
            text += f"💰 {tier['price']}\n"
            text += f"🔗 ID: {tier['id']}\n\n"
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=create_vip_keyboard()
    )

# Discount handlers
async def discounts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Discounts management menu"""
    await update.callback_query.edit_message_text(
        text=LABELS['discounts'],
        reply_markup=create_discounts_keyboard()
    )

async def add_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a discount"""
    context.user_data['new_discount'] = {}
    await update.callback_query.edit_message_text(
        text=LABELS['discount_code'],
        reply_markup=create_back_keyboard()
    )
    context.user_data['state'] = 'waiting_discount_code'
    return DISCOUNT_CODE

async def view_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View all discounts"""
    discounts = data_manager.get_discounts()
    
    if not discounts:
        text = LABELS['no_discounts']
    else:
        text = f"{LABELS['discount_list']}:\n\n"
        for discount in discounts:
            status = "✅" if discount['active'] else "❌"
            text += f"{status} {discount['code']}\n"
            text += f"📊 {discount['percentage']}%\n"
            text += f"📅 {discount['expiry']}\n"
            text += f"🔗 ID: {discount['id']}\n\n"
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=create_discounts_keyboard()
    )

# Message handlers for conversation
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages during conversations"""
    state = context.user_data.get('state')
    text = update.message.text
    
    try:
        # Event conversation
        if state == 'waiting_event_name':
            context.user_data['new_event']['name'] = text
            context.user_data['state'] = 'waiting_event_date'
            await update.message.reply_text(LABELS['event_date'])
            return EVENT_DATE
        
        elif state == 'waiting_event_date':
            context.user_data['new_event']['date'] = text
            context.user_data['state'] = 'waiting_event_desc'
            await update.message.reply_text(LABELS['event_description'])
            return EVENT_DESC
        
        elif state == 'waiting_event_desc':
            context.user_data['new_event']['description'] = text
            event_data = context.user_data['new_event']
            
            confirm_text = (
                f"📌 {LABELS['event_name']} {event_data['name']}\n"
                f"📅 {LABELS['event_date']} {event_data['date']}\n"
                f"📝 {LABELS['event_description']} {event_data['description']}\n\n"
                f"آیا این اطلاعات صحیح است؟"
            )
            await update.message.reply_text(
                confirm_text,
                reply_markup=create_confirm_keyboard()
            )
            context.user_data['state'] = 'confirming_event'
            return EVENT_CONFIRM
        
        # VIP conversation
        elif state == 'waiting_vip_name':
            context.user_data['new_vip']['name'] = text
            context.user_data['state'] = 'waiting_vip_benefit'
            await update.message.reply_text(LABELS['vip_tier_benefit'])
            return VIP_TIER_BENEFIT
        
        elif state == 'waiting_vip_benefit':
            context.user_data['new_vip']['benefits'] = text
            context.user_data['state'] = 'waiting_vip_price'
            await update.message.reply_text(LABELS['vip_tier_price'])
            return VIP_TIER_PRICE
        
        elif state == 'waiting_vip_price':
            try:
                price = float(text)
                context.user_data['new_vip']['price'] = price
                vip_data = context.user_data['new_vip']
                
                confirm_text = (
                    f"👑 {LABELS['vip_tier_name']} {vip_data['name']}\n"
                    f"💎 {LABELS['vip_tier_benefit']} {vip_data['benefits']}\n"
                    f"💰 {LABELS['vip_tier_price']} {vip_data['price']}\n\n"
                    f"آیا این اطلاعات صحیح است؟"
                )
                await update.message.reply_text(
                    confirm_text,
                    reply_markup=create_confirm_keyboard()
                )
                context.user_data['state'] = 'confirming_vip'
                return VIP_TIER_CONFIRM
            except ValueError:
                await update.message.reply_text("❌ لطفا یک عدد معتبر وارد کنید.")
                return VIP_TIER_PRICE
        
        # Discount conversation
        elif state == 'waiting_discount_code':
            context.user_data['new_discount']['code'] = text
            context.user_data['state'] = 'waiting_discount_percent'
            await update.message.reply_text(LABELS['discount_percent'])
            return DISCOUNT_PERCENT
        
        elif state == 'waiting_discount_percent':
            try:
                percent = float(text)
                if 0 <= percent <= 100:
                    context.user_data['new_discount']['percentage'] = percent
                    context.user_data['state'] = 'waiting_discount_expiry'
                    await update.message.reply_text(LABELS['discount_expiry'])
                    return DISCOUNT_EXPIRY
                else:
                    await update.message.reply_text("❌ درصد باید بین 0 و 100 باشد.")
                    return DISCOUNT_PERCENT
            except ValueError:
                await update.message.reply_text("❌ لطفا یک عدد معتبر وارد کنید.")
                return DISCOUNT_PERCENT
        
        elif state == 'waiting_discount_expiry':
            context.user_data['new_discount']['expiry'] = text
            discount_data = context.user_data['new_discount']
            
            confirm_text = (
                f"🎁 {LABELS['discount_code']} {discount_data['code']}\n"
                f"📊 {LABELS['discount_percent']} {discount_data['percentage']}%\n"
                f"📅 {LABELS['discount_expiry']} {discount_data['expiry']}\n\n"
                f"آیا این اطلاعات صحیح است؟"
            )
            await update.message.reply_text(
                confirm_text,
                reply_markup=create_confirm_keyboard()
            )
            context.user_data['state'] = 'confirming_discount'
            return DISCOUNT_CONFIRM
    
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text(LABELS['error'])

# Callback handlers for confirmations
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Navigation
    if data == 'back_to_admin':
        await admin_panel(update, context)
    elif data == 'events_menu':
        await events_menu(update, context)
    elif data == 'add_event':
        await add_event(update, context)
    elif data == 'view_events':
        await view_events(update, context)
    elif data == 'vip_menu':
        await vip_menu(update, context)
    elif data == 'add_vip':
        await add_vip(update, context)
    elif data == 'view_vip':
        await view_vip(update, context)
    elif data == 'discounts_menu':
        await discounts_menu(update, context)
    elif data == 'add_discount':
        await add_discount(update, context)
    elif data == 'view_discounts':
        await view_discounts(update, context)
    
    # Confirmations
    elif data == 'confirm_yes':
        state = context.user_data.get('state')
        
        if state == 'confirming_event':
            event_data = context.user_data['new_event']
            data_manager.add_event(
                event_data['name'],
                event_data['date'],
                event_data['description']
            )
            await query.edit_message_text(
                text=LABELS['event_added'],
                reply_markup=create_event_keyboard()
            )
            context.user_data['state'] = None
        
        elif state == 'confirming_vip':
            vip_data = context.user_data['new_vip']
            data_manager.add_vip_tier(
                vip_data['name'],
                vip_data['benefits'],
                vip_data['price']
            )
            await query.edit_message_text(
                text=LABELS['vip_added'],
                reply_markup=create_vip_keyboard()
            )
            context.user_data['state'] = None
        
        elif state == 'confirming_discount':
            discount_data = context.user_data['new_discount']
            data_manager.add_discount(
                discount_data['code'],
                discount_data['percentage'],
                discount_data['expiry']
            )
            await query.edit_message_text(
                text=LABELS['discount_added'],
                reply_markup=create_discounts_keyboard()
            )
            context.user_data['state'] = None
    
    elif data == 'confirm_no':
        await query.edit_message_text(
            text=LABELS['cancel'],
            reply_markup=create_main_keyboard()
        )
        context.user_data['state'] = None

def main():
    """Main function to start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
