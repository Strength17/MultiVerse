# core/audio_capture.py
import sounddevice as sd
import numpy as np
import logging
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class AudioCapture(QObject):
    """Captures real-time audio from the selected input device."""
    
    audio_level = pyqtSignal(float)
    
    def __init__(self, device_index: int = 0, sample_rate: int = 16000, channels: int = 1, callback: Optional[Callable[[np.ndarray], None]] = None):
        """
        Initializes the AudioCapture.
        
        Args:
            device_index: Index of the audio input device.
            sample_rate: Sample rate for capture.
            channels: Number of audio channels.
            callback: Function to call with audio chunks.
        """
        super().__init__()
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.channels = channels
        self.callback = callback
        self.stream: Optional[sd.InputStream] = None
        
    @staticmethod
    def get_devices():
        """Returns a list of available input devices."""
        return sd.query_devices()

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
        
        # Calculate RMS
        rms = float(np.sqrt(np.mean(indata ** 2)))
        self.audio_level.emit(rms)
        
        # Pass the audio data to the provided callback
        if self.callback:
            self.callback(indata.copy())
