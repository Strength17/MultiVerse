# core/transcriber.py
import logging
from faster_whisper import WhisperModel
import configparser
from typing import Optional

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

logger = logging.getLogger(__name__)

class Transcriber:
    """Wraps faster-whisper for real-time transcription."""
    
    def __init__(self):
        self.model_size = config.get('transcription', 'model_size', fallback='medium.en')
        self.device = config.get('transcription', 'device', fallback='cpu')
        self.compute_type = config.get('transcription', 'compute_type', fallback='int8')
        self.model: Optional[WhisperModel] = None

    def initialize_model(self):
        """Initializes the Whisper model. Handles download if necessary."""
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(self, audio_data, initial_prompt: str = ""):
        """
        Transcribes audio data.
        
        Args:
            audio_data: Numpy array of audio samples.
            initial_prompt: Vocabulary injection string.
        """
        if not self.model:
            raise RuntimeError("Model not initialized. Call initialize_model() first.")
            
        segments, info = self.model.transcribe(
            audio_data,
            beam_size=5,
            initial_prompt=initial_prompt
        )
        
        full_text = " ".join([segment.text for segment in segments])
        return full_text.strip()
