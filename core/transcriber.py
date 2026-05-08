# core/transcriber.py
import logging
import os
import whisper
import numpy as np
import time
from configparser import ConfigParser
from typing import Optional

logger = logging.getLogger(__name__)

class Transcriber:
    """Wraps openai-whisper for real-time transcription."""
    
    def __init__(self, config: ConfigParser):
        """
        Initializes the Transcriber with settings from config.
        
        Args:
            config: ConfigParser instance containing [transcription] section.
        """
        self.config = config
        self.model_size = config.get('transcription', 'model_size', fallback='base.en')
        self.device = config.get('transcription', 'device', fallback='cpu')
        self.model_dir = config.get('transcription', 'model_cache_path', fallback=None)
        self.chunk_seconds = config.getint('audio', 'chunk_seconds', fallback=5)
        self.model: Optional[whisper.Whisper] = None

    def initialize_model(self):
        """Initializes the standard Whisper model."""
        try:
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
            # Ensure local files only if configured
            is_local = self.config.getboolean('transcription', 'local_files_only', fallback=True)
            self.model = whisper.load_model(
                self.model_size,
                device=self.device,
                download_root=self.model_dir
            )
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(self, audio_data: np.ndarray, initial_prompt: str = ""):
        """
        Transcribes audio data using standard Whisper with benchmarking.
        
        Args:
            audio_data: Numpy array of audio samples (float32).
            initial_prompt: Vocabulary injection string.
        """
        if not self.model:
            raise RuntimeError("Model not initialized. Call initialize_model() first.")
            
        t = time.perf_counter()
        result = self.model.transcribe(
            audio_data,
            initial_prompt=initial_prompt,
            language='en',
            fp16=False # Critical: N3530 has no hardware float16 support
        )
        duration = time.perf_counter() - t
        
        logger.info(f"Transcription took {duration:.2f}s for {self.chunk_seconds}s audio")
        
        return result.get("text", "").strip()
