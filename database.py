"""
Database module for SQLite operations.
Handles all reminder storage and retrieval operations.
Supports both local SQLite and Turso (cloud SQLite).
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Try to import Turso config
try:
    from config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN, USE_TURSO
except ImportError:
    TURSO_DATABASE_URL = None
    TURSO_AUTH_TOKEN = None
    USE_TURSO = False

from config import DATABASE_PATH

# Try to import libsql for Turso
LIBSQL_AVAILABLE = False
libsql = None
try:
    import libsql_experimental as libsql
    LIBSQL_AVAILABLE = True
    logger.info("libsql_experimental available")
except ImportError:
    try:
        import libsql_client as libsql
        LIBSQL_AVAILABLE = True
        logger.info("libsql_client available")
    except ImportError:
        logger.warning("No libsql library available, using local SQLite")


def get_connection():
    """Get database connection (Turso or local SQLite)."""
    if USE_TURSO and LIBSQL_AVAILABLE and TURSO_DATABASE_URL and TURSO_AUTH_TOKEN and libsql:
        try:
            conn = libsql.connect(
                TURSO_DATABASE_URL,
                auth_token=TURSO_AUTH_TOKEN
            )
            logger.info("Connected to Turso")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to Turso: {e}, falling back to local SQLite")
            return sqlite3.connect(DATABASE_PATH)
    else:
        return sqlite3.connect(DATABASE_PATH)


def rows_to_dicts(cursor, rows) -> List[dict]:
    """Convert rows to list of dictionaries."""
    if not rows:
        return []
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


def row_to_dict(cursor, row) -> Optional[dict]:
    """Convert single row to dictionary."""
    if not row:
        return None
    columns = [description[0] for description in cursor.description]
    return dict(zip(columns, row))


def init_database() -> None:
    """Initialize the database and create tables if they don't exist."""
    db_type = "Turso" if (USE_TURSO and LIBSQL_AVAILABLE) else "local SQLite"
    logger.info(f"Initializing {db_type} database...")
    
    conn = get_connection()
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
    
    logger.info(f"Database initialized successfully using {db_type}")


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
    """Add a new reminder to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reminders (user_id, chat_id, task_text, notes, location, scheduled_time_utc, user_timezone, recurrence_type, recurrence_time, initial_reminder_sent, follow_up_sent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
        """,
        (user_id, chat_id, task_text, notes, location, scheduled_time.isoformat(), user_timezone, recurrence_type, recurrence_time)
    )
    conn.commit()
    lastrowid = cursor.lastrowid
    conn.close()
    return lastrowid


async def get_pending_reminders(before_time: datetime) -> List[dict]:
    """Get all pending reminders scheduled before the given time (UTC)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, chat_id, task_text, notes, location, scheduled_time_utc, 
               user_timezone, initial_reminder_sent, follow_up_sent, 
               recurrence_type, recurrence_time
        FROM reminders
        WHERE status = 'pending' AND scheduled_time_utc <= ?
        ORDER BY scheduled_time_utc ASC
        """,
        (before_time.isoformat(),)
    )
    rows = cursor.fetchall()
    result = rows_to_dicts(cursor, rows)
    conn.close()
    
    for d in result:
        d.setdefault('recurrence_type', None)
        d.setdefault('recurrence_time', None)
        d.setdefault('notes', None)
        d.setdefault('location', None)
    return result


async def get_follow_up_reminders(follow_up_after: datetime) -> List[dict]:
    """Get reminders that need a follow-up (30 minutes after initial reminder)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, chat_id, task_text, notes, location, scheduled_time_utc, user_timezone, recurrence_type
        FROM reminders
        WHERE status = 'pending' 
        AND initial_reminder_sent = 1
        AND follow_up_sent = 0
        AND scheduled_time_utc <= ?
        ORDER BY scheduled_time_utc ASC
        """,
        (follow_up_after.isoformat(),)
    )
    rows = cursor.fetchall()
    result = rows_to_dicts(cursor, rows)
    conn.close()
    return result


