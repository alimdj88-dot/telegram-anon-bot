#!/usr/bin/env python3
"""
Telegram Anonymous Bot - Enhanced Version
Features: Anonymous messaging, VIP tiers, event management, and discount system
Author: alimdj88-dot
"""

import logging
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User as TelegramUser
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatAction, ParseMode

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Data Classes
# ============================================================================

class VIPTier(Enum):
    """VIP tier levels"""
    STANDARD = 0
    SILVER = 1
    GOLD = 2
    PLATINUM = 3


class EventStatus(Enum):
    """Event status types"""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DiscountType(Enum):
    """Discount type options"""
    PERCENTAGE = "percentage"
    FIXED = "fixed"


@dataclass
class UserProfile:
    """User profile data"""
    user_id: int
    username: str
    vip_tier: int = VIPTier.STANDARD.value
    messages_sent: int = 0
    messages_received: int = 0
    joined_date: str = None
    total_spent: float = 0.0
    
    def __post_init__(self):
        if self.joined_date is None:
            self.joined_date = datetime.utcnow().isoformat()


@dataclass
class Event:
    """Event data"""
    event_id: int
    title: str
    description: str
    creator_id: int
    status: str = EventStatus.DRAFT.value
    created_date: str = None
    start_date: str = None
    end_date: str = None
    participants: int = 0
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.utcnow().isoformat()


@dataclass
class Discount:
    """Discount data"""
    discount_id: int
    code: str
    discount_type: str = DiscountType.PERCENTAGE.value
    discount_value: float = 0.0
    applicable_vip_tier: int = VIPTier.STANDARD.value
    max_uses: int = -1  # -1 for unlimited
    current_uses: int = 0
    expiry_date: str = None
    active: bool = True


# ============================================================================
# Database Manager
# ============================================================================

