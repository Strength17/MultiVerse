# core/transcriber.py
import logging
import configparser
from faster_whisper import WhisperModel
from data.book_names import BIBLE_BOOKS

logger = logging.getLogger(__name__)

class Transcriber:
    """Wrapper for faster-whisper transcription engine."""
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        self.model_size = self.config.get('transcription', 'model_size', fallback='medium.en')
        self.device = self.config.get('transcription', 'device', fallback='cpu')
        self.compute_type = self.config.get('transcription', 'compute_type', fallback='int8')
        
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        self.initial_prompt = self._build_prompt()

    def _build_prompt(self):
        """Constructs the initial prompt for Bible book injection."""
        books = [book for book in BIBLE_BOOKS.keys()]
        # Keep prompt under 200 tokens per L-002
        return ", ".join(books[:50])

    def transcribe(self, audio_data):
        """Transcribes audio buffer."""
        try:
            segments, info = self.model.transcribe(audio_data, initial_prompt=self.initial_prompt)
            return " ".join([segment.text for segment in segments])
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
