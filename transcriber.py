# transcriber.py

import os
import time
import logging
import numpy as np
import configparser
from typing import Optional

# path/to/GEMINI.md - Section 2: MANDATORY IMPORT GUARD
try:
    from faster_whisper import WhisperModel
    USE_FASTER_WHISPER = True
except (ImportError, OSError):
    import whisper as openai_whisper
    USE_FASTER_WHISPER = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instance
_model = None

def load_model():
    """
    Loads the Whisper model based on the active backend.
    """
    global _model
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    model_size = config.get('transcription', 'model_size', fallback='tiny.en')
    device = config.get('transcription', 'device', fallback='cpu')
    compute_type = config.get('transcription', 'compute_type', fallback='int8')
    model_dir = config.get('transcription', 'model_dir', fallback=None)
    local_files_only = config.getboolean('transcription', 'local_files_only', fallback=True)

    start_time = time.time()
    
    logger.info(f"Loading Whisper model '{model_size}' using {'faster-whisper' if USE_FASTER_WHISPER else 'openai-whisper'}")
    
    try:
        if USE_FASTER_WHISPER:
            _model = WhisperModel(
                model_size, 
                device=device, 
                compute_type=compute_type,
                download_root=model_dir,
                local_files_only=local_files_only
            )
        else:
            _model = openai_whisper.load_model(model_size, device=device)
            
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")

# Load model at import time
load_model()

def transcribe_chunk(audio_array: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Transcribe a numpy float32 audio array using the configured Whisper model.
    Passes initial_prompt from config.ini on every call to bias Whisper toward
    Bible vocabulary, verse notation, and theological terminology.

    Args:
        audio_array: float32 numpy array of audio samples.
        sample_rate:  sample rate in Hz (default 16000).

    Returns:
        Transcribed text string, stripped of leading/trailing whitespace.
    """
    config = configparser.ConfigParser()
    config.read('config.ini')
    initial_prompt = config.get('transcription', 'initial_prompt', fallback='')

    if _model is None:
        return ""
        
    try:
        if USE_FASTER_WHISPER:
            segments, _ = _model.transcribe(
                audio_array,
                beam_size=5,
                initial_prompt=initial_prompt if initial_prompt else None,
                language='en',
            )
            return ' '.join(seg.text for seg in segments).strip()
        else:
            # openai-whisper fallback
            result = _model.transcribe(
                audio_array,
                initial_prompt=initial_prompt if initial_prompt else None,
                language='en',
                fp16=False,
            )
            return result['text'].strip()
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return ""

if __name__ == '__main__':
    # Performance Benchmark
    print("Running performance benchmark...")
    # Create 3 seconds of dummy audio (silence + noise)
    dummy_audio = np.random.uniform(-0.01, 0.01, 16000 * 3).astype(np.float32)
    
    start_time = time.time()
    result = transcribe_chunk(dummy_audio)
    end_time = time.time()
    
    duration_ms = (end_time - start_time) * 1000
    print(f"Transcription of 3.0s audio took: {duration_ms:.2f}ms")
    print(f"Result: '{result}'")
