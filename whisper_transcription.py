"""
OpenAI Whisper transcription service for Uzbek voice messages.
Provides better accuracy than Google Cloud STT for Uzbek language.
"""

import logging
import os
import tempfile
import whisper
from pydub import AudioSegment
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class WhisperTranscriber:
    """Handles voice transcription using OpenAI Whisper."""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper transcriber.
        
        Args:
            model_size: Model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        self.custom_vocabulary = self._load_uzbek_vocabulary()
        logger.info(f"WhisperTranscriber initialized with model size: {model_size}")
        logger.info(f"Loaded custom Uzbek vocabulary: {len(self.custom_vocabulary)} chars")
    
    def _load_uzbek_vocabulary(self) -> str:
        """Load Uzbek vocabulary from book corpus for better transcription."""
        vocab_file = Path(__file__).parent / "uzbek_vocabulary.txt"
        
        if vocab_file.exists():
            try:
                vocabulary = vocab_file.read_text(encoding='utf-8').strip()
                logger.info(f"Loaded custom vocabulary from {vocab_file}")
                return vocabulary
            except Exception as e:
                logger.warning(f"Failed to load vocabulary file: {e}")
        
        # Fallback: basic reminder vocabulary
        return (
            "minutdan keyin soatdan keyin ertaga bugun eslat eslatma "
            "qilish kerak o'qish namoz kitob dars ish qo'ng'iroq xabar "
            "uchrash vaqt payt borish kelish yozish"
        )
    
    def load_model(self):
        """Lazy load the Whisper model (downloads on first use)."""
        if self.model is None:
            logger.info(f"Loading Whisper model '{self.model_size}'... (first run will download ~140MB)")
            self.model = whisper.load_model(self.model_size)
            logger.info("Whisper model loaded successfully")
    
    async def transcribe_voice(self, file_path: str, language: str = "uz") -> Optional[str]:
        """
        Transcribe voice message using Whisper.
        
        Args:
            file_path: Path to the voice file (OGG format from Telegram).
            language: Expected language code (uz for Uzbek, ru for Russian).
        
        Returns:
            Transcribed text or None if transcription fails.
        """
        try:
            # Load model if not already loaded
            self.load_model()
            
            # Convert OGG to WAV (Whisper prefers WAV format)
            wav_path = await self._convert_to_wav(file_path)
            
            # Use custom vocabulary from Uzbek dialect book for better accuracy
            initial_prompt = self.custom_vocabulary
            
            # Transcribe with language hint and book-based vocabulary
            logger.info(f"Transcribing with Whisper ({self.model_size} model, language={language}, vocab={len(initial_prompt)} chars)...")
            result = self.model.transcribe(
                wav_path,
                language=language if language in ["uz", "ru"] else None,
                initial_prompt=initial_prompt,
                temperature=0.0,  # More conservative/deterministic
                word_timestamps=False,  # Not needed for reminders
                fp16=False  # Disable FP16 for CPU compatibility
            )
            
            transcribed_text = result["text"].strip()
            logger.info(f"Whisper transcribed: {transcribed_text}")
            
            # Clean up temporary WAV file
            if os.path.exists(wav_path):
                os.remove(wav_path)
            
            return transcribed_text
        
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return None
    
    async def _convert_to_wav(self, ogg_path: str) -> str:
        """
        Convert OGG file to WAV format for Whisper.
        
        Args:
            ogg_path: Path to OGG audio file.
        
        Returns:
            Path to converted WAV file.
        """
        try:
            # Load OGG file
            audio = AudioSegment.from_ogg(ogg_path)
            
            # Whisper expects 16kHz mono audio
            audio = audio.set_frame_rate(16000).set_channels(1)
            
            # Create temporary WAV file
            wav_path = ogg_path.replace(".ogg", ".wav")
            
            # Export as 16-bit PCM WAV
            audio.export(
                wav_path,
                format="wav",
                parameters=["-acodec", "pcm_s16le"]
            )
            
            logger.info(f"Converted {ogg_path} to WAV format")
            return wav_path
        
        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            raise


# Global transcriber instance
_transcriber = None

def get_transcriber(model_size: str = "base") -> WhisperTranscriber:
    """Get or create the global Whisper transcriber instance."""
    global _transcriber
    if _transcriber is None or _transcriber.model_size != model_size:
        _transcriber = WhisperTranscriber(model_size)
    return _transcriber


async def transcribe_audio(file_path: str, model_size: str = "base") -> Optional[str]:
    """
    Convenience function to transcribe audio with Whisper.
    
    Args:
        file_path: Path to audio file.
        model_size: Whisper model size.
    
    Returns:
        Transcribed text or None.
    """
    transcriber = get_transcriber(model_size)
    return await transcriber.transcribe_voice(file_path)
