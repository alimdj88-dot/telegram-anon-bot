"""
Telegram Anonymous Bot with Advanced Management Features
Features: Events, VIP Tiers, Discounts, and Admin Panel
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database configuration
DB_NAME = 'telegram_bot.db'

# Conversation states
class ConversationState(Enum):
    """Conversation states for different flows"""
    WAITING_EVENT_NAME = 1
    WAITING_EVENT_DATE = 2
    WAITING_EVENT_DESCRIPTION = 3
    WAITING_VIP_TIER_NAME = 4
    WAITING_VIP_TIER_BENEFITS = 5
    WAITING_VIP_TIER_PRICE = 6
    WAITING_DISCOUNT_NAME = 7
    WAITING_DISCOUNT_PERCENTAGE = 8
    WAITING_DISCOUNT_CODE = 9
    WAITING_DISCOUNT_EXPIRY = 10


# Data Models
@dataclass
class Event:
    """Event data model"""
    id: Optional[int] = None
    name: str = ""
    date: str = ""
    description: str = ""
    max_participants: int = 0
    current_participants: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class VIPTier:
    """VIP Tier data model"""
    id: Optional[int] = None
    name: str = ""
    benefits: str = ""
    price: float = 0.0
    max_members: int = 0
    current_members: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Discount:
    """Discount data model"""
    id: Optional[int] = None
    name: str = ""
    code: str = ""
    percentage: float = 0.0
    max_uses: int = 0
    current_uses: int = 0
    expiry_date: str = ""
    created_at: str = ""
    updated_at: str = ""


# Database Manager
class DatabaseManager:
    """Handles all database operations"""

    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                is_admin BOOLEAN DEFAULT 0,
                is_vip BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                max_participants INTEGER DEFAULT 0,
                current_participants INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # VIP Tiers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_tiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                benefits TEXT,
                price REAL NOT NULL,
                max_members INTEGER DEFAULT 0,
                current_members INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Discounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                percentage REAL NOT NULL,
                max_uses INTEGER DEFAULT 0,
                current_uses INTEGER DEFAULT 0,
                expiry_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Event Registrations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (event_id) REFERENCES events(id),
                UNIQUE(user_id, event_id)
            )
        ''')

        # VIP Memberships table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vip_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tier_id INTEGER NOT NULL,
                expiry_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (tier_id) REFERENCES vip_tiers(id)
            )
        ''')

        # Discount Usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discount_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                discount_id INTEGER NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (discount_id) REFERENCES discounts(id)
            )
        ''')

        conn.commit()
        conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Execute a SELECT query"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        return result

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT, UPDATE, or DELETE query"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id


# Event Manager
class EventManager:
    """Manages event CRUD operations and admin controls"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_event(self, name: str, date: str, description: str, max_participants: int = 0) -> int:
        """Create a new event"""
        query = '''
            INSERT INTO events (name, date, description, max_participants, current_participants)
            VALUES (?, ?, ?, ?, 0)
        '''
        return self.db.execute_update(query, (name, date, description, max_participants))

    def read_event(self, event_id: int) -> Optional[Event]:
        """Get event by ID"""
        query = 'SELECT * FROM events WHERE id = ?'
        result = self.db.execute_query(query, (event_id,))
        if result:
            return self._map_to_event(result[0])
        return None

    def read_all_events(self, limit: int = 100, offset: int = 0) -> List[Event]:
        """Get all events with pagination"""
        query = 'SELECT * FROM events ORDER BY date DESC LIMIT ? OFFSET ?'
        results = self.db.execute_query(query, (limit, offset))
        return [self._map_to_event(row) for row in results]

    def update_event(self, event_id: int, **kwargs) -> bool:
        """Update event details"""
        allowed_fields = {'name', 'date', 'description', 'max_participants'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False

        updates['updated_at'] = datetime.utcnow().isoformat()
        set_clause = ', '.join([f'{k} = ?' for k in updates.keys()])
        query = f'UPDATE events SET {set_clause} WHERE id = ?'
        
        self.db.execute_update(query, tuple(updates.values()) + (event_id,))
        return True

    def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        # Delete registrations first
        self.db.execute_update('DELETE FROM event_registrations WHERE event_id = ?', (event_id,))
        # Delete event
        self.db.execute_update('DELETE FROM events WHERE id = ?', (event_id,))
        return True

    def register_user(self, user_id: int, event_id: int) -> bool:
        """Register user for event"""
        try:
            query = '''
                INSERT INTO event_registrations (user_id, event_id)
                VALUES (?, ?)
            '''
            self.db.execute_update(query, (user_id, event_id))
            
            # Update current participants
            self.db.execute_update(
                'UPDATE events SET current_participants = current_participants + 1 WHERE id = ?',
                (event_id,)
            )
            return True
        except sqlite3.IntegrityError:
            return False  # Already registered

    def unregister_user(self, user_id: int, event_id: int) -> bool:
        """Unregister user from event"""
        self.db.execute_update(
            'DELETE FROM event_registrations WHERE user_id = ? AND event_id = ?',
            (user_id, event_id)
        )
        # Update current participants
        self.db.execute_update(
            'UPDATE events SET current_participants = current_participants - 1 WHERE id = ?',
            (event_id,)
        )
        return True

    def get_event_participants(self, event_id: int) -> List[Dict]:
        """Get all participants of an event"""
        query = '''
            SELECT u.telegram_id, u.username 
            FROM event_registrations er
            JOIN users u ON er.user_id = u.id
            WHERE er.event_id = ?
        '''
        results = self.db.execute_query(query, (event_id,))
        return [{'telegram_id': r[0], 'username': r[1]} for r in results]

    @staticmethod
    def _map_to_event(row: Tuple) -> Event:
        """Map database row to Event object"""
        return Event(
            id=row[0],
            name=row[1],
            date=row[2],
            description=row[3],
            max_participants=row[4],
            current_participants=row[5],
            created_at=row[6],
            updated_at=row[7]
        )


# VIP Tier Manager
class VIPTierManager:
    """Manages VIP tier CRUD operations and admin controls"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_tier(self, name: str, benefits: str, price: float, max_members: int = 0) -> int:
        """Create a new VIP tier"""
        query = '''
            INSERT INTO vip_tiers (name, benefits, price, max_members, current_members)
            VALUES (?, ?, ?, ?, 0)
        '''
        return self.db.execute_update(query, (name, benefits, price, max_members))

    def read_tier(self, tier_id: int) -> Optional[VIPTier]:
        """Get VIP tier by ID"""
        query = 'SELECT * FROM vip_tiers WHERE id = ?'
        result = self.db.execute_query(query, (tier_id,))
        if result:
            return self._map_to_tier(result[0])
        return None

    def read_tier_by_name(self, name: str) -> Optional[VIPTier]:
        """Get VIP tier by name"""
        query = 'SELECT * FROM vip_tiers WHERE name = ?'
        result = self.db.execute_query(query, (name,))
        if result:
            return self._map_to_tier(result[0])
        return None

    def read_all_tiers(self, limit: int = 100, offset: int = 0) -> List[VIPTier]:
        """Get all VIP tiers with pagination"""
        query = 'SELECT * FROM vip_tiers ORDER BY price ASC LIMIT ? OFFSET ?'
        results = self.db.execute_query(query, (limit, offset))
        return [self._map_to_tier(row) for row in results]

    def update_tier(self, tier_id: int, **kwargs) -> bool:
        """Update VIP tier details"""
        allowed_fields = {'name', 'benefits', 'price', 'max_members'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False

        updates['updated_at'] = datetime.utcnow().isoformat()
        set_clause = ', '.join([f'{k} = ?' for k in updates.keys()])
        query = f'UPDATE vip_tiers SET {set_clause} WHERE id = ?'
        
        self.db.execute_update(query, tuple(updates.values()) + (tier_id,))
        return True

    def delete_tier(self, tier_id: int) -> bool:
        """Delete a VIP tier"""
        # Delete memberships first
        self.db.execute_update('DELETE FROM vip_memberships WHERE tier_id = ?', (tier_id,))
        # Delete tier
        self.db.execute_update('DELETE FROM vip_tiers WHERE id = ?', (tier_id,))
        return True

    def add_member(self, user_id: int, tier_id: int, expiry_days: int = 365) -> bool:
        """Add user to VIP tier"""
        try:
            expiry_date = (datetime.utcnow() + timedelta(days=expiry_days)).isoformat()
            query = '''
                INSERT INTO vip_memberships (user_id, tier_id, expiry_date)
                VALUES (?, ?, ?)
            '''
            self.db.execute_update(query, (user_id, tier_id, expiry_date))
            
            # Update current members
            self.db.execute_update(
                'UPDATE vip_tiers SET current_members = current_members + 1 WHERE id = ?',
                (tier_id,)
            )
            
            # Mark user as VIP
            self.db.execute_update(
                'UPDATE users SET is_vip = 1 WHERE id = ?',
                (user_id,)
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_member(self, user_id: int, tier_id: int) -> bool:
        """Remove user from VIP tier"""
        self.db.execute_update(
            'DELETE FROM vip_memberships WHERE user_id = ? AND tier_id = ?',
            (user_id, tier_id)
        )
        # Update current members
        self.db.execute_update(
            'UPDATE vip_tiers SET current_members = current_members - 1 WHERE id = ?',
            (tier_id,)
        )
        
        # Check if user has any other VIP membership
        result = self.db.execute_query(
            'SELECT COUNT(*) FROM vip_memberships WHERE user_id = ?',
            (user_id,)
        )
        if result[0][0] == 0:
            self.db.execute_update(
                'UPDATE users SET is_vip = 0 WHERE id = ?',
                (user_id,)
            )
        return True

    def get_tier_members(self, tier_id: int) -> List[Dict]:
        """Get all members of a VIP tier"""
        query = '''
            SELECT u.telegram_id, u.username, vm.expiry_date
            FROM vip_memberships vm
            JOIN users u ON vm.user_id = u.id
            WHERE vm.tier_id = ?
        '''
        results = self.db.execute_query(query, (tier_id,))
        return [{'telegram_id': r[0], 'username': r[1], 'expiry_date': r[2]} for r in results]

    @staticmethod
    def _map_to_tier(row: Tuple) -> VIPTier:
        """Map database row to VIPTier object"""
        return VIPTier(
            id=row[0],
            name=row[1],
            benefits=row[2],
            price=row[3],
            max_members=row[4],
            current_members=row[5],
            created_at=row[6],
            updated_at=row[7]
        )


# Discount Manager
class DiscountManager:
    """Manages discount CRUD operations and admin controls"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def create_discount(self, name: str, code: str, percentage: float, max_uses: int, expiry_date: str) -> int:
        """Create a new discount"""
        query = '''
            INSERT INTO discounts (name, code, percentage, max_uses, current_uses, expiry_date)
            VALUES (?, ?, ?, ?, 0, ?)
        '''
        return self.db.execute_update(query, (name, code, percentage, max_uses, expiry_date))

    def read_discount(self, discount_id: int) -> Optional[Discount]:
        """Get discount by ID"""
        query = 'SELECT * FROM discounts WHERE id = ?'
        result = self.db.execute_query(query, (discount_id,))
        if result:
            return self._map_to_discount(result[0])
        return None

    def read_discount_by_code(self, code: str) -> Optional[Discount]:
        """Get discount by code"""
        query = 'SELECT * FROM discounts WHERE code = ?'
        result = self.db.execute_query(query, (code,))
        if result:
            return self._map_to_discount(result[0])
        return None

    def read_all_discounts(self, limit: int = 100, offset: int = 0) -> List[Discount]:
        """Get all discounts with pagination"""
        query = 'SELECT * FROM discounts ORDER BY created_at DESC LIMIT ? OFFSET ?'
        results = self.db.execute_query(query, (limit, offset))
        return [self._map_to_discount(row) for row in results]

    def update_discount(self, discount_id: int, **kwargs) -> bool:
        """Update discount details"""
        allowed_fields = {'name', 'code', 'percentage', 'max_uses', 'expiry_date'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False

        updates['updated_at'] = datetime.utcnow().isoformat()
        set_clause = ', '.join([f'{k} = ?' for k in updates.keys()])
        query = f'UPDATE discounts SET {set_clause} WHERE id = ?'
        
        self.db.execute_update(query, tuple(updates.values()) + (discount_id,))
        return True

    def delete_discount(self, discount_id: int) -> bool:
        """Delete a discount"""
        # Delete usage records first
        self.db.execute_update('DELETE FROM discount_usage WHERE discount_id = ?', (discount_id,))
        # Delete discount
        self.db.execute_update('DELETE FROM discounts WHERE id = ?', (discount_id,))
        return True

    def apply_discount(self, user_id: int, discount_id: int) -> Tuple[bool, str]:
        """Apply discount for user"""
        discount = self.read_discount(discount_id)
        if not discount:
            return False, "Discount not found"

        # Check expiry
        if datetime.fromisoformat(discount.expiry_date) < datetime.utcnow():
            return False, "Discount has expired"

        # Check max uses
        if discount.current_uses >= discount.max_uses > 0:
            return False, "Discount usage limit reached"

        # Record usage
        query = '''
            INSERT INTO discount_usage (user_id, discount_id)
            VALUES (?, ?)
        '''
        try:
            self.db.execute_update(query, (user_id, discount_id))
            
            # Update current uses
            self.db.execute_update(
                'UPDATE discounts SET current_uses = current_uses + 1 WHERE id = ?',
                (discount_id,)
            )
            return True, f"Discount applied: {discount.percentage}% off"
        except sqlite3.IntegrityError:
            return False, "Error applying discount"

    def get_discount_usage(self, discount_id: int) -> List[Dict]:
        """Get all users who used a discount"""
        query = '''
            SELECT u.telegram_id, u.username, du.used_at
            FROM discount_usage du
            JOIN users u ON du.user_id = u.id
            WHERE du.discount_id = ?
        '''
        results = self.db.execute_query(query, (discount_id,))
        return [{'telegram_id': r[0], 'username': r[1], 'used_at': r[2]} for r in results]

    def is_valid_discount(self, code: str) -> Tuple[bool, Optional[Discount]]:
        """Check if discount code is valid"""
        discount = self.read_discount_by_code(code)
        if not discount:
            return False, None

        # Check expiry
        if datetime.fromisoformat(discount.expiry_date) < datetime.utcnow():
            return False, None

        # Check max uses
        if discount.current_uses >= discount.max_uses > 0:
            return False, None

        return True, discount

    @staticmethod
    def _map_to_discount(row: Tuple) -> Discount:
        """Map database row to Discount object"""
        return Discount(
            id=row[0],
            name=row[1],
            code=row[2],
            percentage=row[3],
            max_uses=row[4],
            current_uses=row[5],
            expiry_date=row[6],
            created_at=row[7],
            updated_at=row[8]
        )


# Admin UI Callbacks
async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display admin menu"""
    keyboard = [
        [InlineKeyboardButton("📅 Manage Events", callback_data="admin_events")],
        [InlineKeyboardButton("👑 Manage VIP Tiers", callback_data="admin_vip_tiers")],
        [InlineKeyboardButton("🏷️ Manage Discounts", callback_data="admin_discounts")],
        [InlineKeyboardButton("❌ Close Menu", callback_data="admin_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text="🔧 *Admin Control Panel*\n\nSelect an option to manage:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


async def show_events_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show events management menu"""
    db = context.bot_data['db']
    event_manager = context.bot_data['event_manager']
    
    events = event_manager.read_all_events(limit=5)
    
    keyboard = [
        [InlineKeyboardButton("➕ Create Event", callback_data="event_create")],
        [InlineKeyboardButton("📖 View Events", callback_data="event_list")],
        [InlineKeyboardButton("🔄 Back", callback_data="admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "*📅 Event Management*\n\n"
    if events:
        text += f"Active Events ({len(events)}):\n"
        for event in events:
            text += f"• {event.name} - {event.date}\n"
    else:
        text += "No events yet.\n"
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationState.WAITING_EVENT_NAME.value


async def create_event_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start creating new event"""
    await update.callback_query.edit_message_text(
        text="📝 Enter event name:",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationState.WAITING_EVENT_NAME.value


async def event_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle event name input"""
    context.user_data['event_name'] = update.message.text
    await update.message.reply_text("📅 Enter event date (YYYY-MM-DD):")
    return ConversationState.WAITING_EVENT_DATE.value


async def event_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle event date input"""
    context.user_data['event_date'] = update.message.text
    await update.message.reply_text("📖 Enter event description:")
    return ConversationState.WAITING_EVENT_DESCRIPTION.value


async def event_description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle event description and save"""
    event_manager = context.bot_data['event_manager']
    
    event_id = event_manager.create_event(
        name=context.user_data['event_name'],
        date=context.user_data['event_date'],
        description=update.message.text
    )
    
    await update.message.reply_text(
        f"✅ Event '{context.user_data['event_name']}' created successfully!\nEvent ID: {event_id}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data.clear()


async def show_vip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show VIP tiers management menu"""
    vip_manager = context.bot_data['vip_manager']
    tiers = vip_manager.read_all_tiers(limit=5)
    
    keyboard = [
        [InlineKeyboardButton("➕ Create Tier", callback_data="vip_create")],
        [InlineKeyboardButton("📖 View Tiers", callback_data="vip_list")],
        [InlineKeyboardButton("🔄 Back", callback_data="admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "*👑 VIP Tier Management*\n\n"
    if tiers:
        text += f"Active Tiers ({len(tiers)}):\n"
        for tier in tiers:
            text += f"• {tier.name} - ${tier.price}\n"
    else:
        text += "No VIP tiers yet.\n"
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationState.WAITING_VIP_TIER_NAME.value


async def create_vip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start creating new VIP tier"""
    await update.callback_query.edit_message_text(
        text="👑 Enter VIP tier name:",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationState.WAITING_VIP_TIER_NAME.value


async def vip_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle VIP tier name input"""
    context.user_data['vip_name'] = update.message.text
    await update.message.reply_text("📝 Enter tier benefits (comma-separated):")
    return ConversationState.WAITING_VIP_TIER_BENEFITS.value


async def vip_benefits_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle VIP tier benefits input"""
    context.user_data['vip_benefits'] = update.message.text
    await update.message.reply_text("💰 Enter tier price (USD):")
    return ConversationState.WAITING_VIP_TIER_PRICE.value


async def vip_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle VIP tier price and save"""
    vip_manager = context.bot_data['vip_manager']
    
    try:
        price = float(update.message.text)
        tier_id = vip_manager.create_tier(
            name=context.user_data['vip_name'],
            benefits=context.user_data['vip_benefits'],
            price=price
        )
        
        await update.message.reply_text(
            f"✅ VIP tier '{context.user_data['vip_name']}' created successfully!\nTier ID: {tier_id}",
            parse_mode=ParseMode.MARKDOWN
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Please enter a valid number.")
    
    context.user_data.clear()


async def show_discounts_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show discounts management menu"""
    discount_manager = context.bot_data['discount_manager']
    discounts = discount_manager.read_all_discounts(limit=5)
    
    keyboard = [
        [InlineKeyboardButton("➕ Create Discount", callback_data="discount_create")],
        [InlineKeyboardButton("📖 View Discounts", callback_data="discount_list")],
        [InlineKeyboardButton("🔄 Back", callback_data="admin_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "*🏷️ Discount Management*\n\n"
    if discounts:
        text += f"Active Discounts ({len(discounts)}):\n"
        for discount in discounts:
            text += f"• {discount.code} - {discount.percentage}% off\n"
    else:
        text += "No discounts yet.\n"
    
    await update.callback_query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationState.WAITING_DISCOUNT_NAME.value


async def create_discount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start creating new discount"""
    await update.callback_query.edit_message_text(
        text="🏷️ Enter discount name:",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationState.WAITING_DISCOUNT_NAME.value


async def discount_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle discount name input"""
    context.user_data['discount_name'] = update.message.text
    await update.message.reply_text("🔤 Enter discount code:")
    return ConversationState.WAITING_DISCOUNT_CODE.value


async def discount_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle discount code input"""
    context.user_data['discount_code'] = update.message.text.upper()
    await update.message.reply_text("📊 Enter discount percentage:")
    return ConversationState.WAITING_DISCOUNT_PERCENTAGE.value


async def discount_percentage_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle discount percentage input"""
    try:
        context.user_data['discount_percentage'] = float(update.message.text)
        await update.message.reply_text("📅 Enter expiry date (YYYY-MM-DD):")
        return ConversationState.WAITING_DISCOUNT_EXPIRY.value
    except ValueError:
        await update.message.reply_text("❌ Invalid percentage. Please enter a valid number.")
        return ConversationState.WAITING_DISCOUNT_PERCENTAGE.value


async def discount_expiry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle discount expiry and save"""
    discount_manager = context.bot_data['discount_manager']
    
    try:
        discount_id = discount_manager.create_discount(
            name=context.user_data['discount_name'],
            code=context.user_data['discount_code'],
            percentage=context.user_data['discount_percentage'],
            max_uses=0,  # Unlimited
            expiry_date=update.message.text
        )
        
        await update.message.reply_text(
            f"✅ Discount '{context.user_data['discount_code']}' created successfully!\nDiscount ID: {discount_id}",
            parse_mode=ParseMode.MARKDOWN
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid date format. Please use YYYY-MM-DD.")
    
    context.user_data.clear()


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_menu":
        await show_admin_menu(update, context)
    elif query.data == "admin_events":
        return await show_events_menu(update, context)
    elif query.data == "event_create":
        return await create_event_handler(update, context)
    elif query.data == "admin_vip_tiers":
        return await show_vip_menu(update, context)
    elif query.data == "vip_create":
        return await create_vip_handler(update, context)
    elif query.data == "admin_discounts":
        return await show_discounts_menu(update, context)
    elif query.data == "discount_create":
        return await create_discount_handler(update, context)
    elif query.data == "admin_close":
        await query.delete_message()
    
    return ConversationHandler.END


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    keyboard = [
        [InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_menu")],
        [InlineKeyboardButton("📅 View Events", callback_data="view_events")],
        [InlineKeyboardButton("👑 VIP Membership", callback_data="view_vip")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 Welcome to Telegram Anonymous Bot!\n\n"
        "Choose an option:",
        reply_markup=reply_markup
    )


async def main():
    """Initialize and run the bot"""
    from telegram import BotCommand
    
    # Replace with your bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # Initialize application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Initialize database and managers
    db = DatabaseManager()
    event_manager = EventManager(db)
    vip_manager = VIPTierManager(db)
    discount_manager = DiscountManager(db)
    
    # Store in bot data
    application.bot_data['db'] = db
    application.bot_data['event_manager'] = event_manager
    application.bot_data['vip_manager'] = vip_manager
    application.bot_data['discount_manager'] = discount_manager
    
    # Set bot commands
    await application.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("admin", "Access admin panel"),
        BotCommand("help", "Show help"),
    ])
    
    # Conversation handlers
    event_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_event_handler, pattern="event_create"),
        ],
        states={
            ConversationState.WAITING_EVENT_NAME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_name_handler)
            ],
            ConversationState.WAITING_EVENT_DATE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_date_handler)
            ],
            ConversationState.WAITING_EVENT_DESCRIPTION.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, event_description_handler)
            ],
        },
        fallbacks=[CallbackQueryHandler(button_callback)],
    )
    
    vip_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_vip_handler, pattern="vip_create"),
        ],
        states={
            ConversationState.WAITING_VIP_TIER_NAME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, vip_name_handler)
            ],
            ConversationState.WAITING_VIP_TIER_BENEFITS.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, vip_benefits_handler)
            ],
            ConversationState.WAITING_VIP_TIER_PRICE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, vip_price_handler)
            ],
        },
        fallbacks=[CallbackQueryHandler(button_callback)],
    )
    
    discount_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_discount_handler, pattern="discount_create"),
        ],
        states={
            ConversationState.WAITING_DISCOUNT_NAME.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, discount_name_handler)
            ],
            ConversationState.WAITING_DISCOUNT_CODE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, discount_code_handler)
            ],
            ConversationState.WAITING_DISCOUNT_PERCENTAGE.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, discount_percentage_handler)
            ],
            ConversationState.WAITING_DISCOUNT_EXPIRY.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, discount_expiry_handler)
            ],
        },
        fallbacks=[CallbackQueryHandler(button_callback)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(event_conv)
    application.add_handler(vip_conv)
    application.add_handler(discount_conv)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start the bot
    await application.run_polling()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
