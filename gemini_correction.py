"""
Gemini AI post-correction for Whisper transcriptions.
Fixes common Uzbek STT errors using AI understanding.
"""

import logging
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


async def correct_transcription(text: str, language: str = "uz") -> str:
    """
    Correct Whisper transcription errors using Gemini AI.
    
    Args:
        text: Raw Whisper transcription
        language: Language code (uz or ru)
    
    Returns:
        Corrected transcription
    """
    if not GEMINI_API_KEY or not text:
        return text
    
    try:
        # Create correction prompt
        prompt = f"""You are a transcription correction expert for Uzbek/Russian voice messages.

The following text was transcribed by Whisper AI but may contain errors:
"{text}"

Please correct ONLY the obvious transcription errors while preserving the original meaning. Fix:
1. Misspelled Uzbek/Russian words
2. Wrong numbers (e.g., "um" → "o'n", "on" → "o'n")
3. Grammar mistakes from misheard words
4. Common speech-to-text errors in Uzbek (ш/с, к/қ, ғ/г confusion)

DO NOT:
- Change the meaning or intent
- Add new words
- Rephrase sentences
- Remove any content

Return ONLY the corrected text, no explanations."""

        # Call Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        
        corrected = response.text.strip()
        
        if corrected and corrected != text:
            logger.info(f"Gemini corrected: '{text}' → '{corrected}'")
            return corrected
        else:
            return text
    
    except Exception as e:
        logger.error(f"Gemini correction error: {e}")
        return text  # Return original on error
