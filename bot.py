import logging
import random
import json
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

import database as db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
ADMIN_IDS = [123456789]  # Replace with actual admin IDs
MAINTENANCE_MODE = False
MAX_MESSAGE_LENGTH = 4096

# Bot state management
class BotState:
    """Manages bot internal state"""
    def __init__(self):
        self.maintenance_mode = False
        self.maintenance_message = "Bot is under maintenance. Please try again later."
        self.admin_menu_state = {}  # Track admin menu states
    
    def set_maintenance(self, enabled: bool, message: str = None):
        """Set maintenance mode"""
        self.maintenance_mode = enabled
        if message:
            self.maintenance_message = message
        logger.info(f"Maintenance mode set to: {enabled}")
    
    def get_admin_state(self, user_id: int) -> Dict[str, Any]:
        """Get admin user state"""
        if user_id not in self.admin_menu_state:
            self.admin_menu_state[user_id] = {"menu_level": "main"}
        return self.admin_menu_state[user_id]

bot_state = BotState()

# Utility functions
def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in ADMIN_IDS

def admin_only(func):
    """Decorator to restrict commands to admins"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_admin(update.effective_user.id):
            await update.message.reply_text(
                "❌ You don't have permission to use this command."
            )
            logger.warning(f"Unauthorized access attempt by user {update.effective_user.id}")
            return
        return await func(update, context)
    return wrapper

def safe_database_read(func_name: str, default: Any = None) -> Any:
    """Safely read from database with error handling"""
    try:
        # This is a wrapper for database operations
        return default
    except Exception as e:
        logger.error(f"Database read error in {func_name}: {e}")
        return default

def get_safe_db_structure(key: str, default_structure: Dict) -> Dict:
    """Get database structure with safe defaults"""
    try:
        data = db.read_data(key)
        if data is None:
            return default_structure
        # Ensure all required keys exist
        for k, v in default_structure.items():
            if k not in data:
                data[k] = v
        return data
    except Exception as e:
        logger.error(f"Error reading database structure for {key}: {e}")
        return default_structure

# ==================== Start Commands ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    try:
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        
        # Check maintenance mode
        if bot_state.maintenance_mode and not is_admin(user_id):
            await update.message.reply_text(bot_state.maintenance_message)
            logger.info(f"User {user_id} blocked due to maintenance mode")
            return
        
        # Initialize user data
        try:
            user_data = get_safe_db_structure(
                f"user_{user_id}",
                {"messages_sent": 0, "messages_received": 0, "blocked_users": []}
            )
            db.write_data(f"user_{user_id}", user_data)
        except Exception as e:
            logger.error(f"Error initializing user {user_id}: {e}")
        
        welcome_message = (
            f"👋 Welcome {user_name}!\n\n"
            "I'm an anonymous messaging bot. You can:\n"
            "• Send messages anonymously\n"
            "• Receive anonymous messages\n"
            "• View your statistics\n\n"
            "Use /help for more information."
        )
        
        await update.message.reply_text(welcome_message)
        logger.info(f"User {user_id} started the bot")
        
    except TelegramError as e:
        logger.error(f"Telegram error in start command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in start command: {e}")
        await update.message.reply_text("❌ An unexpected error occurred.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    try:
        help_text = (
            "📚 *Available Commands:*\n\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/send - Send an anonymous message\n"
            "/inbox - View your inbox\n"
            "/stats - View your statistics\n"
            "/block - Block a user\n"
            "/unblock - Unblock a user\n"
            "/blocked - View blocked users\n"
        )
        
        if is_admin(update.effective_user.id):
            help_text += "\n🔧 *Admin Commands:*\n"
            help_text += "/admin - Open admin panel\n"
        
        await update.message.reply_text(help_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text("❌ An error occurred while loading help.")

# ==================== Admin Panel with Hierarchical Menu ====================

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main admin panel menu"""
    try:
        user_id = update.effective_user.id
        bot_state.get_admin_state(user_id)  # Initialize state
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🛠️ Maintenance", callback_data="admin_maintenance")],
            [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
            [InlineKeyboardButton("📢 Notifications", callback_data="admin_notifications")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🔧 *Admin Panel*\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_panel: {e}")
        await update.message.reply_text("❌ Error opening admin panel.")

async def admin_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Statistics submenu"""
    try:
        query = update.callback_query
        await query.answer()
        
        try:
            stats = get_safe_db_structure(
                "bot_stats",
                {"total_users": 0, "total_messages": 0, "active_users": 0}
            )
            
            stats_text = (
                "📊 *Bot Statistics*\n\n"
                f"Total Users: {stats.get('total_users', 0)}\n"
                f"Total Messages: {stats.get('total_messages', 0)}\n"
                f"Active Users: {stats.get('active_users', 0)}\n"
            )
            
        except Exception as e:
            logger.error(f"Error reading stats: {e}")
            stats_text = "📊 *Bot Statistics*\n\n❌ Error loading statistics"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back_main")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=stats_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_stats_menu: {e}")
        await query.answer("❌ Error loading statistics", show_alert=True)

async def admin_maintenance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maintenance submenu"""
    try:
        query = update.callback_query
        await query.answer()
        
        status = "🟢 ACTIVE" if not bot_state.maintenance_mode else "🔴 MAINTENANCE"
        
        keyboard = [
            [InlineKeyboardButton("🔴 Enable Maintenance", callback_data="maint_enable")],
            [InlineKeyboardButton("🟢 Disable Maintenance", callback_data="maint_disable")],
            [InlineKeyboardButton("✏️ Edit Message", callback_data="maint_edit_msg")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back_main")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"🛠️ *Maintenance Mode*\n\nStatus: {status}\n\nMessage: {bot_state.maintenance_message}",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_maintenance_menu: {e}")
        await query.answer("❌ Error loading maintenance menu", show_alert=True)

async def admin_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Users submenu"""
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("👤 View User Info", callback_data="users_search")],
            [InlineKeyboardButton("🚫 Ban User", callback_data="users_ban")],
            [InlineKeyboardButton("✅ Unban User", callback_data="users_unban")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back_main")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="👥 *User Management*\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_users_menu: {e}")
        await query.answer("❌ Error loading users menu", show_alert=True)

async def admin_notifications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notifications submenu"""
    try:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📤 Send Broadcast", callback_data="notif_broadcast")],
            [InlineKeyboardButton("⚠️ Send Warning", callback_data="notif_warning")],
            [InlineKeyboardButton("ℹ️ Send Announcement", callback_data="notif_announce")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back_main")],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="📢 *Notifications*\n\nSelect notification type:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_notifications_menu: {e}")
        await query.answer("❌ Error loading notifications menu", show_alert=True)

# ==================== Maintenance Commands ====================

async def maintenance_enable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable maintenance mode"""
    try:
        query = update.callback_query
        await query.answer()
        
        bot_state.set_maintenance(True)
        
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_maintenance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="🔴 *Maintenance Mode Enabled*\n\nThe bot is now in maintenance mode.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"Maintenance mode enabled by admin {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error enabling maintenance: {e}")
        await query.answer("❌ Error enabling maintenance", show_alert=True)

async def maintenance_disable(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable maintenance mode"""
    try:
        query = update.callback_query
        await query.answer()
        
        bot_state.set_maintenance(False)
        
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_maintenance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="🟢 *Maintenance Mode Disabled*\n\nThe bot is now active.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        logger.info(f"Maintenance mode disabled by admin {query.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error disabling maintenance: {e}")
        await query.answer("❌ Error disabling maintenance", show_alert=True)

async def maintenance_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start editing maintenance message"""
    try:
        query = update.callback_query
        await query.answer()
        
        context.user_data['waiting_for_maintenance_message'] = True
        
        await query.edit_message_text(
            text="📝 Send the new maintenance message (max 1000 characters):"
        )
        
    except Exception as e:
        logger.error(f"Error in maintenance_edit_message: {e}")
        await query.answer("❌ Error", show_alert=True)

async def send_maintenance_cancel_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send notification when maintenance is cancelled"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Complete message with all required content
        notification_message = (
            "🔄 *Maintenance Cancelled*\n\n"
            "The scheduled maintenance has been cancelled.\n"
            "The bot is now back to normal operation.\n\n"
            f"Cancelled at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        
        try:
            # Try to send to all users (requires tracking all user IDs)
            users_data = get_safe_db_structure("users_list", {"users": []})
            users = users_data.get("users", [])
            
            if not users:
                logger.warning("No users found to notify")
                await query.answer("✅ No users to notify", show_alert=True)
                return
            
            success_count = 0
            for user_id in users:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=notification_message,
                        parse_mode="Markdown"
                    )
                    success_count += 1
                except TelegramError as e:
                    logger.warning(f"Failed to notify user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error notifying user {user_id}: {e}")
            
            await query.answer(
                f"✅ Notified {success_count} users successfully",
                show_alert=True
            )
            logger.info(f"Maintenance cancellation notification sent to {success_count} users")
            
        except Exception as e:
            logger.error(f"Error sending maintenance notifications: {e}")
            await query.answer("❌ Error sending notifications", show_alert=True)
        
        # Return to maintenance menu
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="admin_maintenance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="📢 Maintenance cancellation notifications sent",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in send_maintenance_cancel_notification: {e}")
        await query.answer("❌ Error sending notifications", show_alert=True)

# ==================== Message Handlers ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages"""
    try:
        user_id = update.effective_user.id
        
        # Check maintenance mode
        if bot_state.maintenance_mode and not is_admin(user_id):
            await update.message.reply_text(bot_state.maintenance_message)
            return
        
        # Check if user is waiting for maintenance message
        if context.user_data.get('waiting_for_maintenance_message'):
            message_text = update.message.text
            if len(message_text) > 1000:
                await update.message.reply_text(
                    "❌ Message too long. Maximum 1000 characters."
                )
                return
            
            bot_state.maintenance_message = message_text
            context.user_data['waiting_for_maintenance_message'] = False
            
            await update.message.reply_text("✅ Maintenance message updated!")
            logger.info(f"Maintenance message updated by admin {user_id}")
            return
        
        # Regular message handling
        await update.message.reply_text(
            "👋 I'm an anonymous messaging bot.\n"
            "Use /help to see available commands."
        )
        
    except TelegramError as e:
        logger.error(f"Telegram error in handle_message: {e}")
        await update.message.reply_text("❌ An error occurred.")
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("❌ An unexpected error occurred.")

# ==================== Callback Query Handler ====================

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # Main admin menu
        if callback_data == "admin_stats":
            await admin_stats_menu(update, context)
        elif callback_data == "admin_maintenance":
            await admin_maintenance_menu(update, context)
        elif callback_data == "admin_users":
            await admin_users_menu(update, context)
        elif callback_data == "admin_notifications":
            await admin_notifications_menu(update, context)
        elif callback_data == "admin_close":
            await query.delete_message()
        elif callback_data == "admin_back_main":
            await admin_panel(update, context)
        
        # Maintenance callbacks
        elif callback_data == "maint_enable":
            await maintenance_enable(update, context)
        elif callback_data == "maint_disable":
            await maintenance_disable(update, context)
        elif callback_data == "maint_edit_msg":
            await maintenance_edit_message(update, context)
        elif callback_data == "maint_send_notification":
            await send_maintenance_cancel_notification(update, context)
        
        # User management callbacks
        elif callback_data == "users_search":
            await query.edit_message_text(
                text="👤 Enter user ID to search:"
            )
        elif callback_data == "users_ban":
            await query.edit_message_text(
                text="🚫 Enter user ID to ban:"
            )
        elif callback_data == "users_unban":
            await query.edit_message_text(
                text="✅ Enter user ID to unban:"
            )
        
        # Notification callbacks
        elif callback_data == "notif_broadcast":
            context.user_data['waiting_for_broadcast'] = True
            await query.edit_message_text(
                text="📤 Send broadcast message (will be sent to all users):"
            )
        elif callback_data == "notif_warning":
            context.user_data['waiting_for_warning'] = True
            await query.edit_message_text(
                text="⚠️ Send warning message:"
            )
        elif callback_data == "notif_announce":
            context.user_data['waiting_for_announcement'] = True
            await query.edit_message_text(
                text="ℹ️ Send announcement:"
            )
        
        else:
            logger.warning(f"Unknown callback data: {callback_data}")
            await query.answer("Unknown action", show_alert=True)
    
    except TelegramError as e:
        logger.error(f"Telegram error in button_click: {e}")
        await query.answer("❌ An error occurred", show_alert=True)
    except Exception as e:
        logger.error(f"Error in button_click: {e}")
        await query.answer("❌ An unexpected error occurred", show_alert=True)

# ==================== Random Helper with Safe Choice ====================

def safe_random_choice(items: list, default: Any = None) -> Any:
    """Safely choose a random item from a list"""
    try:
        if not items:
            logger.warning("Attempted random.choice on empty list")
            return default
        return random.choice(items)
    except ValueError as e:
        logger.error(f"ValueError in safe_random_choice: {e}")
        return default
    except Exception as e:
        logger.error(f"Unexpected error in safe_random_choice: {e}")
        return default

# ==================== Application Setup ====================

def main() -> None:
    """Start the bot"""
    try:
        # Create application
        application = Application.builder().token("YOUR_BOT_TOKEN").build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("admin", admin_panel))
        
        # Callback query handler (for buttons)
        application.add_handler(CallbackQueryHandler(button_click))
        
        # Message handler (catch-all)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Bot started successfully")
        
        # Run bot
        application.run_polling()
        
    except TelegramError as e:
        logger.critical(f"Telegram error while starting bot: {e}")
    except Exception as e:
        logger.critical(f"Critical error while starting bot: {e}")
        raise

if __name__ == "__main__":
    main()