class DatabaseManager:
    """Manages SQLite database operations"""
    
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    vip_tier INTEGER DEFAULT 0,
                    messages_sent INTEGER DEFAULT 0,
                    messages_received INTEGER DEFAULT 0,
                    joined_date TEXT,
                    total_spent REAL DEFAULT 0.0,
                    last_active TEXT
                )
            ''')
            
            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER,
                    recipient_id INTEGER,
                    content TEXT,
                    sent_date TEXT,
                    is_read INTEGER DEFAULT 0,
                    FOREIGN KEY(sender_id) REFERENCES users(user_id),
                    FOREIGN KEY(recipient_id) REFERENCES users(user_id)
                )
            ''')
            
            # Events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    creator_id INTEGER,
                    status TEXT DEFAULT 'draft',
                    created_date TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    participants INTEGER DEFAULT 0,
                    FOREIGN KEY(creator_id) REFERENCES users(user_id)
                )
            ''')
            
            # Event participants table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS event_participants (
                    event_id INTEGER,
                    user_id INTEGER,
                    joined_date TEXT,
                    PRIMARY KEY(event_id, user_id),
                    FOREIGN KEY(event_id) REFERENCES events(event_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Discounts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discounts (
                    discount_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    discount_type TEXT,
                    discount_value REAL,
                    applicable_vip_tier INTEGER,
                    max_uses INTEGER DEFAULT -1,
                    current_uses INTEGER DEFAULT 0,
                    expiry_date TEXT,
                    active INTEGER DEFAULT 1,
                    created_date TEXT
                )
            ''')
            
            # Discount usage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discount_usage (
                    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discount_id INTEGER,
                    user_id INTEGER,
                    used_date TEXT,
                    FOREIGN KEY(discount_id) REFERENCES discounts(discount_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sender ON messages(sender_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipient ON messages(recipient_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_creator ON events(creator_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_discount_code ON discounts(code)')
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")


# ============================================================================
# Event Manager
# ============================================================================

class EventManager:
    """Manages events and event participants"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_event(self, title: str, description: str, creator_id: int,
                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[int]:
        """Create a new event"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO events (title, description, creator_id, created_date, start_date, end_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (title, description, creator_id, datetime.utcnow().isoformat(), start_date, end_date))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None
    
    def get_event(self, event_id: int) -> Optional[Event]:
        """Get event details"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM events WHERE event_id = ?', (event_id,))
                row = cursor.fetchone()
                if row:
                    return Event(**dict(row))
        except Exception as e:
            logger.error(f"Error fetching event: {e}")
        return None
    
    def list_events(self, status: Optional[str] = None, limit: int = 10) -> List[Event]:
        """List events"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute('SELECT * FROM events WHERE status = ? ORDER BY created_date DESC LIMIT ?',
                                 (status, limit))
                else:
                    cursor.execute('SELECT * FROM events ORDER BY created_date DESC LIMIT ?', (limit,))
                return [Event(**dict(row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return []
    
    def update_event_status(self, event_id: int, status: str) -> bool:
        """Update event status"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE events SET status = ? WHERE event_id = ?', (status, event_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating event status: {e}")
            return False
    
    def join_event(self, event_id: int, user_id: int) -> bool:
        """Add user to event"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO event_participants (event_id, user_id, joined_date)
                    VALUES (?, ?, ?)
                ''', (event_id, user_id, datetime.utcnow().isoformat()))
                
                # Update participant count
                cursor.execute('UPDATE events SET participants = participants + 1 WHERE event_id = ?', (event_id,))
                return True
        except sqlite3.IntegrityError:
            logger.info(f"User {user_id} already joined event {event_id}")
            return False
        except Exception as e:
            logger.error(f"Error joining event: {e}")
            return False
    
    def get_event_participants(self, event_id: int) -> List[int]:
        """Get list of participants in an event"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM event_participants WHERE event_id = ?', (event_id,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching event participants: {e}")
            return []


# ============================================================================
# VIP Tier Manager
# ============================================================================

class VIPTierManager:
    """Manages VIP tiers and user progression"""
    
    # VIP tier requirements (in terms of messages sent)
    TIER_THRESHOLDS = {
        VIPTier.SILVER: 50,
        VIPTier.GOLD: 150,
        VIPTier.PLATINUM: 300,
    }
    
    # VIP tier benefits
    TIER_BENEFITS = {
        VIPTier.STANDARD: {"message_limit": 10, "discount_percentage": 0},
        VIPTier.SILVER: {"message_limit": 25, "discount_percentage": 5},
        VIPTier.GOLD: {"message_limit": 50, "discount_percentage": 10},
        VIPTier.PLATINUM: {"message_limit": -1, "discount_percentage": 20},  # Unlimited
    }
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def get_user_tier(self, user_id: int) -> VIPTier:
        """Get user's current VIP tier"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT vip_tier FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if row:
                    return VIPTier(row[0])
        except Exception as e:
            logger.error(f"Error fetching user tier: {e}")
        return VIPTier.STANDARD
    
    def promote_user(self, user_id: int, new_tier: VIPTier) -> bool:
        """Promote user to a new VIP tier"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET vip_tier = ? WHERE user_id = ?', (new_tier.value, user_id))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error promoting user: {e}")
            return False
    
    def check_and_update_tier(self, user_id: int) -> Tuple[bool, VIPTier]:
        """Check if user qualifies for tier upgrade based on messages sent"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT messages_sent, vip_tier FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                
                if not row:
                    return False, VIPTier.STANDARD
                
                messages_sent, current_tier = row[0], VIPTier(row[1])
                
                # Check for tier upgrade
                for tier, threshold in sorted(self.TIER_THRESHOLDS.items(), key=lambda x: x[1]):
                    if messages_sent >= threshold and tier.value > current_tier.value:
                        self.promote_user(user_id, tier)
                        return True, tier
                
                return False, current_tier
        except Exception as e:
            logger.error(f"Error checking tier: {e}")
            return False, VIPTier.STANDARD
    
    def get_tier_benefits(self, tier: VIPTier) -> Dict:
        """Get benefits for a VIP tier"""
        return self.TIER_BENEFITS.get(tier, self.TIER_BENEFITS[VIPTier.STANDARD])
    
    def get_tier_name(self, tier: VIPTier) -> str:
        """Get display name for a tier"""
        names = {
            VIPTier.STANDARD: "Standard",
            VIPTier.SILVER: "Silver",
            VIPTier.GOLD: "Gold",
            VIPTier.PLATINUM: "Platinum",
        }
        return names.get(tier, "Unknown")


# ============================================================================
# Discount Manager
# ============================================================================

class DiscountManager:
    """Manages discount codes and user redemptions"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_discount(self, code: str, discount_type: str, discount_value: float,
                       applicable_vip_tier: int = VIPTier.STANDARD.value,
                       max_uses: int = -1, expiry_date: Optional[str] = None) -> Optional[int]:
        """Create a new discount code"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO discounts (code, discount_type, discount_value, applicable_vip_tier, max_uses, expiry_date, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (code.upper(), discount_type, discount_value, applicable_vip_tier, max_uses, expiry_date, datetime.utcnow().isoformat()))
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Discount code {code} already exists")
            return None
        except Exception as e:
            logger.error(f"Error creating discount: {e}")
            return None
    
    def validate_discount(self, code: str, user_id: int) -> Tuple[bool, str, Optional[float]]:
        """Validate if a discount code is usable by the user"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get discount details
                cursor.execute('SELECT * FROM discounts WHERE code = ?', (code.upper(),))
                discount_row = cursor.fetchone()
                
                if not discount_row:
                    return False, "Discount code not found", None
                
                discount = dict(discount_row)
                
                if not discount['active']:
                    return False, "Discount code is inactive", None
                
                # Check expiry
                if discount['expiry_date']:
                    if datetime.fromisoformat(discount['expiry_date']) < datetime.utcnow():
                        return False, "Discount code has expired", None
                
                # Check max uses
                if discount['max_uses'] != -1 and discount['current_uses'] >= discount['max_uses']:
                    return False, "Discount code has reached maximum uses", None
                
                # Check VIP tier requirement
                cursor.execute('SELECT vip_tier FROM users WHERE user_id = ?', (user_id,))
                user_row = cursor.fetchone()
                if user_row and user_row[0] < discount['applicable_vip_tier']:
                    return False, f"You need at least {VIPTier(discount['applicable_vip_tier']).name} tier", None
                
                return True, "Valid", discount['discount_value']
        except Exception as e:
            logger.error(f"Error validating discount: {e}")
            return False, "Error validating discount", None
    
    def redeem_discount(self, code: str, user_id: int) -> bool:
        """Redeem a discount code for a user"""
        try:
            is_valid, message, _ = self.validate_discount(code, user_id)
            if not is_valid:
                return False
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get discount ID
                cursor.execute('SELECT discount_id FROM discounts WHERE code = ?', (code.upper(),))
                discount_row = cursor.fetchone()
                
                if discount_row:
                    discount_id = discount_row[0]
                    
                    # Record usage
                    cursor.execute('''
                        INSERT INTO discount_usage (discount_id, user_id, used_date)
                        VALUES (?, ?, ?)
                    ''', (discount_id, user_id, datetime.utcnow().isoformat()))
                    
                    # Update usage count
                    cursor.execute('UPDATE discounts SET current_uses = current_uses + 1 WHERE discount_id = ?', (discount_id,))
                    return True
        except Exception as e:
            logger.error(f"Error redeeming discount: {e}")
        return False
    
    def get_discount(self, code: str) -> Optional[Dict]:
        """Get discount details"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM discounts WHERE code = ?', (code.upper(),))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching discount: {e}")
            return None
    
    def list_active_discounts(self, limit: int = 10) -> List[Dict]:
        """List active discount codes"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM discounts WHERE active = 1 
                    ORDER BY created_date DESC LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing discounts: {e}")
            return []


# ============================================================================
# User Manager
# ============================================================================

class UserManager:
    """Manages user profiles and statistics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_user(self, user_id: int, username: str) -> bool:
        """Create new user profile"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (user_id, username, joined_date, last_active)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, username, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                return True
        except sqlite3.IntegrityError:
            logger.info(f"User {user_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if row:
                    return UserProfile(**dict(row))
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
        return None
    
    def update_last_active(self, user_id: int) -> bool:
        """Update user's last active timestamp"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ?',
                             (datetime.utcnow().isoformat(), user_id))
                return True
        except Exception as e:
            logger.error(f"Error updating last active: {e}")
            return False
    
    def increment_messages_sent(self, user_id: int) -> bool:
        """Increment messages sent count"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET messages_sent = messages_sent + 1 WHERE user_id = ?', (user_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error incrementing messages sent: {e}")
            return False
    
    def increment_messages_received(self, user_id: int) -> bool:
        """Increment messages received count"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET messages_received = messages_received + 1 WHERE user_id = ?', (user_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error incrementing messages received: {e}")
            return False


# ============================================================================
# Message Manager
# ============================================================================

class MessageManager:
    """Manages anonymous messages"""
    
    def __init__(self, db_manager: DatabaseManager, user_manager: UserManager, vip_manager: VIPTierManager):
        self.db = db_manager
        self.user_manager = user_manager
        self.vip_manager = vip_manager
    
    def send_message(self, sender_id: int, recipient_id: int, content: str) -> Optional[int]:
        """Send anonymous message"""
        try:
            # Check rate limiting based on VIP tier
            sender = self.user_manager.get_user(sender_id)
            if sender:
                tier = self.vip_manager.get_user_tier(sender_id)
                benefits = self.vip_manager.get_tier_benefits(tier)
                limit = benefits['message_limit']
                
                if limit != -1 and sender.messages_sent >= limit:
                    return None  # Rate limit exceeded
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO messages (sender_id, recipient_id, content, sent_date)
                    VALUES (?, ?, ?, ?)
                ''', (sender_id, recipient_id, content, datetime.utcnow().isoformat()))
                
                message_id = cursor.lastrowid
                
                # Update user statistics
                self.user_manager.increment_messages_sent(sender_id)
                self.user_manager.increment_messages_received(recipient_id)
                
                # Check for VIP tier upgrade
                self.vip_manager.check_and_update_tier(sender_id)
                
                return message_id
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    def get_messages(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get received messages for user"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT message_id, sender_id, content, sent_date, is_read
                    FROM messages
                    WHERE recipient_id = ?
                    ORDER BY sent_date DESC
                    LIMIT ?
                ''', (user_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []
    
    def mark_as_read(self, message_id: int) -> bool:
        """Mark message as read"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE messages SET is_read = 1 WHERE message_id = ?', (message_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False


# ============================================================================
# Bot Commands and Handlers
# ============================================================================

class AnonymousBotManager:
    """Main bot manager class"""
    
    def __init__(self, token: str):
        self.token = token
        self.db = DatabaseManager()
        self.user_manager = UserManager(self.db)
        self.vip_manager = VIPTierManager(self.db)
        self.message_manager = MessageManager(self.db, self.user_manager, self.vip_manager)
        self.event_manager = EventManager(self.db)
        self.discount_manager = DiscountManager(self.db)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start command handler"""
        user = update.effective_user
        
        # Create user if doesn't exist
        self.user_manager.create_user(user.id, user.username or user.first_name)
        self.user_manager.update_last_active(user.id)
        
        welcome_message = (
            f"🎭 Welcome to Anonymous Bot, {user.first_name}!\n\n"
            f"This bot allows you to send and receive anonymous messages.\n\n"
            f"📋 Available Commands:\n"
            f"/send - Send an anonymous message\n"
            f"/messages - View your messages\n"
            f"/profile - View your profile\n"
            f"/vip - Check VIP tier info\n"
            f"/events - View events\n"
            f"/discount - Redeem discount codes\n"
            f"/help - Get help\n"
        )
        
        await update.message.reply_text(welcome_message)
        return ConversationHandler.END
    
    async def send_message_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start message sending flow"""
        user = update.effective_user
        self.user_manager.update_last_active(user.id)
        
        await update.message.reply_text("Enter the user ID of the recipient:")
        return 1  # Expecting recipient ID
    
    async def send_message_recipient(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get recipient ID"""
        try:
            recipient_id = int(update.message.text)
            context.user_data['recipient_id'] = recipient_id
            
            # Check if recipient exists
            recipient = self.user_manager.get_user(recipient_id)
            if not recipient:
                await update.message.reply_text("Recipient not found. Please enter a valid user ID.")
                return 1
            
            await update.message.reply_text("Now send your message (keep it respectful):")
            return 2  # Expecting message content
        except ValueError:
            await update.message.reply_text("Invalid user ID. Please enter a valid number.")
            return 1
    
    async def send_message_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Send the message"""
        sender_id = update.effective_user.id
        recipient_id = context.user_data.get('recipient_id')
        content = update.message.text
        
        # Check for rate limiting
        sender = self.user_manager.get_user(sender_id)
        tier = self.vip_manager.get_user_tier(sender_id)
        benefits = self.vip_manager.get_tier_benefits(tier)
        
        if benefits['message_limit'] != -1 and sender.messages_sent >= benefits['message_limit']:
            await update.message.reply_text(
                f"⛔ You've reached your message limit for today.\n"
                f"Your tier: {self.vip_manager.get_tier_name(tier)}\n"
                f"Upgrade to VIP for more messages!"
            )
            return ConversationHandler.END
        
        message_id = self.message_manager.send_message(sender_id, recipient_id, content)
        
        if message_id:
            await update.message.reply_text(
                f"✅ Message sent successfully!\n"
                f"Message ID: {message_id}"
            )
        else:
            await update.message.reply_text("❌ Failed to send message. Please try again.")
        
        return ConversationHandler.END
    
    async def view_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """View received messages"""
        user_id = update.effective_user.id
        self.user_manager.update_last_active(user_id)
        
        messages = self.message_manager.get_messages(user_id, limit=5)
        
        if not messages:
            await update.message.reply_text("📭 You have no messages yet.")
            return
        
        message_text = "📬 Your Messages:\n\n"
        for msg in messages:
            read_status = "✅ Read" if msg['is_read'] else "🆕 New"
            message_text += f"From: Anonymous (ID: {msg['sender_id']})\n"
            message_text += f"Status: {read_status}\n"
            message_text += f"Message: {msg['content']}\n"
            message_text += f"Time: {msg['sent_date']}\n"
            message_text += "-" * 40 + "\n"
        
        await update.message.reply_text(message_text)
    
    async def view_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """View user profile"""
        user_id = update.effective_user.id
        self.user_manager.update_last_active(user_id)
        
        user = self.user_manager.get_user(user_id)
        tier = self.vip_manager.get_user_tier(user_id)
        
        if not user:
            await update.message.reply_text("Profile not found.")
            return
        
        tier_name = self.vip_manager.get_tier_name(tier)
        benefits = self.vip_manager.get_tier_benefits(tier)
        
        profile_text = (
            f"👤 User Profile\n\n"
            f"Username: {user.username}\n"
            f"User ID: {user_id}\n"
            f"VIP Tier: {tier_name}\n"
            f"Messages Sent: {user.messages_sent}\n"
            f"Messages Received: {user.messages_received}\n"
            f"Joined: {user.joined_date}\n"
            f"Total Spent: ${user.total_spent:.2f}\n\n"
            f"💎 Current Benefits:\n"
            f"Message Limit: {benefits['message_limit'] if benefits['message_limit'] != -1 else 'Unlimited'}\n"
            f"Discount: {benefits['discount_percentage']}%\n"
        )
        
        await update.message.reply_text(profile_text)
    
    async def vip_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show VIP tier information"""
        user_id = update.effective_user.id
        self.user_manager.update_last_active(user_id)
        
        user = self.user_manager.get_user(user_id)
        current_tier = self.vip_manager.get_user_tier(user_id)
        
        vip_text = "💎 VIP Tier System\n\n"
        
        for tier in VIPTier:
            benefits = self.vip_manager.get_tier_benefits(tier)
            tier_name = self.vip_manager.get_tier_name(tier)
            
            if tier == current_tier:
                vip_text += f"✅ {tier_name} (Current)\n"
            else:
                threshold = self.vip_manager.TIER_THRESHOLDS.get(tier, 0)
                vip_text += f"🔒 {tier_name} (Requires {threshold} messages)\n"
            
            vip_text += f"  - Message Limit: {benefits['message_limit'] if benefits['message_limit'] != -1 else 'Unlimited'}\n"
            vip_text += f"  - Discount: {benefits['discount_percentage']}%\n\n"
        
        if user:
            vip_text += f"Your Progress: {user.messages_sent} messages sent"
        
        await update.message.reply_text(vip_text)
    
    async def events_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List active events"""
        user_id = update.effective_user.id
        self.user_manager.update_last_active(user_id)
        
        events = self.event_manager.list_events(status=EventStatus.ACTIVE.value, limit=5)
        
        if not events:
            await update.message.reply_text("📭 No active events at the moment.")
            return
        
        events_text = "📅 Active Events:\n\n"
        for event in events:
            events_text += f"Event ID: {event.event_id}\n"
            events_text += f"Title: {event.title}\n"
            events_text += f"Description: {event.description}\n"
            events_text += f"Participants: {event.participants}\n"
            events_text += "-" * 40 + "\n"
        
        await update.message.reply_text(events_text)
    
    async def redeem_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start discount redemption"""
        user_id = update.effective_user.id
        self.user_manager.update_last_active(user_id)
        
        await update.message.reply_text("Enter your discount code:")
        return 1
    
    async def process_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process discount code"""
        user_id = update.effective_user.id
        code = update.message.text.strip()
        
        is_valid, message, discount_value = self.discount_manager.validate_discount(code, user_id)
        
        if is_valid:
            # Redeem the discount
            self.discount_manager.redeem_discount(code, user_id)
            await update.message.reply_text(
                f"✅ Discount redeemed successfully!\n"
                f"Discount Value: {discount_value}\n"
                f"Thank you for your purchase!"
            )
        else:
            await update.message.reply_text(f"❌ {message}")
        
        return ConversationHandler.END
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show help information"""
        user_id = update.effective_user.id
        self.user_manager.update_last_active(user_id)
        
        help_text = (
            "ℹ️ Bot Help\n\n"
            "🔹 /start - Initialize the bot\n"
            "🔹 /send - Send an anonymous message\n"
            "🔹 /messages - View your received messages\n"
            "🔹 /profile - View your profile\n"
            "🔹 /vip - Check VIP tier information\n"
            "🔹 /events - View active events\n"
            "🔹 /discount - Redeem a discount code\n"
            "🔹 /help - Show this help message\n\n"
            "📌 Features:\n"
            "• Send anonymous messages\n"
            "• Track message statistics\n"
            "• VIP tier system with benefits\n"
            "• Event management\n"
            "• Discount code system\n"
            "• Automatic tier promotion\n"
        )
        
        await update.message.reply_text(help_text)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    def run(self):
        """Start the bot"""
        app = Application.builder().token(self.token).build()
        
        # Command handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("profile", self.view_profile))
        app.add_handler(CommandHandler("vip", self.vip_info))
        app.add_handler(CommandHandler("messages", self.view_messages))
        app.add_handler(CommandHandler("events", self.events_list))
        app.add_handler(CommandHandler("help", self.help_command))
        
        # Conversation handlers
        send_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("send", self.send_message_start)],
            states={
                1: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.send_message_recipient)],
                2: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.send_message_content)],
            },
            fallbacks=[CommandHandler("help", self.help_command)],
        )
        
        discount_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("discount", self.redeem_discount)],
            states={
                1: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_discount)],
            },
            fallbacks=[CommandHandler("help", self.help_command)],
        )
        
        app.add_handler(send_conv_handler)
        app.add_handler(discount_conv_handler)
        
        # Error handler
        app.add_error_handler(self.error_handler)
        
        logger.info("Bot started successfully")
        app.run_polling()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    # Get bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        return
    
    bot = AnonymousBotManager(token)
    bot.run()


if __name__ == '__main__':
    main()
