# core/transcription_worker.py

import logging
import numpy as np
import queue
import time
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from core.audio_capture import AudioCapture
from core.transcriber import Transcriber
from core.verse_detector import VerseDetector
from core.bible_db import BibleDB
from data.book_names import BIBLE_BOOKS
from configparser import ConfigParser

logger = logging.getLogger(__name__)

class TranscriptionWorker(QObject):
    """
    Worker class to handle audio capture, transcription, and verse detection in a background thread.
    Emits signals for UI updates.
    """
    transcript_signal = pyqtSignal(str)
    verse_detected_signal = pyqtSignal(str, str, float) # text, reference, confidence
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, config: ConfigParser, bible_db: BibleDB):
        super().__init__()
        self.config = config
        self.bible_db = bible_db
        self.audio_queue = queue.Queue()
        self.is_running = False
        
        self.transcriber = Transcriber()
        self.detector = VerseDetector(
            confidence_threshold=self.config.getfloat('detection', 'confidence_threshold', fallback=0.75)
        )
        self.audio_capture = AudioCapture(callback=self._audio_callback)

        # Build initial prompt for Whisper (Bible vocabulary)
        self.initial_prompt = ", ".join(BIBLE_BOOKS.keys())

    def _audio_callback(self, audio_chunk: np.ndarray):
        """Callback from AudioCapture to queue audio data."""
        self.audio_queue.put(audio_chunk)

    @pyqtSlot()
    def start_processing(self):
        """Main loop for transcription and detection."""
        self.is_running = True
        try:
            self.transcriber.initialize_model()
            self.audio_capture.start()
            self.status_signal.emit("Transcription Started")
            logger.info("TranscriptionWorker loop started.")

            chunk_seconds = self.config.getint('audio', 'chunk_seconds', fallback=5)
            sample_rate = self.config.getint('audio', 'sample_rate', fallback=16000)
            required_frames = chunk_seconds * sample_rate
            
            audio_buffer = np.zeros((0, 1), dtype=np.float32)

            while self.is_running:
                try:
                    # Get all available audio chunks from queue
                    while not self.audio_queue.empty():
                        chunk = self.audio_queue.get_nowait()
                        audio_buffer = np.vstack((audio_buffer, chunk))

                    # If we have enough audio, process it
                    if len(audio_buffer) >= required_frames:
                        # Process only the required frames, keep the rest for rolling window
                        to_process = audio_buffer[:required_frames].flatten()
                        # Shift buffer (simple rolling window: keep last 2 seconds)
                        overlap_frames = 2 * sample_rate
                        audio_buffer = audio_buffer[-(overlap_frames):] if len(audio_buffer) > overlap_frames else np.zeros((0, 1), dtype=np.float32)

                        # Transcribe
                        text = self.transcriber.transcribe(to_process, initial_prompt=self.initial_prompt)
                        if text:
                            logger.debug(f"Transcript: {text}")
                            self.transcript_signal.emit(text)

                            # Detect Verses
                            detections = self.detector.detect(text)
                            for d in detections:
                                logger.info(f"Verse Detected: {d['book']} {d['chapter']}:{d['verse']} ({d['confidence']})")
                                # Lookup verse text in DB
                                verse_text, ref = self.bible_db.lookup_verse(f"{d['book']} {d['chapter']}:{d['verse']}")
                                if verse_text:
                                    self.verse_detected_signal.emit(verse_text, ref, d['confidence'])

                    time.sleep(0.5) # Prevent CPU spinning
                except queue.Empty:
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error in transcription loop: {e}")
                    self.error_signal.emit(str(e))

        except Exception as e:
            logger.error(f"Failed to start TranscriptionWorker: {e}")
            self.error_signal.emit(str(e))
        finally:
            self.stop_processing()

    @pyqtSlot()
    def stop_processing(self):
        """Stops the worker loop and audio capture."""
        self.is_running = False
        self.audio_capture.stop()
        self.status_signal.emit("Transcription Stopped")
        logger.info("TranscriptionWorker loop stopped.")
