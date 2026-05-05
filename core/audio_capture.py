# core/audio_capture.py
import sounddevice as sd
import numpy as np
import queue
import logging
from typing import Optional, Callable
import configparser

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

logger = logging.getLogger(__name__)

class AudioCapture:
    """Captures real-time audio from the selected input device."""
    
    def __init__(self, callback: Callable[[np.ndarray], None]):
        """
        Initializes the AudioCapture with a callback.
        
        Args:
            callback: Function to call with audio chunks.
        """
        self.device_index = config.getint('audio', 'input_device_index', fallback=0)
        self.sample_rate = config.getint('audio', 'sample_rate', fallback=16000)
        self.channels = config.getint('audio', 'channels', fallback=1)
        self.callback = callback
        self.stream: Optional[sd.InputStream] = None
        
    def start(self):
        """Starts the audio input stream."""
        try:
            self.stream = sd.InputStream(
                device=self.device_index,
                channels=self.channels,
                samplerate=self.sample_rate,
                callback=self._audio_callback
            )
            self.stream.start()
            logger.info(f"Audio capture started on device {self.device_index}")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            raise

    def stop(self):
        """Stops the audio input stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Audio capture stopped")

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status: sd.CallbackFlags):
        """Callback function for the audio stream."""
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        # Pass the audio data to the provided callback
        self.callback(indata.copy())
