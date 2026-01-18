"""
Time parsing module for natural language date/time expressions.
Uses dateparser for flexible parsing of expressions in multiple languages.
Supports Uzbek and Russian languages for Uzbekistan users.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
import dateparser
from dateutil import parser as dateutil_parser
from dateutil import tz
from slang_dictionary import normalize_slang

logger = logging.getLogger(__name__)

# Common time patterns for extraction (Uzbek and Russian)
TIME_PATTERNS = [
    # Uzbek: "X minut/soatdan keyin"
    r"(.+?)\s+(\d+)\s*(minut|soat|kun)(?:dan\s+keyin)?",
    # Russian: "напомни мне через X минут"
    r"(?:напомни\s+(?:мне\s+)?)?(.+?)\s+через\s+(\d+)\s*(минут[у|ы]?|час[а|ов]?|дн[яей]?)",
    # Uzbek: "ertaga/bugun soat X da"
    r"(ertaga|bugun|indinga)\s+(?:soat\s+)?(\d{1,2})(?::(\d{2}))?\s*(?:da)?",
    # Russian: "завтра в X"
    r"(завтра|сегодня|послезавтра)\s+(?:в\s+)?(\d{1,2})(?::(\d{2}))?",
]

# Task separators for multiple tasks
TASK_SEPARATORS = [
    r'\s+(?:va\s+yana|shuningdek|va\s+ham)\s+',   # Uzbek (removed 'keyin' - it's for time)
    r'\s+(?:и\s+ещё|а\s+также|также|потом)\s+',    # Russian
    r'\s*[;]\s*',                                    # Semicolon
    r'\s*,\s*(?=(?:напомни|также|va|yana|eslat))',  # Comma before keywords
]


def parse_reminder_text(
    text: str,
    user_timezone: str = 'Asia/Tashkent',
    language: Optional[str] = None
) -> Tuple[str, Optional[datetime]]:
    """
    Parse a reminder text to extract the task and scheduled time.
    Supports Uzbek and Russian languages.
    
    Args:
        text: The transcribed text from voice message.
        user_timezone: User's timezone for relative time calculations.
        language: Detected language code (e.g., 'ru', 'uz').
    
    Returns:
        Tuple of (task_text, scheduled_datetime in UTC).
        If no time could be parsed, scheduled_datetime will be None.
    """
    text = text.strip()
    original_text = text
    
    # Normalize slang before parsing
    text = normalize_slang(text)
    logger.info(f"After slang normalization: '{text}'")
    
    # Configure dateparser for Uzbek and Russian
    languages = ['uz', 'ru']
    if language:
        if language.startswith('ru'):
            languages = ['ru', 'uz']
        elif language.startswith('uz'):
            languages = ['uz', 'ru']
    
    # Try Uzbek relative time patterns first (support both numbers and word numbers)
    relative_match = re.search(
        r"(\d+|bir|ikki|uch|to'rt|besh|olti|yetti|sakkiz|to'qqiz|o'n)\s*(minut|soat|kun|hafta)(?:dan\s+keyin)?",
        text,
        re.IGNORECASE
    )
    
    # Also try Russian relative patterns
    if not relative_match:
        relative_match = re.search(
            r"через\s+(\d+)\s*(минут[у|ы]?|час[а|ов]?|дн[яей]?|недел[ю|и]?)",
            text,
            re.IGNORECASE
        )
    
    if relative_match:
        # Convert Uzbek word numbers to integers
        uzbek_numbers = {
            'bir': 1, 'ikki': 2, 'uch': 3, "to'rt": 4, 'besh': 5,
            'olti': 6, 'yetti': 7, 'sakkiz': 8, "to'qqiz": 9, "o'n": 10
        }
        amount_str = relative_match.group(1).lower()
        amount = uzbek_numbers.get(amount_str, int(amount_str) if amount_str.isdigit() else 1)
        unit = relative_match.group(2).lower()
        
        # Calculate the scheduled time
        now = datetime.utcnow()
        if any(u in unit for u in ["minut", "мин"]):
            scheduled_time = now + timedelta(minutes=amount)
        elif any(u in unit for u in ["soat", "час"]):
            scheduled_time = now + timedelta(hours=amount)
        elif any(u in unit for u in ["kun", "дн"]):
            scheduled_time = now + timedelta(days=amount)
        elif any(u in unit for u in ["hafta", "недел"]):
            scheduled_time = now + timedelta(weeks=amount)
        else:
            scheduled_time = now + timedelta(hours=1)  # Default to 1 hour
        
        # Extract task (remove the time part)
        task = re.sub(
            r"\s*(\d+\s*(minut|soat|kun|hafta)(?:dan\s+keyin)?|через\s+\d+\s*(минут[уы]?|час[аов]?|дн[яей]?|недел[юи]?))\s*",
            " ",
            text,
            flags=re.IGNORECASE
        ).strip()
        
        # Clean up common prefixes (Uzbek and Russian)
        task = re.sub(
            r"^(?:eslatma|eslat|menga\s+eslat)?|^(?:напомни\s+(?:мне\s+)?)?",
            "",
            task,
            flags=re.IGNORECASE
        ).strip()
        
        if task:
            logger.info(f"Parsed relative time: task='{task}', time={scheduled_time}")
            return task, scheduled_time
    
    # Try to parse with dateparser for natural language
    settings = {
        'PREFER_DATES_FROM': 'future',
        'PREFER_DAY_OF_MONTH': 'first',
        'RETURN_AS_TIMEZONE_AWARE': False,
        'TIMEZONE': user_timezone,
        'TO_TIMEZONE': 'UTC',
    }
    
    # Common time expressions (Uzbek and Russian)
    time_expressions = [
        # Uzbek patterns
        r"(ertaga|bugun|indinga|keyingi\s+hafta)(?:\s+soat\s+[\d:]+(?:\s*da)?)?",
        r"(soat\s+\d{1,2}(?::\d{2})?(?:\s*da)?)",
        r"((?:dushanba|seshanba|chorshanba|payshanba|juma|shanba|yakshanba)\s+(?:soat\s+)?[\d:]+)",
        # Russian patterns
        r"(завтра|сегодня|послезавтра|на\s+следующей\s+неделе)(?:\s+в\s+[\d:]+)?",
        r"(в\s+\d{1,2}(?::\d{2})?(?:\s*час[аов]?)?)",
        r"((?:понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)\s+(?:в\s+)?[\d:]+)",
    ]
    
    parsed_time = None
    time_text_found = None
    
    for pattern in time_expressions:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            time_text = match.group(1) if match.lastindex else match.group(0)
            parsed = dateparser.parse(time_text, settings=settings)
            if parsed and parsed > datetime.utcnow():
                parsed_time = parsed
                time_text_found = match.group(0)
                break
    
    # If no specific pattern matched, try parsing the whole text
    if not parsed_time:
        parsed = dateparser.parse(text, settings=settings)
        if parsed and parsed > datetime.utcnow():
            parsed_time = parsed
    
    # Extract the task by removing time-related parts
    if parsed_time:
        task = text
        
        # Remove common time-related phrases (Uzbek and Russian)
        time_removals = [
            # Uzbek patterns
            r"\s*soat\s+\d{1,2}(?::\d{2})?\s*(?:da)?\s*",
            r"\s*ertaga\s*",
            r"\s*bugun\s*",
            r"\s*indinga\s*",
            r"\s*keyingi\s+\w+\s*",
            r"\s*(?:dushanba|seshanba|chorshanba|payshanba|juma|shanba|yakshanba)\s*",
            # Russian patterns
            r"\s*завтра\s*",
            r"\s*сегодня\s*",
            r"\s*послезавтра\s*",
            r"\s*в\s+\d{1,2}(?::\d{2})?\s*(?:час[аов]?)?\s*",
            r"\s*(?:понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)\s*",
        ]
        
        for removal in time_removals:
            task = re.sub(removal, " ", task, flags=re.IGNORECASE)
        
        # Clean up prefixes (Uzbek and Russian)
        task = re.sub(
            r"^(?:eslatma|eslat|menga\s+eslat)?|^(?:напомни\s+(?:мне\s+)?)?",
            "",
            task,
            flags=re.IGNORECASE
        )
        task = " ".join(task.split())  # Normalize whitespace
        
        if task:
            logger.info(f"Parsed natural language time: task='{task}', time={parsed_time}")
            return task, parsed_time
    
    # If no time could be parsed, return the original text with None
    task = re.sub(
        r"^(?:eslatma|eslat|menga\s+eslat)?|^(?:напомни\s+(?:мне\s+)?)?",
        "",
        original_text,
        flags=re.IGNORECASE
    ).strip()
    logger.warning(f"Could not parse time from text: '{original_text}'")
    return task, None


def parse_multiple_tasks(text: str, language: Optional[str] = None) -> List[str]:
    """
    Split text containing multiple tasks into individual task strings.
    
    Args:
        text: The full transcription text.
        language: Detected language for better parsing.
    
    Returns:
        List of individual task strings.
    """
    # First, try to split by explicit separators
    for sep_pattern in TASK_SEPARATORS:
        if re.search(sep_pattern, text, re.IGNORECASE):
            parts = re.split(sep_pattern, text, flags=re.IGNORECASE)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                logger.info(f"Split into {len(parts)} tasks using separator")
                return parts
    
    # Check for numbered lists: "1. task one 2. task two"
    numbered_match = re.findall(r'(?:^|\s)(\d+[.)]\s*.+?)(?=\s*\d+[.)]|\s*$)', text)
    if len(numbered_match) > 1:
        logger.info(f"Found {len(numbered_match)} numbered tasks")
        return [re.sub(r'^\d+[.)]\s*', '', t.strip()) for t in numbered_match]
    
    # Check for "first... second... third..." patterns
    ordinal_pattern = r'(?:first|second|third|fourth|fifth|во-первых|во-вторых|в-третьих)'
    if re.search(ordinal_pattern, text, re.IGNORECASE):
        parts = re.split(ordinal_pattern, text, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 3]
        if len(parts) > 1:
            logger.info(f"Split into {len(parts)} tasks using ordinals")
            return parts
    
    # No multiple tasks detected
    return [text]


def parse_snooze_duration(text: str) -> Optional[timedelta]:
    """
    Parse a snooze duration from user input.
    Supports Uzbek and Russian.
    
    Args:
        text: User input like "30 minut", "1 soat", "2 soat", "30 минут".
    
    Returns:
        timedelta representing the snooze duration, or None if not parseable.
    """
    text = text.lower().strip()
    
    # Match patterns (Uzbek and Russian)
    patterns = [
        # Uzbek patterns
        (r"(\d+)\s*(?:minut|daqiqa)", "minutes"),
        (r"(\d+)\s*(?:soat)", "hours"),
        (r"(\d+)\s*(?:kun)", "days"),
        # Russian patterns
        (r"(\d+)\s*(?:минут[уы]?|мин)", "minutes"),
        (r"(\d+)\s*(?:час[аов]?|ч\b)", "hours"),
        (r"(\d+)\s*(?:дн[яей]?|д\b)", "days"),
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, text)
        if match:
            amount = int(match.group(1))
            if unit == "minutes":
                return timedelta(minutes=amount)
            elif unit == "hours":
                return timedelta(hours=amount)
            elif unit == "days":
                return timedelta(days=amount)
    
    # Try to parse just a number (default to minutes)
    if text.isdigit():
        return timedelta(minutes=int(text))
    
    return None


def format_datetime(dt: datetime, user_timezone: str = 'UTC') -> str:
    """
    Format a datetime for user-friendly display in their timezone.
    
    Args:
        dt: The datetime to format (assumed UTC if naive).
        user_timezone: User's timezone string.
    
    Returns:
        Formatted string like "Tomorrow at 3:00 PM" or "Monday, Jan 15 at 2:30 PM".
    """
    try:
        # Convert from UTC to user timezone
        user_tz = tz.gettz(user_timezone) or tz.UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.UTC)
        dt_local = dt.astimezone(user_tz)
    except Exception:
        dt_local = dt
    
    now = datetime.now(user_tz if 'user_tz' in dir() else None) or datetime.now()
    if dt_local.tzinfo:
        now = datetime.now(dt_local.tzinfo)
    
    today = now.date()
    tomorrow = today + timedelta(days=1)
    
    # Uzbek day names
    uzbek_days = {
        'Monday': 'Dushanba',
        'Tuesday': 'Seshanba', 
        'Wednesday': 'Chorshanba',
        'Thursday': 'Payshanba',
        'Friday': 'Juma',
        'Saturday': 'Shanba',
        'Sunday': 'Yakshanba'
    }
    
    # Uzbek month names
    uzbek_months = {
        'January': 'Yanvar', 'February': 'Fevral', 'March': 'Mart',
        'April': 'Aprel', 'May': 'May', 'June': 'Iyun',
        'July': 'Iyul', 'August': 'Avgust', 'September': 'Sentabr',
        'October': 'Oktabr', 'November': 'Noyabr', 'December': 'Dekabr'
    }
    
    if dt_local.date() == today:
        return f"Bugun soat {dt_local.strftime('%H:%M')}"
    elif dt_local.date() == tomorrow:
        return f"Ertaga soat {dt_local.strftime('%H:%M')}"
    elif (dt_local.date() - today).days < 7:
        day_name = uzbek_days.get(dt_local.strftime('%A'), dt_local.strftime('%A'))
        return f"{day_name} soat {dt_local.strftime('%H:%M')}"
    else:
        month_name = uzbek_months.get(dt_local.strftime('%B'), dt_local.strftime('%B'))
        return f"{dt_local.day}-{month_name}, {dt_local.year} soat {dt_local.strftime('%H:%M')}"


def detect_timezone_from_location(location_text: str) -> Optional[str]:
    """
    Try to detect timezone from location mention in text.
    Focuses on Uzbekistan cities.
    
    Args:
        location_text: Text that might contain location/timezone info.
    
    Returns:
        Timezone string or None.
    """
    # Uzbekistan cities and regions to timezone mappings
    timezone_hints = {
        # Uzbekistan cities (all Asia/Tashkent +5)
        'toshkent': 'Asia/Tashkent',
        'tashkent': 'Asia/Tashkent',
        'ташкент': 'Asia/Tashkent',
        'samarqand': 'Asia/Samarkand',
        'samarkand': 'Asia/Samarkand',
        'самарканд': 'Asia/Samarkand',
        'buxoro': 'Asia/Samarkand',
        'bukhara': 'Asia/Samarkand',
        'бухара': 'Asia/Samarkand',
        'andijon': 'Asia/Tashkent',
        'andijan': 'Asia/Tashkent',
        'андижан': 'Asia/Tashkent',
        "farg'ona": 'Asia/Tashkent',
        'fergana': 'Asia/Tashkent',
        'фергана': 'Asia/Tashkent',
        'namangan': 'Asia/Tashkent',
        'наманган': 'Asia/Tashkent',
        'xorazm': 'Asia/Samarkand',
        'urgench': 'Asia/Samarkand',
        'ургенч': 'Asia/Samarkand',
        'nukus': 'Asia/Samarkand',
        'нукус': 'Asia/Samarkand',
        'qarshi': 'Asia/Samarkand',
        'karshi': 'Asia/Samarkand',
        'карши': 'Asia/Samarkand',
        'navoiy': 'Asia/Samarkand',
        'navoi': 'Asia/Samarkand',
        'навои': 'Asia/Samarkand',
        "o'zbekiston": 'Asia/Tashkent',
        'uzbekistan': 'Asia/Tashkent',
        'узбекистан': 'Asia/Tashkent',
        # Russian cities (for Russian speakers)
        'moscow': 'Europe/Moscow',
        'москва': 'Europe/Moscow',
    }
    
    text_lower = location_text.lower()
    for hint, timezone in timezone_hints.items():
        if hint in text_lower:
            return timezone
    
    return None
