"""
Scheduler module for handling reminder jobs.
Uses python-telegram-bot's built-in JobQueue for scheduling.
Includes startup recovery for bot restarts.
"""

import logging
from datetime import datetime, timedelta
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import (
    get_pending_reminders,
    get_follow_up_reminders,
    mark_initial_reminder_sent,
    mark_follow_up_sent,
    update_reminder_status,
    get_all_pending_reminders,
)
from config import FOLLOW_UP_DELAY_SECONDS
from time_parser import format_datetime

logger = logging.getLogger(__name__)


async def check_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Check for pending reminders that are due and send them.
    This function is called periodically by the job queue.
    """
    now = datetime.utcnow()
    
    try:
        # Get all pending reminders that are due
        pending_reminders = await get_pending_reminders(now)
        
        for reminder in pending_reminders:
            if reminder['initial_reminder_sent'] == 0:
                # This reminder hasn't been sent yet - send initial reminder
                await send_reminder(context, reminder)
        
        # Check for follow-ups (reminders sent more than 30 minutes ago)
        follow_up_threshold = now - timedelta(seconds=FOLLOW_UP_DELAY_SECONDS)
        follow_up_reminders = await get_follow_up_reminders(follow_up_threshold)
        
        for reminder in follow_up_reminders:
            await send_follow_up(context, reminder)
    
    except Exception as e:
        logger.error(f"Error checking reminders: {e}")


async def send_reminder(context: ContextTypes.DEFAULT_TYPE, reminder: dict) -> None:
    """
    Send a reminder message to the user.
    
    Args:
        context: The context from the job.
        reminder: The reminder dictionary from database.
    """
    try:
        user_tz = reminder.get('user_timezone', 'Asia/Tashkent')
        scheduled_time = datetime.fromisoformat(reminder['scheduled_time_utc'])
        formatted_time = format_datetime(scheduled_time, user_tz)
        
        message = (
            f"🔔 **Eslatma!** / **Напоминание!**\n\n"
            f"📝 {reminder['task_text']}\n\n"
            f"⏰ _{formatted_time}_"
        )
        
        await context.bot.send_message(
            chat_id=reminder['chat_id'],
            text=message,
            parse_mode='Markdown'
        )
        
        # Mark that initial reminder has been sent (NOT follow-up)
        # This allows the follow-up to be sent 30 minutes later
        await mark_initial_reminder_sent(reminder['id'])
        
        logger.info(f"Sent reminder {reminder['id']} to user {reminder['user_id']}")
        
    except Exception as e:
        logger.error(f"Failed to send reminder {reminder['id']}: {e}")


async def send_follow_up(context: ContextTypes.DEFAULT_TYPE, reminder: dict) -> None:
    """
    Send a follow-up message asking if the task is done.
    
    Args:
        context: The context from the job.
        reminder: The reminder dictionary from database.
    """
    try:
        message = (
            f"⏰ **Vazifa bajarildimi?**\n"
            f"**Задача выполнена?**\n\n"
            f"📝 {reminder['task_text']}"
        )
        
        # Create inline keyboard with YES/NO buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ HA / ДА", callback_data="reminder_yes"),
                InlineKeyboardButton("❌ YO'Q / НЕТ", callback_data="reminder_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=reminder['chat_id'],
            text=message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Mark that follow-up has been sent
        await mark_follow_up_sent(reminder['id'])
        
        logger.info(f"Sent follow-up for reminder {reminder['id']} to user {reminder['user_id']}")
        
    except Exception as e:
        logger.error(f"Failed to send follow-up for reminder {reminder['id']}: {e}")


def setup_scheduler(application) -> None:
    """
    Set up the periodic job to check for reminders.
    
    Args:
        application: The Telegram Application instance.
    """
    job_queue = application.job_queue
    
    # Check for reminders every 30 seconds
    job_queue.run_repeating(
        check_reminders,
        interval=30,
        first=10,  # Start 10 seconds after bot startup
        name="reminder_checker"
    )
    
    logger.info("Scheduler set up successfully - checking reminders every 30 seconds")


async def recover_pending_reminders(application) -> None:
    """
    Recover pending reminders after bot restart.
    Checks for any reminders that should have been sent while bot was down.
    
    Args:
        application: The Telegram Application instance.
    """
    try:
        logger.info("Checking for missed reminders after restart...")
        
        now = datetime.utcnow()
        pending = await get_all_pending_reminders()
        
        missed_count = 0
        upcoming_count = 0
        
        for reminder in pending:
            scheduled = datetime.fromisoformat(reminder['scheduled_time_utc'])
            
            if scheduled <= now:
                # This reminder was missed while bot was down
                overdue_seconds = (now - scheduled).total_seconds()
                max_delay_seconds = 2 * 3600  # 2 hours grace period
                
                if overdue_seconds > max_delay_seconds:
                    # Too old, skip this reminder
                    missed_count += 1
                    try:
                        await update_reminder_status(reminder['id'], 'completed')
                        logger.info(f"Skipped reminder {reminder['id']} - deadline passed by {overdue_seconds/3600:.1f} hours")
                    except Exception as e:
                        logger.error(f"Failed to mark reminder {reminder['id']} as completed: {e}")
                else:
                    # Still relevant, send delayed notification
                    missed_count += 1
                    
                    # Calculate how overdue it is (Uzbek/Russian)
                    overdue = now - scheduled
                    if overdue.seconds >= 3600:
                        hours = overdue.seconds // 3600
                        overdue_uz = f"{hours} soat oldin"
                        overdue_ru = f"{hours} ч. назад"
                    else:
                        minutes = overdue.seconds // 60
                        overdue_uz = f"{minutes} minut oldin"
                        overdue_ru = f"{minutes} мин. назад"
                    
                    # Send delayed notification
                    try:
                        message = (
                            f"🔔 **Kechikkan eslatma** / **Отложенное напоминание**\n\n"
                            f"📝 {reminder['task_text']}\n\n"
                            f"⚠️ _Bu {overdue_uz} rejalashtirilgan edi._\n"
                            f"_Это было запланировано {overdue_ru}._"
                        )
                        
                        await application.bot.send_message(
                            chat_id=reminder['chat_id'],
                            text=message,
                            parse_mode='Markdown'
                        )
                        
                        logger.info(f"Sent delayed reminder {reminder['id']} to user {reminder['user_id']}")
                        
                    except Exception as e:
                        logger.error(f"Failed to send delayed reminder {reminder['id']}: {e}")
            else:
                upcoming_count += 1
        
        logger.info(
            f"Startup recovery complete: "
            f"{missed_count} missed reminders sent, "
            f"{upcoming_count} upcoming reminders scheduled"
        )
        
    except Exception as e:
        logger.error(f"Error during startup recovery: {e}")
