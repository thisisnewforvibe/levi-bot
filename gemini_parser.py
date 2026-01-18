"""
Gemini AI-powered intelligent parsing for reminder tasks and times.
Uses Google's Gemini model for natural language understanding.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import google.generativeai as genai
from config import GEMINI_API_KEY, DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Use the latest stable flash model
    model = genai.GenerativeModel('models/gemini-2.0-flash')
else:
    model = None


async def parse_with_gemini(
    text: str,
    user_timezone: str = DEFAULT_TIMEZONE,
    language: Optional[str] = None
) -> List[Tuple[str, Optional[datetime]]]:
    """
    Use Gemini AI to intelligently parse reminder text into tasks and times.
    
    Args:
        text: The transcribed text from voice message.
        user_timezone: User's timezone (default: Asia/Tashkent).
        language: Detected language (uz, ru).
    
    Returns:
        List of tuples: [(task_text, scheduled_datetime_utc), ...]
    """
    if not model:
        logger.warning("Gemini API key not configured, skipping AI parsing")
        return []
    
    try:
        # Get current time in user's timezone
        now_utc = datetime.utcnow()
        
        # Create a prompt for Gemini
        prompt = f"""You are a smart reminder assistant for Uzbekistan users. Parse the following text and extract reminder tasks with their scheduled times.

Current date and time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M')}
User timezone: {user_timezone}
User language: {language or 'uz/ru'}

Text: "{text}"

Extract ALL reminders from this text. For each reminder, determine:
1. The task description (what to do)
2. The scheduled time in ISO format (YYYY-MM-DD HH:MM in UTC)

Time parsing rules (including slang & colloquialisms):
CRITICAL: If text contains "X minut" or "X daqiqa" patterns, ALWAYS interpret as "in X minutes from now":
- "5 minut" / "5 minutdan" / "5 minut anca" / "5 minutda" = 5 minutes from now
- "10 minut" / "10 minutdan keyin" / "10 daqiqa" = 10 minutes from now
- "15 minut" / "15 minutdan" = 15 minutes from now
- "30 minut" / "yarim soat" = 30 minutes from now
- "bir soatdan keyin" / "bir soatdan so'ng" = 1 hour from now
- "ikki soatdan keyin" = 2 hours from now
- "ertaga" / "ertangi kun" = tomorrow at 9:00 AM
- "bugun" / "shu kun" = today
- "kechqurun" / "oqshom" = today at 6:00 PM
- "ertalab" / "tongda" = tomorrow at 8:00 AM
- "tushlikda" / "peshindan keyin" = today at 1:00 PM
- "завтра" / "завтра утром" = tomorrow morning (9 AM)
- "сегодня вечером" / "вечером" = today evening (6 PM)
- "через час" / "через часик" = 1 hour from now
- "попозже" / "позже" = 2 hours from now
- "через полчаса" / "через полчасика" = 30 minutes from now
- "5 минут" / "через 5 минут" = 5 minutes from now

Common slang expressions:
- "keyin" alone = later (2 hours from now)
- "hoziroq" / "сейчас" = now (5 minutes from now)
- "biroz keyin" / "немного попозже" = a bit later (30 minutes)
- "tezda" / "tez" / "быстро" = soon (15 minutes)
- "kechasi" / "ночью" = tonight at 10:00 PM
- "yangi yilda" / "новый год" = January 1st at 12:00 AM

Task slang & informal words:
- "qo'ng'iroq qil" / "звони" / "позвони" = call
- "xabar qil" / "напиши" / "сообщи" = message/text
- "chiqish" / "выйти" / "пойти" = go out
- "uchrashish" / "встреча" / "встретиться" = meet
- "ovqat" / "еда" / "покушать" / "поесть" = eat
- "uxlash" / "спать" / "лечь спать" = sleep

Return ONLY a JSON array with this exact format:
[
  {{"task": "task description", "time_utc": "2026-01-16 16:30"}},
  {{"task": "another task", "time_utc": "2026-01-17 09:00"}}
]

If the text is not a reminder or makes no sense, return an empty array: []
"""
        
        # Call Gemini
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Extract JSON from response (remove markdown code blocks if present)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON response
        reminders = json.loads(result_text)
        
        if not isinstance(reminders, list):
            logger.error(f"Gemini returned non-list: {result_text}")
            return []
        
        # Convert to tuples with datetime objects
        parsed_reminders = []
        for reminder in reminders:
            if not isinstance(reminder, dict) or 'task' not in reminder or 'time_utc' not in reminder:
                continue
            
            task = reminder['task']
            time_str = reminder['time_utc']
            
            try:
                # Parse the UTC time string
                scheduled_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                
                # Only add if time is in the future
                if scheduled_time > now_utc:
                    parsed_reminders.append((task, scheduled_time))
                    logger.info(f"Gemini parsed: task='{task}', time={scheduled_time}")
                else:
                    logger.warning(f"Gemini returned past time: {time_str}")
            except ValueError as e:
                logger.error(f"Failed to parse Gemini time '{time_str}': {e}")
                continue
        
        return parsed_reminders
    
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}, response: {result_text if 'result_text' in locals() else 'N/A'}")
        return []
    
    except Exception as e:
        logger.error(f"Gemini parsing error: {e}")
        return []
