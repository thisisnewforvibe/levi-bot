"""
Gemini AI-powered intelligent parsing for reminder tasks and times.
Uses Google's Gemini model for natural language understanding.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
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
) -> List[Dict[str, Any]]:
    """
    Use Gemini AI to intelligently parse reminder text into tasks, times, notes, and locations.
    
    Args:
        text: The transcribed text from voice message.
        user_timezone: User's timezone (default: Asia/Tashkent).
        language: Detected language (uz, ru).
    
    Returns:
        List of dicts: [{"task": str, "time": datetime, "notes": str, "location": str}, ...]
    """
    if not model:
        logger.warning("Gemini API key not configured, skipping AI parsing")
        return []
    
    try:
        # Get current time in user's timezone
        now_utc = datetime.utcnow()
        
        # Create a prompt for Gemini
        prompt = f"""You are a smart reminder assistant for Uzbekistan users. Parse the following text and extract reminder tasks with their scheduled times, additional notes/details, locations, and recurrence patterns.

Current date and time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M')}
User timezone: {user_timezone}
User language: {language or 'uz/ru'}

Text: "{text}"

Extract ALL reminders from this text. For each reminder, determine:
1. The task description (main action - what to do, keep it short like "Dori ichish" or "Magazinga borish")
2. The scheduled time in ISO format (YYYY-MM-DD HH:MM in UTC) - for recurring reminders, use the FIRST occurrence
3. Notes/details (items to buy, things to remember, list of items - extracted from the message)
4. Location (where to do it, if mentioned)
5. Recurrence type (if the reminder should repeat)
6. Recurrence time (the time of day for recurring reminders in HH:MM format, in USER's timezone)

RECURRENCE DETECTION RULES:
- "har kuni" / "каждый день" / "ежедневно" = recurrence_type: "daily"
- "har hafta" / "каждую неделю" / "еженедельно" = recurrence_type: "weekly"  
- "har oy" / "каждый месяц" / "ежемесячно" = recurrence_type: "monthly"
- "ish kunlari" / "har ish kuni" / "по будням" / "в рабочие дни" = recurrence_type: "weekdays"
- If NO recurrence pattern is detected, set recurrence_type to null

IMPORTANT EXTRACTION RULES:
- If user says "har kuni ertalab 9 da dori ichish" - task is "Dori ichish", recurrence_type is "daily", recurrence_time is "09:00"
- If user says "har hafta dushanba 10 da uchrashish" - task is "Uchrashish", recurrence_type is "weekly", recurrence_time is "10:00"
- If user says "magazinga borib olma, non, go'sht olish" - the task is "Magazinga borish", notes are "olma, non, go'sht", location is "magazin"
- For shopping lists, extract ALL items mentioned as notes
- Keep task short and action-oriented
- Notes should contain details, items, or specifications

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
- "ertalab" / "tongda" = 8:00 AM (or 9:00 if "ertalab 9 da")
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

Location words to recognize:
- "magazin" / "do'kon" / "supermarket" / "bozor" = shopping places
- "uy" / "hovli" = home
- "ish" / "ofis" = work/office
- "maktab" / "universitet" = school/university
- "shifoxona" / "kasalxona" / "klinika" = hospital/clinic
- "apteka" / "dorixona" = pharmacy
- "bank" = bank

Return ONLY a JSON array with this exact format:
[
  {{"task": "short task description", "time_utc": "2026-01-16 16:30", "notes": "item1, item2, item3", "location": "place name", "recurrence_type": "daily", "recurrence_time": "09:00"}},
  {{"task": "another task", "time_utc": "2026-01-17 09:00", "notes": null, "location": null, "recurrence_type": null, "recurrence_time": null}}
]

If the text is not a reminder or makes no sense, return an empty array: []
"""
        
        # Call Gemini
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        logger.info(f"Gemini raw response: {result_text[:500]}")
        
        # Extract JSON from response (remove markdown code blocks if present)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        logger.info(f"Gemini cleaned JSON: {result_text}")
        
        # Parse JSON response
        reminders = json.loads(result_text)
        
        if not isinstance(reminders, list):
            logger.error(f"Gemini returned non-list: {result_text}")
            return []
        
        # Convert to list of dicts with datetime objects
        parsed_reminders = []
        for reminder in reminders:
            if not isinstance(reminder, dict) or 'task' not in reminder or 'time_utc' not in reminder:
                continue
            
            task = reminder['task']
            time_str = reminder['time_utc']
            notes = reminder.get('notes')
            location = reminder.get('location')
            recurrence_type = reminder.get('recurrence_type')
            recurrence_time = reminder.get('recurrence_time')
            
            try:
                # Parse the UTC time string
                scheduled_time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
                
                # Check if time is in the past
                if scheduled_time <= now_utc:
                    # For RECURRING reminders, schedule for next valid occurrence
                    if recurrence_type:
                        logger.info(f"Recurring reminder with past time {time_str}, scheduling for next occurrence")
                        if recurrence_type == 'daily':
                            # Schedule for tomorrow at the same time
                            scheduled_time = scheduled_time + timedelta(days=1)
                        elif recurrence_type == 'weekdays':
                            # Schedule for next weekday
                            scheduled_time = scheduled_time + timedelta(days=1)
                            while scheduled_time.weekday() >= 5:  # Skip weekends
                                scheduled_time = scheduled_time + timedelta(days=1)
                        elif recurrence_type == 'weekly':
                            # Schedule for next week
                            scheduled_time = scheduled_time + timedelta(weeks=1)
                        elif recurrence_type == 'monthly':
                            # Schedule for next month
                            if scheduled_time.month == 12:
                                scheduled_time = scheduled_time.replace(year=scheduled_time.year + 1, month=1)
                            else:
                                scheduled_time = scheduled_time.replace(month=scheduled_time.month + 1)
                        logger.info(f"Rescheduled recurring reminder to: {scheduled_time}")
                    else:
                        # Non-recurring reminder in past - skip it
                        logger.warning(f"Gemini returned past time for non-recurring: {time_str}")
                        continue
                
                parsed_reminders.append({
                    "task": task,
                    "time": scheduled_time,
                    "notes": notes,
                    "location": location,
                    "recurrence_type": recurrence_type,
                    "recurrence_time": recurrence_time
                })
                logger.info(f"Gemini parsed: task='{task}', time={scheduled_time}, notes='{notes}', location='{location}', recurrence='{recurrence_type}' at '{recurrence_time}'")
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