async def mark_initial_reminder_sent(reminder_id: int) -> None:
    """Mark that the initial reminder has been sent."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE reminders 
        SET initial_reminder_sent = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (reminder_id,)
    )
    conn.commit()
    conn.close()


async def mark_follow_up_sent(reminder_id: int) -> None:
    """Mark that a follow-up has been sent for a reminder."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE reminders 
        SET follow_up_sent = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (reminder_id,)
    )
    conn.commit()
    conn.close()


async def reschedule_reminder_for_followup(reminder_id: int, new_scheduled_time: datetime) -> None:
    """Reschedule a reminder and reset follow-up flags."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
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
    conn.commit()
    conn.close()


async def update_reminder_status(reminder_id: int, status: str) -> None:
    """Update the status of a reminder."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE reminders 
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, reminder_id)
    )
    conn.commit()
    conn.close()


async def reschedule_reminder(reminder_id: int, new_time: datetime) -> None:
    """Reschedule a reminder to a new time (UTC)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
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
    conn.commit()
    conn.close()


async def get_user_reminders(user_id: int, status: Optional[str] = None) -> List[dict]:
    """Get all reminders for a specific user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute(
            """
            SELECT id, task_text, notes, location, scheduled_time_utc, user_timezone, status, recurrence_type, recurrence_time, created_at
            FROM reminders
            WHERE user_id = ? AND status = ?
            ORDER BY scheduled_time_utc ASC
            """,
            (user_id, status)
        )
    else:
        cursor.execute(
            """
            SELECT id, task_text, notes, location, scheduled_time_utc, user_timezone, status, recurrence_type, recurrence_time, created_at
            FROM reminders
            WHERE user_id = ?
            ORDER BY scheduled_time_utc ASC
            """,
            (user_id,)
        )
    
    rows = cursor.fetchall()
    result = rows_to_dicts(cursor, rows)
    conn.close()
    return result


async def get_reminder_by_id(reminder_id: int) -> Optional[dict]:
    """Get a specific reminder by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, chat_id, task_text, scheduled_time_utc, 
               user_timezone, status, follow_up_sent
        FROM reminders
        WHERE id = ?
        """,
        (reminder_id,)
    )
    row = cursor.fetchone()
    result = row_to_dict(cursor, row)
    conn.close()
    return result


async def delete_reminder(reminder_id: int) -> bool:
    """Delete a reminder by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM reminders WHERE id = ?",
        (reminder_id,)
    )
    conn.commit()
    rowcount = cursor.rowcount
    conn.close()
    return rowcount > 0


async def get_latest_pending_reminder(user_id: int) -> Optional[dict]:
    """Get the most recently created pending reminder for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, chat_id, task_text, scheduled_time_utc, 
               user_timezone, status, follow_up_sent, notes, location,
               recurrence_type, recurrence_time
        FROM reminders
        WHERE user_id = ? AND status = 'pending' AND follow_up_sent = 1
        ORDER BY scheduled_time_utc DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    result = row_to_dict(cursor, row)
    conn.close()
    return result


# ============ User Preferences Functions ============

async def get_user_preferences(user_id: int) -> Optional[dict]:
    """Get user preferences (timezone, language)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    result = row_to_dict(cursor, row)
    conn.close()
    return result


async def set_user_preferences(
    user_id: int,
    timezone: Optional[str] = None,
    language: Optional[str] = None
) -> None:
    """Set or update user preferences."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT 1 FROM user_preferences WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    if exists:
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
            cursor.execute(
                f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = ?",
                values
            )
    else:
        cursor.execute(
            "INSERT INTO user_preferences (user_id, timezone, language) VALUES (?, ?, ?)",
            (user_id, timezone or 'UTC', language or 'en')
        )
    
    conn.commit()
    conn.close()


# ============ Rate Limiting Functions ============

