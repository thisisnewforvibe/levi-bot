"""
Main entry point for the Telegram Voice Reminder Bot.
Supports multiple languages including Russian and Uzbek.
"""

import logging
import sys
import asyncio
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from database import init_database
from scheduler import setup_scheduler, recover_pending_reminders
from handlers import (
    start_command,
    help_command,
    list_reminders_command,
    done_command,
    delete_command,
    timezone_command,
    timezone_input_handler,
    voice_message_handler,
    time_input_handler,
    yes_no_handler,
    yes_no_callback_handler,
    snooze_handler,
    cancel_command,
    unknown_message_handler,
    error_handler,
    admin_command,
    admin_users_command,
    admin_reminders_command,
    admin_user_command,
    # New menu handlers
    setup_bot_menu,
    menu_command,
    reminders_command,
    recurring_command,
    settings_command,
    menu_callback_handler,
    delete_callback_handler,
    WAITING_FOR_TIME,
    WAITING_FOR_CONFIRMATION,
    WAITING_FOR_SNOOZE,
    WAITING_FOR_TIMEZONE,
    WAITING_FOR_TASK_CONFIRMATION,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8'),
    ]
)

# Reduce noise from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    logger.info("Starting Voice Reminder Bot...")
    
    # Initialize the database
    init_database()
    logger.info("Database initialized")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Set up the scheduler for checking reminders
    setup_scheduler(application)
    
    # Conversation handler for voice message flow
    voice_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.VOICE, voice_message_handler),
        ],
        states={
            WAITING_FOR_TIME: [
                CommandHandler("cancel", cancel_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, time_input_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
        ],
        allow_reentry=True,
    )
    
    # Conversation handler for timezone setting
    timezone_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("timezone", timezone_command),
        ],
        states={
            WAITING_FOR_TIMEZONE: [
                CommandHandler("cancel", cancel_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, timezone_input_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
        ],
        allow_reentry=True,
    )
    
    # Conversation handler for YES/NO follow-up
    # Support Uzbek and Russian responses
    yes_no_pattern = r'^(ha|xa|ха|bajarildi|tayyor|tugadi|yo\'?q|yoq|yoʻq|hali|keyinroq|да|нет|д|н|готово|выполнено|ещё нет|позже|отложить|✅)$'
    followup_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(yes_no_pattern) & ~filters.COMMAND,
                yes_no_handler
            ),
        ],
        states={
            WAITING_FOR_SNOOZE: [
                CommandHandler("cancel", cancel_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, snooze_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
        ],
        allow_reentry=True,
    )
    
    # Add callback query handler for inline buttons (YES/NO)
    application.add_handler(CallbackQueryHandler(yes_no_callback_handler, pattern="^reminder_(yes|no)$"))
    
    # Add callback handlers for menu
    application.add_handler(CallbackQueryHandler(menu_callback_handler, pattern="^menu_"))
    application.add_handler(CallbackQueryHandler(delete_callback_handler, pattern="^(del_|stop_|confirm_del_)"))
    application.add_handler(CallbackQueryHandler(menu_callback_handler, pattern="^settings_"))
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_reminders_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    
    # New menu commands
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("reminders", reminders_command))
    application.add_handler(CommandHandler("recurring", recurring_command))
    application.add_handler(CommandHandler("settings", settings_command))
    
    # Admin commands
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("users", admin_users_command))
    application.add_handler(CommandHandler("reminders", admin_reminders_command))
    application.add_handler(CommandHandler("user", admin_user_command))
    
    # Add conversation handlers
    application.add_handler(voice_conv_handler)
    application.add_handler(timezone_conv_handler)
    application.add_handler(followup_conv_handler)
    
    # Add fallback handler for unknown messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Run startup recovery for missed reminders and set up menu
    async def post_init(app: Application) -> None:
        await setup_bot_menu(app)
        await recover_pending_reminders(app)
    
    application.post_init = post_init
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
