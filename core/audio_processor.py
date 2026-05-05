# core/audio_processor.py
import queue
import numpy as np
import logging
import configparser

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Buffers and processes audio chunks for transcription."""
    
    def __init__(self):
        self.chunk_seconds = config.getint('audio', 'chunk_seconds', fallback=5)
        self.sample_rate = config.getint('audio', 'sample_rate', fallback=16000)
        self.buffer = queue.Queue()
        self.frame_limit = self.chunk_seconds * self.sample_rate
        self.accumulated_frames = []

    def add_chunk(self, chunk: np.ndarray):
        """
        Adds a chunk of audio to the buffer.
        
        Args:
            chunk: Numpy array of audio samples.
        """
        self.accumulated_frames.append(chunk)
        
        # Check if we have accumulated enough frames
        total_frames = sum(len(c) for c in self.accumulated_frames)
        
        if total_frames >= self.frame_limit:
            # Concatenate and process
            full_audio = np.concatenate(self.accumulated_frames)
            
            # Keep only the last remaining frames if any (for rolling window)
            # For MVP, we'll just reset or implement overlap
            self.accumulated_frames = [] 
            
            return full_audio
        
        return None
