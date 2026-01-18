"""
Database module for SQLite operations.
Handles all reminder storage and retrieval operations.
"""

import sqlite3
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from config import DATABASE_PATH


def init_database() -> None:
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # User preferences table for timezone and language
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id INTEGER PRIMARY KEY,
            timezone TEXT DEFAULT 'UTC',
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            notes TEXT,
            location TEXT,
            scheduled_time_utc TIMESTAMP NOT NULL,
            user_timezone TEXT DEFAULT 'UTC',
            status TEXT DEFAULT 'pending',
            initial_reminder_sent INTEGER DEFAULT 0,
            follow_up_sent INTEGER DEFAULT 0,
            recurrence_type TEXT DEFAULT NULL,
            recurrence_time TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Migration: Add notes and location columns if they don't exist
    try:
        cursor.execute("ALTER TABLE reminders ADD COLUMN notes TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE reminders ADD COLUMN location TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Migration: Add recurrence columns if they don't exist
    try:
        cursor.execute("ALTER TABLE reminders ADD COLUMN recurrence_type TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE reminders ADD COLUMN recurrence_time TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Rate limiting table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            user_id INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL
        )
    """)
    
    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_status_time 
        ON reminders(status, scheduled_time_utc)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_reminders_user 
        ON reminders(user_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rate_limits_user_time
        ON rate_limits(user_id, timestamp)
    """)
    
    conn.commit()
    conn.close()


async def add_reminder(
    user_id: int,
    chat_id: int,
    task_text: str,
    scheduled_time: datetime,
    user_timezone: str = 'UTC',
    notes: str = None,
    location: str = None,
    recurrence_type: str = None,
    recurrence_time: str = None
) -> int:
    """
    Add a new reminder to the database.
    Times are stored in UTC.
    
    Args:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        task_text: Main task description
        scheduled_time: When to remind (UTC)
        user_timezone: User's timezone
        notes: Additional details/items (e.g., shopping list)
        location: Where the task should be done
        recurrence_type: 'daily', 'weekly', 'weekdays', 'monthly', or None
        recurrence_time: Time in HH:MM format for recurring reminders
    
    Returns:
        The ID of the newly created reminder.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO reminders (user_id, chat_id, task_text, notes, location, scheduled_time_utc, user_timezone, recurrence_type, recurrence_time, initial_reminder_sent, follow_up_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """,
            (user_id, chat_id, task_text, notes, location, scheduled_time.isoformat(), user_timezone, recurrence_type, recurrence_time)
        )
        await db.commit()
        return cursor.lastrowid


async def get_pending_reminders(before_time: datetime) -> List[Tuple]:
    """
    Get all pending reminders scheduled before the given time (UTC).
    
    Returns:
        List of tuples containing reminder data.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, chat_id, task_text, notes, location, scheduled_time_utc, 
                   user_timezone, initial_reminder_sent, follow_up_sent, recurrence_type, recurrence_time
            FROM reminders
            WHERE status = 'pending' AND scheduled_time_utc <= ?
            ORDER BY scheduled_time_utc ASC
            """,
            (before_time.isoformat(),)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_follow_up_reminders(follow_up_after: datetime) -> List[dict]:
    """
    Get reminders that need a follow-up (30 minutes after initial reminder).
    Only for non-recurring reminders (recurring ones don't need follow-up).
    
    Returns:
        List of reminder dictionaries needing follow-up.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, chat_id, task_text, notes, location, scheduled_time_utc, user_timezone, recurrence_type
            FROM reminders
            WHERE status = 'pending' 
            AND initial_reminder_sent = 1
            AND follow_up_sent = 0
            AND recurrence_type IS NULL
            AND scheduled_time_utc <= ?
            ORDER BY scheduled_time_utc ASC
            """,
            (follow_up_after.isoformat(),)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def mark_initial_reminder_sent(reminder_id: int) -> None:
    """Mark that the initial reminder has been sent."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE reminders 
            SET initial_reminder_sent = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reminder_id,)
        )
        await db.commit()


async def mark_follow_up_sent(reminder_id: int) -> None:
    """Mark that a follow-up has been sent for a reminder."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE reminders 
            SET follow_up_sent = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reminder_id,)
        )
        await db.commit()