async def check_rate_limit(user_id: int, limit: int, window_seconds: int) -> bool:
    """Check if user is within rate limits."""
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    
    # Clean old entries
    cursor.execute(
        "DELETE FROM rate_limits WHERE timestamp < ?",
        (cutoff.isoformat(),)
    )
    
    # Count recent requests
    cursor.execute(
        "SELECT COUNT(*) FROM rate_limits WHERE user_id = ? AND timestamp >= ?",
        (user_id, cutoff.isoformat())
    )
    row = cursor.fetchone()
    count = row[0] if row else 0
    
    if count >= limit:
        conn.close()
        return False
    
    # Record this request
    cursor.execute(
        "INSERT INTO rate_limits (user_id, timestamp) VALUES (?, ?)",
        (user_id, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()
    return True


# ============ Startup Recovery ============

async def get_all_pending_reminders() -> List[dict]:
    """Get ALL pending reminders for restart recovery."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, chat_id, task_text, notes, location, scheduled_time_utc, 
               user_timezone, follow_up_sent, status, recurrence_type, recurrence_time
        FROM reminders
        WHERE status = 'pending'
        ORDER BY scheduled_time_utc ASC
        """
    )
    rows = cursor.fetchall()
    result = rows_to_dicts(cursor, rows)
    conn.close()
    return result


async def schedule_next_recurrence(reminder: dict) -> Optional[int]:
    """Schedule the next occurrence of a recurring reminder."""
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
        next_date = now_local + timedelta(days=1)
    elif recurrence_type == 'weekdays':
        next_date = now_local + timedelta(days=1)
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)
    elif recurrence_type == 'weekly':
        next_date = now_local + timedelta(weeks=1)
    elif recurrence_type == 'monthly':
        next_month = now_local.month + 1
        next_year = now_local.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        try:
            next_date = now_local.replace(year=next_year, month=next_month)
        except ValueError:
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


# ============ Admin Functions ============

async def get_all_reminders_admin(limit: int = 100) -> List[dict]:
    """Get all reminders for admin panel."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, user_id, chat_id, task_text, notes, location, 
               scheduled_time_utc, user_timezone, status, 
               recurrence_type, created_at
        FROM reminders
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    result = rows_to_dicts(cursor, rows)
    conn.close()
    return result


async def get_all_users_admin() -> List[dict]:
    """Get all users with their reminder counts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            r.user_id,
            COUNT(*) as total_reminders,
            SUM(CASE WHEN r.status = 'pending' THEN 1 ELSE 0 END) as pending_reminders,
            SUM(CASE WHEN r.status = 'done' THEN 1 ELSE 0 END) as completed_reminders,
            MIN(r.created_at) as first_reminder,
            MAX(r.created_at) as last_reminder
        FROM reminders r
        GROUP BY r.user_id
        ORDER BY last_reminder DESC
        """
    )
    rows = cursor.fetchall()
    result = rows_to_dicts(cursor, rows)
    conn.close()
    return result


async def get_user_reminders_admin(user_id: int) -> List[dict]:
    """Get all reminders for a specific user (admin view)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, task_text, notes, location, scheduled_time_utc, 
               user_timezone, status, recurrence_type, created_at
        FROM reminders
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (user_id,)
    )
    rows = cursor.fetchall()
    result = rows_to_dicts(cursor, rows)
    conn.close()
    return result


async def get_stats_admin() -> dict:
    """Get overall bot statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total reminders
    cursor.execute("SELECT COUNT(*) FROM reminders")
    total_reminders = cursor.fetchone()[0]
    
    # Pending reminders
    cursor.execute("SELECT COUNT(*) FROM reminders WHERE status = 'pending'")
    pending_reminders = cursor.fetchone()[0]
    
    # Unique users
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM reminders")
    total_users = cursor.fetchone()[0]
    
    # Today's reminders
    cursor.execute(
        "SELECT COUNT(*) FROM reminders WHERE DATE(created_at) = DATE('now')"
    )
    today_reminders = cursor.fetchone()[0]
    
    # Recurring reminders
    cursor.execute(
        "SELECT COUNT(*) FROM reminders WHERE recurrence_type IS NOT NULL AND status = 'pending'"
    )
    recurring_reminders = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_reminders': total_reminders,
        'pending_reminders': pending_reminders,
        'total_users': total_users,
        'today_reminders': today_reminders,
        'recurring_reminders': recurring_reminders,
    }
