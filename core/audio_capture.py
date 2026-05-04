# core/audio_capture.py
import sounddevice as sd
import numpy as np
import queue
import logging
import configparser

logger = logging.getLogger(__name__)

class AudioCapture:
    """Manages real-time audio capture using sounddevice callback pattern."""
    
    def __init__(self, callback_func):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        self.device_index = self.config.getint('audio', 'input_device_index', fallback=0)
        self.sample_rate = self.config.getint('audio', 'sample_rate', fallback=16000)
        self.channels = self.config.getint('audio', 'channels', fallback=1)
        self.callback_func = callback_func
        self.stream = None

    def _audio_callback(self, indata, frames, time, status):
        """Callback triggered by sounddevice for each audio buffer."""
        if status:
            logger.warning(f"Audio buffer status: {status}")
        self.callback_func(indata.copy())

    def start(self):
        """Starts the audio capture stream."""
        try:
            self.stream = sd.InputStream(
                device=self.device_index,
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self._audio_callback
            )
            self.stream.start()
            logger.info("Audio capture started.")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")

    def stop(self):
        """Stops the audio capture stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Audio capture stopped.")