async def reschedule_reminder_for_followup(reminder_id: int, new_scheduled_time: datetime) -> None:
    """
    Reschedule a reminder and reset follow-up flags so it gets asked again.
    Used when user says NO to follow-up - automatically remind in 30 minutes.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE reminders 
            SET scheduled_time_utc = ?,
                initial_reminder_sent = 0,
                follow_up_sent = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_scheduled_time.isoformat(), reminder_id)
        )
        await db.commit()


async def update_reminder_status(reminder_id: int, status: str) -> None:
    """
    Update the status of a reminder.
    
    Args:
        reminder_id: The ID of the reminder to update.
        status: New status ('pending', 'done', 'snoozed').
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE reminders 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, reminder_id)
        )
        await db.commit()


async def reschedule_reminder(reminder_id: int, new_time: datetime) -> None:
    """
    Reschedule a reminder to a new time (UTC).
    
    Args:
        reminder_id: The ID of the reminder to reschedule.
        new_time: The new scheduled time in UTC.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """
            UPDATE reminders 
            SET scheduled_time_utc = ?, 
                status = 'pending', 
                follow_up_sent = 0,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_time.isoformat(), reminder_id)
        )
        await db.commit()


async def get_user_reminders(user_id: int, status: Optional[str] = None) -> List[dict]:
    """
    Get all reminders for a specific user.
    
    Args:
        user_id: The Telegram user ID.
        status: Optional status filter.
    
    Returns:
        List of reminder dictionaries.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        if status:
            cursor = await db.execute(
                """
                SELECT id, task_text, notes, location, scheduled_time_utc, user_timezone, status, recurrence_type, recurrence_time, created_at
                FROM reminders
                WHERE user_id = ? AND status = ?
                ORDER BY scheduled_time_utc ASC
                """,
                (user_id, status)
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, task_text, notes, location, scheduled_time_utc, user_timezone, status, recurrence_type, recurrence_time, created_at
                FROM reminders
                WHERE user_id = ?
                ORDER BY scheduled_time_utc ASC
                """,
                (user_id,)
            )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_reminder_by_id(reminder_id: int) -> Optional[dict]:
    """
    Get a specific reminder by ID.
    
    Returns:
        Reminder dictionary or None if not found.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, chat_id, task_text, scheduled_time_utc, 
                   user_timezone, status, follow_up_sent
            FROM reminders
            WHERE id = ?
            """,
            (reminder_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def delete_reminder(reminder_id: int) -> bool:
    """
    Delete a reminder by ID.
    
    Returns:
        True if a reminder was deleted, False otherwise.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM reminders WHERE id = ?",
            (reminder_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_latest_pending_reminder(user_id: int) -> Optional[dict]:
    """
    Get the most recently created pending reminder for a user.
    Useful for handling follow-up responses.
    
    Returns:
        Reminder dictionary or None if not found.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, chat_id, task_text, scheduled_time_utc, 
                   user_timezone, status, follow_up_sent
            FROM reminders
            WHERE user_id = ? AND status = 'pending' AND follow_up_sent = 1
            ORDER BY scheduled_time_utc DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


# ============ User Preferences Functions ============

async def get_user_preferences(user_id: int) -> Optional[dict]:
    """Get user preferences (timezone, language)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_user_preferences(
    user_id: int,
    timezone: Optional[str] = None,
    language: Optional[str] = None
) -> None:
    """Set or update user preferences."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        existing = await get_user_preferences(user_id)
        
        if existing:
            updates = []
            values = []
            if timezone:
                updates.append("timezone = ?")
                values.append(timezone)
            if language:
                updates.append("language = ?")
                values.append(language)
            
            if updates:
                updates.append("updated_at = CURRENT_TIMESTAMP")
                values.append(user_id)
                await db.execute(
                    f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = ?",
                    values
                )
        else:
            await db.execute(
                "INSERT INTO user_preferences (user_id, timezone, language) VALUES (?, ?, ?)",
                (user_id, timezone or 'UTC', language or 'en')
            )
        
        await db.commit()


# ============ Rate Limiting Functions ============

async def check_rate_limit(user_id: int, limit: int, window_seconds: int) -> bool:
    """
    Check if user is within rate limits.
    
    Returns:
        True if within limits, False if rate limited.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        
        # Clean old entries
        await db.execute(
            "DELETE FROM rate_limits WHERE timestamp < ?",
            (cutoff.isoformat(),)
        )
        
        # Count recent requests
        cursor = await db.execute(
            "SELECT COUNT(*) FROM rate_limits WHERE user_id = ? AND timestamp >= ?",
            (user_id, cutoff.isoformat())
        )
        row = await cursor.fetchone()
        count = row[0] if row else 0
        
        if count >= limit:
            return False
        
        # Record this request
        await db.execute(
            "INSERT INTO rate_limits (user_id, timestamp) VALUES (?, ?)",
            (user_id, datetime.utcnow().isoformat())
        )
        await db.commit()
        return True


# ============ Startup Recovery ============

async def get_all_pending_reminders() -> List[dict]:
    """
    Get ALL pending reminders for restart recovery.
    
    Returns:
        List of all pending reminder dictionaries.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, user_id, chat_id, task_text, notes, location, scheduled_time_utc, 
                   user_timezone, follow_up_sent, status, recurrence_type, recurrence_time
            FROM reminders
            WHERE status = 'pending'
            ORDER BY scheduled_time_utc ASC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def schedule_next_recurrence(reminder: dict) -> Optional[int]:
    """
    Schedule the next occurrence of a recurring reminder.
    
    Args:
        reminder: The reminder dict with recurrence info
        
    Returns:
        The new reminder ID, or None if not recurring
    """
    from dateutil import tz as tz_module
    
    recurrence_type = reminder.get('recurrence_type')
    if not recurrence_type:
        return None
    
    recurrence_time = reminder.get('recurrence_time', '09:00')
    user_tz = reminder.get('user_timezone', 'Asia/Tashkent')
    
    # Parse the recurrence time
    try:
        hour, minute = map(int, recurrence_time.split(':'))
    except:
        hour, minute = 9, 0
    
    # Get current time in user's timezone
    user_timezone = tz_module.gettz(user_tz)
    now_local = datetime.now(user_timezone)
    
    # Calculate next occurrence based on recurrence type
    if recurrence_type == 'daily':
        # Tomorrow at the same time
        next_date = now_local + timedelta(days=1)
    elif recurrence_type == 'weekdays':
        # Next weekday (Mon-Fri)
        next_date = now_local + timedelta(days=1)
        while next_date.weekday() >= 5:  # Skip Saturday (5) and Sunday (6)
            next_date += timedelta(days=1)
    elif recurrence_type == 'weekly':
        # Same day next week
        next_date = now_local + timedelta(weeks=1)
    elif recurrence_type == 'monthly':
        # Same day next month
        next_month = now_local.month + 1
        next_year = now_local.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        try:
            next_date = now_local.replace(year=next_year, month=next_month)
        except ValueError:
            # Handle edge case for months with different days
            next_date = now_local.replace(year=next_year, month=next_month, day=28)
    else:
        return None
    
    # Set the time
    next_datetime_local = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # Convert to UTC
    next_datetime_utc = next_datetime_local.astimezone(tz_module.UTC).replace(tzinfo=None)
    
    # Create new reminder
    new_id = await add_reminder(
        user_id=reminder['user_id'],
        chat_id=reminder['chat_id'],
        task_text=reminder['task_text'],
        scheduled_time=next_datetime_utc,
        user_timezone=user_tz,
        notes=reminder.get('notes'),
        location=reminder.get('location'),
        recurrence_type=recurrence_type,
        recurrence_time=recurrence_time
    )
    
    return new_id
